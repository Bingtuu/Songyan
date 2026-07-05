"""DB-backed long-form metrics for V6 Stage A (Task 145+).

Derive-on-read collectors that read the SQLite fact source (via the current
``settings.database_url``, so ``DATABASE_URL`` override targets historical DBs)
and produce per-chapter metric curves for the ``songyan metrics`` command.

Task 145 implements orphan-absolute + new-critical-rate (T7). Tasks 146/147/148
extend this module with quality-debt, literary-trend, and foreshadowing metrics.
"""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from pathlib import Path

from pydantic import BaseModel

from songyan.db.continuity_repo import (
    ContinuityReportRepository,
    SettingTrackingRepository,
)
from songyan.db.narrative_repo import NarrativeRepository
from songyan.db.review_repo import LiteraryObservationRepository
from songyan.db.run_db_metrics_repo import RunDbMetricsRepository
from songyan.db.run_quality_debt_repo import RunQualityDebtRepository, RunQualityDebtRow
from songyan.db.settlement_repo import ForeshadowingRepository
from songyan.evals.concept_budget import (
    collect_concept_budget_report,
    render_concept_budget_section,
)
from songyan.evals.db_maintenance_metrics import (
    DbSizeMetrics,
    analyze_t5_latency_samples,
    check_t5_size_redline,
)
from songyan.evals.text_cleanliness import (
    refresh_text_cleanliness_metrics,
    render_text_cleanliness_section,
)
from songyan.evals.timeline_consistency import (
    collect_timeline_conflicts,
    render_timeline_consistency_section,
)
from songyan.models.run_log import ChapterRunLog

# --------------------------------------------------------------------------- #
# Row models
# --------------------------------------------------------------------------- #


class OrphanPoint(BaseModel):
    """逐章 orphan 计数（直接统计 report.orphaned_settings 的 category）.

    不变量：orphan_critical + orphan_recurring + orphan_other == orphan_total。
    """

    chapter: int
    orphan_total: int
    orphan_critical: int      # category == 'critical'
    orphan_recurring: int     # category == 'recurring'
    orphan_other: int         # background / technical / historical（v6-plan 口径 P3）
    forgotten_items: int = 0  # 独立计数（非 orphaned_settings）


class CriticalRatePoint(BaseModel):
    """逐章新设定写入速率（T7 = new_critical/章，写入侧）."""

    chapter: int
    new_critical: int
    new_total: int


class SettingLifecycleMetrics(BaseModel):
    """setting_tracking 生命周期分布（Task 152：区分显式 resolve/abandon 与归档）."""

    active_count: int
    resolved_count: int      # status == 'resolved'：剧情已交代收束
    abandoned_count: int     # status == 'abandoned'：显式废弃
    archived_count: int      # status == 'archived'：逾期/被遗忘


# --------------------------------------------------------------------------- #
# Collectors
# --------------------------------------------------------------------------- #


async def collect_orphan_metrics(
    project_id: str,
    start: int,
    end: int,
    repo: ContinuityReportRepository | None = None,
) -> list[OrphanPoint]:
    """从 continuity_reports 逐章还原 orphan 绝对量与分类分布.

    每个 ``checked_up_to_chapter`` 取最新一条 report（list_by_chapter_range 按章升序，
    同章多条时取最后一条），直接统计其 ``orphaned_settings`` 的 category。
    不使用 ``classify_report``（它聚合了 state_mismatches/forgotten_items，会污染 orphan 口径）。
    """
    repo = repo or ContinuityReportRepository()
    reports = await repo.list_by_chapter_range(project_id, start, end)

    latest_by_chapter: dict[int, object] = {}
    for report in reports:
        latest_by_chapter[report.checked_up_to_chapter] = report

    points: list[OrphanPoint] = []
    for chapter in sorted(latest_by_chapter):
        report = latest_by_chapter[chapter]
        critical = recurring = other = 0
        for setting in report.orphaned_settings:  # type: ignore[attr-defined]
            cat = getattr(setting, "category", "background")
            if cat == "critical":
                critical += 1
            elif cat == "recurring":
                recurring += 1
            else:
                other += 1
        points.append(
            OrphanPoint(
                chapter=chapter,
                orphan_total=len(report.orphaned_settings),  # type: ignore[attr-defined]
                orphan_critical=critical,
                orphan_recurring=recurring,
                orphan_other=other,
                forgotten_items=len(report.forgotten_items),  # type: ignore[attr-defined]
            )
        )
    return points


