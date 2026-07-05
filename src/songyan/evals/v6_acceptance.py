"""V6 阶段 D 验收判据 harness（Task 157a）.

把 §1.4 的 T1-T8 红线从散文/报告表格收敛为可单测的函数，
供 157/158/159 三个长窗口复用，避免阈值漂移。

所有判据只读 SQLite + run log，不改治理/门禁/Agent，无 LLM 调用。
"""

from __future__ import annotations

from pydantic import BaseModel

from songyan.agents.continuity_auditor.continuity_health import (
    collect_continuity_health_metrics,
)
from songyan.db.continuity_repo import (
    ContinuityReportRepository,
    SettingTrackingRepository,
)
from songyan.db.narrative_repo import NarrativeRepository
from songyan.db.repository import ChapterHeadRepository
from songyan.db.run_db_metrics_repo import RunDbMetricsRepository
from songyan.evals.db_maintenance_metrics import (
    DbSizeMetrics,
    analyze_t5_latency_samples,
    check_t5_size_redline,
)
from songyan.evals.db_metrics import (
    _T4_CONVERGENCE_MAX,
    _T4_DEGRADED_MAX,
    ChapterRunLog,
    collect_literary_scores,
    collect_new_critical_rate,
    collect_orphan_metrics,
    compute_quality_debt,
    detect_literary_trend,
    linear_slope,
)
from songyan.evals.text_cleanliness import collect_text_cleanliness_metrics

# --------------------------------------------------------------------------- #
# 阈值常量（出处见 docs/v6-plan.md §1.4 与 tasks/148z-stage-a-threshold-calibration-DONE.md）
# --------------------------------------------------------------------------- #

# T6a: Ch50-100 窗 orphan 总量线性斜率 ≤ 3.14/章（=138n 基线 6.2836 × 0.5）
_T6A_ORPHAN_SLOPE_THRESHOLD = 3.14
_T6A_ORPHAN_SLOPE_BASELINE = 6.2836  # 138n Ch1-Ch30 rerun

# T6c: T7 新 critical 速率基线 1.767/章（138k rehearsal）
_T6C_T7_RATE_BASELINE = 1.767
_T6C_ATTRIBUTION_RATIO = 0.5  # T7 降幅 ≥ orphan 斜率降幅的 50%

# T6c-obs: 被降级为 candidate 的 critical ≤ 同窗新增 critical 总数 15%
_T6C_OBS_MAX_RATIO = 0.15

_MIN_ORPHAN_POINTS = 3
_MIN_T7_POINTS = 1
_MIN_T5_SAMPLES = 3
_T6C_SMALL_T7_RATE = 0.1

# T2: 项目 chapter_heads.status 当前只支持 accepted（无 edited）
_COMPLETING_STATUSES = ("accepted",)


# --------------------------------------------------------------------------- #
# 结果模型
# --------------------------------------------------------------------------- #


class ThresholdResult(BaseModel):
    """单项判据结果（三态：通过 / 未通过 / 样本不足未判定）."""

    key: str
    passed: bool | None
    measured: float | str | None
    threshold: float | str | None
    sufficient: bool
    detail: str


class V6AcceptanceResult(BaseModel):
    """聚合判据结果."""

    project_id: str
    chapter_start: int
    chapter_end: int
    results: list[ThresholdResult]
    all_passed: bool
    undecided: list[str]


# --------------------------------------------------------------------------- #
# 单项判据
# --------------------------------------------------------------------------- #


async def check_t1(
    project_id: str,
    start: int,
    end: int,
    narrative_repo: NarrativeRepository | None = None,
) -> ThresholdResult:
    """T1: 至少一条 is_mainline PlotThread 在窗口内发生可追溯状态跃迁.

    跃迁定义：status 由 opened→advanced 或 advanced→resolved，
    且 last_status_chapter > opened_chapter、last_status_version_id 非空。
    """
    repo = narrative_repo or NarrativeRepository()
    threads = await repo.list_threads(project_id)
    mainline = [t for t in threads if t.is_mainline]

    advanced_threads: list[str] = []
    for t in mainline:
        if t.status in ("advanced", "resolved") and t.opened_chapter is not None:
            if (
                t.last_status_chapter is not None
                and t.last_status_chapter > t.opened_chapter
                and t.last_status_version_id
                and start <= t.last_status_chapter <= end
            ):
                advanced_threads.append(
                    f"{t.thread_id}(Ch{t.opened_chapter}→Ch{t.last_status_chapter})"
                )

    passed = bool(advanced_threads)
    return ThresholdResult(
        key="T1",
        passed=passed,
        measured=len(advanced_threads),
        threshold="≥1 mainline thread advanced/resolved",
        sufficient=bool(mainline),
        detail=(
            f"主线线索 {len(mainline)} 条，跃迁 {len(advanced_threads)} 条"
            f"{': ' + ', '.join(advanced_threads) if advanced_threads else ''}"
        ),
    )


