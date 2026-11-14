"""task 265 S2: chapter continue 空定向提醒（bible/goal/brief/story_brief 全空时可见提示）。"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from click.testing import CliRunner

from songyan.cli.main import cli
from songyan.config import settings
from songyan.db.migrations import init_schema
from songyan.db.narrative_repo import NarrativeRepository
from songyan.db.repository import ProjectRepository
from songyan.models import ProjectSetting
from songyan.models.narrative import StoryOutline

_PROJECT = "p-orient-notice"
_BODY = "夜雨落在站台。\n\n陈照收起铜镜，转身走进雨里。\n\n末班车进站了。"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
async def bare_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """裸项目：无书名/主角/钩子、无大纲——四路定向全空。"""
    db_path = tmp_path / "orient-notice.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="mystery_noir",
            mode_id="webnovel",
            protagonist_name="",
            words_per_chapter=2500,
        ),
        _PROJECT,
    )
    # 清空模板默认可能带入的定向字段，制造「四路全空」
    import sqlite3

    con = sqlite3.connect(db_path)
    con.execute(
        "UPDATE projects SET title='', protagonist_name='', core_hook='', "
        "protagonist_background='' WHERE project_id=?",
        (_PROJECT,),
    )
    con.commit()
    con.close()
    monkeypatch.setattr(
        "songyan.agents.writer.call_llm", AsyncMock(return_value=_BODY)
    )
    monkeypatch.setattr(
        "songyan.services.chapter_continue.extract_settlement",
        AsyncMock(return_value=None),
    )
    return db_path


def test_notice_fires_when_nothing_orients(
    runner: CliRunner, bare_db: Path
) -> None:
    result = runner.invoke(
        cli,
        ["chapter", "continue", "--project-id", _PROJECT, "--chapter", "1", "--json"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["orientation_notice"] is True


def test_notice_suppressed_with_storyline(
    runner: CliRunner, bare_db: Path
) -> None:
    async def _seed() -> None:
        await NarrativeRepository().upsert_outline(
            StoryOutline(
                project_id=_PROJECT,
                core_conflict="保安与鬼电梯的对峙",
            )
        )

    import asyncio

    asyncio.run(_seed())
    result = runner.invoke(
        cli,
        ["chapter", "continue", "--project-id", _PROJECT, "--chapter", "1", "--json"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["orientation_notice"] is False


def test_notice_printed_in_text_mode(runner: CliRunner, bare_db: Path) -> None:
    result = runner.invoke(
        cli,
        ["chapter", "continue", "--project-id", _PROJECT, "--chapter", "1"],
    )
    assert result.exit_code == 0, result.output
    assert "定向" in result.output
