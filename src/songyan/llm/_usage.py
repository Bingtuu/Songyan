"""LLM 调用遥测内部实现（V9 Task 175）——usage 提取 + llm_call_usage 落库.

从 client.py 抽离（175 阶段 B reviewer 建议）：client.py 只保留编排
（get_llm / call_llm / 重试 / 预算熔断），本模块承载单次调用的归因上下文、
token 用量提取与遥测落库。调用方仍经 client.py 编排入口间接触达，无需直接
import 本模块；测试的 patch 点（songyan.llm.client._record_llm_call_usage）
经 client 模块命名空间转发，保持有效。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import structlog
from structlog.contextvars import get_contextvars

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class LLMCallContext:
    """单次 LLM 调用的归因上下文（读取 174 的 structlog contextvars 字段链）."""

    run_id: str | None = None
    project_id: str | None = None
    chapter_number: int | None = None
    stage: str | None = None
    version_id: str | None = None
    # 仅随 174 字段链读取留痕；写库路由不消费（repo 经 settings.database_url 连接）
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
