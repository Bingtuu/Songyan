"""Settlement DB 应用 — 将验证通过的结算写入数据库."""

from __future__ import annotations

import asyncio
import re
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
from songyan.db.human_mark_repo import HumanMarkRepository
from songyan.db.layered_context_repo import PermanentSceneRepository
from songyan.db.repository import CharacterRepository, ProjectRepository
from songyan.db.settlement_repo import (
    ForeshadowingRepository,
    NumericalLedgerRepository,
    SettingSnapshotRepository,
)
from songyan.exceptions import SettlementError
from songyan.models import (
    Character,
    CharacterState,
    ForeshadowingItem,
    NewSetting,
    PermanentScene,
    ProjectSetting,
    StateSettlement,
)

from ._setting_quality import (
    _archive_previous_setting_version,
    _normalize_setting_key,
)
from ._state_compression import compress_character_state_value

logger = structlog.get_logger(__name__)

_T = TypeVar("_T")

_SETTING_REFERENCE_BOUNDARY_CHARS = set(
    "的了着过在为是被将把从到向对于由以"
    "中上下里内外前后间处和与及或并、，。；：！？,.!?;:()（）[]【】"
    "\"'“”‘’ \t\r\n"
)
_SETTING_REFERENCE_SPLIT_RE = re.compile(
    r"[·—\-_/（）()\[\]【】,，、;；:.：\s]+|"
    r"[的了着过在为是被将把从到向对于由以中上下里内外前后间处和与及或并]"
)
_LOW_INFO_REFERENCE_TOKENS = {
    "这个",
    "那个",
    "一种",
    "不是",
    "没有",
    "已经",
    "正在",
    "开始",
    "继续",
    "系统",
    "结构",
    "装置",
    "通道",
    "核心",
    "数据",
    "信息",
    "能力",
}


def _clamp_foreshadowing_horizon(
    expected_resolve_chapter: int | None,
    *,
    planted_in_chapter: int,
    horizon_floor: int,
) -> int | None:
    """172a.p: 按体裁 horizon 下限夹紧伏笔预计回收章.

    LLM 在结算时选定 ``expected_resolve_chapter``，玄幻等体裁常给出偏短的
    horizon（如 planted+2），在短窗口内立即 overdue。此函数把 horizon 夹到
    ``>= planted_in_chapter + horizon_floor``：

    - 只**抬高**，从不缩短（若 LLM 已给出更长 horizon 则保留）；
    - ``horizon_floor <= 0``（scifi 默认）时**完全不改变**输入，保证回退旧行为；
    - ``expected_resolve_chapter is None``（未知 horizon）时不夹，保持 None
      语义（由后续 due/overdue 逻辑处理）。

    这是运行时参数化（GenreRuntimeProfile 字段），不改结算 prompt、不新增节点，
    符合 V8 MVP 边界。
    """
    if horizon_floor <= 0 or expected_resolve_chapter is None:
        return expected_resolve_chapter
    return max(expected_resolve_chapter, planted_in_chapter + horizon_floor)


def _term_in_content(term: str, content: str) -> bool:
    """判断术语是否作为独立词出现在正文中.

    中文没有空格分词，因此普通中文后缀仍视为更长词，
    但允许「术语 + 的/中/，」等语法边界，避免漏刷真实提及。
    """
    if len(term) < 2:
        return False
    term = term.lower()
    content = content.lower()
    identifier_term = bool(re.search(r"[a-z0-9θ]", term))
    idx = content.find(term)
    while idx != -1:
        end = idx + len(term)
        if end >= len(content) or content[end] in _SETTING_REFERENCE_BOUNDARY_CHARS:
            return True
        if identifier_term and not re.match(r"[a-z0-9θ]", content[end]):
            return True
        if len(term) >= 4 and "\u4e00" <= content[end] <= "\u9fa5":
            return True
        # 后接普通中文字符 → 属于更长词，跳过
        if not ("\u4e00" <= content[end] <= "\u9fa5"):
            return True
        idx = content.find(term, idx + 1)
    return False


def _setting_value(setting: dict[str, Any] | NewSetting, field: str) -> str:
    if isinstance(setting, dict):
        return str(setting.get(field) or "")
    return str(getattr(setting, field, "") or "")


