"""Adaptive halt decision models (V7 Task 169a)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

AdaptiveHaltDecisionStatus = Literal[
    "continue",
    "observe",
    "warn",
    "halt_candidate",
    "halt",
]
AdaptiveHaltReasonCode = Literal[
    "insufficient_samples",
    "warmup_protection",
    "health_p1_spike",
    "orphan_acceleration",
    "quality_debt_streak",
    "schedule_miss_spike",
    "context_pressure_streak",
    "cleanliness_regression",
]
AdaptiveHaltPolicyMode = Literal["observe", "enforce"]


class AdaptiveHaltPolicy(BaseModel):
    """Conservative adaptive halt policy consumed by the pure decision engine."""

    policy_id: str = "v7-adaptive-halt-mvp"
    policy_version: str = "1.0"
    mode: AdaptiveHaltPolicyMode = "observe"
    warmup_chapters: int = Field(default=10, ge=0)
    min_window_count: int = Field(default=1, ge=1)
    min_present_ratio: float = Field(default=0.6, ge=0.0, le=1.0)
    require_multi_signal: bool = True
    health_min_threshold: float = 7.0
    p1_median_threshold: float = Field(default=1.0, ge=0.0)
    p2_median_threshold: float = Field(default=3.0, ge=0.0)
    orphan_slope_threshold: float = Field(default=1.0, ge=0.0)
    orphan_delta_threshold: int = Field(default=5, ge=0)
    quality_debt_ratio: float = Field(default=0.4, ge=0.0, le=1.0)
    schedule_missed_rate: float = Field(default=0.5, ge=0.0, le=1.0)
    schedule_overdue_rate: float = Field(default=0.5, ge=0.0, le=1.0)
    context_pressure_ratio: float = Field(default=0.5, ge=0.0, le=1.0)
    context_budget_threshold: float = Field(default=1.0, ge=0.0)
    cleanliness_hard_count_threshold: int = Field(default=1, ge=0)


class AdaptiveHaltReason(BaseModel):
    """One explainable reason produced by adaptive halt evaluation."""

    reason_id: str
    code: AdaptiveHaltReasonCode
    severity: Literal["observe", "warn", "halt_candidate"] = "warn"
    signal_domain: str
    message: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class AdaptiveHaltDecision(BaseModel):
    """Result of evaluating one AdaptiveGateDataPlaneReport."""

    decision_id: str
    project_id: str
    run_id: str | None = None
    chapter_start: int = Field(ge=1)
    chapter_end: int = Field(ge=1)
    evaluated_at_chapter: int = Field(ge=1)
    status: AdaptiveHaltDecisionStatus = "continue"
    reasons: list[AdaptiveHaltReason] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)
    policy_id: str = "v7-adaptive-halt-mvp"
    policy_version: str = "1.0"
    created_at: datetime = Field(default_factory=datetime.now)
