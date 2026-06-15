"""Tests for ArcSummaryGenerator and VolumeSummaryGenerator."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from songyan.agents.arc_summary_generator import (
    ArcSummaryGenerator,
    VolumeSummaryGenerator,
)
from songyan.db.context_repo import SummaryRepository
from songyan.db.layered_context_repo import ArcSummaryRepository
from songyan.db.repository import ProjectRepository
from songyan.models import ArcSummary, ChapterSummary, ProjectSetting
from songyan.workflows._helpers import new_id


@pytest.fixture
async def _seed_project() -> str:
    """Create a test project and return its ID."""
    project_id = new_id("proj")
    await ProjectRepository().create(
        ProjectSetting(
            title="测试项目",
            genre_id="scifi",
            mode_id="webnovel",
            protagonist_name="主角",
        ),
        project_id,
    )
    return project_id


class TestArcSummaryGenerator:
    """ArcSummaryGenerator tests with mocked LLM."""

    _LLM_RESPONSE = json.dumps({
        "arc_title": "觉醒篇",
        "arc_summary": "主角经历了觉醒和转变。",
        "key_events": ["觉醒", "试炼"],
        "resolved_threads": ["旧怨"],
        "new_threads": ["新威胁"],
        "character_arcs": {"主角": "从普通人到觉醒者"},
    })

    @pytest.mark.asyncio
    async def test_generate_with_summaries(self, test_db) -> None:
        """Generator calls LLM and returns structured ArcSummary."""
        project_id = new_id("proj")
        await ProjectRepository().create(
            ProjectSetting(
                title="测试项目",
                genre_id="scifi",
                mode_id="webnovel",
                protagonist_name="主角",
            ),
            project_id,
        )

        repo = SummaryRepository()
        for i in range(1, 4):
            summary = ChapterSummary(
                chapter_number=i,
                summary=f"第{i}章摘要。",
                key_events=[f"事件{i}"],
                characters_appeared=["主角"],
                impact_score=0.5,
            )
            await repo.create(summary, project_id, new_id("sum"))

        generator = ArcSummaryGenerator()
        with patch(
            "songyan.agents.arc_summary_generator.call_llm",
            new_callable=AsyncMock,
            return_value=self._LLM_RESPONSE,
        ):
            arc = await generator.generate(project_id, 1, 3)

        assert arc.project_id == project_id
        assert arc.start_chapter == 1
        assert arc.end_chapter == 3
        assert arc.arc_title == "觉醒篇"
        assert "主角" in arc.character_arcs
        assert arc.key_events == ["觉醒", "试炼"]

        # Verify persisted to DB
        loaded = await ArcSummaryRepository().get_by_arc_id(arc.arc_id)
        assert loaded is not None
        assert loaded.arc_title == "觉醒篇"

    @pytest.mark.asyncio
    async def test_generate_no_summaries(self, test_db) -> None:
        """When no chapter summaries exist, returns placeholder."""
        project_id = new_id("proj")
        await ProjectRepository().create(
            ProjectSetting(
                title="测试项目",
                genre_id="scifi",
                mode_id="webnovel",
                protagonist_name="主角",
            ),
            project_id,
        )

        generator = ArcSummaryGenerator()
        arc = await generator.generate(project_id, 1, 3)

        assert arc.arc_summary == "（暂无摘要数据）"
        assert arc.project_id == project_id

    @pytest.mark.asyncio
    async def test_generate_llm_error_propagates(self, test_db) -> None:
        """LLM parse errors should propagate."""
        project_id = new_id("proj")
        await ProjectRepository().create(
            ProjectSetting(
                title="测试项目",
                genre_id="scifi",
                mode_id="webnovel",
                protagonist_name="主角",
            ),
            project_id,
        )

        repo = SummaryRepository()
        summary = ChapterSummary(
            chapter_number=1,
            summary="第1章摘要。",
            key_events=["事件1"],
        )
        await repo.create(summary, project_id, new_id("sum"))

        generator = ArcSummaryGenerator()
        from songyan.exceptions import LLMResponseParseError

        with patch(
            "songyan.agents.arc_summary_generator.call_llm",
            new_callable=AsyncMock,
            return_value="not valid json",
        ):
            with pytest.raises(LLMResponseParseError):
                await generator.generate(project_id, 1, 1)


class TestVolumeSummaryGenerator:
    """VolumeSummaryGenerator tests with mocked LLM."""

    _LLM_RESPONSE = json.dumps({
        "volume_title": "第一卷：觉醒",
        "volume_summary": "主角踏上觉醒之路。",
        "major_revelations": ["世界真相"],
        "world_state": "混乱中的秩序萌芽",
    })

    @pytest.mark.asyncio
    async def test_generate_with_arcs(self, test_db) -> None:
        """Generator calls LLM and returns structured VolumeSummary."""
        project_id = new_id("proj")
        await ProjectRepository().create(
            ProjectSetting(
                title="测试项目",
                genre_id="scifi",
                mode_id="webnovel",
                protagonist_name="主角",
            ),
            project_id,
        )

        arcs = [
            ArcSummary(
                arc_id="arc-1",
                project_id=project_id,
                start_chapter=1,
                end_chapter=5,
                arc_title="觉醒篇",
                arc_summary="主角觉醒。",
                key_events=["觉醒"],
            ),
            ArcSummary(
                arc_id="arc-2",
                project_id=project_id,
                start_chapter=6,
                end_chapter=10,
                arc_title="试炼篇",
                arc_summary="主角接受试炼。",
                key_events=["试炼"],
            ),
        ]

        generator = VolumeSummaryGenerator()
        with patch(
            "songyan.agents.arc_summary_generator.call_llm",
            new_callable=AsyncMock,
            return_value=self._LLM_RESPONSE,
        ):
            volume = await generator.generate(project_id, arcs)

        assert volume.project_id == project_id
        assert volume.start_chapter == 1
        assert volume.end_chapter == 10
        assert volume.volume_title == "第一卷：觉醒"
        assert volume.major_revelations == ["世界真相"]

    @pytest.mark.asyncio
    async def test_generate_empty_arcs(self, test_db) -> None:
        """When no arcs provided, returns placeholder."""
        project_id = new_id("proj")
        await ProjectRepository().create(
            ProjectSetting(
                title="测试项目",
                genre_id="scifi",
                mode_id="webnovel",
                protagonist_name="主角",
            ),
            project_id,
        )

        generator = VolumeSummaryGenerator()
        volume = await generator.generate(project_id, [])

        assert volume.volume_title == "（暂无卷数据）"
        assert volume.project_id == project_id
