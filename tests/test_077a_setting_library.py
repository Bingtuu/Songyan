"""Task 077a: 分层 Setting 库 — 排序 + 入站过滤 单元测试."""

from __future__ import annotations

from songyan.agents.context_manager import (
    MAX_SETTING_INPUT,
)
from songyan.agents.context_manager._assemblers import (
    _build_soft_references,
    _calculate_dynamic_relevance,
    _compute_keyword_overlap,
    _extract_keywords,
    _is_setting_critical,
    _split_terms,
)
from songyan.models import ChapterGoal, NewSetting, SoftReference

# =============================================================================
# Helper: create test fixtures
# =============================================================================

def _make_goal(
    target_events: list[str] | None = None,
    hooks: list[str] | None = None,
    obligations: list[str] | None = None,
    chapter_type: str = "",
    chapter_number: int = 50,
) -> ChapterGoal:
    return ChapterGoal(
        chapter_number=chapter_number,
        target_events=target_events or [],
        hooks=hooks or [],
        obligations=obligations or [],
        chapter_type=chapter_type,
        word_count_target=3200,
    )


def _make_setting(name: str, desc: str = "", key: str = "", chapter: int = 0) -> NewSetting:
    return NewSetting(
        setting_name=name,
        description=desc or f"{name}的描述",
        source_quote=f"有关{name}的引用",
        setting_key=key or name,
        chapter_number=chapter,
    )


# =============================================================================
# _split_terms and _extract_keywords
# =============================================================================

class TestSplitTerms:
    def test_split_terms_simple(self) -> None:
        result = _split_terms("主角发现飞船残骸")
        assert "主角发现飞船残骸" in result

    def test_split_terms_with_punctuation(self) -> None:
        result = _split_terms("主角，发现飞船。神秘信号？")
        assert "主角" in result
        assert "发现飞船" in result
        assert "神秘信号" in result

    def test_split_terms_empty(self) -> None:
        assert _split_terms("  ") == []


class TestExtractKeywords:
    def test_from_target_events(self) -> None:
        goal = _make_goal(target_events=["主角调查飞船残骸", "与神秘势力首次接触"])
        kws = _extract_keywords(goal)
        assert len(kws) > 0

    def test_removes_stop_words(self) -> None:
        goal = _make_goal(target_events=["的"], hooks=["了"])
        kws = _extract_keywords(goal)
        for bad in ("的", "了", "在"):
            assert bad not in kws

    def test_deduplicates(self) -> None:
        goal = _make_goal(target_events=["飞船坠毁", "飞船坠毁再次"])
        kws = _extract_keywords(goal)
        assert len(kws) == len(set(kws))

    def test_includes_chapter_type(self) -> None:
        goal = _make_goal(chapter_type="高潮")
        kws = _extract_keywords(goal)
        assert "高潮" in kws


# =============================================================================
# _is_setting_critical
# =============================================================================

class TestIsSettingCritical:
    def test_setting_name_in_target_event(self) -> None:
        goal = _make_goal(target_events=["主角发现飞船残骸"])
        setting = _make_setting(name="飞船残骸")
        assert _is_setting_critical(setting, goal) is True

    def test_setting_key_in_obligation(self) -> None:
        goal = _make_goal(obligations=["必须提到星际联盟"])
        setting = _make_setting(name="星际", key="星际联盟")
        assert _is_setting_critical(setting, goal) is True

    def test_unrelated_setting_not_critical(self) -> None:
        goal = _make_goal(target_events=["主角调查飞船"])
        setting = _make_setting(name="森林精灵")
        assert _is_setting_critical(setting, goal) is False


# =============================================================================
# _compute_keyword_overlap
# =============================================================================

class TestComputeKeywordOverlap:
    def test_full_match(self) -> None:
        score = _compute_keyword_overlap("飞船残骸", "", ["飞船残骸", "主角"])
        assert score > 0

    def test_no_match(self) -> None:
        score = _compute_keyword_overlap("森林", "", ["飞船", "主角"])
        assert score == 0.0

    def test_empty_keywords(self) -> None:
        score = _compute_keyword_overlap("任意设定", "", [])
        assert score == 0.0

    def test_partial_match(self) -> None:
        score = _compute_keyword_overlap("飞船残骸", "", ["飞船残骸", "陌生信号", "神秘势力"])
        assert 0 < score < 1.0


