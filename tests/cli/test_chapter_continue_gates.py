"""M4 步 3 切片 1: chapter continue 门禁（tech-m4 §5 步 3 / B1 / B11）。

B1 两前置 exit 2 且零写入；目标章判定跨章；--count 参数非法 exit 1；
空项目 / 全 accepted → exit 0。每测试钉死 plan_* approved 集与 accepted 集不变。
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
from songyan.db.chapter_variant_repo import ChapterVariantRepository
from songyan.db.connection import get_db
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
from songyan.models.variant import ChapterVariant
from songyan.services.chapter_accept import accept_chapter
from songyan.utils.word_count import count_chinese_words

_PROJECT = "p-m4-cont-gates"
_BODY = "夜雨落在南站站台。\n\n陈照收起铜镜，转身走进雨里。\n\n末班车进站了。"
_SUMMARY_JSON = (
    '{"plot_summary": "陈照抵达北站。", "key_events": ["陈照到北站"], '
    '"characters_appeared": ["陈照"], "emotional_tone": "沉静"}'
)
_TS = "2026-11-08T00:00:00Z"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
async def gates_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "m4-cont-gates.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="mystery_noir",
            mode_id="webnovel",
            protagonist_name="陈照",
            title="m4 continue gates",
        ),
        _PROJECT,
    )
    return db_path


def _install_mocks(monkeypatch: pytest.MonkeyPatch) -> None:
    writer = AsyncMock(return_value=_BODY)
    monkeypatch.setattr("songyan.agents.writer.call_llm", writer)
    monkeypatch.setattr(
        "songyan.agents.summary_writer.call_llm",
        AsyncMock(return_value=_SUMMARY_JSON),
    )
    monkeypatch.setattr(
        "songyan.services.chapter_continue.extract_settlement",
        AsyncMock(return_value=StateSettlement(validation_status="valid")),
    )


def _invoke_continue(runner: CliRunner, *extra: str) -> Result:
    return runner.invoke(cli, ["chapter", "continue", "--project-id", _PROJECT, *extra])


async def _seed_accepted(chapter: int, content: str = "第一章正文：陈照到了南站。") -> str:
    """走 accept_chapter 真实写径产出一章 accepted（含 accepted 版本行）。"""
    version = ChapterVersion(
        version_id=f"v-gates-{chapter}-draft",
        project_id=_PROJECT,
        chapter_number=chapter,
        version_number=1,
        version_type="draft",
        content=content,
        word_count=count_chinese_words(content),
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
    outcome = await accept_chapter(_PROJECT, chapter)
    return outcome.accepted_version_id


async def _seed_empty_head(chapter: int) -> None:
    """让该章进入章宇宙（head 双指针 NULL，无工作稿）。"""
    await ChapterHeadRepository().update(
        ChapterHead(
            project_id=_PROJECT,
            chapter_number=chapter,
            current_version_id=None,
            accepted_version_id=None,
            status="draft",
        )
    )


async def _seed_workdraft(chapter: int) -> None:
    """目标章已有未确认工作稿（draft head，accepted NULL）。"""
    version = ChapterVersion(
        version_id=f"v-gates-{chapter}-work",
        project_id=_PROJECT,
        chapter_number=chapter,
        version_number=1,
        version_type="draft",
        content="未确认工作稿。",
        word_count=5,
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


async def _seed_generated_slot(chapter: int, slot: int = 1) -> None:
    version = ChapterVersion(
        version_id=f"v-gates-{chapter}-slot{slot}",
        project_id=_PROJECT,
        chapter_number=chapter,
        version_number=1,
        version_type="draft",
        content="槽稿。",
        word_count=3,
    )
    await ChapterVersionRepository().create(version)
    await ChapterVariantRepository().insert(
        ChapterVariant(
            variant_id=f"var-gates-{chapter}-{slot}",
            project_id=_PROJECT,
            chapter_number=chapter,
            slot_index=slot,
            status="generated",
            parent_canon_fingerprint="fp-gates",
            content_ref=version.version_id,
            created_at=_TS,
            updated_at=_TS,
        )
    )


async def _seed_picked_slot(chapter: int, slot: int, content_ref: str) -> None:
    await ChapterVariantRepository().insert(
        ChapterVariant(
            variant_id=f"var-gates-{chapter}-{slot}",
            project_id=_PROJECT,
            chapter_number=chapter,
            slot_index=slot,
            status="picked",
            parent_canon_fingerprint="fp-gates",
            content_ref=content_ref,
            created_at=_TS,
            updated_at=_TS,
        )
    )


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


async def _run_shell_count() -> int:
    async with get_db() as conn:
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM project_runs WHERE project_id = ?", (_PROJECT,)
        )
        row = await cursor.fetchone()
    return int(row[0]) if row else 0


async def _zero_writes(extra_check: bool = False) -> None:
    assert await _run_shell_count() == 0
    versions = await ChapterVersionRepository().list_by_chapter(_PROJECT, 2)
    assert versions == []
    assert not extra_check


# --- B1 前置 ①：目标章之前 picked 未 accept（accepted 章残留 picked 槽） ------


def test_picked_slot_before_target_exit_2_zero_writes(
    runner: CliRunner, gates_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ch1 accepted 但残留 picked 槽；目标 ch2 → exit 2 且全程零写入。"""
    accepted_id = asyncio.run(_seed_accepted(1))
    asyncio.run(_seed_picked_slot(1, 1, accepted_id))
    asyncio.run(_seed_empty_head(2))
    before_approved = asyncio.run(_approved_snapshot())
    before_accepted = asyncio.run(_accepted_snapshot())

    result = _invoke_continue(runner)
    assert result.exit_code == 2, result.output
    assert "picked" in result.output

    asyncio.run(_zero_writes())
    assert asyncio.run(_approved_snapshot()) == before_approved
    assert asyncio.run(_accepted_snapshot()) == before_accepted


