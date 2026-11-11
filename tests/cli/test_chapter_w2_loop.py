"""M4 步 5: W2 短环 3 章连走集成测试（task 242 / tech-m4 §5 步 5 / §6 清单 1）。

``chapter continue`` → ``chapter accept`` 循环 3 章全链走通：settlement 在
continue 准备阶段自动补跑（第 2、3 章前 summaries 出现新行），只产 plan_*
pending 提案；全程 approved 行数零变化；accepted 集仅由显式 chapter accept
逐章 +1。

mock 面（评审 M1，钉死）：``songyan.agents.writer.call_llm``（三章不同正文）、
``songyan.agents.settlement_extractor.call_llm``（含指向种子角色的
character_updates 的合法 settlement JSON）、``songyan.agents.summary_writer.call_llm``
（防静默落到 fallback 路径）。种子数据不预置 summaries / character_states 行。
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
from songyan.db.connection import get_db
from songyan.db.migrations import init_schema
from songyan.db.plan_fact_repo import PlanFactRepository
from songyan.db.repository import (
    ChapterHeadRepository,
    ChapterVersionRepository,
    CharacterRepository,
    ProjectRepository,
)
from songyan.models.chapter import ChapterHead
from songyan.models.character import Character
from songyan.models.project import ProjectSetting

_PROJECT = "p-m4-w2-loop"
_CHARACTER_ID = "char-s1"
_BODY_1 = "第一章正文：陈照到了北站，铜镜在口袋里发烫。"
_BODY_2 = "第二章正文：陈照走进雨里，末班车进站。"
_BODY_3 = "第三章正文：陈照在车厢里坐下，铜镜渐渐冷却。"
# 同一 JSON 服务 ch1 / ch2 两次 settlement；source_quote 须在两次正文中都可命中。
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
async def loop_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "m4-w2-loop.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="mystery_noir",
            mode_id="webnovel",
            protagonist_name="陈照",
            title="m4 w2 loop",
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
    # 章宇宙：1..3 空 head；不预置 summaries / character_states 行。
    for chapter in (1, 2, 3):
        await ChapterHeadRepository().update(
            ChapterHead(
                project_id=_PROJECT,
                chapter_number=chapter,
                current_version_id=None,
                accepted_version_id=None,
                status="draft",
            )
        )
    return db_path


def _install_mocks(monkeypatch: pytest.MonkeyPatch) -> dict[str, AsyncMock]:
    writer = AsyncMock(side_effect=[_BODY_1, _BODY_2, _BODY_3])
    monkeypatch.setattr("songyan.agents.writer.call_llm", writer)
    settlement = AsyncMock(return_value=_SETTLEMENT_JSON)
    monkeypatch.setattr("songyan.agents.settlement_extractor.call_llm", settlement)
    summary = AsyncMock(return_value=_SUMMARY_JSON)
    monkeypatch.setattr("songyan.agents.summary_writer.call_llm", summary)
    return {"writer": writer, "settlement": settlement, "summary": summary}


def _invoke_continue(runner: CliRunner) -> Result:
    return runner.invoke(cli, ["chapter", "continue", "--project-id", _PROJECT])


def _invoke_accept(runner: CliRunner, chapter: int) -> Result:
    return runner.invoke(
        cli,
        ["chapter", "accept", "--project-id", _PROJECT, "--chapter", str(chapter)],
    )


async def _approved_snapshot() -> frozenset[tuple[str, str]]:
    repo = PlanFactRepository()
    pairs: set[tuple[str, str]] = set()
    for ent in await repo.list_canon_entities(_PROJECT):
        pairs.add(("entity", ent.entity_id))
    for attr in await repo.list_canon_attributes(_PROJECT):
        pairs.add(("attribute", attr.attribute_id))
    for evt in await repo.list_canon_events(_PROJECT):
        pairs.add(("event", evt.event_id))
    for clue in await repo.list_canon_clues(_PROJECT):
        pairs.add(("clue", clue.clue_id))
    for anchor in await repo.list_canon_time_anchors(_PROJECT):
        pairs.add(("time_anchor", anchor.anchor_id))
    return frozenset(pairs)


async def _accepted_snapshot() -> frozenset[int]:
    heads = await ChapterHeadRepository().list_by_project(_PROJECT)
    return frozenset(h.chapter_number for h in heads if h.accepted_version_id is not None)


async def _pending_counts() -> tuple[int, int]:
    repo = PlanFactRepository()
    return (
        len(await repo.list_pending_attributes(_PROJECT)),
        len(await repo.list_pending_entities(_PROJECT)),
    )


async def _pending_entity_ids() -> set[str]:
    repo = PlanFactRepository()
    return {e.entity_id for e in await repo.list_pending_entities(_PROJECT)}


async def _has_summary_row(chapter: int) -> bool:
    async with get_db() as conn:
        cursor = await conn.execute(
            "SELECT 1 FROM summaries WHERE project_id = ? AND chapter_number = ? LIMIT 1",
            (_PROJECT, chapter),
        )
        return await cursor.fetchone() is not None


async def _settlement_rows_for(version_id: str) -> int:
    async with get_db() as conn:
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM character_states WHERE source_version_id = ?",
            (version_id,),
        )
        row = await cursor.fetchone()
    return int(row[0]) if row else 0


async def _draft_content(chapter: int) -> str:
    head = await ChapterHeadRepository().get(_PROJECT, chapter)
    assert head is not None and head.current_version_id is not None
    version = await ChapterVersionRepository().get(head.current_version_id)
    assert version is not None
    content: str = version.content
    return content


def test_w2_loop_three_chapters(
    runner: CliRunner, loop_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """continue → accept ×3：settlement 自动补跑、approved 零变化、accepted 逐章 +1。"""
    mocks = _install_mocks(monkeypatch)
    approved_before = asyncio.run(_approved_snapshot())
    assert asyncio.run(_accepted_snapshot()) == frozenset()

    # --- 章 1：首章跳过 settlement ---
    result = _invoke_continue(runner)
    assert result.exit_code == 0, result.output
    assert asyncio.run(_draft_content(1)) == _BODY_1
    assert asyncio.run(_has_summary_row(1)) is False
    assert asyncio.run(_approved_snapshot()) == approved_before
    assert asyncio.run(_accepted_snapshot()) == frozenset()
    assert asyncio.run(_pending_counts()) == (0, 0)

    result = _invoke_accept(runner, 1)
    assert result.exit_code == 0, result.output
    assert asyncio.run(_accepted_snapshot()) == frozenset({1})
    assert asyncio.run(_approved_snapshot()) == approved_before

    # --- 章 2：continue 前 settlement 补跑章 1 ---
    result = _invoke_continue(runner)
    assert result.exit_code == 0, result.output
    assert asyncio.run(_draft_content(2)) == _BODY_2
    assert asyncio.run(_has_summary_row(1)) is True
    head_1 = asyncio.run(ChapterHeadRepository().get(_PROJECT, 1))
    assert head_1 is not None
    assert head_1.accepted_version_id is not None
    assert asyncio.run(_settlement_rows_for(head_1.accepted_version_id)) >= 1
    # settlement 只产 pending 提案；approved 集不变。
    pending_attrs, pending_entities = asyncio.run(_pending_counts())
    assert pending_attrs >= 1
    assert pending_entities >= 1
    # pending 提案指向种子角色（非空转断言）
    pending_entity_ids = asyncio.run(_pending_entity_ids())
    assert "char-s1" in pending_entity_ids
    assert asyncio.run(_approved_snapshot()) == approved_before
    assert asyncio.run(_accepted_snapshot()) == frozenset({1})

    result = _invoke_accept(runner, 2)
    assert result.exit_code == 0, result.output
    assert asyncio.run(_accepted_snapshot()) == frozenset({1, 2})
    assert asyncio.run(_approved_snapshot()) == approved_before

    # --- 章 3：continue 前 settlement 补跑章 2 ---
    result = _invoke_continue(runner)
    assert result.exit_code == 0, result.output
    assert asyncio.run(_draft_content(3)) == _BODY_3
    assert asyncio.run(_has_summary_row(2)) is True
    head_2 = asyncio.run(ChapterHeadRepository().get(_PROJECT, 2))
    assert head_2 is not None
    assert head_2.accepted_version_id is not None
    assert asyncio.run(_settlement_rows_for(head_2.accepted_version_id)) >= 1
    assert asyncio.run(_approved_snapshot()) == approved_before
    assert asyncio.run(_accepted_snapshot()) == frozenset({1, 2})

    result = _invoke_accept(runner, 3)
    assert result.exit_code == 0, result.output
    assert asyncio.run(_accepted_snapshot()) == frozenset({1, 2, 3})
    assert asyncio.run(_approved_snapshot()) == approved_before

    # 调用面：writer ×3；settlement / summary 各 ×2（首章无上一章可结算）。
    assert mocks["writer"].await_count == 3
    assert mocks["settlement"].await_count == 2
    assert mocks["summary"].await_count == 2


def test_w2_loop_pick_then_accept_does_not_block_continue(
    runner: CliRunner, loop_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """抽卡路 pick→accept 后 continue 下一章照常生成（冒烟发现 5 回归锁）。

    M3 pick 只改 head 工作指针、variant 行残留 picked；accept（B2/B5）不动
    variant 行。tech-m4 B1：picked 稿进入可续写态唯一路径 = chapter accept，
    故 accepted 章的残留 picked 槽不得阻塞后续章（task 244）。
    """
    from songyan.services.variant_generate import SlotDraft

    writer = AsyncMock(side_effect=[_BODY_1, _BODY_3])
    monkeypatch.setattr("songyan.agents.writer.call_llm", writer)
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
        AsyncMock(return_value=SlotDraft(content=_BODY_2, cost_cny_estimate=0.01)),
    )

    # ch1：continue 单稿 → accept
    assert _invoke_continue(runner).exit_code == 0
    assert _invoke_accept(runner, 1).exit_code == 0

    # ch2：抽卡 generate → pick → accept（残留 picked 槽）
    result = runner.invoke(
        cli, ["variant", "generate", "--project-id", _PROJECT, "--chapter", "2", "--n", "1"]
    )
    assert result.exit_code == 0, result.output
    result = runner.invoke(
        cli, ["variant", "pick", "--project-id", _PROJECT, "--chapter", "2", "--slot", "1"]
    )
    assert result.exit_code == 0, result.output
    result = _invoke_accept(runner, 2)
    assert result.exit_code == 0, result.output
    head_2 = asyncio.run(ChapterHeadRepository().get(_PROJECT, 2))
    assert head_2 is not None and head_2.accepted_version_id is not None

    # ch3：continue 应照常生成（修复前此处 B1 前置① exit 2 死锁）
    result = _invoke_continue(runner)
    assert result.exit_code == 0, result.output
    assert asyncio.run(_draft_content(3)) == _BODY_3
    assert writer.await_count == 2
