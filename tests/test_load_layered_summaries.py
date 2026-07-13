"""Tests for load_layered_summaries and _build_recent_plot source_type handling."""

from __future__ import annotations

import pytest

from songyan.agents.context_manager._assemblers import _build_recent_plot
from songyan.db.context_repo import SummaryRepository
from songyan.db.layered_context_repo import ArcSummaryRepository, VolumeSummaryRepository
from songyan.db.repository import ProjectRepository
from songyan.models import ArcSummary, ChapterSummary, ProjectSetting, VolumeSummary
from songyan.workflows._helpers import load_layered_summaries

pytestmark = pytest.mark.performance


async def _seed_project(project_id: str) -> None:
    await ProjectRepository().create(
        ProjectSetting(
            title="测试项目",
            genre_id="scifi",
            mode_id="webnovel",
            protagonist_name="主角",
        ),
        project_id,
    )


class TestLoadLayeredSummaries:
    """分层加载摘要测试."""

    @pytest.mark.asyncio
    async def test_only_recent_when_no_arc_volume(self, test_db) -> None:
        """没有 Arc/Volume 时只返回最近 5 章（Task 101: 从 3 改为 5）."""
        project_id = "proj-layer-1"
        await _seed_project(project_id)

        repo = SummaryRepository()
        for i in range(1, 8):
            s = ChapterSummary(
                chapter_number=i,
                summary=f"第{i}章摘要",
                key_events=[f"事件{i}"],
            )
            await repo.create(s, project_id, f"sum-{i}")

        result = await load_layered_summaries(project_id, current_chapter=8)

        assert len(result) == 5
        assert all(s.source_type == "chapter" for s in result)
        assert result[0].chapter_number == 3
        assert result[1].chapter_number == 4
        assert result[2].chapter_number == 5
        assert result[3].chapter_number == 6
        assert result[4].chapter_number == 7

    @pytest.mark.asyncio
    async def test_includes_arc_when_available(self, test_db) -> None:
        """有 Arc 摘要时混入单个最近已完成弧（Task 101: 金字塔分层）."""
        project_id = "proj-layer-2"
        await _seed_project(project_id)

        # 插入 summaries
        repo = SummaryRepository()
        for i in range(1, 16):
            s = ChapterSummary(chapter_number=i, summary=f"第{i}章摘要")
            await repo.create(s, project_id, f"sum-{i}")

        # 插入 Arc 摘要
        arc_repo = ArcSummaryRepository()
        arc = ArcSummary(
            arc_id="arc-1",
            start_chapter=1,
            end_chapter=10,
            arc_title="觉醒篇",
            arc_summary="主角觉醒的弧",
            key_events=["觉醒"],
            character_arcs={"主角": "从普通人到觉醒者"},
        )
        await arc_repo.create(arc, project_id)

        result = await load_layered_summaries(project_id, current_chapter=15)

        # 最近 5 章 + 最近一个已完成弧
        types = [s.source_type for s in result]
        assert "chapter" in types
        assert "arc" in types

        # 精细层：11, 12, 13, 14, 15
        chapters = [s for s in result if s.source_type == "chapter"]
        assert len(chapters) == 5
        assert chapters[0].chapter_number == 11

        # Arc 层：只取最近一个已完成弧
        arcs = [s for s in result if s.source_type == "arc"]
        assert len(arcs) == 1
        assert arcs[0].chapter_number == 1
        assert "觉醒篇" in arcs[0].summary or "主角觉醒" in arcs[0].summary

    @pytest.mark.asyncio
    async def test_skips_arc_fully_covered_by_recent(self, test_db) -> None:
        """与精细层完全重叠的 Arc 被跳过."""
        project_id = "proj-layer-3"
        await _seed_project(project_id)

        repo = SummaryRepository()
        for i in range(28, 31):
            s = ChapterSummary(chapter_number=i, summary=f"第{i}章摘要")
            await repo.create(s, project_id, f"sum-{i}")

        arc_repo = ArcSummaryRepository()
        arc = ArcSummary(
            arc_id="arc-3",
            start_chapter=28,
            end_chapter=30,
            arc_title="结尾篇",
            arc_summary="结尾",
        )
        await arc_repo.create(arc, project_id)

        result = await load_layered_summaries(project_id, current_chapter=31)

        # 精细层覆盖了 28-30，Arc 完全被覆盖 → 跳过
        arcs = [s for s in result if s.source_type == "arc"]
        assert len(arcs) == 0

    @pytest.mark.asyncio
    async def test_includes_volume_when_available(self, test_db) -> None:
        """有 Volume 摘要时混入历史卷（Task 101: 只加载 end_chapter < current 的卷）."""
        project_id = "proj-layer-4"
        await _seed_project(project_id)

        repo = SummaryRepository()
        for i in range(1, 8):
            s = ChapterSummary(chapter_number=i, summary=f"第{i}章摘要")
            await repo.create(s, project_id, f"sum-{i}")

        vol_repo = VolumeSummaryRepository()
        # 第一卷在 Ch4 结束，对 current_chapter=6 来说是历史卷
        vol = VolumeSummary(
            volume_id="vol-1",
            start_chapter=1,
            end_chapter=4,
            volume_title="第一卷",
            volume_summary="全篇宏观摘要",
        )
        await vol_repo.create(vol, project_id)

        result = await load_layered_summaries(project_id, current_chapter=6)

        volumes = [s for s in result if s.source_type == "volume"]
        assert len(volumes) == 1
        assert volumes[0].chapter_number == 0
        assert "全篇宏观摘要" in volumes[0].summary

    @pytest.mark.asyncio
    async def test_sorted_by_chapter_number(self, test_db) -> None:
        """结果按 chapter_number 排序."""
        project_id = "proj-layer-5"
        await _seed_project(project_id)

        repo = SummaryRepository()
        for i in range(1, 16):
            s = ChapterSummary(chapter_number=i, summary=f"第{i}章摘要")
            await repo.create(s, project_id, f"sum-{i}")

        arc_repo = ArcSummaryRepository()
        arc = ArcSummary(
            arc_id="arc-1",
            start_chapter=1,
            end_chapter=10,
            arc_title="觉醒篇",
            arc_summary="觉醒",
        )
        await arc_repo.create(arc, project_id)

        # 历史卷：end_chapter < current_chapter
        vol_repo = VolumeSummaryRepository()
        vol = VolumeSummary(
            volume_id="vol-1",
            start_chapter=1,
            end_chapter=8,
            volume_title="第一卷",
            volume_summary="宏观",
        )
        await vol_repo.create(vol, project_id)

        result = await load_layered_summaries(project_id, current_chapter=15)

        chapter_numbers = [s.chapter_number for s in result]
        assert chapter_numbers == sorted(chapter_numbers)
        assert chapter_numbers[0] == 0  # Volume


