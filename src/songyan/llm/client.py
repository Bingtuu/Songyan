"""LLM Client —— 统一封装 LangChain + litellm."""

from __future__ import annotations

import asyncio
import inspect
import os
from contextvars import ContextVar
from functools import lru_cache
from typing import TYPE_CHECKING, Any

import structlog

from songyan.config import settings
from songyan.exceptions import LLMBudgetExceededError, LLMError, LLMRateLimitError
from songyan.llm.retry import retry_with_backoff

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.messages import BaseMessage

logger = structlog.get_logger(__name__)

# per-run LLM 调用计数（非进程级单例，随 async context 生命周期）
_llm_call_count: ContextVar[int] = ContextVar("llm_call_count", default=0)
_llm_budget_last_chapter: ContextVar[int] = ContextVar("llm_budget_last_chapter", default=0)
_llm_client_registry: dict[tuple[str, str, str, float, int, int], Any] = {}

_CLIENT_RESOURCE_ATTRS = (
    "client",
    "async_client",
    "root_client",
    "aclient",
    "http_client",
    "async_http_client",
    "_client",
    "_async_client",
)


def reset_llm_call_count() -> None:
    """重置当前 run 的 LLM 调用计数（在 run 开始时调用）."""
    _llm_call_count.set(0)


def set_llm_budget_last_chapter(chapter_number: int) -> None:
    """设置预算熔断异常中记录的最近章号."""
    _llm_budget_last_chapter.set(chapter_number)


def get_llm_call_count() -> int:
    """获取当前 run 已用 LLM 调用数."""
    return _llm_call_count.get(0)


def _extract_retry_after(exc: Exception) -> float | None:
    """从异常中提取 Retry-After（秒）."""
    headers: dict[str, str] | None = None
    for attr in ("headers", "response", "litellm_headers"):
        obj = getattr(exc, attr, None)
        if obj is None:
            continue
        if attr == "response":
            headers = getattr(obj, "headers", None)
        else:
            headers = obj if isinstance(obj, dict) else None
        if headers:
            for key in ("retry-after", "Retry-After"):
                value = headers.get(key)
                if value:
                    try:
                        return float(value)
                    except (ValueError, TypeError):
                        return None
    return None


def _is_rate_limit_error(exc: Exception) -> bool:
    """判断异常是否为 429 / 限流."""
    status_code = getattr(exc, "status_code", None)
    if status_code == 429:
        return True
    # litellm 常见限流异常名
    if type(exc).__name__ in ("RateLimitError", "RateLimitExceededError"):
        return True
    return False


async def _maybe_close_resource(resource: Any, *, seen: set[int]) -> None:
    """Close one resource if it exposes close/aclose; best-effort and idempotent."""
    if resource is None:
        return
    resource_id = id(resource)
    if resource_id in seen:
        return
    seen.add(resource_id)

    for method_name in ("aclose", "close"):
        method = getattr(resource, method_name, None)
        if not callable(method):
            continue
        try:
            result = method()
            if inspect.isawaitable(result):
                await result
            return
        except Exception as exc:  # 清理路径任何失败都不应传播
            logger.warning(
                "llm.client_close_failed",
                resource_type=type(resource).__name__,
                method=method_name,
                error=str(exc),
            )
            return


async def _close_litellm_global_client(seen: set[int]) -> None:
    try:
        import litellm  # type: ignore[import-untyped]
    except ImportError:
        return

    for method_name in ("aclose", "close"):
        method = getattr(litellm, method_name, None)
        if not callable(method):
            continue
        method_id = id(method)
        if method_id in seen:
            return
        seen.add(method_id)
        try:
            result = method()
            if inspect.isawaitable(result):
                await result
        except Exception as exc:  # 清理路径任何失败都不应传播
            logger.warning(
                "llm.litellm_global_close_failed",
                method=method_name,
                error=str(exc),
            )
        return


async def aclose_llm_clients() -> None:
    """Close cached LLM client resources before process or run shutdown."""
    seen: set[int] = set()
    clients = list(_llm_client_registry.values())

    for client in clients:
        for attr in _CLIENT_RESOURCE_ATTRS:
            try:
                resource = getattr(client, attr, None)
            except (RuntimeError, AttributeError, TypeError, ValueError):
                continue
            if resource is not None and resource is not client:
                await _maybe_close_resource(resource, seen=seen)
        await _maybe_close_resource(client, seen=seen)

    await _close_litellm_global_client(seen)
    _llm_client_registry.clear()
    _get_llm_cached.cache_clear()


@lru_cache(maxsize=16)
def _get_llm_cached(
    model: str,
    api_key: str,
    base_url: str,
    temperature: float,
    max_tokens: int,
    timeout: int,
) -> BaseChatModel:
    """缓存 LLM 实例，避免每次调用都重新创建."""
    from langchain_litellm import ChatLiteLLM

    client = ChatLiteLLM(  # type: ignore[call-arg]  # langchain_litellm stub: base_url/timeout
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    )
    _llm_client_registry[
        (model, api_key, base_url, temperature, max_tokens, timeout)
    ] = client
    return client