async def collect_new_critical_rate(
    project_id: str,
    start: int,
    end: int,
    repo: SettingTrackingRepository | None = None,
) -> list[CriticalRatePoint]:
    """从 setting_tracking 逐章还原新 critical 设定产生速率（T7，写入侧）."""
    repo = repo or SettingTrackingRepository()
    rows = await repo.new_settings_by_chapter(project_id, start, end)

    critical_by_chapter: dict[int, int] = {}
    total_by_chapter: dict[int, int] = {}
    for row in rows:
        chapter = int(row["introduced_in_chapter"])
        count = int(row["count"])
        total_by_chapter[chapter] = total_by_chapter.get(chapter, 0) + count
        if row["category"] == "critical":
            critical_by_chapter[chapter] = critical_by_chapter.get(chapter, 0) + count

    return [
        CriticalRatePoint(
            chapter=chapter,
            new_critical=critical_by_chapter.get(chapter, 0),
            new_total=total_by_chapter[chapter],
        )
        for chapter in sorted(total_by_chapter)
    ]


async def collect_setting_lifecycle_metrics(
    project_id: str,
    repo: SettingTrackingRepository | None = None,
) -> SettingLifecycleMetrics:
    """统计 setting_tracking 各终态数量，区分显式回收与逾期归档."""
    repo = repo or SettingTrackingRepository()
    rows = await repo.list_by_project(project_id)
    counts = Counter(str(row.get("status", "active")) for row in rows)
    return SettingLifecycleMetrics(
        active_count=counts.get("active", 0),
        resolved_count=counts.get("resolved", 0),
        abandoned_count=counts.get("abandoned", 0),
        archived_count=counts.get("archived", 0),
    )


# --------------------------------------------------------------------------- #
# Slope + rendering
# --------------------------------------------------------------------------- #


def linear_slope(xs: list[int], ys: list[float]) -> float:
    """最小二乘线性斜率；点数 < 2 或 x 无方差时返回 0.0."""
    n = len(xs)
    if n < 2:
        return 0.0
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    denom = sum((x - mean_x) ** 2 for x in xs)
    if denom == 0:
        return 0.0
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=False))
    return num / denom


def render_orphan_section(points: list[OrphanPoint]) -> str:
    lines = ["## orphan 绝对量（total / critical / recurring / other）", ""]
    if not points:
        lines.append("（无 continuity_reports 数据）")
        return "\n".join(lines)
    lines.append("| 章 | total | critical | recurring | other | forgotten |")
    lines.append("|----|-------|----------|-----------|-------|-----------|")
    for p in points:
        lines.append(
            f"| {p.chapter} | {p.orphan_total} | {p.orphan_critical} "
            f"| {p.orphan_recurring} | {p.orphan_other} | {p.forgotten_items} |"
        )
    slope = linear_slope([p.chapter for p in points], [float(p.orphan_total) for p in points])
    max_critical = max(p.orphan_critical for p in points)
    lines.append("")
    lines.append(f"- orphan 总量线性斜率：**{slope:.4f}**/章")
    lines.append(f"- P1(critical) orphan 峰值：**{max_critical}**（T6(b) 要求全程 =0）")
    return "\n".join(lines)


def render_critical_rate_section(points: list[CriticalRatePoint]) -> str:
    lines = ["## 每章新 critical 产生速率（T7，写入侧）", ""]
    if not points:
        lines.append("（无 setting_tracking 数据）")
        return "\n".join(lines)
    lines.append("| 章 | new_critical | new_total |")
    lines.append("|----|--------------|-----------|")
    for p in points:
        lines.append(f"| {p.chapter} | {p.new_critical} | {p.new_total} |")
    total_critical = sum(p.new_critical for p in points)
    n = len(points)
    avg = total_critical / n if n else 0.0
    lines.append("")
    lines.append(f"- 新 critical 合计：**{total_critical}**；每章均值（T7）：**{avg:.3f}**")
    return "\n".join(lines)


def render_setting_lifecycle_section(metrics: SettingLifecycleMetrics | None) -> str:
    lines = ["## setting 生命周期分布（显式 resolve / 显式 abandon / 逾期归档）", ""]
    if metrics is None:
        lines.append("（无 setting_tracking 数据）")
        return "\n".join(lines)
    lines.append(f"- active（仍在监测）：**{metrics.active_count}**")
    lines.append(f"- resolved（显式剧情收束）：**{metrics.resolved_count}**")
    lines.append(f"- abandoned（显式废弃）：**{metrics.abandoned_count}**")
    lines.append(f"- archived（逾期/被遗忘）：**{metrics.archived_count}**")
    return "\n".join(lines)