class TestBuildRecentPlotSourceType:
    """_build_recent_plot 按 source_type 使用不同截断长度."""

    def test_chapter_truncated_to_120(self) -> None:
        s = ChapterSummary(
            chapter_number=1,
            summary="x" * 300,
            source_type="chapter",
        )
        plot = _build_recent_plot([s])
        assert len(plot.summaries[0].summary) == 123  # 120 + "..."

    def test_arc_truncated_to_280(self) -> None:
        s = ChapterSummary(
            chapter_number=1,
            summary="x" * 700,
            source_type="arc",
        )
        plot = _build_recent_plot([s])
        assert len(plot.summaries[0].summary) == 283  # 280 + "..."

    def test_volume_truncated_to_180(self) -> None:
        s = ChapterSummary(
            chapter_number=0,
            summary="x" * 500,
            source_type="volume",
        )
        plot = _build_recent_plot([s])
        assert len(plot.summaries[0].summary) == 183  # 180 + "..."

    def test_mixed_sources_preserved(self) -> None:
        summaries = [
            ChapterSummary(chapter_number=0, summary="vol", source_type="volume"),
            ChapterSummary(chapter_number=1, summary="arc", source_type="arc"),
            ChapterSummary(chapter_number=2, summary="ch", source_type="chapter"),
        ]
        plot = _build_recent_plot(summaries)
        assert [s.source_type for s in plot.summaries] == ["volume", "arc", "chapter"]


