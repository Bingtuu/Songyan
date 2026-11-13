"""task 256：`songyan project list`（PRD :559 之一；B7 只做 list）。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from songyan.cli.main import cli
from songyan.config import settings
from songyan.db.migrations import init_schema
from songyan.db.repository import ChapterHeadRepository, ProjectRepository
from songyan.models.chapter import ChapterHead
from songyan.models.project import ProjectSetting


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
async def multi_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "projects.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    repo = ProjectRepository()
    await repo.create(
        ProjectSetting(
            genre_id="mystery",
            mode_id="webnovel",
            protagonist_name="陈照",
            title="甲项目",
        ),
        "proj-aaa",
    )
    await repo.create(
        ProjectSetting(
            genre_id="urban",
            mode_id="webnovel",
            protagonist_name="李箱",
            title="乙项目",
        ),
        "proj-bbb",
    )
    await ChapterHeadRepository().update(
        ChapterHead(
            project_id="proj-aaa",
            chapter_number=1,
            current_version_id=None,
            accepted_version_id=None,
            status="draft",
        )
    )
    return db_path


def test_list_text(runner: CliRunner, multi_db: Path) -> None:
    result = runner.invoke(cli, ["project", "list"])
    assert result.exit_code == 0, result.output
    assert "proj-aaa" in result.output
    assert "proj-bbb" in result.output
    assert "甲项目" in result.output


def test_list_json_structure(runner: CliRunner, multi_db: Path) -> None:
    result = runner.invoke(cli, ["project", "list", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    by_id = {p["project_id"]: p for p in payload["projects"]}
    assert set(by_id) == {"proj-aaa", "proj-bbb"}
    assert by_id["proj-aaa"]["title"] == "甲项目"
    assert by_id["proj-aaa"]["genre_id"] == "mystery"
    assert by_id["proj-aaa"]["heads"] == 1
    assert by_id["proj-bbb"]["heads"] == 0


def test_list_empty_db_exit_0(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "empty.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    import asyncio

    asyncio.run(init_schema(db_path))
    result = runner.invoke(cli, ["project", "list", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["projects"] == []
