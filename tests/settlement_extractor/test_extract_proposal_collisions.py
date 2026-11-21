"""task 270: extract 提案 attribute_id 碰撞修复的锁测试。

碰撞向量（修复前全部静默覆盖，人在 canon pending 看不到被覆盖的提案）：
1. 同 settlement 同 (entity, key, chapter) 多次观测（章中多次变化）。
2. character_updates.field 与 numerical_updates.attribute_name 跨族同 key。
3. 非 ASCII key 经 _slug 塌缩成 "x"，同章不同 key 互覆。

同时锁：正常 ASCII 路径 ID 形态不变；同值重入幂等。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from songyan.agents.settlement_extractor._proposals import (
    _attribute_id,
    enqueue_extract_proposals,
)
from songyan.config import settings
from songyan.db.connection import get_db
from songyan.db.migrations import init_schema
from songyan.db.plan_fact_repo import PlanFactRepository
from songyan.db.repository import (
    CharacterRepository,
    ProjectRepository,
)
from songyan.models import (
    Character,
    CharacterUpdate,
    NumericalUpdate,
    ProjectSetting,
    StateSettlement,
)

_PROJECT_ID = "p-coll"
_CHAR_ID = "char-chen"


@pytest.fixture
async def coll_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "collisions.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="mystery",
            mode_id="webnovel",
            protagonist_name="陈照",
            title="collision fixture",
        ),
        _PROJECT_ID,
    )
    await CharacterRepository().create(
        Character(
            character_id=_CHAR_ID,
            project_id=_PROJECT_ID,
            name="陈照",
            role_type="protagonist",
        )
    )
    return db_path


async def _enqueue(coll_db: Path, settlement: StateSettlement, chapter: int) -> list[str]:
    async with get_db() as conn:
        written = await enqueue_extract_proposals(
            settlement, project_id=_PROJECT_ID, chapter_number=chapter, conn=conn
        )
        await conn.commit()
    return written


async def _pending_rows(key: str) -> list[tuple[str, str]]:
    pending = await PlanFactRepository().list_pending_attributes(_PROJECT_ID)
    return [
        (a.attribute_id, a.value)
        for a in pending
        if a.entity_id == _CHAR_ID and a.key == key
    ]


@pytest.mark.asyncio
async def test_same_key_same_chapter_two_values_both_visible(
    coll_db: Path,
) -> None:
    settlement = StateSettlement(
        validation_status="valid",
        character_updates=[
            CharacterUpdate(
                character_id=_CHAR_ID,
                field="location",
                old_value="霞飞路",
                new_value="外滩",
                source_quote="陈照走到了外滩",
            ),
            CharacterUpdate(
                character_id=_CHAR_ID,
                field="location",
                old_value="外滩",
                new_value="城隍庙",
                source_quote="陈照又去了城隍庙",
            ),
        ],
    )
    await _enqueue(coll_db, settlement, chapter=3)

    rows = await _pending_rows("location")
    values = sorted(value for _attr_id, value in rows)
    assert values == ["城隍庙", "外滩"]
    assert len({attr_id for attr_id, _value in rows}) == 2, "两条提案必须有独立 ID"


@pytest.mark.asyncio
async def test_same_key_same_value_reenqueue_is_idempotent(coll_db: Path) -> None:
    def settlement() -> StateSettlement:
        return StateSettlement(
            validation_status="valid",
            character_updates=[
                CharacterUpdate(
                    character_id=_CHAR_ID,
                    field="mood",
                    old_value="冷静",
                    new_value="愤怒",
                    source_quote="他怒了",
                ),
                CharacterUpdate(
                    character_id=_CHAR_ID,
                    field="mood",
                    old_value="冷静",
                    new_value="愤怒",
                    source_quote="他怒了",
                ),
            ],
        )

    written = await _enqueue(coll_db, settlement(), chapter=3)
    assert len(written) == 1, "同值重复观测不得在 written 里记两条"
    written_again = await _enqueue(coll_db, settlement(), chapter=3)
    assert written_again == written, "重跑结算必须幂等（同 ID）"

    rows = await _pending_rows("mood")
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_cross_family_same_key_not_clobbered(coll_db: Path) -> None:
    settlement = StateSettlement(
        validation_status="valid",
        character_updates=[
            CharacterUpdate(
                character_id=_CHAR_ID,
                field="level",
                old_value="三级警司",
                new_value="二级警司",
                source_quote="他升了职",
            )
        ],
        numerical_updates=[
            NumericalUpdate(
                character_id=_CHAR_ID,
                attribute_name="level",
                opening_value=3.0,
                closing_value=4.0,
                formula="opening + 1",
            )
        ],
    )
    await _enqueue(coll_db, settlement, chapter=4)

    rows = await _pending_rows("level")
    values = sorted(value for _attr_id, value in rows)
    assert values == ["4.0", "二级警司"]


@pytest.mark.asyncio
async def test_non_ascii_keys_do_not_slug_collapse(coll_db: Path) -> None:
    settlement = StateSettlement(
        validation_status="valid",
        character_updates=[
            CharacterUpdate(
                character_id=_CHAR_ID,
                field="体力",
                old_value="充沛",
                new_value="透支",
                source_quote="他喘不上气",
            ),
            CharacterUpdate(
                character_id=_CHAR_ID,
                field="灵力",
                old_value="十成",
                new_value="三成",
                source_quote="灵力见底",
            ),
        ],
    )
    await _enqueue(coll_db, settlement, chapter=5)

    rows = await _pending_rows("体力")
    assert [value for _a, value in rows] == ["透支"]
    rows = await _pending_rows("灵力")
    assert [value for _a, value in rows] == ["三成"]


@pytest.mark.asyncio
async def test_ascii_id_form_unchanged(coll_db: Path) -> None:
    settlement = StateSettlement(
        validation_status="valid",
        character_updates=[
            CharacterUpdate(
                character_id=_CHAR_ID,
                field="location",
                old_value="霞飞路",
                new_value="外滩",
                source_quote="陈照走到了外滩",
            )
        ],
    )
    written = await _enqueue(coll_db, settlement, chapter=3)

    assert written == ["ext-p-coll-char-chen-location-c3"]
    legacy = _attribute_id(
        project_id=_PROJECT_ID,
        entity_id=_CHAR_ID,
        key="location",
        chapter_number=3,
    )
    assert legacy == "ext-p-coll-char-chen-location-c3"