def _compact_setting_text(text: str) -> str:
    compact = text.lower().replace("theta", "θ").replace("第七", "第7")
    return re.sub(r"[\s·—\-_/（）()\[\]【】,，、;；:.：]+", "", compact)


def _cjk_runs(text: str) -> list[str]:
    """提取连续中文片段。"""
    return re.findall(r"[\u4e00-\u9fff]{2,}", text)


def _setting_low_info_tokens(setting: dict[str, Any]) -> set[str]:
    """推断不适合作为引用证据的低信息 token。"""
    tokens = set(_LOW_INFO_REFERENCE_TOKENS)
    name = str(setting.get("setting_name") or "")
    # 复合设定常以“角色A与对象B的属性”命名；开头 2-3 字多为角色/主体名，
    # 单独命中不能证明该设定被回收。
    prefix = re.split(r"[与和及的]", name, maxsplit=1)[0].strip()
    if 2 <= len(prefix) <= 3:
        tokens.add(prefix)
    return tokens


def _setting_core_phrases(setting: dict[str, Any]) -> set[str]:
    """从 setting name/description 派生较强的中文核心短语。"""
    text = " ".join(
        [
            str(setting.get("setting_name") or ""),
            str(setting.get("description") or ""),
        ]
    )
    low_info = _setting_low_info_tokens(setting)
    phrases: set[str] = set()
    for run in _cjk_runs(text):
        for part in _SETTING_REFERENCE_SPLIT_RE.split(run):
            cleaned = part.strip()
            if len(cleaned) >= 5 and cleaned not in low_info:
                phrases.add(cleaned)
    return phrases


def _setting_reference_tokens(setting: dict[str, Any]) -> set[str]:
    """生成复合设定的轻量 token，用于多 token 命中。"""
    low_info = _setting_low_info_tokens(setting)
    tokens: set[str] = set()
    for phrase in _setting_core_phrases(setting):
        if 2 <= len(phrase) <= 8:
            tokens.add(phrase)
        max_n = min(4, len(phrase))
        for n in range(2, max_n + 1):
            for i in range(0, len(phrase) - n + 1):
                token = phrase[i : i + n]
                if token not in low_info:
                    tokens.add(token)
    return tokens


def _has_multi_token_setting_reference(setting: dict[str, Any], content: str) -> bool:
    """复合设定多 token 命中。

    单个“基因”这类短词不构成回收；但“基因 + 收割者 + 签名”等多 token 同章出现，
    足以证明正文在推进同一 critical setting。
    """
    if setting.get("category") != "critical":
        return False
    tokens = _setting_reference_tokens(setting)
    if len(tokens) < 3:
        return False
    lowered_content = content.lower()
    matched = {token for token in tokens if token.lower() in lowered_content}
    if len(matched) < 3:
        return False
    return any(len(token) >= 3 for token in matched)


def _setting_cluster_canonical(setting: dict[str, Any] | NewSetting) -> str | None:
    text = " ".join(
        [
            _setting_value(setting, "setting_key"),
            _setting_value(setting, "setting_name"),
            _setting_value(setting, "description"),
        ]
    )
    compact = _compact_setting_text(text)
    if "e7" in compact and any(token in compact for token in ("通道", "相位", "节点", "拓扑")):
        return "e7_phase_channel_node"
    if "拓扑" in compact and ("空间" in compact or "相位" in compact):
        return "space_phase_topology"
    if "自修复" in compact and any(token in compact for token in ("墙壁", "墙体", "舱壁", "材料")):
        return "wall_material_self_repair"
    if "第7远征队" in compact:
        return "expedition_team_7"
    if "巨型遗迹" in compact and any(
        token in compact for token in ("表面材料", "表面", "外层", "合金")
    ):
        return "mega_ruin_surface_material"
    if "英仙臂外侧巨型遗迹" in compact:
        return "perseus_arm_mega_ruin"
    if "斐波那契" in compact and any(
        token in compact for token in ("频率", "跳变序列", "frequency")
    ):
        return "fibonacci_frequency_sequence"
    if "时空标记" in compact:
        return "spacetime_marking_system"
    if "墙壁" in compact and any(token in compact for token in ("活体", "能量纹路")):
        return "ruin_wall_living_properties"
    return None


