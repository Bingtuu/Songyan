"""Settlement DB 应用 — 将验证通过的结算写入数据库."""

from __future__ import annotations

import asyncio
import sqlite3
import uuid
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    import aiosqlite

import structlog

from songyan.db.continuity_repo import (
    InventoryTrackerRepository,
    LocationTrackerRepository,
    SettingTrackingRepository,
)
from songyan.db.layered_context_repo import PermanentSceneRepository
from songyan.db.repository import CharacterRepository
from songyan.db.settlement_repo import (
    ForeshadowingRepository,
    NumericalLedgerRepository,
    SettingSnapshotRepository,
)
from songyan.exceptions import SettlementError
from songyan.models import (
    CharacterState,
    ForeshadowingItem,
    NewSetting,
    PermanentScene,
    StateSettlement,
)

from ._setting_quality import (
    _archive_previous_setting_version,
    _normalize_setting_key,
)
from ._state_compression import compress_character_state_value

logger = structlog.get_logger(__name__)

_T = TypeVar("_T")


async def _execute_with_db_retry(
    func: Callable[..., Awaitable[_T]],
    *args: Any,
    max_retries: int = 3,
    backoff_ms: float = 100,
    **kwargs: Any,
) -> _T:
    """执行异步函数，捕获 SQLite busy/locked 时指数退避重试.

    仅对 ``sqlite3.OperationalError`` 中 message 包含 ``locked`` 或
    ``busy`` 的异常进行重试，其余异常直接抛出。
    """
    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except sqlite3.OperationalError as exc:
            err_msg = str(exc).lower()
            if "locked" not in err_msg and "busy" not in err_msg:
                raise
            if attempt >= max_retries:
                raise
            wait_ms = backoff_ms * (2 ** attempt)
            logger.warning(
                "settlement.db_retry",
                attempt=attempt + 1,
                max_retries=max_retries,
                wait_ms=wait_ms,
                error=str(exc),
            )
            await asyncio.sleep(wait_ms / 1000)
    raise RuntimeError("Unexpected exit from retry loop")


