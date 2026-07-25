"""Task 172b: xuanhuan Ch100 长跑爬坡验证（V8 V 维度）.

复用 run_158 的编排思路，但：
- 项目初始化改用 ProjectInitializer.from_template("xuanhuan")（自动导入 9-arc/3-thread 骨架），
  不再手搓 outline。
- runtime_profile 由 pipeline 按 genre 自动加载
  （xuanhuan base=15000, foreshadowing_horizon_floor=48）。
- 分段爬坡（默认每 25 章一段 = arc 边界），段间读 DB 汇总
  budget/overdue/health/CED，任一段触发 halt 或指标劣化即停并路由 172b.p。

用法:
    # 初始化干净 DB + 从模板建项目（含骨架）
    python scripts/run_172b_ch100_climb.py --init

    # 无人值守分段跑到 Ch100（enforce, isolate, resume 续跑）
    python scripts/run_172b_ch100_climb.py --to 100

    # 只跑一段（调参/排障）
    python scripts/run_172b_ch100_climb.py --to 25
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from songyan.config import settings
from songyan.db.connection import get_db, get_db_path
from songyan.db.migrations import init_schema
from songyan.db.repository import (
    ChapterHeadRepository,
    ChapterVersionRepository,
    ProjectRepository,
)
from songyan.exceptions import AutoHaltException
from songyan.llm.client import aclose_llm_clients
from songyan.models import GateConfig
from songyan.project_templates import ProjectInitializer, ProjectTemplateLoader
from songyan.utils.logging_setup import configure_logging
from songyan.utils.process_exit import force_exit_after_run_if_requested
from songyan.workflows.phase2_graph import run_project_pipeline

TEMPLATE_ID = os.getenv("TEMPLATE_ID", "xuanhuan")
RUN_ID = os.getenv("RUN_ID", "172b")
SEGMENT = int(os.getenv("SEGMENT", "25"))
HALT_RETRIES = int(os.getenv("HALT_RETRIES", "2"))
ON_FAILURE = os.getenv("ON_FAILURE", "abort" if RUN_ID == "192" else "isolate")
DB_PATH = Path(f".tmp/task172b_{TEMPLATE_ID}_ch100.db")
PROJECT_FILE = Path(f".tmp/task172b_{TEMPLATE_ID}_project.json")
REPORT_PATH = Path(f"docs/reports/{RUN_ID}-{TEMPLATE_ID}-ch100-climb.md")
METRICS_PATH = Path(f".tmp/task172b_{TEMPLATE_ID}_segments.jsonl")


def _task_label() -> str:
    return f"Task {RUN_ID}"


def _force_exit_enabled_for_harness() -> bool:
    if "SONGYAN_FORCE_EXIT" in os.environ or "FORCE_EXIT_AFTER_RUN" in os.environ:
        return settings.force_exit_after_run
    return True


def _halt_route() -> str:
    explicit = os.getenv("HALT_ROUTE")
    if explicit:
        return explicit
    return {"172b": "172b.p", "172c": "172c.t"}.get(RUN_ID, f"{RUN_ID}.p")


def _word_count(content: str) -> int:
    chinese = len(re.findall(r"[\u4e00-\u9fff]", content))
    other = len(re.findall(r"[a-zA-Z0-9]+", content))
    return chinese + other


async def _init_db() -> str:
    settings.database_url = f"sqlite:///{DB_PATH.as_posix()}"
    db_path = get_db_path()
    for suffix in ("", "-wal", "-shm"):
        p = db_path.with_name(db_path.name + suffix) if suffix else db_path
        if p.exists():
            p.unlink()
            print(f"[init] removed {p}")
    await init_schema()
    template = ProjectTemplateLoader().load(TEMPLATE_ID)
    project_id, project = await ProjectInitializer.from_template(template)
    print(f"[init] template={TEMPLATE_ID} project={project_id} genre={project.genre_id}")

    # 确认骨架已导入
    async with get_db() as conn:
        cur = await conn.execute(
            "SELECT COUNT(*) FROM arc_plans WHERE project_id = ?", (project_id,)
        )
        arc_count = (await cur.fetchone())[0]
        cur = await conn.execute(
            "SELECT COUNT(*) FROM plot_threads WHERE project_id = ?", (project_id,)
        )
        thread_count = (await cur.fetchone())[0]
    print(f"[init] skeleton: {arc_count} arcs, {thread_count} threads")

    PROJECT_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROJECT_FILE.write_text(
        json.dumps({"project_id": project_id, "db": str(db_path.as_posix())}, ensure_ascii=False),
        encoding="utf-8",
    )
    return project_id


def _resolve_project_id() -> str | None:
    if PROJECT_FILE.exists():
        try:
            return json.loads(PROJECT_FILE.read_text(encoding="utf-8")).get("project_id")
        except (json.JSONDecodeError, OSError):
            return None
    return None


async def _segment_metrics(project_id: str, up_to: int) -> dict[str, Any]:
    """读取一段结束时的 budget/overdue/health/CED 汇总."""
    async with get_db() as conn:
        # budget
        cur = await conn.execute(
            """SELECT chapter_number, budget_used, context_emergency,
                      budget_used_before_emergency
               FROM context_snapshots
               WHERE project_id = ? AND chapter_number BETWEEN 1 AND ?
               ORDER BY chapter_number""",
            (project_id, up_to),
        )
        rows = await cur.fetchall()
        peak = 0.0
        peak_before = 0.0
        emergencies = 0
        for r in rows:
            peak = max(peak, float(r[1] or 0.0))
            if r[2]:
                emergencies += 1
            if r[3] is not None:
                peak_before = max(peak_before, float(r[3]))

        # overdue foreshadowing
        cur = await conn.execute(
            """SELECT COUNT(*) FROM foreshadowings
               WHERE project_id = ? AND expected_resolve_chapter IS NOT NULL
                 AND expected_resolve_chapter < ? AND status != 'resolved'""",
            (project_id, up_to),
        )
        overdue = (await cur.fetchone())[0]

        # health (latest continuity report <= up_to)
        cur = await conn.execute(
            """SELECT overall_health_score FROM continuity_reports
               WHERE project_id = ? AND checked_up_to_chapter <= ?
               ORDER BY checked_up_to_chapter DESC LIMIT 1""",
            (project_id, up_to),
        )
        hrow = await cur.fetchone()
        health = float(hrow[0]) if hrow and hrow[0] is not None else None

    # CED + accepted count via repos
    head_repo = ChapterHeadRepository()
    version_repo = ChapterVersionRepository()
    total_words = 0
    accepted = 0
    for ch in range(1, up_to + 1):
        head = await head_repo.get(project_id, ch)
        if head and head.status == "accepted" and head.accepted_version_id:
            v = await version_repo.get(head.accepted_version_id)
            if v:
                total_words += _word_count(v.content)
                accepted += 1
    issue_count = 0
    async with get_db() as conn:
        cur = await conn.execute(
            """SELECT rr.issues FROM review_reports rr
               JOIN chapter_versions cv ON cv.version_id = rr.chapter_version_id
               WHERE cv.project_id = ?""",
            (project_id,),
        )
        for row in await cur.fetchall():
            try:
                issues = json.loads(row[0] or "[]")
            except (json.JSONDecodeError, TypeError):
                continue
            for issue in issues:
                sev = str(issue.get("severity", "")).lower()
                if sev in ("critical", "major") and issue.get("evidence_quote"):
                    issue_count += 1
    ced = round(issue_count / total_words * 1000, 4) if total_words else 0.0

    return {
        "up_to": up_to,
        "accepted": accepted,
        "budget_used_peak": round(peak, 4),
        "budget_used_before_emergency_peak": round(peak_before, 4),
        "context_emergency_count": emergencies,
        "overdue_foreshadowing": overdue,
        "health_latest": health,
        "ced_per_1k_words": ced,
        "total_words": total_words,
    }


def _append_metric(record: dict[str, Any]) -> None:
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with METRICS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--init", action="store_true")
    parser.add_argument("--to", type=int, default=100, help="爬坡目标章")
    args = parser.parse_args()

    if args.init:
        await _init_db()
        return

    settings.database_url = f"sqlite:///{DB_PATH.as_posix()}"
    project_id = _resolve_project_id()
    if not project_id:
        parser.error("请先 --init")
    project = await ProjectRepository().get(project_id)
    if project is None:
        raise ValueError(f"project not found: {project_id}")

    gate_config = GateConfig.for_mode("enforce")
    print(
        f"[climb] project={project_id} genre={project.genre_id} "
        f"to=Ch{args.to} seg={SEGMENT} on_failure={ON_FAILURE}"
    )

    segments: list[dict[str, Any]] = []
    halt_reason: str | None = None
    seg_start = 1
    while seg_start <= args.to:
        seg_end = min(seg_start + SEGMENT - 1, args.to)
        print(f"\n=== segment Ch{seg_start}-Ch{seg_end} ===")
        # 段内 halt 自动重试：LLM 随机波动（修订不收敛/hook 误伤等）触发的
        # AutoHalt 可通过 resume 从失败章重新生成恢复；重试耗尽才停爬路由人工。
        halt_reason = None
        for attempt in range(HALT_RETRIES + 1):
            try:
                result = await run_project_pipeline(
                    project_id=project_id,
                    chapter_range=(1, seg_end),
                    mode_id=project.mode_id,
                    auto_confirm=True,
                    on_failure=ON_FAILURE,
                    gate_config=gate_config,
                    resume=True,
                )
                print(f"completed={len(result.chapters_completed)} failed={result.chapters_failed}")
                if result.chapters_failed and ON_FAILURE in {"abort", "retry"}:
                    halt_reason = (
                        f"chapter_failed_abort: {result.chapters_failed}"
                    )
                    print(
                        "=== stopping climb due to failed chapters "
                        f"-> route {_halt_route()} ==="
                    )
                    break
                halt_reason = None
                break
            except AutoHaltException as exc:
                halt_reason = f"{exc.reason} (last chapter {exc.last_chapter})"
                print(f"=== AutoHalt attempt {attempt + 1}/{HALT_RETRIES + 1}: {halt_reason} ===")

        metrics = await _segment_metrics(project_id, seg_end)
        metrics["halt"] = halt_reason
        segments.append(metrics)
        _append_metric(metrics)
        print(json.dumps(metrics, ensure_ascii=False, indent=2))

        if halt_reason:
            print(
                "=== stopping climb due to halt/failed chapter "
                f"-> route {_halt_route()} ==="
            )
            break
        seg_start = seg_end + 1

    _write_report(project_id, project.genre_id, args.to, segments, halt_reason)


def _write_report(
    project_id: str, genre: str, target: int,
    segments: list[dict[str, Any]], halt_reason: str | None,
) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# {_task_label()}: {genre} Ch{target} 爬坡验证报告",
        "",
        f"- 生成时间: {datetime.now().isoformat()}",
        f"- 项目: `{project_id}`  体裁: `{genre}`  目标: Ch{target}",
        f"- Gate: enforce / {ON_FAILURE} / resume  Halt: {halt_reason or 'None'}",
        "",
        "## 分段指标",
        "",
        "| up_to | accepted | budget_peak | before_emerg_peak | emerg | overdue "
        "| health | CED/1k |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for s in segments:
        lines.append(
            f"| {s['up_to']} | {s['accepted']} | {s['budget_used_peak']} | "
            f"{s['budget_used_before_emergency_peak']} | {s['context_emergency_count']} | "
            f"{s['overdue_foreshadowing']} | {s.get('health_latest')} | {s['ced_per_1k_words']} |"
        )
    lines.extend(["", "## 结论", ""])
    if halt_reason:
        lines.append(
            f"爬坡在中途触发 halt：{halt_reason}。"
            f"按纪律路由 {_halt_route()} 定点修复，不放宽口径。"
        )
    elif segments and segments[-1]["up_to"] == target and segments[-1]["accepted"] == target:
        lines.append(f"Ch{target} 全 accepted 达标，无 halt。V 维度证据见上表。")
    else:
        lines.append("未达标（见分段表），检查失败清单与日志。")
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[report] {REPORT_PATH}")


if __name__ == "__main__":
    configure_logging(settings.log_level, file_level=settings.log_file_level)
    asyncio.run(main())
    asyncio.run(aclose_llm_clients())
    force_exit_after_run_if_requested(enabled=_force_exit_enabled_for_harness())
