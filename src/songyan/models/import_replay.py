"""V15 Task 236: 导入回放模型."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ReplayMark(BaseModel):
    """单章回放幂等标记：已应用的 (project_id, chapter_number) 事实."""

    model_config = ConfigDict(extra="forbid")

    project_id: str
    run_id: str
    chapter_number: int = Field(ge=1)
    draft_version_id: str
    accepted_version_id: str
    summary_id: str | None = None
    source_fingerprint: str = Field(min_length=64, max_length=64)


class ChapterReplayOutcome(BaseModel):
    """单章回放结果（含跳过与失败）."""

    model_config = ConfigDict(extra="forbid")

    chapter_number: int
    title: str
    status: Literal["applied", "skipped", "failed"]
    accepted_version_id: str | None = None
    summary_missing_facts: int = 0
    over_token_budget: bool = False
    error: str | None = None


class ReplayReport(BaseModel):
    """一次回放 run 的结果汇总."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    project_id: str
    outcomes: list[ChapterReplayOutcome] = Field(default_factory=list)

    def by_status(self, status: str) -> list[ChapterReplayOutcome]:
        """按状态过滤章节结果."""
        return [o for o in self.outcomes if o.status == status]