async def apply_settlement(
    settlement: StateSettlement,
    project_id: str,
    chapter_number: int,
    version_id: str,
    conn: aiosqlite.Connection,
    char_repo: CharacterRepository | None = None,
    setting_repo: SettingSnapshotRepository | None = None,
    foreshadowing_repo: ForeshadowingRepository | None = None,
    numerical_repo: NumericalLedgerRepository | None = None,
) -> None:
    """将验证通过的结算结果应用到数据库 — INSERT 新快照，不 UPDATE 旧记录.

    所有写入操作绑定到传入的 ``conn``，由调用方管理事务生命周期
    （BEGIN / COMMIT / ROLLBACK）。满足规则 53（Agent 不直接拿
    DB connection）和规则 56（settlement 写入使用事务）。

    Args:
        settlement: 验证通过的 StateSettlement
        project_id: 项目 ID
        chapter_number: 章节号
        version_id: 关联版本 ID
        conn: 数据库连接；由调用方创建并管理事务。
    """
    if settlement.validation_status != "valid":
        logger.warning(
            "settlement.apply_blocked_invalid",
            project_id=project_id,
            chapter_number=chapter_number,
            version_id=version_id,
            validation_status=settlement.validation_status,
            validation_errors=settlement.validation_errors,
        )
        raise SettlementError(
            f"Refusing to apply invalid settlement: {settlement.validation_status}"
        )

    if char_repo is None:
        char_repo = CharacterRepository()
    if setting_repo is None:
        setting_repo = SettingSnapshotRepository()
    if foreshadowing_repo is None:
        foreshadowing_repo = ForeshadowingRepository()
    if numerical_repo is None:
        numerical_repo = NumericalLedgerRepository()

    # 预加载项目角色白名单（LLM 可能 hallucinate 不存在的角色）
    project_characters = await char_repo.list_by_project(project_id)
    valid_char_ids = {c.character_id for c in project_characters}
    role_type_by_id = {c.character_id: c.role_type for c in project_characters}

    # Continuity tracking repositories
    setting_tracking_repo = SettingTrackingRepository()
    inventory_repo = InventoryTrackerRepository()
    location_repo = LocationTrackerRepository()

    async def _apply_core(
        c: aiosqlite.Connection,
    ) -> None:
        """核心写入逻辑（与连接来源无关）."""
        # 1. 角色状态变更 — INSERT 新快照
        for update in settlement.character_updates:
            if update.character_id not in valid_char_ids:
                logger.warning(
                    "settlement.character_id_not_found",
                    character_id=update.character_id,
                    project_id=project_id,
                    action="skip",
                )
                continue

            # Task 110a: 按角色层级保真压缩状态值
            role_type = role_type_by_id.get(update.character_id, "supporting")
            compressed_value = compress_character_state_value(
                update.new_value, update.field, role_type
            )

            state = CharacterState(
                character_id=update.character_id,
                field=update.field,
                value=compressed_value,
                source_version_id=version_id,
            )
            await char_repo.add_state_snapshot(state, conn=c)
            logger.info(
                "settlement.character_state_inserted",
                character_id=update.character_id,
                field=update.field,
                value=update.new_value,
            )

        # 2. 新设定登记 — INSERT
        for setting in settlement.new_settings:
            # Task 110b: 规范化 setting_key，无法生成合规 key 则跳过
            normalized_key = _normalize_setting_key(
                setting.setting_key, setting.setting_name
            )
            if normalized_key is None:
                continue
            setting.setting_key = normalized_key

            # Task 110b: 同一 setting_key 的旧版本自动归档
            await _archive_previous_setting_version(
                project_id=project_id,
                setting_key=normalized_key,
                setting_repo=setting_repo,
                conn=c,
            )

            setting_id = f"set-{project_id}-{uuid.uuid4().hex[:8]}"
            await setting_repo.create(setting, project_id, setting_id, conn=c)
            logger.info(
                "settlement.setting_inserted",
                setting_id=setting_id,
                setting_name=setting.setting_name,
                setting_key=normalized_key,
            )

        # 3. 伏笔操作 — plant 时 INSERT，resolve 时 UPDATE
        for fs in settlement.foreshadowing_updates:
            if fs.operation == "plant":
                fs_id = fs.foreshadowing_id or f"fs-{project_id}-{uuid.uuid4().hex[:8]}"
                item = ForeshadowingItem(
                    foreshadowing_id=fs_id,
                    description=fs.description,
                    planted_in_chapter=chapter_number,
                    expected_resolve_chapter=fs.expected_resolve_chapter,
                    status="planted",
                )
                await foreshadowing_repo.create(item, project_id, version_id, conn=c)
                logger.info("settlement.foreshadowing_planted", foreshadowing_id=fs_id)
            elif fs.operation == "resolve" and fs.foreshadowing_id:
                await foreshadowing_repo.update_status(
                    fs.foreshadowing_id, "resolved", conn=c
                )
                logger.info(
                    "settlement.foreshadowing_resolved",
                    foreshadowing_id=fs.foreshadowing_id,
                )

        # 4. 数值变更 — INSERT
        for num in settlement.numerical_updates:
            if num.character_id not in valid_char_ids:
                logger.warning(
                    "settlement.character_id_not_found",
                    character_id=num.character_id,
                    project_id=project_id,
                    action="skip_numerical",
                )
                continue
            ledger_id = f"num-{project_id}-{chapter_number}-{uuid.uuid4().hex[:8]}"
            await numerical_repo.create(num, project_id, chapter_number, ledger_id, conn=c)
            logger.info(
                "settlement.numerical_inserted",
                ledger_id=ledger_id,
                character_id=num.character_id,
                attribute=num.attribute_name,
            )

    # 核心写入（同一连接，调用方管理事务）
    try:
        await _apply_core(conn)
        logger.info("settlement.applied", project_id=project_id, chapter_number=chapter_number)
    except (RuntimeError, OSError, ConnectionError, ValueError, TypeError):
        logger.error(
            "settlement.failed",
            project_id=project_id,
            chapter_number=chapter_number,
            exc_info=True,
        )
        raise

    # Task 110: Foreshadowing pressure tracking
    try:
        await foreshadowing_repo.mark_overdue(project_id, chapter_number, conn=conn)
        ratio = await foreshadowing_repo.get_unresolved_ratio(
            project_id, chapter_number, conn=conn
        )
        if ratio > 0.30:
            settlement.foreshadowing_pressure = "high"
        elif ratio > 0.20:
            settlement.foreshadowing_pressure = "medium"
        else:
            settlement.foreshadowing_pressure = "low"
        logger.info(
            "settlement.foreshadowing_pressure",
            project_id=project_id,
            chapter_number=chapter_number,
            ratio=round(ratio, 3),
            pressure=settlement.foreshadowing_pressure,
        )
    except (RuntimeError, OSError, ConnectionError, ValueError, TypeError) as exc:
        logger.warning(
            "settlement.foreshadowing_pressure_failed",
            project_id=project_id,
            chapter_number=chapter_number,
            error=str(exc),
        )

    # 5+6. Continuity tracking + Permanent scenes（同一连接，调用方管理事务）
    try:
        await _update_continuity_tracking(
            settlement=settlement,
            project_id=project_id,
            chapter_number=chapter_number,
            version_id=version_id,
            setting_tracking_repo=setting_tracking_repo,
            inventory_repo=inventory_repo,
            location_repo=location_repo,
            foreshadowing_repo=foreshadowing_repo,
            conn=conn,
        )
        await _save_permanent_scenes(
            settlement=settlement,
            project_id=project_id,
            chapter_number=chapter_number,
            version_id=version_id,
            conn=conn,
        )
        logger.info(
            "settlement.continuity_tracking_applied",
            project_id=project_id,
            chapter_number=chapter_number,
        )
    except (RuntimeError, OSError, ConnectionError, ValueError, TypeError) as exc:
        logger.warning(
            "settlement.continuity_tracking_failed",
            project_id=project_id,
            chapter_number=chapter_number,
            error=str(exc),
        )