# =============================================================================
# _build_soft_references
# =============================================================================

class TestBuildSoftReferences:
    def test_sets_last_mentioned_chapter(self) -> None:
        settings = [_make_setting("旧设定", chapter=1), _make_setting("新设定", chapter=50)]
        refs = _build_soft_references(settings, current_chapter=50)
        assert refs[0].last_mentioned_chapter is not None
        assert refs[0].last_mentioned_chapter <= refs[1].last_mentioned_chapter

    def test_sets_is_critical_from_chapter_goal(self) -> None:
        goal = _make_goal(target_events=["飞船残骸"])
        settings = [_make_setting("飞船残骸"), _make_setting("森林精灵")]
        refs = _build_soft_references(settings, current_chapter=50, chapter_goal=goal)
        assert refs[0].is_critical is True
        assert refs[1].is_critical is False

    def test_relevance_score_higher_for_critical(self) -> None:
        goal = _make_goal(target_events=["飞船残骸"])
        settings = [_make_setting("飞船残骸"), _make_setting("森林精灵")]
        refs = _build_soft_references(settings, current_chapter=50, chapter_goal=goal)
        assert refs[0].relevance_score >= 0.9
        assert refs[1].relevance_score < refs[0].relevance_score

    def test_single_setting_estimates_current_chapter(self) -> None:
        settings = [_make_setting("唯一设定", chapter=30)]
        refs = _build_soft_references(settings, current_chapter=30)
        assert refs[0].last_mentioned_chapter == 30

    def test_empty_settings(self) -> None:
        refs = _build_soft_references([])
        assert refs == []

    def test_without_chapter_goal_fallback(self) -> None:
        settings = [_make_setting("普通设定")]
        refs = _build_soft_references(settings, current_chapter=30)
        assert refs[0].is_critical is False
        assert refs[0].relevance_score == 0.7


# =============================================================================
# _calculate_dynamic_relevance
# =============================================================================

class TestCalculateDynamicRelevance:
    def _make_ref(self, last_chapter: int, is_critical: bool = False) -> SoftReference:
        return SoftReference(
            type="world_setting",
            content="飞船残骸: 废弃的飞船残骸",
            relevance_score=0.7,
            last_mentioned_chapter=last_chapter,
            is_critical=is_critical,
        )

    def test_time_decay_for_old_setting(self) -> None:
        ref = self._make_ref(last_chapter=5)
        score = _calculate_dynamic_relevance(ref, current_chapter=50, recent_chapters=[])
        assert score < 0.7

    def test_recent_setting_higher_score(self) -> None:
        old_ref = self._make_ref(last_chapter=5)
        new_ref = self._make_ref(last_chapter=48)
        old_score = _calculate_dynamic_relevance(old_ref, 50, [])
        new_score = _calculate_dynamic_relevance(new_ref, 50, [])
        assert new_score > old_score

    def test_critical_override(self) -> None:
        ref = self._make_ref(last_chapter=5, is_critical=True)
        score = _calculate_dynamic_relevance(ref, 50, [])
        assert score >= 0.9

    def test_recent_chapters_boost(self) -> None:
        ref = self._make_ref(last_chapter=48)
        score_without = _calculate_dynamic_relevance(ref, 50, [])
        score_with = _calculate_dynamic_relevance(ref, 50, [48])
        assert score_with >= score_without

    def test_with_keyword_overlap(self) -> None:
        ref = self._make_ref(last_chapter=48)
        goal = _make_goal(target_events=["飞船残骸"])
        score_no_goal = _calculate_dynamic_relevance(ref, 50, [48])
        score_with_goal = _calculate_dynamic_relevance(ref, 50, [48], chapter_goal=goal)
        assert score_with_goal >= score_no_goal

    def test_no_keyword_match_uses_only_time_decay(self) -> None:
        ref = self._make_ref(last_chapter=48)
        goal = _make_goal(target_events=["完全不相关的剧情"])
        score = _calculate_dynamic_relevance(ref, 50, [48], chapter_goal=goal)
        assert 0 < score < 1.0


# =============================================================================
# MAX_SETTING_INPUT constant
# =============================================================================

class TestMaxSettingInput:
    def test_constant_defined(self) -> None:
        assert MAX_SETTING_INPUT == 10
