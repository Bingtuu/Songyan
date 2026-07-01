"""Task 139c: Enforce 模式 Ch51-Ch150 长窗口实跑验证.

用法:
    # 复用 Task 139b 的项目继续跑 Ch51-Ch150
    $env:DATABASE_URL = "sqlite:///.tmp/task139b_enforce_ch1_ch50_rerun2.db"
    $env:PROJECT_ID = "6dde3f9083f54725b867a6100cefc7eb"
    $env:GATE_MODE = "enforce"
    python scripts/run_139c_enforce_ch51_ch150.py

说明:
    - 必须先用 Task 139b 创建项目并跑完 Ch1-Ch50。
    - 使用与 139b 相同的 DB 与项目 ID，不创建新项目。
    - gate_mode="enforce"，触发 gate 即暂停 run。
    - 生成 docs/reports/task-139c-enforce-ch51-ch150-validation-report.md。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from songyan.db import get_db
from songyan.db.connection import get_db_path
from songyan.db.continuity_repo import ContinuityReportRepository
from songyan.db.repository import (
    ChapterVersionRepository,
    ProjectRepository,
)
from songyan.exceptions import AutoHaltException
from songyan.models import GateConfig
from songyan.workflows.phase2_graph import run_project_pipeline

DB_PATH = Path(".tmp/task139b_enforce_ch1_ch50_rerun2.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")
GATE_MODE = os.getenv("GATE_MODE", "enforce")
REPORT_PATH = Path(
    "docs/reports/task-139c-enforce-ch51-ch150-validation-report.md"
)
METRICS_PATH = Path(".tmp/task139c_ch51_ch150_metrics.jsonl")

START_CHAPTER = int(os.getenv("START_CHAPTER", "51"))
END_CHAPTER = int(os.getenv("END_CHAPTER", "150"))


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
           ORDER BY created_at DESC
           LIMIT 1""",
        (project_id,),
    )
    return rows[0]["run_id"] if rows else None


async def _load_accepted_versions(project_id: str) -> dict[int, Any]:
    repo = ChapterVersionRepository()
    result: dict[int, Any] = {}
    rows = await _query_dicts(
        """SELECT * FROM chapter_versions
           WHERE project_id = ?
             AND version_type IN ('accepted', 'revision', 'edited')
             AND is_abandoned = 0
           ORDER BY chapter_number, version_number""",
        (project_id,),
    )
    for row in rows:
        ch = row["chapter_number"]
        result[ch] = await repo.get(row["version_id"])
    return result


async def _load_settlement_counts(project_id: str) -> dict[int, dict[str, int]]:
    counts: dict[int, dict[str, int]] = defaultdict(
        lambda: {"character_states": 0, "numerical_ledgers": 0}
    )
    rows = await _query_dicts(
        """SELECT cv.chapter_number, COUNT(cs.state_id) AS cnt
           FROM chapter_versions cv
           LEFT JOIN character_states cs ON cs.source_version_id = cv.version_id
           WHERE cv.project_id = ? AND cv.version_type = 'accepted'
           GROUP BY cv.chapter_number""",
        (project_id,),
    )
    for row in rows:
        counts[row["chapter_number"]]["character_states"] = row["cnt"]
    rows = await _query_dicts(
        """SELECT chapter_number, COUNT(*) AS cnt
           FROM numerical_ledgers
           WHERE project_id = ?
           GROUP BY chapter_number""",
        (project_id,),
    )
    for row in rows:
        counts[row["chapter_number"]]["numerical_ledgers"] = row["cnt"]
    return dict(counts)


async def _load_continuity_reports(project_id: str) -> list[dict[str, Any]]:
    reports = await ContinuityReportRepository().list_by_chapter_range(
        project_id, START_CHAPTER, END_CHAPTER
    )
    return [
        {
            "chapter": r.checked_up_to_chapter,
            "health_score": r.overall_health_score,
            "orphaned_count": len(r.orphaned_settings),
            "forgotten_count": len(r.forgotten_items),
            "mismatch_count": len(r.state_mismatches),
            "overdue_count": len(r.overdue_foreshadowings),
            "p1": sum(
                1
                for s in r.orphaned_settings
                if getattr(s, "category", "background") == "critical"
            )
            + len(r.state_mismatches),
            "p2": sum(
                1
                for s in r.orphaned_settings
                if getattr(s, "category", "background") == "recurring"
            )
            + len(r.overdue_foreshadowings),
            "p3": sum(
                1
                for s in r.orphaned_settings
                if getattr(s, "category", "background")
                not in ("critical", "recurring")
            )
            + len(r.forgotten_items),
        }
        for r in reports
    ]


def _fmt(value: Any) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def _fmt_bool(value: bool | None) -> str:
    if value is True:
        return "Y"
    if value is False:
        return "N"
    return ""