def _infer_setting_category(setting: NewSetting) -> str:
    """Task 094: 根据 setting 内容推断分类."""
    text = f"{setting.setting_key} {setting.setting_name} {setting.description}".lower()

    technical_keywords = [
        "型号", "参数", "引擎", "协议", "版本", "system", "model",
        "规格", "配置", "功率", "频率", "波长", "速率", "接口",
        "带宽", "电压", "容量", "速度", "精度",
    ]
    if any(kw in text for kw in technical_keywords):
        return "technical"

    critical_keywords = [
        "主角", "核心", "能力", "锚", "法则", "本源", "命格",
        "天赋", "血脉", "传承", "main", "protagonist", "core", "anchor",
    ]
    if any(kw in text for kw in critical_keywords):
        return "critical"

    historical_keywords = [
        "历史", "过去", "年代", "纪元", "古代", "上古", "曾经",
        "history", "past", "era", "ancient",
    ]
    if any(kw in text for kw in historical_keywords):
        return "historical"

    return "background"


async def _update_continuity_tracking(
    settlement: StateSettlement,
    project_id: str,
    chapter_number: int,
    version_id: str,
    setting_tracking_repo: SettingTrackingRepository,
    inventory_repo: InventoryTrackerRepository,
    location_repo: LocationTrackerRepository,
    foreshadowing_repo: ForeshadowingRepository,
    conn: aiosqlite.Connection | None = None,
) -> None:
    """更新连续性追踪表 — 失败不阻塞主流程.

    当传入 conn 时，所有写操作在同一个连接中执行（减少 WAL 锁竞争）。
    """
    # 5.1 Setting tracking
    existing_settings = await setting_tracking_repo.list_by_project(project_id)
    existing_keys = {s["setting_key"]: s for s in existing_settings}

    for setting in settlement.new_settings:
        key = setting.setting_key or setting.setting_name
        if key in existing_keys:
            await setting_tracking_repo.update_last_mentioned(
                existing_keys[key]["tracking_id"], chapter_number, conn=conn
            )
        else:
            tracking_id = f"track-{project_id}-{uuid.uuid4().hex[:8]}"
            category = _infer_setting_category(setting)
            await setting_tracking_repo.create(
                tracking_id=tracking_id,
                project_id=project_id,
                setting_key=key,
                setting_name=setting.setting_name,
                description=setting.description,
                introduced_in_chapter=chapter_number,
                source_version_id=version_id,
                category=category,
                conn=conn,
            )

    # 5.2 Inventory / Location tracking（轻量级：从 character_updates 推断）
    for update in settlement.character_updates:
        field_lower = update.field.lower()
        if "inventory" in field_lower or "物品" in field_lower or "道具" in field_lower:
            track_id = f"inv-{project_id}-{uuid.uuid4().hex[:8]}"
            await inventory_repo.create(
                track_id=track_id,
                project_id=project_id,
                character_id=update.character_id,
                item_name=update.new_value[:50],
                item_description=f"From field '{update.field}'",
                acquired_in_chapter=chapter_number,
                conn=conn,
            )
        elif "location" in field_lower or "位置" in field_lower:
            track_id = f"loc-{project_id}-{uuid.uuid4().hex[:8]}"
            await location_repo.create(
                track_id=track_id,
                project_id=project_id,
                character_id=update.character_id,
                location=update.new_value,
                entered_in_chapter=chapter_number,
                conn=conn,
            )

    # 5.3 Foreshadowing status auto-update (planted -> due -> overdue)
    active = await foreshadowing_repo.list_active(project_id)
    for fs in active:
        expected = fs.expected_resolve_chapter
        if expected is None:
            continue
        if chapter_number >= expected:
            await foreshadowing_repo.update_status(fs.foreshadowing_id, "overdue", conn=conn)
        elif chapter_number >= expected - 1:
            await foreshadowing_repo.update_status(fs.foreshadowing_id, "due", conn=conn)


