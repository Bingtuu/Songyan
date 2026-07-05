"""Adaptive gate signal snapshot models (V7 Task 168a)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

AdaptiveGateSignalSourceStatus = Literal[
    "present",
    "missing",
    "insufficient",
    "observation",
]

ADAPTIVE_GATE_SIGNAL_DOMAINS: tuple[str, ...] = (
    "continuity",
    "quality",
    "literary",
    "cleanliness",
    "context",
    "narrative",
)


def default_source_status() -> dict[str, AdaptiveGateSignalSourceStatus]:
    """Return source status defaults for all adaptive gate domains."""
    return {domain: "missing" for domain in ADAPTIVE_GATE_SIGNAL_DOMAINS}


class AdaptiveGateContinuitySignals(BaseModel):
    """Continuity/orphan signals captured for one chapter or audit point."""

    health_score: float | None = None
    p1_count: int = Field(default=0, ge=0)
    p2_count: int = Field(default=0, ge=0)
    p3_count: int = Field(default=0, ge=0)
    orphan_total: int = Field(default=0, ge=0)
    orphan_critical: int = Field(default=0, ge=0)
    orphan_recurring: int = Field(default=0, ge=0)
    orphan_other: int = Field(default=0, ge=0)
    forgotten_count: int = Field(default=0, ge=0)
    state_mismatch_count: int = Field(default=0, ge=0)
    new_critical_count: int = Field(default=0, ge=0)
    new_setting_count: int = Field(default=0, ge=0)


class AdaptiveGateQualitySignals(BaseModel):
    """Quality gate and run-quality-debt signals."""

    quality_gate_passed: bool | None = None
    degraded_accept: bool = False
    convergence_failed: bool = False
    qg_false: bool = False
    revision_rounds: int | None = Field(default=None, ge=0)


class AdaptiveGateLiterarySignals(BaseModel):
    """Literary score signals reused by T3/T10-style data planes."""

    literary_quality_score: float | None = None
    character_autonomy_score: float | None = None
    conceptual_grounding_score: float | None = None
    fissure_preservation_score: float | None = None


class AdaptiveGateCleanlinessSignals(BaseModel):
    """Text cleanliness signals from Task 164/165."""

    meta_tag_leak_count: int = Field(default=0, ge=0)
    duplicate_paragraph_count: int = Field(default=0, ge=0)
    timeline_conflict_count: int = Field(default=0, ge=0)


class AdaptiveGateContextSignals(BaseModel):
    """Context pressure and DB telemetry signals."""

    context_emergency: bool = False
    budget_used: float | None = None
    budget_used_before_emergency: float | None = None
    db_size_bytes: int | None = Field(default=None, ge=0)
    scan_latency_ms: float | None = Field(default=None, ge=0)


class AdaptiveGateNarrativeSignals(BaseModel):
    """Planning and foreshadowing schedule lifecycle signals."""

    schedule_active_count: int = Field(default=0, ge=0)
    schedule_injected_count: int = Field(default=0, ge=0)
    schedule_satisfied_count: int = Field(default=0, ge=0)
    schedule_missed_count: int = Field(default=0, ge=0)
    schedule_cancelled_count: int = Field(default=0, ge=0)
    overdue_foreshadowing_count: int = Field(default=0, ge=0)
    active_planning_constraint_count: int = Field(default=0, ge=0)


class AdaptiveGateSignalSnapshot(BaseModel):
    """One persisted adaptive-gate input snapshot.

    ``run_id=None`` is valid at the model boundary for historical DB refreshes.
    The repository stores it as an empty string to keep SQLite upserts stable.
    """

    snapshot_id: str
    project_id: str
    chapter_number: int = Field(ge=1)
    run_id: str | None = None
    source_status: dict[str, AdaptiveGateSignalSourceStatus] = Field(
        default_factory=default_source_status
    )
    continuity: AdaptiveGateContinuitySignals = Field(
        default_factory=AdaptiveGateContinuitySignals
    )
    quality: AdaptiveGateQualitySignals = Field(default_factory=AdaptiveGateQualitySignals)
    literary: AdaptiveGateLiterarySignals = Field(
        default_factory=AdaptiveGateLiterarySignals
    )
    cleanliness: AdaptiveGateCleanlinessSignals = Field(
        default_factory=AdaptiveGateCleanlinessSignals
    )
    context: AdaptiveGateContextSignals = Field(default_factory=AdaptiveGateContextSignals)
    narrative: AdaptiveGateNarrativeSignals = Field(
        default_factory=AdaptiveGateNarrativeSignals
    )
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class AdaptiveGateTrendPoint(BaseModel):
    """One numeric trend point in an adaptive gate window."""

    name: str
    value: float | None = None
    sample_count: int = Field(default=0, ge=0)
    sufficient: bool = False
    source_status: AdaptiveGateSignalSourceStatus = "missing"


class AdaptiveGateSignalWindow(BaseModel):
    """Window-level adaptive gate data-plane signals.

    This model is intentionally descriptive: it does not encode halt/pass/fail
    decisions. Task 169 consumes it to decide whether a window is abnormal.
    """

    start_chapter: int = Field(ge=1)
    end_chapter: int = Field(ge=1)
    sample_count: int = Field(default=0, ge=0)
    window_size: int = Field(default=5, ge=1)
    source_status_counts: dict[str, dict[str, int]] = Field(default_factory=dict)
    health_min: float | None = None
    health_median: float | None = None
    p1_median: float | None = None
    p2_median: float | None = None
    orphan_slope: float | None = None
    orphan_delta: int | None = None
    new_critical_mean: float | None = None
    degraded_ratio: float | None = None
    convergence_ratio: float | None = None
    qg_false_ratio: float | None = None
    literary_quality_mean: float | None = None
    character_autonomy_mean: float | None = None
    conceptual_grounding_mean: float | None = None
    fissure_preservation_mean: float | None = None
    meta_tag_leak_total: int = Field(default=0, ge=0)
    duplicate_paragraph_total: int = Field(default=0, ge=0)
    timeline_conflict_total: int = Field(default=0, ge=0)
    context_emergency_ratio: float | None = None
    budget_used_max: float | None = None
    db_size_max_mb: float | None = None
    scan_latency_max_ms: float | None = None
    schedule_injected_count: int = Field(default=0, ge=0)
    schedule_satisfied_count: int = Field(default=0, ge=0)
    schedule_missed_count: int = Field(default=0, ge=0)
    schedule_overdue_count: int = Field(default=0, ge=0)
    schedule_hit_rate: float | None = None
    schedule_missed_rate: float | None = None
    schedule_overdue_rate: float | None = None


class AdaptiveGateDataPlaneReport(BaseModel):
    """Adaptive gate data-plane report for one project/range."""

    project_id: str
    run_id: str | None = None
    chapter_start: int = Field(ge=1)
    chapter_end: int = Field(ge=1)
    window_size: int = Field(default=5, ge=1)
    snapshot_count: int = Field(default=0, ge=0)
    source_status_counts: dict[str, dict[str, int]] = Field(default_factory=dict)
    windows: list[AdaptiveGateSignalWindow] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.now)
