"""Task 037: Style Mimicry Engine 测试."""

from __future__ import annotations

import pytest

from songyan.agents.style_mimicry_engine import StyleMimicryEngine
from songyan.models import ContextPackage, StyleSample
from songyan.models.chapter import ChapterGoal
from songyan.models.context import RecentPlot

# ---------------------------------------------------------------------------
#  Layer 1: 模型测试
# ---------------------------------------------------------------------------


class TestStyleSample:
    """StyleSample 模型测试."""

    def test_minimal_instantiation(self) -> None:
        ss = StyleSample(work_name="测试")
        assert ss.work_name == "测试"
        assert ss.author == ""
        assert ss.confidence == 0.0

    def test_full_instantiation(self) -> None:
        ss = StyleSample(
            work_name="三体",
            author="刘慈欣",
            excerpt="宇宙很大，生活更大。",
            analysis="简洁、概念密集",
            genre_tags=["硬科幻"],
            confidence=0.95,
        )
        assert ss.confidence == 0.95
        assert ss.genre_tags == ["硬科幻"]

    def test_confidence_range(self) -> None:
        with pytest.raises(Exception):
            StyleSample(work_name="test", confidence=1.1)


class TestBuiltinLibrary:
    """内置风格样本库测试."""

    def test_has_five_samples(self) -> None:
        engine = StyleMimicryEngine()
        # 通过已知作品名反推内置库大小
        known = ["三体", "射雕英雄传", "长安十二时辰", "流浪地球", "雪中悍刀行"]
        for name in known:
            sample = engine.extract_style_sample(name)
            assert sample is not None, f"缺少内置样本: {name}"

    def test_builtin_confidence_high(self) -> None:
        engine = StyleMimicryEngine()
        sample = engine.extract_style_sample("三体")
        assert sample is not None
        assert sample.confidence >= 0.8


# ---------------------------------------------------------------------------
#  Layer 2: 模块测试
# ---------------------------------------------------------------------------


class TestExtractStyleSample:
    """extract_style_sample 方法测试."""

    def test_known_work_returns_preset(self) -> None:
        engine = StyleMimicryEngine()
        sample = engine.extract_style_sample("三体")
        assert sample is not None
        assert sample.work_name == "三体"
        assert sample.author == "刘慈欣"
        assert len(sample.excerpt) > 0
        assert len(sample.analysis) > 0

    def test_known_work_with_book_marks(self) -> None:
        engine = StyleMimicryEngine()
        sample = engine.extract_style_sample("《三体》")
        assert sample is not None
        assert sample.work_name == "三体"

    def test_unknown_work_returns_none(self) -> None:
        engine = StyleMimicryEngine()
        sample = engine.extract_style_sample("完全不存在的作品名")
        assert sample is None

    def test_text_fragment_heuristic(self) -> None:
        engine = StyleMimicryEngine()
        text = (
            "这是一个很长的文本片段。"
            "它包含了很多句子。"
            "每一句话都有自己的意思。"
            "我们可以用它来测试启发式提取。"
            "这个文本的长度肯定超过了五十个字。"
        )
        sample = engine.extract_style_sample(text)
        assert sample is not None
        assert sample.work_name == "自定义文本"
        assert sample.confidence == 0.5
        assert "句式节奏" in sample.analysis

    def test_short_text_returns_none(self) -> None:
        engine = StyleMimicryEngine()
        sample = engine.extract_style_sample("很短")
        assert sample is None


class TestInjectIntoContext:
    """inject_into_context 方法测试."""

    def test_inject_adds_soft_reference(self) -> None:
        engine = StyleMimicryEngine()
        sample = engine.extract_style_sample("三体")
        assert sample is not None

        ctx = ContextPackage(
            chapter_goal=ChapterGoal(chapter_number=1),
            recent_plot=RecentPlot(),
        )
        assert len(ctx.soft_references) == 0

        ctx = engine.inject_into_context(sample, ctx)
        assert len(ctx.soft_references) == 1

    def test_inject_reference_type(self) -> None:
        engine = StyleMimicryEngine()
        sample = engine.extract_style_sample("三体")
        assert sample is not None

        ctx = ContextPackage(
            chapter_goal=ChapterGoal(chapter_number=1),
            recent_plot=RecentPlot(),
        )
        ctx = engine.inject_into_context(sample, ctx)
        ref = ctx.soft_references[0]
        assert ref.type == "style_sample"
        assert ref.relevance_score == 0.9

    def test_inject_content_contains_work_name(self) -> None:
        import json as _json

        engine = StyleMimicryEngine()
        sample = engine.extract_style_sample("三体")
        assert sample is not None

        ctx = ContextPackage(
            chapter_goal=ChapterGoal(chapter_number=1),
            recent_plot=RecentPlot(),
        )
        ctx = engine.inject_into_context(sample, ctx)
        ref = ctx.soft_references[0]
        data = _json.loads(ref.content)
        assert data["work_name"] == "三体"
        assert data["author"] == "刘慈欣"
        assert "句式节奏" in data["analysis"]

    def test_inject_multiple(self) -> None:
        engine = StyleMimicryEngine()
        samples = [
            engine.extract_style_sample("三体"),
            engine.extract_style_sample("射雕英雄传"),
        ]
        samples = [s for s in samples if s is not None]

        ctx = ContextPackage(
            chapter_goal=ChapterGoal(chapter_number=1),
            recent_plot=RecentPlot(),
        )
        ctx = engine.inject_multiple(samples, ctx)
        assert len(ctx.soft_references) == 2


