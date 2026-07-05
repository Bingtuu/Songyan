"""Task 169b: adaptive halt workflow integration tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from songyan.exceptions import AutoHaltException
from songyan.models import (
    AdaptiveGateDataPlaneReport,
    AdaptiveHaltDecision,
    AdaptiveHaltPolicy,
    AdaptiveHaltReason,
    GateConfig,
)
from songyan.workflows.phase2_graph import (
    _evaluate_adaptive_halt_for_run,
    run_project_pipeline,
)


def _chapter_success(**kwargs) -> dict:
    chapter_number = kwargs["chapter_number"]
    return {
        "success": True,
        "summary_text": "summary",
        "error": None,
        "final_state": {},
        "final_version_id": f"v-{chapter_number}",
        "budget_used": 0.8,
        "context_emergency": False,
        "quality_gate_passed": True,
        "settlement_success": True,
        "summary_success": True,
    }


def _decision(status: str) -> AdaptiveHaltDecision:
    reasons = [
        AdaptiveHaltReason(
            reason_id="ahr-test-01",
            code="quality_debt_streak",
            severity="halt_candidate",
            signal_domain="quality",
            message="测试自适应 halt",
        )
    ]
    return AdaptiveHaltDecision(
        decision_id=f"ahd-{status}",
        project_id="proj-169b",
        run_id="run-169b",
        chapter_start=1,
        chapter_end=1,
        evaluated_at_chapter=1,
        status=status,  # type: ignore[arg-type]
        reasons=reasons,
    )


@pytest.mark.asyncio
async def test_adaptive_disabled_does_not_call_helper() -> None:
    saved_states: list[object] = []

    async def _capture_state(state) -> None:
        saved_states.append(state.model_copy(deep=True))

    helper = AsyncMock(return_value=None)
    with (
        patch("songyan.workflows.phase2_graph._run_single_chapter", side_effect=_chapter_success),
        patch("songyan.workflows.phase2_graph._save_run_state", side_effect=_capture_state),
        patch("songyan.workflows.phase2_graph._run_db_maintenance", new_callable=AsyncMock),
        patch("songyan.workflows.phase2_graph._evaluate_adaptive_halt_for_run", helper),
    ):
        result = await run_project_pipeline(
            project_id="proj-169b",
            chapter_range=(1, 1),
            auto_confirm=True,
            gate_config=GateConfig(adaptive_halt_enabled=False),
        )

    assert result.final_status == "completed"
    assert helper.await_count == 0
    assert saved_states[-1].status == "completed"


@pytest.mark.asyncio
async def test_observe_halt_candidate_records_without_autohalt() -> None:
    saved_states: list[object] = []

    async def _capture_state(state) -> None:
        saved_states.append(state.model_copy(deep=True))

    helper = AsyncMock(return_value=_decision("halt_candidate"))
    with (
        patch("songyan.workflows.phase2_graph._run_single_chapter", side_effect=_chapter_success),
        patch("songyan.workflows.phase2_graph._save_run_state", side_effect=_capture_state),
        patch("songyan.workflows.phase2_graph._run_db_maintenance", new_callable=AsyncMock),
        patch("songyan.workflows.phase2_graph._evaluate_adaptive_halt_for_run", helper),
    ):
        result = await run_project_pipeline(
            project_id="proj-169b",
            chapter_range=(1, 1),
            auto_confirm=True,
            gate_config=GateConfig(
                adaptive_halt_enabled=True,
                adaptive_halt_action_mode="observe",
            ),
        )

    assert result.final_status == "completed"
    assert helper.await_count == 1
    assert saved_states[-1].status == "completed"


@pytest.mark.asyncio
async def test_enforce_halt_decision_pauses_run() -> None:
    saved_states: list[object] = []

    async def _capture_state(state) -> None:
        saved_states.append(state.model_copy(deep=True))

    helper = AsyncMock(return_value=_decision("halt"))
    with (
        patch("songyan.workflows.phase2_graph._run_single_chapter", side_effect=_chapter_success),
        patch("songyan.workflows.phase2_graph._save_run_state", side_effect=_capture_state),
        patch("songyan.workflows.phase2_graph._run_db_maintenance", new_callable=AsyncMock),
        patch("songyan.workflows.phase2_graph._evaluate_adaptive_halt_for_run", helper),
    ):
        with pytest.raises(AutoHaltException) as exc_info:
            await run_project_pipeline(
                project_id="proj-169b",
                chapter_range=(1, 1),
                auto_confirm=True,
                gate_config=GateConfig(
                    adaptive_halt_enabled=True,
                    adaptive_halt_action_mode="enforce",
                ),
            )

    assert exc_info.value.reason == "adaptive_halt_decision"
    assert exc_info.value.last_chapter == 1
    assert saved_states[-1].status == "paused"
    assert saved_states[-1].completed_chapters == [1]


@pytest.mark.asyncio
async def test_helper_ledger_failure_is_non_blocking() -> None:
    report = AdaptiveGateDataPlaneReport(
        project_id="proj-169b",
        run_id="run-169b",
        chapter_start=1,
        chapter_end=1,
        snapshot_count=0,
    )
    with (
        patch(
            "songyan.workflows.phase2_graph.refresh_adaptive_gate_signal_snapshots",
            new_callable=AsyncMock,
            return_value=1,
        ),
        patch(
            "songyan.workflows.phase2_graph.build_adaptive_gate_data_plane_report",
            new_callable=AsyncMock,
            return_value=report,
        ),
        patch(
            "songyan.workflows.phase2_graph.evaluate_adaptive_halt",
            return_value=_decision("observe"),
        ),
        patch(
            "songyan.workflows.phase2_graph.AdaptiveHaltDecisionRepository"
        ) as repo_cls,
    ):
        repo_cls.return_value.create = AsyncMock(side_effect=RuntimeError("db locked"))
        result = await _evaluate_adaptive_halt_for_run(
            project_id="proj-169b",
            run_id="run-169b",
            chapter_start=1,
            chapter_number=1,
            gate_config=GateConfig(adaptive_halt_enabled=True),
        )

    assert result is None


@pytest.mark.asyncio
async def test_helper_uses_policy_from_gate_config() -> None:
    report = AdaptiveGateDataPlaneReport(
        project_id="proj-169b",
        run_id="run-169b",
        chapter_start=1,
        chapter_end=1,
        snapshot_count=0,
    )
    captured_policy: AdaptiveHaltPolicy | None = None

    def _capture_policy(_report, policy):
        nonlocal captured_policy
        captured_policy = policy
        return _decision("observe")

    with (
        patch(
            "songyan.workflows.phase2_graph.refresh_adaptive_gate_signal_snapshots",
            new_callable=AsyncMock,
            return_value=1,
        ),
        patch(
            "songyan.workflows.phase2_graph.build_adaptive_gate_data_plane_report",
            new_callable=AsyncMock,
            return_value=report,
        ),
        patch(
            "songyan.workflows.phase2_graph.evaluate_adaptive_halt",
            side_effect=_capture_policy,
        ),
        patch(
            "songyan.workflows.phase2_graph.AdaptiveHaltDecisionRepository"
        ) as repo_cls,
    ):
        repo_cls.return_value.create = AsyncMock(return_value=None)
        result = await _evaluate_adaptive_halt_for_run(
            project_id="proj-169b",
            run_id="run-169b",
            chapter_start=1,
            chapter_number=1,
            gate_config=GateConfig(
                adaptive_halt_enabled=True,
                adaptive_halt_action_mode="enforce",
                adaptive_halt_policy_id="custom-policy",
                adaptive_halt_window=7,
                adaptive_halt_warmup_chapters=20,
            ),
        )

    assert result is not None
    assert captured_policy is not None
    assert captured_policy.mode == "enforce"
    assert captured_policy.policy_id == "custom-policy"
    assert captured_policy.warmup_chapters == 20
