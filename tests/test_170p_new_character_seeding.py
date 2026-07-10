"""Task 170p: new_characters seeding — 修复 seeding gap.

覆盖：
- _build_new_character 解析
- _build_state_settlement 装配 new_characters
- _filter_new_characters 证据门禁（代词/不在正文/已存在/去重/长度）
- _validate_settlement 调用门禁后就地剔除不合格条目
"""

from __future__ import annotations

import pytest

from songyan.agents.settlement_extractor import (
    _build_new_character,
    _build_state_settlement,
)
from songyan.agents.settlement_extractor._validate import (
    _filter_new_characters,
    _validate_settlement,
)
from songyan.models import NewCharacter, StateSettlement


class TestBuildNewCharacter:
    def test_parses_minimal_fields(self) -> None:
        nc = _build_new_character(
            {"name": "陈薇", "role_type": "supporting", "source_quote": "陈薇说"}
        )
        assert nc is not None
        assert nc.name == "陈薇"
        assert nc.role_type == "supporting"

    def test_empty_name_returns_none(self) -> None:
        assert _build_new_character({"name": "", "source_quote": "x"}) is None

    def test_invalid_role_type_defaults_supporting(self) -> None:
        nc = _build_new_character({"name": "韩墨", "role_type": "protagonist"})
        assert nc is not None
        assert nc.role_type == "supporting"

    def test_non_dict_returns_none(self) -> None:
        assert _build_new_character("陈薇") is None  # type: ignore[arg-type]


class TestBuildStateSettlementNewCharacters:
    def test_assembles_new_characters(self) -> None:
        data = {
            "new_characters": [
                {"name": "陈薇", "role_type": "supporting", "source_quote": "陈薇说"},
                {"name": "韩墨", "role_type": "antagonist", "source_quote": "韩墨说"},
            ]
        }
        settlement = _build_state_settlement(data)
        assert [c.name for c in settlement.new_characters] == ["陈薇", "韩墨"]

    def test_missing_field_defaults_empty(self) -> None:
        settlement = _build_state_settlement({})
        assert settlement.new_characters == []


class TestFilterNewCharacters:
    def _settlement(self, names_quotes: list[tuple[str, str]]) -> StateSettlement:
        return StateSettlement(
            new_characters=[
                NewCharacter(name=n, role_type="supporting", source_quote=q)
                for n, q in names_quotes
            ]
        )

    def test_accepts_valid_named_character(self) -> None:
        content = "陈薇的声音从通讯频道里传来：“别相信钥匙。”"
        s = self._settlement([("陈薇", "陈薇的声音从通讯频道里传来")])
        _filter_new_characters(s, content, set(), 30, "p1")
        assert [c.name for c in s.new_characters] == ["陈薇"]

    def test_filters_pronoun(self) -> None:
        content = "他握紧右臂。"
        s = self._settlement([("他", "他握紧右臂")])
        _filter_new_characters(s, content, set(), 30, "p1")
        assert s.new_characters == []

    def test_filters_name_not_in_content(self) -> None:
        content = "林渊握紧右臂。"
        s = self._settlement([("虚构者", "虚构者出现了")])
        _filter_new_characters(s, content, set(), 30, "p1")
        assert s.new_characters == []

    def test_filters_existing_character(self) -> None:
        content = "林渊握紧右臂。"
        s = self._settlement([("林渊", "林渊握紧右臂")])
        _filter_new_characters(s, content, {"林渊"}, 30, "p1")
        assert s.new_characters == []

    def test_filters_source_quote_not_in_content(self) -> None:
        content = "陈薇出现在核心舱。"
        s = self._settlement([("陈薇", "这句话根本不在正文里出现过的证据引文")])
        _filter_new_characters(s, content, set(), 30, "p1")
        assert s.new_characters == []

    def test_dedups_within_settlement(self) -> None:
        content = "韩墨说：“方舟必须锁死。”"
        s = self._settlement([("韩墨", "韩墨说"), ("韩墨", "韩墨说")])
        _filter_new_characters(s, content, set(), 31, "p1")
        assert [c.name for c in s.new_characters] == ["韩墨"]


