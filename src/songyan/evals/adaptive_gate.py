"""Adaptive gate data-plane helpers (V7 Task 168a/168b)."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from statistics import median
from typing import Any

from pydantic import BaseModel

from songyan.db.adaptive_gate_repo import AdaptiveGateSignalRepository
from songyan.models import (
    AdaptiveGateCleanlinessSignals,
    AdaptiveGateContextSignals,
    AdaptiveGateContinuitySignals,
    AdaptiveGateDataPlaneReport,
    AdaptiveGateLiterarySignals,
    AdaptiveGateNarrativeSignals,
    AdaptiveGateQualitySignals,
    AdaptiveGateSignalSnapshot,
    AdaptiveGateSignalSourceStatus,
    AdaptiveGateSignalWindow,
)
from songyan.models.adaptive_gate import (
    ADAPTIVE_GATE_SIGNAL_DOMAINS,
    default_source_status,
)


def _snapshot_id(project_id: str, chapter_number: int, run_id: str | None) -> str:
    run_key = run_id or "norun"
    return f"ags-{project_id}-{run_key}-{chapter_number}"


def _model_data(value: BaseModel | dict[str, Any] | None) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, BaseModel):
        return value.model_dump()
    return dict(value)


def _source_status(
    *,
    source_status: dict[str, AdaptiveGateSignalSourceStatus] | None,
    provided_domains: set[str],
) -> dict[str, AdaptiveGateSignalSourceStatus]:
    result = default_source_status()
    for domain in provided_domains:
        if domain in result:
            result[domain] = "present"
    if source_status:
        result.update(source_status)
    return {
        domain: result.get(domain, "missing")
        for domain in ADAPTIVE_GATE_SIGNAL_DOMAINS
    }


def build_adaptive_gate_signal_snapshot(
    *,
    project_id: str,
    chapter_number: int,
    run_id: str | None = None,
    snapshot_id: str | None = None,
    source_status: dict[str, AdaptiveGateSignalSourceStatus] | None = None,
    continuity: AdaptiveGateContinuitySignals | dict[str, Any] | None = None,
    quality: AdaptiveGateQualitySignals | dict[str, Any] | None = None,
    literary: AdaptiveGateLiterarySignals | dict[str, Any] | None = None,
    cleanliness: AdaptiveGateCleanlinessSignals | dict[str, Any] | None = None,
    context: AdaptiveGateContextSignals | dict[str, Any] | None = None,
    narrative: AdaptiveGateNarrativeSignals | dict[str, Any] | None = None,
    created_at: datetime | None = None,
) -> AdaptiveGateSignalSnapshot:
    """Build one adaptive-gate signal snapshot from already-collected inputs.

    Missing domain inputs are preserved as explicit ``source_status=missing``.
    This helper intentionally does not query SQLite, inspect LangGraph state, or
    call LLMs; refresh/collection orchestration belongs to later data-plane code.
    """
    provided = {
        name
        for name, value in {
            "continuity": continuity,
            "quality": quality,
            "literary": literary,
            "cleanliness": cleanliness,
            "context": context,
            "narrative": narrative,
        }.items()
        if value is not None
    }
    now = created_at or datetime.now()
    return AdaptiveGateSignalSnapshot(
        snapshot_id=snapshot_id or _snapshot_id(project_id, chapter_number, run_id),
        project_id=project_id,
        run_id=run_id,
        chapter_number=chapter_number,
        source_status=_source_status(
            source_status=source_status,
            provided_domains=provided,
        ),
        continuity=AdaptiveGateContinuitySignals(**_model_data(continuity)),
        quality=AdaptiveGateQualitySignals(**_model_data(quality)),
        literary=AdaptiveGateLiterarySignals(**_model_data(literary)),
        cleanliness=AdaptiveGateCleanlinessSignals(**_model_data(cleanliness)),
        context=AdaptiveGateContextSignals(**_model_data(context)),
        narrative=AdaptiveGateNarrativeSignals(**_model_data(narrative)),
        created_at=now,
        updated_at=now,
    )


async def _safe_collect(awaitable: Any, fallback: Any) -> Any:
    try:
        return await awaitable
    except sqlite3.OperationalError:
        return fallback


async def refresh_adaptive_gate_signal_snapshots(
    project_id: str,
    start: int,
    end: int,
    *,
    run_id: str | None = None,
    repo: AdaptiveGateSignalRepository | None = None,
) -> int:
    """Refresh snapshot rows from existing DB facts and optional run logs.

    This is a data-plane refresh only. It does not evaluate gates, create halt
    reasons, or mutate workflow state.
    """
    # Local imports avoid making db_metrics import adaptive_gate at module load time.
    from songyan.db.foreshadowing_schedule_repo import ForeshadowingScheduleRepository
    from songyan.db.replan_repo import ReplanProposalRepository
    from songyan.db.settlement_repo import ForeshadowingRepository
    from songyan.evals.db_metrics import (
        collect_db_maintenance_samples,
        collect_literary_scores,
        collect_new_critical_rate,
        collect_orphan_metrics,
    )
    from songyan.evals.streaming_report import read_run_logs
    from songyan.evals.text_cleanliness import load_text_cleanliness_metrics

    repo = repo or AdaptiveGateSignalRepository()
    orphan_points = await _safe_collect(collect_orphan_metrics(project_id, start, end), [])
    critical_points = await _safe_collect(
        collect_new_critical_rate(project_id, start, end), []
    )
    literary_points = await _safe_collect(
        collect_literary_scores(project_id, start, end), []
    )
    cleanliness_rows = await _safe_collect(
        load_text_cleanliness_metrics(project_id, start, end), []
    )
    db_samples = await _safe_collect(
        collect_db_maintenance_samples(project_id, start, end), []
    )
    schedule_items = await _safe_collect(
        ForeshadowingScheduleRepository().list_recent_items(
            project_id,
            start_chapter=start,
            end_chapter=end,
            statuses=(
                "active",
                "injected",
                "satisfied",
                "missed",
                "cancelled",
            ),
        ),
        [],
    )
    schedulable_foreshadowings = await _safe_collect(
        ForeshadowingRepository().list_schedulable(project_id),
        [],
    )
    planning_constraints = await _safe_collect(
        ReplanProposalRepository().list_planning_constraints(project_id),
        [],
    )
    run_logs = read_run_logs(run_id) if run_id else []

    orphan_by_chapter = {point.chapter: point for point in orphan_points}
    critical_by_chapter = {point.chapter: point for point in critical_points}
    literary_by_chapter = {point.chapter: point for point in literary_points}
    cleanliness_by_chapter = {
        row.chapter_number: row for row in cleanliness_rows
    }
    db_by_chapter = {
        int(sample["chapter_number"]): sample for sample in db_samples
    }
    log_by_chapter = {
        log.chapter_number: log
        for log in run_logs
        if start <= log.chapter_number <= end
    }
    schedule_by_chapter: dict[int, list[Any]] = {}
    for item in schedule_items:
        schedule_by_chapter.setdefault(item.target_chapter, []).append(item)

    await repo.delete_range(project_id, start, end, run_id=run_id)
    count = 0
    for chapter in range(start, end + 1):
        source_status: dict[str, AdaptiveGateSignalSourceStatus] = {}
        continuity: dict[str, Any] | None = None
        orphan = orphan_by_chapter.get(chapter)
        critical = critical_by_chapter.get(chapter)
        if orphan is not None or critical is not None:
            continuity = {
                "health_score": None,
                "p1_count": orphan.orphan_critical if orphan is not None else 0,
                "p2_count": orphan.orphan_recurring if orphan is not None else 0,
                "p3_count": (
                    orphan.orphan_other + orphan.forgotten_items
                    if orphan is not None
                    else 0
                ),
                "orphan_total": orphan.orphan_total if orphan is not None else 0,
                "orphan_critical": orphan.orphan_critical if orphan is not None else 0,
                "orphan_recurring": orphan.orphan_recurring if orphan is not None else 0,
                "orphan_other": orphan.orphan_other if orphan is not None else 0,
                "forgotten_count": orphan.forgotten_items if orphan is not None else 0,
                "new_critical_count": critical.new_critical if critical is not None else 0,
                "new_setting_count": critical.new_total if critical is not None else 0,
            }
        else:
            source_status["continuity"] = "missing"

        quality: dict[str, Any] | None = None
        log = log_by_chapter.get(chapter)
        if log is not None:
            quality = {
                "quality_gate_passed": log.quality_gate_passed,
                "degraded_accept": log.degraded_accept,
                "convergence_failed": log.convergence_failed,
                "qg_false": log.quality_gate_passed is False,
                "revision_rounds": log.revision_rounds,
            }
            if continuity is None and log.continuity_health_score is not None:
                continuity = {
                    "health_score": log.continuity_health_score,
                    "p1_count": (log.continuity_health_severity or {}).get("P1", 0),
                    "p2_count": (log.continuity_health_severity or {}).get("P2", 0),
                    "p3_count": (log.continuity_health_severity or {}).get("P3", 0),
                }
                source_status.pop("continuity", None)
        else:
            source_status["quality"] = "missing"

        literary = literary_by_chapter.get(chapter)
        literary_payload = (
            {
                "literary_quality_score": literary.literary_quality_score,
                "character_autonomy_score": literary.character_autonomy_score,
                "conceptual_grounding_score": literary.conceptual_grounding_score,
                "fissure_preservation_score": literary.fissure_preservation_score,
            }
            if literary is not None
            else None
        )
        if literary is None:
            source_status["literary"] = "missing"

        cleanliness = cleanliness_by_chapter.get(chapter)
        cleanliness_payload = (
            {
                "meta_tag_leak_count": cleanliness.meta_tag_leak_count,
                "duplicate_paragraph_count": cleanliness.duplicate_paragraph_count,
                "timeline_conflict_count": cleanliness.timeline_conflict_count,
            }
            if cleanliness is not None
            else None
        )
        if cleanliness is None:
            source_status["cleanliness"] = "missing"

        db_sample = db_by_chapter.get(chapter)
        context_payload = None
        if db_sample is not None or log is not None:
            context_payload = {
                "context_emergency": bool(log.context_emergency) if log else False,
                "budget_used": log.budget_used if log else None,
                "budget_used_before_emergency": (
                    log.budget_used_before_emergency if log else None
                ),
                "db_size_bytes": (
                    int(db_sample["db_size_bytes"]) if db_sample is not None else None
                ),
                "scan_latency_ms": (
                    float(db_sample["scan_latency_ms"]) if db_sample is not None else None
                ),
            }
        else:
            source_status["context"] = "missing"

        chapter_schedule = schedule_by_chapter.get(chapter, [])
        overdue_count = sum(
            1
            for item in schedulable_foreshadowings
            if item.expected_resolve_chapter is not None
            and item.expected_resolve_chapter <= chapter
        )
        narrative_payload = None
        if chapter_schedule or overdue_count or planning_constraints:
            narrative_payload = {
                "schedule_active_count": sum(
                    1 for item in chapter_schedule if item.status == "active"
                ),
                "schedule_injected_count": sum(
                    1 for item in chapter_schedule if item.status == "injected"
                ),
                "schedule_satisfied_count": sum(
                    1 for item in chapter_schedule if item.status == "satisfied"
                ),
                "schedule_missed_count": sum(
                    1 for item in chapter_schedule if item.status == "missed"
                ),
                "schedule_cancelled_count": sum(
                    1 for item in chapter_schedule if item.status == "cancelled"
                ),
                "overdue_foreshadowing_count": overdue_count,
                "active_planning_constraint_count": len(planning_constraints),
            }
        else:
            source_status["narrative"] = "missing"

        snapshot = build_adaptive_gate_signal_snapshot(
            project_id=project_id,
            run_id=run_id,
            chapter_number=chapter,
            source_status=source_status,
            continuity=continuity,
            quality=quality,
            literary=literary_payload,
            cleanliness=cleanliness_payload,
            context=context_payload,
            narrative=narrative_payload,
        )
        await repo.upsert(snapshot)
        count += 1
    return count


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _median(values: list[float]) -> float | None:
    return float(median(values)) if values else None


def _ratio(count: int, total: int) -> float | None:
    return count / total if total else None


def _linear_slope(xs: list[int], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 2:
        return None
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    denom = sum((x - mean_x) ** 2 for x in xs)
    if denom == 0:
        return None
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=False))
    return num / denom


def _domain_present(
    snapshot: AdaptiveGateSignalSnapshot,
    domain: str,
    *,
    include_observation: bool = False,
) -> bool:
    status = snapshot.source_status.get(domain, "missing")
    return status == "present" or (include_observation and status == "observation")


def _status_counts(
    snapshots: list[AdaptiveGateSignalSnapshot],
) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for domain in ADAPTIVE_GATE_SIGNAL_DOMAINS:
        domain_counts = {
            "present": 0,
            "missing": 0,
            "insufficient": 0,
            "observation": 0,
        }
        for snapshot in snapshots:
            status = snapshot.source_status.get(domain, "missing")
            domain_counts[status] = domain_counts.get(status, 0) + 1
        counts[domain] = domain_counts
    return counts


def _window_from_snapshots(
    snapshots: list[AdaptiveGateSignalSnapshot],
    *,
    window_size: int,
) -> AdaptiveGateSignalWindow:
    start = snapshots[0].chapter_number
    end = snapshots[-1].chapter_number
    continuity = [s for s in snapshots if _domain_present(s, "continuity")]
    quality = [s for s in snapshots if _domain_present(s, "quality")]
    literary = [s for s in snapshots if _domain_present(s, "literary")]
    cleanliness = [
        s for s in snapshots if _domain_present(s, "cleanliness", include_observation=True)
    ]
    context = [s for s in snapshots if _domain_present(s, "context")]
    narrative = [s for s in snapshots if _domain_present(s, "narrative")]

    health_values = [
        float(s.continuity.health_score)
        for s in continuity
        if s.continuity.health_score is not None
    ]
    orphan_points = [
        (s.chapter_number, float(s.continuity.orphan_total))
        for s in continuity
    ]
    orphan_delta = (
        int(orphan_points[-1][1] - orphan_points[0][1])
        if len(orphan_points) >= 2
        else None
    )
    degraded = sum(1 for s in quality if s.quality.degraded_accept)
    convergence = sum(1 for s in quality if s.quality.convergence_failed)
    qg_false = sum(1 for s in quality if s.quality.qg_false)
    context_emergency = sum(1 for s in context if s.context.context_emergency)
    budget_values = [
        float(s.context.budget_used)
        for s in context
        if s.context.budget_used is not None
    ]
    db_size_values = [
        int(s.context.db_size_bytes)
        for s in context
        if s.context.db_size_bytes is not None
    ]
    scan_values = [
        float(s.context.scan_latency_ms)
        for s in context
        if s.context.scan_latency_ms is not None
    ]
    schedule_satisfied = sum(s.narrative.schedule_satisfied_count for s in narrative)
    schedule_missed = sum(s.narrative.schedule_missed_count for s in narrative)
    schedule_injected = sum(s.narrative.schedule_injected_count for s in narrative)
    schedule_overdue = sum(s.narrative.overdue_foreshadowing_count for s in narrative)
    schedule_outcome_total = schedule_satisfied + schedule_missed
    schedule_total = schedule_injected + schedule_satisfied + schedule_missed + schedule_overdue

    orphan_x = [p[0] for p in orphan_points]
    orphan_y = [p[1] for p in orphan_points]
    return AdaptiveGateSignalWindow(
        start_chapter=start,
        end_chapter=end,
        sample_count=len(snapshots),
        window_size=window_size,
        source_status_counts=_status_counts(snapshots),
        health_min=min(health_values) if health_values else None,
        health_median=_median(health_values),
        p1_median=_median([float(s.continuity.p1_count) for s in continuity]),
        p2_median=_median([float(s.continuity.p2_count) for s in continuity]),
        orphan_slope=_linear_slope(orphan_x, orphan_y),
        orphan_delta=orphan_delta,
        new_critical_mean=_mean(
            [float(s.continuity.new_critical_count) for s in continuity]
        ),
        degraded_ratio=_ratio(degraded, len(quality)),
        convergence_ratio=_ratio(convergence, len(quality)),
        qg_false_ratio=_ratio(qg_false, len(quality)),
        literary_quality_mean=_mean(
            [
                float(s.literary.literary_quality_score)
                for s in literary
                if s.literary.literary_quality_score is not None
            ]
        ),
        character_autonomy_mean=_mean(
            [
                float(s.literary.character_autonomy_score)
                for s in literary
                if s.literary.character_autonomy_score is not None
            ]
        ),
        conceptual_grounding_mean=_mean(
            [
                float(s.literary.conceptual_grounding_score)
                for s in literary
                if s.literary.conceptual_grounding_score is not None
            ]
        ),
        fissure_preservation_mean=_mean(
            [
                float(s.literary.fissure_preservation_score)
                for s in literary
                if s.literary.fissure_preservation_score is not None
            ]
        ),
        meta_tag_leak_total=sum(s.cleanliness.meta_tag_leak_count for s in cleanliness),
        duplicate_paragraph_total=sum(
            s.cleanliness.duplicate_paragraph_count for s in cleanliness
        ),
        timeline_conflict_total=sum(
            s.cleanliness.timeline_conflict_count for s in cleanliness
        ),
        context_emergency_ratio=_ratio(context_emergency, len(context)),
        budget_used_max=max(budget_values) if budget_values else None,
        db_size_max_mb=(
            max(db_size_values) / (1024 * 1024) if db_size_values else None
        ),
        scan_latency_max_ms=max(scan_values) if scan_values else None,
        schedule_injected_count=schedule_injected,
        schedule_satisfied_count=schedule_satisfied,
        schedule_missed_count=schedule_missed,
        schedule_overdue_count=schedule_overdue,
        schedule_hit_rate=_ratio(schedule_satisfied, schedule_outcome_total),
        schedule_missed_rate=_ratio(schedule_missed, schedule_outcome_total),
        schedule_overdue_rate=_ratio(schedule_overdue, schedule_total),
    )


async def collect_adaptive_gate_windows(
    project_id: str,
    start: int,
    end: int,
    *,
    run_id: str | None = None,
    window: int = 5,
    repo: AdaptiveGateSignalRepository | None = None,
) -> list[AdaptiveGateSignalWindow]:
    """Collect rolling adaptive-gate windows from persisted snapshots only."""
    repo = repo or AdaptiveGateSignalRepository()
    snapshots = await repo.list_range(project_id, start, end, run_id=run_id)
    snapshots.sort(key=lambda item: item.chapter_number)
    if not snapshots or len(snapshots) < window:
        return []
    return [
        _window_from_snapshots(snapshots[index : index + window], window_size=window)
        for index in range(len(snapshots) - window + 1)
    ]


async def build_adaptive_gate_data_plane_report(
    project_id: str,
    start: int,
    end: int,
    *,
    run_id: str | None = None,
    window: int = 5,
    repo: AdaptiveGateSignalRepository | None = None,
) -> AdaptiveGateDataPlaneReport:
    """Build a report that describes adaptive-gate inputs without judging them."""
    repo = repo or AdaptiveGateSignalRepository()
    snapshots = await repo.list_range(project_id, start, end, run_id=run_id)
    windows = await collect_adaptive_gate_windows(
        project_id,
        start,
        end,
        run_id=run_id,
        window=window,
        repo=repo,
    )
    return AdaptiveGateDataPlaneReport(
        project_id=project_id,
        run_id=run_id,
        chapter_start=start,
        chapter_end=end,
        window_size=window,
        snapshot_count=len(snapshots),
        source_status_counts=_status_counts(snapshots),
        windows=windows,
    )


def _fmt(value: float | int | None, *, percent: bool = False) -> str:
    if value is None:
        return "-"
    if percent:
        return f"{float(value):.1%}"
    if isinstance(value, int):
        return str(value)
    return f"{float(value):.3f}"


def render_adaptive_gate_data_plane_section(
    report: AdaptiveGateDataPlaneReport,
) -> str:
    """Render Task 168 data-plane metrics for songyan metrics."""
    lines = [
        "## 自适应门禁数据面（Task 168；只供 Task 169 判定使用）",
        "",
        "本段只展示 gate 输入信号，不输出 pass/fail/halt，不改变 enforce 行为。",
        "",
    ]
    if report.snapshot_count == 0:
        lines.append("（无 adaptive_gate_signal_snapshots；请先刷新 168a 快照）")
        return "\n".join(lines)

    lines.append("### 样本充分性")
    lines.append("| 信号域 | present | missing | insufficient | observation |")
    lines.append("|--------|---------|---------|--------------|-------------|")
    for domain in ADAPTIVE_GATE_SIGNAL_DOMAINS:
        counts = report.source_status_counts.get(domain, {})
        lines.append(
            f"| {domain} | {counts.get('present', 0)} | {counts.get('missing', 0)} "
            f"| {counts.get('insufficient', 0)} | {counts.get('observation', 0)} |"
        )
    lines.append("")

    if not report.windows:
        lines.append(
            f"（快照数 {report.snapshot_count}，不足 W={report.window_size}，不生成窗口）"
        )
        return "\n".join(lines)

    lines.append("### Continuity / Orphan 窗口")
    lines.append(
        "| 窗口 | health_min | health_median | P1_median | orphan_slope "
        "| orphan_delta | new_critical_mean |"
    )
    lines.append(
        "|------|------------|---------------|-----------|--------------"
        "|--------------|-------------------|"
    )
    for window in report.windows:
        lines.append(
            f"| {window.start_chapter}-{window.end_chapter} "
            f"| {_fmt(window.health_min)} | {_fmt(window.health_median)} "
            f"| {_fmt(window.p1_median)} | {_fmt(window.orphan_slope)} "
            f"| {_fmt(window.orphan_delta)} | {_fmt(window.new_critical_mean)} |"
        )
    lines.append("")

    lines.append("### Quality Debt 窗口")
    lines.append("| 窗口 | degraded% | convergence% | qg_false% |")
    lines.append("|------|-----------|--------------|-----------|")
    for window in report.windows:
        lines.append(
            f"| {window.start_chapter}-{window.end_chapter} "
            f"| {_fmt(window.degraded_ratio, percent=True)} "
            f"| {_fmt(window.convergence_ratio, percent=True)} "
            f"| {_fmt(window.qg_false_ratio, percent=True)} |"
        )
    lines.append("")

    lines.append("### Literary / Cleanliness 窗口")
    lines.append("| 窗口 | literary | conceptual | meta | duplicate | timeline(obs) |")
    lines.append("|------|----------|------------|------|-----------|---------------|")
    for window in report.windows:
        lines.append(
            f"| {window.start_chapter}-{window.end_chapter} "
            f"| {_fmt(window.literary_quality_mean)} "
            f"| {_fmt(window.conceptual_grounding_mean)} "
            f"| {window.meta_tag_leak_total} | {window.duplicate_paragraph_total} "
            f"| {window.timeline_conflict_total} |"
        )
    lines.append("")

    lines.append("### Schedule Lifecycle 窗口")
    lines.append("| 窗口 | injected | satisfied | missed | hit_rate | missed_rate | overdue_rate |")
    lines.append("|------|----------|-----------|--------|----------|-------------|--------------|")
    for window in report.windows:
        lines.append(
            f"| {window.start_chapter}-{window.end_chapter} "
            f"| {window.schedule_injected_count} | {window.schedule_satisfied_count} "
            f"| {window.schedule_missed_count} "
            f"| {_fmt(window.schedule_hit_rate, percent=True)} "
            f"| {_fmt(window.schedule_missed_rate, percent=True)} "
            f"| {_fmt(window.schedule_overdue_rate, percent=True)} |"
        )
    lines.append("")

    lines.append("### Context / T5 压力")
    lines.append("| 窗口 | context_emergency% | budget_max | db_max_mb | scan_max_ms |")
    lines.append("|------|--------------------|------------|-----------|-------------|")
    for window in report.windows:
        lines.append(
            f"| {window.start_chapter}-{window.end_chapter} "
            f"| {_fmt(window.context_emergency_ratio, percent=True)} "
            f"| {_fmt(window.budget_used_max)} | {_fmt(window.db_size_max_mb)} "
            f"| {_fmt(window.scan_latency_max_ms)} |"
        )
    return "\n".join(lines)
