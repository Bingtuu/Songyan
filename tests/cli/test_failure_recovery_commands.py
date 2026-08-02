"""Task 212: CLI failure recovery advice tests."""

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
async def export_recovery_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "export-recovery.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            title="无 accepted 项目",
            genre_id="scifi",
            mode_id="webnovel",
            protagonist_name="林远",
        ),
        "no-accepted-project",
    )
    return db_path


def test_export_no_accepted_content_shows_recovery_advice(
    runner: CliRunner,
    export_recovery_db: Path,
) -> None:
    result = runner.invoke(
        cli,
        [
            "export",
            "--project-id",
            "no-accepted-project",
            "--chapters",
            "1-3",
            "--format",
            "md",
            "--output",
            "exports",
        ],
    )

    assert result.exit_code != 0
    assert "没有可导出的 accepted 章节" in result.output
    assert "[no_accepted_content]" in result.output
    assert "songyan run --project-id no-accepted-project" in result.output