def _load_run_log_metrics(run_id: str | None) -> dict[int, dict[str, Any]]:
    metrics: dict[int, dict[str, Any]] = {}
    if run_id is None:
        return metrics
    path = Path(f"logs/chapter_runs/{run_id}.jsonl")
    if not path.exists():
        return metrics
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        ch = entry.get("chapter_number")
        if not isinstance(ch, int):
            continue
        metrics[ch] = {
            "success": entry.get("success"),
            "settlement_success": entry.get("settlement_success"),
            "summary_success": entry.get("summary_success"),
            "quality_gate_passed": entry.get("quality_gate_passed"),
            "skip_settlement": entry.get("skip_settlement"),
            "revision_rounds": entry.get("revision_rounds"),
            "rule_violations": entry.get("rule_violations"),
            "llm_audit_issues": entry.get("llm_audit_issues"),
            "llm_audit_critical": entry.get("llm_audit_critical"),
            "gate_triggered": entry.get("gate_triggered"),
            "gate_reasons": entry.get("gate_reasons") or [],
            "budget_used": entry.get("budget_used"),
            "context_emergency": entry.get("context_emergency"),
            "duration_sec": entry.get("duration_sec"),
            "word_count": entry.get("word_count"),
            "continuity_health_score": entry.get("continuity_health_score"),
        }
    return metrics


