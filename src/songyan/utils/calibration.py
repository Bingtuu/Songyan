"""Calibration-window helpers."""

from __future__ import annotations


def min_word_count_for_chapter(chapter_number: int, word_count_target: int) -> int:
    """Return the effective lower word-count bound for a chapter."""
    if word_count_target <= 0:
        return 0
    baseline = int(word_count_target * 0.80)
    if 1 <= chapter_number <= 3 and word_count_target >= 2800:
        return max(baseline, int(word_count_target * 0.90))
    return baseline


def max_word_count_for_chapter(chapter_number: int, word_count_target: int) -> int:
    """Return the effective upper word-count bound for a chapter."""
    if word_count_target <= 0:
        return 0
    baseline = int(word_count_target * 1.20)
    if 1 <= chapter_number <= 3 and word_count_target >= 2800:
        return min(baseline, 3300)
    return baseline