async def _guard(awaitable, fallback):
    """执行 collector；表缺失（历史 DB 无该 V6 表）时返回 fallback（优雅降级）."""
    try:
        return await awaitable
    except sqlite3.OperationalError:
        return fallback


async def render_stage_a_metrics(project_id: str, start: int, end: int) -> str:
    """组装 Stage A 度量 markdown（145 orphan/T7 + 146 质量债 + 147 文学趋势 + 148 伏笔）.

    每个 collector 独立降级：历史 DB 缺某张 V6 表时只跳过对应段，不影响其余段。
    """
    orphan_points = await _guard(collect_orphan_metrics(project_id, start, end), [])
    critical_points = await _guard(collect_new_critical_rate(project_id, start, end), [])
    lifecycle = await _guard(collect_setting_lifecycle_metrics(project_id), None)
    debt_rows = await _guard(RunQualityDebtRepository().list_by_project(project_id), [])
    literary_points = await _guard(collect_literary_scores(project_id, start, end), [])
    literary_trend = detect_literary_trend(literary_points)
    arc_fulfillment = await _guard(collect_arc_fulfillment(project_id), [])
    ledger = await _guard(collect_long_range_ledger(project_id, end), [])
    db_samples = await _guard(collect_db_maintenance_samples(project_id, start, end), [])
    timeline = await _guard(collect_timeline_conflicts(project_id, start, end), ({}, []))
    concept_budget = await _guard(collect_concept_budget_report(project_id, end), None)
    text_cleanliness = await _guard(
        refresh_text_cleanliness_metrics(project_id, start, end), []
    )
    from songyan.evals.adaptive_gate import (
        build_adaptive_gate_data_plane_report,
        refresh_adaptive_gate_signal_snapshots,
        render_adaptive_gate_data_plane_section,
    )
    await _guard(refresh_adaptive_gate_signal_snapshots(project_id, start, end), 0)
    adaptive_gate_report = await _guard(
        build_adaptive_gate_data_plane_report(project_id, start, end), None
    )
    # 局部导入避免与 v6_acceptance 循环引用（v6_acceptance 已导入本模块）
    from songyan.evals.v6_acceptance import evaluate_v6_acceptance, render_v6_acceptance_section
    acceptance = await _guard(evaluate_v6_acceptance(project_id, start, end), None)
    header = f"# V6 阶段 A 度量报告 — 项目 {project_id}（Ch{start}-Ch{end}）\n"
    sections = [
        header,
        render_setting_lifecycle_section(lifecycle),
        render_orphan_section(orphan_points),
        render_critical_rate_section(critical_points),
        render_run_quality_debt_section(debt_rows),
        render_literary_section(literary_points, literary_trend),
        render_arc_fulfillment_section(arc_fulfillment),
        render_foreshadowing_ledger_section(ledger),
        render_db_maintenance_section(db_samples),
        render_timeline_consistency_section(timeline[0], timeline[1]),
        render_concept_budget_section(concept_budget),
        render_text_cleanliness_section(text_cleanliness),
    ]
    if adaptive_gate_report is not None:
        sections.append(render_adaptive_gate_data_plane_section(adaptive_gate_report))
    if acceptance is not None:
        sections.append(render_v6_acceptance_section(acceptance))
    return "\n\n".join(sections)


# --------------------------------------------------------------------------- #
# 质量债账本（Task 146）
# --------------------------------------------------------------------------- #

# T4 红线：50 章窗内 degraded 占比 ≤20% 且 convergence 占比 ≤10%（超出即破）
_T4_DEGRADED_MAX = 0.20
_T4_CONVERGENCE_MAX = 0.10


class QualityDebtWindow(BaseModel):
    start_chapter: int
    end_chapter: int
    degraded_ratio: float
    convergence_ratio: float
    t4_breached: bool


class QualityDebtReport(BaseModel):
    total_chapters: int
    degraded_chapters: list[int]
    convergence_failed_chapters: list[int]
    qg_false_chapters: list[int]
    degraded_ratio: float
    convergence_ratio: float
    windows: list[QualityDebtWindow]
    t4_breached: bool
    window_size: int = 50
    window_sufficient: bool = False