_UPHEAVAL_KEYWORDS = ["颠覆", "改变", "真相", "revelation", "世界观", "秘密"]
_DEATH_INJURY_KEYWORDS = ["死亡", "重伤", "残废", "濒死", "牺牲", "陨落"]
_MYSTERY_KEYWORDS = ["秘密", "未知", "谜团", "真相", "尚未", "隐藏", "幕后"]


async def _save_permanent_scenes(
    settlement: StateSettlement,
    project_id: str,
    chapter_number: int,
    version_id: str,
    conn: aiosqlite.Connection | None = None,
) -> None:
    """保存高影响力章节为永久场景（impact_score ≥ 0.6）."""
    if settlement.impact_score < 0.6:
        return

    repo = PermanentSceneRepository()
    scene_id = f"perm-{project_id}-{chapter_number}"

    # 从 settlement 推断 impact_tags
    tags: list[str] = []
    for s in settlement.new_settings:
        if any(kw in s.description for kw in _UPHEAVAL_KEYWORDS):
            tags.append("世界观颠覆")
    for cu in settlement.character_updates:
        if any(kw in cu.new_value for kw in _DEATH_INJURY_KEYWORDS):
            tags.append("角色死亡/重伤")
    if settlement.new_settings:
        tags.append("新设定首次出现")
    if not tags:
        tags.append("高影响力事件")

    scene = PermanentScene(
        scene_id=scene_id,
        chapter_number=chapter_number,
        scene_number=1,
        excerpt="",  # 简化：excerpt 为空，后续可从 version.content 提取
        impact_tags=tags,
    )
    await repo.create(scene, project_id, conn=conn)
    logger.info(
        "settlement.permanent_scene_saved",
        scene_id=scene_id,
        project_id=project_id,
        chapter_number=chapter_number,
        impact_score=settlement.impact_score,
        tags=tags,
    )