def _add_cluster_reference_terms(
    setting: dict[str, Any] | NewSetting, terms: set[str]
) -> None:
    canonical = _setting_cluster_canonical(setting)
    if canonical == "e7_phase_channel_node":
        terms.update(
            {
                "E-7通道相位节点",
                "E-7-θ通道相位节点",
                "E-7θ通道相位节点",
                "E-7-θ",
                "E-7θ",
                "E-7通道",
                "E-7相位节点",
                "E-7相位拓扑",
                "E-7空间拓扑",
            }
        )
    elif canonical == "space_phase_topology":
        terms.update({"空间拓扑", "相位拓扑", "空间/相位拓扑", "空间相位拓扑"})
    elif canonical == "wall_material_self_repair":
        terms.update(
            {"墙壁自修复", "材料自修复", "墙壁/材料自修复", "墙壁材料自修复", "舱壁自修复"}
        )
    elif canonical == "expedition_team_7":
        terms.update({"第7远征队", "第七远征队"})
    elif canonical == "mega_ruin_surface_material":
        terms.update(
            {
                "巨型遗迹表面材料",
                "遗迹表面半流体材料",
                "从表面材料下浮现",
                "半流体材料",
                "巨型遗迹表面的能量纹路",
                "遗迹表面的能量纹路",
                "墙壁上的能量纹路",
                "非欧几何合金碎片",
            }
        )
    elif canonical == "perseus_arm_mega_ruin":
        terms.update(
            {
                "英仙臂外侧巨型遗迹",
                "英仙臂外侧的巨型遗迹",
                "英仙臂外侧巨型遗迹外层",
                "英仙臂外侧的巨型遗迹外层",
                "巨型遗迹外层",
            }
        )
    elif canonical == "fibonacci_frequency_sequence":
        terms.update(
            {
                "斐波那契频率跳变序列",
                "斐波那契序列频率",
                "斐波那契频率",
                "频率跳变序列",
            }
        )
    elif canonical == "spacetime_marking_system":
        terms.update({"非本地时空标记", "非本地时空标记系统", "时空标记系统"})
    elif canonical == "ruin_wall_living_properties":
        terms.update(
            {
                "遗迹墙壁活体特性",
                "墙壁活体特性",
                "墙壁能量纹路",
                "墙壁上的能量纹路",
            }
        )


def _setting_reference_terms(setting: dict[str, Any]) -> set[str]:
    """生成 setting 的轻量引用词集合."""
    terms: set[str] = set()
    name = (setting.get("setting_name") or "").strip()
    if len(name) >= 2:
        terms.add(name)
        # Bug（V8 172b.p）：xuanhuan 惯用引号包裹的口语化设定名（如 祭坛上的'那个东西'），
        # 旧 split 集不含引号，导致引号内的 4 字核心词（那个东西）永远不生成为引用词，
        # 正文明明多次出现却判为 orphan → 误触 health_low_p1_halt。将中英文引号纳入
        # 分隔符，使引号内实体成为独立 name-part term（仍受 len>=2 与 low-info 过滤约束）。
        for part in re.split(
            r"[·—\-_/（）()\[\]【】,，、;；:\s'\u2018\u2019\u201c\u201d\"“”]+", name
        ):
            cleaned = part.strip()
            if len(cleaned) >= 2:
                terms.add(cleaned)

    setting_key = str(setting.get("setting_key") or "")
    key_tail = setting_key.split(".")[-1].replace("_", "")
    if len(key_tail) >= 2:
        terms.add(key_tail)

    terms.update(_setting_core_phrases(setting))
    _add_cluster_reference_terms(setting, terms)
    return terms