def _window_breached(degraded_ratio: float, convergence_ratio: float) -> bool:
    return degraded_ratio > _T4_DEGRADED_MAX or convergence_ratio > _T4_CONVERGENCE_MAX


def compute_quality_debt(logs: list[ChapterRunLog], window: int = 50) -> QualityDebtReport:
    """跨章聚合质量债：degraded_accept / convergence_failed / quality_gate_passed=false.

    50 章滑窗按 T4 判定（degraded ≤20% 且 convergence ≤10%）；总章数不足 window 时
    不产出窗口（window_sufficient=False），避免小样本误判红线。
    """
    ordered = sorted(logs, key=lambda item: item.chapter_number)
    total = len(ordered)

    degraded = [item.chapter_number for item in ordered if item.degraded_accept]
    convergence = [item.chapter_number for item in ordered if item.convergence_failed]
    qg_false = [
        item.chapter_number for item in ordered if item.quality_gate_passed is False
    ]

    degraded_ratio = len(degraded) / total if total else 0.0
    convergence_ratio = len(convergence) / total if total else 0.0

    windows: list[QualityDebtWindow] = []
    window_sufficient = total >= window
    if window_sufficient:
        for i in range(total - window + 1):
            chunk = ordered[i : i + window]
            d_ratio = sum(1 for item in chunk if item.degraded_accept) / window
            c_ratio = sum(1 for item in chunk if item.convergence_failed) / window
            windows.append(
                QualityDebtWindow(
                    start_chapter=chunk[0].chapter_number,
                    end_chapter=chunk[-1].chapter_number,
                    degraded_ratio=d_ratio,
                    convergence_ratio=c_ratio,
                    t4_breached=_window_breached(d_ratio, c_ratio),
                )
            )

    return QualityDebtReport(
        total_chapters=total,
        degraded_chapters=degraded,
        convergence_failed_chapters=convergence,
        qg_false_chapters=qg_false,
        degraded_ratio=degraded_ratio,
        convergence_ratio=convergence_ratio,
        windows=windows,
        t4_breached=any(w.t4_breached for w in windows),
        window_size=window,
        window_sufficient=window_sufficient,
    )


def quality_debt_row(run_id: str, project_id: str, report: QualityDebtReport) -> RunQualityDebtRow:
    """把 QualityDebtReport 折成一行 run 级汇总（供 run_quality_debt upsert）."""
    return RunQualityDebtRow(
        run_id=run_id,
        project_id=project_id,
        total_chapters=report.total_chapters,
        degraded_count=len(report.degraded_chapters),
        convergence_failed_count=len(report.convergence_failed_chapters),
        qg_false_count=len(report.qg_false_chapters),
        degraded_ratio=report.degraded_ratio,
        convergence_ratio=report.convergence_ratio,
        t4_breached=report.t4_breached,
    )


def quality_debt_from_metrics_jsonl(path: str | Path, window: int = 50) -> QualityDebtReport:
    """一次性适配器：从 .tmp/*_per_chapter_metrics.jsonl 计算质量债（仅 qg_false 口径）.

    历史导出的 jsonl 不含 degraded_accept/convergence_failed（仅 quality_gate_passed），
    故 degraded/convergence 恒为 0；仅供标定报告的 qg_false 参考分布，不作它用。
    """
    from datetime import datetime

    logs: list[ChapterRunLog] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        data = json.loads(line)
        chapter = int(data.get("chapter", 0))
        logs.append(
            ChapterRunLog(
                log_id=f"jsonl-{chapter}",
                project_id="",
                chapter_number=chapter,
                started_at=datetime.now(),
                finished_at=datetime.now(),
                success=bool(data.get("accepted", data.get("success", True))),
                quality_gate_passed=data.get("quality_gate_passed"),
            )
        )
    return compute_quality_debt(logs, window=window)


def render_run_quality_debt_section(rows: list[RunQualityDebtRow]) -> str:
    lines = ["## 质量债账本（run 级；T4：50 章窗 degraded ≤20% 且 convergence ≤10%）", ""]
    if not rows:
        lines.append("（无 run 质量债记录：历史 DB 或该项目尚无 run）")
        return "\n".join(lines)
    lines.append("| run | 章数 | degraded | conv_failed | QG=false | degraded% | conv% | T4 |")
    lines.append("|-----|------|----------|-------------|----------|-----------|-------|----|")
    for r in rows:
        flag = "🔴 破线" if r.t4_breached else "✓"
        lines.append(
            f"| {r.run_id} | {r.total_chapters} | {r.degraded_count} "
            f"| {r.convergence_failed_count} | {r.qg_false_count} "
            f"| {r.degraded_ratio:.1%} | {r.convergence_ratio:.1%} | {flag} |"
        )
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# 文学质量趋势化（Task 147）
# --------------------------------------------------------------------------- #

