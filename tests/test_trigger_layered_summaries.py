"""Tests for trigger_layered_summaries in SettlementExtractor flow."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from songyan.db.context_repo import SummaryRepository
from songyan.db.layered_context_repo import ArcSummaryRepository
from songyan.db.repository import ProjectRepository
from songyan.exceptions import LLMError
from songyan.models import ArcSummary, ChapterSummary, ProjectSetting
from songyan.workflows._helpers import trigger_layered_summaries


async def _seed_project(project_id: str, arc_boundaries: list[int] | None = None) -> None:
    await ProjectRepository().create(
        ProjectSetting(
            title="测试项目",
            genre_id="scifi",
            mode_id="webnovel",
            protagonist_name="主角",
            arc_boundaries=arc_boundaries or [],
        ),
        project_id,
    )


class TestTriggerLayeredSummaries:
    """Settlement accept 后触发弧/卷摘要生成测试."""

    @pytest.mark.asyncio
    async def test_triggers_arc_at_boundary(self, test_db) -> None:
        """章节号为弧边界时触发 Arc 摘要生成."""
        project_id = "proj-trigger-1"
        await _seed_project(project_id)

        # 插入 10 章 summaries
        repo = SummaryRepository()
        for i in range(1, 11):
            s = ChapterSummary(chapter_number=i, summary=f"第{i}章摘要")
            await repo.create(s, project_id, f"sum-{i}")

        project = await ProjectRepository().get(project_id)
        assert project is not None

        with patch(
            "songyan.agents.arc_summary_generator.call_llm",
            new_callable=AsyncMock,
            return_value=json.dumps({
                "arc_title": "觉醒篇",
                "arc_summary": "主角觉醒。",
                "key_events": ["觉醒"],
                "resolved_threads": [],
                "new_threads": [],
                "character_arcs": {},
            }),
        ):
            await trigger_layered_summaries(project_id, chapter_number=10, project=project)

        # 验证 Arc 摘要已生成
        arcs = await ArcSummaryRepository().list_by_project(project_id)
        assert len(arcs) == 1
        assert arcs[0].start_chapter == 1
        assert arcs[0].end_chapter == 10

    @pytest.mark.asyncio
    async def test_does_not_trigger_arc_mid_arc(self, test_db) -> None:
        """章节号不是弧边界时不触发 Arc 摘要生成."""
        project_id = "proj-trigger-2"
        await _seed_project(project_id)

        repo = SummaryRepository()
        for i in range(1, 6):
            s = ChapterSummary(chapter_number=i, summary=f"第{i}章摘要")
            await repo.create(s, project_id, f"sum-{i}")

        project = await ProjectRepository().get(project_id)
        assert project is not None

        await trigger_layered_summaries(project_id, chapter_number=5, project=project)

        arcs = await ArcSummaryRepository().list_by_project(project_id)
        assert len(arcs) == 0

    @pytest.mark.asyncio
    async def test_updates_existing_arc(self, test_db) -> None:
        """Arc 已存在时更新而不是新建."""
        project_id = "proj-trigger-3"
        await _seed_project(project_id)

        repo = SummaryRepository()
        for i in range(1, 11):
            s = ChapterSummary(chapter_number=i, summary=f"第{i}章摘要")
            await repo.create(s, project_id, f"sum-{i}")

        # 预插入一个 Arc
        arc_repo = ArcSummaryRepository()
        existing = ArcSummary(
            arc_id="arc-old",
            start_chapter=1,
            end_chapter=10,
            arc_title="旧标题",
            arc_summary="旧摘要",
        )
        await arc_repo.create(existing, project_id)

        project = await ProjectRepository().get(project_id)
        assert project is not None

        with patch(
            "songyan.agents.arc_summary_generator.call_llm",
            new_callable=AsyncMock,
            return_value=json.dumps({
                "arc_title": "新标题",
                "arc_summary": "新摘要。",
                "key_events": ["新事件"],
                "resolved_threads": [],
                "new_threads": [],
                "character_arcs": {},
            }),
        ):
            await trigger_layered_summaries(project_id, chapter_number=10, project=project)

        arcs = await ArcSummaryRepository().list_by_project(project_id)
        assert len(arcs) == 1
        assert arcs[0].arc_id == "arc-old"
        assert arcs[0].arc_title == "新标题"
        assert arcs[0].arc_summary == "新摘要。"

    @pytest.mark.asyncio
    async def test_failure_does_not_raise(self, test_db) -> None:
        """生成器失败时不抛出异常."""
        project_id = "proj-trigger-4"
        await _seed_project(project_id)

        # 插入 summaries，使生成器尝试调用 LLM
        repo = SummaryRepository()
        for i in range(1, 11):
            s = ChapterSummary(chapter_number=i, summary=f"第{i}章摘要")
            await repo.create(s, project_id, f"sum-{i}")

        project = await ProjectRepository().get(project_id)
        assert project is not None

        with patch(
            "songyan.agents.arc_summary_generator.call_llm",
            new_callable=AsyncMock,
            side_effect=LLMError("LLM failed"),
        ):
            # 不应抛出
            await trigger_layered_summaries(project_id, chapter_number=10, project=project)

        # LLM 失败，不应创建 Arc 摘要（有数据时不会创建 placeholder）
        arcs = await ArcSummaryRepository().list_by_project(project_id)
        assert len(arcs) == 0
