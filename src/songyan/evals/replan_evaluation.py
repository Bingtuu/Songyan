"""Arc outcome evaluation and draft re-plan proposal generation (Task 166a)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import uuid4

from songyan.db.context_repo import SummaryRepository
from songyan.db.layered_context_repo import ArcSummaryRepository
from songyan.db.narrative_repo import NarrativeRepository
from songyan.db.review_repo import LiteraryObservationRepository
from songyan.db.text_cleanliness_repo import TextCleanlinessMetricRepository
from songyan.evals.db_metrics import (
    collect_literary_scores,
    collect_new_critical_rate,
    collect_orphan_metrics,
    linear_slope,
)
from songyan.exceptions import SongyanError
from songyan.models import (
    ArcOutcomeEvaluation,
    ArcPlan,
    PlotThread,
    ReplanAction,
    ReplanActionTargetType,
    ReplanProposal,
)

_T10_COEFFICIENT = 0.85
_STYLE_SIGNAL_CONSTRAINTS: dict[str, str] = {
    "ai_rhythm_pattern": (
        "限制模型化句式复用，尤其避免连续使用“不是 A，是 B”和空泛比喻；"
        "下一阶段每章必须用动作或具体场景承载抽象判断。"
    ),
    "conceptual_idling": (
        "压低概念解释密度；新概念必须通过行动、冲突或可观察后果落地，"
        "不得只以定义式旁白推进。"
    ),
    "polyphony_weakness": (
        "强化关键角色声纹区分；每个核心角色在下一阶段必须承担不同的"
        "语言功能、行动偏好和冲突立场。"
    ),
}
_STYLE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "ai_rhythm_pattern": ("句式模型化", "不是", "像", "AI节奏", "ai 节奏"),
    "conceptual_idling": ("概念解释", "概念空转", "概念密度", "定义式"),
    "polyphony_weakness": ("声纹", "同质", "人物工具化", "角色声纹"),
}


class ReplanEvaluationError(SongyanError):
    """Raised when Task 166a cannot select a valid evaluation target."""


def _model_dump_list(items: Sequence[Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in items:
        if hasattr(item, "model_dump"):
            result.append(item.model_dump(mode="json"))
        elif isinstance(item, dict):
            result.append(dict(item))
    return result


def _normalize_chapter_range(
    chapter_range: tuple[int, int] | None,
) -> tuple[int, int] | None:
    if chapter_range is None:
        return None
    start, end = chapter_range
    if start <= 0 or end <= 0 or start > end:
        msg = f"invalid chapter_range: {chapter_range}"
        raise ReplanEvaluationError(msg)
    return start, end


def _select_arc(
    arcs: list[ArcPlan],
    *,
    arc_index: int | None,
    chapter_range: tuple[int, int] | None,
) -> ArcPlan | None:
    if not arcs:
        return None
    if arc_index is not None:
        for arc in arcs:
            if arc.arc_index == arc_index:
                return arc
        msg = f"arc_index not found: {arc_index}"
        raise ReplanEvaluationError(msg)
    if chapter_range is not None:
        start, end = chapter_range
        for arc in arcs:
            if arc.start_chapter <= start and arc.end_chapter >= end:
                return arc
        for arc in arcs:
            if arc.start_chapter <= end and arc.end_chapter >= start:
                return arc
        return None
    return max(arcs, key=lambda item: item.arc_index)


def _related_threads(
    arc: ArcPlan,
    threads: list[PlotThread],
) -> dict[str, PlotThread]:
    ids = set(arc.threads_to_open) | set(arc.threads_to_resolve)
    return {thread.thread_id: thread for thread in threads if thread.thread_id in ids}


def _extract_style_debt_signals(rows: list[dict[str, Any]]) -> list[str]:
    signals: list[str] = []
    for row in rows:
        text_parts = [str(row.get("summary", ""))]
        for observation in row.get("observations", []):
            obs_type = str(observation.get("observation_type", ""))
            if obs_type in _STYLE_SIGNAL_CONSTRAINTS and obs_type not in signals:
                signals.append(obs_type)
            text_parts.extend(
                [
                    str(observation.get("description", "")),
                    str(observation.get("recommendation", "")),
                ]
            )
        text = "\n".join(text_parts)
        for signal, keywords in _STYLE_KEYWORDS.items():
            if signal not in signals and any(keyword in text for keyword in keywords):
                signals.append(signal)
    return signals


def _t10_warning(literary_points: list[Any]) -> dict[str, Any]:
    if len(literary_points) < 2:
        return {"available": False, "warning": None}
    first = literary_points[0].conceptual_grounding_score
    last = literary_points[-1].conceptual_grounding_score
    threshold = first * _T10_COEFFICIENT
    warning = (
        "T10 conceptual_grounding 下滑"
        if first > 0 and last < threshold
        else None
    )
    return {
        "available": True,
        "first": first,
        "last": last,
        "threshold": threshold,
        "coefficient": _T10_COEFFICIENT,
        "warning": warning,
    }


def _risk_level(
    *,
    has_skeleton: bool,
    unopened_threads: list[str],
    unresolved_threads: list[str],
    metric_warnings: list[str],
    style_debt_signals: list[str],
) -> str:
    if not has_skeleton:
        return "none"
    if unopened_threads or unresolved_threads:
        return "high"
    hard_warnings = [
        item for item in metric_warnings if item.startswith(("T9", "T6"))
    ]
    if hard_warnings:
        return "medium"
    if metric_warnings or style_debt_signals:
        return "low"
    return "low"


async def evaluate_arc_outcome(
    project_id: str,
    *,
    arc_index: int | None = None,
    chapter_range: tuple[int, int] | None = None,
    narrative_repo: NarrativeRepository | None = None,
    summary_repo: SummaryRepository | None = None,
    arc_summary_repo: ArcSummaryRepository | None = None,
    text_metric_repo: TextCleanlinessMetricRepository | None = None,
    literary_repo: LiteraryObservationRepository | None = None,
) -> ArcOutcomeEvaluation:
    """Evaluate one planned arc against generated facts from SQLite."""
    narrative_repo = narrative_repo or NarrativeRepository()
    summary_repo = summary_repo or SummaryRepository()
    arc_summary_repo = arc_summary_repo or ArcSummaryRepository()
    text_metric_repo = text_metric_repo or TextCleanlinessMetricRepository()
    literary_repo = literary_repo or LiteraryObservationRepository()

    normalized_range = _normalize_chapter_range(chapter_range)
    arcs = await narrative_repo.list_arc_plans(project_id)
    arc = _select_arc(arcs, arc_index=arc_index, chapter_range=normalized_range)
    if arc is None:
        start = normalized_range[0] if normalized_range else None
        end = normalized_range[1] if normalized_range else None
        return ArcOutcomeEvaluation(
            project_id=project_id,
            has_skeleton=False,
            source_start_chapter=start,
            source_end_chapter=end,
            risk_level="none",
            summary="无叙事骨架或无匹配 ArcPlan，166a 返回 no-op evaluation。",
            evidence={"reason": "no_arc_plan", "requested_range": normalized_range},
        )

    start = arc.start_chapter
    end = arc.end_chapter
    threads = await narrative_repo.list_threads(project_id)
    thread_map = _related_threads(arc, threads)
    summaries = await summary_repo.list_by_chapter_range(project_id, start, end)
    arc_summaries = [
        item
        for item in await arc_summary_repo.list_by_project(project_id)
        if item.start_chapter <= end and item.end_chapter >= start
    ]
    text_rows = await text_metric_repo.list_by_project(project_id, start, end)
    literary_points = await collect_literary_scores(
        project_id, start, end, repo=literary_repo
    )
    literary_rows = await literary_repo.list_observations_by_chapter_range(
        project_id, start, end
    )
    orphan_points = await collect_orphan_metrics(project_id, start, end)
    critical_points = await collect_new_critical_rate(project_id, start, end)

    unopened = [
        thread_id
        for thread_id in arc.threads_to_open
        if thread_map.get(thread_id) is not None
        and thread_map[thread_id].status == "planned"
    ]
    unresolved = [
        thread_id
        for thread_id in arc.threads_to_resolve
        if thread_map.get(thread_id) is None
        or thread_map[thread_id].status not in {"resolved", "abandoned"}
    ]

    metric_warnings: list[str] = []
    meta_total = sum(row.meta_tag_leak_count for row in text_rows)
    duplicate_total = sum(row.duplicate_paragraph_count for row in text_rows)
    timeline_total = sum(row.timeline_conflict_count for row in text_rows)
    if meta_total or duplicate_total:
        metric_warnings.append(
            f"T9 hard cleanliness breach: meta={meta_total}, duplicate={duplicate_total}"
        )

    t10 = _t10_warning(literary_points)
    if t10["warning"]:
        metric_warnings.append(str(t10["warning"]))

    max_critical_orphans = (
        max((point.orphan_critical for point in orphan_points), default=0)
    )
    if max_critical_orphans > 0:
        metric_warnings.append(f"T6 critical orphan remains: {max_critical_orphans}")
    orphan_slope = linear_slope(
        [point.chapter for point in orphan_points],
        [float(point.orphan_total) for point in orphan_points],
    )
    avg_new_critical = (
        sum(point.new_critical for point in critical_points) / len(critical_points)
        if critical_points
        else 0.0
    )
    style_signals = _extract_style_debt_signals(literary_rows)

    risk = _risk_level(
        has_skeleton=True,
        unopened_threads=unopened,
        unresolved_threads=unresolved,
        metric_warnings=metric_warnings,
        style_debt_signals=style_signals,
    )
    summary = (
        f"Arc {arc.arc_index} evaluated: unopened={len(unopened)}, "
        f"unresolved={len(unresolved)}, metric_warnings={len(metric_warnings)}, "
        f"style_debts={len(style_signals)}."
    )

    return ArcOutcomeEvaluation(
        project_id=project_id,
        has_skeleton=True,
        source_arc_id=arc.arc_id,
        source_arc_index=arc.arc_index,
        source_start_chapter=start,
        source_end_chapter=end,
        arc_goal=arc.arc_goal,
        risk_level=risk,
        summary=summary,
        unopened_threads=unopened,
        unresolved_threads=unresolved,
        metric_warnings=metric_warnings,
        style_debt_signals=style_signals,
        evidence={
            "arc": arc.model_dump(mode="json"),
            "threads": {
                thread_id: thread.model_dump(mode="json")
                for thread_id, thread in thread_map.items()
            },
            "summaries": _model_dump_list(summaries),
            "arc_summaries": _model_dump_list(arc_summaries),
            "metrics": {
                "text_cleanliness": {
                    "sample_count": len(text_rows),
                    "meta_tag_leak_count": meta_total,
                    "duplicate_paragraph_count": duplicate_total,
                    "timeline_conflict_count": timeline_total,
                },
                "t10": t10,
                "orphan": {
                    "sample_count": len(orphan_points),
                    "max_critical": max_critical_orphans,
                    "slope": orphan_slope,
                },
                "new_critical_rate": {
                    "sample_count": len(critical_points),
                    "average": avg_new_critical,
                },
            },
            "style_debt_signals": style_signals,
        },
    )


def build_replan_proposal(
    evaluation: ArcOutcomeEvaluation,
    *,
    proposal_id: str | None = None,
) -> ReplanProposal:
    """Build a draft proposal from a read-only evaluation."""
    proposal_id = proposal_id or (
        f"rp-{evaluation.project_id}-"
        f"{evaluation.source_arc_index if evaluation.source_arc_index is not None else 'noop'}-"
        f"{uuid4().hex[:8]}"
    )
    proposal = ReplanProposal(
        proposal_id=proposal_id,
        project_id=evaluation.project_id,
        source_arc_index=evaluation.source_arc_index,
        source_start_chapter=evaluation.source_start_chapter,
        source_end_chapter=evaluation.source_end_chapter,
        status="draft",
        summary=evaluation.summary,
        evidence=evaluation.model_dump(mode="json"),
    )
    if not evaluation.has_skeleton:
        proposal.summary = "No-op replan proposal: project has no matching narrative skeleton."
        return proposal

    thread_evidence = evaluation.evidence.get("threads", {})
    next_arc = (
        evaluation.source_arc_index + 1
        if evaluation.source_arc_index is not None
        else None
    )

    def add_action(
        *,
        target_type: ReplanActionTargetType,
        target_id: str,
        field: str,
        old_value: Any,
        new_value: Any,
        reason: str,
        evidence: dict[str, Any] | None = None,
    ) -> None:
        order = len(proposal.actions)
        proposal.actions.append(
            ReplanAction(
                action_id=f"{proposal.proposal_id}-a{order:03d}",
                proposal_id=proposal.proposal_id,
                action_order=order,
                target_type=target_type,
                target_id=target_id,
                field=field,
                old_value=old_value,
                new_value=new_value,
                reason=reason,
                evidence=evidence or {},
            )
        )

    for thread_id in evaluation.unopened_threads:
        thread = thread_evidence.get(thread_id, {})
        add_action(
            target_type="plot_thread",
            target_id=thread_id,
            field="status",
            old_value=thread.get("status", "planned"),
            new_value="opened",
            reason="该线索在本弧 threads_to_open 中列出，但生成结果未开启。",
            evidence={"source": "threads_to_open", "arc_index": evaluation.source_arc_index},
        )

    for thread_id in evaluation.unresolved_threads:
        thread = thread_evidence.get(thread_id, {})
        add_action(
            target_type="plot_thread",
            target_id=thread_id,
            field="expected_resolve_arc",
            old_value=thread.get("expected_resolve_arc"),
            new_value=next_arc,
            reason="该线索在本弧 threads_to_resolve 中列出，但生成结果未收束。",
            evidence={
                "source": "threads_to_resolve",
                "arc_index": evaluation.source_arc_index,
            },
        )

    for warning in evaluation.metric_warnings:
        add_action(
            target_type="style_constraint",
            target_id=evaluation.source_arc_id or evaluation.project_id,
            field="planning_constraints",
            old_value=None,
            new_value=warning,
            reason="质量度量显示后续规划需要加入约束，避免同类债务扩大。",
            evidence={"warning": warning},
        )

    for signal in evaluation.style_debt_signals:
        add_action(
            target_type="style_constraint",
            target_id=evaluation.source_arc_id or evaluation.project_id,
            field="style_constraints",
            old_value=None,
            new_value=_STYLE_SIGNAL_CONSTRAINTS.get(signal, signal),
            reason=f"阶段 W 读后风格债信号：{signal}",
            evidence={"style_debt_signal": signal},
        )

    if proposal.actions:
        proposal.summary = (
            f"{evaluation.summary} Generated {len(proposal.actions)} draft "
            "replan action(s)."
        )
    else:
        proposal.summary = (
            f"{evaluation.summary} No draft replan action is required."
        )
    return proposal