_LITERARY_DIMS = (
    "literary_quality_score",
    "character_autonomy_score",
    "conceptual_grounding_score",
    "fissure_preservation_score",
)


class LiteraryScorePoint(BaseModel):
    chapter: int
    literary_quality_score: float
    character_autonomy_score: float
    conceptual_grounding_score: float
    fissure_preservation_score: float


class LiteraryTrendResult(BaseModel):
    baseline_available: bool
    baseline: dict[str, float]
    breached_dimensions: list[str]
    first_breach_window: dict[str, int | None]
    windows: dict[str, list[float]]


async def collect_literary_scores(
    project_id: str,
    start: int,
    end: int,
    repo: LiteraryObservationRepository | None = None,
) -> list[LiteraryScorePoint]:
    """逐章回读文学四维度分数（每章取最新一条 observation）."""
    repo = repo or LiteraryObservationRepository()
    rows = await repo.list_scores_by_chapter_range(project_id, start, end)
    points = [
        LiteraryScorePoint(
            chapter=int(row["chapter"]),
            literary_quality_score=float(row["literary_quality_score"] or 0.0),
            character_autonomy_score=float(row["character_autonomy_score"] or 0.0),
            conceptual_grounding_score=float(row["conceptual_grounding_score"] or 0.0),
            fissure_preservation_score=float(row["fissure_preservation_score"] or 0.0),
        )
        for row in rows
    ]
    points.sort(key=lambda p: p.chapter)
    return points


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def detect_literary_trend(
    points: list[LiteraryScorePoint],
    *,
    baseline_n: int = 10,
    window: int = 5,
    drop: float = 0.20,
) -> LiteraryTrendResult:
    """T3/T8：某维度 W=5 滑窗均值相对前 baseline_n 章基线下降 ≥drop 即触红线.

    基线不足 baseline_n 章时 baseline_available=False，不判红线（避免小样本误判）。
    """
    ordered = sorted(points, key=lambda p: p.chapter)
    baseline_available = len(ordered) >= baseline_n

    baseline: dict[str, float] = {}
    windows: dict[str, list[float]] = {}
    breached: list[str] = []
    first_breach: dict[str, int | None] = {}

    for dim in _LITERARY_DIMS:
        series = [getattr(p, dim) for p in ordered]
        win_means: list[float] = []
        if len(series) >= window:
            for i in range(len(series) - window + 1):
                win_means.append(_mean(series[i : i + window]))
        windows[dim] = win_means
        first_breach[dim] = None

        if not baseline_available:
            baseline[dim] = 0.0
            continue

        base = _mean(series[:baseline_n])
        baseline[dim] = base
        threshold = base * (1 - drop)
        for idx, wmean in enumerate(win_means):
            if wmean <= threshold:
                breached.append(dim)
                first_breach[dim] = ordered[idx].chapter
                break

    return LiteraryTrendResult(
        baseline_available=baseline_available,
        baseline=baseline,
        breached_dimensions=breached,
        first_breach_window=first_breach,
        windows=windows,
    )


def render_literary_section(
    points: list[LiteraryScorePoint], trend: LiteraryTrendResult
) -> str:
    lines = ["## 文学质量趋势（T3：W=5 均值相对前 10 章基线降 ≥20%；只诊断不阻断）", ""]
    if not points:
        lines.append("（无 literary_observations 数据）")
        return "\n".join(lines)
    lines.append("| 章 | literary | char_autonomy | conceptual | fissure |")
    lines.append("|----|----------|---------------|------------|---------|")
    for p in points:
        lines.append(
            f"| {p.chapter} | {p.literary_quality_score:.2f} "
            f"| {p.character_autonomy_score:.2f} | {p.conceptual_grounding_score:.2f} "
            f"| {p.fissure_preservation_score:.2f} |"
        )
    lines.append("")
    if not trend.baseline_available:
        lines.append("- 基线不足（< 10 章），暂不判 T3 红线")
    elif trend.breached_dimensions:
        for dim in trend.breached_dimensions:
            lines.append(
                f"- 🔴 T3 触线维度 **{dim}**：首个触线窗口起始 Ch{trend.first_breach_window[dim]}"
                f"（基线 {trend.baseline[dim]:.2f}）"
            )
    else:
        lines.append("- ✓ 无维度触 T3 红线")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# 弧级伏笔兑现率 + 长程伏笔台账（Task 148）
