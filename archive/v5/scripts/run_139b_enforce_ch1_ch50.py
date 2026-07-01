"""Task 139b: Enforce 模式 Ch1-Ch50 实跑验证.

用法:
    # 1. 初始化干净 DB（首次）
    $env:DATABASE_URL = "sqlite:///.tmp/task139b_enforce_ch1_ch50.db"
    python scripts/run_139b_enforce_ch1_ch50.py --init

    # 2. 运行 Ch1-Ch50 enforce 验证
    $env:DATABASE_URL = "sqlite:///.tmp/task139b_enforce_ch1_ch50.db"
    python scripts/run_139b_enforce_ch1_ch50.py

说明:
    - 在干净 DB 中新建项目，不克隆旧项目数据。
    - 使用 manifest 默认 Writer 版本，不做临时切换。
    - gate_mode="enforce"，触发 gate 即暂停 run。
    - 生成 docs/reports/task-139b-enforce-ch1-ch50-validation-report.md。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from songyan.db import get_db
from songyan.db.connection import get_db_path
from songyan.db.continuity_repo import ContinuityReportRepository
from songyan.db.migrations import init_schema
from songyan.db.repository import (
    ChapterVersionRepository,
    ProjectRepository,
)
from songyan.exceptions import AutoHaltException
from songyan.models import GateConfig, ProjectSetting
from songyan.workflows.phase2_graph import run_project_pipeline

DB_PATH = Path(".tmp/task139b_enforce_ch1_ch50.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")
GATE_MODE = os.getenv("GATE_MODE", "enforce")
REPORT_PATH = Path(
    "docs/reports/task-139b-enforce-ch1-ch50-validation-report.md"
)
METRICS_PATH = Path(".tmp/task139b_ch1_ch50_metrics.jsonl")

START_CHAPTER = int(os.getenv("START_CHAPTER", "1"))
END_CHAPTER = int(os.getenv("END_CHAPTER", "50"))


def _project_setting() -> ProjectSetting:
    """构造与历史验证一致的 scifi / webnovel_intense 项目设置."""
    return ProjectSetting(
        title="轨道蜃景",
        genre_id="scifi",
        mode_id="webnovel_intense",
        protagonist_name="林渊",
        protagonist_background="前星际考古学家，因一次事故失去搭档，独自追查真相",
        core_hook="人类在太阳系边缘发现一座无法解析的黑色结构，"
                  "林渊是唯一能与之产生共鸣的个体",
        target_reader_expectation="硬科幻+太空悬疑，要求科学细节与剧情张力兼顾",
        target_word_count=450000,
        tone="热血",
        estimated_chapters=150,
        words_per_chapter=3000,
        story_structure="serial",
        sub_genre_id="space_opera",
        arc_boundaries=[25, 50, 75, 100, 125],
        arc_boundaries_auto=True,
    )


async def _query_dicts(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    async with get_db() as conn:
        conn.row_factory = lambda cursor, row: {
            col[0]: row[i] for i, col in enumerate(cursor.description)
        }
        cursor = await conn.execute(sql, params)
        return await cursor.fetchall()


async def _init_db() -> None:
    """初始化干净 DB schema."""
    db_path = get_db_path()
    if db_path.exists():
        db_path.unlink()
        print(f"[init] removed existing {db_path}")
    await init_schema()
    print(f"[init] schema initialized at {db_path}")


async def _create_project() -> str:
    """在干净 DB 中创建新项目."""
    project_id = uuid.uuid4().hex
    project = _project_setting()
    await ProjectRepository().create(project, project_id)
    print(f"[project] created {project_id}")
    return project_id


def _run_log_path(run_id: str) -> Path:
    return Path(f"logs/chapter_runs/{run_id}.jsonl")


async def _find_run_id(project_id: str) -> str | None:
    rows = await _query_dicts(
        """SELECT run_id FROM project_runs
           WHERE project_id = ?
           ORDER BY created_at DESC
           LIMIT 1""",
        (project_id,),
    )
    return rows[0]["run_id"] if rows else None


def _load_run_log_metrics(run_id: str | None) -> dict[int, dict[str, Any]]:
    metrics: dict[int, dict[str, Any]] = {}
    if run_id is None:
        return metrics
    path = _run_log_path(run_id)
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

    lines: list[str] = [
        "# Task 139b：Enforce 模式 Ch1-Ch50 实跑验证报告",
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
            f"实跑触发 halt：{halt_reason}。需根据根因决定是否回退 Task 139a 或新建修复任务。"
        )
    elif len(completed) == target_count:
        lines.append(
            f"Ch{START_CHAPTER}-Ch{END_CHAPTER} 全部完成，无 AutoHalt。"
            " enforce 模式在 Ch1-Ch50 验证通过，可进入 Task 139c 长窗口验证。"
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
        "--init", action="store_true", help="初始化干净 DB 并创建项目"
    )
    args = parser.parse_args()

    if args.init:
        await _init_db()
        project_id = await _create_project()
        print(f"[init] project_id={project_id}")
        return

    project_id = os.getenv("PROJECT_ID")
    if not project_id:
        parser.error("请先用 --init 创建项目并记录 PROJECT_ID")

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
