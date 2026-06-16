"""Task 110a: CharacterState 分层保真压缩.

在 settlement 写入 character_states 前，按角色重要性对长文本状态值做保真压缩。
核心原则：保留叙事功能所需的关键事实，删除修辞、过程描写和重复状态。
"""

from __future__ import annotations

import re
from typing import Literal

import structlog

logger = structlog.get_logger(__name__)

# 按角色层级的最大状态值长度
MAX_VALUE_LENGTH: dict[str, int] = {
    "protagonist": 400,
    "antagonist": 300,
    "supporting": 150,
    "functional": 60,
}

# 可压缩的 narrative 字段（location/goals/relationships 等不压缩）
COMPRESSIBLE_FIELDS: frozenset[str] = frozenset({
    "mental_state",
    "physical_state",
    "emotional_state",
    "protocol_status",
    "infection_stage",
    "status",
    "condition",
})

# 触发事件关键词
_TRIGGER_KEYWORDS: tuple[str, ...] = (
    "发现", "意识到", "得知", "看到", "听到", "了解到", "察觉到", "注意到",
    "遇见", "遭遇", "面对", "经历", "被", "受到", "接到",
)

# 决策/影响关键词
_IMPACT_KEYWORDS: tuple[str, ...] = (
    "决定", "要", "必须", "计划", "打算", "准备", "选择", "拒绝",
    "接受", "承诺", "发誓", "决心", "意图", "目标",
)

# 状态/情绪关键词
_STATUS_KEYWORDS: tuple[str, ...] = (
    "感到", "感觉", "状态", "情绪", "心情", "精神", "身体", "健康",
    "疲惫", "焦虑", "愤怒", "恐惧", "绝望", "坚定", "冷静",
)


def _split_sentences(text: str) -> list[str]:
    """按中文标点分句."""
    parts = re.split(r"[。！？；\n]+", text)
    return [p.strip() for p in parts if p.strip()]


def _find_trigger_sentence(sentences: list[str]) -> str | None:
    """找包含触发事件的句子."""
    for s in sentences:
        if any(kw in s for kw in _TRIGGER_KEYWORDS):
            return s
    return None


def _find_impact_sentence(sentences: list[str]) -> str | None:
    """找包含决策/影响的句子."""
    for s in sentences:
        if any(kw in s for kw in _IMPACT_KEYWORDS):
            return s
    return None


def _find_status_sentence(sentences: list[str]) -> str | None:
    """找描述当前状态的句子（通常第一句，或包含状态关键词）."""
    if not sentences:
        return None
    # 优先返回包含状态关键词的短句
    for s in sentences:
        if any(kw in s for kw in _STATUS_KEYWORDS) and len(s) <= 80:
            return s
    # 回退到第一句
    first = sentences[0]
    return first[:80] if len(first) > 80 else first


def _compress_narrative(value: str, max_length: int) -> str:
    """对 narrative 长文本做结构化压缩.

    输出格式：状态 | 触发 | 影响
    如果原文本很短，直接返回。
    如果无法提取有效关键信息，回退到截断。
    """
    value = value.strip()
    if len(value) <= max_length:
        return value

    sentences = _split_sentences(value)
    status = _find_status_sentence(sentences)
    trigger = _find_trigger_sentence(sentences)
    impact = _find_impact_sentence(sentences)

    # 如果 status 没有关键信息且原文本超长，直接截断
    if status and not any(
        kw in status for kw in _TRIGGER_KEYWORDS + _IMPACT_KEYWORDS + _STATUS_KEYWORDS
    ):
        return value[: max_length - 3] + "..."

    parts: list[str] = []
    if status:
        parts.append(status)
    if trigger and trigger != status:
        parts.append(trigger)
    if impact and impact not in (status, trigger):
        parts.append(impact)

    if not parts:
        #  fallback：保留前 max_length 字
        return value[: max_length - 3] + "..."

    result = " | ".join(parts)
    if len(result) > max_length:
        # 优先保留状态和决策，截断触发
        if impact:
            result = f"{status or ''} | {impact}" if status else impact
        else:
            result = status or value[:max_length]
        if len(result) > max_length:
            result = result[: max_length - 3] + "..."
    return result


def compress_character_state_value(
    value: str,
    field: str,
    role_type: Literal["protagonist", "antagonist", "supporting", "functional"],
) -> str:
    """按角色层级和字段类型压缩状态值.

    Args:
        value: LLM 提取的原始状态值
        field: 状态字段名
        role_type: 角色类型

    Returns:
        压缩后的状态值
    """
    if not value or not isinstance(value, str):
        return value

    # 默认按 supporting 处理未知角色
    max_length = MAX_VALUE_LENGTH.get(role_type, MAX_VALUE_LENGTH["supporting"])

    # location / goals / relationships 等结构化字段不压缩
    if field.lower() in ("location", "goals", "relationships", "name", "role"):
        return value

    # 只有可压缩字段且长度超过阈值才处理
    if field.lower() not in COMPRESSIBLE_FIELDS and len(value) <= max_length:
        return value

    compressed = _compress_narrative(value, max_length)

    if compressed != value:
        logger.debug(
            "state_compression.applied",
            field=field,
            role_type=role_type,
            original_length=len(value),
            compressed_length=len(compressed),
        )
    return compressed