# --------------------------------------------------------------------------- #

# 逾期归档（非真兑现）的 lifecycle 状态
_ABANDONED_LIFECYCLE = ("dormant", "archived")


class ArcFulfillment(BaseModel):
    arc_index: int
    start_chapter: int
    end_chapter: int
    total: int
    resolved: int
    abandoned: int
    fulfillment_rate: float  # resolved / total（total=0 时 0.0）


class ForeshadowingLedgerRow(BaseModel):
    foreshadowing_id: str
    description: str
    planted_in_chapter: int
    expected_resolve_chapter: int | None
    span: int
    status: str
    is_abandoned: bool


def _is_abandoned(status: str, lifecycle_status: str) -> bool:
    """逾期归档（非真兑现）：非 resolved 且 lifecycle 已 dormant/archived."""
    return status != "resolved" and lifecycle_status in _ABANDONED_LIFECYCLE


async def collect_arc_fulfillment(
    project_id: str,
    narrative_repo: NarrativeRepository | None = None,
    foreshadowing_repo: ForeshadowingRepository | None = None,
) -> list[ArcFulfillment]:
    """弧级伏笔兑现率：按 planted_in_chapter 落入 ArcPlan 章节范围桶化.

    无 arc_plans（历史 DB / 无大纲）时返回空列表（优雅降级）。
    """
    nrepo = narrative_repo or NarrativeRepository()
    arcs = await nrepo.list_arc_plans(project_id)
    if not arcs:
        return []
    frepo = foreshadowing_repo or ForeshadowingRepository()
    rows = await frepo.list_with_lifecycle(project_id)

    result: list[ArcFulfillment] = []
    for arc in arcs:
        bucket = [
            r for r in rows
            if arc.start_chapter <= r["planted_in_chapter"] <= arc.end_chapter
        ]
        total = len(bucket)
        resolved = sum(1 for r in bucket if r["status"] == "resolved")
        abandoned = sum(
            1 for r in bucket if _is_abandoned(r["status"], r["lifecycle_status"])
        )
        result.append(
            ArcFulfillment(
                arc_index=arc.arc_index,
                start_chapter=arc.start_chapter,
                end_chapter=arc.end_chapter,
                total=total,
                resolved=resolved,
                abandoned=abandoned,
                fulfillment_rate=(resolved / total if total else 0.0),
            )
        )
    return result


async def collect_long_range_ledger(
    project_id: str,
    current_chapter: int,
    foreshadowing_repo: ForeshadowingRepository | None = None,
) -> list[ForeshadowingLedgerRow]:
    """长程未兑现伏笔台账：所有 status != 'resolved' 的伏笔 + span + 逾期归档标记."""
    frepo = foreshadowing_repo or ForeshadowingRepository()
    rows = await frepo.list_with_lifecycle(project_id)
    ledger: list[ForeshadowingLedgerRow] = []
    for r in rows:
        if r["status"] == "resolved":
            continue
        ledger.append(
            ForeshadowingLedgerRow(
                foreshadowing_id=r["foreshadowing_id"],
                description=r["description"] or "",
                planted_in_chapter=r["planted_in_chapter"],
                expected_resolve_chapter=r["expected_resolve_chapter"],
                span=current_chapter - r["planted_in_chapter"],
                status=r["status"],
                is_abandoned=_is_abandoned(r["status"], r["lifecycle_status"]),
            )
        )
    return ledger


def render_arc_fulfillment_section(arcs: list[ArcFulfillment]) -> str:
    lines = ["## 弧级伏笔兑现率（fulfilled ⇔ status=resolved）", ""]
    if not arcs:
        lines.append("（无 arc_plans：历史 DB 或无大纲项目）")
        return "\n".join(lines)
    lines.append("| 弧 | 章范围 | total | resolved | abandoned | 兑现率 |")
    lines.append("|----|--------|-------|----------|-----------|--------|")
    for a in arcs:
        lines.append(
            f"| {a.arc_index} | {a.start_chapter}-{a.end_chapter} | {a.total} "
            f"| {a.resolved} | {a.abandoned} | {a.fulfillment_rate:.1%} |"
        )
    return "\n".join(lines)


