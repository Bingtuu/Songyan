"""Task 038: Writer Prompt 风格注入测试."""

from __future__ import annotations

from songyan.agents.writer import _render_prompt
from songyan.models import (
    ContextPackage,
    GenreRules,
    ModeRules,
    SoftReference,
)
from songyan.models.chapter import ChapterGoal
from songyan.models.context import RecentPlot
from songyan.models.genre import StyleBaseline

# ---------------------------------------------------------------------------
#  helpers
# ---------------------------------------------------------------------------


def _make_ctx(
    chapter_type: str = "opening",
    style_baseline: StyleBaseline | None = None,
    style_samples: list[SoftReference] | None = None,
    pacing_templates: list[dict] | None = None,
    sensory_templates: list[dict] | None = None,
    fatigue_words: list[str] | None = None,
) -> ContextPackage:
    """快速构建 ContextPackage."""
    return ContextPackage(
        chapter_goal=ChapterGoal(
            chapter_number=1,
            chapter_type=chapter_type,
            target_events=["测试事件"],
        ),
        creative_brief=None,
        genre_rules=GenreRules(
            genre_id="test",
            writer_rules=["规则1"],
            fatigue_words=fatigue_words or [],
            pacing_rule="测试节奏",
            style_baseline=style_baseline,
            pacing_templates=pacing_templates or [],
            sensory_templates=sensory_templates or [],
        ),
        mode_rules=ModeRules(mode_id="webnovel"),
        soft_references=style_samples or [],
        recent_plot=RecentPlot(),
    )


# ---------------------------------------------------------------------------
#  Layer 1 & 2: Prompt 渲染测试
# ---------------------------------------------------------------------------


class TestStyleBaselineRendering:
    """style_baseline 分区渲染测试."""

    def test_with_style_baseline(self) -> None:
        sb = StyleBaseline(
            sentence_rhythm="短促有力",
            description_density=0.35,
            dialogue_ratio=0.25,
            inner_monologue="克制",
            pov_depth="中",
        )
        ctx = _make_ctx(style_baseline=sb)
        prompt = _render_prompt(ctx)
        assert "风格基线参考" in prompt
        assert "短促有力" in prompt
        assert "0.35" in prompt
        assert "克制" in prompt

    def test_without_style_baseline(self) -> None:
        ctx = _make_ctx(style_baseline=None)
        prompt = _render_prompt(ctx)
        assert "风格基线参考" not in prompt


class TestStyleSamplesRendering:
    """style_samples 分区渲染测试."""

    def test_with_style_sample(self) -> None:
        ref = SoftReference(
            type="style_sample",
            content=(
                "【风格参考：三体（刘慈欣）】\n"
                "代表性段落：宇宙很大。\n"
                "风格特征：简洁、概念密集"
            ),
            relevance_score=0.9,
        )
        ctx = _make_ctx(style_samples=[ref])
        prompt = _render_prompt(ctx)
        assert "参考作品风格" in prompt
        assert "三体" in prompt
        assert "刘慈欣" in prompt

    def test_without_style_samples(self) -> None:
        ctx = _make_ctx(style_samples=[])
        prompt = _render_prompt(ctx)
        assert "参考作品风格" not in prompt


class TestPacingTemplateRendering:
    """pacing_template 分区渲染测试."""

    def test_matching_chapter_type(self) -> None:
        pts = [
            {
                "chapter_types": ["opening"],
                "emotion_arc": "觉醒",
                "punch_density": 2.0,
                "info_release_strategy": "快速",
            },
            {
                "chapter_types": ["combat"],
                "emotion_arc": "搏杀",
                "punch_density": 3.0,
                "info_release_strategy": "激烈",
            },
        ]
        ctx = _make_ctx(chapter_type="opening", pacing_templates=pts)
        prompt = _render_prompt(ctx)
        assert "当前章节节奏模板" in prompt
        assert "觉醒" in prompt
        assert "2.0" in prompt

    def test_fallback_to_first(self) -> None:
        pts = [
            {
                "chapter_types": ["combat"],
                "emotion_arc": "搏杀",
                "punch_density": 3.0,
                "info_release_strategy": "激烈",
            },
        ]
        ctx = _make_ctx(chapter_type="unknown", pacing_templates=pts)
        prompt = _render_prompt(ctx)
        assert "当前章节节奏模板" in prompt
        assert "搏杀" in prompt

    def test_without_pacing_templates(self) -> None:
        ctx = _make_ctx(pacing_templates=[])
        prompt = _render_prompt(ctx)
        assert "当前章节节奏模板" not in prompt