def _write_report(
    project_id: str,
    run_id: str | None,
    halt_reason: str | None,
    chapters: list[dict[str, Any]],
    continuity: list[dict[str, Any]],
) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    completed = [c for c in chapters if c.get("accepted")]
    failed = [c for c in chapters if not c.get("accepted")]
    settlement_ok = [c for c in chapters if c.get("settlement_success") is True]
    qg_ok = [c for c in chapters if c.get("quality_gate_passed") is True]
    duration_total = sum(c.get("duration_sec") or 0 for c in chapters)
    target_count = END_CHAPTER - START_CHAPTER + 1
    gate_triggers = [c for c in chapters if c.get("gate_triggered")]
    emergency_chapters = [c for c in chapters if c.get("context_emergency")]

    lines: list[str] = [
        "# Task 139c：Enforce 模式 Ch51-Ch150 长窗口实跑验证报告",
        "",
        f"- 生成时间: {datetime.now().isoformat()}",
        f"- DB: `{get_db_path()}`",
        f"- 项目 ID: `{project_id}`",
        f"- Run ID: `{run_id}`",
        f"- 章节范围: Ch{START_CHAPTER}-Ch{END_CHAPTER}",
        f"- Gate 模式: {GATE_MODE}",
        f"- Halt 原因: {halt_reason or 'None'}",
        "",
        "## 总体统计",
        "",
        f"- 完成/目标: {len(completed)} / {target_count}",
        f"- 失败章节: {[c['chapter'] for c in failed]}",
        f"- settlement 成功: {len(settlement_ok)} / {len(chapters)}",
        f"- QG 通过: {len(qg_ok)} / {len(chapters)}",
        f"- Gate 触发章节: {len(gate_triggers)}",
        f"- Context Emergency 章节: {len(emergency_chapters)} { [c['chapter'] for c in emergency_chapters]}",
        f"- 总耗时: {duration_total:.1f}s ({duration_total / 60:.1f} min)",
        "",
        "## 每章关键指标",
        "",
        "| Ch | Word | Scenes | Settlement | Summary | QG | Revisions | "
        "Rule | LLM | Gate | Budget | Emergency | Dur(s) |",
        "|---:|---:|---:|:---|:---|:---|---:|---:|---:|:---|---:|:---|---:|",
    ]
    for c in chapters:
        lines.append(
            f"| {c['chapter']} | {c.get('word_count', '')} | "
            f"{c.get('scenes_count', '')} | "
            f"{_fmt_bool(c.get('settlement_success'))} | "
            f"{_fmt_bool(c.get('summary_success'))} | "
            f"{_fmt_bool(c.get('quality_gate_passed'))} | "
            f"{c.get('revision_rounds', '')} | "
            f"{c.get('rule_violations', '')} | "
            f"{c.get('llm_audit_issues', '')} | "
            f"{_fmt_bool(c.get('gate_triggered'))} | "
            f"{_fmt(c.get('budget_used'))} | "
            f"{_fmt_bool(c.get('context_emergency'))} | "
            f"{c.get('duration_sec', '')} |"
        )

    lines.extend(["", "## Continuity 趋势", ""])
    lines.append(
        "| Ch | Health | Orphaned | Forgotten | Mismatches | Overdue | P1 | P2 | P3 |"
    )
    lines.append("|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in continuity:
        lines.append(
            f"| {r['chapter']} | {_fmt(r['health_score'])} | {r['orphaned_count']} | "
            f"{r['forgotten_count']} | {r['mismatch_count']} | {r['overdue_count']} | "
            f"{r['p1']} | {r['p2']} | {r['p3']} |"
        )

    lines.extend(["", "## 结论", ""])
    if halt_reason:
        lines.append(
            f"实跑触发 halt：{halt_reason}。需根据根因决定是否新建修复任务。"
        )
    elif len(completed) == target_count:
        lines.append(
            f"Ch{START_CHAPTER}-Ch{END_CHAPTER} 全部完成，无 AutoHalt。"
            " enforce 模式在 Ch1-Ch150 长窗口验证通过，可执行 Task 139d 切换 CLI 默认 gate_mode。"
        )
    else:
        lines.append(
            f"未完成全部章节（完成 {len(completed)}/{target_count}），未触发 AutoHalt，请检查日志。"
        )

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[report] {REPORT_PATH}")


def _append_metric(record: dict[str, Any]) -> None:
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with METRICS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--project-id",
        default=os.getenv("PROJECT_ID"),
        help="Task 139b 创建的项目 ID",
    )
    args = parser.parse_args()

    project_id = args.project_id or os.getenv("PROJECT_ID")
    if not project_id:
        parser.error("必须提供 --project-id 或设置 PROJECT_ID 环境变量")

    db_path = get_db_path()
    print(f"[preflight] db={db_path}")
    print(f"[preflight] project={project_id}, range=({START_CHAPTER}, {END_CHAPTER})")

    project = await ProjectRepository().get(project_id)
    if project is None:
        raise ValueError(f"Project not found: {project_id}")

    gate_config = GateConfig.for_mode(GATE_MODE)  # type: ignore[arg-type]
    print(f"[gate] mode={gate_config.gate_mode}")

    halt_reason: str | None = None
    try:
        result = await run_project_pipeline(
            project_id=project_id,
            chapter_range=(START_CHAPTER, END_CHAPTER),
            mode_id=project.mode_id,
            auto_confirm=True,
            on_failure="retry",
            gate_config=gate_config,
        )
        print("\n=== Pipeline completed ===")
        print(f"Completed chapters: {result.chapters_completed}")
        print(f"Failed chapters: {result.chapters_failed}")
        print(f"Total cost: {result.total_cost}")
        print(f"Total duration: {result.total_duration_sec:.1f}s")
    except AutoHaltException as exc:
        halt_reason = f"{exc.reason} (last chapter: {exc.last_chapter})"
        print("\n=== AutoHalt / Gate triggered ===")
        print(halt_reason)

    run_id = await _find_run_id(project_id)
    accepted_versions = await _load_accepted_versions(project_id)
    settlement_counts = await _load_settlement_counts(project_id)
    run_log = _load_run_log_metrics(run_id)
    continuity = await _load_continuity_reports(project_id)

    chapters: list[dict[str, Any]] = []
    for ch in sorted(set(list(accepted_versions.keys()) + list(run_log.keys()))):
        if ch < START_CHAPTER or ch > END_CHAPTER:
            continue
        version = accepted_versions.get(ch)
        log = run_log.get(ch, {})
        sc = settlement_counts.get(ch, {"character_states": 0, "numerical_ledgers": 0})
        record = {
            "chapter": ch,
            "accepted": ch in accepted_versions,
            "word_count": version.word_count if version else log.get("word_count"),
            "scenes_count": len(version.scenes) if version else None,
            "character_states": sc["character_states"],
            "numerical_ledgers": sc["numerical_ledgers"],
            "settlement_success": log.get("settlement_success"),
            "summary_success": log.get("summary_success"),
            "quality_gate_passed": log.get("quality_gate_passed"),
            "skip_settlement": log.get("skip_settlement"),
            "revision_rounds": log.get("revision_rounds"),
            "rule_violations": log.get("rule_violations"),
            "llm_audit_issues": log.get("llm_audit_issues"),
            "llm_audit_critical": log.get("llm_audit_critical"),
            "gate_triggered": log.get("gate_triggered"),
            "gate_reasons": log.get("gate_reasons") or [],
            "budget_used": log.get("budget_used"),
            "context_emergency": log.get("context_emergency"),
            "duration_sec": log.get("duration_sec"),
            "continuity_health_score": log.get("continuity_health_score"),
        }
        chapters.append(record)
        _append_metric(record)

    _write_report(project_id, run_id, halt_reason, chapters, continuity)

    print("\n=== Summary ===")
    print(f"Project: {project_id}")
    print(f"Run ID: {run_id}")
    completed_count = sum(1 for c in chapters if c["accepted"])
    target_count = END_CHAPTER - START_CHAPTER + 1
    print(f"Completed: {completed_count} / {target_count}")
    print(f"Halt: {halt_reason or 'None'}")


if __name__ == "__main__":
    asyncio.run(main())
