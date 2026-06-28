"""Task 137: Ch10 起点聚焦验证.

用法:
    $env:DATABASE_URL = "sqlite:///.tmp/task137_ch10_focus.db"
    python scripts/run_137_ch10_focus_validation.py

说明:
    - 运行前应先把 `songyan.db` 复制为一次性 DB 副本，并通过 DATABASE_URL 指向副本。
    - 脚本会在该副本中清理 Task 137 上次验证项目的 Ch11+ 残留。
    - 保留 Ch1-Ch10 accepted 事实，运行范围为 Ch10-Ch12；Ch10 会被 pipeline
      识别为已 accepted 并跳过，作为一致状态锚点。
    - 临时切换 Writer default_version 为 1.2.0，退出时恢复运行前版本。
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from songyan.db import get_db
from songyan.db.connection import get_db_path
from songyan.db.repository import ProjectRepository
from songyan.exceptions import AutoHaltException
from songyan.models import GateConfig
from songyan.workflows.phase2_graph import run_project_pipeline

FOCUS_PROJECT_ID = "56fbb888d78f4b29bb1a0e8aa7e6a675"
RUN_START_CHAPTER = 10
RUN_END_CHAPTER = 12
CLEAN_FROM_CHAPTER = 11
VALIDATION_WRITER_VERSION = "1.2.0"
MANIFEST_PATH = Path("prompts/cards/writer/_manifest.yaml")
REPORT_PATH = Path("docs/reports/task-137-ch10-focus-validation-report.md")


def _read_manifest() -> str:
    return MANIFEST_PATH.read_text(encoding="utf-8")


def _write_manifest(content: str) -> None:
    MANIFEST_PATH.write_text(content, encoding="utf-8")


def _extract_default_version(content: str) -> str:
    match = re.search(r'^(default_version:\s*)["\']?([\d.]+)["\']?', content, flags=re.MULTILINE)
    if match is None:
        msg = f"Failed to read default_version in {MANIFEST_PATH}"
        raise RuntimeError(msg)
    return match.group(2)


def _replace_default_version(content: str, version: str) -> str:
    pattern = r'^(default_version:\s*)["\']?[\d.]+["\']?'
    replacement = rf'\1"{version}"'
    new_content, count = re.subn(pattern, replacement, content, flags=re.MULTILINE)
    if count != 1:
        msg = f"Failed to replace default_version in {MANIFEST_PATH}: matched {count} lines"
        raise RuntimeError(msg)
    return new_content


@contextlib.contextmanager
def _temp_writer_version(target_version: str):
    original = _read_manifest()
    original_version = _extract_default_version(original)
    try:
        _write_manifest(_replace_default_version(original, target_version))
        print(f"[manifest] Writer default_version {original_version} -> {target_version}")
        yield original_version
    finally:
        _write_manifest(original)
        print(f"[manifest] Writer default_version restored to {original_version}")


async def _query_dicts(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    async with get_db() as conn:
        conn.row_factory = lambda cursor, row: {
            col[0]: row[i] for i, col in enumerate(cursor.description)
        }
        cursor = await conn.execute(sql, params)
        return await cursor.fetchall()


async def _preflight() -> None:
    db_path = get_db_path()
    if db_path.name == "songyan.db":
        msg = (
            "Refusing to clean focus project in the main DB. "
            "Copy songyan.db to .tmp and set DATABASE_URL first."
        )
        raise RuntimeError(msg)

    project = await ProjectRepository().get(FOCUS_PROJECT_ID)
    if project is None:
        raise ValueError(f"Focus project not found: {FOCUS_PROJECT_ID}")

    heads = await _query_dicts(
        """SELECT chapter_number, status, accepted_version_id
           FROM chapter_heads
           WHERE project_id = ?
             AND chapter_number BETWEEN 1 AND 10
           ORDER BY chapter_number""",
        (FOCUS_PROJECT_ID,),
    )
    accepted = [h["chapter_number"] for h in heads if h["status"] == "accepted"]
    if accepted != list(range(1, 11)):
        msg = f"Expected Ch1-Ch10 accepted before focus run, got {accepted}"
        raise RuntimeError(msg)

    print(f"[preflight] db={db_path}")
    print(f"[preflight] focus_project={FOCUS_PROJECT_ID}, accepted_anchor=Ch1-Ch10")


async def _clean_tail_residue() -> None:
    """清理副本 DB 中 Ch11+ 残留，保留 Ch1-Ch10 一致锚点."""
    async with get_db() as conn:
        await conn.execute("PRAGMA foreign_keys = OFF")

        cursor = await conn.execute(
            """SELECT version_id
               FROM chapter_versions
               WHERE project_id = ?
                 AND chapter_number >= ?""",
            (FOCUS_PROJECT_ID, CLEAN_FROM_CHAPTER),
        )
        version_ids = [row[0] for row in await cursor.fetchall()]

        if version_ids:
            placeholders = ",".join("?" for _ in version_ids)
            params: tuple[Any, ...] = tuple(version_ids)
            await conn.execute(
                f"DELETE FROM literary_observations WHERE version_id IN ({placeholders})",
                params,
            )
            await conn.execute(
                f"DELETE FROM review_reports WHERE chapter_version_id IN ({placeholders})",
                params,
            )
            await conn.execute(
                f"DELETE FROM character_states WHERE source_version_id IN ({placeholders})",
                params,
            )
            await conn.execute(
                f"DELETE FROM chapter_chunks WHERE version_id IN ({placeholders})",
                params,
            )
            await conn.execute(
                f"DELETE FROM human_marks WHERE version_id IN ({placeholders})",
                params,
            )
            await conn.execute(
                f"DELETE FROM foreshadowings WHERE source_version_id IN ({placeholders})",
                params,
            )
            await conn.execute(
                f"DELETE FROM setting_tracking WHERE source_version_id IN ({placeholders})",
                params,
            )

        chapter_params = (FOCUS_PROJECT_ID, CLEAN_FROM_CHAPTER)
        for table, column in [
            ("chapter_chunks", "chapter_number"),
            ("chapter_goals", "chapter_number"),
            ("chapter_heads", "chapter_number"),
            ("context_snapshots", "chapter_number"),
            ("continuity_reports", "checked_up_to_chapter"),
            ("creative_briefs", "chapter_number"),
            ("human_instructions", "chapter_number"),
            ("numerical_ledgers", "chapter_number"),
            ("permanent_scenes", "chapter_number"),
            ("run_logs", "chapter_number"),
            ("summaries", "chapter_number"),
        ]:
            await conn.execute(
                f"DELETE FROM {table} WHERE project_id = ? AND {column} >= ?",
                chapter_params,
            )

        for table, column in [
            ("foreshadowings", "planted_in_chapter"),
            ("human_marks", "created_at_chapter"),
            ("inventory_tracker", "acquired_in_chapter"),
            ("location_tracker", "entered_in_chapter"),
            ("setting_tracking", "introduced_in_chapter"),
        ]:
            await conn.execute(
                f"DELETE FROM {table} WHERE project_id = ? AND {column} >= ?",
                chapter_params,
            )

        await conn.execute(
            """DELETE FROM chapter_versions
               WHERE project_id = ?
                 AND chapter_number >= ?""",
            chapter_params,
        )
        await conn.execute(
            "DELETE FROM project_runs WHERE project_id = ?",
            (FOCUS_PROJECT_ID,),
        )

        await conn.commit()
        await conn.execute("PRAGMA foreign_keys = ON")

    print(
        f"[cleanup] Removed Ch{CLEAN_FROM_CHAPTER}+ residue "
        f"from focus DB project {FOCUS_PROJECT_ID}"
    )


def _run_log_path(run_id: str) -> Path:
    return Path(f"logs/chapter_runs/{run_id}.jsonl")


async def _latest_run_id() -> str | None:
    rows = await _query_dicts(
        """SELECT run_id
           FROM project_runs
           WHERE project_id = ?
           ORDER BY created_at DESC
           LIMIT 1""",
        (FOCUS_PROJECT_ID,),
    )
    return rows[0]["run_id"] if rows else None


def _load_run_log(run_id: str | None) -> list[dict[str, Any]]:
    if run_id is None:
        return []
    path = _run_log_path(run_id)
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


async def _collect_focus_state() -> dict[str, Any]:
    run_id = await _latest_run_id()
    heads = await _query_dicts(
        """SELECT chapter_number, status, current_version_id, accepted_version_id
           FROM chapter_heads
           WHERE project_id = ?
             AND chapter_number BETWEEN ? AND ?
           ORDER BY chapter_number""",
        (FOCUS_PROJECT_ID, RUN_START_CHAPTER, RUN_END_CHAPTER),
    )
    versions = await _query_dicts(
        """SELECT chapter_number, version_id, version_type, word_count, is_abandoned
           FROM chapter_versions
           WHERE project_id = ?
             AND chapter_number BETWEEN ? AND ?
           ORDER BY chapter_number, version_number""",
        (FOCUS_PROJECT_ID, RUN_START_CHAPTER, RUN_END_CHAPTER),
    )
    continuity = await _query_dicts(
        """SELECT checked_up_to_chapter, overall_health_score, orphaned_settings,
                  state_mismatches
           FROM continuity_reports
           WHERE project_id = ?
             AND checked_up_to_chapter BETWEEN ? AND ?
           ORDER BY checked_up_to_chapter""",
        (FOCUS_PROJECT_ID, RUN_START_CHAPTER, RUN_END_CHAPTER),
    )
    return {
        "run_id": run_id,
        "heads": heads,
        "versions": versions,
        "continuity": continuity,
        "run_log": _load_run_log(run_id),
    }


def _write_report(state: dict[str, Any], halt_reason: str | None) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Task 137: Ch10 起点聚焦验证报告",
        "",
        f"- 生成时间: {datetime.now().isoformat()}",
        f"- DB: `{get_db_path()}`",
        f"- 项目 ID: `{FOCUS_PROJECT_ID}`",
        f"- Run ID: `{state['run_id']}`",
        f"- 运行窗口: Ch{RUN_START_CHAPTER}-Ch{RUN_END_CHAPTER}",
        "- 前置状态: 保留 Ch1-Ch10 accepted，清理 Ch11+ 残留后运行",
        f"- Writer 工艺卡: {VALIDATION_WRITER_VERSION}",
        f"- Halt: {halt_reason or 'None'}",
        "",
        "## Heads",
        "",
        "| Ch | Status | Current | Accepted |",
        "|---:|---|---|---|",
    ]
    for head in state["heads"]:
        lines.append(
            f"| {head['chapter_number']} | {head['status']} | "
            f"{head['current_version_id']} | {head['accepted_version_id']} |"
        )
    lines.extend(["", "## Run Log", ""])
    for entry in state["run_log"]:
        if RUN_START_CHAPTER <= entry.get("chapter_number", 0) <= RUN_END_CHAPTER:
            lines.append(
                "- Ch{chapter_number}: success={success}, settlement={settlement_success}, "
                "summary={summary_success}, qg={quality_gate_passed}, "
                "skip_settlement={skip_settlement}, error={error}".format(**entry)
            )
    lines.extend(["", "## Continuity", ""])
    for report in state["continuity"]:
        orphaned = len(json.loads(report["orphaned_settings"] or "[]"))
        mismatches = len(json.loads(report["state_mismatches"] or "[]"))
        lines.append(
            f"- Ch{report['checked_up_to_chapter']}: "
            f"health={report['overall_health_score']}, "
            f"orphaned={orphaned}, mismatches={mismatches}"
        )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[report] {REPORT_PATH}")


async def main() -> None:
    await _preflight()
    await _clean_tail_residue()

    project = await ProjectRepository().get(FOCUS_PROJECT_ID)
    if project is None:
        raise ValueError(f"Focus project not found after cleanup: {FOCUS_PROJECT_ID}")

    gate_config = GateConfig.for_mode("enforce")
    gate_config.health_low_p1_halt = False
    gate_config.health_low_streak_halt = False
    gate_config.health_low_score_halt_enabled = False

    halt_reason: str | None = None
    with _temp_writer_version(VALIDATION_WRITER_VERSION):
        try:
            result = await run_project_pipeline(
                project_id=FOCUS_PROJECT_ID,
                chapter_range=(RUN_START_CHAPTER, RUN_END_CHAPTER),
                mode_id=project.mode_id,
                auto_confirm=True,
                on_failure="retry",
                gate_config=gate_config,
            )
            print("\n=== Focus pipeline completed ===")
            print(f"Completed chapters: {result.chapters_completed}")
            print(f"Failed chapters: {result.chapters_failed}")
            print(f"Total cost: {result.total_cost}")
            print(f"Total duration: {result.total_duration_sec:.1f}s")
        except AutoHaltException as exc:
            halt_reason = f"{exc.reason} (last chapter: {exc.last_chapter})"
            print("\n=== AutoHalt / Gate triggered ===")
            print(halt_reason)

    state = await _collect_focus_state()
    _write_report(state, halt_reason)

    print("\n=== Focus summary ===")
    print(f"Run ID: {state['run_id']}")
    for head in state["heads"]:
        print(
            f"Ch{head['chapter_number']}: "
            f"status={head['status']}, accepted={head['accepted_version_id']}"
        )


if __name__ == "__main__":
    asyncio.run(main())
