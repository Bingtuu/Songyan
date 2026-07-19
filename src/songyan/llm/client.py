"""LLM Client —— 统一封装 LangChain + litellm."""

from __future__ import annotations

import asyncio
import inspect
import os
import time
from contextvars import ContextVar
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Literal

import structlog

from songyan.config import settings
from songyan.exceptions import LLMBudgetExceededError, LLMError, LLMRateLimitError
from songyan.llm._usage import (
    _current_call_context,
    _extract_usage,
    _record_llm_call_usage,
    _UsageExtract,
)
from songyan.llm.retry import retry_with_backoff
from songyan.utils.cost_estimator import count_tokens, estimate_cost_from_tokens

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.messages import BaseMessage

logger = structlog.get_logger(__name__)

# per-run LLM 调用计数（非进程级单例，随 async context 生命周期）
# 已知同病（Task 175 阶段 D 确诊，不在该次修复范围）：与 _llm_run_cost_cny 一样，
# LangGraph 节点 task 的 context 副本不回传 ContextVar 写入，计数按节点重置；
# 默认 llm_run_call_budget=0 不启用，启用前需同样改为 DB 权威。
_llm_call_count: ContextVar[int] = ContextVar("llm_call_count", default=0)
_llm_budget_last_chapter: ContextVar[int] = ContextVar("llm_budget_last_chapter", default=0)
# Task 175: per-run LLM 成本累计（CNY，镜像 _llm_call_count 模式）；
# 由 init_run_cost_from_db 在 run 确定后初始化（resume 接续历史合计）。
# 阶段 D 修复后：run 上下文下本变量只是 DB 权威值的镜像（call_llm 前置检查把
# llm_call_usage 合计 set 进来）——LangGraph 节点 task 的 context 副本不回传
# ContextVar 写入，本变量在 run 语义下不可作权威；非 run 上下文（脚本/测试）
# 仍是权威累计路径。
_llm_run_cost_cny: ContextVar[float] = ContextVar("llm_run_cost_cny", default=0.0)
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


def get_llm_run_cost() -> float:
    """获取当前 run 已累计的 LLM 成本（CNY）."""
    return _llm_run_cost_cny.get(0.0)


async def init_run_cost_from_db(run_id: str, *, fallback: float | None = None) -> float:
    """从 llm_call_usage 历史合计初始化 run 级成本累计器（Task 175，resume 安全）.

    新 run 无用量行时初始化为 0.0；resume run 恢复历史累计，使成本预算熔断
    跨进程/跨 resume 连续。DB 读取失败（如库未迁移遥测表）时回退 0.0 并记
    warning；调用方可传入 fallback 保留已持久化 total_cost，避免 resume 早期保存
    把历史值冲为 0.0。与遥测落库同一哲学：生成不可断；预算熔断退化为仅统计
    当前进程新增成本。

    Returns:
        初始化后的累计成本（CNY）
    """
    from songyan.db.llm_call_usage_repo import LlmCallUsageRepository

    try:
        total = await LlmCallUsageRepository().sum_cost_for_run(run_id)
    except Exception as exc:
        logger.warning("llm.run_cost_init_failed", run_id=run_id, error=str(exc))
        total = fallback if fallback is not None else 0.0
    _llm_run_cost_cny.set(total)
    return total


def _resolve_model() -> str:
    """解析当前模型名（settings 优先，环境变量兜底）；get_llm 与遥测路径共用."""
    return settings.llm_model or os.getenv("LLM_MODEL", "deepseek-chat")


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
        import litellm
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
    model = _resolve_model()

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
# Task 175: 调用遥测（usage 提取 + llm_call_usage 落库）已抽离至 _usage.py；
# 本模块经上方 import 转发 `_record_llm_call_usage` 等名字（测试 patch 点不变）
# --------------------------------------------------------------------------- #


