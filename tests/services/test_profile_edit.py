"""task 266：角色/设定人编辑写径服务（profile_edit）。

切片 1（character）：edit 改 name/role_type/background/traits/goals（审计同事务）；
remove 软删 archived（幂等 no-op；主角拒绝 exit 2；不存在 exit 2）；
软删行从默认 list 与组装出口（load_characters）消失，--include-archived 可见。
切片 2（setting）：edit 改 name/description；remove 置 lifecycle_status='archived'
（复用既有列，不另建）；同样幂等 / 审计 / 默认隐藏。
边界：edit 命中已软删行 = 复活（与 storyline review-C1 口径一致，记录在案）。
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from songyan.config import settings
from songyan.db.migrations import init_schema
from songyan.db.repository import CharacterRepository, ProjectRepository
from songyan.db.settlement_repo import SettingSnapshotRepository
from songyan.models.character import Character
from songyan.models.project import ProjectSetting
from songyan.services.profile_edit import (
    ProfileEditError,
    edit_character,
    edit_setting,
    list_characters,
    list_settings,
    remove_character,
    remove_setting,
)
from songyan.workflows._helpers import load_characters

_PROJECT = "p-profile"
_PROTAGONIST_ID = "char-protagonist"
_ANTAGONIST_ID = "char-zhou"
_SUPPORTING_ID = "char-lin"
_SETTING_ECHO = "set-echo"
_SETTING_DEBT = "set-debt"


@pytest.fixture
async def profile_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "profile.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="urban",
            mode_id="webnovel",
            protagonist_name="陈屿",
            title="profile edit",
        ),
        _PROJECT,
    )
    char_repo = CharacterRepository()
    await char_repo.create(
        Character(
            character_id=_PROTAGONIST_ID,
            project_id=_PROJECT,
            name="陈屿",
            role_type="protagonist",
            background="钟表店学徒",
        )
    )
    await char_repo.create(
        Character(
            character_id=_ANTAGONIST_ID,
            project_id=_PROJECT,
            name="周牧野",
            role_type="antagonist",
            background="追债人",
        )
    )
    await char_repo.create(
        Character(
            character_id=_SUPPORTING_ID,
            project_id=_PROJECT,
            name="林知遥",
            role_type="supporting",
            background="同事",
        )
    )
    set_repo = SettingSnapshotRepository()
    await set_repo.create(
        _setting("Echo", "店里的旧座钟", "echo-key"),
        _PROJECT,
        _SETTING_ECHO,
    )
    await set_repo.create(
        _setting("债务", "陈屿父亲的欠款", "debt-key"),
        _PROJECT,
        _SETTING_DEBT,
    )
    return db_path


def _setting(name: str, desc: str, key: str):
    from songyan.models.settlement import NewSetting

    return NewSetting(setting_name=name, description=desc, source_quote="", setting_key=key)


def _history(db_path: Path) -> list[tuple]:
    con = sqlite3.connect(db_path)
    rows = con.execute(
        "SELECT target_type, target_id, action, before_json, after_json "
        "FROM profile_edit_history ORDER BY rowid"
    ).fetchall()
    con.close()
    return rows


class TestCharacterEdit:
    async def test_edit_updates_fields_and_writes_audit(self, profile_db: Path) -> None:
        action = await edit_character(
            _PROJECT,
            _ANTAGONIST_ID,
            name="周德顺",
            role_type="supporting",
            background="改后的背景",
            traits=["沉默"],
            goals=["看店"],
        )
        assert action == "update"

        char = await CharacterRepository().get(_ANTAGONIST_ID)
        assert char is not None
        assert char.name == "周德顺"
        assert char.role_type == "supporting"
        assert char.background == "改后的背景"
        assert char.personality_traits == ["沉默"]
        assert char.goals == ["看店"]

        rows = _history(profile_db)
        assert len(rows) == 1
        target_type, target_id, action_name, before_json, after_json = rows[0]
        assert target_type == "character"
        assert target_id == _ANTAGONIST_ID
        assert action_name == "update"
        assert json.loads(before_json)["name"] == "周牧野"
        assert json.loads(after_json)["name"] == "周德顺"

    async def test_edit_not_found_raises_exit_2(self, profile_db: Path) -> None:
        with pytest.raises(ProfileEditError) as exc_info:
            await edit_character(_PROJECT, "char-missing", name=" nobody")
        assert exc_info.value.exit_code == 2
        assert _history(profile_db) == []

    async def test_edit_partial_fields_keep_others(self, profile_db: Path) -> None:
        await edit_character(_PROJECT, _SUPPORTING_ID, name="林小遥")
        char = await CharacterRepository().get(_SUPPORTING_ID)
        assert char is not None
        assert char.name == "林小遥"
        assert char.role_type == "supporting"

    async def test_edit_archived_row_revives(self, profile_db: Path) -> None:
        """边界（与 storyline 一致）：edit 命中已软删行 = 复活并更新。"""
        await remove_character(_PROJECT, _ANTAGONIST_ID)
        action = await edit_character(_PROJECT, _ANTAGONIST_ID, name="复活者")
        assert action == "update"
        chars = await list_characters(_PROJECT)
        assert any(c.character_id == _ANTAGONIST_ID for c in chars)


class TestCharacterRemove:
    async def test_remove_antagonist_archives_and_hides(self, profile_db: Path) -> None:
        action = await remove_character(_PROJECT, _ANTAGONIST_ID)
        assert action == "remove"

        chars = await list_characters(_PROJECT)
        assert _ANTAGONIST_ID not in {c.character_id for c in chars}
        all_chars = await list_characters(_PROJECT, include_archived=True)
        assert _ANTAGONIST_ID in {c.character_id for c in all_chars}

        # 组装出口同步隐藏
        loaded = await load_characters(_PROJECT)
        assert "周牧野" not in {c.name for c in loaded}

        rows = _history(profile_db)
        assert len(rows) == 1
        assert rows[0][2] == "remove"
        assert json.loads(rows[0][4])["archived"] is True

    async def test_remove_protagonist_rejected_without_write(self, profile_db: Path) -> None:
        with pytest.raises(ProfileEditError) as exc_info:
            await remove_character(_PROJECT, _PROTAGONIST_ID)
        assert exc_info.value.exit_code == 2
        char = await CharacterRepository().get(_PROTAGONIST_ID)
        assert char is not None
        assert char.archived is False
        assert _history(profile_db) == []

    async def test_remove_twice_is_noop_single_audit(self, profile_db: Path) -> None:
        assert await remove_character(_PROJECT, _SUPPORTING_ID) == "remove"
        assert await remove_character(_PROJECT, _SUPPORTING_ID) == "noop"
        assert len(_history(profile_db)) == 1

    async def test_remove_not_found_raises_exit_2(self, profile_db: Path) -> None:
        with pytest.raises(ProfileEditError) as exc_info:
            await remove_character(_PROJECT, "char-missing")
        assert exc_info.value.exit_code == 2


class TestSettingEdit:
    async def test_edit_updates_name_description_and_audits(self, profile_db: Path) -> None:
        action = await edit_setting(
            _PROJECT, _SETTING_ECHO, name="座钟", description="雨夜会慢五分钟"
        )
        assert action == "update"
        rows = await list_settings(_PROJECT, include_archived=True)
        echo = next(r for r in rows if r["setting_id"] == _SETTING_ECHO)
        assert echo["setting_name"] == "座钟"
        assert echo["description"] == "雨夜会慢五分钟"

        history = _history(profile_db)
        assert len(history) == 1
        assert history[0][0] == "setting"
        assert history[0][2] == "update"

    async def test_edit_not_found_raises_exit_2(self, profile_db: Path) -> None:
        with pytest.raises(ProfileEditError) as exc_info:
            await edit_setting(_PROJECT, "set-missing", name="x")
        assert exc_info.value.exit_code == 2


class TestSettingRemove:
    async def test_remove_archives_lifecycle_and_hides(self, profile_db: Path) -> None:
        action = await remove_setting(_PROJECT, _SETTING_ECHO)
        assert action == "remove"

        visible = await list_settings(_PROJECT)
        assert _SETTING_ECHO not in {r["setting_id"] for r in visible}
        # 另一条不受影响
        assert _SETTING_DEBT in {r["setting_id"] for r in visible}
        all_rows = await list_settings(_PROJECT, include_archived=True)
        echo = next(r for r in all_rows if r["setting_id"] == _SETTING_ECHO)
        assert echo["lifecycle_status"] == "archived"

        history = _history(profile_db)
        assert len(history) == 1
        assert history[0][2] == "remove"

    async def test_remove_twice_is_noop(self, profile_db: Path) -> None:
        assert await remove_setting(_PROJECT, _SETTING_DEBT) == "remove"
        assert await remove_setting(_PROJECT, _SETTING_DEBT) == "noop"
        assert len(_history(profile_db)) == 1

    async def test_remove_not_found_raises_exit_2(self, profile_db: Path) -> None:
        with pytest.raises(ProfileEditError) as exc_info:
            await remove_setting(_PROJECT, "set-missing")
        assert exc_info.value.exit_code == 2