async def _recycle_duplicate_setting_clusters(
    settlement: StateSettlement,
    project_id: str,
    chapter_number: int,
    setting_tracking_repo: SettingTrackingRepository,
    conn: aiosqlite.Connection | None = None,
) -> set[str]:
    """新设定若命中已有同簇 canonical，则刷新旧设定并跳过重复登记."""
    if not settlement.new_settings:
        return set()

    active_settings = [
        s
        for s in await setting_tracking_repo.list_by_project(project_id)
        if s.get("status", "active") == "active"
    ]
    canonical_to_existing: dict[str, dict[str, Any]] = {}
    for row in active_settings:
        canonical = _setting_cluster_canonical(row)
        if canonical and canonical not in canonical_to_existing:
            canonical_to_existing[canonical] = row

    retained: list[NewSetting] = []
    refreshed_keys: set[str] = set()
    seen_new_canonicals: set[str] = set()
    for setting in settlement.new_settings:
        normalized_key = _normalize_setting_key(setting.setting_key, setting.setting_name)
        if normalized_key is not None:
            setting.setting_key = normalized_key
        canonical = _setting_cluster_canonical(setting)
        existing = canonical_to_existing.get(canonical or "")
        if (
            canonical
            and existing
            and existing.get("setting_key")
            and existing.get("setting_key") != setting.setting_key
        ):
            await setting_tracking_repo.update_last_mentioned(
                existing["tracking_id"], chapter_number, conn=conn
            )
            refreshed_keys.add(str(existing["setting_key"]))
            logger.info(
                "settlement.setting_duplicate_cluster_recycled",
                project_id=project_id,
                chapter_number=chapter_number,
                duplicate_key=setting.setting_key,
                canonical_key=existing["setting_key"],
                canonical=canonical,
            )
            continue
        if canonical and canonical in seen_new_canonicals:
            logger.info(
                "settlement.setting_duplicate_cluster_skipped",
                project_id=project_id,
                chapter_number=chapter_number,
                duplicate_key=setting.setting_key,
                canonical=canonical,
            )
            continue
        retained.append(setting)
        if canonical:
            seen_new_canonicals.add(canonical)

    settlement.new_settings = retained
    return refreshed_keys


def _detect_setting_references(
    content: str,
    active_settings: list[dict[str, Any]],
) -> dict[str, str]:
    """扫描正文，返回被引用的 setting_tracking_id -> setting_key 映射.

    优先使用 setting_name；若 setting_name 为空或太短，则回退到 setting_key 最后一段。
    """
    referenced: dict[str, str] = {}
    if not content:
        return referenced

    for setting in active_settings:
        tracking_id = setting.get("tracking_id")
        setting_key = setting.get("setting_key", "")
        if not tracking_id or not setting_key:
            continue

        for term in _setting_reference_terms(setting):
            if _term_in_content(term, content):
                referenced[tracking_id] = setting_key
                break
        else:
            if _has_multi_token_setting_reference(setting, content):
                referenced[tracking_id] = setting_key

    return referenced