@pytest.mark.asyncio
async def test_validate_settlement_applies_new_character_gate() -> None:
    content = "陈薇的声音传来：“别相信钥匙。”老雷没有回答。"
    settlement = StateSettlement(
        new_characters=[
            NewCharacter(name="陈薇", role_type="supporting", source_quote="陈薇的声音传来"),
            NewCharacter(name="他", role_type="supporting", source_quote="他握紧右臂"),
            NewCharacter(name="林渊", role_type="supporting", source_quote="林渊"),
        ]
    )
    errors = await _validate_settlement(
        settlement,
        content,
        current_states=[],
        current_settings=[],
        chapter_number=30,
        project_id="p1",
        existing_character_names={"林渊"},
    )
    # 门禁只做就地剔除，不阻断整章结算
    assert errors == []
    assert [c.name for c in settlement.new_characters] == ["陈薇"]


@pytest.mark.asyncio
async def test_apply_settlement_inserts_new_characters(test_db) -> None:
    """Task 170p: apply_settlement 幂等 INSERT 新配角，绑定事务，供后续章引用."""
    from songyan.agents.settlement_extractor import apply_settlement
    from songyan.db.connection import get_db
    from songyan.db.repository import CharacterRepository, ProjectRepository
    from songyan.models import Character, ProjectSetting

    project_id = "proj-170p"
    project = ProjectSetting(
        project_id=project_id,
        title="seeding gap test",
        genre_id="scifi",
        protagonist_name="林渊",
    )
    await ProjectRepository().create(project, project_id)
    await CharacterRepository().create(
        Character(
            character_id="char-lin",
            project_id=project_id,
            name="林渊",
            role_type="protagonist",
        )
    )

    content = "陈薇的声音传来：“别相信钥匙。”老雷没有回答。"
    settlement = StateSettlement(
        new_characters=[
            NewCharacter(name="陈薇", role_type="supporting", source_quote="陈薇的声音传来"),
            NewCharacter(name="老雷", role_type="supporting", source_quote="老雷没有回答"),
        ]
    )

    async with get_db() as conn:
        await apply_settlement(
            settlement,
            project_id,
            chapter_number=30,
            version_id="v-170p-30",
            conn=conn,
            content=content,
        )
        await conn.commit()

    chars = await CharacterRepository().list_by_project(project_id)
    names = {c.name for c in chars}
    assert names == {"林渊", "陈薇", "老雷"}
    # 配角 role_type 正确入库
    role_by_name = {c.name: c.role_type for c in chars}
    assert role_by_name["陈薇"] == "supporting"
    assert role_by_name["老雷"] == "supporting"


@pytest.mark.asyncio
async def test_apply_settlement_new_character_idempotent(test_db) -> None:
    """重复出现的同名配角不重复入库（幂等）."""
    from songyan.agents.settlement_extractor import apply_settlement
    from songyan.db.connection import get_db
    from songyan.db.repository import CharacterRepository, ProjectRepository
    from songyan.models import Character, ProjectSetting

    project_id = "proj-170p-idem"
    await ProjectRepository().create(
        ProjectSetting(
            project_id=project_id,
            title="idem test",
            genre_id="scifi",
            protagonist_name="林渊",
        ),
        project_id,
    )
    await CharacterRepository().create(
        Character(
            character_id="char-lin2",
            project_id=project_id,
            name="林渊",
            role_type="protagonist",
        )
    )

    content = "陈薇的声音传来：“别相信钥匙。”"
    for ch in (30, 31):
        settlement = StateSettlement(
            new_characters=[
                NewCharacter(name="陈薇", role_type="supporting", source_quote="陈薇的声音传来"),
            ]
        )
        async with get_db() as conn:
            await apply_settlement(
                settlement,
                project_id,
                chapter_number=ch,
                version_id=f"v-{ch}",
                conn=conn,
                content=content,
            )
            await conn.commit()

    chars = await CharacterRepository().list_by_project(project_id)
    chen = [c for c in chars if c.name == "陈薇"]
    assert len(chen) == 1, "同名配角应幂等，只入库一次"

