"""M4 步 4 专名启发式（tech-m4 §4.4 / B8；tasks/241 钉死规格）。

纯函数 v1，可判定规格：
- 拉丁候选 = 连续 A-Za-z 且首字母大写串（≥2 字符）
- CJK 候选 = 出现 ≥3 次的 2-4 字 n-gram，减实现锁定的虚词小表
- 已登记集合由调用方组装（canon approved aliases ∪ 主角名 ∪ characters protagonist）
- 匹配 = 精确、大小写不敏感；命中 = info 级「未登记专名，考虑登记」，非错误
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Literal

from pydantic import BaseModel

from songyan.utils._helpers import locate_position

_LATIN_RUN = re.compile(r"[A-Za-z]+")
_CJK_RUN = re.compile(r"[一-鿿]+")

# 实现锁定的虚词小表（tasks/241 钉死，勿扩）。
_STOP_CHARS = frozenset("的了吗呢吧啊哦嗯在与把被让向从和及或等")

_MIN_LATIN_LEN = 2
_MIN_CJK_GRAM = 2
_MAX_CJK_GRAM = 4
_MIN_CJK_COUNT = 3

_DETAIL = "未登记专名，考虑登记"


class ProperNounHit(BaseModel):
    """一处未登记专名提示（info 级，非错误）。"""

    name: str
    kind: Literal["latin", "cjk"]
    location: str
    count: int
    detail: str = _DETAIL


def check_proper_nouns(
    chapter_text: str,
    *,
    chapter: int,
    registered: frozenset[str] | set[str],
) -> list[ProperNounHit]:
    """找出正文里未登记的专名候选；registered 匹配精确、大小写不敏感。"""
    registered_lower = {name.strip().lower() for name in registered if name and name.strip()}
    hits = _latin_hits(chapter_text, registered_lower)
    hits.extend(_cjk_hits(chapter_text, registered_lower))
    return hits


def _latin_hits(chapter_text: str, registered_lower: set[str]) -> list[ProperNounHit]:
    runs = [match.group(0) for match in _LATIN_RUN.finditer(chapter_text)]
    counts: Counter[str] = Counter(run.lower() for run in runs)
    hits: list[ProperNounHit] = []
    seen: set[str] = set()
    for run in runs:
        key = run.lower()
        if key in seen:
            continue
        seen.add(key)
        if len(run) < _MIN_LATIN_LEN or not run[0].isupper():
            continue
        if key in registered_lower:
            continue
        hits.append(
            ProperNounHit(
                name=run,
                kind="latin",
                location=locate_position(chapter_text, chapter_text.find(run)),
                count=counts[key],
            )
        )
    return hits


def _cjk_hits(chapter_text: str, registered_lower: set[str]) -> list[ProperNounHit]:
    counts: Counter[str] = Counter()
    for run in _CJK_RUN.findall(chapter_text):
        for size in range(_MIN_CJK_GRAM, _MAX_CJK_GRAM + 1):
            if len(run) < size:
                continue
            for start in range(len(run) - size + 1):
                counts[run[start : start + size]] += 1

    candidates = [
        (gram, count)
        for gram, count in counts.items()
        if count >= _MIN_CJK_COUNT and not (set(gram) & _STOP_CHARS)
    ]
    # 长词吸收其短子串候选，避免「黑潮会馆」与「黑潮」同时刷屏。
    kept: list[tuple[str, int]] = []
    for gram, count in sorted(candidates, key=lambda item: (-len(item[0]), item[0])):
        if any(gram in longer for longer, _ in kept):
            continue
        kept.append((gram, count))

    hits: list[ProperNounHit] = []
    for gram, count in sorted(kept, key=lambda item: (-len(item[0]), item[0])):
        if gram.lower() in registered_lower:
            continue
        hits.append(
            ProperNounHit(
                name=gram,
                kind="cjk",
                location=locate_position(chapter_text, chapter_text.find(gram)),
                count=count,
            )
        )
    return hits
