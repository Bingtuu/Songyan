"""Tests for Task 086: Dynamic Budget + Genre Rules Grouping."""

from __future__ import annotations

from songyan.agents.context_manager._assemblers import (
    BUDGET_INCREMENT_PER_CHAPTER,
    DEFAULT_BASE_BUDGET,
    _build_genre_rules,
    _dynamic_budget,
)
from songyan.models import (
    ChapterGoal,
    GenreProfile,
    ProjectSetting,
)


class TestDynamicBudget:
    """验证动态预算公式: base + chapter_number * increment."""

    def test_chapter_1(self) -> None:
        assert _dynamic_budget(1) == 8080

    def test_chapter_50(self) -> None:
        assert _dynamic_budget(50) == 12000

    def test_chapter_70(self) -> None:
        assert _dynamic_budget(70) == 13600

    def test_chapter_100(self) -> None:
        assert _dynamic_budget(100) == 16000

    def test_custom_base_budget(self) -> None:
        """传入自定义 base_budget 时公式仍正确."""
        assert _dynamic_budget(50, base_budget=6000) == 6000 + 50 * 80

    def test_chapter_0(self) -> None:
        """第 0 章（边界）预算等于 base."""
        assert _dynamic_budget(0) == DEFAULT_BASE_BUDGET

    def test_constants(self) -> None:
        assert DEFAULT_BASE_BUDGET == 8000
        assert BUDGET_INCREMENT_PER_CHAPTER == 80


class TestGenreRulesByType:
    """验证 GenreProfile writer_rules_by_type 分组加载."""

    def _make_genre(self, writer_rules_by_type: dict | None = None) -> GenreProfile:
        return GenreProfile(
            id="test",
            name="Test",
            writer_rules=["default_rule_1", "default_rule_2"],
            writer_rules_by_type=writer_rules_by_type or {},
            fatigue_words=[],
            reviewer_focus=[],
            active_audit_dimensions=[],
        )

    def _make_project(self) -> ProjectSetting:
        return ProjectSetting(
            genre_id="test",
            mode_id="webnovel",
            protagonist_name="Test",
        )

    def test_grouped_rules_loaded(self) -> None:
        """chapter_type 匹配时加载分组规则."""
        genre = self._make_genre(
            writer_rules_by_type={
                "combat": ["combat_rule_1", "combat_rule_2"],
                "daily": ["daily_rule_1"],
            }
        )
        goal = ChapterGoal(chapter_number=1, chapter_type="combat")
        project = self._make_project()

        rules = _build_genre_rules(genre, project, goal)
        assert rules.writer_rules == ["combat_rule_1", "combat_rule_2"]

    def test_fallback_to_default_rules(self) -> None:
        """chapter_type 未在分组中定义时回退到 writer_rules."""
        genre = self._make_genre(
            writer_rules_by_type={
                "combat": ["combat_rule_1"],
            }
        )
        goal = ChapterGoal(chapter_number=1, chapter_type="unknown_type")
        project = self._make_project()

        rules = _build_genre_rules(genre, project, goal)
        assert rules.writer_rules == ["default_rule_1", "default_rule_2"]

    def test_empty_grouping_uses_default(self) -> None:
        """writer_rules_by_type 为空时回退到 writer_rules."""
        genre = self._make_genre(writer_rules_by_type={})
        goal = ChapterGoal(chapter_number=1, chapter_type="combat")
        project = self._make_project()

        rules = _build_genre_rules(genre, project, goal)
        assert rules.writer_rules == ["default_rule_1", "default_rule_2"]

    def test_no_chapter_type_uses_default(self) -> None:
        """chapter_type 为空字符串时回退到 writer_rules."""
        genre = self._make_genre(
            writer_rules_by_type={
                "combat": ["combat_rule_1"],
            }
        )
        goal = ChapterGoal(chapter_number=1, chapter_type="")
        project = self._make_project()

        rules = _build_genre_rules(genre, project, goal)
        assert rules.writer_rules == ["default_rule_1", "default_rule_2"]

    def test_case_insensitive_chapter_type(self) -> None:
        """chapter_type 大小写不敏感匹配."""
        genre = self._make_genre(
            writer_rules_by_type={
                "combat": ["combat_rule_1"],
            }
        )
        goal = ChapterGoal(chapter_number=1, chapter_type="COMBAT")
        project = self._make_project()

        rules = _build_genre_rules(genre, project, goal)
        assert rules.writer_rules == ["combat_rule_1"]

    def test_backward_compatibility_no_field(self) -> None:
        """旧 GenreProfile（无 writer_rules_by_type）向后兼容."""
        genre = GenreProfile(
            id="legacy",
            name="Legacy",
            writer_rules=["legacy_rule"],
        )
        goal = ChapterGoal(chapter_number=1, chapter_type="combat")
        project = self._make_project()

        rules = _build_genre_rules(genre, project, goal)
        assert rules.writer_rules == ["legacy_rule"]
