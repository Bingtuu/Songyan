"""Task 125: 候选硬门禁阈值调优单元测试."""

from __future__ import annotations

from songyan.models import ContinuityReport, GateConfig, StateMismatch
from songyan.workflows._gates import (
    check_health_low_single_gate,
    check_health_low_streak_gate,
    evaluate_all_gates,
)


def _state_mismatches(count: int) -> list[StateMismatch]:
    return [
        StateMismatch(
            character_id=f"c{i}",
            field="health",
            chapter_a=1,
            value_a="fine",
            chapter_b=2,
            value_b="dead",
            issue="inconsistent",
        )
        for i in range(count)
    ]


def _report(
    chapter: int,
    health_score: float = 10.0,
    p1_count: int = 0,
) -> ContinuityReport:
    return ContinuityReport(
        report_id=f"rpt-{chapter}",
        project_id="proj",
        checked_up_to_chapter=chapter,
        overall_health_score=health_score,
        state_mismatches=_state_mismatches(p1_count),
    )


# ---------------------------------------------------------------------------
# P1 anomaly gate
# ---------------------------------------------------------------------------


def test_p1_anomaly_not_triggered_when_below_baseline() -> None:
    report = _report(6, p1_count=30)
    cfg = GateConfig(
        health_low_gate_enabled=True,
        health_low_p1_halt=True,
        health_low_p1_min_absolute=20,
        health_low_p1_anomaly_factor=1.5,
    )
    triggered, _ = check_health_low_single_gate(
        report, cfg, previous_p1_counts=[20, 20, 20]
    )
    assert not triggered


def test_p1_anomaly_triggered_when_spike_above_baseline() -> None:
    report = _report(6, p1_count=60)
    cfg = GateConfig(
        health_low_gate_enabled=True,
        health_low_p1_halt=True,
        health_low_p1_min_absolute=50,
        health_low_p1_anomaly_factor=1.5,
    )
    triggered, reasons = check_health_low_single_gate(
        report, cfg, previous_p1_counts=[20, 20, 20]
    )
    assert triggered
    assert "P1_count=60" in reasons[0]


def test_p1_anomaly_not_triggered_below_min_absolute() -> None:
    report = _report(6, p1_count=5)
    cfg = GateConfig(
        health_low_gate_enabled=True,
        health_low_p1_halt=True,
        health_low_p1_min_absolute=10,
        health_low_p1_anomaly_factor=1.5,
    )
    triggered, _ = check_health_low_single_gate(report, cfg, previous_p1_counts=[])
    assert not triggered


# ---------------------------------------------------------------------------
# health_score drop gate
# ---------------------------------------------------------------------------


def test_score_drop_triggered() -> None:
    previous = _report(3, health_score=8.0)
    current = _report(6, health_score=2.0)
    cfg = GateConfig(
        health_low_gate_enabled=True,
        health_low_absolute_score_halt=True,
        health_low_score_drop_threshold=2.0,
    )
    triggered, reasons = check_health_low_single_gate(
        current, cfg, previous_report=previous
    )
    assert triggered
    assert "dropped from 8.0 to 2.0" in reasons[0]


def test_score_drop_not_triggered_when_rising() -> None:
    previous = _report(3, health_score=2.0)
    current = _report(6, health_score=8.0)
    cfg = GateConfig(
        health_low_gate_enabled=True,
        health_low_absolute_score_halt=True,
        health_low_score_drop_threshold=2.0,
    )
    triggered, _ = check_health_low_single_gate(current, cfg, previous_report=previous)
    assert not triggered


def test_score_drop_not_triggered_without_previous_report() -> None:
    current = _report(3, health_score=2.0)
    cfg = GateConfig(
        health_low_gate_enabled=True,
        health_low_absolute_score_halt=True,
        health_low_score_drop_threshold=2.0,
    )
    triggered, _ = check_health_low_single_gate(current, cfg, previous_report=None)
    assert not triggered


# ---------------------------------------------------------------------------
# Backward compatibility
# ---------------------------------------------------------------------------


