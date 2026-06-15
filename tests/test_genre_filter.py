"""Tests for genre_rules on-demand loading — Task 067."""

from __future__ import annotations

import pytest

from songyan.agents.context_manager._genre_filter import filter_genre_profile
from songyan.models.chapter import ChapterGoal
from songyan.models.genre import GenreProfile


@pytest.fixture
def sample_genre() -> GenreProfile:
    return GenreProfile(
        id="scifi",
        name="科幻",
        writer_rules=[
            "科技设定必须基于科学原理",
            "技术细节服务剧情",
        ],
        reviewer_focus=[
            "科技设定是否前后一致",
            "世界观信息是否自然带出",
            "时间线与因果关系是否清晰",
            "战斗节奏是否紧凑",
        ],
        satisfaction_types=[
            "科技突破",
            "危机化解",
            "真相揭露",
            "文明碰撞",
            "生存逆袭",
            "日常温馨",
        ],
        taboos=["科技设定随意吃书"],
    )


class TestFilterGenreProfile:
    def test_combat_type_filters_to_battle_focus(self, sample_genre: GenreProfile) -> None:
        """战斗类型只保留战斗相关的 reviewer_focus."""
        goal = ChapterGoal(chapter_number=1, chapter_type="combat")
        filtered = filter_genre_profile(sample_genre, goal)

        # "战斗节奏是否紧凑" 应保留
        assert any("战斗" in f for f in filtered.reviewer_focus)
        # 过滤后至少保留 MIN_RETAIN (2) 条
        assert len(filtered.reviewer_focus) >= 2

    def test_daily_type_filters_to_character_focus(self, sample_genre: GenreProfile) -> None:
        """日常类型只保留角色/情感相关的 reviewer_focus."""
        goal = ChapterGoal(chapter_number=1, chapter_type="daily")
        filtered = filter_genre_profile(sample_genre, goal)

        # "世界观信息是否自然带出" 含"自然"，与日常相关
        assert len(filtered.reviewer_focus) >= 2

    def test_twist_type_filters_to_plot_focus(self, sample_genre: GenreProfile) -> None:
        """转折类型只保留悬念/真相相关的 reviewer_focus."""
        goal = ChapterGoal(chapter_number=1, chapter_type="twist")
        filtered = filter_genre_profile(sample_genre, goal)

        # "真相揭露"相关的 focus 应保留
        assert any("清晰" in f or "因果" in f for f in filtered.reviewer_focus)
        assert len(filtered.reviewer_focus) >= 2

    def test_unknown_type_preserves_all(self, sample_genre: GenreProfile) -> None:
        """未知 chapter_type 不过滤."""
        goal = ChapterGoal(chapter_number=1, chapter_type="unknown")
        filtered = filter_genre_profile(sample_genre, goal)

        assert len(filtered.reviewer_focus) == 4
        assert len(filtered.satisfaction_types) == 6

    def test_no_chapter_type_preserves_all(self, sample_genre: GenreProfile) -> None:
        """空 chapter_type 不过滤."""
        goal = ChapterGoal(chapter_number=1, chapter_type="")
        filtered = filter_genre_profile(sample_genre, goal)

        assert len(filtered.reviewer_focus) == 4
        assert len(filtered.satisfaction_types) == 6

    def test_satisfaction_types_filtered(self, sample_genre: GenreProfile) -> None:
        """satisfaction_types 也按 chapter_type 过滤."""
        goal = ChapterGoal(chapter_number=1, chapter_type="combat")
        filtered = filter_genre_profile(sample_genre, goal)

        # 战斗类型应保留"危机化解""生存逆袭"
        assert any("危机" in s for s in filtered.satisfaction_types)
        assert any("生存" in s for s in filtered.satisfaction_types)
        assert len(filtered.satisfaction_types) >= 2

    def test_writer_rules_not_filtered(self, sample_genre: GenreProfile) -> None:
        """writer_rules 不过滤（通用规则）."""
        goal = ChapterGoal(chapter_number=1, chapter_type="combat")
        filtered = filter_genre_profile(sample_genre, goal)

        assert len(filtered.writer_rules) == 2

    def test_taboos_not_filtered(self, sample_genre: GenreProfile) -> None:
        """taboos 不过滤（硬约束）."""
        goal = ChapterGoal(chapter_number=1, chapter_type="combat")
        filtered = filter_genre_profile(sample_genre, goal)

        assert len(filtered.taboos) == 1

    def test_less_than_min_retain_falls_back(self) -> None:
        """过滤后少于 MIN_RETAIN 时回退到全部保留."""
        genre = GenreProfile(
            id="test",
            name="测试",
            reviewer_focus=[
                "只有一条完全无关的规则",
            ],
        )
        goal = ChapterGoal(chapter_number=1, chapter_type="combat")
        filtered = filter_genre_profile(genre, goal)

        # 回退到全部保留
        assert len(filtered.reviewer_focus) == 1

    def test_does_not_modify_original(self, sample_genre: GenreProfile) -> None:
        """过滤返回副本，不修改原对象."""
        original_focus_count = len(sample_genre.reviewer_focus)
        goal = ChapterGoal(chapter_number=1, chapter_type="combat")
        filter_genre_profile(sample_genre, goal)

        assert len(sample_genre.reviewer_focus) == original_focus_count
