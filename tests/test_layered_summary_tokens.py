"""Integration test: verify Ch30 token budget with layered summaries."""

from __future__ import annotations

from songyan.agents.context_manager import assemble_context_package
from songyan.agents.context_manager._assemblers import _build_recent_plot
from songyan.models import (
    ArcSummary,
    ChapterGoal,
    ChapterSummary,
    CreativeBrief,
    CreativeModeProfile,
    GenreProfile,
    ProjectSetting,
    VolumeSummary,
)
from songyan.utils.token_estimator import TokenEstimator


class TestLayeredSummaryTokenBudget:
    """验证分层加载后的 Token 预算."""

    def _make_chapter_summaries(self, count: int) -> list[ChapterSummary]:
        """生成 N 个精细摘要（每个 250 字）."""
        return [
            ChapterSummary(
                chapter_number=i,
                summary="x" * 250,
                key_events=["事件"],
                characters_appeared=["主角"],
            )
            for i in range(1, count + 1)
        ]

    def _make_arc_summaries(self, count: int) -> list[ChapterSummary]:
        """生成 N 个 Arc 摘要（每个 600 字）."""
        return [
            ChapterSummary(
                chapter_number=i * 10 + 1,
                summary="y" * 600,
                key_events=["弧事件"],
                characters_appeared=["主角"],
                source_type="arc",
            )
            for i in range(count)
        ]

    def _make_volume_summary(self) -> ChapterSummary:
        """生成 Volume 摘要（400 字）."""
        return ChapterSummary(
            chapter_number=0,
            summary="z" * 400,
            key_events=["重大揭示"],
            source_type="volume",
        )

    def test_recent_plot_tokens_reduced_with_layering(self) -> None:
        """分层加载后 recent_plot 的 token 数比纯精细加载少."""
        # 纯精细加载：30 章 × 250 字 = 7500 字
        fine_only = self._make_chapter_summaries(30)
        plot_fine = _build_recent_plot(fine_only)

        # 分层加载：3 章精细 + 2 Arc + 1 Volume
        # = 3×250 + 2×600 + 1×400 = 750 + 1200 + 400 = 2350 字
        layered = (
            self._make_chapter_summaries(3)
            + self._make_arc_summaries(2)
            + [self._make_volume_summary()]
        )
        plot_layered = _build_recent_plot(layered)

        estimator = TokenEstimator()
        tokens_fine = estimator.estimate_model(plot_fine)
        tokens_layered = estimator.estimate_model(plot_layered)

        # 分层加载应显著减少 token 数
        assert tokens_layered < tokens_fine
        # 具体数值验证（允许一定误差）
        assert tokens_layered < tokens_fine * 0.5

    def test_full_context_package_ch30_budget(self) -> None:
        """模拟 Ch30 场景，验证 ContextPackage token < 28800."""
        goal = ChapterGoal(
            chapter_number=30,
            target_events=["事件"],
            word_count_target=3000,
        )
        brief = CreativeBrief(
            mode_id="webnovel",
            chapter_goal=goal,
            creative_intent="测试",
            required_tensions=[],
        )
        genre = GenreProfile(
            id="scifi",
            name="科幻",
            writer_rules=[],
            fatigue_words=[],
        )
        mode = CreativeModeProfile(
            id="webnovel",
            name="网文",
        )
        project = ProjectSetting(
            genre_id="scifi",
            protagonist_name="主角",
        )

        # 分层加载的 recent_plot
        layered = (
            self._make_chapter_summaries(3)
            + self._make_arc_summaries(2)
            + [self._make_volume_summary()]
        )

        ctx = assemble_context_package(
            chapter_goal=goal,
            creative_brief=brief,
            genre_profile=genre,
            mode_profile=mode,
            project=project,
            characters=[],
            character_states=[],
            recent_summaries=layered,
            active_foreshadowings=[],
            setting_snapshots=[],
            arc_context=ArcSummary(
                arc_id="arc-3",
                start_chapter=21,
                end_chapter=30,
                arc_title="第三弧",
                arc_summary="a" * 500,
            ),
            volume_context=VolumeSummary(
                volume_id="vol-1",
                start_chapter=1,
                end_chapter=30,
                volume_title="第一卷",
                volume_summary="b" * 300,
            ),
        )

        # 验证 budget_used < 3.0
        assert ctx.budget_used < 3.0
        # 验证 estimated_tokens < 28800（3.0x × 8000 预算，但动态预算可能是 9600）
        # 按动态预算：chapter 30 属于 mid_chapters (11-50)，boost 20% → 9600
        # 3.0x × 9600 = 28800
        assert ctx.estimated_tokens < 28800
