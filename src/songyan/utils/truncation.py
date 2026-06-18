"""字数截断工具 — 按 scene 边界或自然语言边界截断正文."""

from __future__ import annotations

import re

from songyan.utils.scene_parser import SCENE_PATTERN, parse_scenes
from songyan.utils.word_count import count_chinese_words

# 章节类型感知的字数容差倍数：不同章节类型有不同的自然篇幅
_CHAPTER_TYPE_TOLERANCE: dict[str, float] = {
    "conflict": 1.35,
    "tech_revelation": 1.30,
    "world_building": 1.25,
    "opening": 1.20,
    "exploration": 1.20,
    "transition": 1.15,
    "exposition": 1.20,
    "climax": 1.35,
    "action": 1.35,
    "revelation": 1.30,
}
_DEFAULT_TOLERANCE: float = 1.20
_LOWER_TOLERANCE: float = 0.80


def word_count_bounds(
    word_count_target: int,
    chapter_type: str | None = None,
) -> tuple[int, int]:
    """返回 Writer/RuleAuditor/ScoreAggregator 共用的字数上下界."""
    if word_count_target <= 0:
        return 0, 0
    multiplier = _CHAPTER_TYPE_TOLERANCE.get(chapter_type or "", _DEFAULT_TOLERANCE)
    return int(word_count_target * _LOWER_TOLERANCE), int(word_count_target * multiplier)


def enforce_word_count(
    content: str,
    scenes: list[dict],
    word_count_target: int,
    current_word_count: int,
    chapter_type: str | None = None,
) -> tuple[str, list[dict], int, bool, str]:
    """强制截断正文到目标字数以内，根据章节类型动态调整上限。

    删除了 min_scenes 场景数保护 — Task 096 数据证明 1-scene 章节在叙事上合理，
    不应因其场景数少而被豁免字数截断。
    """
    _lower, _upper = word_count_bounds(word_count_target, chapter_type)
    if current_word_count <= _upper:
        return content, scenes, current_word_count, False, ""
    if len(scenes) < 1:
        return content, scenes, current_word_count, False, "_no_scenes_found"
    _headers = list(SCENE_PATTERN.finditer(content))
    if len(_headers) < 1:
        return content, scenes, current_word_count, False, "no_scene_headers_found"

    for _i in range(len(_headers) - 1, 0, -1):
        _cut = _headers[_i].start()
        _t = content[:_cut].strip()
        _wc = count_chinese_words(_t)
        _ns = parse_scenes(_t)

        # 字数在 [lower, upper] 范围内且 scene 数满足最低要求
        if _wc <= _upper and _wc >= _lower and len(_ns) >= 1:
            return _t, _ns, _wc, True, f"truncated_before_scene_{_i + 1}"

        # 如果字数已低于 lower，往前一个 scene 回退
        if _wc < _lower and _i + 1 < len(_headers):
            _cut = _headers[_i + 1].start()
            _t2 = content[:_cut].strip()
            _wc2 = count_chinese_words(_t2)
            _ns2 = parse_scenes(_t2)
            if _wc2 >= _lower and len(_ns2) >= 1:
                return _t2, _ns2, _wc2, True, f"truncated_before_scene_{_i + 2}"
            continue

    # 兜底：截断到第 2 个 scene 开头（仅当有至少 2 个 scene 时）
    if len(_headers) >= 2:
        _cut = _headers[1].start()
        _t = content[:_cut].strip()
        _wc = count_chinese_words(_t)
        _ns = parse_scenes(_t)
        if _wc <= _upper and _wc >= _lower and len(_ns) >= 1:
            return _t, _ns, _wc, True, "truncated_before_scene_2"

    # 所有截断方案都不满足约束 → 保留原始内容
    return content, scenes, current_word_count, False, "truncation_would_destroy_structure"


def hard_truncate_at_boundary(content: str, max_words: int) -> str:
    """硬截断：在字数上限附近找自然语言边界截断，不保护 scene 结构.

    090b-2: rewrite 后结构保护阻止截断时的回退策略。
    从后向前删除段落/句子，直到字数达标，并补省略号过渡。
    """
    current_wc = count_chinese_words(content)
    if current_wc <= max_words:
        return content

    # 策略 1：从后向前删除段落
    paragraphs = content.split("\n\n")
    while len(paragraphs) > 1:
        paragraphs.pop()
        candidate = "\n\n".join(paragraphs)
        if count_chinese_words(candidate) <= max_words:
            candidate = candidate.strip()
            if candidate and candidate[-1] not in "。！？…":
                candidate += "……"
            return candidate

    # 策略 2：只剩一个段落，从后向前删除句子
    para = paragraphs[0]
    sentences = re.split(r"(.*?[。！？…])", para, flags=re.DOTALL)
    sentence_parts: list[str] = []
    for s in sentences:
        if s.strip():
            sentence_parts.append(s)

    while len(sentence_parts) > 1:
        sentence_parts.pop()
        candidate = "".join(sentence_parts)
        if count_chinese_words(candidate) <= max_words:
            candidate = candidate.strip()
            if candidate and candidate[-1] not in "。！？…":
                candidate += "……"
            return candidate

    # 策略 3：单句就超过上限，无法截断
    return para