async def check_t2(
    project_id: str,
    start: int,
    end: int,
    chapter_head_repo: ChapterHeadRepository | None = None,
) -> ThresholdResult:
    """T2: 目标区间每章都有 accepted head.

    当前 chapter_heads.status 取值只有 draft/under_review/accepted（无 edited），
    因此只认 accepted；若未来增加 edited，可在此扩展 _COMPLETING_STATUSES。
    """
    repo = chapter_head_repo or ChapterHeadRepository()
    heads = await repo.list_by_project(project_id)
    in_range = {h.chapter_number: h for h in heads if start <= h.chapter_number <= end}

    expected = list(range(start, end + 1))
    accepted_chapters = [
        ch for ch, h in in_range.items() if h.status in _COMPLETING_STATUSES
    ]
    missing = [ch for ch in expected if ch not in in_range]
    not_accepted = [
        ch for ch, h in in_range.items() if h.status not in _COMPLETING_STATUSES
    ]

    sufficient = len(in_range) > 0
    passed = sufficient and not missing and not not_accepted
    return ThresholdResult(
        key="T2",
        passed=passed if sufficient else None,
        measured=f"{len(accepted_chapters)}/{len(expected)}",
        threshold=f"{len(expected)}/{len(expected)} accepted",
        sufficient=sufficient,
        detail=(
            f"accepted {len(accepted_chapters)} 章"
            f"{'; 缺口: ' + ', '.join(map(str, missing)) if missing else ''}"
            f"{'; 未 accept: ' + ', '.join(map(str, not_accepted)) if not_accepted else ''}"
        ),
    )


async def check_t6a(
    project_id: str,
    start: int,
    end: int,
    *,
    threshold: float = _T6A_ORPHAN_SLOPE_THRESHOLD,
    continuity_repo: ContinuityReportRepository | None = None,
) -> ThresholdResult:
    """T6a: 窗口内 orphan_total 线性斜率 ≤ threshold."""
    points = await collect_orphan_metrics(
        project_id, start, end, repo=continuity_repo
    )
    sufficient = len(points) >= _MIN_ORPHAN_POINTS
    if not sufficient:
        return ThresholdResult(
            key="T6a",
            passed=None,
            measured=None,
            threshold=f"≤{threshold}",
            sufficient=False,
            detail=f" continuity_reports 样本不足（{len(points)} < {_MIN_ORPHAN_POINTS}）",
        )

    slope = linear_slope(
        [p.chapter for p in points], [float(p.orphan_total) for p in points]
    )
    return ThresholdResult(
        key="T6a",
        passed=slope <= threshold,
        measured=round(slope, 4),
        threshold=threshold,
        sufficient=True,
        detail=f"orphan_total 线性斜率 {slope:.4f}/章（基于 {len(points)} 章）",
    )


async def check_t6b(
    project_id: str,
    start: int,
    end: int,
    continuity_repo: ContinuityReportRepository | None = None,
) -> ThresholdResult:
    """T6b: 审计点上 orphan_critical == 0.

    ContinuityAuditor 默认按审计点产出报告，不要求每章都有 report。
    只要审计点样本足够且 P1 critical orphan 为 0，即可判定通过。
    """
    points = await collect_orphan_metrics(
        project_id, start, end, repo=continuity_repo
    )
    sufficient = len(points) >= _MIN_ORPHAN_POINTS

    if not sufficient:
        return ThresholdResult(
            key="T6b",
            passed=None,
            measured=None,
            threshold="orphan_critical = 0 全程",
            sufficient=False,
            detail=(
                f"continuity_report 审计点样本不足（{len(points)} < "
                f"{_MIN_ORPHAN_POINTS}），无法判定 P1=0"
            ),
        )

    breaches = [p.chapter for p in points if p.orphan_critical > 0]
    return ThresholdResult(
        key="T6b",
        passed=not breaches,
        measured=len(breaches),
        threshold="0",
        sufficient=True,
        detail=(
            f"P1 critical orphan 审计点全程为 0（基于 {len(points)} 个审计点）"
            if not breaches
            else f"P1 critical orphan >0 的章: {breaches[:20]}"
        ),
    )


