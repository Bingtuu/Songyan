"""Application service for approved re-plan proposals (V7 Task 166b)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import structlog

from songyan.db.connection import get_db
from songyan.db.narrative_repo import NarrativeRepository
from songyan.db.replan_repo import ReplanProposalRepository
from songyan.exceptions import SongyanError
from songyan.models import (
    ArcPlan,
    PlanningConstraint,
    PlotThreadStatus,
    ReplanAction,
    ReplanApplicationResult,
    ReplanProposal,
)

logger = structlog.get_logger(__name__)


class ReplanApplicationError(SongyanError):
    """Raised when a proposal cannot be approved, rejected, or applied."""


async def approve_replan_proposal(
    proposal_id: str,
    *,
    approved_by: str = "human",
    repo: ReplanProposalRepository | None = None,
) -> ReplanProposal:
    """Approve a draft proposal for later application."""
    return await (repo or ReplanProposalRepository()).approve(
        proposal_id,
        approved_by=approved_by,
    )


async def reject_replan_proposal(
    proposal_id: str,
    *,
    reason: str,
    repo: ReplanProposalRepository | None = None,
) -> ReplanProposal:
    """Reject a draft proposal without touching planning tables."""
    if not reason.strip():
        msg = "reject reason is required"
        raise ReplanApplicationError(msg)
    return await (repo or ReplanProposalRepository()).reject(
        proposal_id,
        reason=reason,
    )


async def apply_replan_proposal(
    proposal_id: str,
    *,
    applied_by: str = "human",
    repo: ReplanProposalRepository | None = None,
    narrative_repo: NarrativeRepository | None = None,
) -> ReplanApplicationResult:
    """Apply an approved proposal transactionally."""
    repo = repo or ReplanProposalRepository()
    narrative_repo = narrative_repo or NarrativeRepository()
    async with get_db() as conn:
        try:
            proposal = await repo.get(proposal_id, conn=conn)
            if proposal is None:
                msg = f"replan proposal not found: {proposal_id}"
                raise ReplanApplicationError(msg)
            if proposal.status != "approved":
                msg = (
                    "only approved replan proposals can be applied "
                    f"(proposal_id={proposal_id}, status={proposal.status})"
                )
                raise ReplanApplicationError(msg)
            applied: list[str] = []
            for action in proposal.actions:
                await _apply_action(conn, proposal, action, repo, narrative_repo)
                applied.append(action.action_id)
            await repo.mark_applied(proposal_id, applied_by=applied_by, conn=conn)
            await conn.commit()
        except Exception as exc:  # noqa: BLE001 - rollback and wrap service errors
            await conn.rollback()
            if isinstance(exc, ReplanApplicationError):
                raise
            msg = f"failed to apply replan proposal: {proposal_id}"
            raise ReplanApplicationError(msg) from exc

    result = ReplanApplicationResult(
        proposal_id=proposal_id,
        project_id=proposal.project_id,
        applied_action_ids=applied,
        applied_by=applied_by,
        applied_at=datetime.now(),
    )
    logger.info(
        "replan.apply",
        proposal_id=proposal_id,
        project_id=proposal.project_id,
        actions=len(applied),
    )
    return result


async def _apply_action(
    conn: Any,
    proposal: ReplanProposal,
    action: ReplanAction,
    repo: ReplanProposalRepository,
    narrative_repo: NarrativeRepository,
) -> None:
    if not action.reason.strip():
        msg = f"replan action reason is required: {action.action_id}"
        raise ReplanApplicationError(msg)
    if action.target_type == "arc_plan":
        await _apply_arc_plan_action(conn, proposal, action, narrative_repo)
        return
    if action.target_type == "plot_thread":
        await _apply_plot_thread_action(conn, action, narrative_repo)
        return
    if action.target_type == "style_constraint":
        await _apply_style_constraint_action(conn, proposal, action, repo)
        return
    msg = f"unsupported replan action target_type: {action.target_type}"
    raise ReplanApplicationError(msg)


async def _apply_arc_plan_action(
    conn: Any,
    proposal: ReplanProposal,
    action: ReplanAction,
    narrative_repo: NarrativeRepository,
) -> None:
    arc = await narrative_repo.get_arc_by_id(action.target_id, conn=conn)
    if arc is None:
        msg = f"arc plan not found for replan action: {action.target_id}"
        raise ReplanApplicationError(msg)
    _ensure_future_arc(proposal, arc)

    if action.field == "arc_goal":
        _expect_equal(arc.arc_goal, action.old_value, action, "arc_plan.arc_goal")
        await narrative_repo.update_arc_goal(action.target_id, str(action.new_value), conn=conn)
        updated = await narrative_repo.get_arc_by_id(action.target_id, conn=conn)
        if updated is None or updated.arc_goal != action.new_value:
            msg = f"arc_goal verification failed: {action.action_id}"
            raise ReplanApplicationError(msg)
        return

    if action.field in {"threads_to_open", "threads_to_resolve"}:
        if not isinstance(action.new_value, list) or not all(
            isinstance(item, str) for item in action.new_value
        ):
            msg = f"arc thread list action new_value must be list[str]: {action.action_id}"
            raise ReplanApplicationError(msg)
        current = getattr(arc, action.field)
        _expect_equal(current, action.old_value, action, f"arc_plan.{action.field}")
        await narrative_repo.update_arc_thread_list(
            action.target_id,
            action.field,  # type: ignore[arg-type]
            action.new_value,
            conn=conn,
        )
        updated = await narrative_repo.get_arc_by_id(action.target_id, conn=conn)
        if updated is None or getattr(updated, action.field) != action.new_value:
            msg = f"arc thread list verification failed: {action.action_id}"
            raise ReplanApplicationError(msg)
        return

    msg = f"unsupported arc_plan field: {action.field}"
    raise ReplanApplicationError(msg)


async def _apply_plot_thread_action(
    conn: Any,
    action: ReplanAction,
    narrative_repo: NarrativeRepository,
) -> None:
    thread = await narrative_repo.get_thread(action.target_id, conn=conn)
    if thread is None:
        msg = f"plot thread not found for replan action: {action.target_id}"
        raise ReplanApplicationError(msg)

    if action.field == "expected_resolve_arc":
        _expect_equal(
            thread.expected_resolve_arc,
            action.old_value,
            action,
            "plot_thread.expected_resolve_arc",
        )
        new_value = _optional_int(action.new_value, action)
        await narrative_repo.update_thread_expected_resolve_arc(
            action.target_id,
            new_value,
            conn=conn,
        )
        updated = await narrative_repo.get_thread(action.target_id, conn=conn)
        if updated is None or updated.expected_resolve_arc != new_value:
            msg = f"expected_resolve_arc verification failed: {action.action_id}"
            raise ReplanApplicationError(msg)
        return

    if action.field == "status":
        _expect_equal(thread.status, action.old_value, action, "plot_thread.status")
        new_status = _plot_thread_status(action.new_value, action)
        chapter = _required_int_evidence(action, "chapter")
        version_id = _required_str_evidence(action, "version_id")
        await narrative_repo.advance_thread_status(
            action.target_id,
            new_status,
            chapter,
            version_id,
            conn=conn,
        )
        updated = await narrative_repo.get_thread(action.target_id, conn=conn)
        if updated is None or updated.status != new_status:
            msg = f"plot_thread.status verification failed: {action.action_id}"
            raise ReplanApplicationError(msg)
        return

    msg = f"unsupported plot_thread field: {action.field}"
    raise ReplanApplicationError(msg)


async def _apply_style_constraint_action(
    conn: Any,
    proposal: ReplanProposal,
    action: ReplanAction,
    repo: ReplanProposalRepository,
) -> None:
    if action.new_value is None:
        msg = f"style constraint action requires new_value: {action.action_id}"
        raise ReplanApplicationError(msg)
    constraint_type = (
        "style_constraint"
        if action.field == "style_constraints"
        else "planning_constraint"
    )
    constraint = PlanningConstraint(
        constraint_id=f"pc-{action.action_id}",
        project_id=proposal.project_id,
        source_proposal_id=proposal.proposal_id,
        source_action_id=action.action_id,
        target_id=action.target_id,
        constraint_type=constraint_type,
        content=str(action.new_value),
        reason=action.reason,
    )
    await repo.create_planning_constraint(constraint, conn=conn)


def _ensure_future_arc(proposal: ReplanProposal, arc: ArcPlan) -> None:
    if proposal.source_end_chapter is None:
        return
    if arc.start_chapter <= proposal.source_end_chapter:
        msg = (
            "replan cannot modify historical or source arc plans "
            f"(proposal_id={proposal.proposal_id}, arc_id={arc.arc_id})"
        )
        raise ReplanApplicationError(msg)


def _expect_equal(
    actual: Any,
    expected: Any,
    action: ReplanAction,
    label: str,
) -> None:
    if actual != expected:
        msg = (
            f"replan action old_value mismatch for {label}: "
            f"expected {expected!r}, got {actual!r} (action_id={action.action_id})"
        )
        raise ReplanApplicationError(msg)


def _optional_int(value: Any, action: ReplanAction) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    msg = f"replan action value must be int or null: {action.action_id}"
    raise ReplanApplicationError(msg)


def _plot_thread_status(value: Any, action: ReplanAction) -> PlotThreadStatus:
    valid = {"planned", "opened", "advanced", "resolved", "abandoned"}
    if isinstance(value, str) and value in valid:
        return value  # type: ignore[return-value]
    msg = f"invalid plot thread status in replan action: {action.action_id}"
    raise ReplanApplicationError(msg)


def _required_int_evidence(action: ReplanAction, key: str) -> int:
    value = action.evidence.get(key)
    if isinstance(value, int):
        return value
    msg = f"replan action evidence requires integer {key}: {action.action_id}"
    raise ReplanApplicationError(msg)


def _required_str_evidence(action: ReplanAction, key: str) -> str:
    value = action.evidence.get(key)
    if isinstance(value, str) and value:
        return value
    msg = f"replan action evidence requires string {key}: {action.action_id}"
    raise ReplanApplicationError(msg)
