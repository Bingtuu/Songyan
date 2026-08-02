"""Run diagnostic bundle service for V11 open-source readiness."""

from __future__ import annotations

import json
import re
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from songyan.db.connection import get_db
from songyan.db.llm_call_usage_repo import LlmCallUsageRepository
from songyan.db.project_run_repo import ProjectRunRepository
from songyan.db.repository import ProjectRepository
from songyan.evals.streaming_report import read_run_logs
from songyan.exceptions import SongyanError
from songyan.models.project_run import ProjectRunState
from songyan.models.run_log import ChapterRunLog

RUN_BUNDLE_FORMAT = "songyan_run_bundle"
RUN_BUNDLE_FORMAT_VERSION = 1
BUNDLE_JSON_MEMBER = "bundle.json"
BUNDLE_MARKDOWN_MEMBER = "bundle.md"
LOG_INDEX_MEMBER = "logs/index.json"

_SECRET_HINTS = (
    "api_key",
    "apikey",
    "authorization",
    "bearer",
    "llm_api_key",
    "password",
    "secret",
    "token",
)


class RunBundleServiceError(SongyanError):
    """Run bundle cannot be generated safely."""


@dataclass(frozen=True)
class RunBundleResult:
    """Result of a completed run bundle."""

    bundle_path: Path
    bundle: dict[str, Any]
    markdown: str


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _timestamp_for_filename(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%SZ")


def _json_dump(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)


def _redact_string(value: str) -> str:
    lower = value.lower()
    if any(hint in lower for hint in _SECRET_HINTS):
        return "<redacted>"
    value = re.sub(r"[A-Za-z]:[\\/][^\s\"']+", "<redacted-path>", value)
    value = re.sub(
        r"(?<![A-Za-z0-9_])/(?:Users|home|tmp|var|private|mnt|workspace)[^\s\"']*",
        "<redacted-path>",
        value,
    )
    return value


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if any(hint in key_text.lower() for hint in _SECRET_HINTS):
                sanitized[key_text] = "<redacted>"
            else:
                sanitized[key_text] = _sanitize(item)
        return sanitized
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, Path):
        return _relative_or_redacted_path(value)
    if isinstance(value, str):
        return _redact_string(value)
    return value


def _relative_or_redacted_path(path: Path) -> str:
    if path.is_absolute():
        return f"<redacted-path>/{path.name}"
    return path.as_posix()


def _resolve_bundle_path(output: Path, run_id: str, created_at: datetime) -> Path:
    if output.suffix.lower() == ".zip":
        bundle_path = output
    else:
        bundle_path = (
            output
            / f"songyan-run-bundle-{run_id}-{_timestamp_for_filename(created_at)}.zip"
        )
    if bundle_path.exists():
        raise RunBundleServiceError(f"bundle file already exists: {bundle_path}")
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    return bundle_path


def _artifact(path: Path, *, kind: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "path": _relative_or_redacted_path(path),
        "exists": path.is_file(),
        "size_bytes": path.stat().st_size if path.is_file() else 0,
        "content_included": False,
    }


def _logs_index(run_id: str) -> dict[str, Any]:
    chapter_log = Path("logs/chapter_runs") / f"{run_id}.jsonl"
    report = Path("logs/reports") / f"report-{run_id}.md"
    app_logs = Path("logs/app")
    items = [
        _artifact(chapter_log, kind="chapter_run_jsonl"),
        _artifact(report, kind="report_markdown"),
        {
            "kind": "app_log_directory",
            "path": _relative_or_redacted_path(app_logs),
            "exists": app_logs.is_dir(),
            "size_bytes": 0,
            "content_included": False,
        },
    ]
    return {
        "content_included": False,
        "items": items,
        "existing_count": sum(1 for item in items if item["exists"]),
    }


def _chapter_status(log: ChapterRunLog) -> dict[str, Any]:
    failure_category = None if log.success else _classify_failure(log)
    return _sanitize(
        {
            "chapter_number": log.chapter_number,
            "success": log.success,
            "failure_category": failure_category,
            "error_stage": log.error_stage,
            "error": log.error,
            "word_count": log.word_count,
            "budget_used": log.budget_used,
            "context_emergency": log.context_emergency,
            "quality_gate_passed": log.quality_gate_passed,
            "gate_triggered": log.gate_triggered,
            "gate_reasons": log.gate_reasons,
            "settlement_success": log.settlement_success,
            "summary_success": log.summary_success,
            "duration_sec": log.duration_sec,
        }
    )


