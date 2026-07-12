"""Task 125 / Task 127: 候选硬门禁阈值调优单元测试."""

from __future__ import annotations

from songyan.models import ContinuityReport, GateConfig, OrphanedSetting
from songyan.workflows._gates import (
    check_health_low_single_gate,
    check_health_low_streak_gate,
    evaluate_all_gates,
)


def _critical_orphans(count: int) -> list[OrphanedSetting]:
    # Task 171p2: 硬 P1 来源改用 critical orphaned setting（state_mismatch 已降为观测）。
    return [
        OrphanedSetting(
            tracking_id=f"t{i}",
            setting_key=f"k{i}",
            setting_name=f"设定{i}",
            introduced_in_chapter=1,
            last_mentioned_chapter=1,
            chapters_since_mention=5,
            category="critical",
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
        orphaned_settings=_critical_orphans(p1_count),
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
    triggered, _, _ = check_health_low_single_gate(
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
    triggered, reasons, _ = check_health_low_single_gate(
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
    triggered, _, _ = check_health_low_single_gate(report, cfg, previous_p1_counts=[])
    assert not triggered


# ---------------------------------------------------------------------------
# health_score halt gate (Task 127 复合条件)
# ---------------------------------------------------------------------------


def test_score_halt_triggered_on_new_low_and_p1_spike() -> None:
    current = _report(6, health_score=2.0, p1_count=60)
    cfg = GateConfig(
        health_low_gate_enabled=True,
        health_low_score_halt_enabled=True,
        health_low_score_halt_window=3,
        health_low_score_halt_min_p1=20,
        health_low_score_halt_anomaly_factor=1.8,
    )
    triggered, reasons, updated_min = check_health_low_single_gate(
        current,
        cfg,
        previous_p1_counts=[10, 10, 10],
        min_health_score_so_far=8.0,
    )
    assert triggered
    assert "health_low_score_halt" in reasons[0]
    assert updated_min == 2.0


def test_score_halt_not_triggered_when_only_new_low() -> None:
    current = _report(6, health_score=2.0, p1_count=5)
    cfg = GateConfig(
        health_low_gate_enabled=True,
        health_low_score_halt_enabled=True,
        health_low_score_halt_window=3,
        health_low_score_halt_min_p1=20,
        health_low_score_halt_anomaly_factor=1.8,
    )
    triggered, _, updated_min = check_health_low_single_gate(
        current,
        cfg,
        previous_p1_counts=[10, 10, 10],
        min_health_score_so_far=8.0,
    )
    assert not triggered
    assert updated_min == 2.0


def test_score_halt_not_triggered_when_only_p1_spike() -> None:
    current = _report(6, health_score=6.0, p1_count=60)
    cfg = GateConfig(
        health_low_gate_enabled=True,
        health_low_score_halt_enabled=True,
        health_low_score_halt_window=3,
        health_low_score_halt_min_p1=20,
        health_low_score_halt_anomaly_factor=1.8,
    )
    triggered, _, updated_min = check_health_low_single_gate(
        current,
        cfg,
        previous_p1_counts=[10, 10, 10],
        min_health_score_so_far=5.2,
    )
    assert not triggered
    assert updated_min == 5.2


# ---------------------------------------------------------------------------
# Backward compatibility
# ---------------------------------------------------------------------------


def test_legacy_p1_halt_still_triggers_on_any_p1() -> None:
    report = _report(3, p1_count=1)
    cfg = GateConfig(
        health_low_gate_enabled=True,
        health_low_p1_halt=True,
    )
    triggered, _, _ = check_health_low_single_gate(report, cfg)
    assert triggered


def test_score_halt_enabled_triggers_on_composite_condition() -> None:
    report = _report(3, health_score=2.0, p1_count=60)
    cfg = GateConfig(
        health_low_gate_enabled=True,
        health_low_score_halt_enabled=True,
        health_low_score_halt_window=3,
        health_low_score_halt_min_p1=20,
        health_low_score_halt_anomaly_factor=1.8,
    )
    triggered, reasons, _ = check_health_low_single_gate(
        report, cfg, previous_p1_counts=[10], min_health_score_so_far=5.0
    )
    assert triggered
    assert any("health_low_score_halt" in r for r in reasons)


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
        health_low_score_halt_enabled=True,
        health_low_score_halt_window=3,
        health_low_score_halt_min_p1=20,
        health_low_score_halt_anomaly_factor=1.8,
    )
    triggered, reasons, updated_min = evaluate_all_gates(
        health_low_report=current,
        context_metrics={"context_emergency": False},
        chapter_result={"success": True, "settlement_success": True, "summary_success": True},
        recent_results=[],
        config=cfg,
        previous_health_low_report=previous,
        previous_p1_counts=[20, 20, 20],
        min_health_score_so_far=8.0,
    )
    assert triggered
    assert any("health_low_p1_halt" in r for r in reasons)
    assert any("health_low_score_halt" in r for r in reasons)
    assert updated_min == 2.0
