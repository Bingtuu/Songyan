"""Task 171: Ch1-Ch200 长跑（阶段 Z 第一里程碑，文学=观测，已解冻）.

复用 Task 159 的项目/大纲构造 + 稳定性面验收 harness，把爬坡目标从 Ch150 延到
Ch200。放行判据回到**已验证稳定性面**（T9 硬红线 + continuity health + orphan
斜率 + T12 门禁），**文学 rubric 转 observe**（三层契约 Tier 2，跌破仅建议人工
抽读、不阻塞——见 Task 171d `detect_literary_spot_read`）。

用法:
    # 1. 初始化干净隔离 DB + 创建带大纲项目（与 159 同口径）
    $env:DATABASE_URL = "sqlite:///.tmp/task171_ch1_ch200.db"
    python scripts/run_171_ch200.py --init

    # 2. 无人值守跑 Ch1-Ch200（enforce 门禁，on_failure=isolate）
    python scripts/run_171_ch200.py

    # 中途 kill / AutoHalt 后续跑（复用同一 run_id，跳过已 accepted 章）
    python scripts/run_171_ch200.py --resume

    # 仅从已有 DB 重新生成报告（不跑 LLM）——含三层契约 metrics + 稳定性面验收
    python scripts/run_171_ch200.py --report

    # 小窗口验证（用户偏好：长跑前先小窗口）：END_CHAPTER=5 python scripts/run_171_ch200.py
说明:
    - 稳定性面判据/曲线全部复用 159 harness（evaluate_v6_acceptance）与
      render_stage_a_metrics（含 171d 三层契约摘要），不 fork。
    - 文学 Tier 2 只观测入库（LiteraryAuditor 随跑），不进自动判据（框架 §8 D2）。
    - 产出 docs/reports/task-171-ch200-long-run-report.md。
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

import scripts.run_158_ch1_ch100 as base
import scripts.run_159_ch1_ch150 as t159
from songyan.db import get_db
from songyan.db.connection import get_db_path
from songyan.db.migrations import init_schema
from songyan.db.narrative_repo import NarrativeRepository
from songyan.db.repository import ProjectRepository
from songyan.evals.db_metrics import (
    collect_literary_scores,
    detect_literary_spot_read,
    render_stage_a_metrics,
)
from songyan.evals.streaming_report import read_run_logs
from songyan.evals.v6_acceptance import (
    evaluate_v6_acceptance,
    render_v6_acceptance_section,
)
from songyan.exceptions import AutoHaltException
from songyan.models import GateConfig
from songyan.services.text_cleanliness_cleaner import apply_project_text_cleaning
from songyan.workflows.phase2_graph import run_project_pipeline

DB_PATH = Path(".tmp/task171_ch1_ch200.db")
REPORT_PATH = Path("docs/reports/task-171-ch200-long-run-report.md")
METRICS_PATH = Path(".tmp/task171_ch1_ch200_metrics.jsonl")
PROJECT_FILE = Path(".tmp/task171_project.json")

GATE_MODE = os.getenv("GATE_MODE", "enforce")
ON_FAILURE = os.getenv("ON_FAILURE", "isolate")
LLM_BUDGET = os.getenv("LLM_BUDGET", "0")
START_CHAPTER = int(os.getenv("START_CHAPTER", "1"))
END_CHAPTER = int(os.getenv("END_CHAPTER", "200"))


async def _query_dicts(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
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

    project_id = uuid.uuid4().hex
    await ProjectRepository().create(base._project_setting(), project_id)
    outline, arcs, threads = base._build_outline(project_id)
    await NarrativeRepository().import_outline(project_id, outline, arcs, threads)
    print(f"[init] project {project_id}: {len(arcs)} arcs, {len(threads)} threads")

    PROJECT_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROJECT_FILE.write_text(
        json.dumps({"project_id": project_id, "db": str(db_path.as_posix())}, ensure_ascii=False),
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
            return json.loads(PROJECT_FILE.read_text(encoding="utf-8")).get("project_id")
        except (json.JSONDecodeError, OSError):
            return None
    return None


async def _find_run_id(project_id: str) -> str | None:
    rows = await _query_dicts(
        "SELECT run_id FROM project_runs WHERE project_id = ? "
        "ORDER BY created_at DESC LIMIT 1",
        (project_id,),
    )
    return rows[0]["run_id"] if rows else None


def _resolve_output(args: argparse.Namespace) -> Path | None:
    if args.output:
        return Path(args.output)
    return None


def _render_tier2_observation(spot_read: Any, points: list[Any]) -> str:
    """D2：文学 Tier 2 观测随跑输出（跌破触发人工抽读建议，不阻塞）."""
    lines = ["## 文学 Tier 2 观测（框架 §8 D2；observe-only，不阻塞）", ""]
    lines.append(f"- 观测章数: {len(points)}")
    if not spot_read.baseline_available:
        lines.append("- 基线不足（< 10 章），暂只入库观测、不判趋势地板。")
    elif spot_read.spot_read_recommended:
        dims = "、".join(spot_read.triggered_dimensions)
        lines.append(
            f"- ⚠️ **建议人工抽读**：{dims}"
            f"（跌破 base×{spot_read.relative_floor} 或 <{spot_read.absolute_floor}）"
        )
        for dim in spot_read.triggered_dimensions:
            lines.append(f"  - {dim}：首破窗口起始 Ch{spot_read.first_trigger_window[dim]}")
    else:
        lines.append("- ✓ 各维度在趋势地板之上，无需抽读。")
    lines.append("")
    lines.append("> 文学分为 Tier 2/Tier 3 观测项，**不参与放行判定**；放行只看稳定性面。")
    return "\n".join(lines)


async def _build_and_write_report(
    project_id: str,
    run_id: str | None,
    *,
    output_path: Path | None = None,
    include_legacy_harness: bool = False,
) -> None:
    """复用 159 稳定性面验收 + 三层契约 metrics + D2 文学观测。"""
    completed = await _query_dicts(
        "SELECT DISTINCT chapter_number FROM chapter_versions "
        "WHERE project_id = ? AND version_type='accepted' "
        "AND chapter_number BETWEEN ? AND ? ORDER BY chapter_number",
        (project_id, START_CHAPTER, END_CHAPTER),
    )
    completed_count = len(completed)
    target_count = END_CHAPTER - START_CHAPTER + 1

    run_logs = read_run_logs(run_id) if run_id else []
    stage_a_section = await render_stage_a_metrics(project_id, START_CHAPTER, END_CHAPTER)

    literary_points = await collect_literary_scores(project_id, START_CHAPTER, END_CHAPTER)
    spot_read = detect_literary_spot_read(literary_points)
    tier2_section = _render_tier2_observation(spot_read, literary_points)

    report_path = output_path or REPORT_PATH
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Task 171：Ch{START_CHAPTER}-Ch{END_CHAPTER} 长跑报告（阶段 Z 第一里程碑，文学=观测）",
        "",
        f"- 生成时间: {datetime.now().isoformat()}",
        f"- DB: `{get_db_path()}`",
        f"- 项目 ID: `{project_id}`",
        f"- Run ID: `{run_id}`",
        f"- 章节范围: Ch{START_CHAPTER}-Ch{END_CHAPTER}",
        f"- Gate 模式: {GATE_MODE}；on_failure: {ON_FAILURE}",
        f"- 完成: {completed_count}/{target_count}",
        "",
        "## 放行判据（稳定性面，不含文学 rubric）",
        "",
        "见下方稳定性面验收（T9/health/orphan/T12）；文学 Tier 2 仅观测（下节），不阻塞。",
        "",
        tier2_section,
        "",
        stage_a_section,
    ]
    if include_legacy_harness:
        harness = await evaluate_v6_acceptance(
            project_id, START_CHAPTER, END_CHAPTER, run_id=run_id, run_logs=run_logs
        )
        harness_section = render_v6_acceptance_section(harness)
        lines.extend(["", harness_section])
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[report] {report_path}")
    print(
        f"[report] completed {completed_count}/{target_count}; "
        f"spot_read={spot_read.spot_read_recommended}"
    )


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--init", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--project-id", default=None)
    parser.add_argument("--report", action="store_true", help="仅从已有 DB 重新生成报告")
    parser.add_argument(
        "--run-id",
        default=None,
        help="指定 run_id 生成报告（默认取最新 run）",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="报告输出路径（默认 docs/reports/task-171-ch200-long-run-report.md）",
    )
    parser.add_argument(
        "--include-legacy-harness",
        action="store_true",
        help="保留旧 V6 harness 聚合表（默认不输出，避免旧口径干扰当前判定）",
    )
    parser.add_argument(
        "--clean-d1",
        action="store_true",
        help="Task 171u: 对 accepted head 执行 deterministic D1 清洁并重算报告",
    )
    args = parser.parse_args()

    if args.init:
        await _init_db()
        return

    project_id = args.project_id or _resolve_project_id()
    if not project_id:
        parser.error("请先 --init 创建项目，或提供 --project-id / PROJECT_ID")

    if args.clean_d1:
        results = await apply_project_text_cleaning(project_id, START_CHAPTER, END_CHAPTER)
        changed = [r for r in results if r.changed]
        remaining = sum(len(r.remaining_issues) for r in results)
        print(
            f"[clean-d1] changed={len(changed)} / {len(results)}, "
            f"remaining_issues={remaining}"
        )
        for result in changed:
            print(
                f"[clean-d1] Ch{result.chapter_number}: "
                f"{result.original_version_id} -> {result.cleaned_version_id} "
                f"issues={len(result.issues)}"
            )
        run_id = args.run_id or await _find_run_id(project_id)
        await _build_and_write_report(project_id, run_id, output_path=_resolve_output(args))
        return

    if args.report:
        run_id = args.run_id or await _find_run_id(project_id)
        await _build_and_write_report(
            project_id, run_id,
            output_path=_resolve_output(args),
            include_legacy_harness=args.include_legacy_harness,
        )
        return

    project = await ProjectRepository().get(project_id)
    if project is None:
        raise ValueError(f"Project not found: {project_id}")

    print(f"[preflight] db={get_db_path()} project={project_id}")
    print(
        f"[preflight] gate_mode={GATE_MODE}, on_failure={ON_FAILURE}, "
        f"resume={args.resume}, range=({START_CHAPTER},{END_CHAPTER})"
    )

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
    except AutoHaltException as exc:
        halt_reason = f"{exc.reason} (last chapter: {exc.last_chapter})"
        print(f"\n=== AutoHalt / Gate triggered ===\n{halt_reason}")

    run_id = args.run_id or await _find_run_id(project_id)
    await _build_and_write_report(project_id, run_id, output_path=_resolve_output(args))
    print(
        f"\n=== Summary ===\n"
        f"Project: {project_id}; Run ID: {run_id}; Halt: {halt_reason or 'None'}"
    )


# 保持与 159 harness 的显式关联，避免"未使用导入"并声明复用来源。
_REUSES = (t159.compare_to_baseline, t159.analyze_t5_samples)


if __name__ == "__main__":
    asyncio.run(main())