async def check_t7_rate(
    project_id: str,
    start: int,
    end: int,
    *,
    t7_baseline: float = _T6C_T7_RATE_BASELINE,
    setting_repo: SettingTrackingRepository | None = None,
) -> ThresholdResult:
    """T7: 返回窗口内每章新 critical 产生速率（不设置独立红线，供 T6c 归因）."""
    points = await collect_new_critical_rate(
        project_id, start, end, repo=setting_repo
    )
    sufficient = len(points) >= _MIN_T7_POINTS
    if not sufficient:
        return ThresholdResult(
            key="T7",
            passed=None,
            measured=None,
            threshold=f"baseline={t7_baseline}",
            sufficient=False,
            detail="setting_tracking 样本不足，无法计算 T7",
        )

    avg_rate = sum(p.new_critical for p in points) / len(points)
    return ThresholdResult(
        key="T7",
        passed=None,
        measured=round(avg_rate, 4),
        threshold=t7_baseline,
        sufficient=True,
        detail=f"新 critical 速率 {avg_rate:.4f}/章（138k 基线 {t7_baseline}）",
    )


async def check_t6c_attribution(
    project_id: str,
    start: int,
    end: int,
    *,
    t7_baseline: float = _T6C_T7_RATE_BASELINE,
    orphan_slope_baseline: float = _T6A_ORPHAN_SLOPE_BASELINE,
    attribution_ratio: float = _T6C_ATTRIBUTION_RATIO,
    continuity_repo: ContinuityReportRepository | None = None,
    setting_repo: SettingTrackingRepository | None = None,
) -> ThresholdResult:
    """T6c hard: T7 降幅 ≥ orphan 斜率降幅的 50%，小基数保护."""
    orphan_points = await collect_orphan_metrics(
        project_id, start, end, repo=continuity_repo
    )
    critical_points = await collect_new_critical_rate(
        project_id, start, end, repo=setting_repo
    )
    sufficient = (
        len(orphan_points) >= _MIN_ORPHAN_POINTS
        and len(critical_points) >= _MIN_T7_POINTS
    )
    if not sufficient:
        return ThresholdResult(
            key="T6c",
            passed=None,
            measured=None,
            threshold=f"T7降幅 ≥ {attribution_ratio}× orphan斜率降幅",
            sufficient=False,
            detail="orphan 或 T7 样本不足，无法判定归因",
        )

    orphan_slope = linear_slope(
        [p.chapter for p in orphan_points], [float(p.orphan_total) for p in orphan_points]
    )
    avg_t7 = sum(p.new_critical for p in critical_points) / len(critical_points)

    orphan_decrease = orphan_slope_baseline - orphan_slope
    t7_decrease = t7_baseline - avg_t7
    required = attribution_ratio * orphan_decrease

    # 小基数保护：新 critical 已接近 0 时，T7 绝对可降空间不足，
    # 不能再用线性降幅比例判定为归因失败。
    if avg_t7 <= _T6C_SMALL_T7_RATE and t7_decrease >= 0:
        return ThresholdResult(
            key="T6c",
            passed=True,
            measured=f"orphan_slope={orphan_slope:.4f}, t7={avg_t7:.4f}",
            threshold=(
                f"T7≤{_T6C_SMALL_T7_RATE:.2f}/章时启用小基数保护；"
                f"否则 T7降幅≥{attribution_ratio}×orphan降幅"
            ),
            sufficient=True,
            detail=(
                "小基数保护：新 critical 产生率已接近 0，原降幅比值口径会被绝对可降空间"
                f"限制误伤；orphan 斜率降幅 {orphan_decrease:.4f}，"
                f"T7 降幅 {t7_decrease:.4f}"
            ),
        )

    # orphan 斜率没有下降时，归因自然不成立
    if orphan_decrease <= 0:
        return ThresholdResult(
            key="T6c",
            passed=False,
            measured=f"orphan_slope={orphan_slope:.4f}, t7={avg_t7:.4f}",
            threshold=f"orphan降幅>0 且 T7降幅≥{attribution_ratio}×orphan降幅",
            sufficient=True,
            detail="orphan 斜率未下降（或上升），无法归因于新设定减少",
        )

    passed = t7_decrease >= required
    return ThresholdResult(
        key="T6c",
        passed=passed,
        measured=f"orphan_slope={orphan_slope:.4f}, t7={avg_t7:.4f}",
        threshold=f"T7降幅 {t7_decrease:.4f} ≥ {required:.4f}",
        sufficient=True,
        detail=(
            f"orphan 斜率降幅 {orphan_decrease:.4f}"
            f"，T7 降幅 {t7_decrease:.4f}"
            f"（要求 ≥{required:.4f}）"
        ),
    )