async def _resolve_recycled_continuity_marks(
    project_id: str,
    referenced_keys: set[str],
    human_mark_repo: HumanMarkRepository,
    conn: aiosqlite.Connection | None = None,
) -> int:
    """将目标 setting 已被回收/提及的 continuity_auditor human_mark 标记为 resolved."""
    if not referenced_keys:
        return 0

    marks = await human_mark_repo.list_by_project(
        project_id, include_resolved=False
    )
    resolved_count = 0
    for mark in marks:
        if mark.source != "continuity_auditor":
            continue
        if mark.target_key in referenced_keys and mark.mark_type == "setting":
            if await human_mark_repo.resolve(mark.mark_id, conn=conn):
                resolved_count += 1
                logger.info(
                    "settlement.human_mark_resolved",
                    mark_id=mark.mark_id,
                    target_key=mark.target_key,
                    project_id=project_id,
                )
    return resolved_count


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
    content: str | None = None,
    foreshadowing_horizon_floor: int = 0,
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
        foreshadowing_horizon_floor: 172a.p 按体裁伏笔 horizon 下限（章）；
            plant 时把 expected_resolve_chapter 夹到 >= planted+floor（只抬高）。
            0（scifi 默认）= 不夹 = 旧行为。
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
    duplicate_refreshed_keys = await _recycle_duplicate_setting_clusters(
        settlement=settlement,
        project_id=project_id,
        chapter_number=chapter_number,
        setting_tracking_repo=setting_tracking_repo,
        conn=conn,
    )

    async def _apply_core(
        c: aiosqlite.Connection,
    ) -> None:
        """核心写入逻辑（与连接来源无关）."""
        # 0. Task 170p: 本章首次出场的具名配角/反派 — 幂等 INSERT characters.
        #    settlement 已做证据门禁（source_quote/name 在正文中、去重、非代词）。
        #    绑定到同一事务 conn；新建角色 ID 加入 valid_char_ids，使同章 update 可引用。
        existing_names = {c2.name for c2 in project_characters if c2.name}
        for nc in settlement.new_characters:
            name = (nc.name or "").strip()
            if not name or name in existing_names:
                continue
            character = Character(
                character_id=f"char-{project_id}-{uuid.uuid4().hex[:8]}",
                project_id=project_id,
                name=name,
                role_type=nc.role_type,
                background=nc.background or "",
            )
            await char_repo.create(character, conn=c)
            valid_char_ids.add(character.character_id)
            role_type_by_id[character.character_id] = nc.role_type
            existing_names.add(name)
            logger.info(
                "settlement.new_character_created",
                character_id=character.character_id,
                name=name,
                role_type=nc.role_type,
                project_id=project_id,
                chapter_number=chapter_number,
            )

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
                # 172a.p: 按体裁 horizon 下限夹紧 expected_resolve_chapter。
                # 只抬高、从不缩短；floor=0（scifi 默认）时完全等价旧行为。
                expected = _clamp_foreshadowing_horizon(
                    fs.expected_resolve_chapter,
                    planted_in_chapter=chapter_number,
                    horizon_floor=foreshadowing_horizon_floor,
                )
                item = ForeshadowingItem(
                    foreshadowing_id=fs_id,
                    description=fs.description,
                    planted_in_chapter=chapter_number,
                    expected_resolve_chapter=expected,
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

    # 5. Task 137: 设定回收闭环 — 正文提及已存在设定时刷新 last_mentioned
    refreshed_keys: set[str] = set(duplicate_refreshed_keys)
    if content:
        try:
            active_settings = [
                s
                for s in await setting_tracking_repo.list_by_project(project_id)
                if s.get("status", "active") == "active"
            ]
            referenced = _detect_setting_references(content, active_settings)
            for tracking_id, setting_key in referenced.items():
                await setting_tracking_repo.update_last_mentioned(
                    tracking_id, chapter_number, conn=conn
                )
                refreshed_keys.add(setting_key)

            # 同时接纳 SettlementExtractor 显式报告的 recycled_settings
            key_to_tracking = {
                s.get("setting_key", ""): s.get("tracking_id")
                for s in active_settings
                if s.get("setting_key")
            }
            canonical_to_setting = {
                canonical: s
                for s in active_settings
                if (canonical := _setting_cluster_canonical(s))
            }
            for key in set(settlement.recycled_settings or []):
                recycled_tracking_id: str | None = key_to_tracking.get(key)
                refresh_key = key
                if not recycled_tracking_id:
                    canonical = _setting_cluster_canonical(
                        {
                            "setting_key": key,
                            "setting_name": key,
                            "description": key,
                        }
                    )
                    setting = canonical_to_setting.get(canonical or "")
                    recycled_tracking_id = setting.get("tracking_id") if setting else None
                    refresh_key = setting.get("setting_key", key) if setting else key
                if recycled_tracking_id and refresh_key not in refreshed_keys:
                    await setting_tracking_repo.update_last_mentioned(
                        recycled_tracking_id, chapter_number, conn=conn
                    )
                    refreshed_keys.add(refresh_key)

            if refreshed_keys:
                logger.info(
                    "settlement.settings_recycled",
                    project_id=project_id,
                    chapter_number=chapter_number,
                    count=len(refreshed_keys),
                    keys=sorted(refreshed_keys),
                )
            resolved_count = await _resolve_recycled_continuity_marks(
                project_id, refreshed_keys, HumanMarkRepository(), conn
            )
            if resolved_count:
                logger.info(
                    "settlement.human_marks_resolved",
                    project_id=project_id,
                    chapter_number=chapter_number,
                    count=resolved_count,
                )
        except (RuntimeError, OSError, ConnectionError, ValueError, TypeError) as exc:
            logger.warning(
                "settlement.recycling_detection_failed",
                project_id=project_id,
                chapter_number=chapter_number,
                error=str(exc),
            )

    # 6+7. Continuity tracking + Permanent scenes（同一连接，调用方管理事务）
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


def _infer_setting_category(
    setting: NewSetting,
    *,
    protagonist_names: set[str] | None = None,
) -> str:
    """根据 setting 内容推断分类.

    ``critical`` 判定需同时命中 ``critical_keywords`` 与主角标识集合；
    不再硬编码主角名，主角名由调用方从项目档案注入。
    """
    text = f"{setting.setting_key} {setting.setting_name} {setting.description}".lower()

    technical_keywords = [
        "型号", "参数", "引擎", "协议", "版本", "system", "model",
        "规格", "配置", "功率", "频率", "波长", "速率", "接口",
        "带宽", "电压", "容量", "速度", "精度",
    ]
    if any(kw in text for kw in technical_keywords):
        return "technical"

    critical_keywords = [
        "主角", "protagonist", "main",
        "命格", "天赋", "血脉", "传承",
    ]
    if protagonist_names:
        protagonist_terms = {name.lower() for name in protagonist_names if name}
    else:
        protagonist_terms = {
            "主角", "主人公", "protagonist", "命定之人", "全书核心",
        }
    if any(kw in text for kw in critical_keywords) and any(
        term in text for term in protagonist_terms
    ):
        return "critical"

    historical_keywords = [
        "历史", "过去", "年代", "纪元", "古代", "上古", "曾经",
        "history", "past", "era", "ancient",
    ]
    if any(kw in text for kw in historical_keywords):
        return "historical"

    return "background"


def _build_protagonist_names(project: ProjectSetting | None) -> set[str]:
    """Build protagonist name set from project; falls back to generic terms."""
    names: set[str] = set()
    if project and project.protagonist_name:
        names.add(project.protagonist_name)
        if len(project.protagonist_name) >= 2:
            names.add(project.protagonist_name[:2])
        return names
    names.update({"主角", "主人公", "protagonist", "命定之人", "全书核心"})
    return names


# Task 172c.p: inventory 聚合清单拆分 — wuxia 等体裁的结算 LLM 习惯把主角持有物写成
# 聚合清单（「持有断刀、断刀门刀谱、断刀令（两块铁牌）…」），旧实现整串截 50 字建一条
# 记录且旧记录 last_used 永久冻结 → 每章一条新聚合串、3 章后 forgotten，是粒度伪影。
# 按顶层分隔符拆单物品（括号内分隔符不切）、剥除持有/缴获类前缀，再与已有 held 记录
# 同名匹配：命中刷新 last_used，未命中才建档。
_INVENTORY_SEPARATOR_CHARS = "、，,；;/"
_INVENTORY_PREFIX_RE = re.compile(
    r"^(?:从[^、，,；;/]+?处)?"
    r"(?:缴获|持有|携带|随身带着|随身|拥有|获得|取得|收起|带着|提着|握着|背着|怀揣)的?"
)
_INVENTORY_LOW_INFO_TOKENS = frozenset(
    {"无", "空手", "暂无", "没有", "随身物品", "物品", "道具"}
)


def _normalize_item_name(name: str) -> str:
    """物品名归一化（去空白），用于同名匹配."""
    return re.sub(r"\s+", "", name)


def _split_inventory_items(value: str) -> list[str]:
    """把 inventory 字段的 new_value 拆成单物品名列表.

    - 按 `、` `，` `,` `；` `;` `/` 顶层分隔符切分，括号（`（）()`）内的分隔符不切
      （「断刀令（两块铁牌）」保持一条）；
    - 剥除「持有/携带/缴获/从…处缴获」等前缀；
    - 过滤低信息碎片（len<2、空值、纯无意义词）；
    - 同一 value 内按归一化名去重（保序）。
    """
    items: list[str] = []
    current: list[str] = []
    depth = 0

    def _flush() -> None:
        name = _INVENTORY_PREFIX_RE.sub("", "".join(current).strip()).strip()
        if len(name) >= 2 and name not in _INVENTORY_LOW_INFO_TOKENS:
            items.append(name)

    for ch in value:
        if ch in "（(":
            depth += 1
            current.append(ch)
        elif ch in "）)":
            depth = max(0, depth - 1)
            current.append(ch)
        elif ch in _INVENTORY_SEPARATOR_CHARS and depth == 0:
            _flush()
            current = []
        else:
            current.append(ch)
    _flush()

    seen: set[str] = set()
    unique: list[str] = []
    for name in items:
        key = _normalize_item_name(name)
        if key not in seen:
            seen.add(key)
            unique.append(name)
    return unique


# Task 172c.q: 物品身份 = 基底名（首个括号前的核心名词）。wuxia 结算 LLM 把当章状态
# 写进物品名（「断刀（濒临碎裂）」「断刀（裂纹上百道）」逐章变体），全名精确匹配
# 永不命中 → 同一物理物品逐章堆积。基底名相等即同一物品；「断刀」与「断刀门刀谱」
# 基底名不同，不会被误并。不做前缀匹配（「断刀门刀谱」以「断刀」为前缀，前缀规则
# 必然误吞）。
_INVENTORY_CONSUMED_RE = re.compile(r"已服下|已交出|已损毁|已用完|已耗尽|被夺走|被抢|抢走|已赠|已消耗|已捏碎|已碎裂|已折断")
_INVENTORY_BASE_NAME_MAX = 10


def _item_base_name(name: str) -> str:
    """物品基底名：首个括号（`（`/`(`）前的片段."""
    return re.split(r"[（(]", name, maxsplit=1)[0].strip()


def _is_inventory_fragment(base_name: str) -> bool:
    """基底名 >10 字视为叙述句碎片.

    172c.q 段 2 实证：正常物品基底名 ≤8 字（「密室三把钥匙之一」为最长样本），
    >10 字无一例外是「透出一丝不属于这个世界的微光」类叙述句碎片。
    """
    return len(base_name) > _INVENTORY_BASE_NAME_MAX


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
    project = await ProjectRepository().get(project_id)
    protagonist_names = _build_protagonist_names(project)

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
            category = _infer_setting_category(
                setting, protagonist_names=protagonist_names
            )
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
    existing_items = await inventory_repo.list_by_project(project_id)
    # 172c.q: 同时维护全名索引与基底名索引，用于状态变体归一。
    held_full: dict[str, dict[str, dict[str, Any]]] = {}
    held_base: dict[str, dict[str, dict[str, Any]]] = {}
    for row in existing_items:
        if row.get("status", "held") != "held":
            continue
        char_key = row.get("character_id") or ""
        held_full.setdefault(char_key, {})[_normalize_item_name(row["item_name"])] = row
        base_key = _normalize_item_name(_item_base_name(row["item_name"]))
        if len(base_key) >= 2:
            held_base.setdefault(char_key, {}).setdefault(base_key, row)

    for update in settlement.character_updates:
        field_lower = update.field.lower()
        if "inventory" in field_lower or "物品" in field_lower or "道具" in field_lower:
            # 172c.p: 拆单物品 + 同名 held 记录刷新（不新建），聚合清单不再逐章堆积
            # 172c.q: 基底名变体归一 + 非物品碎片过滤 + 消耗状态流转
            char_key = update.character_id or ""
            full_index = held_full.setdefault(char_key, {})
            base_index = held_base.setdefault(char_key, {})
            for item_name in _split_inventory_items(update.new_value):
                base_name = _item_base_name(item_name)
                if _is_inventory_fragment(base_name):
                    logger.warning(
                        "settlement.inventory_fragment_rejected",
                        project_id=project_id,
                        chapter_number=chapter_number,
                        item_name=item_name[:50],
                    )
                    continue
                consumed = bool(_INVENTORY_CONSUMED_RE.search(item_name))
                norm = _normalize_item_name(item_name)
                norm_base = _normalize_item_name(base_name)

                existing = full_index.get(norm)
                if existing is None and len(norm_base) >= 2:
                    existing = base_index.get(norm_base)
                if existing is not None:
                    await inventory_repo.update_last_used(
                        existing["track_id"], chapter_number, conn=conn
                    )
                    if consumed:
                        await inventory_repo.update_status(
                            existing["track_id"], "consumed", conn=conn
                        )
                        # 消耗后从 held 索引移除；后续再获得同物可重新登记
                        full_index.pop(
                            _normalize_item_name(existing["item_name"]), None
                        )
                        base_index.pop(
                            _normalize_item_name(
                                _item_base_name(existing["item_name"])
                            ),
                            None,
                        )
                    continue

                track_id = f"inv-{project_id}-{uuid.uuid4().hex[:8]}"
                status = "consumed" if consumed else "held"
                await inventory_repo.create(
                    track_id=track_id,
                    project_id=project_id,
                    character_id=update.character_id,
                    item_name=item_name[:50],
                    item_description=f"From field '{update.field}'",
                    acquired_in_chapter=chapter_number,
                    status=status,
                    conn=conn,
                )
                new_row: dict[str, Any] = {
                    "track_id": track_id,
                    "item_name": item_name,
                    "status": status,
                }
                if status == "held":
                    full_index[norm] = new_row
                    if len(norm_base) >= 2:
                        base_index.setdefault(norm_base, new_row)
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