# --- B1 前置 ②：目标章已有未确认工作稿 --------------------------------------


def test_target_with_unconfirmed_draft_exit_2(
    runner: CliRunner, gates_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    asyncio.run(_seed_accepted(1))
    asyncio.run(_seed_workdraft(2))
    before_approved = asyncio.run(_approved_snapshot())
    before_accepted = asyncio.run(_accepted_snapshot())

    result = _invoke_continue(runner)
    assert result.exit_code == 2, result.output
    assert "未确认" in result.output or "工作稿" in result.output

    assert asyncio.run(_run_shell_count()) == 0
    assert asyncio.run(_approved_snapshot()) == before_approved
    assert asyncio.run(_accepted_snapshot()) == before_accepted


def test_target_with_picked_slot_exit_2(
    runner: CliRunner, gates_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    asyncio.run(_seed_accepted(1))
    asyncio.run(_seed_generated_slot(2))
    asyncio.run(_seed_picked_slot(2, 2, "v-gates-2-slot2"))

    result = _invoke_continue(runner)
    assert result.exit_code == 2, result.output


# --- 目标章判定跨章 ----------------------------------------------------------


def test_target_determination_cross_chapter(
    runner: CliRunner, gates_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ch1 accepted、ch2 仅有 generated 槽 → 目标 = ch2 并生成草稿。"""
    asyncio.run(_seed_accepted(1))
    asyncio.run(_seed_generated_slot(2))
    before_approved = asyncio.run(_approved_snapshot())
    before_accepted = asyncio.run(_accepted_snapshot())
    _install_mocks(monkeypatch)

    result = _invoke_continue(runner, "--json")
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["chapter"] == 2

    head = asyncio.run(ChapterHeadRepository().get(_PROJECT, 2))
    assert head is not None
    assert head.current_version_id == payload["version_id"]
    assert head.accepted_version_id is None
    assert asyncio.run(_approved_snapshot()) == before_approved
    assert asyncio.run(_accepted_snapshot()) == before_accepted


# --- --count 参数非法 ---------------------------------------------------------


def test_count_four_exit_1(runner: CliRunner, gates_db: Path) -> None:
    asyncio.run(_seed_accepted(1))
    result = _invoke_continue(runner, "--count", "4")
    assert result.exit_code == 1
    asyncio.run(_zero_writes())


def test_count_zero_exit_1(runner: CliRunner, gates_db: Path) -> None:
    asyncio.run(_seed_accepted(1))
    result = _invoke_continue(runner, "--count", "0")
    assert result.exit_code == 1
    asyncio.run(_zero_writes())


# --- 空项目 / 全 accepted -----------------------------------------------------


def test_empty_project_exit_0(runner: CliRunner, gates_db: Path) -> None:
    result = _invoke_continue(runner)
    assert result.exit_code == 0, result.output
    assert "全部章已 accepted" in result.output


def test_all_accepted_exit_0(runner: CliRunner, gates_db: Path) -> None:
    asyncio.run(_seed_accepted(1))
    asyncio.run(_seed_accepted(2))
    result = _invoke_continue(runner)
    assert result.exit_code == 0, result.output
    assert "全部章已 accepted" in result.output
