"""task 266：角色/设定人编辑服务（character / setting，与 storyline 编辑同形）。

直写 + 审计（profile_edit_history，同事务）。软删即隐藏：默认 list 与所有
组装出口（load_characters / 角色名册 / 初始化去重）都不含 archived 行。

边界（与 storyline review-C1 一致，记录在案）：edit 查找基于含软删快照，
命中已软删行 = 复活（character archived=False / setting lifecycle 回 active）。
"""

from __future__ import annotations

import structlog

from songyan.db.connection import get_db
from songyan.db.profile_edit_repo import ProfileEditHistoryRepository
from songyan.db.repository import CharacterRepository
from songyan.db.settlement_repo import SettingSnapshotRepository
from songyan.exceptions import SongyanError
from songyan.models.character import Character

logger = structlog.get_logger(__name__)


class ProfileEditError(SongyanError):
    """角色/设定编辑业务拒绝（CLI 映射 exit 2）。"""

    exit_code = 2


ROLE_TYPES = ("protagonist", "supporting", "antagonist")


async def list_characters(
    project_id: str, include_archived: bool = False
) -> list[Character]:
    return await CharacterRepository().list_by_project(
        project_id, include_archived=include_archived
    )


async def edit_character(
    project_id: str,
    character_id: str,
    *,
    name: str | None = None,
    role_type: str | None = None,
    background: str | None = None,
    traits: list[str] | None = None,
    goals: list[str] | None = None,
) -> str:
    """更新角色档案（未传字段保持原值）；审计同事务；命中软删行 = 复活。"""
    repo = CharacterRepository()
    snapshot = await repo.list_by_project(project_id, include_archived=True)
    before = next((c for c in snapshot if c.character_id == character_id), None)
    if before is None:
        raise ProfileEditError(f"角色不存在：{character_id}")
    merged = before.model_copy(
        update={
            "name": name if name is not None else before.name,
            "role_type": role_type if role_type is not None else before.role_type,
            "background": background if background is not None else before.background,
            "personality_traits": traits
            if traits is not None
            else before.personality_traits,
            "goals": goals if goals is not None else before.goals,
            "archived": False,
        }
    )
    if merged.role_type not in ROLE_TYPES:
        raise ProfileEditError(
            f"role_type 非法：{merged.role_type}（允许 {list(ROLE_TYPES)}）"
        )
    async with get_db() as conn:
        await repo.update_profile(merged, conn=conn)
        await ProfileEditHistoryRepository().record_history(
            project_id=project_id,
            target_type="character",
            target_id=character_id,
            action="update",
            before=before,
            after=merged,
            conn=conn,
        )
        await conn.commit()
    logger.info(
        "profile.edit.character",
        project_id=project_id,
        character_id=character_id,
    )
    return "update"


async def remove_character(project_id: str, character_id: str) -> str:
    """软删角色（archived=1）；幂等——已软删返回 'noop' 不写审计；主角拒绝。"""
    repo = CharacterRepository()
    snapshot = await repo.list_by_project(project_id, include_archived=True)
    before = next((c for c in snapshot if c.character_id == character_id), None)
    if before is None:
        raise ProfileEditError(f"角色不存在：{character_id}")
    if before.archived:
        return "noop"
    if before.role_type == "protagonist":
        raise ProfileEditError("主角不能 remove，请用 edit 修改（或先转移主角身份）")
    after = before.model_copy(update={"archived": True})
    async with get_db() as conn:
        await repo.set_archived(character_id, True, conn=conn)
        await ProfileEditHistoryRepository().record_history(
            project_id=project_id,
            target_type="character",
            target_id=character_id,
            action="remove",
            before=before,
            after=after,
            conn=conn,
        )
        await conn.commit()
    logger.info(
        "profile.remove.character",
        project_id=project_id,
        character_id=character_id,
    )
    return "remove"


async def list_settings(
    project_id: str, include_archived: bool = False
) -> list[dict[str, object]]:
    """编辑面设定列表（含 setting_id / lifecycle_status；默认排除 archived）。"""
    return await SettingSnapshotRepository().list_rows(
        project_id, include_archived=include_archived
    )


async def edit_setting(
    project_id: str,
    setting_id: str,
    *,
    name: str | None = None,
    description: str | None = None,
) -> str:
    """更新设定 name/description；命中 archived 行 = 复活回 active。"""
    repo = SettingSnapshotRepository()
    before = await repo.get_row(setting_id)
    if before is None or before["project_id"] != project_id:
        raise ProfileEditError(f"设定不存在：{setting_id}")
    merged = dict(before)
    if name is not None:
        merged["setting_name"] = name
    if description is not None:
        merged["description"] = description
    if before["lifecycle_status"] == "archived":
        merged["lifecycle_status"] = "active"
    async with get_db() as conn:
        await repo.update_fields(
            setting_id, setting_name=name, description=description, conn=conn
        )
        if before["lifecycle_status"] == "archived":
            await repo.set_lifecycle_status(setting_id, "active", conn=conn)
        await ProfileEditHistoryRepository().record_history(
            project_id=project_id,
            target_type="setting",
            target_id=setting_id,
            action="update",
            before=before,
            after=merged,
            conn=conn,
        )
        await conn.commit()
    logger.info(
        "profile.edit.setting",
        project_id=project_id,
        setting_id=setting_id,
    )
    return "update"


async def remove_setting(project_id: str, setting_id: str) -> str:
    """软删设定（lifecycle_status='archived'，复用既有列）；幂等同 character。"""
    repo = SettingSnapshotRepository()
    before = await repo.get_row(setting_id)
    if before is None or before["project_id"] != project_id:
        raise ProfileEditError(f"设定不存在：{setting_id}")
    if before["lifecycle_status"] == "archived":
        return "noop"
    after = dict(before)
    after["lifecycle_status"] = "archived"
    async with get_db() as conn:
        await repo.set_lifecycle_status(setting_id, "archived", conn=conn)
        await ProfileEditHistoryRepository().record_history(
            project_id=project_id,
            target_type="setting",
            target_id=setting_id,
            action="remove",
            before=before,
            after=after,
            conn=conn,
        )
        await conn.commit()
    logger.info(
        "profile.remove.setting",
        project_id=project_id,
        setting_id=setting_id,
    )
    return "remove"
