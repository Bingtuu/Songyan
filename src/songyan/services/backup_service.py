"""Project backup / restore service for V11 open-source readiness."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path
from sqlite3 import Row
from typing import Any, cast

from songyan.config import Settings, settings
from songyan.creative_modes.registry import list_creative_mode_profiles
from songyan.db.migrations import _EXPECTED_TABLES
from songyan.exceptions import SongyanError
from songyan.genres.loader import list_genre_profiles

BACKUP_FORMAT = "songyan_project_backup"
BACKUP_FORMAT_VERSION = 1
SNAPSHOT_MEMBER = "db/songyan.db"
MANIFEST_MEMBER = "manifest.json"
CONFIG_SUMMARY_MEMBER = "config/config.summary.json"
RUNS_MEMBER = "runs/project_runs.json"
LOG_INDEX_MEMBER = "logs/index.json"


class BackupServiceError(SongyanError):
    """Backup or restore cannot be completed safely."""


@dataclass(frozen=True)
class BackupResult:
    """Result of a completed project backup."""

    backup_path: Path
    manifest: dict[str, Any]


@dataclass(frozen=True)
class RestoreResult:
    """Result of a completed restore operation."""

    database_path: Path
    manifest: dict[str, Any]
    schema: dict[str, Any]


def sqlite_path_from_url(database_url: str) -> Path:
    """Return the SQLite file path from a ``sqlite:///`` URL."""
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise BackupServiceError("当前 backup/restore 仅支持 sqlite:///... DATABASE_URL")
    path_text = database_url[len(prefix) :]
    if not path_text:
        raise BackupServiceError("sqlite DATABASE_URL 缺少文件路径")
    return Path(path_text)


