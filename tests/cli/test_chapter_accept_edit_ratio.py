"""task 253：S5 人改率警告的 CLI 行为（accept stderr/JSON + chapter status 露出）。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from songyan.cli.main import cli
from songyan.config import settings
from songyan.db.migrations import init_schema
from songyan.db.repository import (
    ChapterHeadRepository,
    ChapterVersionRepository,
    ProjectRepository,
)
from songyan.models.chapter import ChapterHead, ChapterVersion
from songyan.models.project import ProjectSetting

_PROJECT = "p-edratio"
_CHAPTER = 1

_DRAFT = "夜色压低站台，陈屿等着末班车。\n" * 12  # 12 行工作稿


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
async def ratio_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "edit-ratio.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="mystery",
            mode_id="webnovel",
            protagonist_name="陈照",
            title="edit ratio",
        ),
        _PROJECT,
    )
    await ChapterVersionRepository().create(
        ChapterVersion(
            version_id="ver-draft",
            project_id=_PROJECT,
            chapter_number=_CHAPTER,
            version_number=1,
            version_type="draft",
            content=_DRAFT,
            word_count=len(_DRAFT),
        )
    )
    await ChapterHeadRepository().update(
        ChapterHead(
            project_id=_PROJECT,
            chapter_number=_CHAPTER,
            current_version_id="ver-draft",
            accepted_version_id=None,
            status="draft",
        )
    )
    return db_path


def test_accept_pure_copy_warns_exit_0(
    runner: CliRunner, ratio_db: Path
) -> None:
    result = runner.invoke(
        cli,
        [
            "chapter",
            "accept",
            "--project-id",
            _PROJECT,
            "--chapter",
            str(_CHAPTER),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "所有权提醒" in result.stderr
    assert "人改率" in result.stderr


def test_accept_pure_copy_json_has_edit_ratio(
    runner: CliRunner, ratio_db: Path
) -> None:
    result = runner.invoke(
        cli,
        [
            "chapter",
            "accept",
            "--project-id",
            _PROJECT,
            "--chapter",
            str(_CHAPTER),
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["edit_ratio"] == 0.0


def test_accept_from_file_heavy_edit_no_warning(
    runner: CliRunner, ratio_db: Path, tmp_path: Path
) -> None:
    edited = tmp_path / "edited.txt"
    edited.write_text(
        "清晨的南站没什么人，陈照拎着行李走过天桥。\n" * 12,
        encoding="utf-8",
    )
    result = runner.invoke(
        cli,
        [
            "chapter",
            "accept",
            "--project-id",
            _PROJECT,
            "--chapter",
            str(_CHAPTER),
            "--from-file",
            str(edited),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "所有权提醒" not in result.stderr


def test_chapter_status_shows_edit_ratio(
    runner: CliRunner, ratio_db: Path
) -> None:
    runner.invoke(
        cli,
        [
            "chapter",
            "accept",
            "--project-id",
            _PROJECT,
            "--chapter",
            str(_CHAPTER),
        ],
    )
    result = runner.invoke(
        cli,
        [
            "chapter",
            "status",
            "--project-id",
            _PROJECT,
            "--chapter",
            str(_CHAPTER),
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["state"] == "settled"
    assert payload["edit_ratio"] == 0.0
