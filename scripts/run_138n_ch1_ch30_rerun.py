"""Task 138n: Ch1-Ch30 重跑验证（应用 A+C 改动后）.

用法:
    # 1. 先把主库复制到 .tmp
    Copy-Item "songyan.db" ".tmp/task138n_ch1_ch30_rerun.db"

    # 2. 设置环境变量并运行（默认 Ch1-Ch30）
    $env:DATABASE_URL = "sqlite:///.tmp/task138n_ch1_ch30_rerun.db"
    python scripts/run_138n_ch1_ch30_rerun.py

说明:
    - 从主库克隆源项目（默认 e95a1fa3）创建新验证项目，避免复用已 accepted 章节。
    - 临时切换 Writer default_version 为 1.2.0，退出时恢复。
    - 默认使用 gate_mode="observe"，记录但不主动因 health_low 暂停。
    - 每章输出关键指标；每 10 章输出趋势摘要。
    - 生成 docs/reports/task-138n-ch1-ch30-rerun-report.md。
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import re
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from songyan.db import get_db
from songyan.db.connection import get_db_path
from songyan.db.continuity_repo import ContinuityReportRepository
from songyan.db.repository import (
    ChapterVersionRepository,
    ProjectRepository,
)
from songyan.exceptions import AutoHaltException
from songyan.models import GateConfig, ProjectSetting
from songyan.utils.project_clone import clone_characters
from songyan.workflows.phase2_graph import run_project_pipeline

SOURCE_PROJECT_ID = os.getenv("SOURCE_PROJECT_ID", "e95a1fa3")
PROJECT_ID = os.getenv("PROJECT_ID")
TARGET_CHAPTER = int(os.getenv("TARGET_CHAPTER", "30"))
VALIDATION_WRITER_VERSION = os.getenv("VALIDATION_WRITER_VERSION", "1.2.0")
GATE_MODE = os.getenv("GATE_MODE", "observe")
MANIFEST_PATH = Path("prompts/cards/writer/_manifest.yaml")
REPORT_PATH = Path("docs/reports/task-138n-ch1-ch30-rerun-report.md")
METRICS_PATH = Path(".tmp/task138n_per_chapter_metrics.jsonl")


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


async def _validate_source() -> None:
    db_path = get_db_path()
    if db_path.name == "songyan.db":
        raise RuntimeError(
            "Refusing to run rehearsal in main DB. Copy to .tmp first and set DATABASE_URL."
        )

    source = await ProjectRepository().get(SOURCE_PROJECT_ID)
    if source is None:
        raise ValueError(f"Source project not found: {SOURCE_PROJECT_ID}")

    async with get_db() as conn:
        cursor = await conn.execute(
            """SELECT COUNT(*) FROM chapter_heads
               WHERE project_id = ? AND chapter_number = 1 AND status = 'accepted'""",
            (SOURCE_PROJECT_ID,),
        )
        has_accepted = (await cursor.fetchone())[0] == 1
    if not has_accepted:
        raise RuntimeError(
            f"Source project {SOURCE_PROJECT_ID} has no accepted Ch1; cannot clone baseline."
        )

    print(f"[preflight] db={db_path}")
    print(f"[preflight] source_project={SOURCE_PROJECT_ID}, target_chapter={TARGET_CHAPTER}")





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
        project_id, 1, TARGET_CHAPTER
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
                if getattr(s, "category", "background") not in ("critical", "recurring")
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

    lines: list[str] = [
        "# Task 138k: 长窗口 Rehearsal 报告",
        "",
        f"- 生成时间: {datetime.now().isoformat()}",
        f"- DB: `{get_db_path()}`",
        f"- 源项目 ID: `{SOURCE_PROJECT_ID}`",
        f"- 验证项目 ID: `{project_id}`",
        f"- Run ID: `{run_id}`",
        f"- 章节范围: Ch1-Ch{TARGET_CHAPTER}",
        f"- Writer 工艺卡: {VALIDATION_WRITER_VERSION}",
        f"- Gate 模式: {GATE_MODE}",
        f"- Halt 原因: {halt_reason or 'None'}",
        "",
        "## 总体统计",
        "",
        f"- 完成/目标: {len(completed)} / {TARGET_CHAPTER}",
        f"- 失败章节: {[c['chapter'] for c in failed]}",
        f"- settlement 成功: {len(settlement_ok)} / {len(chapters)}",
        f"- QG 通过: {len(qg_ok)} / {len(chapters)}",
        f"- 总耗时: {duration_total:.1f}s ({duration_total / 60:.1f} min)",
        f"- 单章平均耗时: {duration_total / len(chapters):.1f}s" if chapters else "",
        "",
        "## 每章关键指标",
        "",
        "| Ch | Word | Scenes | Settlement | Summary | QG | Revisions | "
        "Rule | LLM | Gate | Budget | Emergency | Dur(s) |",
        "|---:|---:|---:|:---|:---|:---|---:|---:|---:|:---|---:|:---|---:|",
    ]
    for c in chapters:
        lines.append(
            f"| {c['chapter']} | {c.get('word_count', '')} | {c.get('scenes_count', '')} | "
            f"{_fmt_bool(c.get('settlement_success'))} | {_fmt_bool(c.get('summary_success'))} | "
            f"{_fmt_bool(c.get('quality_gate_passed'))} | {c.get('revision_rounds', '')} | "
            f"{c.get('rule_violations', '')} | {c.get('llm_audit_issues', '')} | "
            f"{_fmt_bool(c.get('gate_triggered'))} | {_fmt(c.get('budget_used'))} | "
            f"{_fmt_bool(c.get('context_emergency'))} | {c.get('duration_sec', '')} |"
        )
    lines.extend(["", "## Continuity 趋势", ""])
    lines.append("| Ch | Health | Orphaned | Forgotten | Mismatches | Overdue | P1 | P2 | P3 |")
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
            f"实跑触发 halt：{halt_reason}。需根据根因决定是否另起 Task 138l 修复。"
        )
    elif len(completed) == TARGET_CHAPTER:
        lines.append(
            f"Ch1-Ch{TARGET_CHAPTER} 全部完成，无 AutoHalt。"
            "请结合 continuity 趋势判断 138h-138j 改进是否稳定。"
        )
    else:
        lines.append(
            f"未完成全部章节（完成 {len(completed)}/{TARGET_CHAPTER}），"
            "未触发 AutoHalt，请检查日志。"
        )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[report] {REPORT_PATH}")


def _append_metric(record: dict[str, Any]) -> None:
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with METRICS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


async def main() -> None:
    await _validate_source()

    source = await ProjectRepository().get(SOURCE_PROJECT_ID)
    if source is None:
        raise ValueError(f"Source project not found: {SOURCE_PROJECT_ID}")

    if PROJECT_ID:
        project = await ProjectRepository().get(PROJECT_ID)
        if project is None:
            raise ValueError(f"Continue project not found: {PROJECT_ID}")
        project_id = PROJECT_ID
        print(f"[project] Continuing existing rehearsal project: {project_id}")
    else:
        project_id = uuid.uuid4().hex
        project = ProjectSetting.model_validate(source.model_dump())
        await ProjectRepository().create(project, project_id)
        print(f"[project] Created rehearsal project: {project_id}")
        aliases = await clone_characters(SOURCE_PROJECT_ID, project_id)
        print(f"[clone] Cloned {len(aliases)} character alias(es)")

    gate_config = GateConfig.for_mode(GATE_MODE)  # type: ignore[arg-type]
    print(f"[gate] mode={gate_config.gate_mode}")

    halt_reason: str | None = None
    with _temp_writer_version(VALIDATION_WRITER_VERSION):
        try:
            result = await run_project_pipeline(
                project_id=project_id,
                chapter_range=(1, TARGET_CHAPTER),
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
    print(f"Completed: {sum(1 for c in chapters if c['accepted'])} / {TARGET_CHAPTER}")
    print(f"Halt: {halt_reason or 'None'}")


if __name__ == "__main__":
    asyncio.run(main())
