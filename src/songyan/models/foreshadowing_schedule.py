"""Foreshadowing active scheduling models (V7 Task 167a)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

ForeshadowingScheduleStatus = Literal[
    "draft",
    "active",
    "injected",
    "satisfied",
    "missed",
    "cancelled",
]
ForeshadowingScheduleSourceType = Literal[
    "plot_thread",
    "foreshadowing",
    "planning_constraint",
]
ForeshadowingScheduleReason = Literal[
    "mainline_thread",
    "arc_thread_to_open",
    "arc_thread_to_resolve",
    "resolve_arc_due",
    "resolve_arc_overdue",
    "foreshadowing_due",
    "foreshadowing_overdue",
    "replan_backed",
]


class ForeshadowingScheduleItem(BaseModel):
    """One active scheduling candidate for a future chapter."""

    item_id: str
    plan_id: str
    project_id: str
    item_order: int = Field(ge=0)
    target_chapter: int = Field(ge=1)
    source_type: ForeshadowingScheduleSourceType
    source_id: str
    title: str = ""
    description: str = ""
    priority_score: float = 0.0
    reason_codes: list[ForeshadowingScheduleReason] = Field(default_factory=list)
    rationale: str = ""
    status: ForeshadowingScheduleStatus = "draft"
    evidence: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)


class ForeshadowingSchedulePlan(BaseModel):
    """A per-chapter schedule plan generated before planning injection."""

    plan_id: str
    project_id: str
    target_chapter: int = Field(ge=1)
    current_arc_index: int | None = None
    horizon_chapters: int = Field(default=5, ge=0)
    max_items: int = Field(default=3, ge=0)
    status: ForeshadowingScheduleStatus = "draft"
    summary: str = ""
    evidence: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    items: list[ForeshadowingScheduleItem] = Field(default_factory=list)
