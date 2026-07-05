"""Task 166b: approved re-plan proposal application tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from songyan.db.migrations import _EXPECTED_TABLES
from songyan.db.narrative_repo import NarrativeRepository
from songyan.db.replan_repo import ReplanProposalRepository
from songyan.db.repository import ProjectRepository
from songyan.models import (
    ArcPlan,
    PlotThread,
    ProjectSetting,
    ReplanAction,
    ReplanProposal,
)
from songyan.services.replan_application import (
    ReplanApplicationError,
    apply_replan_proposal,
    approve_replan_proposal,
    reject_replan_proposal,
)

PID = "proj-166b"


async def _seed_project(project_id: str = PID) -> str:
    await ProjectRepository().create(
        ProjectSetting(title=project_id, genre_id="scifi", protagonist_name="林渊"),
        project_id=project_id,
    )
    return project_id


async def _seed_arc(
    arc_id: str,
    project_id: str = PID,
    *,
    arc_index: int,
    start: int,
    end: int,
    goal: str = "",
    threads_to_open: list[str] | None = None,
    threads_to_resolve: list[str] | None = None,
) -> ArcPlan:
    arc = ArcPlan(
        arc_id=arc_id,
        project_id=project_id,
        arc_index=arc_index,
        start_chapter=start,
        end_chapter=end,
        arc_goal=goal,
        threads_to_open=threads_to_open or [],
        threads_to_resolve=threads_to_resolve or [],
        is_mainline=True,
    )
    await NarrativeRepository().add_arc_plan(arc)
    return arc


async def _seed_thread(
    thread_id: str,
    project_id: str = PID,
    *,
    expected_resolve_arc: int | None = 0,
    status: str = "advanced",
) -> PlotThread:
    thread = PlotThread(
        thread_id=thread_id,
        project_id=project_id,
        title=thread_id,
        is_mainline=True,
        opened_chapter=2,
        expected_resolve_arc=expected_resolve_arc,
        status=status,  # type: ignore[arg-type]
        last_status_chapter=2,
        last_status_version_id="v-open",
    )
    await NarrativeRepository().add_thread(thread)
    return thread


def _action(
    proposal_id: str,
    order: int,
    *,
    target_type: str,
    target_id: str,
    field: str,
    old_value: object,
    new_value: object,
    reason: str = "测试重规划应用",
    evidence: dict | None = None,
) -> ReplanAction:
    return ReplanAction(
        action_id=f"{proposal_id}-a{order:03d}",
        proposal_id=proposal_id,
        action_order=order,
        target_type=target_type,  # type: ignore[arg-type]
        target_id=target_id,
        field=field,
        old_value=old_value,
        new_value=new_value,
        reason=reason,
        evidence=evidence or {},
    )


async def _create_proposal(
    proposal_id: str,
    *,
    actions: list[ReplanAction] | None = None,
    source_end_chapter: int = 5,
) -> ReplanProposal:
    proposal = ReplanProposal(
        proposal_id=proposal_id,
        project_id=PID,
        source_arc_index=0,
        source_start_chapter=1,
        source_end_chapter=source_end_chapter,
        status="draft",
        summary="测试 proposal",
        actions=actions or [],
    )
    await ReplanProposalRepository().create(proposal)
    return proposal


class TestReplanApplicationSchema:
    async def test_planning_constraints_table_registered(self, test_db: Path) -> None:
        assert "planning_constraints" in _EXPECTED_TABLES


class TestReplanProposalStatus:
    async def test_approve_and_reject_status_transitions(self, test_db: Path) -> None:
        await _seed_project()
        await _create_proposal("rp-approve")
        await _create_proposal("rp-reject")

        approved = await approve_replan_proposal("rp-approve", approved_by="reviewer")
        rejected = await reject_replan_proposal("rp-reject", reason="证据不足")

        assert approved.status == "approved"
        assert rejected.status == "rejected"

        with pytest.raises(Exception):
            await reject_replan_proposal("rp-approve", reason="不能拒绝已批准")

    async def test_draft_proposal_cannot_apply(self, test_db: Path) -> None:
        await _seed_project()
        await _create_proposal("rp-draft")

        with pytest.raises(ReplanApplicationError):
            await apply_replan_proposal("rp-draft")


class TestReplanApply:
    async def test_approved_proposal_applies_transactionally(
        self, test_db: Path
    ) -> None:
        await _seed_project()
        await _seed_arc("arc-source", arc_index=0, start=1, end=5, goal="已结束弧")
        await _seed_arc("arc-future", arc_index=1, start=6, end=10, goal="旧未来目标")
        await _seed_thread("thread-main", expected_resolve_arc=0)
        proposal_id = "rp-apply"
        actions = [
            _action(
                proposal_id,
                0,
                target_type="arc_plan",
                target_id="arc-future",
                field="threads_to_open",
                old_value=[],
                new_value=["thread-main"],
            ),
            _action(
                proposal_id,
                1,
                target_type="arc_plan",
                target_id="arc-future",
                field="threads_to_resolve",
                old_value=[],
                new_value=["thread-main"],
            ),
            _action(
                proposal_id,
                2,
                target_type="plot_thread",
                target_id="thread-main",
                field="expected_resolve_arc",
                old_value=0,
                new_value=1,
            ),
            _action(
                proposal_id,
                3,
                target_type="style_constraint",
                target_id="arc-future",
                field="style_constraints",
                old_value=None,
                new_value="下一弧限制模型化句式。",
            ),
        ]
        await _create_proposal(proposal_id, actions=actions)
        await approve_replan_proposal(proposal_id)

        result = await apply_replan_proposal(proposal_id, applied_by="reviewer")

        assert result.applied_action_ids == [action.action_id for action in actions]
        future = await NarrativeRepository().get_arc_by_id("arc-future")
        thread = await NarrativeRepository().get_thread("thread-main")
        applied = await ReplanProposalRepository().get(proposal_id)
        constraints = await ReplanProposalRepository().list_planning_constraints(PID)

        assert future is not None
        assert future.threads_to_open == ["thread-main"]
        assert future.threads_to_resolve == ["thread-main"]
        assert thread is not None
        assert thread.expected_resolve_arc == 1
        assert applied is not None
        assert applied.status == "applied"
        assert len(constraints) == 1
        assert constraints[0].content == "下一弧限制模型化句式。"

        with pytest.raises(ReplanApplicationError):
            await apply_replan_proposal(proposal_id)

    async def test_rejected_proposal_does_not_modify_planning(
        self, test_db: Path
    ) -> None:
        await _seed_project()
        await _seed_arc("arc-source", arc_index=0, start=1, end=5, goal="已结束弧")
        await _seed_arc("arc-future", arc_index=1, start=6, end=10, goal="旧目标")
        proposal_id = "rp-rejected-noop"
        await _create_proposal(
            proposal_id,
            actions=[
                _action(
                    proposal_id,
                    0,
                    target_type="arc_plan",
                    target_id="arc-future",
                    field="arc_goal",
                    old_value="旧目标",
                    new_value="新目标",
                )
            ],
        )

        await reject_replan_proposal(proposal_id, reason="人工拒绝")
        with pytest.raises(ReplanApplicationError):
            await apply_replan_proposal(proposal_id)

        arc = await NarrativeRepository().get_arc_by_id("arc-future")
        assert arc is not None
        assert arc.arc_goal == "旧目标"

    async def test_action_failure_rolls_back_all_changes(self, test_db: Path) -> None:
        await _seed_project()
        await _seed_arc("arc-source", arc_index=0, start=1, end=5, goal="已结束弧")
        await _seed_arc("arc-future", arc_index=1, start=6, end=10, goal="旧目标")
        proposal_id = "rp-rollback"
        await _create_proposal(
            proposal_id,
            actions=[
                _action(
                    proposal_id,
                    0,
                    target_type="arc_plan",
                    target_id="arc-future",
                    field="arc_goal",
                    old_value="旧目标",
                    new_value="新目标",
                ),
                _action(
                    proposal_id,
                    1,
                    target_type="arc_plan",
                    target_id="missing-arc",
                    field="arc_goal",
                    old_value="",
                    new_value="不应写入",
                ),
            ],
        )
        await approve_replan_proposal(proposal_id)

        with pytest.raises(ReplanApplicationError):
            await apply_replan_proposal(proposal_id)

        arc = await NarrativeRepository().get_arc_by_id("arc-future")
        proposal = await ReplanProposalRepository().get(proposal_id)
        constraints = await ReplanProposalRepository().list_planning_constraints(PID)

        assert arc is not None
        assert arc.arc_goal == "旧目标"
        assert proposal is not None
        assert proposal.status == "approved"
        assert constraints == []

    async def test_historical_arc_modification_is_rejected(self, test_db: Path) -> None:
        await _seed_project()
        await _seed_arc("arc-source", arc_index=0, start=1, end=5, goal="旧目标")
        proposal_id = "rp-history"
        await _create_proposal(
            proposal_id,
            actions=[
                _action(
                    proposal_id,
                    0,
                    target_type="arc_plan",
                    target_id="arc-source",
                    field="arc_goal",
                    old_value="旧目标",
                    new_value="不应改历史弧",
                )
            ],
        )
        await approve_replan_proposal(proposal_id)

        with pytest.raises(ReplanApplicationError):
            await apply_replan_proposal(proposal_id)

        arc = await NarrativeRepository().get_arc_by_id("arc-source")
        assert arc is not None
        assert arc.arc_goal == "旧目标"
