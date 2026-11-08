"""M4 步 4 复读启发式（tech-m4 §4.4 / B8；tasks/241 钉死规格）。

纯代码检查器，移植 evals/excellence_signals.py 的复读检测（阈值原样：
``MIN_REPEAT_SENTENCE_LEN=12`` / 段落 ≥40 且 ≥2 次，见 excellence_signals.py:30,636-671）。
不 import evals 模块（evals 顶层有 DB/采样依赖），纯函数在此拷贝。

跨章腿为语义改写并写明理由：evals 原语义是「跨样本语料索引」（跨项目样本库），
不适配单项目逐章审；review 场景 = 与上一章（章号-1 的 accepted 正文）比对，
句归一化 ≥14 字符；无上一章 accepted 正文时由调用方跳过此腿并注明。
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Literal

from pydantic import BaseModel

from songyan.utils._helpers import locate_position, split_paragraphs, split_sentences

MIN_REPEAT_SENTENCE_LEN = 12
MIN_CROSS_CHAPTER_SENTENCE_LEN = 14
MIN_REPEAT_PARAGRAPH_LEN = 40
_MAX_HITS_PER_LEG = 5

_NORMALIZE_PATTERN = re.compile(r"[^\u4e00-\u9fffA-Za-z0-9]")
_SHORTEN_LIMIT = 120


class RepetitionHit(BaseModel):
    """一次复读命中：quote / 位置 / 次数。"""

    kind: Literal["sentence", "paragraph", "cross_chapter"]
    quote: str
    location: str
    count: int
    detail: str


def check_repetition(
    chapter_text: str,
    *,
    chapter: int,
    previous_accepted_text: str | None = None,
) -> list[RepetitionHit]:
    """逐章复读检查：句子腿 + 段落腿 + 跨章腿（上一章 accepted 比对）。"""
    hits = _repeated_sentences(chapter_text)
    hits.extend(_repeated_paragraphs(chapter_text))
    if previous_accepted_text:
        hits.extend(_cross_chapter_repetition(chapter_text, previous_accepted_text))
    return hits


def _normalize(text: str) -> str:
    return _NORMALIZE_PATTERN.sub("", text).lower()


def _shorten(text: str, limit: int = _SHORTEN_LIMIT) -> str:
    collapsed = re.sub(r"\s+", " ", text.strip())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 1] + "…"


def _repeated_sentences(chapter_text: str) -> list[RepetitionHit]:
    grouped: dict[str, list[str]] = {}
    for sentence in split_sentences(chapter_text):
        normalized = _normalize(sentence)
        if len(normalized) >= MIN_REPEAT_SENTENCE_LEN:
            grouped.setdefault(normalized, []).append(sentence.strip())
    hits: list[RepetitionHit] = []
    for sentences in grouped.values():
        if len(sentences) < 3:
            continue
        quote = sentences[0]
        hits.append(
            RepetitionHit(
                kind="sentence",
                quote=quote,
                location=locate_position(chapter_text, chapter_text.find(quote)),
                count=len(sentences),
                detail=f"同一句子逐字重复 {len(sentences)} 次",
            )
        )
    return hits[:_MAX_HITS_PER_LEG]


def _repeated_paragraphs(chapter_text: str) -> list[RepetitionHit]:
    grouped: dict[str, list[str]] = {}
    for paragraph in split_paragraphs(chapter_text):
        normalized = _normalize(paragraph)
        if len(normalized) >= MIN_REPEAT_PARAGRAPH_LEN:
            grouped.setdefault(normalized, []).append(paragraph.strip())
    hits: list[RepetitionHit] = []
    for paragraphs in grouped.values():
        if len(paragraphs) < 2:
            continue
        quote = paragraphs[0]
        hits.append(
            RepetitionHit(
                kind="paragraph",
                quote=_shorten(quote),
                location=locate_position(chapter_text, chapter_text.find(quote)),
                count=len(paragraphs),
                detail=f"同一长段落逐字重复 {len(paragraphs)} 次",
            )
        )
    return hits[:_MAX_HITS_PER_LEG]


def _cross_chapter_repetition(
    chapter_text: str,
    previous_accepted_text: str,
) -> list[RepetitionHit]:
    previous_counts: Counter[str] = Counter()
    for sentence in split_sentences(previous_accepted_text):
        normalized = _normalize(sentence)
        if len(normalized) >= MIN_CROSS_CHAPTER_SENTENCE_LEN:
            previous_counts[normalized] += 1

    hits: list[RepetitionHit] = []
    seen: set[str] = set()
    for sentence in split_sentences(chapter_text):
        normalized = _normalize(sentence)
        if normalized in seen or len(normalized) < MIN_CROSS_CHAPTER_SENTENCE_LEN:
            continue
        seen.add(normalized)
        count = previous_counts.get(normalized, 0)
        if count == 0:
            continue
        quote = sentence.strip()
        hits.append(
            RepetitionHit(
                kind="cross_chapter",
                quote=quote,
                location=locate_position(chapter_text, chapter_text.find(quote)),
                count=count,
                detail="与上一章 accepted 正文逐字重复（跨章复读）",
            )
        )
    return hits[:_MAX_HITS_PER_LEG]
