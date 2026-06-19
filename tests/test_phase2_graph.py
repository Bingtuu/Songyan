"""Module tests for Phase2 multi-chapter orchestration."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from songyan.models import ProjectRunResult
from songyan.workflows.phase2_graph import run_project_pipeline

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_chapter_state(
    status: str = "done",
    error: str | None = None,
    has_interrupt: bool = False,
    thread_id: str = "thread-1",
) -> dict[str, Any]:
    state: dict[str, Any] = {
        "status": status,
        "error": error,
        "thread_id": thread_id,
    }
    if has_interrupt:
        state["__interrupt__"] = []
    return state


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_project_pipeline_3_chapters_success() -> None:
    """3 章全部成功，验证结果统计."""
    with (
        patch(
            "songyan.workflows.phase2_graph.run_chapter_pipeline",
            new_callable=AsyncMock,
        ) as mock_run_chapter,
        patch(
            "songyan.workflows.phase2_graph._get_previous_summary",
            new_callable=AsyncMock,
            return_value="",
        ),
        patch(
            "songyan.workflows.phase2_graph._get_summary_text",
            new_callable=AsyncMock,
            side_effect=["summary-ch1", "summary-ch2", "summary-ch3"],
        ),
        patch(
            "songyan.workflows.phase2_graph._save_run_state",
            new_callable=AsyncMock,
        ),
        patch(
            "songyan.workflows.phase2_graph.log_chapter_run",
            new_callable=AsyncMock,
        ) as mock_log,
    ):
        mock_run_chapter.return_value = _make_chapter_state(status="done")

        result: ProjectRunResult = await run_project_pipeline(
            project_id="proj-001",
            chapter_range=(1, 3),
            mode_id="webnovel",
            auto_confirm=True,
        )

    assert result.final_status == "completed"
    assert result.chapters_completed == [1, 2, 3]
    assert result.chapters_failed == []
    assert mock_run_chapter.call_count == 3
    assert mock_log.call_count == 3


@pytest.mark.asyncio
async def test_run_project_pipeline_previous_summary_propagation() -> None:
    """验证第 2 章的 previous_summary 来自第 1 章的 summary."""
    calls: list[dict[str, Any]] = []

    async def _fake_run_chapter(**kwargs: Any) -> dict[str, Any]:
        calls.append(kwargs)
        return _make_chapter_state(status="done")

    with (
        patch(
            "songyan.workflows.phase2_graph.run_chapter_pipeline",
            side_effect=_fake_run_chapter,
        ),
        patch(
            "songyan.workflows.phase2_graph._get_previous_summary",
            new_callable=AsyncMock,
            side_effect=["", "summary-ch1", "summary-ch2"],
        ),
        patch(
            "songyan.workflows.phase2_graph._get_summary_text",
            new_callable=AsyncMock,
            side_effect=["summary-ch1", "summary-ch2", "summary-ch3"],
        ),
        patch(
            "songyan.workflows.phase2_graph._save_run_state",
            new_callable=AsyncMock,
        ),
        patch(
            "songyan.workflows.phase2_graph.log_chapter_run",
            new_callable=AsyncMock,
        ),
    ):
        result = await run_project_pipeline(
            project_id="proj-001",
            chapter_range=(1, 3),
            auto_confirm=True,
        )

    assert result.final_status == "completed"
    assert len(calls) == 3
    # 第 1 章：previous_summary = ""
    assert calls[0]["previous_summary"] == ""
    # 第 2 章：previous_summary = "summary-ch1"
    assert calls[1]["previous_summary"] == "summary-ch1"
    # 第 3 章：previous_summary = "summary-ch2"
    assert calls[2]["previous_summary"] == "summary-ch2"


@pytest.mark.asyncio
async def test_run_project_pipeline_chapter_failure_abort() -> None:
    """第 2 章失败，abort 终止整批."""
    call_count = 0

    async def _fake_run_chapter(**kwargs: Any) -> dict[str, Any]:
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            return _make_chapter_state(status="error", error="writer_failed")
        return _make_chapter_state(status="done")

    with (
        patch(
            "songyan.workflows.phase2_graph.run_chapter_pipeline",
            side_effect=_fake_run_chapter,
        ),
        patch(
            "songyan.workflows.phase2_graph._get_previous_summary",
            new_callable=AsyncMock,
            return_value="",
        ),
        patch(
            "songyan.workflows.phase2_graph._get_summary_text",
            new_callable=AsyncMock,
            return_value="summary",
        ),
        patch(
            "songyan.workflows.phase2_graph._save_run_state",
            new_callable=AsyncMock,
        ),
        patch(
            "songyan.workflows.phase2_graph.log_chapter_run",
            new_callable=AsyncMock,
        ),
    ):
        result = await run_project_pipeline(
            project_id="proj-001",
            chapter_range=(1, 3),
            auto_confirm=True,
            on_failure="abort",
        )

    assert result.final_status == "partial"
    assert result.chapters_completed == [1]
    assert result.chapters_failed == [2]
    assert call_count == 2  # 第 1 章成功，第 2 章失败后终止


@pytest.mark.asyncio
async def test_run_project_pipeline_chapter_failure_retry_then_success() -> None:
    """第 2 章首次失败，retry 后成功."""
    call_count = 0

    async def _fake_run_chapter(**kwargs: Any) -> dict[str, Any]:
        nonlocal call_count
        call_count += 1
        # 第 2 章第一次调用失败，第二次成功
        if call_count == 2:
            return _make_chapter_state(status="error", error="temp_error")
        if call_count == 3:
            return _make_chapter_state(status="done")
        return _make_chapter_state(status="done")

    with (
        patch(
            "songyan.workflows.phase2_graph.run_chapter_pipeline",
            side_effect=_fake_run_chapter,
        ),
        patch(
            "songyan.workflows.phase2_graph._get_previous_summary",
            new_callable=AsyncMock,
            return_value="",
        ),
        patch(
            "songyan.workflows.phase2_graph._get_summary_text",
            new_callable=AsyncMock,
            return_value="summary",
        ),
        patch(
            "songyan.workflows.phase2_graph._save_run_state",
            new_callable=AsyncMock,
        ),
        patch(
            "songyan.workflows.phase2_graph.log_chapter_run",
            new_callable=AsyncMock,
        ),
    ):
        result = await run_project_pipeline(
            project_id="proj-001",
            chapter_range=(1, 3),
            auto_confirm=True,
            on_failure="retry",
        )

    # retry 后第 2 章成功，继续第 3 章
    assert result.final_status == "completed"
    assert result.chapters_completed == [1, 2, 3]
    assert result.chapters_failed == []
    assert call_count == 4  # ch1(1), ch2-first(2), ch2-retry(3), ch3(4)


@pytest.mark.asyncio
async def test_run_project_pipeline_auto_confirm_handles_interrupt() -> None:
    """auto_confirm=True 时正确处理 human_confirm 中断."""
    with (
        patch(
            "songyan.workflows.phase2_graph.run_chapter_pipeline",
            new_callable=AsyncMock,
            return_value=_make_chapter_state(
                status="settlement", has_interrupt=True
            ),
        ),
        patch(
            "songyan.workflows.phase2_graph.resume_human_confirm",
            new_callable=AsyncMock,
            return_value=_make_chapter_state(status="done"),
        ),
        patch(
            "songyan.workflows.phase2_graph._get_previous_summary",
            new_callable=AsyncMock,
            return_value="",
        ),
        patch(
            "songyan.workflows.phase2_graph._get_summary_text",
            new_callable=AsyncMock,
            return_value="summary",
        ),
        patch(
            "songyan.workflows.phase2_graph._save_run_state",
            new_callable=AsyncMock,
        ),
        patch(
            "songyan.workflows.phase2_graph.log_chapter_run",
            new_callable=AsyncMock,
        ),
    ):
        result = await run_project_pipeline(
            project_id="proj-001",
            chapter_range=(1, 1),
            auto_confirm=True,
        )

    assert result.final_status == "completed"
    assert result.chapters_completed == [1]


@pytest.mark.asyncio
async def test_run_project_pipeline_invalid_range_start_gt_end() -> None:
    """start > end 时抛出 ValueError."""
    with pytest.raises(ValueError, match="start .* must be <= end"):
        await run_project_pipeline(
            project_id="proj-001",
            chapter_range=(3, 1),
            auto_confirm=True,
        )


@pytest.mark.asyncio
async def test_run_project_pipeline_invalid_range_start_lt_1() -> None:
    """start < 1 时抛出 ValueError."""
    with pytest.raises(ValueError, match="start .* must be >= 1"):
        await run_project_pipeline(
            project_id="proj-001",
            chapter_range=(0, 2),
            auto_confirm=True,
        )


@pytest.mark.asyncio
async def test_run_project_pipeline_auto_confirm_false_rejected() -> None:
    """auto_confirm=False rasies ValueError."""
    with pytest.raises(ValueError, match="auto_confirm=False"):
        await run_project_pipeline(
            project_id="proj-001",
            chapter_range=(1, 2),
            auto_confirm=False,
        )


@pytest.mark.asyncio
async def test_run_project_pipeline_persists_only_latest_summary_entry() -> None:
    """project_runs 持久化只写最近单章摘要，避免全量历史写放大."""

    async def _fake_run(**kwargs: Any) -> dict[str, Any]:
        chapter_number = kwargs["chapter_number"]
        return {
            "success": True,
            "summary_text": f"summary-ch{chapter_number}",
            "error": None,
            "final_state": {},
            "final_version_id": f"v-{chapter_number}",
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
            chapter_range=(1, 4),
            auto_confirm=True,
        )

    assert result.accumulated_summary == (
        "第1章：summary-ch1\n\n"
        "第2章：summary-ch2\n\n"
        "第3章：summary-ch3\n\n"
        "第4章：summary-ch4"
    )
    assert saved_states[-1].accumulated_summary == "第4章：summary-ch4"
    assert all("\n\n" not in state.accumulated_summary for state in saved_states)

# ---------- _run_single_chapter stage tracking -- Task 059 ----------


@pytest.mark.asyncio
async def test_run_single_chapter_pipeline_exception_sets_stage() -> None:
    """_run_single_chapter at pipeline stage sets error_stage to pipeline."""
    from songyan.workflows.phase2_graph import _run_single_chapter

    with (
        patch(
            "songyan.workflows.phase2_graph.run_chapter_pipeline",
            new_callable=AsyncMock,
            side_effect=RuntimeError("crash"),
        ),
        patch(
            "songyan.workflows.phase2_graph.log_chapter_run",
            new_callable=AsyncMock,
        ) as mock_log,
    ):
        result = await _run_single_chapter(
            project_id="p-1",
            chapter_number=1,
            mode_id="webnovel",
            previous_summary="",
            auto_confirm=True,
            on_failure="abort",
        )

    assert result["success"] is False
    mock_log.assert_called_once()
    assert mock_log.call_args.kwargs["error_stage"] == "pipeline"


@pytest.mark.asyncio
async def test_run_single_chapter_human_confirm_exception_sets_stage() -> None:
    """_run_single_chapter at human_confirm stage sets error_stage."""
    from songyan.workflows.phase2_graph import _run_single_chapter

    state_int: dict[str, Any] = {
        "status": "settlement",
        "__interrupt__": [],
        "thread_id": "t-1",
    }

    with (
        patch(
            "songyan.workflows.phase2_graph.run_chapter_pipeline",
            new_callable=AsyncMock,
            return_value=state_int,
        ),
        patch(
            "songyan.workflows.phase2_graph.resume_human_confirm",
            new_callable=AsyncMock,
            side_effect=RuntimeError("resume failed"),
        ),
        patch(
            "songyan.workflows.phase2_graph.log_chapter_run",
            new_callable=AsyncMock,
        ) as mock_log,
    ):
        result = await _run_single_chapter(
            project_id="p-1",
            chapter_number=1,
            mode_id="webnovel",
            previous_summary="",
            auto_confirm=True,
            on_failure="abort",
        )

    assert result["success"] is False
    mock_log.assert_called_once()
    assert mock_log.call_args.kwargs["error_stage"] == "human_confirm"


@pytest.mark.asyncio
async def test_run_single_chapter_success_no_error_stage() -> None:
    """Successful _run_single_chapter has no error_stage."""
    from songyan.workflows.phase2_graph import _run_single_chapter

    with (
        patch(
            "songyan.workflows.phase2_graph.run_chapter_pipeline",
            new_callable=AsyncMock,
            return_value=_make_chapter_state(status="done"),
        ),
        patch(
            "songyan.workflows.phase2_graph._get_summary_text",
            new_callable=AsyncMock,
            return_value="summary",
        ),
        patch("songyan.workflows.phase2_graph._save_run_state", new_callable=AsyncMock),
        patch(
            "songyan.workflows.phase2_graph.log_chapter_run",
            new_callable=AsyncMock,
        ) as mock_log,
    ):
        result = await _run_single_chapter(
            project_id="p-1",
            chapter_number=1,
            mode_id="webnovel",
            previous_summary="",
            auto_confirm=True,
            on_failure="abort",
        )

    assert result["success"] is True
    mock_log.assert_called_once()
    assert mock_log.call_args.kwargs.get("error_stage") is None


@pytest.mark.asyncio
async def test_run_single_chapter_returns_logged_circuit_metrics() -> None:
    """外层熔断使用写入 JSONL 的最终指标，避免与报告口径分叉."""
    from songyan.workflows.phase2_graph import _run_single_chapter

    state = _make_chapter_state(status="done")
    state["_context_metrics"] = {"budget_used": 0.4, "context_emergency": False}
    state["_quality_gate_passed"] = True

    logged = SimpleNamespace(
        budget_used=0.9,
        context_emergency=True,
        quality_gate_passed=False,
    )

    with (
        patch(
            "songyan.workflows.phase2_graph.run_chapter_pipeline",
            new_callable=AsyncMock,
            return_value=state,
        ),
        patch(
            "songyan.workflows.phase2_graph._get_summary_text",
            new_callable=AsyncMock,
            return_value="summary",
        ),
        patch(
            "songyan.workflows.phase2_graph.log_chapter_run",
            new_callable=AsyncMock,
            return_value=logged,
        ),
    ):
        result = await _run_single_chapter(
            project_id="p-1",
            chapter_number=1,
            mode_id="webnovel",
            previous_summary="",
            auto_confirm=True,
            on_failure="abort",
        )

    assert result["budget_used"] == 0.9
    assert result["context_emergency"] is True
    assert result["quality_gate_passed"] is False


@pytest.mark.asyncio
async def test_pipeline_halts_on_logged_context_emergency_streak() -> None:
    """回归真实试跑问题：最终日志指标连续 emergency 时外层必须熔断."""
    from songyan.exceptions import AutoHaltException
    from songyan.workflows.phase2_graph import run_project_pipeline

    async def _fake_run(**kwargs: Any) -> dict[str, Any]:
        return {
            "success": True,
            "summary_text": "summary",
            "error": None,
            "final_state": {},
            "final_version_id": f"v-{kwargs['chapter_number']}",
            "budget_used": 0.8,
            "context_emergency": True,
            "quality_gate_passed": True,
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

    assert exc_info.value.reason == "context_emergency_streak"
    assert exc_info.value.last_chapter == 3
    assert saved_states[-1].status == "paused"
    assert saved_states[-1].completed_chapters == [1, 2, 3]
