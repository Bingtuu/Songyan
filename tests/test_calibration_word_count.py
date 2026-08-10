"""Tests for Ch1-Ch3 calibration word-count helpers."""

from __future__ import annotations

from songyan.utils.calibration import (
    max_word_count_for_chapter,
    min_word_count_for_chapter,
)


def test_ch1_3_use_ten_percent_lower_bound_for_3000_target() -> None:
    assert min_word_count_for_chapter(1, 3000) == 2700
    assert min_word_count_for_chapter(2, 3000) == 2700
    assert min_word_count_for_chapter(3, 3000) == 2700
    assert max_word_count_for_chapter(1, 3000) == 3300
    assert max_word_count_for_chapter(2, 3000) == 3300
    assert max_word_count_for_chapter(3, 3000) == 3300


def test_later_chapters_use_standard_eighty_percent_lower_bound() -> None:
    assert min_word_count_for_chapter(4, 3000) == 2400
    assert max_word_count_for_chapter(4, 3000) == 3600


def test_small_targets_do_not_raise_to_calibration_floor() -> None:
    assert min_word_count_for_chapter(1, 1000) == 800
