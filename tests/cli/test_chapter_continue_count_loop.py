"""M4 步 3 切片 6: chapter continue 逐章循环（tech-m4 §5 步 3 / B4）。

--count 2 第一章生成后停闸 exit 0 + next_hint；accept 后再 continue 推进第二章；
resume 时版本已落库 → B1② exit 2。每测试钉死 approved / accepted 集不变。
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from click.testing import CliRunner, Result

from songyan.cli.main import cli
from songyan.config import settings
from songyan.db.migrations import init_schema
from songyan.db.plan_fact_repo import PlanFactRepository
from songyan.db.project_run_repo import ProjectRunRepository
from songyan.db.repository import (
    ChapterHeadRepository,
    ChapterVersionRepository,
    ProjectRepository,
)
from songyan.models.chapter import ChapterHead, ChapterVersion
from songyan.models.project import ProjectSetting
from songyan.models.project_run import ProjectRunState
from songyan.models.settlement import StateSettlement
from songyan.services.chapter_accept import accept_chapter
from songyan.utils.word_count import count_chinese_words

_PROJECT = "p-m4-cont-count"
_BODY_1 = "第一章草稿：陈照走进南站雨夜。"
_BODY_2 = "第二章草稿：末班车载着铜镜的光。"
_SUMMARY_JSON = (
    '{"plot_summary": "陈照抵达北站。", "key_events": ["陈照到北站"], '
    '"characters_appeared": ["陈照"], "emotional_tone": "沉静"}'
)


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
async def count_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "m4-cont-count.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="mystery_noir",
            mode_id="webnovel",
            protagonist_name="陈照",
            title="m4 continue count",
        ),
        _PROJECT,
    )
    return db_path


def _install_settlement_mocks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "songyan.agents.summary_writer.call_llm", AsyncMock(return_value=_SUMMARY_JSON)
    )
    monkeypatch.setattr(
        "songyan.services.chapter_continue.extract_settlement",
        AsyncMock(return_value=StateSettlement(validation_status="valid")),
    )


async def _seed_empty_head(chapter: int) -> None:
    await ChapterHeadRepository().update(
        ChapterHead(
            project_id=_PROJECT,
            chapter_number=chapter,
            current_version_id=None,
            accepted_version_id=None,
            status="draft",
        )
    )


def _invoke_continue(runner: CliRunner, *extra: str) -> Result:
    return runner.invoke(cli, ["chapter", "continue", "--project-id", _PROJECT, *extra])


async def _approved_snapshot() -> frozenset[tuple[str, str]]:
    repo = PlanFactRepository()
    pairs: set[tuple[str, str]] = set()
    for row in await repo.list_canon_entities(_PROJECT):
        pairs.add(("entity", row.entity_id))
    for row in await repo.list_canon_attributes(_PROJECT):
        pairs.add(("attribute", row.attribute_id))
    for row in await repo.list_canon_events(_PROJECT):
        pairs.add(("event", row.event_id))
    for row in await repo.list_canon_clues(_PROJECT):
        pairs.add(("clue", row.clue_id))
    for row in await repo.list_canon_time_anchors(_PROJECT):
        pairs.add(("time_anchor", row.anchor_id))
    return frozenset(pairs)


async def _accepted_snapshot() -> frozenset[tuple[int, str]]:
    heads = await ChapterHeadRepository().list_by_project(_PROJECT)
    return frozenset(
        (h.chapter_number, h.accepted_version_id)
        for h in heads
        if h.accepted_version_id is not None
    )


def test_count_two_stops_after_first_chapter(
    runner: CliRunner, count_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    asyncio.run(_seed_empty_head(1))
    before_approved = asyncio.run(_approved_snapshot())
    before_accepted = asyncio.run(_accepted_snapshot())
    monkeypatch.setattr("songyan.agents.writer.call_llm", AsyncMock(return_value=_BODY_1))

    result = _invoke_continue(runner, "--count", "2", "--json")
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["chapter"] == 1
    assert "chapter accept --chapter 1" in payload["next_hint"]

    versions = asyncio.run(ChapterVersionRepository().list_by_chapter(_PROJECT, 1))
    assert len(versions) == 1
    # 未 accept 不推进：ch2 无写入。
    assert asyncio.run(ChapterVersionRepository().list_by_chapter(_PROJECT, 2)) == []
    assert asyncio.run(_approved_snapshot()) == before_approved
    assert asyncio.run(_accepted_snapshot()) == before_accepted


def test_accept_then_continue_advances_to_second_chapter(
    runner: CliRunner, count_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    asyncio.run(_seed_empty_head(1))
    monkeypatch.setattr("songyan.agents.writer.call_llm", AsyncMock(return_value=_BODY_1))
    first = _invoke_continue(runner, "--count", "2")
    assert first.exit_code == 0, first.output

    asyncio.run(accept_chapter(_PROJECT, 1))
    _install_settlement_mocks(monkeypatch)
    asyncio.run(_seed_empty_head(2))

    monkeypatch.setattr("songyan.agents.writer.call_llm", AsyncMock(return_value=_BODY_2))
    second = _invoke_continue(runner, "--count", "2", "--json")
    assert second.exit_code == 0, second.output
    payload = json.loads(second.stdout)
    assert payload["chapter"] == 2
    assert "chapter accept --chapter 2" in payload["next_hint"]

    accepted = asyncio.run(_accepted_snapshot())
    assert any(chapter == 1 for chapter, _ in accepted)


def test_resume_with_landed_version_exit_2(
    runner: CliRunner, count_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """resume 场景：paused 壳在、版本已落库 → B1② exit 2 接管（锚定）。"""
    version = ChapterVersion(
        version_id="v-count-1-landed",
        project_id=_PROJECT,
        chapter_number=1,
        version_number=1,
        version_type="draft",
        content=_BODY_1,
        word_count=count_chinese_words(_BODY_1),
    )
    asyncio.run(ChapterVersionRepository().create(version))
    asyncio.run(
        ChapterHeadRepository().update(
            ChapterHead(
                project_id=_PROJECT,
                chapter_number=1,
                current_version_id=version.version_id,
                accepted_version_id=None,
                status="draft",
            )
        )
    )

    async def _seed_paused_shell() -> None:
        await ProjectRunRepository().create(
            ProjectRunState(
                run_id="run-paused-1",
                project_id=_PROJECT,
                chapter_range_start=1,
                chapter_range_end=1,
                current_chapter=1,
                status="paused",
                pause_reason="llm_error: boom",
            )
        )

    asyncio.run(_seed_paused_shell())
    monkeypatch.setattr("songyan.agents.writer.call_llm", AsyncMock(return_value=_BODY_2))

    result = _invoke_continue(runner)
    assert result.exit_code == 2, result.output
    # 不追加新版本。
    versions = asyncio.run(ChapterVersionRepository().list_by_chapter(_PROJECT, 1))
    assert [v.version_id for v in versions] == ["v-count-1-landed"]
