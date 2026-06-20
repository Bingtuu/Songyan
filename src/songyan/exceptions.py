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
