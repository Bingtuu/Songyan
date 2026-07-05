"""Task 165: V7 阶段 W 出口 Ch1-Ch150 复跑 + T9/T10 冻结.

用法:
    # 1. 初始化干净隔离 DB + 创建带大纲项目（与 159 同口径骨架）
    $env:DATABASE_URL = "sqlite:///.tmp/task165_stage_w_ch150.db"
    python scripts/run_165_stage_w_ch150.py --init

    # 2. 无人值守跑 Ch1-Ch150（enforce 门禁，on_failure=isolate）
    $env:DATABASE_URL = "sqlite:///.tmp/task165_stage_w_ch150.db"
    python scripts/run_165_stage_w_ch150.py

    # 如中途 kill / AutoHalt，可续跑
    python scripts/run_165_stage_w_ch150.py --resume

    # 仅从已有 DB 重新生成阶段 W 出口报告（不跑 LLM）
    python scripts/run_165_stage_w_ch150.py --report

说明:
    - 本脚本是 Task 165 的执行入口；不会 fork T9/T10 判据。
    - T9 复用 songyan.evals.v6_acceptance.check_t9。
    - T10 复用 Task 147 literary score 回读，并在本脚本中做阶段出口汇总。
    - 产出 docs/reports/task-165-stage-w-exit-report.md。
    - 阈值冻结结论写入报告草案；正式 docs/v7-plan.md 更新需在真实 150 章后执行。
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
from songyan.evals.db_metrics import (
    LiteraryScorePoint,
    collect_literary_scores,
    detect_literary_trend,
    render_literary_section,
    render_stage_a_metrics,
)
from songyan.evals.streaming_report import read_run_logs
from songyan.evals.text_cleanliness import (
    load_text_cleanliness_metrics,
    refresh_text_cleanliness_metrics,
)
from songyan.evals.v6_acceptance import (
    ThresholdResult,
    V6AcceptanceResult,
    evaluate_v6_acceptance,
    render_v6_acceptance_section,
)
from songyan.exceptions import AutoHaltException
from songyan.models import GateConfig
from songyan.workflows.phase2_graph import run_project_pipeline

DB_PATH = Path(".tmp/task165_stage_w_ch150.db")
REPORT_PATH = Path("docs/reports/task-165-stage-w-exit-report.md")
CALIBRATION_REPORT_PATH = Path("docs/reports/task-165-v7-threshold-calibration.md")
METRICS_PATH = Path(".tmp/task165_stage_w_ch150_metrics.jsonl")
PROJECT_FILE = Path(".tmp/task165_project.json")

GATE_MODE = os.getenv("GATE_MODE", "enforce")
ON_FAILURE = os.getenv("ON_FAILURE", "isolate")
LLM_BUDGET = os.getenv("LLM_BUDGET", "0")
START_CHAPTER = int(os.getenv("START_CHAPTER", "1"))
END_CHAPTER = int(os.getenv("END_CHAPTER", "150"))

V6_BASELINE_META_LEAK_CHAPTERS = 52
V6_BASELINE_DUPLICATE_CHAPTERS = 19
DEFAULT_T10_COEFFICIENT = 0.85


class T10Calibration(BaseModel):
    """T10 conceptual_grounding 首/末窗口校准结果."""

    coefficient: float = DEFAULT_T10_COEFFICIENT
    sufficient: bool
    first_window_mean: float | None = None
    last_window_mean: float | None = None
    threshold: float | None = None
    passed: bool | None
    detail: str


class T9Calibration(BaseModel):
    """T9 洁净度冻结决策草案."""

    include_timeline_in_redline: bool
    passed: bool | None
    measured: str | None
    detail: str


class StageWExitRow(BaseModel):
    """阶段 W 出口报告单行."""

    item: str
    criterion: str
    evidence: str
    passed: bool | None
    measured: str
    detail: str


def _flag(state: bool | None) -> str:
    return "✅ pass" if state is True else ("🔴 fail" if state is False else "◯ 未判定")


def _result(result: V6AcceptanceResult, key: str) -> ThresholdResult | None:
    return next((item for item in result.results if item.key == key), None)


def evaluate_t10_calibration(
    points: list[LiteraryScorePoint],
    *,
    coefficient: float = DEFAULT_T10_COEFFICIENT,
    window: int = 5,
) -> T10Calibration:
    """T10：conceptual_grounding 末段 W=5 均值 ≥ 首段 W=5 × coefficient."""
    ordered = sorted(points, key=lambda item: item.chapter)
    if len(ordered) < window * 2:
        return T10Calibration(
            coefficient=coefficient,
            sufficient=False,
            passed=None,
            detail=f"文学分数样本不足（{len(ordered)} < {window * 2}）",
        )
    first = ordered[:window]
    last = ordered[-window:]
    first_mean = sum(p.conceptual_grounding_score for p in first) / window
    last_mean = sum(p.conceptual_grounding_score for p in last) / window
    threshold = first_mean * coefficient
    passed = last_mean >= threshold
    return T10Calibration(
        coefficient=coefficient,
        sufficient=True,
        first_window_mean=round(first_mean, 4),
        last_window_mean=round(last_mean, 4),
        threshold=round(threshold, 4),
        passed=passed,
        detail=(
            f"首段 W={window} 均值 {first_mean:.2f}；末段 W={window} 均值 "
            f"{last_mean:.2f}；阈值 {threshold:.2f}（×{coefficient}）"
        ),
    )


def _count_chapters_with(value_getter, rows: list[Any]) -> int:
    return sum(1 for row in rows if value_getter(row) > 0)


async def _collect_stage_w_rows(
    *,
    project_id: str,
    run_id: str | None,
    run_logs: list[Any],
    include_timeline_in_redline: bool,
) -> tuple[list[StageWExitRow], V6AcceptanceResult, T9Calibration, T10Calibration, str]:
    """从当前 DB 采集阶段 W 出口四项表格数据."""
    await refresh_text_cleanliness_metrics(project_id, START_CHAPTER, END_CHAPTER)
    cleanliness = await load_text_cleanliness_metrics(project_id, START_CHAPTER, END_CHAPTER)
    literary_points = await collect_literary_scores(project_id, START_CHAPTER, END_CHAPTER)
    stage_a_section = await render_stage_a_metrics(project_id, START_CHAPTER, END_CHAPTER)
    harness = await evaluate_v6_acceptance(
        project_id,
        START_CHAPTER,
        END_CHAPTER,
        run_id=run_id,
        run_logs=run_logs,
        t9_include_timeline_in_redline=include_timeline_in_redline,
    )
    t9_result = _result(harness, "T9")
    t9 = T9Calibration(
        include_timeline_in_redline=include_timeline_in_redline,
        passed=t9_result.passed if t9_result else None,
        measured=str(t9_result.measured) if t9_result and t9_result.measured is not None else None,
        detail=t9_result.detail if t9_result else "T9 未生成",
    )
    t10 = evaluate_t10_calibration(literary_points)

    meta_chapters = _count_chapters_with(lambda row: row.meta_tag_leak_count, cleanliness)
    duplicate_chapters = _count_chapters_with(
        lambda row: row.duplicate_paragraph_count, cleanliness
    )
    timeline_chapters = _count_chapters_with(lambda row: row.timeline_conflict_count, cleanliness)
    accepted = _result(harness, "T2")
    t3 = _result(harness, "T3/T8")
    t4 = _result(harness, "T4")
    t5 = _result(harness, "T5")
    t6a = _result(harness, "T6a")
    t6b = _result(harness, "T6b")
    t6c = _result(harness, "T6c")

    p_passed = t9.passed
    l_passed = (t10.passed is True) and (t3.passed is not False if t3 else False)
    repair_passed = (
        meta_chapters == 0
        and duplicate_chapters == 0
        and (t10.passed is True or t10.passed is None)
    )
    no_regression = all(
        item is not None and item.passed is not False
        for item in (accepted, t3, t4, t5, t6a, t6b, t6c)
    )

    rows = [
        StageWExitRow(
            item="P 洁净",
            criterion="accepted 正文元标记=0、重复长段落=0，时间线按冻结口径",
            evidence="check_t9 + text_cleanliness_metrics",
            passed=p_passed,
            measured=t9.measured or "-",
            detail=t9.detail,
        ),
        StageWExitRow(
            item="L 文学",
            criterion="conceptual_grounding 末段 W=5 ≥ 首段 W=5 ×0.85，且 T3/T8 不破",
            evidence="collect_literary_scores + T3/T8",
            passed=l_passed if t10.sufficient else None,
            measured=(
                f"first={t10.first_window_mean}, last={t10.last_window_mean}, "
                f"threshold={t10.threshold}"
                if t10.sufficient
                else "-"
            ),
            detail=f"{t10.detail}；T3/T8={t3.passed if t3 else 'N/A'}",
        ),
        StageWExitRow(
            item="修复对比",
            criterion="vs run-bba292da：52→0 元标记、19→0 重复，时间线收敛，grounding 止跌",
            evidence="text_cleanliness_metrics + T10",
            passed=repair_passed if cleanliness else None,
            measured=(
                f"meta {V6_BASELINE_META_LEAK_CHAPTERS}→{meta_chapters}; "
                f"duplicate {V6_BASELINE_DUPLICATE_CHAPTERS}→{duplicate_chapters}; "
                f"timeline_chapters={timeline_chapters}"
            ),
            detail="真实 150 章后据此判定是否清零/收敛。",
        ),
        StageWExitRow(
            item="不回退",
            criterion="T2/T3/T4/T5/T6 不因阶段 W 修复回退",
            evidence="evaluate_v6_acceptance",
            passed=no_regression,
            measured=(
                f"T2={accepted.passed if accepted else 'N/A'}; "
                f"T3={t3.passed if t3 else 'N/A'}; "
                f"T4={t4.passed if t4 else 'N/A'}; "
                f"T5={t5.passed if t5 else 'N/A'}; "
                f"T6a={t6a.passed if t6a else 'N/A'}; "
                f"T6b={t6b.passed if t6b else 'N/A'}; "
                f"T6c={t6c.passed if t6c else 'N/A'}"
            ),
            detail="任一 sufficient 项 fail 即视为回退。",
        ),
    ]
    return rows, harness, t9, t10, stage_a_section


def summarize_stage_w_exit(rows: list[StageWExitRow]) -> tuple[str, list[str]]:
    """给阶段 W 出口总结论。"""
    blockers = [row.item for row in rows if row.passed is False]
    undecided = [row.item for row in rows if row.passed is None]
    if blockers:
        return (
            f"🔴 **阶段 W 条件不通过**：阻断项 {', '.join(blockers)}"
            + (f"；待判定 {', '.join(undecided)}" if undecided else ""),
            blockers,
        )
    if undecided:
        return (
            f"◯ **阶段 W 条件通过（含待判定项）**：{', '.join(undecided)} 需真实 150 章补足证据",
            [],
        )
    return ("✅ **阶段 W 通过**：P/L/修复对比/不回退全部满足，T9/T10 可冻结", [])


def render_stage_w_exit_section(rows: list[StageWExitRow]) -> str:
    """渲染阶段 W 出口四项核对表。"""
    lines = [
        "## 阶段 W 出口核对（P/L/修复对比/不回退）",
        "",
        "| 项 | 判据 | 结论 | 实测 | 证据 | 详情 |",
        "|----|------|------|------|------|------|",
    ]
    for row in rows:
        lines.append(
            f"| **{row.item}** | {row.criterion} | {_flag(row.passed)} | "
            f"{row.measured} | {row.evidence} | {row.detail} |"
        )
    verdict, _ = summarize_stage_w_exit(rows)
    lines.extend(["", "### 总结论", "", verdict])
    return "\n".join(lines)


def render_threshold_freeze_section(t9: T9Calibration, t10: T10Calibration) -> str:
    """渲染 T9/T10 标定与冻结结论。"""
    t9_timeline = "纳入硬红线" if t9.include_timeline_in_redline else "仅报告不计红线"
    lines = [
        "## T9/T10 阈值标定与冻结结论",
        "",
        "### T9 文本洁净度",
        "",
        "- 元标记=0、重复长段落=0：结构性硬红线。",
        f"- 时间线矛盾口径：**{t9_timeline}**。",
        f"- 当前 T9 结果：{_flag(t9.passed)}；实测：{t9.measured or '-'}；{t9.detail}",
        "",
        "### T10 文学不衰减",
        "",
        f"- 默认系数：×{t10.coefficient}",
        f"- 当前结果：{_flag(t10.passed)}；{t10.detail}",
        "",
        "> 冻结纪律：本结论基于 Task 165 / 165p 的真实 Ch150 修复后基线；"
        "不得在后续长跑撞线后临时放宽。",
    ]
    return "\n".join(lines)


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


async def _query_dicts(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    async with get_db() as conn:
        conn.row_factory = lambda cursor, row: {
            col[0]: row[i] for i, col in enumerate(cursor.description)
        }
        cursor = await conn.execute(sql, params)
        return await cursor.fetchall()


async def _find_run_id(project_id: str) -> str | None:
    rows = await _query_dicts(
        """SELECT run_id FROM project_runs
           WHERE project_id = ?
           ORDER BY created_at DESC LIMIT 1""",
        (project_id,),
    )
    return rows[0]["run_id"] if rows else None


def _append_metric(record: dict[str, Any]) -> None:
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with METRICS_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


async def _build_and_write_report(
    project_id: str,
    run_id: str | None,
    *,
    include_timeline_in_redline: bool = False,
) -> None:
    accepted = await base._load_accepted_versions(project_id)  # type: ignore[attr-defined]
    run_log = base._load_run_log_metrics(run_id)  # type: ignore[attr-defined]
    chapters: list[dict[str, Any]] = []
    for chapter in sorted(set(list(accepted.keys()) + list(run_log.keys()))):
        if chapter < START_CHAPTER or chapter > END_CHAPTER:
            continue
        version = accepted.get(chapter)
        log = run_log.get(chapter, {})
        record = {
            "chapter": chapter,
            "accepted": chapter in accepted,
            "word_count": version.word_count if version else log.get("word_count"),
            "quality_gate_passed": log.get("quality_gate_passed"),
            "context_emergency": log.get("context_emergency"),
            "duration_sec": log.get("duration_sec"),
        }
        chapters.append(record)
        _append_metric(record)

    run_logs = read_run_logs(run_id) if run_id else []
    rows, harness, t9, t10, stage_a_section = await _collect_stage_w_rows(
        project_id=project_id,
        run_id=run_id,
        run_logs=run_logs,
        include_timeline_in_redline=include_timeline_in_redline,
    )
    literary_points = await collect_literary_scores(
        project_id, START_CHAPTER, END_CHAPTER
    )
    literary_trend = detect_literary_trend(literary_points)
    report_lines = [
        "# Task 165：V7 阶段 W 出口报告（Ch1-Ch150 修复后复跑）",
        "",
        f"- 生成时间: {datetime.now().isoformat()}",
        f"- DB: `{get_db_path()}`",
        f"- 项目 ID: `{project_id}`",
        f"- Run ID: `{run_id}`（必须非 `run-bba292da`）",
        f"- 章节范围: Ch{START_CHAPTER}-Ch{END_CHAPTER}",
        f"- Gate 模式: {GATE_MODE}；on_failure: {ON_FAILURE}",
        f"- 当前 accepted: {sum(1 for item in chapters if item['accepted'])}/"
        f"{END_CHAPTER - START_CHAPTER + 1}",
        "",
        render_stage_w_exit_section(rows),
        "",
        render_threshold_freeze_section(t9, t10),
        "",
        render_literary_section(literary_points, literary_trend),
        "",
        stage_a_section,
        "",
        render_v6_acceptance_section(harness),
    ]
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    CALIBRATION_REPORT_PATH.write_text(
        render_threshold_freeze_section(t9, t10) + "\n",
        encoding="utf-8",
    )
    print(f"[report] {REPORT_PATH}")
    print(f"[calibration] {CALIBRATION_REPORT_PATH}")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--init", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--project-id", default=None)
    parser.add_argument("--report", action="store_true", help="仅从已有 DB 重新生成报告")
    parser.add_argument(
        "--include-timeline-in-redline",
        action="store_true",
        help="报告生成时把时间线矛盾计入 T9 红线（默认仅报告）",
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
        await _build_and_write_report(
            project_id,
            run_id,
            include_timeline_in_redline=args.include_timeline_in_redline,
        )
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
    await _build_and_write_report(
        project_id,
        run_id,
        include_timeline_in_redline=args.include_timeline_in_redline,
    )
    print(
        f"\n=== Summary ===\nProject: {project_id}; "
        f"Run ID: {run_id}; Halt: {halt_reason or 'None'}"
    )


if __name__ == "__main__":
    asyncio.run(main())
