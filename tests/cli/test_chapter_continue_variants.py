"""M4 步 3 切片 4: chapter continue --variants 转调（tech-m4 §5 步 3 / B7）。

--variants 2 → 两槽 generated、不 auto-pick、plan_* 不变；
--variants 2 --count 2 → 本章生成后停闸 exit 0。accepted 集不变。
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest
from click.testing import CliRunner, Result

from songyan.cli.main import cli
from songyan.config import settings
from songyan.db.chapter_variant_repo import ChapterVariantRepository
from songyan.db.migrations import init_schema
from songyan.db.plan_fact_repo import PlanFactRepository
from songyan.db.repository import (
    ChapterHeadRepository,
    ChapterVersionRepository,
    ProjectRepository,
)
from songyan.models.chapter import ChapterHead, ChapterVersion
from songyan.models.project import ProjectSetting
from songyan.models.settlement import StateSettlement
from songyan.services.chapter_accept import accept_chapter
from songyan.services.variant_generate import SlotDraft

_PROJECT = "p-m4-cont-variants"
_CONTENT_1 = "槽一：南站夜色。" * 15
_CONTENT_2 = "槽二：南站雨幕。" * 15
_SUMMARY_JSON = (
    '{"plot_summary": "陈照抵达北站。", "key_events": ["陈照到北站"], '
    '"characters_appeared": ["陈照"], "emotional_tone": "沉静"}'
)


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
async def variants_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "m4-cont-variants.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="mystery_noir",
            mode_id="webnovel",
            protagonist_name="陈照",
            title="m4 continue variants",
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


def _install_slot_mock(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    texts = [_CONTENT_1, _CONTENT_2]
    calls = {"i": 0}

    async def _draft(**_kwargs: Any) -> SlotDraft:
        idx = calls["i"]
        calls["i"] += 1
        return SlotDraft(content=texts[idx], cost_cny_estimate=0.01)

    mock = AsyncMock(side_effect=_draft)
    monkeypatch.setattr("songyan.services.variant_generate.default_slot_draft", mock)
    return mock


async def _seed_accepted(chapter: int) -> None:
    version = ChapterVersion(
        version_id=f"v-var-{chapter}-draft",
        project_id=_PROJECT,
        chapter_number=chapter,
        version_number=1,
        version_type="draft",
        content="第一章：陈照到了北站。",
        word_count=10,
    )
    await ChapterVersionRepository().create(version)
    await ChapterHeadRepository().update(
        ChapterHead(
            project_id=_PROJECT,
            chapter_number=chapter,
            current_version_id=version.version_id,
            accepted_version_id=None,
            status="draft",
        )
    )
    await accept_chapter(_PROJECT, chapter)
    # 让下一章进入章宇宙（目标章）。
    await ChapterHeadRepository().update(
        ChapterHead(
            project_id=_PROJECT,
            chapter_number=chapter + 1,
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


def test_variants_two_slots_generated_no_autopick(
    runner: CliRunner, variants_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    asyncio.run(_seed_accepted(1))
    before_approved = asyncio.run(_approved_snapshot())
    before_accepted = asyncio.run(_accepted_snapshot())
    _install_settlement_mocks(monkeypatch)
    _install_slot_mock(monkeypatch)

    result = _invoke_continue(runner, "--variants", "2")
    assert result.exit_code == 0, result.output
    assert "variant pick" in result.output

    slots = asyncio.run(ChapterVariantRepository().list_for_chapter(_PROJECT, 2))
    assert len(slots) == 2
    assert all(s.status == "generated" for s in slots)
    # 不 auto-pick。
    assert asyncio.run(ChapterVariantRepository().get_picked(_PROJECT, 2)) is None
    # 不动 head 工作指针（current 仍为 NULL）。
    head2 = asyncio.run(ChapterHeadRepository().get(_PROJECT, 2))
    assert head2 is None or head2.current_version_id is None

    assert asyncio.run(_approved_snapshot()) == before_approved
    assert asyncio.run(_accepted_snapshot()) == before_accepted


def test_variants_with_count_stops_after_chapter(
    runner: CliRunner, variants_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--variants 2 --count 2 = 本章转调生成后同停闸语义（逐章），exit 0。"""
    asyncio.run(_seed_accepted(1))
    _install_settlement_mocks(monkeypatch)
    _install_slot_mock(monkeypatch)

    result = _invoke_continue(runner, "--variants", "2", "--count", "2")
    assert result.exit_code == 0, result.output
    assert "variant pick" in result.output

    slots = asyncio.run(ChapterVariantRepository().list_for_chapter(_PROJECT, 2))
    assert len(slots) == 2
    # 只推进一章：ch3 无写入。
    assert asyncio.run(ChapterHeadRepository().get(_PROJECT, 3)) is None
