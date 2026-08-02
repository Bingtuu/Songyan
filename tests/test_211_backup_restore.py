"""Task 211: backup / restore / schema ledger service tests."""

from __future__ import annotations

import json
import sqlite3
import zipfile
from pathlib import Path

import pytest

from songyan.config import settings
from songyan.db.migrations import init_schema
from songyan.db.project_run_repo import ProjectRunRepository
from songyan.db.repository import ProjectRepository
from songyan.exceptions import SongyanError
from songyan.models import ProjectSetting
from songyan.models.project_run import ProjectRunState
from songyan.services.backup_service import (
    BACKUP_FORMAT,
    CONFIG_SUMMARY_MEMBER,
    LOG_INDEX_MEMBER,
    MANIFEST_MEMBER,
    RUNS_MEMBER,
    SNAPSHOT_MEMBER,
    backup_project,
    restore_backup,
)


@pytest.fixture
async def backup_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "source.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    monkeypatch.setattr(settings, "llm_api_key", "secret-test-key")
    monkeypatch.setattr(settings, "llm_base_url", "https://api.example.test")
    monkeypatch.setattr(settings, "llm_model", "test-model")
    monkeypatch.setattr(settings, "checkpointer_mode", "memory")
    monkeypatch.setattr(settings, "run_cost_budget", 12.5)
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            title="备份测试",
            genre_id="xuanhuan",
            mode_id="webnovel_intense",
            protagonist_name="陆沉",
        ),
        "proj-backup",
    )
    await ProjectRunRepository().create(
        ProjectRunState(
            run_id="run-backup",
            project_id="proj-backup",
            chapter_range_start=1,
            chapter_range_end=3,
            current_chapter=2,
            completed_chapters=[1],
            failed_chapters=[2],
            total_cost=0.42,
            status="failed",
            pause_reason="llm_error",
        )
    )
    log_dir = tmp_path / "logs" / "chapter_runs"
    report_dir = tmp_path / "logs" / "reports"
    log_dir.mkdir(parents=True)
    report_dir.mkdir(parents=True)
    (log_dir / "run-backup.jsonl").write_text('{"run_id":"run-backup"}\n', encoding="utf-8")
    (report_dir / "report-run-backup.md").write_text("# report\n", encoding="utf-8")
    return db_path


@pytest.mark.asyncio
async def test_backup_package_contains_manifest_snapshot_and_no_secrets(
    backup_db: Path,
    tmp_path: Path,
) -> None:
    result = await backup_project("proj-backup", output=tmp_path / "backups")

    assert result.backup_path.is_file()
    with zipfile.ZipFile(result.backup_path) as archive:
        names = set(archive.namelist())
        assert MANIFEST_MEMBER in names
        assert SNAPSHOT_MEMBER in names
        assert CONFIG_SUMMARY_MEMBER in names
        assert RUNS_MEMBER in names
        assert LOG_INDEX_MEMBER in names
        assert ".env" not in names

        manifest = json.loads(archive.read(MANIFEST_MEMBER).decode("utf-8"))
        config_summary = json.loads(
            archive.read(CONFIG_SUMMARY_MEMBER).decode("utf-8")
        )
        runs = json.loads(archive.read(RUNS_MEMBER).decode("utf-8"))
        logs = json.loads(archive.read(LOG_INDEX_MEMBER).decode("utf-8"))

    assert manifest["format"] == BACKUP_FORMAT
    assert manifest["project"]["project_id"] == "proj-backup"
    assert manifest["schema"]["status"] == "pass"
    assert manifest["database"]["sha256"]
    assert manifest["sensitive_data"]["api_key_included"] is False
    assert manifest["sensitive_data"]["env_file_included"] is False
    assert config_summary["runtime"]["llm_api_key_configured"] is True
    assert "secret-test-key" not in json.dumps(manifest, ensure_ascii=False)
    assert "secret-test-key" not in json.dumps(config_summary, ensure_ascii=False)
    assert runs[0]["run_id"] == "run-backup"
    assert logs["content_included"] is False
    assert logs["existing_count"] == 2


@pytest.mark.asyncio
async def test_restore_backup_to_new_database_and_refuse_overwrite(
    backup_db: Path,
    tmp_path: Path,
) -> None:
    backup = await backup_project("proj-backup", output=tmp_path / "asset.zip")
    restored_db = tmp_path / "restored.db"

    restored = await restore_backup(
        backup.backup_path,
        database_url=f"sqlite:///{restored_db}",
    )

    assert restored.database_path == restored_db
    assert restored.schema["status"] == "pass"
    with sqlite3.connect(restored_db) as conn:
        row = conn.execute(
            "SELECT title, genre_id FROM projects WHERE project_id = ?",
            ("proj-backup",),
        ).fetchone()
    assert row == ("备份测试", "xuanhuan")

    with pytest.raises(SongyanError, match="already exists"):
        await restore_backup(
            backup.backup_path,
            database_url=f"sqlite:///{restored_db}",
        )


@pytest.mark.asyncio
async def test_restore_force_overwrites_existing_database(
    backup_db: Path,
    tmp_path: Path,
) -> None:
    backup = await backup_project("proj-backup", output=tmp_path / "asset-force.zip")
    restored_db = tmp_path / "force.db"
    restored_db.write_bytes(b"not sqlite")

    restored = await restore_backup(
        backup.backup_path,
        database_url=f"sqlite:///{restored_db}",
        force=True,
    )

    assert restored.database_path == restored_db
    with sqlite3.connect(restored_db) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM projects WHERE project_id = ?",
            ("proj-backup",),
        ).fetchone()[0]
    assert count == 1


@pytest.mark.asyncio
async def test_backup_rejects_missing_project(
    backup_db: Path,
    tmp_path: Path,
) -> None:
    with pytest.raises(SongyanError, match="project not found"):
        await backup_project("missing", output=tmp_path / "backups")
