"""Arc boundary resolution — determine which arc a chapter belongs to."""

from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)

DEFAULT_ARC_SIZE = 10


class ArcBoundaryResolver:
    """Resolve chapter → arc boundaries.

    Priority:
    1. Explicit ``arc_boundaries`` config (e.g. [5, 10, 15])
    2. Heuristic: every ``DEFAULT_ARC_SIZE`` chapters
    """

    def resolve(
        self,
        chapter_number: int,
        arc_boundaries: list[int] | None = None,
    ) -> tuple[int, int]:
        """Return the (start_chapter, end_chapter) for *chapter_number*.

        Args:
            chapter_number: 1-based chapter number.
            arc_boundaries: Ordered list of end-chapter numbers for each arc.
                e.g. [5, 10] means Arc1=1-5, Arc2=6-10.

        Returns:
            Tuple of (start_chapter, end_chapter).
        """
        boundaries = arc_boundaries or []
        if boundaries:
            start = 1
            for end in boundaries:
                if chapter_number <= end:
                    return (start, end)
                start = end + 1
            # Beyond last explicit boundary → open-ended next arc
            return (start, start + DEFAULT_ARC_SIZE - 1)

        # Heuristic fallback
        start = ((chapter_number - 1) // DEFAULT_ARC_SIZE) * DEFAULT_ARC_SIZE + 1
        end = start + DEFAULT_ARC_SIZE - 1
        return (start, end)

    def list_boundaries(
        self,
        max_chapter: int,
        arc_boundaries: list[int] | None = None,
    ) -> list[tuple[int, int]]:
        """List all (start, end) arcs up to *max_chapter*.

        Args:
            max_chapter: Highest chapter number to cover.
            arc_boundaries: Explicit boundaries or None for heuristic.

        Returns:
            List of (start_chapter, end_chapter) tuples.
        """
        boundaries = arc_boundaries or []
        if not boundaries:
            # Heuristic: every DEFAULT_ARC_SIZE chapters
            result: list[tuple[int, int]] = []
            start = 1
            while start <= max_chapter:
                end = min(start + DEFAULT_ARC_SIZE - 1, max_chapter)
                result.append((start, end))
                start = end + 1
            return result

        result = []
        start = 1
        for end in boundaries:
            if start > max_chapter:
                break
            actual_end = min(end, max_chapter)
            result.append((start, actual_end))
            start = end + 1
        # Cover remaining chapters beyond last boundary
        if start <= max_chapter:
            result.append((start, max_chapter))
        return result