async def check_t6c_observation(
    project_id: str,
    start: int,
    end: int,
    *,
    max_ratio: float = _T6C_OBS_MAX_RATIO,
    setting_repo: SettingTrackingRepository | None = None,
) -> ThresholdResult:
    """T6c-obs: 被降级 candidate 的 critical 占同窗新增 critical 总数比例（观察项）."""
    repo = setting_repo or SettingTrackingRepository()
    rows = [
        r
        for r in await repo.list_by_project(project_id)
        if start <= int(r.get("introduced_in_chapter") or 0) <= end
    ]

    candidate_critical = sum(
        1
        for r in rows
        if r.get("category") == "critical" and r.get("status") == "candidate"
    )
    new_critical = sum(
        1 for r in rows if r.get("category") == "critical"
    )
    ratio = candidate_critical / new_critical if new_critical else 0.0

    return ThresholdResult(
        key="T6c-obs",
        passed=None,
        measured=f"{ratio:.1%}",
        threshold=f"≤{max_ratio:.0%}（观察项，不进入 all_passed）",
        sufficient=new_critical > 0,
        detail=(
            f"candidate critical {candidate_critical} / 新增 critical {new_critical}"
        ),
    )


async def check_t3_t8(
    project_id: str,
    start: int,
    end: int,
) -> ThresholdResult:
    """T3/T8: 任一文学维度 W=5 均值较前 10 章基线下降 ≥20% 即破."""
    points = await collect_literary_scores(project_id, start, end)
    trend = detect_literary_trend(points)
    sufficient = trend.baseline_available
    if not sufficient:
        return ThresholdResult(
            key="T3/T8",
            passed=None,
            measured=None,
            threshold="无维度 W=5 均值降 ≥20%",
            sufficient=False,
            detail="文学分数基线不足（<10 章），暂不判定 T3/T8",
        )

    breached = trend.breached_dimensions
    return ThresholdResult(
        key="T3/T8",
        passed=not breached,
        measured=", ".join(breached) if breached else "none",
        threshold="breached_dimensions = []",
        sufficient=True,
        detail=(
            "无维度触 T3/T8 红线"
            if not breached
            else f"触线维度: {', '.join(breached)}"
        ),
    )


def check_t4(
    run_logs: list[ChapterRunLog] | None,
) -> ThresholdResult:
    """T4: 50 章窗内 degraded ≤20% 且 convergence_failed ≤10%."""
    if not run_logs:
        return ThresholdResult(
            key="T4",
            passed=None,
            measured=None,
            threshold=(
                f"degraded≤{_T4_DEGRADED_MAX:.0%}, "
                f"convergence≤{_T4_CONVERGENCE_MAX:.0%}"
            ),
            sufficient=False,
            detail="未提供 run_logs，T4 未判定",
        )

    report = compute_quality_debt(run_logs, window=50)
    measured = (
        f"degraded={report.degraded_ratio:.1%}, "
        f"convergence={report.convergence_ratio:.1%}"
    )
    if not report.window_sufficient:
        return ThresholdResult(
            key="T4",
            passed=None,
            measured=measured,
            threshold="50 章满窗",
            sufficient=False,
            detail=f"run_logs 仅 {report.total_chapters} 章，不足 50 章窗口",
        )

    return ThresholdResult(
        key="T4",
        passed=not report.t4_breached,
        measured=measured,
        threshold=(
            f"degraded≤{_T4_DEGRADED_MAX:.0%}, "
            f"convergence≤{_T4_CONVERGENCE_MAX:.0%}"
        ),
        sufficient=True,
        detail=(
            "T4 未破"
            if not report.t4_breached
            else f"破线窗口数 {sum(1 for w in report.windows if w.t4_breached)}"
        ),
    )


