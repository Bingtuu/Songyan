"""task 245 P1: 变体草稿拒写/占位判定（纯函数，窄检查薄封装）。

口径（owner 拍板 2026-11-11）：
- 字数兜底：输出 <100 字无条件判失败（章目标 3000 字；冒烟实证拒写产物
  46–77 字、真实正文 ≥1337 字）。
- 硬信号：短文本（≤500 字）中出现「（空）」回显或显式拒写关键词即判失败。
  500 字以上不查硬信号——长正文里人物台词含「无法完成」类字样的误伤防线。
"""

from __future__ import annotations

MIN_DRAFT_CHARS = 100
_HARD_SIGNAL_MAX_CHARS = 500

_EMPTY_ECHO_MARKERS = ("（空）", "(空)")

_REFUSAL_KEYWORDS = (
    "无法完成",
    "无法撰写",
    "无法续写",
    "不能完成",
    "cannot fulfill",
    "cannot complete",
    "cannot write",
    "unable to fulfill",
)

# 失败原因码（落 chapter_variants.quality_flag；CLI 直接展示）
REASON_EMPTY = "empty"
REASON_TOO_SHORT = "too_short"
REASON_EMPTY_ECHO = "empty_echo"
REASON_REFUSAL_KEYWORD = "refusal_keyword"


def classify_variant_draft(text: str | None) -> str | None:
    """Classify a variant draft; return a failure-reason code or ``None``.

    Pure function. ``None`` = 通过质量门（可交付作者评审，不代表文学质量）。
    """
    stripped = (text or "").strip()
    if not stripped:
        return REASON_EMPTY
    if any(marker in stripped for marker in _EMPTY_ECHO_MARKERS):
        return REASON_EMPTY_ECHO
    if len(stripped) <= _HARD_SIGNAL_MAX_CHARS:
        lowered = stripped.lower()
        if any(keyword in lowered for keyword in _REFUSAL_KEYWORDS):
            return REASON_REFUSAL_KEYWORD
    if len(stripped) < MIN_DRAFT_CHARS:
        return REASON_TOO_SHORT
    return None
