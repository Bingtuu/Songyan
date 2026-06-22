"""Tests for Task 105: Ch51-Ch100 streaming validation (report generator + circuit breaker)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from songyan.evals.streaming_report import (
    _compute_word_count_ratio,
    generate_report,
    read_run_logs,
    run_decision_gate_dg1,
    run_decision_gate_dg2,
    write_report,
)
from songyan.exceptions import AutoHaltException
from songyan.models.run_log import ChapterRunLog

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_log(
    chapter_number: int = 1,
    success: bool = True,
    budget_used: float | None = 0.8,
    character_states_loaded: int | None = 5,
    soft_refs_loaded: int | None = 3,
    context_emergency: bool = False,
    quality_gate_passed: bool | None = True,
    settlement_success: bool = True,
    settlement_needs_human_review: bool = False,
    summary_success: bool | None = True,
    revision_rounds: int = 0,
    word_count: int = 3000,
    context_pressure: dict | None = None,
    error: str | None = None,
    error_stage: str | None = None,
) -> ChapterRunLog:
    return ChapterRunLog(
        log_id=f"log-{chapter_number}",
        project_id="p-1",
        chapter_number=chapter_number,
        started_at=datetime(2024, 1, 1, 12, 0, 0),
        finished_at=datetime(2024, 1, 1, 12, 1, 0),
        success=success,
        error=error,
        error_stage=error_stage,
        budget_used=budget_used,
        character_states_loaded=character_states_loaded,
        soft_refs_loaded=soft_refs_loaded,
        context_emergency=context_emergency,
        quality_gate_passed=quality_gate_passed,
        settlement_success=settlement_success,
        settlement_needs_human_review=settlement_needs_human_review,
        summary_success=summary_success,
        revision_rounds=revision_rounds,
        word_count=word_count,
        context_pressure=context_pressure or {},
    )


# ---------------------------------------------------------------------------
# _compute_word_count_ratio
# ---------------------------------------------------------------------------


def test_compute_word_count_ratio_with_target() -> None:
    log = _make_log(word_count=2400, context_pressure={"word_count_target": 3000})
    assert _compute_word_count_ratio(log) == 0.8


def test_compute_word_count_ratio_no_target() -> None:
    log = _make_log(word_count=2400, context_pressure={})
    assert _compute_word_count_ratio(log) is None


def test_compute_word_count_ratio_zero_word_count() -> None:
    log = _make_log(word_count=0, context_pressure={"word_count_target": 3000})
    assert _compute_word_count_ratio(log) is None


# ---------------------------------------------------------------------------
# generate_report
# ---------------------------------------------------------------------------


def test_generate_report_empty() -> None:
    report = generate_report([])
    assert "无运行日志" in report


def test_generate_report_all_pass() -> None:
    logs = [
        _make_log(chapter_number=1, budget_used=0.8, quality_gate_passed=True),
        _make_log(chapter_number=2, budget_used=0.9, quality_gate_passed=True),
        _make_log(chapter_number=3, budget_used=0.85, quality_gate_passed=True),
    ]
    report = generate_report(logs)
    assert "**达标率**: 100.0%" in report
    assert "**budget_used 均值**: 0.850" in report
    assert "✅ 通过" in report


def test_generate_report_some_failures() -> None:
    logs = [
        _make_log(chapter_number=1, budget_used=0.8, quality_gate_passed=True),
        _make_log(chapter_number=2, budget_used=1.1, quality_gate_passed=False, success=False),
        _make_log(chapter_number=3, budget_used=0.85, quality_gate_passed=True),
    ]
    report = generate_report(logs)
    assert "**达标率**: 66.7%" in report
    assert "**成功**: 2 | **失败**: 1" in report


def test_generate_report_with_emergency() -> None:
    logs = [
        _make_log(chapter_number=1, context_emergency=True),
        _make_log(chapter_number=2, context_emergency=False),
        _make_log(chapter_number=3, context_emergency=False),
    ]
    report = generate_report(logs)
    assert "**context_emergency 次数**: 1" in report


def test_generate_report_word_count_ratios() -> None:
    logs = [
        _make_log(chapter_number=1, word_count=2400, context_pressure={"word_count_target": 3000}),
        _make_log(chapter_number=2, word_count=4000, context_pressure={"word_count_target": 3000}),
        _make_log(chapter_number=3, word_count=3100, context_pressure={"word_count_target": 3000}),
    ]
    report = generate_report(logs)
    assert "**字数不足率 (<0.80x)**: 0.0%" in report
    assert "**字数超标率 (>1.30x)**: 33.3%" in report


def test_generate_report_revision_stats() -> None:
    logs = [
        _make_log(chapter_number=1, revision_rounds=0),
        _make_log(chapter_number=2, revision_rounds=1),
        _make_log(chapter_number=3, revision_rounds=2),
    ]
    report = generate_report(logs)
    assert "**平均 revision 轮数**: 1.0" in report


def test_generate_report_dg1_fail_reason() -> None:
    logs = [
        _make_log(chapter_number=i, budget_used=1.2, quality_gate_passed=False, success=False)
        for i in range(1, 11)
    ]
    report = generate_report(logs)
    assert "❌ 未通过" in report
    assert "未达标项" in report


def test_generate_report_handles_missing_budget_and_zero() -> None:
    logs = [
        _make_log(chapter_number=101, budget_used=None),
        _make_log(chapter_number=102, budget_used=0.0),
    ]
    report = generate_report(logs, chapter_range=(101, 102))
    assert "| Ch101 | Y | - |" in report
    assert "| Ch102 | Y | 0.000 |" in report


def test_generate_report_dg2_lists_blocking_details() -> None:
    logs = [
        _make_log(chapter_number=101, budget_used=0.8),
        _make_log(chapter_number=102, budget_used=1.2),
        _make_log(
            chapter_number=103,
            success=True,
            budget_used=0.9,
            settlement_success=False,
            settlement_needs_human_review=True,
        ),
        _make_log(chapter_number=104, budget_used=0.9, summary_success=False),
        _make_log(
            chapter_number=105,
            success=False,
            budget_used=None,
            quality_gate_passed=False,
            error_stage="writing",
            error="timeout",
        ),
    ]
    report = generate_report(logs, chapter_range=(101, 105))
    assert "**budget 超限章节**: Ch102" in report
    assert "**settlement validation failed 章节**: Ch103" in report
    assert "**accepted 后缺 summary 章节**: Ch104" in report
    assert "**失败章节**: Ch105" in report
    assert "Ch105: writing / timeout" in report


# ---------------------------------------------------------------------------
# run_decision_gate_dg1
# ---------------------------------------------------------------------------


def test_dg1_all_pass() -> None:
    dg = run_decision_gate_dg1(
        pass_rate=0.8,
        avg_budget=0.9,
        over_budget_ratio=0.05,
        under_ratio=0.03,
        over_ratio=0.1,
        avg_rev=1.2,
        emergency_count=3,
        total=10,
    )
    assert dg.passed is True
    assert "推进 V5.1" in dg.reason


def test_dg1_pass_rate_fail() -> None:
    dg = run_decision_gate_dg1(
        pass_rate=0.7,
        avg_budget=0.9,
        over_budget_ratio=0.05,
        under_ratio=0.03,
        over_ratio=0.1,
        avg_rev=1.2,
        emergency_count=3,
        total=10,
    )
    assert dg.passed is False
    assert "达标率 >= 75%" in dg.reason


def test_dg1_budget_fail() -> None:
    dg = run_decision_gate_dg1(
        pass_rate=0.8,
        avg_budget=0.96,
        over_budget_ratio=0.05,
        under_ratio=0.03,
        over_ratio=0.1,
        avg_rev=1.2,
        emergency_count=3,
        total=10,
    )
    assert dg.passed is False
    assert "budget_used 均值 <= 0.95" in dg.reason


def test_dg1_emergency_fail() -> None:
    dg = run_decision_gate_dg1(
        pass_rate=0.8,
        avg_budget=0.9,
        over_budget_ratio=0.05,
        under_ratio=0.03,
        over_ratio=0.1,
        avg_rev=1.2,
        emergency_count=6,
        total=10,
    )
    assert dg.passed is False
    assert "context_emergency 次数 <= 5" in dg.reason


# ---------------------------------------------------------------------------
# run_decision_gate_dg2
# ---------------------------------------------------------------------------


def test_dg2_all_pass() -> None:
    dg = run_decision_gate_dg2(pass_rate=0.75, avg_budget=0.95, total=10)
    assert dg.passed is True
    assert "DG-2 核心指标达标" in dg.reason


def test_dg2_pass_rate_fail() -> None:
    dg = run_decision_gate_dg2(pass_rate=0.65, avg_budget=0.95, total=10)
    assert dg.passed is False
    assert "达标率 >= 70%" in dg.reason


def test_dg2_budget_fail() -> None:
    dg = run_decision_gate_dg2(pass_rate=0.75, avg_budget=1.05, total=10)
    assert dg.passed is False
    assert "budget_used 均值 <= 1.00" in dg.reason


def test_dg2_fails_single_chapter_over_budget() -> None:
    logs = [
        _make_log(chapter_number=101, budget_used=0.8),
        _make_log(chapter_number=102, budget_used=1.2),
        _make_log(chapter_number=103, budget_used=0.8),
    ]
    dg = run_decision_gate_dg2(
        pass_rate=1.0,
        avg_budget=sum(log.budget_used or 0 for log in logs) / len(logs),
        total=len(logs),
        logs=logs,
    )
    assert dg.passed is False
    assert dg.status == "failed"
    assert dg.metrics["over_budget_chapters"] == [102]
    assert "每章 budget_used <= 1.00 且有记录" in dg.reason


def test_dg2_fails_settlement_validation_failure() -> None:
    logs = [
        _make_log(chapter_number=101),
        _make_log(
            chapter_number=102,
            settlement_success=False,
            settlement_needs_human_review=True,
        ),
    ]
    dg = run_decision_gate_dg2(
        pass_rate=1.0,
        avg_budget=0.8,
        total=len(logs),
        logs=logs,
    )
    assert dg.passed is False
    assert dg.metrics["settlement_failed_chapters"] == [102]
    assert "settlement validation failed == 0" in dg.reason


def test_dg2_fails_missing_summary_after_accept() -> None:
    logs = [
        _make_log(chapter_number=101),
        _make_log(chapter_number=102, summary_success=False),
    ]
    dg = run_decision_gate_dg2(
        pass_rate=1.0,
        avg_budget=0.8,
        total=len(logs),
        logs=logs,
    )
    assert dg.passed is False
    assert dg.metrics["missing_summary_chapters"] == [102]
    assert "accepted 后 summary 100% 完整" in dg.reason


def test_dg2_compatible_with_old_logs_missing_new_fields() -> None:
    log = ChapterRunLog(
        log_id="old-log-101",
        project_id="p-1",
        chapter_number=101,
        started_at=datetime(2024, 1, 1, 12, 0, 0),
        finished_at=datetime(2024, 1, 1, 12, 1, 0),
        success=True,
        quality_gate_passed=True,
        budget_used=None,
    )
    report = generate_report([log], chapter_range=(101, 101))
    assert "| Ch101 | Y | - |" in report
    assert "**budget 缺失章节**: Ch101" in report
    assert "❌ 未通过" in report


# ---------------------------------------------------------------------------
# generate_report auto-selects DG-2 for Ch101+
# ---------------------------------------------------------------------------


def test_report_uses_dg2_for_ch101() -> None:
    from datetime import datetime

    log = ChapterRunLog(
        log_id="log-101",
        project_id="p-1",
        chapter_number=101,
        started_at=datetime(2024, 1, 1, 12, 0, 0),
        finished_at=datetime(2024, 1, 1, 12, 1, 0),
        success=True,
        quality_gate_passed=True,
        budget_used=0.9,
        revision_rounds=0,
        context_emergency=False,
        character_states_loaded=5,
        soft_refs_loaded=3,
        summary_success=True,
    )
    report = generate_report([log], chapter_range=(101, 101))
    assert "决策门 DG-2" in report
    assert "✅ 通过" in report


# ---------------------------------------------------------------------------
# read_run_logs / write_report
# ---------------------------------------------------------------------------


def test_read_run_logs_missing_file() -> None:
    logs = read_run_logs("nonexistent-run-id-12345")
    assert logs == []


def test_write_report(tmp_path: Path) -> None:
    out = write_report("# Test Report", "run-001", output_dir=tmp_path)
    assert out.exists()
    assert out.read_text(encoding="utf-8") == "# Test Report"


# ---------------------------------------------------------------------------
# Circuit breaker in run_project_pipeline
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_progress_saved_after_each_success() -> None:
    """每章成功后立即保存 completed_chapters，避免长跑中途异常丢进度."""
    from songyan.workflows.phase2_graph import run_project_pipeline

    async def _fake_run(**kwargs: Any) -> dict[str, Any]:
        chapter_number = kwargs["chapter_number"]
        return {
            "success": True,
            "summary_text": f"s{chapter_number}",
            "error": None,
            "final_state": {"_quality_gate_passed": True},
            "final_version_id": f"v{chapter_number}",
            "budget_used": 0.8,
            "context_emergency": False,
            "quality_gate_passed": True,
        }

    saved_states: list[Any] = []

    async def _capture_state(state: Any) -> None:
        saved_states.append(state.model_copy(deep=True))

    with (
        patch("songyan.workflows.phase2_graph._run_single_chapter", side_effect=_fake_run),
        patch("songyan.workflows.phase2_graph._save_run_state", side_effect=_capture_state),
    ):
        result = await run_project_pipeline(
            project_id="proj-001",
            chapter_range=(1, 2),
            auto_confirm=True,
        )

    assert result.final_status == "completed"
    assert any(state.completed_chapters == [1] for state in saved_states)
    assert any(state.completed_chapters == [1, 2] for state in saved_states)
    assert saved_states[-1].status == "completed"


@pytest.mark.asyncio
async def test_circuit_breaker_quality_gate_3_fails() -> None:
    """连续 3 章 quality_gate_passed=False 触发熔断并保存暂停状态."""
    from songyan.workflows.phase2_graph import run_project_pipeline

    async def _fake_run(**kwargs: Any) -> dict[str, Any]:
        return {
            "success": True,
            "summary_text": "s",
            "error": None,
            "final_state": {"_quality_gate_passed": False},
            "final_version_id": "v1",
            "budget_used": 1.1,
            "context_emergency": False,
            "quality_gate_passed": False,
        }

    saved_states: list[Any] = []

    async def _capture_state(state: Any) -> None:
        saved_states.append(state.model_copy(deep=True))

    with (
        patch("songyan.workflows.phase2_graph._run_single_chapter", side_effect=_fake_run),
        patch("songyan.workflows.phase2_graph._save_run_state", side_effect=_capture_state),
    ):
        with pytest.raises(AutoHaltException) as exc_info:
            await run_project_pipeline(
                project_id="proj-001",
                chapter_range=(1, 5),
                auto_confirm=True,
            )

    assert exc_info.value.reason == "quality_gate_fail_streak"
    assert exc_info.value.last_chapter == 3
    assert saved_states[-1].status == "paused"
    assert saved_states[-1].current_chapter == 3
    assert saved_states[-1].completed_chapters == [1, 2, 3]
    assert saved_states[-1].failed_chapters == []
    assert "第3章：s" in saved_states[-1].accumulated_summary


@pytest.mark.asyncio
async def test_circuit_breaker_allows_successful_emergency_3_streak() -> None:
    """连续 3 章 context_emergency=True 但均成功时不熔断."""
    from songyan.workflows.phase2_graph import run_project_pipeline

    async def _fake_run(**kwargs: Any) -> dict[str, Any]:
        return {
            "success": True,
            "summary_text": "s",
            "error": None,
            "final_state": {},
            "final_version_id": "v1",
            "budget_used": 1.2,
            "context_emergency": True,
            "quality_gate_passed": True,
            "settlement_success": True,
            "summary_success": True,
        }

    saved_states: list[Any] = []

    async def _capture_state(state: Any) -> None:
        saved_states.append(state.model_copy(deep=True))

    with (
        patch("songyan.workflows.phase2_graph._run_single_chapter", side_effect=_fake_run),
        patch("songyan.workflows.phase2_graph._save_run_state", side_effect=_capture_state),
    ):
        result = await run_project_pipeline(
            project_id="proj-001",
            chapter_range=(1, 5),
            auto_confirm=True,
        )

    assert result.final_status == "completed"
    assert result.chapters_completed == [1, 2, 3, 4, 5]
    assert saved_states[-1].status == "completed"
    assert saved_states[-1].current_chapter == 5
    assert saved_states[-1].completed_chapters == [1, 2, 3, 4, 5]
    assert saved_states[-1].failed_chapters == []


@pytest.mark.asyncio
async def test_circuit_breaker_skips_none_qg() -> None:
    """quality_gate_passed=None 的章节不计入熔断窗口."""
    from songyan.workflows.phase2_graph import run_project_pipeline

    call_count = 0

    async def _fake_run(**kwargs: Any) -> dict[str, Any]:
        nonlocal call_count
        call_count += 1
        return {
            "success": True,
            "summary_text": "s",
            "error": None,
            "final_state": {},
            "final_version_id": "v1",
            "budget_used": 1.1,
            "context_emergency": False,
            "quality_gate_passed": None,
        }

    with (
        patch("songyan.workflows.phase2_graph._run_single_chapter", side_effect=_fake_run),
        patch("songyan.workflows.phase2_graph._save_run_state", new_callable=AsyncMock),
    ):
        result = await run_project_pipeline(
            project_id="proj-001",
            chapter_range=(1, 5),
            auto_confirm=True,
        )

    assert result.final_status == "completed"
    assert result.chapters_completed == [1, 2, 3, 4, 5]


@pytest.mark.asyncio
async def test_circuit_breaker_2_fails_no_halt() -> None:
    """仅 2 章连续失败不触发熔断."""
    from songyan.workflows.phase2_graph import run_project_pipeline

    call_count = 0

    async def _fake_run(**kwargs: Any) -> dict[str, Any]:
        nonlocal call_count
        call_count += 1
        qg = False if call_count <= 2 else True
        return {
            "success": True,
            "summary_text": "s",
            "error": None,
            "final_state": {"_quality_gate_passed": qg},
            "final_version_id": "v1",
            "budget_used": 1.1,
            "context_emergency": False,
            "quality_gate_passed": qg,
        }

    with (
        patch("songyan.workflows.phase2_graph._run_single_chapter", side_effect=_fake_run),
        patch("songyan.workflows.phase2_graph._save_run_state", new_callable=AsyncMock),
    ):
        result = await run_project_pipeline(
            project_id="proj-001",
            chapter_range=(1, 4),
            auto_confirm=True,
        )

    assert result.final_status == "completed"
    assert result.chapters_completed == [1, 2, 3, 4]


@pytest.mark.asyncio
async def test_circuit_breaker_interleaved_pass() -> None:
    """失败-通过-失败 不触发熔断."""
    from songyan.workflows.phase2_graph import run_project_pipeline

    call_count = 0

    async def _fake_run(**kwargs: Any) -> dict[str, Any]:
        nonlocal call_count
        call_count += 1
        qg = call_count % 2 == 1  # 奇数通过，偶数失败
        return {
            "success": True,
            "summary_text": "s",
            "error": None,
            "final_state": {"_quality_gate_passed": qg},
            "final_version_id": "v1",
            "budget_used": 1.1,
            "context_emergency": False,
            "quality_gate_passed": qg,
        }

    with (
        patch("songyan.workflows.phase2_graph._run_single_chapter", side_effect=_fake_run),
        patch("songyan.workflows.phase2_graph._save_run_state", new_callable=AsyncMock),
    ):
        result = await run_project_pipeline(
            project_id="proj-001",
            chapter_range=(1, 5),
            auto_confirm=True,
        )

    assert result.final_status == "completed"
