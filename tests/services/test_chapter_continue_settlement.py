"""M4 步 3 切片 2: chapter continue 准备阶段 settlement（tech-m4 §5 步 3 / B5）。

复合判定（评审 M2）：上一章 accepted 且 summaries 无该章记录 且 结算观测层
（character_states.source_version_id = accepted_version_id）无行 → 重跑完整
settlement 序列（extract + apply + summaries 行）；两条件任一存在即跳过；首章跳过。
approved 集不变（settlement 只产 pending 提案，M2 语义）。
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from songyan.config import settings
from songyan.db.connection import get_db
from songyan.db.context_repo import SummaryRepository
from songyan.db.migrations import init_schema
from songyan.db.plan_fact_repo import PlanFactRepository
from songyan.db.repository import (
    ChapterHeadRepository,
    ChapterVersionRepository,
    CharacterRepository,
    ProjectRepository,
)
from songyan.models.chapter import ChapterHead, ChapterVersion
from songyan.models.character import Character, CharacterState
from songyan.models.context import ChapterSummary
from songyan.models.plan_facts import PlanAttribute, PlanEntity
from songyan.models.project import ProjectSetting
from songyan.models.settlement import CharacterUpdate, StateSettlement
from songyan.services.chapter_accept import accept_chapter
from songyan.services.chapter_continue import ContinueOutcome, continue_chapters
from songyan.utils.word_count import count_chinese_words

_PROJECT = "p-m4-cont-settle"
_ACCEPTED_CONTENT = "第一章正文：陈照到了北站，铜镜在口袋里发烫。"
_BODY = "第二章正文：陈照走进雨里，末班车进站。"
_SUMMARY_JSON = (
    '{"plot_summary": "陈照抵达北站。", "key_events": ["陈照到北站"], '
    '"characters_appeared": ["陈照"], "emotional_tone": "沉静"}'
)


@pytest.fixture
async def settle_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "m4-cont-settle.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="mystery_noir",
            mode_id="webnovel",
            protagonist_name="陈照",
            title="m4 continue settle",
        ),
        _PROJECT,
    )
    return db_path


def _install_mocks(monkeypatch: pytest.MonkeyPatch) -> dict[str, AsyncMock]:
    writer = AsyncMock(return_value=_BODY)
    monkeypatch.setattr("songyan.agents.writer.call_llm", writer)
    summary_llm = AsyncMock(return_value=_SUMMARY_JSON)
    monkeypatch.setattr("songyan.agents.summary_writer.call_llm", summary_llm)
    extract = AsyncMock(
        return_value=StateSettlement(
            character_updates=[
                CharacterUpdate(
                    character_id="char-s1",
                    field="location",
                    old_value="南站",
                    new_value="北站",
                    source_quote="陈照到了北站",
                )
            ],
            validation_status="valid",
        )
    )
    monkeypatch.setattr("songyan.services.chapter_continue.extract_settlement", extract)
    return {"writer": writer, "summary_llm": summary_llm, "extract": extract}


async def _seed_accepted_with_character() -> str:
    await CharacterRepository().create(
        Character(
            character_id="char-s1",
            project_id=_PROJECT,
            name="陈照",
            role_type="protagonist",
        )
    )
    version = ChapterVersion(
        version_id="v-settle-1-draft",
        project_id=_PROJECT,
        chapter_number=1,
        version_number=1,
        version_type="draft",
        content=_ACCEPTED_CONTENT,
        word_count=count_chinese_words(_ACCEPTED_CONTENT),
    )
    await ChapterVersionRepository().create(version)
    await ChapterHeadRepository().update(
        ChapterHead(
            project_id=_PROJECT,
            chapter_number=1,
            current_version_id=version.version_id,
            accepted_version_id=None,
            status="draft",
        )
    )
    outcome = await accept_chapter(_PROJECT, 1)
    # 让 ch2 进入章宇宙（目标章），否则全 accepted 直接返回 None。
    await ChapterHeadRepository().update(
        ChapterHead(
            project_id=_PROJECT,
            chapter_number=2,
            current_version_id=None,
            accepted_version_id=None,
            status="draft",
        )
    )
    return outcome.accepted_version_id


async def _seed_approved_canon() -> None:
    repo = PlanFactRepository()
    await repo.write_entity(
        PlanEntity(
            entity_id="ent-seed-1",
            project_id=_PROJECT,
            entity_type="person",
            aliases=["老周"],
            approval_status="approved",
        )
    )
    await repo.write_attribute(
        PlanAttribute(
            attribute_id="attr-seed-1",
            project_id=_PROJECT,
            entity_id="ent-seed-1",
            key="location",
            value="南站",
            source="plan",
            approval_status="approved",
            valid_from_ch=1,
            valid_to_ch=5,
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
            "SELECT COUNT(*) FROM character_states WHERE source_version_id = ?", (version_id,)
        )
        row = await cursor.fetchone()
    return int(row[0]) if row else 0


async def test_full_settlement_sequence_on_accepted_previous(
    settle_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """无 summary 且无结算行 → 完整序列：结算行 + summaries 行 + pending 提案。"""
    await _seed_approved_canon()
    accepted_id = await _seed_accepted_with_character()
    before = await _approved_snapshot()
    mocks = _install_mocks(monkeypatch)
    notices: list[str] = []

    outcome = await continue_chapters(
        _PROJECT, notice=lambda m: notices.append(m)
    )
    assert isinstance(outcome, ContinueOutcome)
    assert outcome.chapter_number == 2
    assert outcome.settled_previous is True

    extract: AsyncMock = mocks["extract"]
    extract.assert_awaited_once()
    _, kwargs = extract.await_args
    assert kwargs["version_id"] == accepted_id
    assert kwargs["chapter_number"] == 1
    assert "北站" in kwargs["content"]

    # 结算观测层新行（source_version_id = accepted 版本）。
    assert await _settlement_rows_for(accepted_id) == 1
    # summaries 新行。
    assert await _has_summary_row(1) is True
    # plan_* pending 提案（M2 语义），approved 集不变。
    repo = PlanFactRepository()
    assert await repo.list_pending_attributes(_PROJECT)
    assert await repo.list_pending_entities(_PROJECT)
    assert await _approved_snapshot() == before
    # 重跑前 stderr 提示。
    assert any("settlement" in m for m in notices)


async def test_skip_when_summary_exists(
    settle_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    accepted_id = await _seed_accepted_with_character()
    await SummaryRepository().create(
        ChapterSummary(chapter_number=1, summary="已有摘要"),
        _PROJECT,
        "sum-existing",
    )
    mocks = _install_mocks(monkeypatch)

    outcome = await continue_chapters(_PROJECT)
    assert outcome is not None
    assert outcome.settled_previous is False
    mocks["extract"].assert_not_awaited()
    assert await _settlement_rows_for(accepted_id) == 0


async def test_skip_when_settlement_row_without_summary(
    settle_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """有结算行无 summary（replay 遗留）→ 复合判定跳过（评审 M2）。"""
    accepted_id = await _seed_accepted_with_character()
    await CharacterRepository().add_state_snapshot(
        CharacterState(
            character_id="char-s1",
            field="location",
            value="北站",
            source_version_id=accepted_id,
        )
    )
    mocks = _install_mocks(monkeypatch)

    outcome = await continue_chapters(_PROJECT)
    assert outcome is not None
    assert outcome.settled_previous is False
    mocks["extract"].assert_not_awaited()
    assert await _has_summary_row(1) is False


async def test_first_chapter_skips_settlement(
    settle_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """首章（无上一章）跳过 settlement；ch1 需存在于章宇宙（空 head）。"""
    await ChapterHeadRepository().update(
        ChapterHead(
            project_id=_PROJECT,
            chapter_number=1,
            current_version_id=None,
            accepted_version_id=None,
            status="draft",
        )
    )
    mocks = _install_mocks(monkeypatch)
    outcome = await continue_chapters(_PROJECT)
    assert outcome is not None
    assert outcome.chapter_number == 1
    assert outcome.settled_previous is False
    mocks["extract"].assert_not_awaited()


async def test_settlement_llm_failure_raises(
    settle_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """settlement 阶段 LLM 失败 → ContinueSettlementError（CLI 层 exit 1）。"""
    from songyan.exceptions import LLMError

    await _seed_accepted_with_character()
    _install_mocks(monkeypatch)
    failing = AsyncMock(side_effect=LLMError("settlement boom"))
    monkeypatch.setattr("songyan.services.chapter_continue.extract_settlement", failing)

    from songyan.services.chapter_continue import ContinueSettlementError

    with pytest.raises(ContinueSettlementError):
        await continue_chapters(_PROJECT)