class TestTemporalCompressor:
    """Task 101: 金字塔分层策略验证."""

    @pytest.mark.asyncio
    async def test_only_single_arc_loaded(self, test_db) -> None:
        """即使存在多个历史弧，也只加载最近一个已完成弧."""
        project_id = "proj-tc-1"
        await _seed_project(project_id)

        repo = SummaryRepository()
        for i in range(1, 26):
            s = ChapterSummary(chapter_number=i, summary=f"第{i}章摘要")
            await repo.create(s, project_id, f"sum-{i}")

        arc_repo = ArcSummaryRepository()
        # 两个已完成弧
        arc1 = ArcSummary(
            arc_id="arc-1", start_chapter=1, end_chapter=10,
            arc_title="弧1", arc_summary="摘要1",
        )
        arc2 = ArcSummary(
            arc_id="arc-2", start_chapter=11, end_chapter=20,
            arc_title="弧2", arc_summary="摘要2",
        )
        await arc_repo.create(arc1, project_id)
        await arc_repo.create(arc2, project_id)

        result = await load_layered_summaries(project_id, current_chapter=25)

        arcs = [s for s in result if s.source_type == "arc"]
        assert len(arcs) == 1
        # 只取最近一个已完成弧 (11-20)
        assert arcs[0].chapter_number == 11
        assert "摘要2" in arcs[0].summary

    @pytest.mark.asyncio
    async def test_skips_current_arc(self, test_db) -> None:
        """current_chapter 所在的未完成弧（end_chapter >= current）不被加载."""
        project_id = "proj-tc-2"
        await _seed_project(project_id)

        repo = SummaryRepository()
        for i in range(1, 16):
            s = ChapterSummary(chapter_number=i, summary=f"第{i}章摘要")
            await repo.create(s, project_id, f"sum-{i}")

        arc_repo = ArcSummaryRepository()
        # 当前弧包含 current_chapter=15（end=15 不小于 15）
        arc_current = ArcSummary(
            arc_id="arc-curr", start_chapter=11, end_chapter=15,
            arc_title="当前弧", arc_summary="当前弧摘要",
        )
        # 已完成弧
        arc_prev = ArcSummary(
            arc_id="arc-prev", start_chapter=1, end_chapter=10,
            arc_title="已完成弧", arc_summary="已完成弧摘要",
        )
        await arc_repo.create(arc_current, project_id)
        await arc_repo.create(arc_prev, project_id)

        result = await load_layered_summaries(project_id, current_chapter=15)

        arcs = [s for s in result if s.source_type == "arc"]
        # 当前弧(11-15)因 end_chapter >= current 被排除，
        # 只加载已完成弧(1-10)，但它与最近5章(11-15)不重叠
        assert len(arcs) == 1
        assert arcs[0].chapter_number == 1

    @pytest.mark.asyncio
    async def test_skips_current_volume(self, test_db) -> None:
        """end_chapter >= current_chapter 的卷（当前卷）不被加载."""
        project_id = "proj-tc-3"
        await _seed_project(project_id)

        repo = SummaryRepository()
        for i in range(1, 8):
            s = ChapterSummary(chapter_number=i, summary=f"第{i}章摘要")
            await repo.create(s, project_id, f"sum-{i}")

        vol_repo = VolumeSummaryRepository()
        # 当前卷包含 current_chapter=6
        vol_current = VolumeSummary(
            volume_id="vol-curr", start_chapter=1, end_chapter=30,
            volume_title="当前卷", volume_summary="当前卷摘要",
        )
        await vol_repo.create(vol_current, project_id)

        result = await load_layered_summaries(project_id, current_chapter=6)

        volumes = [s for s in result if s.source_type == "volume"]
        # 当前卷 end=30 >= 6，不是历史卷 → 不加载
        assert len(volumes) == 0

    @pytest.mark.asyncio
    async def test_token_budget_less_than_flat_60_percent(self, test_db) -> None:
        """金字塔结构的 token 占用 < 平铺结构的 60%.

        计算方式（基于 _build_recent_plot 截断长度）:
        - chapter: 120 字/条
        - arc: 280 字/条
        - volume: 180 字/条

        平铺（Ch51 场景）: 3 chapter + 5 arc + 1 volume = 3*120 + 5*280 + 180 = 1940
        金字塔（Ch51 场景）: 5 chapter + 1 arc + 1 volume = 5*120 + 280 + 180 = 1060
        比例: 1060 / 1940 = 54.6%
        """
        project_id = "proj-tc-4"
        await _seed_project(project_id)

        # 模拟 Ch51 场景：Ch1-50 的 summaries，5 个弧，2 个卷
        repo = SummaryRepository()
        for i in range(1, 51):
            s = ChapterSummary(chapter_number=i, summary=f"第{i}章摘要")
            await repo.create(s, project_id, f"sum-{i}")

        arc_repo = ArcSummaryRepository()
        for idx, start in enumerate(range(1, 51, 10), start=1):
            end = min(start + 9, 50)
            arc = ArcSummary(
                arc_id=f"arc-{idx}",
                start_chapter=start,
                end_chapter=end,
                arc_title=f"弧{idx}",
                arc_summary=f"弧{idx}摘要",
            )
            await arc_repo.create(arc, project_id)

        vol_repo = VolumeSummaryRepository()
        vol1 = VolumeSummary(
            volume_id="vol-1", start_chapter=1, end_chapter=30,
            volume_title="卷1", volume_summary="卷1摘要",
        )
        vol2 = VolumeSummary(
            volume_id="vol-2", start_chapter=31, end_chapter=50,
            volume_title="卷2", volume_summary="卷2摘要",
        )
        await vol_repo.create(vol1, project_id)
        await vol_repo.create(vol2, project_id)

        result = await load_layered_summaries(project_id, current_chapter=51)

        # 计算截断后总字数（模拟 _build_recent_plot 的截断逻辑）
        max_lengths = {"chapter": 120, "arc": 280, "volume": 180}
        pyramid_total = sum(
            min(len(s.summary), max_lengths.get(s.source_type, 120))
            for s in result
        )

        # 平铺结构（旧策略）字数估算
        # 精细层 3 章 + 所有 5 个弧 + 当前卷
        flat_total = 3 * 120 + 5 * 280 + 180

        ratio = pyramid_total / flat_total
        assert ratio < 0.60, f"金字塔 token 比例 {ratio:.2%} 应 < 60%"

        # 结构验证
        chapters = [s for s in result if s.source_type == "chapter"]
        arcs = [s for s in result if s.source_type == "arc"]
        volumes = [s for s in result if s.source_type == "volume"]

        assert len(chapters) == 5  # 最近 5 章
        assert len(arcs) == 1      # 只取最近一个已完成弧
        assert len(volumes) == 1   # 只取上一卷
