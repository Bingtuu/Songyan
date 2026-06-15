"""Settlement 验证 — source_quote、old_value、公式校验."""

from __future__ import annotations

import difflib
import re

import structlog

from songyan.models import (
    CharacterState,
    NewSetting,
    StateSettlement,
)
from songyan.utils.numerical_validator import NUMERICAL_TOLERANCE

logger = structlog.get_logger(__name__)


def _normalize_text(text: str) -> str:
    """统一空白字符：去头尾空格、压缩连续空白、统一换行符."""
    text = text.strip().replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n+", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text


def _quote_in_content(quote: str, content: str, threshold: float = 0.8) -> bool:
    """模糊检查 quote 是否存在于 content 中.

    先尝试精确匹配（归一化后），再尝试 difflib 块匹配。
    """
    if not quote or not content:
        return True  # 空 quote 视为通过

    norm_quote = _normalize_text(quote)
    norm_content = _normalize_text(content)

    # 1. 精确子串匹配（归一化后）
    if norm_quote in norm_content:
        return True

    # 2. 模糊匹配：滑动窗口找最佳相似度
    quote_len = len(norm_quote)
    if quote_len == 0:
        return True

    best_ratio = 0.0
    step = max(1, quote_len // 4)
    for i in range(0, len(norm_content) - quote_len + 1, step):
        window = norm_content[i : i + quote_len]
        ratio = difflib.SequenceMatcher(None, norm_quote, window).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
        if best_ratio >= threshold:
            return True

    return False


_SETTING_KEY_PATTERN = re.compile(r"^[a-z_]+\.[a-z_]+\.[a-z_]+$")


async def _validate_settlement(
    settlement: StateSettlement,
    content: str,
    current_states: list[CharacterState],
    current_settings: list[NewSetting],
    chapter_number: int = 0,
    project_id: str = "",
) -> list[str]:
    """验证结算结果，返回错误列表."""
    errors: list[str] = []

    # 1. 验证 character_update.old_value
    state_map: dict[tuple[str, str], str] = {
        (s.character_id, s.field): s.value for s in current_states
    }
    for update in settlement.character_updates:
        key = (update.character_id, update.field)
        if key in state_map and state_map[key] != update.old_value:
            errors.append(
                f"角色 {update.character_id} 的 {update.field} "
                f"当前值为 '{state_map[key]}'，"
                f"但结算声称 old_value='{update.old_value}'"
            )

    # 2. 验证 source_quote 在正文中存在（模糊匹配）
    # 注：空 source_quote 表示已被 _quote_filter 过滤，跳过验证
    for update in settlement.character_updates:
        if update.source_quote and not _quote_in_content(update.source_quote, content):
            errors.append(
                f"角色 {update.character_id} 的 source_quote "
                f"未在正文中找到: '{update.source_quote[:50]}...'"
            )
    for setting in settlement.new_settings:
        if setting.source_quote and not _quote_in_content(setting.source_quote, content):
            errors.append(
                f"设定 '{setting.setting_name}' 的 source_quote "
                f"未在正文中找到: '{setting.source_quote[:50]}...'"
            )

    # 3. 验证 setting_key 唯一性和格式
    existing_keys = {s.setting_key for s in current_settings if s.setting_key}
    for setting in settlement.new_settings:
        if setting.setting_key:
            if setting.setting_key in existing_keys:
                # Task 094: 去重已在代码层处理，此处仅记录 warning 不报错
                logger.info(
                    "settlement.duplicate_key_skipped",
                    key=setting.setting_key,
                    project_id=project_id,
                )
            if not _SETTING_KEY_PATTERN.match(setting.setting_key):
                errors.append(
                    f"设定 key '{setting.setting_key}' 格式不符合 "
                    f"category.subcategory.name 规范"
                )

    # 4. 验证 numerical_update.closing_value 公式
    for num in settlement.numerical_updates:
        expected = (
            num.opening_value
            + sum(i.amount for i in num.increments)
            - sum(d.amount for d in num.decrements)
        )
        if abs(num.closing_value - expected) > NUMERICAL_TOLERANCE:
            errors.append(
                f"角色 {num.character_id} 的 {num.attribute_name} "
                f"closing_value ({num.closing_value}) 不等于 "
                f"公式值 ({expected:.3f})"
            )

    # 5. 验证 foreshadowing_update.source_version_id
    for fs in settlement.foreshadowing_updates:
        if not fs.source_version_id:
            errors.append(
                f"伏笔 '{fs.description[:30]}...' 的 source_version_id 为空"
            )
        # Task 094: 验证 expected_resolve_chapter 必须在当前章节之后
        if fs.operation == "plant" and fs.expected_resolve_chapter is not None:
            if fs.expected_resolve_chapter <= chapter_number:
                errors.append(
                    f"伏笔 '{fs.description[:30]}...' 的预计回收章节 "
                    f"({fs.expected_resolve_chapter}) 必须大于当前章节 ({chapter_number})"
                )

    return errors
