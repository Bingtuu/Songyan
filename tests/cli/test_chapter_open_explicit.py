"""task 263：``chapter continue --chapter N`` 显式开章（形态 A）。

不在章宇宙 → 命令内联铺 empty head（产品原生 seeding，替代 runbook 的 SQL）；
章号跳跃（前面有未写章）→ exit 2 防 settlement 断档；已 accepted → exit 2。
省略 --chapter = 现状自动 targeting 零变化。
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from click.testing import CliRunner

from songyan.cli.main import cli
from songyan.config import settings
from songyan.db.migrations import init_schema
from songyan.db.repository import (
    ChapterHeadRepository,
    ChapterVersionRepository,
    CharacterRepository,
    ProjectRepository,
)
from songyan.models.chapter import ChapterHead, ChapterVersion
from songyan.models.character import Character
from songyan.models.project import ProjectSetting

_PROJECT = "p-open-chapter"
_CHARACTER_ID = "char-open"
_BODY = "第二章正文：陈照走进雨里，末班车进站。" * 6
_BODY_LONG = "第三章正文：陈照在车厢里坐下。" * 25
_SETTLEMENT_JSON = json.dumps(
    {
        "character_updates": [
            {
                "character_id": _CHARACTER_ID,
                "field": "location",
                "old_value": "",
                "new_value": "途中",
                "source_quote": "陈照",
            }
        ]
    },
    ensure_ascii=False,
)
_SUMMARY_JSON = (
    '{"plot_summary": "陈照继续赶路。", "key_events": ["陈照在路上"], '
    '"characters_appeared": ["陈照"], "emotional_tone": "沉静"}'
)


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
async def open_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "open-chapter.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="mystery_noir",
            mode_id="webnovel",
            protagonist_name="陈照",
            title="open chapter",
        ),
        _PROJECT,
    )
    await CharacterRepository().create(
        Character(
            character_id=_CHARACTER_ID,
            project_id=_PROJECT,
            name="陈照",
            role_type="protagonist",
        )
    )
    return db_path


def _mock_llm(monkeypatch: pytest.MonkeyPatch, bodies: list[str]) -> None:
    from songyan.services.variant_generate import SlotDraft

    monkeypatch.setattr(
        "songyan.agents.writer.call_llm", AsyncMock(side_effect=bodies)
    )
    monkeypatch.setattr(
        "songyan.agents.settlement_extractor.call_llm",
        AsyncMock(return_value=_SETTLEMENT_JSON),
    )
    monkeypatch.setattr(
        "songyan.agents.summary_writer.call_llm",
        AsyncMock(return_value=_SUMMARY_JSON),
    )
    monkeypatch.setattr(
        "songyan.services.variant_generate.default_slot_draft",
        AsyncMock(
            side_effect=[SlotDraft(content=b, cost_cny_estimate=0.01) for b in bodies]
        ),
    )


async def _accept_chapter_one() -> None:
    versions = ChapterVersionRepository()
    await versions.create(
        ChapterVersion(
            version_id="ver-open-1",
            project_id=_PROJECT,
            chapter_number=1,
            version_number=1,
            version_type="draft",
            content="第一章正文。" * 30,
            word_count=150,
        )
    )
    await versions.create(
        ChapterVersion(
            version_id="ver-open-1-acc",
            project_id=_PROJECT,
            chapter_number=1,
            version_number=2,
            version_type="accepted",
            content="第一章正文。" * 30,
            word_count=150,
            parent_version_id="ver-open-1",
        )
    )
    await ChapterHeadRepository().update(
        ChapterHead(
            project_id=_PROJECT,
            chapter_number=1,
            current_version_id="ver-open-1-acc",
            accepted_version_id="ver-open-1-acc",
            status="accepted",
        )
    )


def test_explicit_chapter_opens_and_drafts(
    runner: CliRunner, open_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ch1 accepted 后 continue --chapter 2：内联铺 head + 生成草稿（无 SQL seeding）。"""
    asyncio.run(_accept_chapter_one())
    _mock_llm(monkeypatch, [_BODY])

    result = runner.invoke(
        cli, ["chapter", "continue", "--project-id", _PROJECT, "--chapter", "2"]
    )

    assert result.exit_code == 0, result.output
    head = asyncio.run(ChapterHeadRepository().get(_PROJECT, 2))
    assert head is not None
    assert head.current_version_id is not None  # 草稿已生成


def test_gap_chapter_rejected_exit_2(
    runner: CliRunner, open_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--chapter 3 而 ch2 未写 → exit 2（防 settlement 上一章断档）。"""
    asyncio.run(_accept_chapter_one())
    _mock_llm(monkeypatch, [_BODY_LONG])

    result = runner.invoke(
        cli, ["chapter", "continue", "--project-id", _PROJECT, "--chapter", "3"]
    )

    assert result.exit_code == 2
    assert "章 2" in result.stderr
    head = asyncio.run(ChapterHeadRepository().get(_PROJECT, 3))
    assert head is None  # 未铺 head，零写入


def test_accepted_chapter_rejected_exit_2(
    runner: CliRunner, open_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    asyncio.run(_accept_chapter_one())
    _mock_llm(monkeypatch, [_BODY])

    result = runner.invoke(
        cli, ["chapter", "continue", "--project-id", _PROJECT, "--chapter", "1"]
    )

    assert result.exit_code == 2
    assert "已 accepted" in result.stderr


def test_empty_project_open_chapter_one(
    runner: CliRunner, open_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """空项目 --chapter 1：不再依赖 run 先打出 ch1（新项目的最原生开书路径）。"""
    _mock_llm(monkeypatch, [_BODY])

    result = runner.invoke(
        cli, ["chapter", "continue", "--project-id", _PROJECT, "--chapter", "1"]
    )

    assert result.exit_code == 0, result.output
    head = asyncio.run(ChapterHeadRepository().get(_PROJECT, 1))
    assert head is not None and head.current_version_id is not None


def test_explicit_open_with_variants(
    runner: CliRunner, open_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """显式开章 + 抽卡转调：B7 路径对显式目标同样可用。"""
    asyncio.run(_accept_chapter_one())
    _mock_llm(monkeypatch, [_BODY, _BODY])

    result = runner.invoke(
        cli,
        [
            "chapter", "continue",
            "--project-id", _PROJECT,
            "--chapter", "2",
            "--variants", "2",
        ],
    )

    assert result.exit_code == 0, result.output
