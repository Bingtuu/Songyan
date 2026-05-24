"""Chapter-related models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ChapterGoal(BaseModel):
    """章节目标 — GoalPlanner 输出."""

    chapter_number: int
    previous_summary: str = ""
    target_events: list[str] = Field(default_factory=list)
    emotional_arc: str = ""
    hooks: list[str] = Field(default_factory=list)
    obligations: list[str] = Field(default_factory=list)
    word_count_target: int = 3000
    chapter_type: str = ""  # 从 GenreProfile.chapter_types 中选


class ChapterVersion(BaseModel):
    """章节版本 — 每次生成/修订都创建新记录，禁止覆盖."""

    version_id: str
    project_id: str
    chapter_number: int
    version_number: int = 1
    version_type: str = "draft"  # draft | revision | accepted | edited

    content: str = ""
    word_count: int = 0
    scenes: list[dict] = Field(default_factory=list)
    generation_metadata: dict = Field(default_factory=dict)

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
