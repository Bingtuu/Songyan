"""Task 123: ContextEmergency / health_low 候选硬门禁单元测试."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from songyan.models import ContinuityReport, GateConfig, OrphanedSetting, StateMismatch
from songyan.models.project_run import ProjectRunState
from songyan.workflows._gates import (
    check_context_emergency_single_gate,
    check_health_low_single_gate,
    check_health_low_streak_gate,
    evaluate_all_gates,
)
from songyan.workflows.phase2_graph import _check_auto_halt_window


@pytest.fixture
def gate_config_observe() -> GateConfig:
    return GateConfig(
        gate_mode="observe",
        health_low_gate_enabled=True,
        health_low_p1_halt=True,
        health_low_streak_halt=True,
        health_low_score_halt_enabled=True,
        context_emergency_gate_enabled=True,
        context_emergency_single_halt=True,
        context_emergency_failure_halt=True,
    )


@pytest.fixture
def gate_config_enforce() -> GateConfig:
    return GateConfig(
        gate_mode="enforce",
        health_low_gate_enabled=True,
        health_low_p1_halt=True,
        health_low_streak_halt=True,
        health_low_score_halt_enabled=True,
        context_emergency_gate_enabled=True,
        context_emergency_single_halt=True,
        context_emergency_failure_halt=True,
    )


# ---------------------------------------------------------------------------
# GateConfig defaults
# ---------------------------------------------------------------------------


def test_gate_config_defaults_all_disabled() -> None:
    cfg = GateConfig()
    assert cfg.gate_mode == "observe"
    assert not cfg.health_low_gate_enabled
    assert not cfg.context_emergency_gate_enabled
    assert cfg.is_observe()
    assert not cfg.is_enforce()


# ---------------------------------------------------------------------------
# health_low single-chapter gate
# ---------------------------------------------------------------------------


def test_health_low_p1_triggers_when_enabled() -> None:
    report = ContinuityReport(
        report_id="r1",
        project_id="test-proj-123",
        checked_up_to_chapter=6,
        orphaned_settings=[
            OrphanedSetting(
                tracking_id="s1",
                setting_key="k1",
                setting_name="关键设定",
                introduced_in_chapter=1,
                last_mentioned_chapter=1,
                chapters_since_mention=5,
                category="critical",
            )
        ],
        overall_health_score=5.0,
    )
    cfg = GateConfig(health_low_gate_enabled=True, health_low_p1_halt=True)
    triggered, reasons, _ = check_health_low_single_gate(report, cfg)
    assert triggered
    assert any("health_low_p1_halt" in r for r in reasons)


def test_state_mismatch_does_not_trigger_hard_halt() -> None:
    # Task 171p2: state_mismatch 降为观测——即便存在也不再驱动 run-level 硬 halt。
    report = ContinuityReport(
        report_id="r-sm",
        project_id="test-proj-123",
        checked_up_to_chapter=6,
        state_mismatches=[
            StateMismatch(
                character_id="c1",
                field="emotional_state",
                chapter_a=1,
                value_a="平静",
                chapter_b=2,
                value_b="愤怒",
                issue="演进",
            )
            for _ in range(11)
        ],
        overall_health_score=3.0,
    )
    cfg = GateConfig(health_low_gate_enabled=True, health_low_p1_halt=True)
    triggered, reasons, _ = check_health_low_single_gate(report, cfg)
    assert not triggered


def test_health_low_p1_no_trigger_when_disabled() -> None:
    report = ContinuityReport(
        report_id="r1",
        project_id="test-proj-123",
        checked_up_to_chapter=6,
        state_mismatches=[
            StateMismatch(
                character_id="c1",
                field="location",
                chapter_a=1,
                value_a="A",
                chapter_b=2,
                value_b="B",
                issue="矛盾",
            )
        ],
        overall_health_score=5.0,
    )
    cfg = GateConfig()
    triggered, _, _ = check_health_low_single_gate(report, cfg)
    assert not triggered


def test_health_low_score_halt_trigger() -> None:
    report = ContinuityReport(
        report_id="r1",
        project_id="p1",
        checked_up_to_chapter=6,
        orphaned_settings=[
            OrphanedSetting(
                tracking_id=f"s{i}",
                setting_key=f"k{i}",
                setting_name=f"设定{i}",
                introduced_in_chapter=1,
                last_mentioned_chapter=1,
                chapters_since_mention=5,
                category="critical",
            )
            for i in range(60)
        ],
        overall_health_score=2.0,
    )
    cfg = GateConfig(
        health_low_gate_enabled=True,
        health_low_score_halt_enabled=True,
        health_low_score_halt_window=3,
        health_low_score_halt_min_p1=20,
        health_low_score_halt_anomaly_factor=1.8,
    )
    triggered, reasons, _ = check_health_low_single_gate(
        report,
        cfg,
        previous_p1_counts=[10, 10, 10],
        min_health_score_so_far=5.0,
    )
    assert triggered
    assert any("health_low_score_halt" in r for r in reasons)


def test_health_low_no_p1_no_trigger() -> None:
    report = ContinuityReport(
        report_id="r1",
        project_id="p1",
        checked_up_to_chapter=6,
        orphaned_settings=[
            OrphanedSetting(
                tracking_id="s1",
                setting_key="k1",
                setting_name="name",
                introduced_in_chapter=1,
                last_mentioned_chapter=2,
                chapters_since_mention=4,
                category="background",
            )
        ],
        overall_health_score=6.0,
    )
    cfg = GateConfig(health_low_gate_enabled=True, health_low_p1_halt=True)
    triggered, _, _ = check_health_low_single_gate(report, cfg)
    assert not triggered


# ---------------------------------------------------------------------------
# health_low streak gate
# ---------------------------------------------------------------------------


def test_health_low_streak_p1_triggers() -> None:
    recent = [
        {"chapter_number": 1, "continuity_health_severity": {"P1": 1, "P2": 0, "P3": 0}},
        {"chapter_number": 2, "continuity_health_severity": {"P1": 0, "P2": 0, "P3": 1}},
        {"chapter_number": 3, "continuity_health_severity": {"P1": 1, "P2": 0, "P3": 0}},
    ]
    cfg = GateConfig(
        health_low_gate_enabled=True,
        health_low_streak_halt=True,
        health_low_streak_window=3,
        health_low_streak_p1_limit=1,
    )
    triggered, reasons = check_health_low_streak_gate(recent, cfg)
    assert triggered
    assert any("health_low_streak_halt" in r for r in reasons)


def test_health_low_streak_p2_triggers() -> None:
    recent = [
        {"chapter_number": 1, "continuity_health_severity": {"P1": 0, "P2": 1, "P3": 0}},
        {"chapter_number": 2, "continuity_health_severity": {"P1": 0, "P2": 1, "P3": 0}},
        {"chapter_number": 3, "continuity_health_severity": {"P1": 0, "P2": 0, "P3": 0}},
    ]
    cfg = GateConfig(
        health_low_gate_enabled=True,
        health_low_streak_halt=True,
        health_low_streak_window=3,
        health_low_streak_p1_limit=1,
        health_low_streak_p2_limit=2,
    )
    triggered, reasons = check_health_low_streak_gate(recent, cfg)
    assert triggered
    assert any("P2_total=2" in r for r in reasons)


def test_health_low_streak_no_trigger_when_disabled() -> None:
    recent = [
        {"chapter_number": 1, "continuity_health_severity": {"P1": 1, "P2": 0, "P3": 0}},
        {"chapter_number": 2, "continuity_health_severity": {"P1": 1, "P2": 0, "P3": 0}},
        {"chapter_number": 3, "continuity_health_severity": {"P1": 1, "P2": 0, "P3": 0}},
    ]
    cfg = GateConfig()
    triggered, _ = check_health_low_streak_gate(recent, cfg)
    assert not triggered


def test_health_low_streak_insufficient_window() -> None:
    recent = [
        {"chapter_number": 1, "continuity_health_severity": {"P1": 1, "P2": 0, "P3": 0}},
    ]
    cfg = GateConfig(
        health_low_gate_enabled=True,
        health_low_streak_halt=True,
        health_low_streak_window=3,
    )
    triggered, _ = check_health_low_streak_gate(recent, cfg)
    # 函数本身不检查长度；窗口内 P1=1 达到 limit=1，会触发
    assert triggered


# ---------------------------------------------------------------------------
# ContextEmergency single-chapter gate
# ---------------------------------------------------------------------------


def test_context_emergency_budget_ratio_triggers() -> None:
    ctx_metrics = {"context_emergency": True, "budget_used_before_emergency": 1.35}
    chapter_result = {
        "success": True,
        "settlement_success": True,
        "summary_success": True,
    }
    cfg = GateConfig(
        context_emergency_gate_enabled=True,
        context_emergency_single_halt=True,
        context_emergency_budget_ratio_threshold=1.3,
    )
    triggered, reasons = check_context_emergency_single_gate(ctx_metrics, chapter_result, cfg)
    assert triggered
    assert any("context_emergency_budget_ratio_halt" in r for r in reasons)


def test_context_emergency_failure_halt_triggers() -> None:
    ctx_metrics = {"context_emergency": True}
    chapter_result = {
        "success": True,
        "settlement_success": False,
        "summary_success": True,
    }
    cfg = GateConfig(
        context_emergency_gate_enabled=True,
        context_emergency_failure_halt=True,
    )
    triggered, reasons = check_context_emergency_single_gate(ctx_metrics, chapter_result, cfg)
    assert triggered
    assert any("settlement_success=False" in r for r in reasons)


def test_context_emergency_no_trigger_when_disabled() -> None:
    ctx_metrics = {"context_emergency": True, "budget_used_before_emergency": 1.5}
    chapter_result = {"success": True}
    cfg = GateConfig()
    triggered, _ = check_context_emergency_single_gate(ctx_metrics, chapter_result, cfg)
    assert not triggered


# ---------------------------------------------------------------------------
# evaluate_all_gates
# ---------------------------------------------------------------------------


def test_evaluate_all_gates_combines_reasons() -> None:
    report = ContinuityReport(
        report_id="r1",
        project_id="p1",
        checked_up_to_chapter=6,
        orphaned_settings=[
            OrphanedSetting(
                tracking_id="s1",
                setting_key="k1",
                setting_name="关键设定",
                introduced_in_chapter=1,
                last_mentioned_chapter=1,
                chapters_since_mention=5,
                category="critical",
            )
        ],
        overall_health_score=2.0,
    )
    ctx_metrics = {"context_emergency": True, "budget_used_before_emergency": 1.35}
    chapter_result = {"success": True, "settlement_success": True, "summary_success": True}
    cfg = GateConfig(
        health_low_gate_enabled=True,
        health_low_p1_halt=True,
        health_low_score_halt_enabled=True,
        context_emergency_gate_enabled=True,
        context_emergency_single_halt=True,
    )
    triggered, reasons, _ = evaluate_all_gates(
        health_low_report=report,
        context_metrics=ctx_metrics,
        chapter_result=chapter_result,
        recent_results=[],
        config=cfg,
        previous_p1_counts=[],
        min_health_score_so_far=5.0,
    )
    assert triggered
    assert len(reasons) == 2


def test_evaluate_all_gates_no_trigger_with_default_config() -> None:
    report = ContinuityReport(
        report_id="r1",
        project_id="p1",
        checked_up_to_chapter=6,
        state_mismatches=[
            StateMismatch(
                character_id="c1",
                field="location",
                chapter_a=1,
                value_a="A",
                chapter_b=2,
                value_b="B",
                issue="矛盾",
            )
        ],
        overall_health_score=2.0,
    )
    ctx_metrics = {"context_emergency": True, "budget_used_before_emergency": 1.5}
    chapter_result = {"success": True}
    triggered, _, _ = evaluate_all_gates(
        health_low_report=report,
        context_metrics=ctx_metrics,
        chapter_result=chapter_result,
        recent_results=[],
        config=None,
    )
    assert not triggered


# ---------------------------------------------------------------------------
# _check_auto_halt_window integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_auto_halt_window_health_low_streak(test_db) -> None:
    run_state = ProjectRunState(
        run_id="run-1",
        project_id="test-proj-123",
        chapter_range_start=1,
        chapter_range_end=10,
    )
    recent = [
        {"chapter_number": 1, "quality_gate_passed": True, "context_emergency": False,
         "settlement_success": True, "summary_success": True,
         "continuity_health_severity": {"P1": 1, "P2": 0, "P3": 0},
         "gate_triggered": False, "gate_reasons": []},
        {"chapter_number": 2, "quality_gate_passed": True, "context_emergency": False,
         "settlement_success": True, "summary_success": True,
         "continuity_health_severity": {"P1": 0, "P2": 0, "P3": 0},
         "gate_triggered": False, "gate_reasons": []},
        {"chapter_number": 3, "quality_gate_passed": True, "context_emergency": False,
         "settlement_success": True, "summary_success": True,
         "continuity_health_severity": {"P1": 1, "P2": 0, "P3": 0},
         "gate_triggered": False, "gate_reasons": []},
    ]
    cfg = GateConfig(
        health_low_gate_enabled=True,
        health_low_streak_halt=True,
        health_low_streak_window=3,
        health_low_streak_p1_limit=1,
    )
    with patch("songyan.workflows.phase2_graph._pause_run_for_auto_halt"):
        with pytest.raises(Exception) as exc_info:
            await _check_auto_halt_window(
                run_state, recent, [], [], "", run_id="run-1", chapter_number=3, gate_config=cfg
            )
    assert "health_low_streak_halt" in str(exc_info.value)


@pytest.mark.asyncio
async def test_check_auto_halt_window_no_health_low_when_disabled() -> None:
    run_state = ProjectRunState(
        run_id="run-1",
        project_id="p1",
        chapter_range_start=1,
        chapter_range_end=10,
    )
    recent = [
        {"chapter_number": 1, "quality_gate_passed": True, "context_emergency": False,
         "settlement_success": True, "summary_success": True,
         "continuity_health_severity": {"P1": 1, "P2": 0, "P3": 0},
         "gate_triggered": False, "gate_reasons": []},
        {"chapter_number": 2, "quality_gate_passed": True, "context_emergency": False,
         "settlement_success": True, "summary_success": True,
         "continuity_health_severity": {"P1": 0, "P2": 0, "P3": 0},
         "gate_triggered": False, "gate_reasons": []},
        {"chapter_number": 3, "quality_gate_passed": True, "context_emergency": False,
         "settlement_success": True, "summary_success": True,
         "continuity_health_severity": {"P1": 1, "P2": 0, "P3": 0},
         "gate_triggered": False, "gate_reasons": []},
    ]
    cfg = GateConfig()
    # 不应抛异常
    await _check_auto_halt_window(
        run_state, recent, [], [], "", run_id="run-1", chapter_number=3, gate_config=cfg
    )
    assert run_state.status == "running"