def _classify_failure(log: ChapterRunLog) -> str:
    text = f"{log.error_stage or ''} {log.error or ''}".lower()
    if "key" in text or "llm" in text or "endpoint" in text:
        return "config_error"
    if "budget" in text or "cost" in text:
        return "run_failed"
    if "settlement" in text:
        return "run_failed"
    if "quality" in text or "gate" in text:
        return "run_failed"
    return "run_failed"


def _summarize_chapters(logs: list[ChapterRunLog]) -> dict[str, Any]:
    completed = [log.chapter_number for log in logs if log.success]
    failed = [log.chapter_number for log in logs if not log.success]
    budgets = [log.budget_used for log in logs if log.budget_used is not None]
    return {
        "count": len(logs),
        "completed": completed,
        "failed": failed,
        "success_count": len(completed),
        "failed_count": len(failed),
        "max_budget_used": max(budgets) if budgets else None,
        "context_emergency_count": sum(1 for log in logs if log.context_emergency),
    }


def _quality_from_logs(logs: list[ChapterRunLog]) -> dict[str, Any]:
    qg_pass = sum(1 for log in logs if log.quality_gate_passed is True)
    qg_fail = sum(1 for log in logs if log.quality_gate_passed is False)
    qg_unknown = len(logs) - qg_pass - qg_fail
    gate_reason_counts: dict[str, int] = {}
    gate_mode_counts: dict[str, int] = {}
    health_values: list[float] = []
    for log in logs:
        gate_mode_counts[log.gate_mode] = gate_mode_counts.get(log.gate_mode, 0) + 1
        for reason in log.gate_reasons:
            gate_reason_counts[reason] = gate_reason_counts.get(reason, 0) + 1
        if log.continuity_health_score is not None:
            health_values.append(float(log.continuity_health_score))
    return {
        "quality_gate": {
            "pass": qg_pass,
            "fail": qg_fail,
            "unknown": qg_unknown,
        },
        "candidate_gate": {
            "triggered_count": sum(1 for log in logs if log.gate_triggered),
            "mode_counts": gate_mode_counts,
            "reason_counts": gate_reason_counts,
        },
        "context": {
            "context_emergency_count": sum(1 for log in logs if log.context_emergency),
        },
        "continuity_from_run_log": {
            "health_min": min(health_values) if health_values else None,
            "health_latest": health_values[-1] if health_values else None,
        },
    }


def _project_summary(project: Any | None, project_id: str) -> dict[str, Any]:
    if project is None:
        return {
            "project_id": project_id,
            "found_in_db": False,
        }
    return {
        "project_id": project_id,
        "found_in_db": True,
        "title": project.title,
        "genre_id": project.genre_id,
        "mode_id": project.mode_id,
        "protagonist_name": project.protagonist_name,
        "estimated_chapters": project.estimated_chapters,
        "words_per_chapter": project.words_per_chapter,
        "story_structure": project.story_structure,
    }


def _run_summary(
    *,
    run_id: str,
    project_id: str,
    run_state: ProjectRunState | None,
    logs: list[ChapterRunLog],
) -> dict[str, Any]:
    if run_state is None:
        first = min(log.chapter_number for log in logs)
        last = max(log.chapter_number for log in logs)
        return {
            "run_id": run_id,
            "project_id": project_id,
            "found_in_db": False,
            "chapter_range_start": first,
            "chapter_range_end": last,
            "status": "from_logs_only",
        }
    return {
        "run_id": run_state.run_id,
        "project_id": run_state.project_id,
        "found_in_db": True,
        "chapter_range_start": run_state.chapter_range_start,
        "chapter_range_end": run_state.chapter_range_end,
        "current_chapter": run_state.current_chapter,
        "completed_chapters": run_state.completed_chapters,
        "failed_chapters": run_state.failed_chapters,
        "status": run_state.status,
        "pause_reason": run_state.pause_reason,
        "total_cost": run_state.total_cost,
        "created_at": run_state.created_at.isoformat(),
        "updated_at": run_state.updated_at.isoformat(),
    }


async def _cost_summary(run_id: str) -> tuple[dict[str, Any], list[str]]:
    repo = LlmCallUsageRepository()
    try:
        aggregate = await repo.aggregate_for_run(run_id)
        source_stats = await repo.source_stats_for_run(run_id)
        total_cost = await repo.sum_cost_for_run(run_id)
    except Exception as exc:  # noqa: BLE001 - bundle should degrade to warning
        return (
            {
                "status": "unavailable",
                "total_cost_cny": None,
                "aggregate": {"per_chapter": [], "per_agent": []},
                "source_stats": {},
            },
            [f"cost telemetry unavailable: {_redact_string(str(exc))}"],
        )
    return (
        {
            "status": "ok",
            "total_cost_cny": total_cost,
            "aggregate": aggregate,
            "source_stats": source_stats,
        },
        [],
    )


