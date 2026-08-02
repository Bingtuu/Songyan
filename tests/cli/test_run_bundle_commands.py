"""Task 213: CLI run bundle command tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from songyan.cli.main import cli
from songyan.config import settings
from songyan.db.migrations import init_schema
from songyan.db.project_run_repo import ProjectRunRepository
from songyan.db.repository import ProjectRepository
from songyan.models import ProjectSetting
from songyan.models.project_run import ProjectRunState
from songyan.models.run_log import ChapterRunLog


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
async def bundle_cli_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    from datetime import datetime

    db_path = tmp_path / "cli-bundle.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            title="CLI 诊断包项目",
            genre_id="scifi",
            mode_id="webnovel",
            protagonist_name="林远",
        ),
        "cli-bundle-project",
    )
    await ProjectRunRepository().create(
        ProjectRunState(
            run_id="cli-run-bundle",
            project_id="cli-bundle-project",
            chapter_range_start=1,
            chapter_range_end=1,
            current_chapter=1,
            completed_chapters=[1],
            failed_chapters=[],
            status="completed",
        )
    )
    log_dir = tmp_path / "logs" / "chapter_runs"
    log_dir.mkdir(parents=True)
    log = ChapterRunLog(
        log_id="cli-log-1",
        run_id="cli-run-bundle",
        project_id="cli-bundle-project",
        chapter_number=1,
        started_at=datetime(2026, 1, 1, 0, 0),
        finished_at=datetime(2026, 1, 1, 0, 1),
        success=True,
        word_count=3000,
        budget_used=0.7,
        quality_gate_passed=True,
    )
    (log_dir / "cli-run-bundle.jsonl").write_text(log.to_jsonl() + "\n", encoding="utf-8")
    return db_path


def test_bundle_run_help(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["bundle-run", "--help"])

    assert result.exit_code == 0
    assert "--run-id" in result.output
    assert "--output" in result.output


def test_bundle_run_success(
    runner: CliRunner,
    bundle_cli_db: Path,
    tmp_path: Path,
) -> None:
    result = runner.invoke(
        cli,
        [
            "bundle-run",
            "--run-id",
            "cli-run-bundle",
            "--output",
            str(tmp_path / "bundles"),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "诊断包已生成" in result.output
    assert "bundle.json" in result.output
    assert len(list((tmp_path / "bundles").glob("*.zip"))) == 1


def test_bundle_run_missing_log_shows_recovery_advice(
    runner: CliRunner,
    bundle_cli_db: Path,
    tmp_path: Path,
) -> None:
    result = runner.invoke(
        cli,
        [
            "bundle-run",
            "--run-id",
            "missing-run",
            "--output",
            str(tmp_path / "bundles"),
        ],
    )

    assert result.exit_code != 0
    assert "run log not found" in result.output
    assert "[missing_artifact]" in result.output
    assert "Get-ChildItem logs/chapter_runs" in result.output
