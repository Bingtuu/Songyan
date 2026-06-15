"""Tests for context compression (Task 025)."""

from __future__ import annotations

from songyan.agents.context_manager import _build_recent_plot
from songyan.models import ChapterSummary


class TestBuildRecentPlotTruncation:
    def test_summary_truncated_when_too_long(self) -> None:
        """超过 200 字符的 summary 应被截断."""
        long_summary = "A" * 300
        summaries = [
            ChapterSummary(chapter_number=1, summary=long_summary),
        ]
        recent_plot = _build_recent_plot(summaries)
        assert len(recent_plot.summaries) == 1
        assert len(recent_plot.summaries[0].summary) <= 203  # 200 + "..."
        assert recent_plot.summaries[0].summary.endswith("...")

    def test_summary_unchanged_when_short(self) -> None:
        """短 summary 不应被截断."""
        short_summary = "短摘要"
        summaries = [
            ChapterSummary(chapter_number=1, summary=short_summary),
        ]
        recent_plot = _build_recent_plot(summaries)
        assert recent_plot.summaries[0].summary == short_summary

    def test_multiple_summaries_all_truncated(self) -> None:
        """多个长 summary 都应被截断."""
        summaries = [
            ChapterSummary(chapter_number=1, summary="A" * 300),
            ChapterSummary(chapter_number=2, summary="B" * 300),
        ]
        recent_plot = _build_recent_plot(summaries)
        for s in recent_plot.summaries:
            assert len(s.summary) <= 203

    def test_key_events_preserved(self) -> None:
        """截断时不应丢失 key_events."""
        summaries = [
            ChapterSummary(
                chapter_number=1,
                summary="A" * 300,
                key_events=["事件1", "事件2"],
            ),
        ]
        recent_plot = _build_recent_plot(summaries)
        assert recent_plot.summaries[0].key_events == ["事件1", "事件2"]
