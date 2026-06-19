"""Setting 生产端质量控制 — Task 110b.

负责 setting_key 规范化、fallback 生成、以及同一 key 的版本 archive。
"""

from __future__ import annotations

import re
from hashlib import sha1
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    import aiosqlite

    from songyan.db.settlement_repo import SettingSnapshotRepository

logger = structlog.get_logger(__name__)

# category.subcategory.name，每段允许小写字母、数字、下划线，但必须以字母开头
_SETTING_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")

# 用于从 setting_name 提取字符：连续中文字符、连续英文/数字
_TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9]+|[\u4e00-\u9fff]+")

# 停用词，fallback 生成时跳过
_STOP_WORDS: set[str] = {
    "的", "了", "和", "是", "在", "有", "被", "为", "之", "与", "及", "对", "从", "到",
    "the", "a", "an", "of", "and", "or", "in", "on", "at", "to", "for", "with", "by",
}


def _is_valid_setting_key(key: str) -> bool:
    """检查 setting_key 是否符合 category.subcategory.name 格式."""
    return bool(key) and bool(_SETTING_KEY_PATTERN.match(key))


def _sanitize_key_segment(segment: str, fallback_prefix: str = "s") -> str:
    """将单个 key 段转换为合法 ASCII 标识符段.

    LLM 可能输出中文、数字开头或带符号的段。setting_key 是长期事实源
    标识符，必须稳定且可被 schema 校验，因此非 ASCII 段使用短 hash 编码。
    """
    raw = segment.strip().lower()
    ascii_part = re.sub(r"[^a-z0-9_]+", "_", raw).strip("_")
    if ascii_part:
        if ascii_part[0].isdigit():
            ascii_part = f"{fallback_prefix}_{ascii_part}"
        return ascii_part

    digest = sha1(raw.encode("utf-8")).hexdigest()[:8]
    return f"{fallback_prefix}_{digest}"


def _sanitize_setting_key_candidate(key: str) -> str | None:
    """清洗三段式候选 key，返回满足 schema 的 key."""
    parts = [p.strip() for p in key.split(".") if p.strip()]
    if len(parts) != 3:
        return None
    sanitized = [
        _sanitize_key_segment(parts[0], "c"),
        _sanitize_key_segment(parts[1], "s"),
        _sanitize_key_segment(parts[2], "n"),
    ]
    candidate = ".".join(sanitized)
    return candidate if _is_valid_setting_key(candidate) else None


def _normalize_key_segments(key: str) -> str | None:
    """尝试把多段或两段 key 规范化为 3 段.

    - 4 段及以上：合并前面所有段到第一段
    - 2 段：尝试拆分第二段（如用下划线分割）或返回 None
    - 3 段：清洗非法字符、大小写、数字开头和非 ASCII 段
    """
    parts = [p.strip() for p in key.split(".") if p.strip()]
    if len(parts) == 3:
        return _sanitize_setting_key_candidate(".".join(parts))
    if len(parts) >= 4:
        # 合并前 n-2 段为 category，倒数第二段为 subcategory，最后一段为 name
        category = "_".join(parts[:-2])
        subcategory = parts[-2]
        name = parts[-1]
        return _sanitize_setting_key_candidate(f"{category}.{subcategory}.{name}")
    if len(parts) == 2:
        # 尝试把第二段用下划线拆成两段
        sub_parts = parts[1].split("_")
        if len(sub_parts) >= 2:
            return _sanitize_setting_key_candidate(
                f"{parts[0]}.{sub_parts[0]}.{ '_'.join(sub_parts[1:])}"
            )
    return None


def _split_chinese(text: str, max_pieces: int = 3) -> list[str]:
    """把纯中文字符串按每 2 个字符切分，去掉单个停用字.

    例如 "通信天线构造" → ["通信", "天线", "构造"]
    """
    chars = [ch for ch in text if ch not in _STOP_WORDS]
    result: list[str] = []
    i = 0
    n = len(chars)
    while i < n and len(result) < max_pieces:
        remaining = n - i
        if remaining >= 2:
            result.append("".join(chars[i : i + 2]))
            i += 2
        else:
            result.append(chars[i])
            i += 1
    return result


def _extract_keywords(text: str, max_words: int = 3) -> list[str]:
    """从文本中提取关键词（小写）.

    - 英文/数字连续 token 直接作为候选
    - 中文 token 按每 2 字符切分，并跳过停用字
    - 返回最多 max_words 个不重复候选
    """
    keywords: list[str] = []
    seen: set[str] = set()

    for token in _TOKEN_PATTERN.findall(text):
        token_lower = token.lower()
        if token_lower in _STOP_WORDS or token_lower in seen:
            continue

        # 纯中文 token：做停用字过滤 + 2 字切分
        if all("\u4e00" <= ch <= "\u9fff" for ch in token):
            for piece in _split_chinese(token, max_pieces=max_words):
                piece_lower = piece.lower()
                if piece_lower not in seen and piece_lower not in _STOP_WORDS:
                    keywords.append(piece_lower)
                    seen.add(piece_lower)
                    if len(keywords) >= max_words:
                        break
        else:
            keywords.append(token_lower)
            seen.add(token_lower)

        if len(keywords) >= max_words:
            break

    return keywords[:max_words]


def _generate_fallback_key(setting_name: str) -> str | None:
    """从 setting_name 生成合规的 3 段 fallback key.

    例如 "通信天线构造" → "c_<hash>.s_<hash>.n_<hash>"
    如果无法提取 3 个有效词，返回 None。
    """
    keywords = _extract_keywords(setting_name, max_words=3)
    if len(keywords) < 3:
        return None
    return _sanitize_setting_key_candidate(
        f"{keywords[0]}.{keywords[1]}.{keywords[2]}"
    )


def _normalize_setting_key(key: str, setting_name: str) -> str | None:
    """规范化 setting_key.

    - 已合规的 key 直接返回
    - 不合规时优先从 key 本身做段合并/拆分
    - key 无法规范化时，从 setting_name 生成 fallback key
    - fallback 失败返回 None，表示该 setting 不应进入 setting_snapshots
    """
    if _is_valid_setting_key(key):
        return key

    normalized = _normalize_key_segments(key)
    if normalized is not None:
        logger.info(
            "setting_quality.key_normalized",
            original_key=key,
            fallback_key=normalized,
            setting_name=setting_name,
        )
        return normalized

    fallback = _generate_fallback_key(setting_name)
    if fallback is not None:
        logger.info(
            "setting_quality.key_normalized",
            original_key=key,
            fallback_key=fallback,
            setting_name=setting_name,
        )
        return fallback

    logger.warning(
        "setting_quality.key_discarded",
        original_key=key,
        setting_name=setting_name,
        reason="cannot_generate_fallback_key",
    )
    return None


async def _archive_previous_setting_version(
    project_id: str,
    setting_key: str,
    setting_repo: SettingSnapshotRepository,
    conn: aiosqlite.Connection | None = None,
) -> int:
    """将同一 setting_key 的旧 active snapshot 标记为 archived.

    返回被 archive 的记录数。
    """
    archived = await setting_repo.archive_by_key(
        project_id=project_id,
        setting_key=setting_key,
        conn=conn,
    )
    if archived > 0:
        logger.info(
            "setting_quality.previous_version_archived",
            project_id=project_id,
            setting_key=setting_key,
            archived_count=archived,
        )
    return archived