def test_legacy_p1_halt_still_triggers_on_any_p1() -> None:
    report = _report(3, p1_count=1)
    cfg = GateConfig(
        health_low_gate_enabled=True,
        health_low_p1_halt=True,
    )
    triggered, _ = check_health_low_single_gate(report, cfg)
    assert triggered


def test_legacy_absolute_score_halt_still_triggers() -> None:
    report = _report(3, health_score=2.0)
    cfg = GateConfig(
        health_low_gate_enabled=True,
        health_low_absolute_score_halt=True,
        health_low_absolute_score_threshold=3.0,
    )
    triggered, _ = check_health_low_single_gate(report, cfg)
    assert triggered


# ---------------------------------------------------------------------------
# Streak audit window
# ---------------------------------------------------------------------------


def test_streak_audit_window_triggers_when_sum_exceeds_limit() -> None:
    recent = [
        {"chapter_number": 1, "continuity_health_severity": {"P1": 100, "P2": 0}},
        {"chapter_number": 2, "continuity_health_severity": None},
        {"chapter_number": 3, "continuity_health_severity": {"P1": 100, "P2": 0}},
        {"chapter_number": 4, "continuity_health_severity": None},
        {"chapter_number": 5, "continuity_health_severity": None},
        {"chapter_number": 6, "continuity_health_severity": {"P1": 100, "P2": 0}},
        {"chapter_number": 7, "continuity_health_severity": None},
        {"chapter_number": 8, "continuity_health_severity": None},
        {"chapter_number": 9, "continuity_health_severity": {"P1": 100, "P2": 0}},
    ]
    cfg = GateConfig(
        health_low_gate_enabled=True,
        health_low_streak_halt=True,
        health_low_streak_audit_window=3,
        health_low_streak_p1_limit=250,
    )
    triggered, reasons = check_health_low_streak_gate(recent, cfg)
    assert triggered
    assert "P1_total=300" in reasons[0]


def test_streak_audit_window_not_triggered_when_sum_below_limit() -> None:
    recent = [
        {"chapter_number": 1, "continuity_health_severity": {"P1": 10, "P2": 0}},
        {"chapter_number": 3, "continuity_health_severity": {"P1": 10, "P2": 0}},
        {"chapter_number": 6, "continuity_health_severity": {"P1": 10, "P2": 0}},
    ]
    cfg = GateConfig(
        health_low_gate_enabled=True,
        health_low_streak_halt=True,
        health_low_streak_audit_window=3,
        health_low_streak_p1_limit=250,
    )
    triggered, _ = check_health_low_streak_gate(recent, cfg)
    assert not triggered


def test_streak_audit_window_not_triggered_with_insufficient_audit_points() -> None:
    recent = [
        {"chapter_number": 1, "continuity_health_severity": {"P1": 100, "P2": 0}},
        {"chapter_number": 2, "continuity_health_severity": None},
    ]
    cfg = GateConfig(
        health_low_gate_enabled=True,
        health_low_streak_halt=True,
        health_low_streak_audit_window=3,
        health_low_streak_p1_limit=250,
    )
    triggered, _ = check_health_low_streak_gate(recent, cfg)
    assert not triggered


# ---------------------------------------------------------------------------
# evaluate_all_gates wiring
# ---------------------------------------------------------------------------


def test_evaluate_all_gates_uses_previous_data() -> None:
    previous = _report(3, health_score=8.0)
    current = _report(6, health_score=2.0, p1_count=60)
    cfg = GateConfig(
        gate_mode="enforce",
        health_low_gate_enabled=True,
        health_low_p1_halt=True,
        health_low_p1_min_absolute=50,
        health_low_p1_anomaly_factor=1.5,
        health_low_absolute_score_halt=True,
        health_low_score_drop_threshold=2.0,
    )
    triggered, reasons = evaluate_all_gates(
        health_low_report=current,
        context_metrics={"context_emergency": False},
        chapter_result={"success": True, "settlement_success": True, "summary_success": True},
        recent_results=[],
        config=cfg,
        previous_health_low_report=previous,
        previous_p1_counts=[20, 20, 20],
    )
    assert triggered
    assert any("health_low_p1_halt" in r for r in reasons)
    assert any("health_low_absolute_score_halt" in r for r in reasons)
