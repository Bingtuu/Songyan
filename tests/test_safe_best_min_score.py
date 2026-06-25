"""Tests for _safe_best_min_score boundary values (TS-01)."""

from __future__ import annotations

import pytest

from songyan.workflows._nodes import _safe_best_min_score


class TestSafeBestMinScore:
    """章节阶段感知的 safe-best 门槛边界值测试."""

    @pytest.mark.parametrize(
        ("chapter_number", "expected"),
        [
            (1, 0.75),
            (20, 0.75),
            (21, 0.78),
            (50, 0.78),
            (51, 0.82),
        ],
    )
    def test_boundary_values(self, chapter_number: int, expected: float) -> None:
        """验证各阶段边界返回正确的阈值."""
        assert _safe_best_min_score(chapter_number) == expected

    def test_early_chapter(self) -> None:
        """早期章节（<=20）门槛为 0.75."""
        assert _safe_best_min_score(10) == 0.75

    def test_mid_chapter(self) -> None:
        """中期章节（21-50）门槛为 0.78."""
        assert _safe_best_min_score(35) == 0.78

    def test_late_chapter(self) -> None:
        """后期章节（>50）门槛为 0.82."""
        assert _safe_best_min_score(100) == 0.82