def render_foreshadowing_ledger_section(rows: list[ForeshadowingLedgerRow]) -> str:
    lines = ["## 长程伏笔台账（未兑现；abandoned=逾期归档，被系统遗忘）", ""]
    if not rows:
        lines.append("（无未兑现伏笔）")
        return "\n".join(lines)
    abandoned = sum(1 for r in rows if r.is_abandoned)
    lines.append(f"- 未兑现合计 **{len(rows)}**，其中被遗忘（逾期归档）**{abandoned}**")
    lines.append("")
    lines.append("| id | planted | expected | span | status | 被遗忘 |")
    lines.append("|----|---------|----------|------|--------|--------|")
    for r in rows:
        exp = r.expected_resolve_chapter if r.expected_resolve_chapter is not None else "-"
        mark = "🔴" if r.is_abandoned else ""
        lines.append(
            f"| {r.foreshadowing_id} | {r.planted_in_chapter} | {exp} "
            f"| {r.span} | {r.status} | {mark} |"
        )
    return "\n".join(lines)


async def collect_db_maintenance_samples(
    project_id: str,
    start: int,
    end: int,
    repo: RunDbMetricsRepository | None = None,
) -> list[dict]:
    """读取 run_db_metrics 遥测样本，按章范围过滤."""
    repo = repo or RunDbMetricsRepository()
    return await repo.list_by_project(project_id, chapter_start=start, chapter_end=end)


def render_db_maintenance_section(samples: list[dict]) -> str:
    """T5：DB 尺寸与连续性扫描耗时红线判定."""
    lines = ["## DB 维护遥测（T5：尺寸 ≤300MB；扫描耗时 ≤ 中位数×2.0）", ""]
    if not samples:
        lines.append("（无 run_db_metrics 遥测样本）")
        return "\n".join(lines)

    latency = analyze_t5_latency_samples(samples)
    hard_latency = set(latency.hard_breach_chapters)
    observed_latency = set(latency.observed_breach_chapters)

    lines.append("| 章 | DB(MB) | WAL(KB) | pages | scan(ms) | 尺寸红线 | 耗时状态 |")
    lines.append("|----|--------|---------|-------|----------|----------|----------|")

    size_breaches: list[int] = []
    for s in samples:
        chapter = int(s["chapter_number"])
        db_mb = int(s["db_size_bytes"]) / (1024 * 1024)
        wal_kb = int(s["wal_size_bytes"]) / 1024
        scan_ms = float(s["scan_latency_ms"])
        size_red = check_t5_size_redline(
            DbSizeMetrics(
                db_size_bytes=int(s["db_size_bytes"]),
                wal_size_bytes=int(s["wal_size_bytes"]),
                page_count=int(s["page_count"]),
                page_size=int(s["page_size"]),
            )
        )
        if size_red:
            size_breaches.append(chapter)
        if chapter in hard_latency:
            latency_flag = "🔴 hard"
        elif chapter in observed_latency:
            latency_flag = "△ observe"
        else:
            latency_flag = "✓"
        lines.append(
            f"| {chapter} | {db_mb:.2f} | {wal_kb:.1f} "
            f"| {s['page_count']} | {scan_ms:.3f} | "
            f"{'🔴' if size_red else '✓'} | {latency_flag} |"
        )

    lines.append("")
    lines.append(
        f"- 扫描耗时基线（{latency.baseline_sample_count} 个章级样本中位数）："
        f"**{latency.baseline_ms:.3f} ms**；hard 阈值："
        f"**{latency.threshold_ms:.3f} ms**"
    )
    if size_breaches:
        lines.append(f"- 🔴 DB 尺寸超 300MB 样本章：{size_breaches}")
    else:
        lines.append("- ✓ DB 尺寸未超 300MB 红线")
    if latency.hard_breach_chapters:
        lines.append(f"- 🔴 扫描耗时 hard 破线章：{latency.hard_breach_chapters}")
    else:
        lines.append("- ✓ 扫描耗时无连续/极端 hard 破线")
    if latency.observed_breach_chapters:
        lines.append(f"- △ 扫描耗时观察章：{latency.observed_breach_chapters}")
    return "\n".join(lines)
