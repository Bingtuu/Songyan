"""中文字数统计工具."""

from __future__ import annotations

import re


def count_chinese_words(text: str) -> int:
    """统计中文字数（中文字符 + 连续英文/数字词）.

    Example:
        >>> count_chinese_words("Hello 世界 123")
        4   # "Hello" + "世" + "界" + "123"
    """
    if not text:
        return 0
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    other_words = len(re.findall(r"[a-zA-Z0-9]+", text))
    return chinese_chars + other_words
