"""LLM Client —— 统一封装 LangChain + litellm."""

from __future__ import annotations

import asyncio
import inspect
import os
import time
from contextvars import ContextVar
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Literal

import structlog
from structlog.contextvars import get_contextvars

from songyan.config import settings
from songyan.exceptions import LLMBudgetExceededError, LLMError, LLMRateLimitError
from songyan.llm.retry import retry_with_backoff
from songyan.utils.cost_estimator import count_tokens, estimate_cost_from_tokens

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


# --------------------------------------------------------------------------- #
# Task 175: 调用遥测（usage 提取 + llm_call_usage 落库）
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class LLMCallContext:
    """单次 LLM 调用的归因上下文（读取 174 的 structlog contextvars 字段链）."""

    run_id: str | None = None
    project_id: str | None = None
    chapter_number: int | None = None
    stage: str | None = None
    version_id: str | None = None
    db_path: str | None = None
    agent: str = "unknown"


def _context_str(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _current_call_context() -> LLMCallContext:
    """从 structlog contextvars 组装调用上下文；读取失败回退全空（不阻断调用）."""
    try:
        ctx = get_contextvars()
    except Exception:  # 防御：contextvars 读取异常不应影响 LLM 调用
        return LLMCallContext()
    chapter_raw = ctx.get("chapter_number")
    chapter_number: int | None = None
    if isinstance(chapter_raw, int):
        chapter_number = chapter_raw
    elif isinstance(chapter_raw, str):
        try:
            chapter_number = int(chapter_raw)
        except ValueError:
            chapter_number = None
    return LLMCallContext(
        run_id=_context_str(ctx.get("run_id")),
        project_id=_context_str(ctx.get("project_id")),
        chapter_number=chapter_number,
        stage=_context_str(ctx.get("stage")),
        version_id=_context_str(ctx.get("version_id")),
        db_path=_context_str(ctx.get("db_path")),
        agent=_context_str(ctx.get("agent")) or "unknown",
    )


@dataclass(frozen=True)
class _UsageExtract:
    """从 response 提取的 token 用量；提取不到时全零 + estimate."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    token_source: Literal["response", "estimate"] = "estimate"
    cached_tokens: int | None = None
    cache_miss_tokens: int | None = None


def _meta_value(obj: Any, key: str) -> Any:
    """dict 键或对象属性二选一读取；缺失返回 None（不对 response 形状做假设）."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def _coerce_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _coerce_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _extract_usage(response: Any) -> _UsageExtract:
    """按 langchain-core → litellm 顺序提取 token 用量，缺失回退 estimate.

    DeepSeek cache 信息来源：`prompt_tokens_details.cached_tokens` /
    `prompt_cache_hit_tokens` / `prompt_cache_miss_tokens`（litellm 风格）或
    `usage_metadata.input_token_details.cache_read`（langchain-core 风格）。
    """
    usage = _meta_value(response, "usage_metadata")
    prompt_tokens = _coerce_int(_meta_value(usage, "input_tokens"))
    completion_tokens = _coerce_int(_meta_value(usage, "output_tokens"))
    if prompt_tokens is not None or completion_tokens is not None:
        details = _meta_value(usage, "input_token_details")
        return _UsageExtract(
            prompt_tokens=prompt_tokens or 0,
            completion_tokens=completion_tokens or 0,
            token_source="response",
            cached_tokens=_coerce_int(_meta_value(details, "cache_read")),
        )
    meta = _meta_value(response, "response_metadata")
    token_usage: dict[str, Any] | None = None
    if isinstance(meta, dict):
        for key in ("token_usage", "usage"):
            candidate = meta.get(key)
            if isinstance(candidate, dict):
                token_usage = candidate
                break
    if token_usage is not None:
        prompt_tokens = _coerce_int(token_usage.get("prompt_tokens"))
        completion_tokens = _coerce_int(token_usage.get("completion_tokens"))
        if prompt_tokens is not None or completion_tokens is not None:
            cached = _coerce_int(
                _meta_value(token_usage.get("prompt_tokens_details"), "cached_tokens")
            )
            if cached is None:
                cached = _coerce_int(token_usage.get("prompt_cache_hit_tokens"))
            return _UsageExtract(
                prompt_tokens=prompt_tokens or 0,
                completion_tokens=completion_tokens or 0,
                token_source="response",
                cached_tokens=cached,
                cache_miss_tokens=_coerce_int(token_usage.get("prompt_cache_miss_tokens")),
            )
    return _UsageExtract()


def _extract_provider_cost(response: Any) -> float | None:
    """响应元数据中的 provider 精确成本（如 litellm response_cost）；不存在返回 None."""
    meta = _meta_value(response, "response_metadata")
    if not isinstance(meta, dict):
        return None
    return _coerce_float(meta.get("response_cost"))


async def _record_llm_call_usage(
    *,
    context: LLMCallContext,
    model: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    cost_cny: float = 0.0,
    token_source: Literal["response", "estimate"] = "estimate",
    cost_source: Literal["provider_cost", "pricing_estimate"] = "pricing_estimate",
    cached_tokens: int | None = None,
    cache_miss_tokens: int | None = None,
    latency_ms: int = 0,
    retry_attempt: int = 0,
    success: bool = True,
    error: str | None = None,
) -> None:
    """写入一行调用遥测；telemetry 永不阻断生成（repo 已全捕获，这里再兜一层）."""
    try:
        from songyan.db.llm_call_usage_repo import LlmCallUsageRepository

        await LlmCallUsageRepository().record(
            run_id=context.run_id,
            project_id=context.project_id,
            chapter_number=context.chapter_number,
            agent=context.agent,
            stage=context.stage,
            version_id=context.version_id,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_cny=cost_cny,
            token_source=token_source,
            cost_source=cost_source,
            cached_tokens=cached_tokens,
            cache_miss_tokens=cache_miss_tokens,
            latency_ms=latency_ms,
            retry_attempt=retry_attempt,
            success=success,
            error=error,
        )
    except Exception as exc:
        logger.warning("llm.usage_record_failed", error=str(exc))


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
    model = settings.llm_model or os.getenv("LLM_MODEL", "deepseek-chat")
    call_context = _current_call_context()
    # attempt 索引由 retry_with_backoff 经 on_attempt 回调透传（Task 175）
    attempt_state = {"index": 0}

    def _on_attempt(index: int) -> None:
        attempt_state["index"] = index

    async def _invoke() -> str:
        start = time.monotonic()
        try:
            from langchain_core.messages import HumanMessage

            response: BaseMessage = await llm.ainvoke([HumanMessage(content=prompt)])
            text = str(response.content)
        except (TypeError, ValueError, KeyError, AttributeError):
            # 编程错误（参数类型、配置错误等），直接抛出，不重试
            raise
        except Exception as e:
            latency_ms = int((time.monotonic() - start) * 1000)
            await _record_llm_call_usage(
                context=call_context,
                model=model,
                latency_ms=latency_ms,
                retry_attempt=attempt_state["index"],
                success=False,
                error=str(e)[:500],
            )
            if _is_rate_limit_error(e):
                retry_after = _extract_retry_after(e)
                raise LLMRateLimitError(
                    f"LLM 调用被限流: {e}",
                    retry_after=retry_after,
                    cause=e,
                ) from e
            # 网络/API 瞬态错误，包装为 LLMError 以便重试
            raise LLMError(f"LLM 调用失败: {e}", cause=e) from e

        latency_ms = int((time.monotonic() - start) * 1000)
        try:
            usage = _extract_usage(response)
            provider_cost = _extract_provider_cost(response)
            if usage.token_source == "response":
                prompt_tokens = usage.prompt_tokens
                completion_tokens = usage.completion_tokens
            else:
                prompt_tokens = count_tokens(prompt, model)
                completion_tokens = count_tokens(text, model)
            cost_source: Literal["provider_cost", "pricing_estimate"]
            if provider_cost is not None:
                cost_cny = provider_cost
                cost_source = "provider_cost"
            else:
                # 保守定价估算：response token ≠ 精确金额，标 pricing_estimate
                cost_cny = estimate_cost_from_tokens(prompt_tokens, completion_tokens, model)
                cost_source = "pricing_estimate"
        except Exception as exc:  # 提取失败不阻断：记零值 estimate
            logger.warning("llm.usage_extract_failed", error=str(exc))
            usage = _UsageExtract()
            prompt_tokens = 0
            completion_tokens = 0
            cost_cny = 0.0
            cost_source = "pricing_estimate"
        await _record_llm_call_usage(
            context=call_context,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_cny=cost_cny,
            token_source=usage.token_source,
            cost_source=cost_source,
            cached_tokens=usage.cached_tokens,
            cache_miss_tokens=usage.cache_miss_tokens,
            latency_ms=latency_ms,
            retry_attempt=attempt_state["index"],
            success=True,
        )
        return text

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
                on_attempt=_on_attempt,
            ),
            timeout=total_timeout,
        )
    except TimeoutError as e:
        raise LLMError(f"LLM 调用总超时（超过 {total_timeout} 秒）", cause=e) from e
    except LLMError:
        raise