async def _continuity_summary(project_id: str, end_chapter: int) -> dict[str, Any]:
    try:
        async with get_db() as conn:
            cursor = await conn.execute(
                """SELECT checked_up_to_chapter, overdue_foreshadowings,
                          overall_health_score
                   FROM continuity_reports
                   WHERE project_id = ? AND checked_up_to_chapter <= ?
                   ORDER BY checked_up_to_chapter DESC, rowid DESC
                   LIMIT 1""",
                (project_id, end_chapter),
            )
            row = await cursor.fetchone()
    except Exception as exc:  # noqa: BLE001 - optional signal
        return {"status": "unavailable", "error": _redact_string(str(exc))}

    if row is None:
        return {
            "status": "missing",
            "health_latest": None,
            "health_report_chapter": None,
            "overdue_count": None,
        }
    overdue_raw = row[1] or "[]"
    try:
        overdue = json.loads(overdue_raw)
    except json.JSONDecodeError:
        overdue = []
    return {
        "status": "ok",
        "health_report_chapter": int(row[0]),
        "health_latest": float(row[2]) if row[2] is not None else None,
        "overdue_count": len(overdue) if isinstance(overdue, list) else None,
    }


async def _run_quality_debt_summary(run_id: str) -> dict[str, Any]:
    try:
        async with get_db() as conn:
            conn.row_factory = None
            cursor = await conn.execute(
                """SELECT total_chapters, degraded_count, convergence_failed_count,
                          qg_false_count, degraded_ratio, convergence_ratio,
                          t4_breached
                   FROM run_quality_debt
                   WHERE run_id = ?""",
                (run_id,),
            )
            row = await cursor.fetchone()
    except Exception as exc:  # noqa: BLE001 - optional signal
        return {"status": "unavailable", "error": _redact_string(str(exc))}
    if row is None:
        return {"status": "missing"}
    return {
        "status": "ok",
        "total_chapters": int(row[0]),
        "degraded_count": int(row[1]),
        "convergence_failed_count": int(row[2]),
        "qg_false_count": int(row[3]),
        "degraded_ratio": float(row[4]),
        "convergence_ratio": float(row[5]),
        "t4_breached": bool(row[6]),
    }


def _static_external_signal_summary() -> dict[str, Any]:
    return {
        "five_gate": {
            "status": "external_not_embedded",
            "note": "five-gate replay is a separate harness; bundle records availability only.",
        },
        "t9": {
            "status": "external_not_embedded",
            "note": "T9 hard cleanliness remains a separate frozen harness.",
        },
        "ced": {
            "status": "external_not_embedded",
            "note": "CED remains consistency-only merged/source evidence metric.",
        },
    }


def _render_markdown(bundle: dict[str, Any]) -> str:
    run = bundle["run"]
    project = bundle["project"]
    chapters = bundle["chapters"]
    cost = bundle["cost"]
    quality = bundle["quality_signals"]
    artifacts = bundle["artifacts"]["items"]

    lines = [
        f"# Songyan Run Bundle: {run['run_id']}",
        "",
        "## Run",
        "",
        f"- project_id: `{run['project_id']}`",
        f"- status: `{run.get('status')}`",
        f"- chapter_range: Ch{run['chapter_range_start']}-Ch{run['chapter_range_end']}",
        f"- run_db_record: {run['found_in_db']}",
        "",
        "## Project",
        "",
        f"- title: {project.get('title') or '(unknown)'}",
        f"- genre_id: `{project.get('genre_id', 'unknown')}`",
        f"- mode_id: `{project.get('mode_id', 'unknown')}`",
        "",
        "## Chapters",
        "",
        f"- total: {chapters['summary']['count']}",
        f"- success: {chapters['summary']['success_count']}",
        f"- failed: {chapters['summary']['failed_count']}",
        f"- failed_chapters: {chapters['summary']['failed'] or '-'}",
        "",
        "## Cost",
        "",
        f"- status: {cost['status']}",
        f"- total_cost_cny: {cost.get('total_cost_cny')}",
        "",
        "## Quality Signals",
        "",
        f"- quality_gate: {quality['from_run_log']['quality_gate']}",
        f"- candidate_gate: {quality['from_run_log']['candidate_gate']}",
        f"- continuity: {quality['continuity']}",
        f"- run_quality_debt: {quality['run_quality_debt']}",
        f"- external: {quality['external']}",
        "",
        "## Artifacts",
        "",
    ]
    for item in artifacts:
        lines.append(
            f"- {item['kind']}: {item['path']} "
            f"(exists={item['exists']}, content_included={item['content_included']})"
        )
    lines.extend(
        [
            "",
            "## Redaction",
            "",
            "- `.env` content is not included.",
            "- API keys, tokens, authorization headers and absolute paths are redacted.",
            "- Log content and manuscript content are not included by default.",
        ]
    )
    warnings = bundle.get("warnings", [])
    if warnings:
        lines.extend(["", "## Warnings", ""])
        for warning in warnings:
            lines.append(f"- {warning}")
    lines.append("")
    return "\n".join(lines)


