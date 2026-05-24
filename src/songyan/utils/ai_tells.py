"""AI-tell detection — identify AI-generated phrasing patterns in Chinese text."""

from __future__ import annotations

import re
import time

from songyan.models.review import AiTellMatch
from songyan.utils._helpers import locate_position

#: Common AI-tell regex patterns for Chinese web-novel prose.
AI_TELL_PATTERNS: list[tuple[str, str]] = [
    # Mechanical consciousness triggers
    (r"不禁.{0,10}(?:意识|想|觉|发现|明白|察觉|悟|到)", "机械意识触发"),
    (r"(?:突然|猛然|陡然|刹那间|一瞬间).{0,10}(?:意识|想|觉|发现|明白|察觉|悟|到)", "机械意识触发"),
    (r"(?:不知为何|不知怎的|不知什么时候).{0,10}(?:开始|已经|突然|莫名)", "机械意识触发"),
    # Excessive sensory description
    (r"眼中闪过一丝.{0,10}(?:寒芒|精光|杀意|异色|惊讶|疑惑|诧异|震惊)", "过度感官描写"),
    (r"眼中.{0,5}(?:寒芒|精光|杀意|异色).{0,5}(?:一闪|掠过|浮现)", "过度感官描写"),
    (r"一股.{0,10}涌上.{0,5}心头", "过度感官描写"),
    (r"内心深处.{0,10}(?:涌起|泛起|升起|浮现|回荡|响起)", "过度感官描写"),
    (r"(?:眼底|眸中|目光).{0,5}(?:闪过|掠过|浮现).{1,10}(?:情绪|光芒|异色)", "过度感官描写"),
    # Abstract emotions
    (r"心中.{0,5}五味杂陈", "抽象情感表达"),
    (r"某种难以名状的.{0,10}(?:感觉|情感|情绪|力量|气息|波动)", "抽象情感表达"),
    (r"下意识地.{0,10}(?:想|做|说|看|退|躲|挡|伸出手|握紧|松开)", "抽象情感表达"),
    (r"(?:莫名|莫名地|莫名其妙地).{0,5}(?:感到|觉得|产生|升起)", "抽象情感表达"),
    # Time-perception anomalies
    (r"仿佛时间.{0,5}(?:静止|凝固|停止|变慢|倒流)", "时间感知异常"),
    (r"一切都变得.{0,5}(?:缓慢|安静|模糊|清晰|虚幻|真实)", "时间感知异常"),
    (r"时间仿佛.{0,5}(?:静止|凝固|停止|变慢)", "时间感知异常"),
    (r"(?:周围|四周|世界).{0,5}(?:仿佛|好像).{0,5}(?:静止|凝固|定格)", "时间感知异常"),
    # Other AI clichés
    (r"一股暖流.{0,5}涌上心头", "AI 套路表达"),
    (r"(?:心中|心底|心里).{0,5}(?:一震|一颤|一紧|一沉|一松|一暖)", "AI 套路表达"),
    (r"(?:仿佛|好像).{0,5}看到了.{0,10}(?:画面|场景|景象|幻影|幻觉)", "AI 套路表达"),
    (
        r"(?:脑海中|脑中|脑海里).{0,5}(?:浮现|闪过|响起|回荡)"
        r".{0,10}(?:画面|声音|话语|记忆)",
        "AI 套路表达",
    ),
]


def detect_ai_tells(text: str) -> list[AiTellMatch]:
    """Detect AI-tell patterns in *text*.

    Returns a deduplicated list of :class:`AiTellMatch` ordered by
    appearance in the text.

    Complexity: O(n × m) where *n* is text length and *m* is the number
    of patterns.  For the built-in pattern set this runs in < 50 ms on
    a 3 000-character chapter.
    """
    matches: list[AiTellMatch] = []
    seen: set[tuple[int, int]] = set()

    for pattern, category in AI_TELL_PATTERNS:
        for m in re.finditer(pattern, text):
            key = (m.start(), m.end())
            if key in seen:
                continue
            seen.add(key)
            location = locate_position(text, m.start())
            matches.append(
                AiTellMatch(
                    pattern=f"{category}: {pattern}",
                    matched_text=m.group(),
                    location=location,
                )
            )

    # Sort by position in text for stable output
    matches.sort(key=lambda x: text.find(x.matched_text))
    return matches


def detect_ai_tells_with_timing(text: str) -> tuple[list[AiTellMatch], int]:
    """Run :func:`detect_ai_tells` and return elapsed milliseconds."""
    start = time.perf_counter()
    result = detect_ai_tells(text)
    elapsed = int((time.perf_counter() - start) * 1000)
    return result, elapsed
