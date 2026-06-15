"""Tests for ArcBoundaryResolver."""

from __future__ import annotations

import pytest

from songyan.agents.arc_boundary_resolver import ArcBoundaryResolver


class TestArcBoundaryResolver:
    """Arc boundary resolution tests."""

    @pytest.fixture
    def resolver(self) -> ArcBoundaryResolver:
        return ArcBoundaryResolver()

    def test_explicit_boundaries_first_arc(self, resolver: ArcBoundaryResolver) -> None:
        boundaries = [5, 10, 15]
        assert resolver.resolve(1, boundaries) == (1, 5)
        assert resolver.resolve(3, boundaries) == (1, 5)
        assert resolver.resolve(5, boundaries) == (1, 5)

    def test_explicit_boundaries_second_arc(self, resolver: ArcBoundaryResolver) -> None:
        boundaries = [5, 10, 15]
        assert resolver.resolve(6, boundaries) == (6, 10)
        assert resolver.resolve(8, boundaries) == (6, 10)
        assert resolver.resolve(10, boundaries) == (6, 10)

    def test_explicit_boundaries_third_arc(self, resolver: ArcBoundaryResolver) -> None:
        boundaries = [5, 10, 15]
        assert resolver.resolve(11, boundaries) == (11, 15)
        assert resolver.resolve(15, boundaries) == (11, 15)

    def test_explicit_boundaries_beyond_last(self, resolver: ArcBoundaryResolver) -> None:
        boundaries = [5, 10]
        assert resolver.resolve(16, boundaries) == (11, 20)

    def test_heuristic_default(self, resolver: ArcBoundaryResolver) -> None:
        assert resolver.resolve(1, None) == (1, 10)
        assert resolver.resolve(5, None) == (1, 10)
        assert resolver.resolve(10, None) == (1, 10)
        assert resolver.resolve(11, None) == (11, 20)
        assert resolver.resolve(25, None) == (21, 30)

    def test_heuristic_empty_list(self, resolver: ArcBoundaryResolver) -> None:
        assert resolver.resolve(3, []) == (1, 10)

    def test_list_boundaries_explicit(self, resolver: ArcBoundaryResolver) -> None:
        boundaries = [5, 10]
        result = resolver.list_boundaries(12, boundaries)
        assert result == [(1, 5), (6, 10), (11, 12)]

    def test_list_boundaries_heuristic(self, resolver: ArcBoundaryResolver) -> None:
        result = resolver.list_boundaries(25, None)
        assert result == [(1, 10), (11, 20), (21, 25)]

    def test_list_boundaries_exact_multiple(self, resolver: ArcBoundaryResolver) -> None:
        result = resolver.list_boundaries(20, None)
        assert result == [(1, 10), (11, 20)]

    def test_list_boundaries_single_chapter(self, resolver: ArcBoundaryResolver) -> None:
        result = resolver.list_boundaries(1, None)
        assert result == [(1, 1)]

    def test_list_boundaries_with_explicit_max(self, resolver: ArcBoundaryResolver) -> None:
        boundaries = [3, 7]
        result = resolver.list_boundaries(5, boundaries)
        assert result == [(1, 3), (4, 5)]