async def check_t5(
    project_id: str,
    *,
    run_id: str | None = None,
) -> ThresholdResult:
    """T5: DB ≤300MB、扫描耗时采用中位数 ×2.0 稳健口径."""
    repo = RunDbMetricsRepository()
    if run_id:
        samples = await repo.list_by_run(run_id)
    else:
        samples = await repo.list_by_project(project_id)

    sufficient = len(samples) >= _MIN_T5_SAMPLES
    if not sufficient:
        return ThresholdResult(
            key="T5",
            passed=None,
            measured=None,
            threshold="DB≤300MB; scan≤1.5× baseline",
            sufficient=False,
            detail=f"run_db_metrics 样本不足（{len(samples)} < {_MIN_T5_SAMPLES}）",
        )

    size_breaches: list[int] = []
    max_db_mb = 0.0
    for s in samples:
        db_bytes = int(s["db_size_bytes"])
        db_mb = db_bytes / (1024 * 1024)
        max_db_mb = max(max_db_mb, db_mb)
        if check_t5_size_redline(
            DbSizeMetrics(
                db_size_bytes=db_bytes,
                wal_size_bytes=int(s["wal_size_bytes"]),
                page_count=int(s["page_count"]),
                page_size=int(s["page_size"]),
            )
        ):
            size_breaches.append(int(s["chapter_number"]))

    latency = analyze_t5_latency_samples(samples)

    passed = not size_breaches and not latency.hard_failed
    return ThresholdResult(
        key="T5",
        passed=passed,
        measured=(
            f"max_db={max_db_mb:.2f}MB, "
            f"max_latency_ratio={latency.max_latency_ratio:.2f}x"
        ),
        threshold="DB≤300MB; scan≤median×2.0（连续/极端破线才 hard fail）",
        sufficient=True,
        detail=(
            "T5 未破"
            if passed
            else (
                f"尺寸破线章 {size_breaches}; "
                f"耗时 hard 破线章 {latency.hard_breach_chapters}"
            )
        )
        + (
            f"；耗时观察章 {latency.observed_breach_chapters}"
            if latency.observed_breach_chapters
            else ""
        ),
    )


async def check_health_low(
    project_id: str,
    start: int,
    end: int,
) -> ThresholdResult:
    """阶段 B 出口附加项：health_score 全程 ≥ 7.0."""
    metrics = await collect_continuity_health_metrics(project_id, start, end)
    chapter_details = metrics.get("chapter_details", [])
    low_chapters = [d["chapter_number"] for d in chapter_details if d.get("health_low")]
    sufficient = len(chapter_details) > 0

    return ThresholdResult(
        key="health≥7.0",
        passed=not low_chapters if sufficient else None,
        measured=len(low_chapters),
        threshold="0",
        sufficient=sufficient,
        detail=(
            "health 全程 ≥7.0"
            if not low_chapters
            else f"health<7.0 的章: {low_chapters[:20]}"
        ),
    )


async def check_t9(
    project_id: str,
    start: int,
    end: int,
    *,
    include_timeline_in_redline: bool = False,
) -> ThresholdResult:
    """T9: accepted 正文元标记=0、重复长段落=0；时间线口径待 V7 Task 165 冻结."""
    rows = await collect_text_cleanliness_metrics(project_id, start, end, persist=False)
    expected = list(range(start, end + 1))
    present = {row.chapter_number for row in rows}
    missing = [chapter for chapter in expected if chapter not in present]
    if not rows or missing:
        return ThresholdResult(
            key="T9",
            passed=None,
            measured=f"{len(rows)}/{len(expected)}",
            threshold="meta=0; duplicate=0; timeline configurable",
            sufficient=False,
            detail=(
                f"洁净度样本不足；缺失章: {missing[:20]}"
                if missing
                else "无 accepted 正文洁净度样本"
            ),
        )

    meta_chapters = [row.chapter_number for row in rows if row.meta_tag_leak_count > 0]
    duplicate_chapters = [
        row.chapter_number for row in rows if row.duplicate_paragraph_count > 0
    ]
    timeline_chapters = [
        row.chapter_number for row in rows if row.timeline_conflict_count > 0
    ]
    timeline_breached = bool(timeline_chapters) and include_timeline_in_redline
    passed = not meta_chapters and not duplicate_chapters and not timeline_breached
    measured = (
        f"meta={sum(row.meta_tag_leak_count for row in rows)}, "
        f"duplicate={sum(row.duplicate_paragraph_count for row in rows)}, "
        f"timeline={sum(row.timeline_conflict_count for row in rows)}"
    )
    threshold = (
        "meta=0; duplicate=0; timeline=0"
        if include_timeline_in_redline
        else "meta=0; duplicate=0; timeline report-only"
    )
    detail_parts = []
    if meta_chapters:
        detail_parts.append(f"元标记违规章: {meta_chapters[:20]}")
    if duplicate_chapters:
        detail_parts.append(f"重复长段落违规章: {duplicate_chapters[:20]}")
    if timeline_chapters:
        label = "时间线红线章" if include_timeline_in_redline else "时间线诊断章"
        detail_parts.append(f"{label}: {timeline_chapters[:20]}")
    if not detail_parts:
        detail_parts.append("T9 洁净度红线未破")

    return ThresholdResult(
        key="T9",
        passed=passed,
        measured=measured,
        threshold=threshold,
        sufficient=True,
        detail="；".join(detail_parts),
    )