class TestSensoryFocusRendering:
    """sensory_focus 分区渲染测试."""

    def test_with_sensory_templates(self) -> None:
        sts = [
            {
                "sense": "visual",
                "intensity_target": 0.8,
                "description_density": 100.0,
                "example_phrases": ["光芒万丈"],
            },
            {
                "sense": "pain",
                "intensity_target": 0.7,
                "description_density": 80.0,
                "example_phrases": ["剧痛"],
            },
        ]
        ctx = _make_ctx(sensory_templates=sts)
        prompt = _render_prompt(ctx)
        assert "感官描写侧重" in prompt
        assert "visual" in prompt
        assert "pain" in prompt

    def test_without_sensory_templates(self) -> None:
        ctx = _make_ctx(sensory_templates=[])
        prompt = _render_prompt(ctx)
        assert "感官描写侧重" not in prompt


class TestFatigueWordsCoverage:
    """fatigue_words 覆盖 7 类重复短语模式."""

    def test_scifi_covers_seven_patterns(self) -> None:
        from songyan.genres.loader import load_genre_profile

        profile = load_genre_profile("scifi")
        words = profile.fatigue_words
        # 检查 7 类模式覆盖（至少有一个关键词匹配）
        assert any("盯" in w for w in words), "缺少'盯着看'类"
        assert any("低声" in w for w in words), "缺少'低声说'类"
        assert any(w in words for w in ["僵住了", "停住了"]), "缺少'僵/停住了'类"
        assert any("呼吸" in w for w in words), "缺少'呼吸'类"
        assert any("自言" in w for w in words), "缺少'自言自语'类"
        assert any("喃喃" in w for w in words), "缺少'喃喃自语'类"

    def test_all_genres_have_minimum_fatigue_words(self) -> None:
        from songyan.genres.loader import load_genre_profile

        genres = [
            "scifi", "urban", "urban_fantasy", "post_apocalyptic",
            "mystery_noir", "wuxia", "xuanhuan",
        ]
        for gid in genres:
            profile = load_genre_profile(gid)
            assert len(profile.fatigue_words) >= 10, f"{gid} 疲劳词不足"


# ---------------------------------------------------------------------------
#  Layer 3: 集成测试
# ---------------------------------------------------------------------------


class TestCrossGenrePromptDifference:
    """跨 genre prompt 内容差异测试."""

    def test_scifi_vs_xuanhuan_prompt_diff(self) -> None:
        from songyan.genres.loader import load_genre_profile

        scifi = load_genre_profile("scifi")
        xuanhuan = load_genre_profile("xuanhuan")

        ctx_scifi = _make_ctx(
            style_baseline=scifi.style_baseline,
            pacing_templates=[pt.model_dump() for pt in scifi.pacing_templates],
            sensory_templates=[st.model_dump() for st in scifi.sensory_templates],
            fatigue_words=scifi.fatigue_words,
        )
        ctx_xuanhuan = _make_ctx(
            style_baseline=xuanhuan.style_baseline,
            pacing_templates=[pt.model_dump() for pt in xuanhuan.pacing_templates],
            sensory_templates=[st.model_dump() for st in xuanhuan.sensory_templates],
            fatigue_words=xuanhuan.fatigue_words,
        )

        prompt_scifi = _render_prompt(ctx_scifi)
        prompt_xuanhuan = _render_prompt(ctx_xuanhuan)

        assert prompt_scifi != prompt_xuanhuan
        # scifi 的 style_baseline 是"错落有致"，xuanhuan 是"短促有力"
        assert "错落有致" in prompt_scifi
        assert "短促有力" in prompt_xuanhuan