# ---------------------------------------------------------------------------
#  Layer 3: 集成测试
# ---------------------------------------------------------------------------


class TestContextManagerIntegration:
    """ContextManager 集成测试."""

    def test_assemble_with_style_samples(self) -> None:
        """提供 style_samples 时，soft_references 包含风格样本."""
        from songyan.agents.context_manager import assemble_context_package
        from songyan.models import (
            CreativeModeProfile,
            GenreProfile,
            ProjectSetting,
        )

        engine = StyleMimicryEngine()
        samples = [engine.extract_style_sample("三体")]
        samples = [s for s in samples if s is not None]

        ctx = assemble_context_package(
            chapter_goal=ChapterGoal(chapter_number=1),
            creative_brief=None,
            genre_profile=GenreProfile(id="scifi", name="科幻"),
            mode_profile=CreativeModeProfile(id="webnovel", name="网文"),
            project=ProjectSetting(
                genre_id="scifi",
                protagonist_name="测试",
            ),
            characters=[],
            character_states=[],
            recent_summaries=[],
            active_foreshadowings=[],
            setting_snapshots=[],
            style_samples=samples,
        )

        style_refs = [r for r in ctx.soft_references if r.type == "style_sample"]
        assert len(style_refs) >= 1
        assert "三体" in style_refs[0].content

    def test_assemble_without_style_samples(self) -> None:
        """不提供 style_samples 时，soft_references 不受影响."""
        from songyan.agents.context_manager import assemble_context_package
        from songyan.models import (
            CreativeModeProfile,
            GenreProfile,
            ProjectSetting,
        )

        ctx = assemble_context_package(
            chapter_goal=ChapterGoal(chapter_number=1),
            creative_brief=None,
            genre_profile=GenreProfile(id="scifi", name="科幻"),
            mode_profile=CreativeModeProfile(id="webnovel", name="网文"),
            project=ProjectSetting(
                genre_id="scifi",
                protagonist_name="测试",
            ),
            characters=[],
            character_states=[],
            recent_summaries=[],
            active_foreshadowings=[],
            setting_snapshots=[],
            style_samples=None,
        )

        style_refs = [r for r in ctx.soft_references if r.type == "style_sample"]
        assert len(style_refs) == 0

    def test_assemble_with_project_reference_works(self) -> None:
        """模拟从 project.reference_works 提取并注入的场景."""
        from songyan.agents.context_manager import assemble_context_package
        from songyan.models import (
            CreativeModeProfile,
            GenreProfile,
            ProjectSetting,
        )

        engine = StyleMimicryEngine()
        project = ProjectSetting(
            genre_id="scifi",
            protagonist_name="测试",
            reference_works=["三体", "流浪地球"],
        )
        samples = [
            s for s in (engine.extract_style_sample(w) for w in project.reference_works)
            if s is not None
        ]

        ctx = assemble_context_package(
            chapter_goal=ChapterGoal(chapter_number=1),
            creative_brief=None,
            genre_profile=GenreProfile(id="scifi", name="科幻"),
            mode_profile=CreativeModeProfile(id="webnovel", name="网文"),
            project=project,
            characters=[],
            character_states=[],
            recent_summaries=[],
            active_foreshadowings=[],
            setting_snapshots=[],
            style_samples=samples,
        )

        style_refs = [r for r in ctx.soft_references if r.type == "style_sample"]
        assert len(style_refs) == 2
        contents = " ".join(r.content for r in style_refs)
        assert "三体" in contents
        assert "流浪地球" in contents