async def bundle_run(
    run_id: str,
    *,
    output: Path,
    project_id: str | None = None,
) -> RunBundleResult:
    """Build a shareable diagnostic bundle for one run."""
    logs = read_run_logs(run_id)
    if not logs:
        raise RunBundleServiceError(
            f"run log not found: logs/chapter_runs/{run_id}.jsonl"
        )

    log_project_ids = {log.project_id for log in logs}
    inferred_project_id = sorted(log_project_ids)[0]
    warnings: list[str] = []
    if len(log_project_ids) > 1:
        warnings.append("run log contains multiple project_id values")
    if project_id is not None and project_id != inferred_project_id:
        raise RunBundleServiceError(
            f"project_id mismatch: expected {project_id}, run log has {inferred_project_id}"
        )
    effective_project_id = project_id or inferred_project_id

    run_state: ProjectRunState | None
    try:
        run_state = await ProjectRunRepository().get(run_id)
    except Exception as exc:  # noqa: BLE001 - run log remains useful
        run_state = None
        warnings.append(f"project_runs lookup failed: {_redact_string(str(exc))}")

    if run_state is not None and run_state.project_id != effective_project_id:
        raise RunBundleServiceError(
            "project_id mismatch: project_runs has "
            f"{run_state.project_id}, run log has {effective_project_id}"
        )

    try:
        project = await ProjectRepository().get(effective_project_id)
    except Exception as exc:  # noqa: BLE001 - bundle can degrade
        project = None
        warnings.append(f"project lookup failed: {_redact_string(str(exc))}")

    created_at = _utc_now()
    bundle_path = _resolve_bundle_path(output, run_id, created_at)
    chapter_summary = _summarize_chapters(logs)
    cost, cost_warnings = await _cost_summary(run_id)
    warnings.extend(cost_warnings)
    end_chapter = max(log.chapter_number for log in logs)
    logs_index = _logs_index(run_id)
    artifacts = {
        "items": [
            item
            for item in logs_index["items"]
            if item["kind"] in {"chapter_run_jsonl", "report_markdown"}
        ]
    }

    bundle = _sanitize(
        {
            "format": RUN_BUNDLE_FORMAT,
            "format_version": RUN_BUNDLE_FORMAT_VERSION,
            "created_at": created_at.isoformat(),
            "run": _run_summary(
                run_id=run_id,
                project_id=effective_project_id,
                run_state=run_state,
                logs=logs,
            ),
            "project": _project_summary(project, effective_project_id),
            "chapters": {
                "summary": chapter_summary,
                "items": [_chapter_status(log) for log in logs],
            },
            "cost": cost,
            "quality_signals": {
                "from_run_log": _quality_from_logs(logs),
                "continuity": await _continuity_summary(
                    effective_project_id, end_chapter
                ),
                "run_quality_debt": await _run_quality_debt_summary(run_id),
                "external": _static_external_signal_summary(),
            },
            "artifacts": artifacts,
            "logs": logs_index,
            "redaction": {
                "env_file_included": False,
                "api_key_included": False,
                "sensitive_env_included": False,
                "absolute_paths_redacted": True,
                "log_content_included": False,
                "manuscript_content_included": False,
            },
            "warnings": warnings,
        }
    )
    markdown = _render_markdown(bundle)

    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(BUNDLE_JSON_MEMBER, _json_dump(bundle))
        archive.writestr(BUNDLE_MARKDOWN_MEMBER, markdown)
        archive.writestr(LOG_INDEX_MEMBER, _json_dump(bundle["logs"]))

    return RunBundleResult(bundle_path=bundle_path, bundle=bundle, markdown=markdown)
