"""Human mark models — 人类辅助记忆标记."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class HumanMark(BaseModel):
    """人类标记 — 创作者主动标记或连续性审计生成的关键约束."""

    mark_id: str
    project_id: str
    mark_type: Literal["setting", "character", "foreshadowing", "item", "custom"]
    target_key: str
    note: str = ""
    priority: int = 5  # 1~10, >= threshold 时进入 ContextPackage
    created_at_chapter: int | None = None  # 标记创建时所在的章节号（仅展示/排序）
    resolved_at: datetime | None = None
    lifecycle_status: str = "active"  # active | dormant | archived
    created_at: datetime = Field(default_factory=datetime.utcnow)
    source: Literal["human", "continuity_auditor"] = "human"  # 标记来源
    version_id: str | None = None  # Task 118: 关联产生此标记的版本 ID
    severity: Literal["P1", "P2", "P3"] | None = None  # Task 118: 连续性问题严重等级


class SuggestedMark(BaseModel):
    """连续性审计建议的标记 — 由 ContinuityAuditor 生成."""

    target_key: str
    mark_type: Literal["setting", "character", "foreshadowing", "item"]
    reason: str
    suggested_priority: int = 7
    source_tracking_id: str = ""  # 关联 setting_tracking / inventory_tracker 的 ID
