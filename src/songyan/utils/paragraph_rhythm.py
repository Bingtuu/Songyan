"""Paragraph rhythm analysis — scoring paragraph length distribution."""

from __future__ import annotations

import re
import time

from pydantic import BaseModel, Field

from songyan.utils._helpers import split_paragraphs


class RhythmScore(BaseModel):
    """Paragraph rhythm metrics and overall score."""

    average_length: float = 0.0
    max_length: int = 0
    min_length: int = 0
    single_sentence_ratio: float = 0.0  # paragraphs < 20 chars
    ultra_long_ratio: float = 0.0  # paragraphs > 300 chars
    dialogue_ratio: float = 0.0  # paragraphs containing quotes
    score: float = 0.0  # 0-10
    issues: list[str] = Field(default_factory=list)


# Thresholds
_SINGLE_SENTENCE_THRESHOLD = 20
_ULTRA_LONG_THRESHOLD = 300
_OPTIMAL_AVG_MIN = 80
_OPTIMAL_AVG_MAX = 150
_OPTIMAL_DIALOGUE_MIN = 0.20
_OPTIMAL_DIALOGUE_MAX = 0.40


def _is_dialogue_paragraph(para: str) -> bool:
    """Return True if paragraph contains dialogue markers."""
    return bool(re.search(r"[\"\"''「『]", para))


def analyze_paragraph_rhythm(text: str) -> RhythmScore:
    """Analyze paragraph rhythm and return a scored assessment.

    Metrics:
    - Average paragraph length (optimal: 80-150 CJK chars)
    - Single-sentence paragraph ratio (optimal: < 15%)
    - Ultra-long paragraph ratio (optimal: < 10%)
    - Dialogue paragraph ratio (optimal: 20-40%)

    Score is 0-10, higher is better.

    Complexity: O(n) where n is text length.  < 30 ms for 3 000 chars.
    """
    paragraphs = split_paragraphs(text)
    total = len(paragraphs)

    if total == 0:
        return RhythmScore(
            score=0.0,
            issues=["文本为空或没有段落"],
        )

    lengths = [len(p) for p in paragraphs]
    avg_length = sum(lengths) / total
    max_len = max(lengths)
    min_len = min(lengths)

    single_count = sum(1 for ln in lengths if ln < _SINGLE_SENTENCE_THRESHOLD)
    ultra_count = sum(1 for ln in lengths if ln > _ULTRA_LONG_THRESHOLD)
    dialogue_count = sum(1 for p in paragraphs if _is_dialogue_paragraph(p))

    single_ratio = single_count / total
    ultra_ratio = ultra_count / total
    dialogue_ratio = dialogue_count / total

    issues: list[str] = []
    score = 0.0

    # 1. Average length score (0-4 points)
    if _OPTIMAL_AVG_MIN <= avg_length <= _OPTIMAL_AVG_MAX:
        score += 4.0
    elif avg_length < _OPTIMAL_AVG_MIN:
        deviation = (_OPTIMAL_AVG_MIN - avg_length) / _OPTIMAL_AVG_MIN
        score += max(0.0, 4.0 - deviation * 4.0)
        issues.append(f"平均段落过短 ({avg_length:.0f} 字，建议 80-150)")
    else:
        deviation = (avg_length - _OPTIMAL_AVG_MAX) / _OPTIMAL_AVG_MAX
        score += max(0.0, 4.0 - deviation * 4.0)
        issues.append(f"平均段落过长 ({avg_length:.0f} 字，建议 80-150)")

    # 2. Single-sentence ratio score (0-2 points)
    if single_ratio <= 0.15:
        score += 2.0
    else:
        score += max(0.0, 2.0 - (single_ratio - 0.15) * 10)
        issues.append(f"单句段落占比过高 ({single_ratio:.0%}，建议 <15%)")

    # 3. Ultra-long ratio score (0-2 points)
    if ultra_ratio <= 0.10:
        score += 2.0
    else:
        score += max(0.0, 2.0 - (ultra_ratio - 0.10) * 10)
        issues.append(f"超长段落占比过高 ({ultra_ratio:.0%}，建议 <10%)")

    # 4. Dialogue ratio score (0-2 points)
    if _OPTIMAL_DIALOGUE_MIN <= dialogue_ratio <= _OPTIMAL_DIALOGUE_MAX:
        score += 2.0
    elif dialogue_ratio < _OPTIMAL_DIALOGUE_MIN:
        score += max(0.0, 2.0 - (_OPTIMAL_DIALOGUE_MIN - dialogue_ratio) * 10)
        issues.append(f"对话段落占比过低 ({dialogue_ratio:.0%}，建议 20-40%)")
    else:
        score += max(0.0, 2.0 - (dialogue_ratio - _OPTIMAL_DIALOGUE_MAX) * 10)
        issues.append(f"对话段落占比过高 ({dialogue_ratio:.0%}，建议 20-40%)")

    return RhythmScore(
        average_length=round(avg_length, 1),
        max_length=max_len,
        min_length=min_len,
        single_sentence_ratio=round(single_ratio, 3),
        ultra_long_ratio=round(ultra_ratio, 3),
        dialogue_ratio=round(dialogue_ratio, 3),
        score=round(score, 2),
        issues=issues,
    )


def analyze_paragraph_rhythm_with_timing(text: str) -> tuple[RhythmScore, int]:
    """Run :func:`analyze_paragraph_rhythm` and return elapsed milliseconds."""
    start = time.perf_counter()
    result = analyze_paragraph_rhythm(text)
    elapsed = int((time.perf_counter() - start) * 1000)
    return result, elapsed