def _json_dump(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _timestamp_for_filename(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%SZ")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _open_sqlite(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = Row
    return conn


def _load_project(db_path: Path, project_id: str) -> dict[str, Any]:
    conn = _open_sqlite(db_path)
    try:
        cursor = conn.execute(
            """
            SELECT project_id, title, genre_id, mode_id, protagonist_name,
                   estimated_chapters, words_per_chapter, story_structure,
                   created_at
            FROM projects
            WHERE project_id = ?
            """,
            (project_id,),
        )
        row = cursor.fetchone()
    finally:
        conn.close()
    if row is None:
        raise BackupServiceError(
            f"project not found: {project_id}；请先用 songyan list-projects 确认项目 ID。"
        )
    return dict(row)


def _load_project_runs(db_path: Path, project_id: str) -> list[dict[str, Any]]:
    conn = _open_sqlite(db_path)
    try:
        cursor = conn.execute(
            """
            SELECT run_id, project_id, chapter_range_start, chapter_range_end,
                   current_chapter, completed_chapters, failed_chapters,
                   total_cost, status, pause_reason, created_at, updated_at
            FROM project_runs
            WHERE project_id = ?
            ORDER BY created_at DESC
            """,
            (project_id,),
        )
        rows = cursor.fetchall()
    finally:
        conn.close()

    runs: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["completed_chapters"] = _load_json_list(item.get("completed_chapters"))
        item["failed_chapters"] = _load_json_list(item.get("failed_chapters"))
        runs.append(item)
    return runs


def _load_json_list(value: object) -> list[Any]:
    if not isinstance(value, str) or not value:
        return []
    try:
        loaded = json.loads(value)
    except json.JSONDecodeError:
        return []
    return loaded if isinstance(loaded, list) else []


def _schema_ledger(db_path: Path) -> dict[str, Any]:
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        existing = {str(row[0]) for row in rows}
        missing = [table for table in _EXPECTED_TABLES if table not in existing]
        version = len(_EXPECTED_TABLES) - len(missing)
        quick_check = conn.execute("PRAGMA quick_check").fetchone()
    finally:
        conn.close()
    quick_check_value = str(quick_check[0]) if quick_check else "unknown"
    return {
        "status": "pass" if not missing and quick_check_value == "ok" else "fail",
        "schema_version": version,
        "missing_tables": missing,
        "quick_check": quick_check_value,
    }


def _resource_summary() -> dict[str, Any]:
    try:
        genre_ids = list_genre_profiles()
        mode_ids = list_creative_mode_profiles()
        template_root = files("songyan.project_templates") / "data"
        templates = sorted(
            path.name
            for path in template_root.iterdir()
            if path.is_dir() and (path / "template.yaml").is_file()
        )
    except Exception as exc:  # noqa: BLE001 - asset manifest should capture diagnostics
        return {"status": "fail", "error": str(exc)}
    return {
        "status": "pass",
        "genres": len(genre_ids),
        "modes": len(mode_ids),
        "templates": len(templates),
    }


def _runtime_config_summary(config: Settings) -> dict[str, Any]:
    return {
        "database_url_kind": "sqlite",
        "llm_api_key_configured": bool(config.llm_api_key),
        "llm_base_url": config.llm_base_url,
        "llm_model": config.llm_model,
        "checkpointer_mode": config.checkpointer_mode,
        "run_cost_budget": config.run_cost_budget,
        "sensitive_values_included": False,
        "env_file_included": False,
    }


def _logs_index(runs: list[dict[str, Any]]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for run in runs:
        run_id = str(run.get("run_id", ""))
        if not run_id:
            continue
        for kind, path in (
            ("chapter_run_jsonl", Path("logs/chapter_runs") / f"{run_id}.jsonl"),
            ("report_markdown", Path("logs/reports") / f"report-{run_id}.md"),
        ):
            items.append(
                {
                    "run_id": run_id,
                    "kind": kind,
                    "path": path.as_posix(),
                    "exists": path.is_file(),
                    "size_bytes": path.stat().st_size if path.is_file() else 0,
                }
            )
    return {
        "content_included": False,
        "items": items,
        "existing_count": sum(1 for item in items if item["exists"]),
    }


def _resolve_backup_path(output: Path, project_id: str, created_at: datetime) -> Path:
    if output.suffix.lower() == ".zip":
        backup_path = output
    else:
        backup_path = (
            output
            / f"songyan-backup-{project_id}-{_timestamp_for_filename(created_at)}.zip"
        )
    if backup_path.exists():
        raise BackupServiceError(f"backup file already exists: {backup_path}")
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    return backup_path


def _snapshot_sqlite_db(source_db: Path, snapshot_db: Path) -> None:
    if not source_db.is_file():
        raise BackupServiceError(
            f"database does not exist: {source_db}；请先运行 songyan doctor --init-db。"
        )
    snapshot_db.parent.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect(f"file:{source_db.as_posix()}?mode=ro", uri=True)
    try:
        destination = sqlite3.connect(str(snapshot_db))
        try:
            source.backup(destination)
        finally:
            destination.close()
    finally:
        source.close()


def _build_manifest(
    *,
    created_at: datetime,
    project: dict[str, Any],
    database: dict[str, Any],
    schema: dict[str, Any],
    config_summary: dict[str, Any],
    runs: list[dict[str, Any]],
    log_index: dict[str, Any],
    resources: dict[str, Any],
) -> dict[str, Any]:
    return {
        "format": BACKUP_FORMAT,
        "format_version": BACKUP_FORMAT_VERSION,
        "created_at": created_at.isoformat(),
        "project": project,
        "database": database,
        "schema": schema,
        "config_summary": config_summary,
        "runs": {
            "count": len(runs),
            "completed_runs": sum(1 for run in runs if run.get("status") == "completed"),
            "failed_runs": sum(1 for run in runs if run.get("status") == "failed"),
        },
        "logs": {
            "indexed_count": len(log_index["items"]),
            "existing_count": log_index["existing_count"],
            "content_included": False,
        },
        "resources": resources,
        "sensitive_data": {
            "env_file_included": False,
            "api_key_included": False,
            "log_content_included": False,
        },
    }


async def backup_project(
    project_id: str,
    *,
    output: Path,
    config: Settings = settings,
) -> BackupResult:
    """Create a project asset backup zip."""
    source_db = sqlite_path_from_url(config.database_url)
    created_at = _utc_now()
    backup_path = _resolve_backup_path(output, project_id, created_at)

    with tempfile.TemporaryDirectory(prefix="songyan-backup-") as temp_dir_raw:
        temp_dir = Path(temp_dir_raw)
        snapshot_db = temp_dir / "songyan.db"
        _snapshot_sqlite_db(source_db, snapshot_db)

        project = _load_project(snapshot_db, project_id)
        runs = _load_project_runs(snapshot_db, project_id)
        schema = _schema_ledger(snapshot_db)
        log_index = _logs_index(runs)
        config_summary = {
            "project": project,
            "runtime": _runtime_config_summary(config),
        }
        database = {
            "snapshot_member": SNAPSHOT_MEMBER,
            "source_kind": "sqlite",
            "size_bytes": snapshot_db.stat().st_size,
            "sha256": _sha256_file(snapshot_db),
        }
        manifest = _build_manifest(
            created_at=created_at,
            project=project,
            database=database,
            schema=schema,
            config_summary=config_summary,
            runs=runs,
            log_index=log_index,
            resources=_resource_summary(),
        )

        with zipfile.ZipFile(backup_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(snapshot_db, SNAPSHOT_MEMBER)
            archive.writestr(MANIFEST_MEMBER, _json_dump(manifest))
            archive.writestr(CONFIG_SUMMARY_MEMBER, _json_dump(config_summary))
            archive.writestr(RUNS_MEMBER, _json_dump(runs))
            archive.writestr(LOG_INDEX_MEMBER, _json_dump(log_index))

    return BackupResult(backup_path=backup_path, manifest=manifest)


def _read_manifest(archive: zipfile.ZipFile) -> dict[str, Any]:
    try:
        raw = archive.read(MANIFEST_MEMBER)
    except KeyError as exc:
        raise BackupServiceError("backup package missing manifest.json") from exc
    try:
        manifest = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise BackupServiceError("backup manifest is not valid JSON") from exc
    if manifest.get("format") != BACKUP_FORMAT:
        raise BackupServiceError("unsupported backup format")
    if manifest.get("format_version") != BACKUP_FORMAT_VERSION:
        raise BackupServiceError(
            f"unsupported backup format_version: {manifest.get('format_version')}"
        )
    return cast(dict[str, Any], manifest)


async def restore_backup(
    backup_path: Path,
    *,
    database_url: str,
    force: bool = False,
) -> RestoreResult:
    """Restore a backup package into a SQLite database path."""
    if not backup_path.is_file():
        raise BackupServiceError(f"backup file does not exist: {backup_path}")

    target_db = sqlite_path_from_url(database_url)
    if target_db.exists() and not force:
        raise BackupServiceError(
            f"target database already exists: {target_db}；如需覆盖请显式传入 --force。"
        )
    target_db.parent.mkdir(parents=True, exist_ok=True)
    temp_target = target_db.with_name(f".{target_db.name}.restore-tmp")
    if temp_target.exists():
        temp_target.unlink()

    try:
        try:
            with zipfile.ZipFile(backup_path, "r") as archive:
                manifest = _read_manifest(archive)
                try:
                    with archive.open(SNAPSHOT_MEMBER, "r") as source, temp_target.open(
                        "wb"
                    ) as destination:
                        shutil.copyfileobj(source, destination)
                except KeyError as exc:
                    raise BackupServiceError("backup package missing db/songyan.db") from exc
        except zipfile.BadZipFile as exc:
            raise BackupServiceError("backup package is not a valid zip file") from exc

        expected_hash = manifest.get("database", {}).get("sha256")
        actual_hash = _sha256_file(temp_target)
        if expected_hash and expected_hash != actual_hash:
            raise BackupServiceError("restored database hash does not match manifest")

        schema = _schema_ledger(temp_target)
        if schema["status"] != "pass":
            raise BackupServiceError(
                "restored database schema check failed: "
                + ", ".join(schema.get("missing_tables", []))
            )

        os.replace(temp_target, target_db)
    finally:
        if temp_target.exists():
            temp_target.unlink()

    return RestoreResult(database_path=target_db, manifest=manifest, schema=schema)
