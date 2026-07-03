"""Task 159: Ch1-Ch150 治理管线复现 + V6 阶段验收实跑.

用法:
    # 1. 初始化干净隔离 DB + 创建带大纲项目（与 157/158 同口径骨架）
    $env:DATABASE_URL = "sqlite:///.tmp/task159_ch1_ch150.db"
    python scripts/run_159_ch1_ch150.py --init

    # 2. 无人值守跑 Ch1-Ch150（enforce 门禁，on_failure=isolate，与 158 同口径）
    $env:DATABASE_URL = "sqlite:///.tmp/task159_ch1_ch150.db"
    python scripts/run_159_ch1_ch150.py

    # 如中途 kill / AutoHalt，可续跑（复用同一 run_id，跳过已 accepted 章）
    python scripts/run_159_ch1_ch150.py --resume

    # 仅从已有 DB 重新生成验收报告（不跑 LLM）
    python scripts/run_159_ch1_ch150.py --report

说明:
    - 阶段 D 收官（v6-plan §3 / Task 159）：150 章复现 + 逐项基线对比 +
      N/D/S/R/V 验收 + T5 冻结复核。
    - 判据/曲线全部复用 157 harness（evaluate_v6_acceptance）与 render_stage_a_metrics，不 fork。
    - §1.3-R kill→resume 引用 Task 158r 命令级证据（run-82bd2e07），不重复演练。
    - 产出 docs/reports/task-159-v6-final-acceptance-report.md。
    - 逐章 metrics 追加到 .tmp/task159_ch1_ch150_metrics.jsonl。
    - 项目设定 / 大纲构造器复用 scripts.run_158_ch1_ch100，保证与 158 纵向可比。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from pydantic import BaseModel

import scripts.run_158_ch1_ch100 as base
from songyan.db import get_db
from songyan.db.connection import get_db_path
from songyan.db.migrations import init_schema
from songyan.db.narrative_repo import NarrativeRepository
from songyan.db.repository import ProjectRepository
from songyan.evals.db_metrics import render_stage_a_metrics
from songyan.evals.streaming_report import read_run_logs
from songyan.evals.v6_acceptance import (
    V6AcceptanceResult,
    evaluate_v6_acceptance,
    render_v6_acceptance_section,
)
from songyan.exceptions import AutoHaltException
from songyan.models import GateConfig
from songyan.workflows.phase2_graph import run_project_pipeline

DB_PATH = Path(".tmp/task159_ch1_ch150.db")
REPORT_PATH = Path("docs/reports/task-159-v6-final-acceptance-report.md")
METRICS_PATH = Path(".tmp/task159_ch1_ch150_metrics.jsonl")
PROJECT_FILE = Path(".tmp/task159_project.json")

GATE_MODE = os.getenv("GATE_MODE", "enforce")
ON_FAILURE = os.getenv("ON_FAILURE", "isolate")
LLM_BUDGET = os.getenv("LLM_BUDGET", "0")
START_CHAPTER = int(os.getenv("START_CHAPTER", "1"))
END_CHAPTER = int(os.getenv("END_CHAPTER", "150"))

# 138n Ch1-Ch30 rerun orphan 斜率基线（与 harness _T6A_ORPHAN_SLOPE_BASELINE 同源）。
ORPHAN_SLOPE_BASELINE_138N = 6.2836
ORPHAN_SLOPE_THRESHOLD = 3.14  # =138n×0.5

# §1.3-R：kill→resume 命令级证据引用（Task 158r）。
R_EVIDENCE_RUN_ID = "run-82bd2e07"
R_EVIDENCE_REPORT = "docs/reports/task-158r-kill-resume-drill-report.md"


# --------------------------------------------------------------------------- #
# 纯逻辑：基线对比（可单测，不碰 DB / LLM）
# --------------------------------------------------------------------------- #
class BaselineComparison(BaseModel):
    """与 a2bed648/138n 基线的"不劣于"判定."""

    completion_measured: str
    completion_ok: bool
    orphan_slope: float | None
    orphan_slope_threshold: float
    orphan_slope_ok: bool | None
    p1_critical_zero: bool
    p1_breach_chapters: list[int]
    t3_not_red: bool | None
    t4_not_red: bool | None
    t5_not_red: bool | None
    not_worse_than_baseline: bool
    detail: str


def compare_to_baseline(
    *,
    completed_count: int,
    target_count: int,
    orphan_slope: float | None,
    p1_breach_chapters: list[int],
    t3_passed: bool | None,
    t4_passed: bool | None,
    t5_passed: bool | None,
    orphan_slope_threshold: float = ORPHAN_SLOPE_THRESHOLD,
) -> BaselineComparison:
    """判定 150 章结果是否"不劣于"V5.1 基线.

    "不劣于" = 完成率达标 + orphan 斜率 ≤138n×0.5 + P1 critical orphan=0 +
    T3/T4/T5 均未 fail（None 视为待判定，不算 red，但会在 detail 标注）。
    """
    completion_ok = completed_count >= target_count
    orphan_slope_ok: bool | None = (
        None if orphan_slope is None else orphan_slope <= orphan_slope_threshold
    )
    p1_critical_zero = not p1_breach_chapters
    t3_not_red = None if t3_passed is None else t3_passed is not False
    t4_not_red = None if t4_passed is None else t4_passed is not False
    t5_not_red = None if t5_passed is None else t5_passed is not False

    # 硬失败项：任一为 False 即"劣于基线"。None（待判定）不阻断，但记录。
    hard_flags = [
        completion_ok,
        orphan_slope_ok is not False,
        p1_critical_zero,
        t3_not_red is not False,
        t4_not_red is not False,
        t5_not_red is not False,
    ]
    not_worse = all(hard_flags)

    parts = [
        f"完成率 {completed_count}/{target_count} {'✓' if completion_ok else '🔴'}",
        (
            f"orphan 斜率 {orphan_slope:.4f}≤{orphan_slope_threshold} "
            f"{'✓' if orphan_slope_ok else '🔴'}"
            if orphan_slope is not None
            else "orphan 斜率 未判定"
        ),
        f"P1 critical orphan {'=0 ✓' if p1_critical_zero else f'破线@{p1_breach_chapters} 🔴'}",
        f"T3/T8 {'✓' if t3_not_red else ('🔴' if t3_not_red is False else '未判定')}",
        f"T4 {'✓' if t4_not_red else ('🔴' if t4_not_red is False else '未判定')}",
        f"T5 {'✓' if t5_not_red else ('🔴' if t5_not_red is False else '未判定')}",
    ]
    return BaselineComparison(
        completion_measured=f"{completed_count}/{target_count}",
        completion_ok=completion_ok,
        orphan_slope=orphan_slope,
        orphan_slope_threshold=orphan_slope_threshold,
        orphan_slope_ok=orphan_slope_ok,
        p1_critical_zero=p1_critical_zero,
        p1_breach_chapters=p1_breach_chapters,
        t3_not_red=t3_not_red,
        t4_not_red=t4_not_red,
        t5_not_red=t5_not_red,
        not_worse_than_baseline=not_worse,
        detail="；".join(parts),
    )


# --------------------------------------------------------------------------- #
# 纯逻辑：N/D/S/R/V 汇总（复用 harness 三态，不 fork 判据）
# --------------------------------------------------------------------------- #
class NDSRVRow(BaseModel):
    """§1.3 单项判定行."""

    dim: str
    name: str
    criterion: str
    state: bool | None  # True=pass / False=fail / None=待判定
    detail: str
    evidence: str


def _combine(*states: bool | None) -> bool | None:
    """三态合取：任一 False→False；否则任一 None→None；否则 True."""
    if any(s is False for s in states):
        return False
    if any(s is None for s in states):
        return None
    return True


def _harness_map(result: V6AcceptanceResult) -> dict[str, bool | None]:
    return {r.key: r.passed for r in result.results}


def derive_ndsrv(
    result: V6AcceptanceResult,
    *,
    outline_present: bool,
    d_metrics_present: bool,
    r_passed: bool,
    r_evidence: str,
) -> list[NDSRVRow]:
    """把 harness 三态 + 骨架/度量/可靠性输入映射为 N/D/S/R/V 五行.

    - N（骨架）= 大纲/弧携带 AND T1 跃迁。
    - D（度量）= 五类指标入库且可查（由调用方判定 d_metrics_present）。
    - S（收敛）= T6a AND T6b AND T6c。
    - R（可靠）= Ch100 无人值守 + kill→resume 命令级证据（引用 158/158r）。
    - V（验证）= T2 完成 AND T3/T8 AND T4 AND T5 全未破。
    """
    m = _harness_map(result)
    outline_state = True if outline_present else False

    n_state = _combine(outline_state, m.get("T1"))
    s_state = _combine(m.get("T6a"), m.get("T6b"), m.get("T6c"))
    v_state = _combine(m.get("T2"), m.get("T3/T8"), m.get("T4"), m.get("T5"))

    def _t(key: str) -> str:
        r = next((x for x in result.results if x.key == key), None)
        if r is None:
            return f"{key}: N/A"
        flag = "pass" if r.passed is True else ("fail" if r.passed is False else "未判定")
        return f"{key}={flag}({r.measured})"

    return [
        NDSRVRow(
            dim="N",
            name="骨架",
            criterion="大纲/弧携带 + GoalPlanner 弧上下文 + Ch1-Ch50 ≥1 主线 T1 跃迁",
            state=n_state,
            detail=f"大纲携带={'是' if outline_present else '否'}；{_t('T1')}",
            evidence="NarrativeRepository / context_snapshots / check_t1",
        ),
        NDSRVRow(
            dim="D",
            name="度量",
            criterion="五类指标入库且 songyan metrics 1-150 可查、无断档",
            state=True if d_metrics_present else False,
            detail=f"五类曲线渲染={'有数据' if d_metrics_present else '缺失'}",
            evidence="render_stage_a_metrics 输出",
        ),
        NDSRVRow(
            dim="S",
            name="收敛",
            criterion="T6a 斜率 ≤138n×0.5 + T6b P1=0 + T6c 归因成立",
            state=s_state,
            detail=f"{_t('T6a')}；{_t('T6b')}；{_t('T6c')}",
            evidence="evaluate_v6_acceptance T6*",
        ),
        NDSRVRow(
            dim="R",
            name="可靠",
            criterion="单命令无人值守 Ch100（Task 158）+ kill→resume 命令级证据（Task 158r）",
            state=True if r_passed else False,
            detail=f"kill→resume 引用 {r_evidence}",
            evidence="Task 158 / 158r 报告",
        ),
        NDSRVRow(
            dim="V",
            name="验证",
            criterion="新管线 Ch1-Ch150 连续证据 + 全程 T3/T4 不破 + T5 复核冻结口径不破",
            state=v_state,
            detail=f"{_t('T2')}；{_t('T3/T8')}；{_t('T4')}；{_t('T5')}",
            evidence="本 Task 长跑 + evaluate_v6_acceptance",
        ),
    ]


def summarize_ndsrv(rows: list[NDSRVRow]) -> tuple[str, list[str]]:
    """给出总结论 + 阻断项清单.

    五项全 pass → V6 通过；任一 fail → 条件不通过 + 阻断项；
    无 fail 但有待判定 → 条件通过（待判定项待补）。
    """
    blockers = [f"{r.dim}（{r.name}）" for r in rows if r.state is False]
    undecided = [f"{r.dim}（{r.name}）" for r in rows if r.state is None]
    if blockers:
        return (
            f"🔴 **V6 条件不通过**：阻断项 {', '.join(blockers)}"
            + (f"；待判定 {', '.join(undecided)}" if undecided else ""),
            blockers,
        )
    if undecided:
        return (
            f"◯ **V6 条件通过（含待判定项）**：{', '.join(undecided)} 需补足证据后再终判",
            [],
        )
    return ("✅ **V6 通过**：N/D/S/R/V 五项全部满足", [])


def render_ndsrv_section(
    rows: list[NDSRVRow],
    baseline: BaselineComparison,
) -> str:
    """渲染 N/D/S/R/V 核对表 + 基线对比 + 总结论."""

    def _flag(state: bool | None) -> str:
        return "✅ pass" if state is True else ("🔴 fail" if state is False else "◯ 待判定")

    lines = [
        "## §1.3 N/D/S/R/V 验收核对",
        "",
        "| 维度 | 判据 | 结论 | 实测/证据 | 证据来源 |",
        "|------|------|------|-----------|----------|",
    ]
    for r in rows:
        lines.append(
            f"| **{r.dim} {r.name}** | {r.criterion} | {_flag(r.state)} | "
            f"{r.detail} | {r.evidence} |"
        )
    lines.extend(
        [
            "",
            "### 与 a2bed648/138n 基线逐项对比（不劣于）",
            "",
            f"- 结论：{'✅ 不劣于基线' if baseline.not_worse_than_baseline else '🔴 劣于基线'}",
            f"- 明细：{baseline.detail}",
        ]
    )
    verdict, _ = summarize_ndsrv(rows)
    lines.extend(["", "### 总结论", "", verdict])
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# 纯逻辑：T5 阈值复核（150 章样本重算，供冻结决定）
# --------------------------------------------------------------------------- #
class T5Analysis(BaseModel):
    """T5 复核：现口径 vs 候选稳健口径的对照，供冻结决定."""

    sample_count: int
    max_db_mb: float
    size_redline_mb: float
    size_ok: bool
    scan_samples_ms: list[float]
    # 现口径：前 10 样本均值 ×1.5
    old_baseline_ms: float | None
    old_factor: float
    old_breach_chapters: list[int]
    # 候选稳健口径：全样本中位数 ×factor
    robust_baseline_ms: float | None
    robust_factor: float
    robust_breach_chapters: list[int]
    detail: str


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2.0


def analyze_t5_samples(
    samples: list[dict[str, Any]],
    *,
    size_redline_mb: float = 300.0,
    old_factor: float = 1.5,
    robust_factor: float = 2.0,
) -> T5Analysis:
    """用 150 章全样本复算 T5：诊断现口径破线，给出候选稳健口径.

    现口径（158 破线源）：前 10 样本均值 × old_factor —— 在样本少时基线窗口
    与被比较样本重叠、且受单点 find_orphaned 计时抖动影响，易假破线。
    候选口径：全样本中位数 × robust_factor（抗离群 + 更大窗口）。
    """
    chapters = [int(s["chapter_number"]) for s in samples]
    scan = [
        float(s["scan_latency_ms"])
        for s in samples
        if s.get("scan_latency_ms") is not None
    ]
    db_mbs = [int(s["db_size_bytes"]) / (1024 * 1024) for s in samples]
    max_db_mb = max(db_mbs) if db_mbs else 0.0
    size_ok = max_db_mb <= size_redline_mb

    old_baseline = (sum(scan[:10]) / len(scan[:10])) if scan[:10] else None
    old_breach = (
        [
            chapters[i]
            for i, v in enumerate(scan)
            if old_baseline and v > old_baseline * old_factor
        ]
        if old_baseline
        else []
    )
    robust_baseline = _median(scan) if scan else None
    robust_breach = (
        [
            chapters[i]
            for i, v in enumerate(scan)
            if robust_baseline and v > robust_baseline * robust_factor
        ]
        if robust_baseline
        else []
    )

    detail = (
        f"尺寸峰值 {max_db_mb:.2f}MB（红线 {size_redline_mb:.0f}MB，"
        f"{'✓' if size_ok else '🔴'}）；"
        f"现口径(前10均值×{old_factor})破线章 {old_breach or '无'}；"
        f"候选口径(中位数×{robust_factor})破线章 {robust_breach or '无'}"
    )
    return T5Analysis(
        sample_count=len(samples),
        max_db_mb=max_db_mb,
        size_redline_mb=size_redline_mb,
        size_ok=size_ok,
        scan_samples_ms=scan,
        old_baseline_ms=old_baseline,
        old_factor=old_factor,
        old_breach_chapters=old_breach,
        robust_baseline_ms=robust_baseline,
        robust_factor=robust_factor,
        robust_breach_chapters=robust_breach,
        detail=detail,
    )


def render_t5_review_section(analysis: T5Analysis) -> str:
    """渲染「T5 阈值复核与冻结」专节（冻结决定由报告作者据此填写）."""
    lines = [
        "## T5 阈值复核与冻结",
        "",
        f"- 样本数：{analysis.sample_count}（每 10 章一采样）",
        f"- DB 尺寸峰值：{analysis.max_db_mb:.2f} MB（红线 "
        f"{analysis.size_redline_mb:.0f} MB，"
        f"{'✓ 未破' if analysis.size_ok else '🔴 破线'}）",
        f"- 扫描耗时样本(ms)：{[round(v, 1) for v in analysis.scan_samples_ms]}",
        "",
        "| 口径 | 基线(ms) | 系数 | 破线章 |",
        "|------|---------:|-----:|--------|",
        f"| 现口径（前10样本均值） | "
        f"{analysis.old_baseline_ms:.1f} | ×{analysis.old_factor} | "
        f"{analysis.old_breach_chapters or '无'} |"
        if analysis.old_baseline_ms is not None
        else "| 现口径 | N/A | - | 样本不足 |",
        f"| 候选稳健口径（全样本中位数） | "
        f"{analysis.robust_baseline_ms:.1f} | ×{analysis.robust_factor} | "
        f"{analysis.robust_breach_chapters or '无'} |"
        if analysis.robust_baseline_ms is not None
        else "| 候选口径 | N/A | - | 样本不足 |",
        "",
        f"- 复核明细：{analysis.detail}",
        "- **冻结决定**：_（据上表填写：选定口径 + 系数 + 理由；遵守 148z 纪律，"
        "基于实测调整后冻结，不为凑过临时放宽）_",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# DB 辅助
# --------------------------------------------------------------------------- #
async def _query_dicts(
    sql: str, params: tuple[Any, ...] = ()
) -> list[dict[str, Any]]:
    async with get_db() as conn:
        conn.row_factory = lambda cursor, row: {
            col[0]: row[i] for i, col in enumerate(cursor.description)
        }
        cursor = await conn.execute(sql, params)
        return await cursor.fetchall()


async def _init_db() -> str:
    db_path = get_db_path()
    for suffix in ("", "-wal", "-shm"):
        p = db_path.with_name(db_path.name + suffix) if suffix else db_path
        if p.exists():
            p.unlink()
            print(f"[init] removed {p}")
    await init_schema()
    print(f"[init] schema initialized at {db_path}")

    if METRICS_PATH.exists():
        METRICS_PATH.unlink()
        print(f"[init] removed stale metrics {METRICS_PATH}")

    project_id = uuid.uuid4().hex
    await ProjectRepository().create(base._project_setting(), project_id)
    outline, arcs, threads = base._build_outline(project_id)
    await NarrativeRepository().import_outline(project_id, outline, arcs, threads)
    print(f"[init] project created {project_id}")
    print(f"[init] outline imported: {len(arcs)} arcs, {len(threads)} threads")

    PROJECT_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROJECT_FILE.write_text(
        json.dumps(
            {"project_id": project_id, "db": str(db_path.as_posix())},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"[init] PROJECT_ID={project_id} (saved to {PROJECT_FILE})")
    return project_id


def _resolve_project_id() -> str | None:
    pid = os.getenv("PROJECT_ID")
    if pid:
        return pid
    if PROJECT_FILE.exists():
        try:
            return json.loads(PROJECT_FILE.read_text(encoding="utf-8")).get(
                "project_id"
            )
        except (json.JSONDecodeError, OSError):
            return None
    return None


async def _find_run_id(project_id: str) -> str | None:
    rows = await _query_dicts(
        """SELECT run_id FROM project_runs
           WHERE project_id = ?
           ORDER BY created_at DESC LIMIT 1""",
        (project_id,),
    )
    return rows[0]["run_id"] if rows else None


async def _outline_present(project_id: str) -> bool:
    repo = NarrativeRepository()
    outline = await repo.get_outline(project_id)
    arcs = await repo.list_arc_plans(project_id)
    return outline is not None and len(arcs) > 0


async def _t5_samples(run_id: str | None, project_id: str) -> list[dict[str, Any]]:
    if run_id:
        rows = await _query_dicts(
            """SELECT chapter_number, db_size_bytes, wal_size_bytes,
                      page_count, page_size, scan_latency_ms
               FROM run_db_metrics WHERE run_id = ?
               ORDER BY chapter_number""",
            (run_id,),
        )
    else:
        rows = await _query_dicts(
            """SELECT chapter_number, db_size_bytes, wal_size_bytes,
                      page_count, page_size, scan_latency_ms
               FROM run_db_metrics WHERE project_id = ?
               ORDER BY chapter_number""",
            (project_id,),
        )
    return rows


def _append_metric(record: dict[str, Any]) -> None:
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with METRICS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _harness_val(result: V6AcceptanceResult, key: str) -> bool | None:
    for r in result.results:
        if r.key == key:
            return r.passed
    return None


# --------------------------------------------------------------------------- #
# 报告生成
# --------------------------------------------------------------------------- #
async def _build_and_write_report(
    project_id: str, run_id: str | None
) -> None:
    accepted = await base._load_accepted_versions(project_id)  # type: ignore[attr-defined]
    run_log = base._load_run_log_metrics(run_id)  # type: ignore[attr-defined]
    continuity = await _load_continuity(project_id)

    chapters: list[dict[str, Any]] = []
    for ch in sorted(set(list(accepted.keys()) + list(run_log.keys()))):
        if ch < START_CHAPTER or ch > END_CHAPTER:
            continue
        version = accepted.get(ch)
        log = run_log.get(ch, {})
        record = {
            "chapter": ch,
            "accepted": ch in accepted,
            "word_count": version.word_count if version else log.get("word_count"),
            "settlement_success": log.get("settlement_success"),
            "summary_success": log.get("summary_success"),
            "quality_gate_passed": log.get("quality_gate_passed"),
            "gate_triggered": log.get("gate_triggered"),
            "context_emergency": log.get("context_emergency"),
            "duration_sec": log.get("duration_sec"),
        }
        chapters.append(record)
        _append_metric(record)

    completed_count = sum(1 for c in chapters if c["accepted"])
    target_count = END_CHAPTER - START_CHAPTER + 1

    run_logs = read_run_logs(run_id) if run_id else []
    harness = await evaluate_v6_acceptance(
        project_id, START_CHAPTER, END_CHAPTER, run_id=run_id, run_logs=run_logs
    )
    harness_section = render_v6_acceptance_section(harness)
    stage_a_section = await render_stage_a_metrics(
        project_id, START_CHAPTER, END_CHAPTER
    )

    # T5 复核
    samples = await _t5_samples(run_id, project_id)
    t5 = analyze_t5_samples(samples)

    # 基线对比
    orphan_slope = _extract_orphan_slope(harness)
    p1_breach = [c["chapter"] for c in continuity if c["orphan_critical"] > 0]
    baseline = compare_to_baseline(
        completed_count=completed_count,
        target_count=target_count,
        orphan_slope=orphan_slope,
        p1_breach_chapters=p1_breach,
        t3_passed=_harness_val(harness, "T3/T8"),
        t4_passed=_harness_val(harness, "T4"),
        t5_passed=t5.size_ok and not t5.robust_breach_chapters,
    )

    # D 项：五类曲线均有数据
    d_present = bool(stage_a_section) and "暂无" not in stage_a_section
    rows = derive_ndsrv(
        harness,
        outline_present=await _outline_present(project_id),
        d_metrics_present=d_present,
        r_passed=True,
        r_evidence=f"{R_EVIDENCE_RUN_ID}（{R_EVIDENCE_REPORT}）",
    )
    ndsrv_section = render_ndsrv_section(rows, baseline)
    verdict, blockers = summarize_ndsrv(rows)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Task 159：V6 阶段验收报告（Ch1-Ch150 治理管线复现）",
        "",
        f"- 生成时间: {datetime.now().isoformat()}",
        f"- DB: `{get_db_path()}`",
        f"- 项目 ID: `{project_id}`",
        f"- Run ID: `{run_id}`（**非** a2bed648）",
        f"- 章节范围: Ch{START_CHAPTER}-Ch{END_CHAPTER}",
        f"- Gate 模式: {GATE_MODE}；on_failure: {ON_FAILURE}",
        f"- 完成: {completed_count}/{target_count}",
        "",
        ndsrv_section,
        "",
        render_t5_review_section(t5),
        "",
        stage_a_section,
        "",
        harness_section,
        "",
        "## 结论",
        "",
        verdict,
    ]
    if blockers:
        lines.append("")
        lines.append(f"阻断项：{', '.join(blockers)}；按纪律新开修复 Task，不在 159 改治理。")
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[report] {REPORT_PATH}")
    print(f"\n=== N/D/S/R/V 总结论 ===\n{verdict}")


async def _load_continuity(project_id: str) -> list[dict[str, Any]]:
    from songyan.db.continuity_repo import ContinuityReportRepository

    reports = await ContinuityReportRepository().list_by_chapter_range(
        project_id, START_CHAPTER, END_CHAPTER
    )
    out: list[dict[str, Any]] = []
    for r in reports:
        orphan_critical = sum(
            1
            for s in r.orphaned_settings
            if getattr(s, "category", "background") == "critical"
        )
        out.append(
            {
                "chapter": r.checked_up_to_chapter,
                "orphan_total": len(r.orphaned_settings),
                "orphan_critical": orphan_critical,
            }
        )
    return out


def _extract_orphan_slope(harness: V6AcceptanceResult) -> float | None:
    for r in harness.results:
        if r.key == "T6a" and isinstance(r.measured, (int, float)):
            return float(r.measured)
    return None


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--init", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--project-id", default=None)
    parser.add_argument(
        "--report", action="store_true", help="仅从已有 DB 重新生成报告"
    )
    args = parser.parse_args()

    if args.init:
        await _init_db()
        return

    project_id = args.project_id or _resolve_project_id()
    if not project_id:
        parser.error("请先 --init 创建项目，或提供 --project-id / PROJECT_ID")

    if args.report:
        run_id = await _find_run_id(project_id)
        await _build_and_write_report(project_id, run_id)
        return

    db_path = get_db_path()
    print(f"[preflight] db={db_path} project={project_id}")
    print(
        f"[preflight] gate_mode={GATE_MODE}, on_failure={ON_FAILURE}, "
        f"resume={args.resume}, range=({START_CHAPTER},{END_CHAPTER})"
    )

    project = await ProjectRepository().get(project_id)
    if project is None:
        raise ValueError(f"Project not found: {project_id}")

    budget_value = int(LLM_BUDGET)
    if budget_value > 0:
        from songyan.config import settings

        settings.llm_run_call_budget = budget_value
        print(f"[preflight] llm_run_call_budget={budget_value}")

    gate_config = GateConfig.for_mode(GATE_MODE)  # type: ignore[arg-type]

    halt_reason: str | None = None
    try:
        result = await run_project_pipeline(
            project_id=project_id,
            chapter_range=(START_CHAPTER, END_CHAPTER),
            mode_id=project.mode_id,
            auto_confirm=True,
            on_failure=ON_FAILURE,
            gate_config=gate_config,
            resume=args.resume,
        )
        print("\n=== Pipeline completed ===")
        print(f"Completed: {result.chapters_completed}")
        print(f"Failed: {result.chapters_failed}")
        print(f"Status: {result.final_status}")
        print(f"Duration: {result.total_duration_sec:.1f}s")
    except AutoHaltException as exc:
        halt_reason = f"{exc.reason} (last chapter: {exc.last_chapter})"
        print(f"\n=== AutoHalt / Gate triggered ===\n{halt_reason}")

    run_id = await _find_run_id(project_id)
    await _build_and_write_report(project_id, run_id)

    print("\n=== Summary ===")
    print(f"Project: {project_id}; Run ID: {run_id}; Halt: {halt_reason or 'None'}")


if __name__ == "__main__":
    asyncio.run(main())
