"""Chapter-related models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ChapterGoal(BaseModel):
    """章节目标 — GoalPlanner 输出."""

    chapter_number: int = Field(ge=1)
    previous_summary: str = ""
    target_events: list[str] = Field(default_factory=list)
    emotional_arc: str = ""
    hooks: list[str] = Field(default_factory=list)
    obligations: list[str] = Field(default_factory=list)
    word_count_target: int = Field(3000, ge=500, le=20000)
    chapter_type: str = ""  # 从 GenreProfile.chapter_types 中选
    # V6 阶段 0 / Task 143：本章目标派生自哪个 ArcPlan.arc_index（无骨架时为 None）
    derived_from_arc: int | None = None


class ChapterVersion(BaseModel):
    """章节版本 — 每次生成/修订都创建新记录，禁止覆盖."""

    version_id: str
    project_id: str
    chapter_number: int = Field(ge=1)
    version_number: int = Field(1, ge=1)
    version_type: str = Field(
        default="draft",
        pattern=r"^(draft|revision|accepted|edited)$",
    )
    is_abandoned: bool = False

    content: str = ""
    word_count: int = Field(0, ge=0)
    scenes: list[dict[str, Any]] = Field(default_factory=list)
    generation_metadata: dict[str, Any] = Field(default_factory=dict)
    score_card: dict[str, Any] = Field(default_factory=dict)  # Task 106-patch

    # 外键引用（存 ID，不存对象）
    creative_brief_id: str | None = None
    literary_observation_id: str | None = None
    parent_version_id: str | None = None

    created_at: datetime = Field(default_factory=datetime.now)


class ChapterHead(BaseModel):
    """章节头 — 指向当前版本和 accepted 版本."""

    project_id: str
    chapter_number: int
    current_version_id: str | None = None
    accepted_version_id: str | None = None
    status: str = "draft"  # draft | under_review | accepted
    updated_at: datetime = Field(default_factory=datetime.now)
