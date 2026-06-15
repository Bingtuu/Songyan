"""Fatigue-word detection — count over-used cliché phrases."""

from __future__ import annotations

import time

from songyan.models.review import FatigueWordMatch
from songyan.utils._helpers import locate_position


def detect_fatigue_words(text: str, fatigue_words: list[str]) -> list[FatigueWordMatch]:
    """Detect occurrences of *fatigue_words* in *text*.

    Each entry in *fatigue_words* may be a multi-character phrase.
    Returns a :class:`FatigueWordMatch` per distinct word with
    total count and every occurrence location.

    Complexity: O(k × n) where *k* is ``len(fatigue_words)`` and *n*
    is text length.  Runs in < 20 ms for a typical genre word list.
    """
    matches: list[FatigueWordMatch] = []

    for word in fatigue_words:
        if not word:
            continue

        locations: list[str] = []
        count = 0
        start = 0

        while True:
            idx = text.find(word, start)
            if idx == -1:
                break
            count += 1
            locations.append(locate_position(text, idx))
            start = idx + len(word)

        if count > 0:
            matches.append(
                FatigueWordMatch(
                    word=word,
                    count=count,
                    locations=locations,
                )
            )

    # Sort by descending count, then by word
    matches.sort(key=lambda x: (-x.count, x.word))
    return matches


def detect_fatigue_words_with_timing(
    text: str, fatigue_words: list[str]
) -> tuple[list[FatigueWordMatch], int]:
    """Run :func:`detect_fatigue_words` and return elapsed milliseconds."""
    start = time.perf_counter()
    result = detect_fatigue_words(text, fatigue_words)
    elapsed = int((time.perf_counter() - start) * 1000)
    return result, elapsed
