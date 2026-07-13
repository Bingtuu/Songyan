"""Settlement source_quote 去噪 — 过滤无效引用."""

from __future__ import annotations

import structlog

from songyan.db.repository import CharacterRepository
from songyan.models import StateSettlement

from ._validate import _quote_in_content

logger = structlog.get_logger(__name__)

MAX_QUOTE_LENGTH = 80
MIN_QUOTE_LENGTH = 5


def _contains_keyword(quote: str, keyword: str) -> bool:
    """检查 quote 是否包含 keyword 或其子串."""
    if not keyword:
        return True
    quote_lower = quote.lower()
    keyword_lower = keyword.lower()
    if keyword_lower in quote_lower:
        return True
    # 允许 keyword 的每个字至少出现一部分（中文分字匹配）
    chars = [c for c in keyword_lower if c.strip()]
    matched = sum(1 for c in chars if c in quote_lower)
    return matched >= max(1, len(chars) // 2)


def _is_valid_source_quote(quote: str, content: str, keyword: str = "") -> bool:
    """单条 source_quote 的有效性检查.

    规则：
    1. 长度在 [5, 80] 字之间
    2. 在正文中存在（模糊匹配）
    3. 包含相关关键词（可选）
    """
    if not quote:
        return False  # 空 quote 不是有效证据，必须被过滤/拒绝

    # 1. 长度过滤
    if not (MIN_QUOTE_LENGTH <= len(quote) <= MAX_QUOTE_LENGTH):
        return False

    # 2. 存在性验证
    if not _quote_in_content(quote, content):
        return False

    # 3. 关键词过滤
    if keyword and not _contains_keyword(quote, keyword):
        return False

    return True


async def _build_character_name_map(
    character_ids: set[str],
) -> dict[str, str]:
    """构建 character_id -> 角色名 的映射.

    Task 114a: quote_filter 优先使用角色名而非内部 character_id 做关键词校验.
    角色名缺失时回退至长度与存在性校验。

    Args:
        character_ids: 需要查询的 character_id 集合

    Returns:
        character_id -> 角色名 的映射，查不到的 ID 不包含在结果中
    """
    name_map: dict[str, str] = {}
    if not character_ids:
        return name_map

    char_repo = CharacterRepository()
    for char_id in character_ids:
        try:
            char = await char_repo.get(char_id)
            if char and char.name:
                name_map[char_id] = char.name
        except Exception as exc:
            logger.warning(
                "quote_filter.character_lookup_failed",
                character_id=char_id,
                error=str(exc),
            )
    return name_map


async def filter_settlement_source_quotes(
    settlement: StateSettlement,
    content: str,
) -> int:
    """过滤 settlement 中所有 source_quote 噪声.

    Task 114a 修复：
    - CharacterUpdate 优先使用角色名而非内部 character_id 做关键词校验
    - 角色名缺失时回退至长度与存在性校验，防止误杀合法引用

    对以下对象的 source_quote 执行过滤：
    - CharacterUpdate
    - NewSetting（含同一 setting_key 去重）
    - Increment / Decrement

    无效 quote 被清空为 ""，函数返回被过滤的数量。

    Args:
        settlement: 待过滤的 StateSettlement（原地修改）.
        content: 章节正文，用于存在性验证.

    Returns:
        被过滤的 source_quote 数量.
    """
    filtered_count = 0

    # 1. CharacterUpdate — Task 114a: 使用角色名替代内部 ID
    character_ids = {u.character_id for u in settlement.character_updates}
    name_map = await _build_character_name_map(character_ids)

    for update in settlement.character_updates:
        # Task 114a: 优先使用角色名，缺失时回退至无关键词校验
        keyword = name_map.get(update.character_id, "")
        if not _is_valid_source_quote(
            update.source_quote, content, keyword=keyword
        ):
            if update.source_quote:
                logger.debug(
                    "quote_filter.character_update_filtered",
                    character_id=update.character_id,
                    character_name=name_map.get(update.character_id),
                    field=update.field,
                    quote_length=len(update.source_quote),
                )
                update.source_quote = ""
                filtered_count += 1

    # 2. NewSetting — 先按 setting_key 去重，再逐条过滤
    settings_by_key: dict[str, list[tuple[int, str]]] = {}  # key -> [(index, quote)]
    for idx, setting in enumerate(settlement.new_settings):
        key = setting.setting_key or setting.setting_name
        settings_by_key.setdefault(key, []).append((idx, setting.source_quote))

    # 同一 key 保留 source_quote 最短的（空 quote 不参与）
    keep_indices: set[int] = set()
    for key, items in settings_by_key.items():
        non_empty = [(i, q) for i, q in items if q]
        if len(non_empty) > 1:
            non_empty.sort(key=lambda x: len(x[1]))
            for i, _ in non_empty[1:]:
                settlement.new_settings[i].source_quote = ""
                filtered_count += 1
                logger.debug(
                    "quote_filter.new_setting_deduplicated",
                    setting_key=key,
                    index=i,
                )
        # 标记保留的索引
        if non_empty:
            keep_indices.add(non_empty[0][0])
        for i, q in items:
            if not q:
                keep_indices.add(i)

    # 逐条过滤保留的 NewSetting
    for idx, setting in enumerate(settlement.new_settings):
        if not setting.source_quote:
            continue
        keyword = setting.setting_name or setting.setting_key
        if not _is_valid_source_quote(setting.source_quote, content, keyword=keyword):
            logger.debug(
                "quote_filter.new_setting_filtered",
                setting_name=setting.setting_name,
                setting_key=setting.setting_key,
                quote_length=len(setting.source_quote),
            )
            setting.source_quote = ""
            filtered_count += 1

    # 3. NumericalUpdate — Increment / Decrement
    for num in settlement.numerical_updates:
        for inc in num.increments:
            if not _is_valid_source_quote(inc.source_quote, content):
                if inc.source_quote:
                    logger.debug(
                        "quote_filter.increment_filtered",
                        character_id=num.character_id,
                        attribute=num.attribute_name,
                    )
                    inc.source_quote = ""
                    filtered_count += 1
        for dec in num.decrements:
            if not _is_valid_source_quote(dec.source_quote, content):
                if dec.source_quote:
                    logger.debug(
                        "quote_filter.decrement_filtered",
                        character_id=num.character_id,
                        attribute=num.attribute_name,
                    )
                    dec.source_quote = ""
                    filtered_count += 1

    if filtered_count > 0:
        logger.info(
            "quote_filter.done",
            filtered_count=filtered_count,
            character_updates=len(settlement.character_updates),
            new_settings=len(settlement.new_settings),
            numerical_updates=len(settlement.numerical_updates),
        )
    return filtered_count