async def call_llm(
    prompt: str,
    *,
    temperature: float | None = None,
    max_tokens: int = 4096,
    max_retries: int | None = None,
    timeout: int = 60,
) -> str:
    """调用 LLM 并返回文本响应.

    自带限流感知退避重试；启用 llm_run_call_budget 时按 run 级计数熔断；
    启用 run_cost_budget 时按 run 级成本（CNY）做前置 + 后置双检查熔断（Task 175；
    run 上下文下以 llm_call_usage 的 DB 合计为权威，见前置检查注释）。

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
        LLMBudgetExceededError: 单 run 调用/成本预算耗尽（成本熔断抛出时不返回文本）
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

    # Task 175: 成本预算前置检查——已用成本达预算时不再发起新调用。
    # 阶段 D 修复：run 上下文（174 字段链绑定 run_id）下以 DB 为权威——
    # LangGraph 节点在 task 的 context 副本中执行，_llm_run_cost_cny 的 set()
    # 不回传 graph runner，累计器按节点重置，导致 run_cost_budget 熔断在生产
    # 失效（阶段 D 实跑 budget=0.05 跑出 ¥0.217 未停）。DB 合计覆盖所有节点已
    # 落库的调用（record 在 _invoke 成功路径内 await 且自带 commit，跨节点立即
    # 可见）。读到的 DB 值 set 进累计器作镜像（非 add），使 get_llm_run_cost()
    # 在 run 语义下仍返回真实累计；后置检查 used_after = 该镜像值 + 本次成本，
    # 不再二次查库。DB 读失败（库未迁移等）回退累计器当前值 + warning，不阻断
    # 生成（与遥测同一哲学）；非 run 上下文（脚本/测试）保持 ContextVar 累计器
    # 路径不变。
    cost_budget = settings.run_cost_budget
    call_context = _current_call_context()
    if cost_budget > 0:
        used_cost = _llm_run_cost_cny.get(0.0)
        if call_context.run_id:
            try:
                from songyan.db.llm_call_usage_repo import LlmCallUsageRepository

                used_cost = await LlmCallUsageRepository().sum_cost_for_run(
                    call_context.run_id
                )
                _llm_run_cost_cny.set(used_cost)
            except Exception as exc:
                logger.warning(
                    "llm.run_cost_precheck_db_failed",
                    run_id=call_context.run_id,
                    error=str(exc),
                )
        if used_cost >= cost_budget:
            raise LLMBudgetExceededError(
                message=f"单 run 成本预算耗尽（¥{cost_budget:.2f}），已用 ¥{used_cost:.4f}",
                used_calls=_llm_call_count.get(0),
                budget=0,
                last_chapter=_llm_budget_last_chapter.get(0),
                used_cost=used_cost,
                budget_cost=cost_budget,
            )

    llm = get_llm(temperature=temperature, max_tokens=max_tokens, timeout=timeout)
    model = _resolve_model()
    # attempt 索引由 retry_with_backoff 经 on_attempt 回调透传（Task 175）；
    # cost_cny 由成功路径回传——ContextVar 写入不跨 asyncio.wait_for 的 task
    # 边界回传，故累计在 call_llm 外层 context 进行（与 _llm_call_count 同层）
    attempt_state: dict[str, Any] = {"index": 0, "cost_cny": 0.0}

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
        except asyncio.CancelledError:
            # 总超时/外部取消：in-flight 尝试也落一行（长跑最需要的遥测场景）；
            # CancelledError 是 BaseException，不在下方 Exception 路径内
            latency_ms = int((time.monotonic() - start) * 1000)
            await _record_llm_call_usage(
                context=call_context,
                model=model,
                latency_ms=latency_ms,
                retry_attempt=attempt_state["index"],
                success=False,
                error="cancelled/timeout",
            )
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
            if usage.token_source == "response":
                prompt_tokens = usage.prompt_tokens
                completion_tokens = usage.completion_tokens
            else:
                prompt_tokens = count_tokens(prompt, model)
                completion_tokens = count_tokens(text, model)
            # 成本字段与预算均为 CNY。LiteLLM 的 response_cost 语义是 USD，且当前
            # ChatLiteLLM 默认不透传该字段；在接入明确币种转换前，一律使用本地
            # CNY pricing estimate，避免把 USD 当 CNY 累计导致预算漏停。
            cost_cny = estimate_cost_from_tokens(prompt_tokens, completion_tokens, model)
            cost_source: Literal["provider_cost", "pricing_estimate"] = "pricing_estimate"
        except Exception as exc:  # 提取失败不阻断：记零值 estimate
            logger.warning("llm.usage_extract_failed", error=str(exc))
            usage = _UsageExtract()
            prompt_tokens = 0
            completion_tokens = 0
            cost_cny = 0.0
            cost_source = "pricing_estimate"
        # Task 175: 成本回传先于遥测落库——即使 record 失败被吞，外层累计器也会
        # 增加本次成本，telemetry 故障不会绕过预算熔断
        attempt_state["cost_cny"] = cost_cny
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
        text = await asyncio.wait_for(
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
    # Task 175: 成功调用的成本在外层 context 累加（wait_for 的 task 副本不回传
    # ContextVar 写入）；累加独立于 record 成败，telemetry 故障不会绕过预算熔断。
    # run 上下文下前置检查已把 DB 合计镜像进累计器，累加后即为「DB 前置合计 +
    # 本次成本」；本次调用的 record 已在 _invoke 内先于返回落库，故 resume/下一次
    # 前置检查从 DB 读到的值与此处一致
    _llm_run_cost_cny.set(_llm_run_cost_cny.get(0.0) + attempt_state["cost_cny"])
    # Task 175: 成本预算后置二次检查——单次昂贵调用把预算打穿时，本次调用不返回
    # 文本，立即熔断（由 phase2_graph 章循环接住并 pause）；不二次查库
    if cost_budget > 0:
        used_cost_after = _llm_run_cost_cny.get(0.0)
        if used_cost_after > cost_budget:
            raise LLMBudgetExceededError(
                message=(
                    f"单 run 成本预算超限（¥{cost_budget:.2f}），"
                    f"已用 ¥{used_cost_after:.4f}"
                ),
                used_calls=_llm_call_count.get(0),
                budget=0,
                last_chapter=_llm_budget_last_chapter.get(0),
                used_cost=used_cost_after,
                budget_cost=cost_budget,
            )
    return text
