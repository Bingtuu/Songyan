"""Active foreshadowing scheduling plan generation (V7 Task 167a)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from songyan.db.foreshadowing_schedule_repo import ForeshadowingScheduleRepository
from songyan.db.narrative_repo import NarrativeRepository
from songyan.db.replan_repo import ReplanProposalRepository
from songyan.db.settlement_repo import ForeshadowingRepository
from songyan.models import (
    ArcPlan,
    ForeshadowingItem,
    ForeshadowingScheduleItem,
    ForeshadowingSchedulePlan,
    ForeshadowingScheduleReason,
    ForeshadowingScheduleSourceType,
    PlanningConstraint,
    PlotThread,
)


@dataclass
class _Candidate:
    source_type: ForeshadowingScheduleSourceType
    source_id: str
    title: str
    description: str
    priority_score: float
    reason_codes: list[ForeshadowingScheduleReason] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)


def _current_arc(arcs: list[ArcPlan], target_chapter: int) -> ArcPlan | None:
    for arc in arcs:
        if arc.start_chapter <= target_chapter <= arc.end_chapter:
            return arc
    return None


def _constraint_matches(
    constraint: PlanningConstraint,
    *,
    source_id: str,
    title: str = "",
    description: str = "",
) -> bool:
    needle_parts = [source_id, title, description]
    haystack = f"{constraint.target_id}\n{constraint.content}\n{constraint.reason}"
    return any(part and part in haystack for part in needle_parts)


def _matched_constraints(
    constraints: list[PlanningConstraint],
    *,
    source_id: str,
    title: str = "",
    description: str = "",
) -> list[PlanningConstraint]:
    return [
        constraint
        for constraint in constraints
        if _constraint_matches(
            constraint,
            source_id=source_id,
            title=title,
            description=description,
        )
    ]


def _append_reason(
    reasons: list[ForeshadowingScheduleReason],
    reason: ForeshadowingScheduleReason,
) -> None:
    if reason not in reasons:
        reasons.append(reason)


def _rationale(reasons: list[ForeshadowingScheduleReason]) -> str:
    if not reasons:
        return "普通开放线索，低优先级候选。"
    labels = {
        "mainline_thread": "主线线索",
        "arc_thread_to_open": "当前弧应开启",
        "arc_thread_to_resolve": "当前弧应收束",
        "resolve_arc_due": "临近兑现窗口",
        "resolve_arc_overdue": "已错过兑现窗口",
        "foreshadowing_due": "伏笔临近兑现",
        "foreshadowing_overdue": "伏笔已逾期",
        "replan_backed": "已有 re-plan 约束支持",
    }
    return "；".join(labels[item] for item in reasons if item in labels)


def _thread_candidate(
    thread: PlotThread,
    *,
    current_arc: ArcPlan,
    constraints: list[PlanningConstraint],
) -> _Candidate | None:
    if thread.status in {"resolved", "abandoned"}:
        return None
    score = 10.0
    reasons: list[ForeshadowingScheduleReason] = []
    if thread.is_mainline:
        score += 50.0
        _append_reason(reasons, "mainline_thread")
    if thread.thread_id in current_arc.threads_to_open:
        score += 25.0
        _append_reason(reasons, "arc_thread_to_open")
    if thread.thread_id in current_arc.threads_to_resolve:
        score += 35.0
        _append_reason(reasons, "arc_thread_to_resolve")
    if thread.expected_resolve_arc is not None:
        if thread.expected_resolve_arc < current_arc.arc_index:
            score += 60.0
            _append_reason(reasons, "resolve_arc_overdue")
        elif thread.expected_resolve_arc <= current_arc.arc_index + 1:
            score += 40.0
            _append_reason(reasons, "resolve_arc_due")
    matched = _matched_constraints(
        constraints,
        source_id=thread.thread_id,
        title=thread.title,
        description=thread.description,
    )
    if matched:
        score += 25.0
        _append_reason(reasons, "replan_backed")
    return _Candidate(
        source_type="plot_thread",
        source_id=thread.thread_id,
        title=thread.title or thread.thread_id,
        description=thread.description,
        priority_score=score,
        reason_codes=reasons,
        evidence={
            "thread": thread.model_dump(mode="json"),
            "matched_constraints": [
                item.model_dump(mode="json") for item in matched
            ],
        },
    )


def _foreshadowing_candidate(
    item: ForeshadowingItem,
    *,
    target_chapter: int,
    horizon_chapters: int,
    constraints: list[PlanningConstraint],
) -> _Candidate | None:
    if item.status in {"resolved", "archived"}:
        return None
    score = 8.0
    reasons: list[ForeshadowingScheduleReason] = []
    if (
        item.status == "overdue"
        or (
            item.expected_resolve_chapter is not None
            and item.expected_resolve_chapter < target_chapter
        )
    ):
        score += 70.0
        _append_reason(reasons, "foreshadowing_overdue")
    elif item.status == "due" or (
        item.expected_resolve_chapter is not None
        and item.expected_resolve_chapter <= target_chapter + horizon_chapters
    ):
        score += 45.0
        _append_reason(reasons, "foreshadowing_due")
    matched = _matched_constraints(
        constraints,
        source_id=item.foreshadowing_id,
        description=item.description,
    )
    if matched:
        score += 25.0
        _append_reason(reasons, "replan_backed")
    return _Candidate(
        source_type="foreshadowing",
        source_id=item.foreshadowing_id,
        title=item.description[:40],
        description=item.description,
        priority_score=score,
        reason_codes=reasons,
        evidence={
            "foreshadowing": item.model_dump(mode="json"),
            "matched_constraints": [
                constraint.model_dump(mode="json") for constraint in matched
            ],
        },
    )


def _planning_constraint_candidate(
    constraint: PlanningConstraint,
) -> _Candidate:
    return _Candidate(
        source_type="planning_constraint",
        source_id=constraint.constraint_id,
        title=constraint.content[:40],
        description=constraint.content,
        priority_score=30.0,
        reason_codes=["replan_backed"],
        evidence={"planning_constraint": constraint.model_dump(mode="json")},
    )


def _dedupe_candidates(candidates: list[_Candidate]) -> list[_Candidate]:
    best: dict[tuple[str, str], _Candidate] = {}
    for candidate in candidates:
        key = (candidate.source_type, candidate.source_id)
        existing = best.get(key)
        if existing is None or candidate.priority_score > existing.priority_score:
            best[key] = candidate
    return list(best.values())


async def generate_foreshadowing_schedule_plan(
    project_id: str,
    *,
    target_chapter: int,
    horizon_chapters: int = 5,
    max_items: int = 3,
    duplicate_window: int = 3,
    plan_id: str | None = None,
    narrative_repo: NarrativeRepository | None = None,
    foreshadowing_repo: ForeshadowingRepository | None = None,
    replan_repo: ReplanProposalRepository | None = None,
    schedule_repo: ForeshadowingScheduleRepository | None = None,
) -> ForeshadowingSchedulePlan:
    """Generate a draft schedule plan from SQLite facts."""
    narrative_repo = narrative_repo or NarrativeRepository()
    foreshadowing_repo = foreshadowing_repo or ForeshadowingRepository()
    replan_repo = replan_repo or ReplanProposalRepository()
    schedule_repo = schedule_repo or ForeshadowingScheduleRepository()
    plan_id = plan_id or f"fsp-{project_id}-{target_chapter}-{uuid4().hex[:8]}"

    arcs = await narrative_repo.list_arc_plans(project_id)
    arc = _current_arc(arcs, target_chapter)
    if arc is None:
        return ForeshadowingSchedulePlan(
            plan_id=plan_id,
            project_id=project_id,
            target_chapter=target_chapter,
            horizon_chapters=horizon_chapters,
            max_items=max_items,
            summary="No-op foreshadowing schedule: project has no matching ArcPlan.",
            evidence={"reason": "no_arc_plan", "target_chapter": target_chapter},
        )

    constraints = await replan_repo.list_planning_constraints(project_id)
    recent = await schedule_repo.list_recent_items(
        project_id,
        start_chapter=max(1, target_chapter - duplicate_window),
        end_chapter=target_chapter + duplicate_window,
    )
    recent_keys = {(item.source_type, item.source_id) for item in recent}

    candidates: list[_Candidate] = []
    for thread in await narrative_repo.list_threads(project_id):
        candidate = _thread_candidate(thread, current_arc=arc, constraints=constraints)
        if candidate is not None:
            candidates.append(candidate)
    for item in await foreshadowing_repo.list_schedulable(project_id):
        candidate = _foreshadowing_candidate(
            item,
            target_chapter=target_chapter,
            horizon_chapters=horizon_chapters,
            constraints=constraints,
        )
        if candidate is not None:
            candidates.append(candidate)

    matched_constraint_ids = {
        matched.constraint_id
        for candidate in candidates
        for matched in (
            PlanningConstraint.model_validate(item)
            for item in candidate.evidence.get("matched_constraints", [])
        )
    }
    for constraint in constraints:
        if constraint.constraint_id not in matched_constraint_ids:
            candidates.append(_planning_constraint_candidate(constraint))

    deduped = [
        candidate
        for candidate in _dedupe_candidates(candidates)
        if (candidate.source_type, candidate.source_id) not in recent_keys
    ]
    ordered = sorted(
        deduped,
        key=lambda item: (
            -item.priority_score,
            item.source_type,
            item.source_id,
        ),
    )
    selected = ordered[:max_items]
    plan = ForeshadowingSchedulePlan(
        plan_id=plan_id,
        project_id=project_id,
        target_chapter=target_chapter,
        current_arc_index=arc.arc_index,
        horizon_chapters=horizon_chapters,
        max_items=max_items,
        summary=(
            f"Generated {len(selected)} foreshadowing schedule item(s) "
            f"for Ch{target_chapter}."
        ),
        evidence={
            "arc": arc.model_dump(mode="json"),
            "candidate_count": len(candidates),
            "deduped_count": len(deduped),
            "recent_suppressed": [
                item.model_dump(mode="json") for item in recent
            ],
        },
    )
    plan.items = [
        ForeshadowingScheduleItem(
            item_id=f"{plan.plan_id}-i{idx:03d}",
            plan_id=plan.plan_id,
            project_id=project_id,
            item_order=idx,
            target_chapter=target_chapter,
            source_type=candidate.source_type,
            source_id=candidate.source_id,
            title=candidate.title,
            description=candidate.description,
            priority_score=candidate.priority_score,
            reason_codes=candidate.reason_codes,
            rationale=_rationale(candidate.reason_codes),
            status="draft",
            evidence=candidate.evidence,
        )
        for idx, candidate in enumerate(selected)
    ]
    return plan