# --------------------------------------------------------------------------- #
# 聚合入口
# --------------------------------------------------------------------------- #


async def evaluate_v6_acceptance(
    project_id: str,
    start: int,
    end: int,
    *,
    run_id: str | None = None,
    run_logs: list[ChapterRunLog] | None = None,
    orphan_slope_threshold: float = _T6A_ORPHAN_SLOPE_THRESHOLD,
    orphan_slope_baseline: float = _T6A_ORPHAN_SLOPE_BASELINE,
    t7_rate_baseline: float = _T6C_T7_RATE_BASELINE,
    t9_include_timeline_in_redline: bool = False,
) -> V6AcceptanceResult:
    """对 (project, 章范围) 执行全部 V6 红线判定，返回三态结果.

    Args:
        project_id: 项目 ID。
        start: 起始章号（含）。
        end: 结束章号（含）。
        run_id: 可选 run ID，用于 T5 过滤 run_db_metrics。
        run_logs: 可选每章运行日志，用于 T4 质量债窗口判定；不提供则 T4 标为未判定。
        orphan_slope_threshold: T6a 斜率阈值（默认 3.14）。
        orphan_slope_baseline: T6a 归因基线（默认 138n 的 6.2836）。
        t7_rate_baseline: T7 归因基线（默认 138k 的 1.767）。
    """
    results: list[ThresholdResult] = [
        await check_t1(project_id, start, end),
        await check_t2(project_id, start, end),
        await check_t6a(
            project_id, start, end, threshold=orphan_slope_threshold
        ),
        await check_t6b(project_id, start, end),
        await check_t6c_attribution(
            project_id,
            start,
            end,
            t7_baseline=t7_rate_baseline,
            orphan_slope_baseline=orphan_slope_baseline,
        ),
        await check_t6c_observation(project_id, start, end),
        await check_t7_rate(project_id, start, end, t7_baseline=t7_rate_baseline),
        await check_t3_t8(project_id, start, end),
        check_t4(run_logs),
        await check_t5(project_id, run_id=run_id),
        await check_t9(
            project_id,
            start,
            end,
            include_timeline_in_redline=t9_include_timeline_in_redline,
        ),
        await check_health_low(project_id, start, end),
    ]

    failed_sufficient = [r for r in results if r.sufficient and r.passed is False]
    all_passed = not failed_sufficient
    undecided = [r.key for r in results if r.passed is None]

    return V6AcceptanceResult(
        project_id=project_id,
        chapter_start=start,
        chapter_end=end,
        results=results,
        all_passed=all_passed,
        undecided=undecided,
    )


# --------------------------------------------------------------------------- #
# 渲染
# --------------------------------------------------------------------------- #


def render_v6_acceptance_section(result: V6AcceptanceResult) -> str:
    """渲染验收判据段，供 `songyan metrics` 追加到报告尾部."""
    lines = ["## V6 验收判据（harness 三态）", ""]
    lines.append(
        f"项目 **{result.project_id}** Ch{result.chapter_start}-Ch{result.chapter_end}"
    )
    lines.append("")
    lines.append("| 判据 | 结果 | 实测值 | 阈值 | 充分性 | 详情 |")
    lines.append("|------|------|--------|------|--------|------|")

    for r in result.results:
        if r.passed is True:
            flag = "✓ pass"
        elif r.passed is False:
            flag = "🔴 fail"
        else:
            flag = "◯ 未判定"
        suff = "充分" if r.sufficient else "不足"
        measured = r.measured if r.measured is not None else "-"
        threshold = r.threshold if r.threshold is not None else "-"
        lines.append(
            f"| {r.key} | {flag} | {measured} | {threshold} | {suff} | {r.detail} |"
        )

    lines.append("")
    undecided_text = result.undecided or "无"
    if result.all_passed:
        lines.append(
            f"- **聚合结论：无 failed sufficient 项**（未判定项：{undecided_text}）"
        )
    else:
        lines.append(
            f"- **聚合结论：存在未通过的 sufficient 项**"
            f"（未判定项：{undecided_text}）"
        )
    return "\n".join(lines)
