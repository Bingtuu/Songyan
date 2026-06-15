"""Project-level run state models — multi-chapter orchestration."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ProjectRunState(BaseModel):
    """项目级运行状态 — 追踪多章流水线进度."""

    run_id: str
    project_id: str
    chapter_range_start: int
    chapter_range_end: int
    current_chapter: int = 0
    completed_chapters: list[int] = Field(default_factory=list)
    failed_chapters: list[int] = Field(default_factory=list)
    accumulated_summary: str = ""
    total_cost: float = 0.0
    status: str = "running"  # running | paused | completed | failed
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ProjectRunResult(BaseModel):
    """多章流水线运行结果."""

    project_id: str
    run_id: str
    chapters_completed: list[int] = Field(default_factory=list)
    chapters_failed: list[int] = Field(default_factory=list)
    total_cost: float = 0.0
    total_duration_sec: float = 0.0
    final_status: str = ""  # completed | partial | failed
    accumulated_summary: str = ""
