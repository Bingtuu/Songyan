"""Songyan custom exception hierarchy."""

from __future__ import annotations


class SongyanError(Exception):
    """Root exception for all Songyan-specific errors."""


class LLMError(SongyanError):
    """LLM API call failed or timed out."""

    def __init__(
        self,
        message: str,
        raw_response: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.raw_response = raw_response
        self.cause = cause


class LLMResponseParseError(LLMError):
    """LLM response could not be parsed as expected format."""


class LLMRateLimitError(LLMError):
    """HTTP 429 / 限流；携带服务器建议的 Retry-After（秒）."""

    def __init__(
        self,
        message: str,
        retry_after: float | None = None,
        raw_response: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message, raw_response=raw_response, cause=cause)
        self.retry_after = retry_after


class LLMBudgetExceededError(SongyanError):  # noqa: N818
    """单 run LLM 调用/预算耗尽的可观测熔断（保留已生成章节）."""

    def __init__(
        self,
        message: str,
        used_calls: int,
        budget: int,
        last_chapter: int,
        used_cost: float | None = None,
        budget_cost: float | None = None,
    ) -> None:
        super().__init__(message)
        self.used_calls = used_calls
        self.budget = budget
        self.last_chapter = last_chapter
        # Task 175: run 级成本熔断上下文；调用次数熔断路径保持 None（向后兼容）
        self.used_cost = used_cost
        self.budget_cost = budget_cost


class GoalPlanningError(SongyanError):
    """Goal planning failed to produce valid output."""


class CreativeBriefError(SongyanError):
    """Creative brief generation failed."""


class DatabaseError(SongyanError):
    """Database operation failed (connection, query, migration)."""


class ContextBuildError(SongyanError):
    """ContextPackage assembly failed (incomplete data, missing fields)."""


class SettlementError(SongyanError):
    """Settlement extraction or validation failed."""


class PipelineError(SongyanError):
    """Workflow pipeline error (routing anomaly, state inconsistency)."""
    pass


class AutoHaltException(SongyanError):  # noqa: N818
    """Task 105: 流式验证自动熔断 — 连续多章指标异常时中断生成.

    保留已生成章节，不破坏已有状态。
    """

    def __init__(self, message: str, last_chapter: int, reason: str) -> None:
        super().__init__(message)
        self.last_chapter = last_chapter
        self.reason = reason
