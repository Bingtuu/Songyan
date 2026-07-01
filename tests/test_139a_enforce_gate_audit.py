"""Task 139a: Enforce 门禁配置最终审计单测.

覆盖关键场景:
- 开局期 Ch1-Ch3 单章 QG false 不触发 quality_gate_fail_streak;
- 正常质量爬坡期（health_score 8.5+ / P1=0）不触发任何 health_low gate;
- 长窗口 stability（health_score 8.5+ / P1=0 / 无 ContextEmergency）不触发任何 gate.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from songyan.models import ContinuityReport, GateConfig
from songyan.models.project_run import ProjectRunState
from songyan.workflows._gates import evaluate_all_gates
from songyan.workflows.phase2_graph import _check_auto_halt_window


@pytest.fixture
def enforce_config() -> GateConfig:
    """enforce 模式完整配置."""
    return GateConfig.for_mode("enforce")


def _chapter(
    number: int,
    *,
    success: bool = True,
    qg: bool = True,
    emergency: bool = False,
    settlement: bool = True,
    summary: bool = True,
    severity: dict | None = None,
) -> dict:
    """构造 _check_auto_halt_window 所需的章节结果字典."""
    result: dict = {
        "chapter_number": number,
        "success": success,
        "quality_gate_passed": qg,
        "context_emergency": emergency,
        "settlement_success": settlement,
        "summary_success": summary,
    }
    if severity is not None:
        result["continuity_health_severity"] = severity
    return result


# ---------------------------------------------------------------------------
# 1. 开局期 QG false 不触发 quality_gate_fail_streak
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_opening_qg_false_single_chapter_no_streak(enforce_config: GateConfig) -> None:
    """Ch1-Ch3 仅单章 QG false，不应触发 quality_gate_fail_streak."""
    run_state = ProjectRunState(
        run_id="run-139a-1",
        project_id="proj-139a",
        chapter_range_start=1,
        chapter_range_end=10,
    )
    recent = [
        _chapter(1, qg=True),
        _chapter(2, qg=False),
        _chapter(3, qg=True),
    ]
    # _check_auto_halt_window 是 async 且不返回值的；无异常即通过
    with patch("songyan.workflows.phase2_graph._pause_run_for_auto_halt"):
        await _check_auto_halt_window(
            run_state, recent, [], [], "", run_id="run-139a-1",
            chapter_number=3, gate_config=enforce_config
        )
    assert run_state.status == "running"


@pytest.mark.asyncio
async def test_opening_two_qg_fails_no_streak(enforce_config: GateConfig) -> None:
    """Ch1-Ch3 仅两章 QG false，仍不达连续 3 章阈值."""
    run_state = ProjectRunState(
        run_id="run-139a-2",
        project_id="proj-139a",
        chapter_range_start=1,
        chapter_range_end=10,
    )
    recent = [
        _chapter(1, qg=False),
        _chapter(2, qg=False),
        _chapter(3, qg=True),
    ]
    with patch("songyan.workflows.phase2_graph._pause_run_for_auto_halt"):
        await _check_auto_halt_window(
            run_state, recent, [], [], "", run_id="run-139a-2",
            chapter_number=3, gate_config=enforce_config
        )
    assert run_state.status == "running"


@pytest.mark.asyncio
async def test_opening_three_qg_fails_trigger_streak(enforce_config: GateConfig) -> None:
    """Ch1-Ch3 连续 3 章 QG false，应触发 quality_gate_fail_streak（正例）."""
    run_state = ProjectRunState(
        run_id="run-139a-3",
        project_id="proj-139a",
        chapter_range_start=1,
        chapter_range_end=10,
    )
    recent = [
        _chapter(1, success=False, qg=False),
        _chapter(2, success=False, qg=False),
        _chapter(3, success=False, qg=False),
    ]
    with patch("songyan.workflows.phase2_graph._pause_run_for_auto_halt"):
        with pytest.raises(Exception) as exc_info:
            await _check_auto_halt_window(
                run_state, recent, [], [], "", run_id="run-139a-3",
                chapter_number=3, gate_config=enforce_config
            )
    assert exc_info.value.reason == "quality_gate_fail_streak"


# ---------------------------------------------------------------------------
# 2. 正常质量爬坡期不触发 health_low gate
# ---------------------------------------------------------------------------


def test_quality_ramp_no_health_low_gate(enforce_config: GateConfig) -> None:
    """health_score 8.5+ 且 P1=0/P2=0，不应触发任何 health_low gate."""
    report = ContinuityReport(
        report_id="rpt-ramp",
        project_id="proj-139a",
        checked_up_to_chapter=15,
        overall_health_score=8.7,
    )
    chapter_result = {
        "success": True,
        "quality_gate_passed": True,
        "settlement_success": True,
        "summary_success": True,
    }
    triggered, reasons, _ = evaluate_all_gates(
        health_low_report=report,
        context_metrics={"context_emergency": False},
        chapter_result=chapter_result,
        recent_results=[],
        config=enforce_config,
        previous_p1_counts=[0, 0, 0],
        min_health_score_so_far=9.0,
    )
    assert not triggered
    assert reasons == []


@pytest.mark.asyncio
async def test_quality_ramp_no_streak_gate(enforce_config: GateConfig) -> None:
    """连续审计点 health_score 8.5+ 且 P1=0，不触发 streak gate."""
    run_state = ProjectRunState(
        run_id="run-139a-ramp",
        project_id="proj-139a",
        chapter_range_start=1,
        chapter_range_end=20,
    )
    recent = [
        _chapter(13, severity={"P1": 0, "P2": 0, "P3": 12}),
        _chapter(14, severity={"P1": 0, "P2": 0, "P3": 10}),
        _chapter(15, severity={"P1": 0, "P2": 0, "P3": 8}),
    ]
    with patch("songyan.workflows.phase2_graph._pause_run_for_auto_halt"):
        await _check_auto_halt_window(
            run_state, recent, [], [], "", run_id="run-139a-ramp",
            chapter_number=15, gate_config=enforce_config
        )
    assert run_state.status == "running"


# ---------------------------------------------------------------------------
# 3. 长窗口 stability 不触发任何 gate
# ---------------------------------------------------------------------------


def test_long_window_stability_no_gate(enforce_config: GateConfig) -> None:
    """模拟 Ch30 / Ch50 长窗口检查点：health 8.5+、P1=0、无 CE，gate 全静默."""
    report = ContinuityReport(
        report_id="rpt-long",
        project_id="proj-139a",
        checked_up_to_chapter=50,
        overall_health_score=8.8,
    )
    recent_results = [
        _chapter(48, severity={"P1": 0, "P2": 0, "P3": 5}),
        _chapter(49, severity={"P1": 0, "P2": 0, "P3": 6}),
    ]
    chapter_result = {
        "success": True,
        "quality_gate_passed": True,
        "settlement_success": True,
        "summary_success": True,
    }
    triggered, reasons, _ = evaluate_all_gates(
        health_low_report=report,
        context_metrics={"context_emergency": False},
        chapter_result=chapter_result,
        recent_results=recent_results,
        config=enforce_config,
        previous_p1_counts=[0, 0, 0, 0, 0],
        min_health_score_so_far=8.7,
    )
    assert not triggered
    assert reasons == []


@pytest.mark.asyncio
async def test_long_window_no_degraded_ce_streak(enforce_config: GateConfig) -> None:
    """连续 3 章 ContextEmergency 但全部成功完成，不触发 degraded streak."""
    run_state = ProjectRunState(
        run_id="run-139a-ce",
        project_id="proj-139a",
        chapter_range_start=1,
        chapter_range_end=100,
    )
    recent = [
        _chapter(48, emergency=True),
        _chapter(49, emergency=True),
        _chapter(50, emergency=True),
    ]
    with patch("songyan.workflows.phase2_graph._pause_run_for_auto_halt"):
        await _check_auto_halt_window(
            run_state, recent, [], [], "", run_id="run-139a-ce",
            chapter_number=50, gate_config=enforce_config
        )
    assert run_state.status == "running"


@pytest.mark.asyncio
async def test_long_window_degraded_ce_streak_triggers(enforce_config: GateConfig) -> None:
    """连续 3 章 ContextEmergency 且伴随 settlement 失败，应触发 degraded streak（正例）."""
    run_state = ProjectRunState(
        run_id="run-139a-ce-bad",
        project_id="proj-139a",
        chapter_range_start=1,
        chapter_range_end=100,
    )
    recent = [
        _chapter(48, emergency=True, settlement=False),
        _chapter(49, emergency=True, settlement=False),
        _chapter(50, emergency=True, settlement=False),
    ]
    with patch("songyan.workflows.phase2_graph._pause_run_for_auto_halt"):
        with pytest.raises(Exception) as exc_info:
            await _check_auto_halt_window(
                run_state, recent, [], [], "", run_id="run-139a-ce-bad",
                chapter_number=50, gate_config=enforce_config
            )
    assert exc_info.value.reason == "context_emergency_degraded_streak"