def get_llm(
    temperature: float = 0.7, max_tokens: int = 4096, timeout: int = 60
) -> BaseChatModel:
    """获取配置好的 LLM 实例（带缓存）.

    使用 litellm 统一接口，通过环境变量或 settings 配置模型参数。
    相同参数组合会复用已创建的实例。

    Args:
        temperature: 采样温度
        max_tokens: 最大输出 token 数（默认 4096）
        timeout: 单次 LLM 调用超时秒数（默认 60）

    Returns:
        配置好的 ChatLiteLLM 实例

    Raises:
        LLMError: 配置缺失或模型初始化失败
    """
    import importlib.util

    if importlib.util.find_spec("langchain_litellm") is None:
        msg = "langchain-litellm 未安装，无法初始化 LLM"
        raise LLMError(msg)

    api_key = settings.llm_api_key or os.getenv("LLM_API_KEY", "")
    base_url = settings.llm_base_url or os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
    model = settings.llm_model or os.getenv("LLM_MODEL", "deepseek-chat")

    if not api_key:
        msg = "LLM API Key 未配置（请设置 LLM_API_KEY 环境变量或在 .env 中配置 llm_api_key）"
        raise LLMError(msg)

    try:
        cache_key = (
            model,
            api_key,
            base_url,
            temperature,
            max_tokens,
            timeout,
        )
        llm = _get_llm_cached(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
        _llm_client_registry.setdefault(cache_key, llm)
    except (ImportError, ValueError, TypeError, RuntimeError, ConnectionError) as e:
        msg = f"LLM 初始化失败 (model={model}): {e}"
        raise LLMError(msg, cause=e) from e

    logger.debug(
        "llm.init",
        model=model,
        base_url=base_url,
        temperature=temperature,
        timeout=timeout,
    )
    return llm


async def call_llm(
    prompt: str,
    *,
    temperature: float | None = None,
    max_tokens: int = 4096,
    max_retries: int | None = None,
    timeout: int = 60,
) -> str:
    """调用 LLM 并返回文本响应.

    自带限流感知退避重试；启用 llm_run_call_budget 时按 run 级计数熔断。

    Args:
        prompt: 发送给 LLM 的提示文本
        temperature: 采样温度；None 时使用 settings.llm_temperature（默认 0.7）
        max_tokens: 最大输出 token 数（默认 4096）
        max_retries: 最大重试次数；None 时使用 settings.llm_max_retries
        timeout: 单次 LLM 调用超时秒数（默认 60）

    Returns:
        LLM 返回的文本内容

    Raises:
        LLMError: 调用失败（重试后仍失败）
        LLMBudgetExceededError: 单 run 调用预算耗尽
    """
    if temperature is None:
        temperature = settings.llm_temperature
    if max_retries is None:
        max_retries = settings.llm_max_retries

    budget = settings.llm_run_call_budget
    if budget > 0:
        count = _llm_call_count.get(0) + 1
        if count > budget:
            last_chapter = _llm_budget_last_chapter.get(0)
            raise LLMBudgetExceededError(
                message=f"单 run LLM 调用预算耗尽（{budget} 次），已用 {count - 1} 次",
                used_calls=count - 1,
                budget=budget,
                last_chapter=last_chapter,
            )
        _llm_call_count.set(count)

    llm = get_llm(temperature=temperature, max_tokens=max_tokens, timeout=timeout)

    async def _invoke() -> str:
        try:
            from langchain_core.messages import HumanMessage

            response: BaseMessage = await llm.ainvoke([HumanMessage(content=prompt)])
            return str(response.content)
        except (TypeError, ValueError, KeyError, AttributeError):
            # 编程错误（参数类型、配置错误等），直接抛出，不重试
            raise
        except Exception as e:
            if _is_rate_limit_error(e):
                retry_after = _extract_retry_after(e)
                raise LLMRateLimitError(
                    f"LLM 调用被限流: {e}",
                    retry_after=retry_after,
                    cause=e,
                ) from e
            # 网络/API 瞬态错误，包装为 LLMError 以便重试
            raise LLMError(f"LLM 调用失败: {e}", cause=e) from e

    try:
        # 总超时 = 单次超时 * 最大重试次数 + 退避延迟缓冲
        total_timeout = timeout * max_retries + 30
        return await asyncio.wait_for(
            retry_with_backoff(
                _invoke,
                max_retries=max_retries,
                base_delay=1.0,
                max_delay=10.0,
                retryable_exceptions=(LLMError,),
            ),
            timeout=total_timeout,
        )
    except TimeoutError as e:
        raise LLMError(f"LLM 调用总超时（超过 {total_timeout} 秒）", cause=e) from e
    except LLMError:
        raise
