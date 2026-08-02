"""Task 211: CLI backup / restore command tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from songyan.cli.main import cli
from songyan.config import settings
from songyan.db.migrations import init_schema
from songyan.db.repository import ProjectRepository
from songyan.models import ProjectSetting


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
async def backup_cli_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "cli-backup.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    monkeypatch.setattr(settings, "llm_api_key", "cli-secret")
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            title="CLI 备份项目",
            genre_id="scifi",
            mode_id="webnovel",
            protagonist_name="林远",
        ),
        "cli-backup-project",
    )
    return db_path


def test_backup_and_restore_help(runner: CliRunner) -> None:
    backup_help = runner.invoke(cli, ["backup", "--help"])
    restore_help = runner.invoke(cli, ["restore", "--help"])

    assert backup_help.exit_code == 0, backup_help.output
    assert "--project-id" in backup_help.output
    assert "--output" in backup_help.output
    assert restore_help.exit_code == 0, restore_help.output
    assert "--backup" in restore_help.output
    assert "--database-url" in restore_help.output


def test_backup_restore_roundtrip(
    runner: CliRunner,
    backup_cli_db: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backup_result = runner.invoke(
        cli,
        [
            "backup",
            "--project-id",
            "cli-backup-project",
            "--output",
            str(tmp_path / "backups"),
        ],
    )

    assert backup_result.exit_code == 0, backup_result.output
    assert "备份已生成" in backup_result.output
    backup_files = list((tmp_path / "backups").glob("*.zip"))
    assert len(backup_files) == 1

    restored_db = tmp_path / "restored.db"
    restore_result = runner.invoke(
        cli,
        [
            "restore",
            "--backup",
            str(backup_files[0]),
            "--database-url",
            f"sqlite:///{restored_db}",
        ],
    )

    assert restore_result.exit_code == 0, restore_result.output
    assert "恢复完成" in restore_result.output
    assert restored_db.exists()

    monkeypatch.setattr(settings, "database_url", f"sqlite:///{restored_db}")
    list_result = runner.invoke(cli, ["list-projects"])
    assert list_result.exit_code == 0, list_result.output
    assert "cli-backup-project" in list_result.output
    assert "CLI 备份项目" in list_result.output


def test_restore_refuses_existing_database_without_force(
    runner: CliRunner,
    backup_cli_db: Path,
    tmp_path: Path,
) -> None:
    backup_result = runner.invoke(
        cli,
        [
            "backup",
            "--project-id",
            "cli-backup-project",
            "--output",
            str(tmp_path / "backup.zip"),
        ],
    )
    assert backup_result.exit_code == 0, backup_result.output

    restored_db = tmp_path / "existing.db"
    restored_db.write_bytes(b"existing")
    restore_result = runner.invoke(
        cli,
        [
            "restore",
            "--backup",
            str(tmp_path / "backup.zip"),
            "--database-url",
            f"sqlite:///{restored_db}",
        ],
    )

    assert restore_result.exit_code != 0
    assert "already exists" in restore_result.output or "已存在" in restore_result.output


def test_backup_missing_project_fails(
    runner: CliRunner,
    backup_cli_db: Path,
    tmp_path: Path,
) -> None:
    result = runner.invoke(
        cli,
        [
            "backup",
            "--project-id",
            "missing",
            "--output",
            str(tmp_path / "backups"),
        ],
    )

    assert result.exit_code != 0
    assert "project not found" in result.output


def test_restore_bad_zip_fails(runner: CliRunner, tmp_path: Path) -> None:
    bad_zip = tmp_path / "bad.zip"
    bad_zip.write_text("not a zip", encoding="utf-8")

    result = runner.invoke(
        cli,
        [
            "restore",
            "--backup",
            str(bad_zip),
            "--database-url",
            f"sqlite:///{tmp_path / 'restored.db'}",
        ],
    )

    assert result.exit_code != 0
    assert "not a valid zip" in result.output
