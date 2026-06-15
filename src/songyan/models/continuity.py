"""ContinuityAuditor 模型 — 跨章一致性检查报告."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from songyan.models.human_mark import SuggestedMark


class OrphanedSetting(BaseModel):
    """被埋设后未被回收的设定."""

    tracking_id: str
    setting_key: str
    setting_name: str
    introduced_in_chapter: int
    last_mentioned_chapter: int
    chapters_since_mention: int
    category: str = "background"  # Task 094: critical/recurring/background/technical/historical


class ForgottenItem(BaseModel):
    """获得后未再提及的物品/道具."""

    track_id: str
    character_id: str
    item_name: str
    acquired_in_chapter: int
    last_used_chapter: int


class StateMismatch(BaseModel):
    """角色状态在短时间内剧烈变化（矛盾）."""

    character_id: str
    field: str
    chapter_a: int
    value_a: str
    chapter_b: int
    value_b: str
    issue: str


class OverdueForeshadowing(BaseModel):
    """超过预期回收章节仍未回收的伏笔."""

    foreshadowing_id: str
    description: str
    planted_in_chapter: int
    expected_resolve_chapter: int
    overdue_by: int


class ContinuityReport(BaseModel):
    """连续性审计报告."""

    report_id: str
    project_id: str
    checked_up_to_chapter: int
    orphaned_settings: list[OrphanedSetting] = Field(default_factory=list)
    forgotten_items: list[ForgottenItem] = Field(default_factory=list)
    state_mismatches: list[StateMismatch] = Field(default_factory=list)
    overdue_foreshadowings: list[OverdueForeshadowing] = Field(default_factory=list)
    suggested_marks: list[SuggestedMark] = Field(default_factory=list)
    overall_health_score: float = 10.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
