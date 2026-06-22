"""Tests for Phase 4 layered context features."""

from __future__ import annotations

import pytest

from songyan.agents.context_manager import (
    _calculate_dynamic_relevance,
    _dynamic_budget,
)
from songyan.db.layered_context_repo import (
    ArcSummaryRepository,
    PermanentSceneRepository,
    VolumeSummaryRepository,
)
from songyan.db.repository import ProjectRepository
from songyan.models import (
    ArcSummary,
    OpenThread,
    PermanentScene,
    ProjectSetting,
    SoftReference,
    VolumeSummary,
)


async def _seed_project(project_id: str = "proj-test") -> None:
    """创建一个测试项目."""
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="xuanhuan",
            protagonist_name="Test",
        ),
        project_id,
    )


# ---------------------------------------------------------------------------
# Dynamic Budget
# ---------------------------------------------------------------------------
class TestDynamicBudget:
    def test_early_chapters_base_budget(self) -> None:
        assert _dynamic_budget(1, 8000) == 8250
        assert _dynamic_budget(10, 8000) == 10500

    def test_mid_chapters_boosted(self) -> None:
        assert _dynamic_budget(11, 8000) == 10750
        assert _dynamic_budget(50, 8000) == 20500

    def test_late_chapters_base_budget(self) -> None:
        assert _dynamic_budget(51, 8000) == 20750
        assert _dynamic_budget(100, 8000) == 33000

    def test_custom_base_budget(self) -> None:
        assert _dynamic_budget(25, 5000) == 11250


# ---------------------------------------------------------------------------
# Dynamic Relevance
# ---------------------------------------------------------------------------
class TestDynamicRelevance:
    def test_decay_over_time(self) -> None:
        ref = SoftReference(
            type="world_setting",
            content="test",
            relevance_score=1.0,
            last_mentioned_chapter=10,
        )
        result = _calculate_dynamic_relevance(ref, current_chapter=20, recent_chapters=[])
        # 10 章差距 → decay = max(0.3, 1.0 - 10*0.05) = 0.5
        assert result == 0.5

    def test_boost_when_recently_mentioned(self) -> None:
        ref = SoftReference(
            type="world_setting",
            content="test",
            relevance_score=1.0,
            last_mentioned_chapter=10,
        )
        result = _calculate_dynamic_relevance(ref, current_chapter=20, recent_chapters=[10])
        # decay 0.5 * boost 1.3 = 0.65
        assert result == 0.65

    def test_critical_setting_no_decay(self) -> None:
        ref = SoftReference(
            type="world_setting",
            content="test",
            relevance_score=0.5,
            last_mentioned_chapter=1,
            is_critical=True,
        )
        result = _calculate_dynamic_relevance(ref, current_chapter=100, recent_chapters=[])
        # is_critical → max(0.5, 0.9) = 0.9
        assert result == 0.9

    def test_capped_at_1_0(self) -> None:
        ref = SoftReference(
            type="world_setting",
            content="test",
            relevance_score=1.0,
            last_mentioned_chapter=20,
            is_critical=True,
        )
        result = _calculate_dynamic_relevance(ref, current_chapter=20, recent_chapters=[20])
        # 1.0 * 1.0 * 1.3 = 1.3 → capped at 1.0
        assert result == 1.0

    def test_no_last_mentioned(self) -> None:
        ref = SoftReference(
            type="world_setting",
            content="test",
            relevance_score=0.8,
        )
        result = _calculate_dynamic_relevance(ref, current_chapter=20, recent_chapters=[])
        assert result == 0.8

    def test_floor_at_0_3(self) -> None:
        ref = SoftReference(
            type="world_setting",
            content="test",
            relevance_score=1.0,
            last_mentioned_chapter=1,
        )
        result = _calculate_dynamic_relevance(ref, current_chapter=100, recent_chapters=[])
        # decay = max(0.3, 1.0 - 99*0.05) = 0.3
        assert result == 0.3


# ---------------------------------------------------------------------------
# ArcSummary Repository
# ---------------------------------------------------------------------------
class TestArcSummaryRepository:
    pytestmark = pytest.mark.asyncio

    @pytest.fixture(autouse=True)
    async def _init_db(self, test_db):
        """Auto-use fixture to ensure DB is initialized."""
        await _seed_project("proj-test")
        await _seed_project("proj-list")
        await _seed_project("proj-del")
    @pytest.mark.asyncio
    async def test_create_and_get_current_arc(self) -> None:
        repo = ArcSummaryRepository()
        arc = ArcSummary(
            arc_id="arc-001",
            start_chapter=1,
            end_chapter=10,
            arc_title="觉醒篇",
            arc_summary="主角觉醒力量",
            key_events=["觉醒"],
        )
        await repo.create(arc, project_id="proj-test")

        result = await repo.get_current_arc("proj-test", 5)
        assert result is not None
        assert result.arc_id == "arc-001"
        assert result.arc_title == "觉醒篇"

    @pytest.mark.asyncio
    async def test_get_current_arc_out_of_range(self) -> None:
        repo = ArcSummaryRepository()
        result = await repo.get_current_arc("proj-test", 99)
        assert result is None

    @pytest.mark.asyncio
    async def test_list_by_project(self) -> None:
        repo = ArcSummaryRepository()
        arc1 = ArcSummary(arc_id="arc-a", start_chapter=1, end_chapter=5)
        arc2 = ArcSummary(arc_id="arc-b", start_chapter=6, end_chapter=10)
        await repo.create(arc1, project_id="proj-list")
        await repo.create(arc2, project_id="proj-list")

        results = await repo.list_by_project("proj-list")
        assert len(results) == 2
        assert results[0].arc_id == "arc-a"
        assert results[1].arc_id == "arc-b"

    @pytest.mark.asyncio
    async def test_get_by_arc_id(self) -> None:
        repo = ArcSummaryRepository()
        arc = ArcSummary(
            arc_id="arc-get",
            start_chapter=1,
            end_chapter=5,
            arc_title="测试弧",
            arc_summary="测试摘要",
        )
        await repo.create(arc, project_id="proj-test")

        result = await repo.get_by_arc_id("arc-get")
        assert result is not None
        assert result.arc_id == "arc-get"
        assert result.arc_title == "测试弧"
        assert result.project_id == "proj-test"

    @pytest.mark.asyncio
    async def test_get_by_arc_id_not_found(self) -> None:
        repo = ArcSummaryRepository()
        result = await repo.get_by_arc_id("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_update(self) -> None:
        repo = ArcSummaryRepository()
        arc = ArcSummary(
            arc_id="arc-update",
            start_chapter=1,
            end_chapter=5,
            arc_title="旧标题",
            arc_summary="旧摘要",
        )
        await repo.create(arc, project_id="proj-test")

        arc.arc_title = "新标题"
        arc.arc_summary = "新摘要"
        arc.key_events = ["事件1"]
        await repo.update(arc, project_id="proj-test")

        result = await repo.get_by_arc_id("arc-update")
        assert result is not None
        assert result.arc_title == "新标题"
        assert result.arc_summary == "新摘要"
        assert result.key_events == ["事件1"]

    @pytest.mark.asyncio
    async def test_delete_by_project(self) -> None:
        repo = ArcSummaryRepository()
        arc = ArcSummary(arc_id="arc-del", start_chapter=1, end_chapter=5)
        await repo.create(arc, project_id="proj-del")

        deleted = await repo.delete_by_project("proj-del")
        assert deleted == 1

        result = await repo.get_by_arc_id("arc-del")
        assert result is None


# ---------------------------------------------------------------------------
# VolumeSummary Repository
# ---------------------------------------------------------------------------
class TestVolumeSummaryRepository:
    pytestmark = pytest.mark.asyncio

    @pytest.fixture(autouse=True)
    async def _init_db(self, test_db):
        await _seed_project("proj-test")
        await _seed_project("proj-vol")
        await _seed_project("proj-del")
    @pytest.mark.asyncio
    async def test_create_and_get_current_volume(self) -> None:
        repo = VolumeSummaryRepository()
        vol = VolumeSummary(
            volume_id="vol-001",
            start_chapter=1,
            end_chapter=30,
            volume_title="第一卷",
            volume_summary="初入江湖",
        )
        await repo.create(vol, project_id="proj-test")

        result = await repo.get_current_volume("proj-test", 15)
        assert result is not None
        assert result.volume_id == "vol-001"
        assert result.volume_title == "第一卷"

    @pytest.mark.asyncio
    async def test_list_by_project(self) -> None:
        repo = VolumeSummaryRepository()
        vol = VolumeSummary(volume_id="vol-001", start_chapter=1, end_chapter=30)
        await repo.create(vol, project_id="proj-vol")

        results = await repo.list_by_project("proj-vol")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_get_by_volume_id(self) -> None:
        repo = VolumeSummaryRepository()
        vol = VolumeSummary(
            volume_id="vol-get",
            start_chapter=1,
            end_chapter=30,
            volume_title="测试卷",
            volume_summary="测试摘要",
        )
        await repo.create(vol, project_id="proj-test")

        result = await repo.get_by_volume_id("vol-get")
        assert result is not None
        assert result.volume_id == "vol-get"
        assert result.volume_title == "测试卷"
        assert result.project_id == "proj-test"

    @pytest.mark.asyncio
    async def test_get_by_volume_id_not_found(self) -> None:
        repo = VolumeSummaryRepository()
        result = await repo.get_by_volume_id("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_update(self) -> None:
        repo = VolumeSummaryRepository()
        vol = VolumeSummary(
            volume_id="vol-update",
            start_chapter=1,
            end_chapter=30,
            volume_title="旧标题",
            volume_summary="旧摘要",
        )
        await repo.create(vol, project_id="proj-test")

        vol.volume_title = "新标题"
        vol.volume_summary = "新摘要"
        vol.major_revelations = ["真相"]
        await repo.update(vol, project_id="proj-test")

        result = await repo.get_by_volume_id("vol-update")
        assert result is not None
        assert result.volume_title == "新标题"
        assert result.volume_summary == "新摘要"
        assert result.major_revelations == ["真相"]

    @pytest.mark.asyncio
    async def test_delete_by_project(self) -> None:
        repo = VolumeSummaryRepository()
        vol = VolumeSummary(volume_id="vol-del", start_chapter=1, end_chapter=30)
        await repo.create(vol, project_id="proj-del")

        deleted = await repo.delete_by_project("proj-del")
        assert deleted == 1

        result = await repo.get_by_volume_id("vol-del")
        assert result is None


# ---------------------------------------------------------------------------
# PermanentScene Repository
# ---------------------------------------------------------------------------
class TestPermanentSceneRepository:
    pytestmark = pytest.mark.asyncio

    @pytest.fixture(autouse=True)
    async def _init_db(self, test_db):
        await _seed_project("proj-test")
        await _seed_project("proj-ref")
    @pytest.mark.asyncio
    async def test_create_and_list(self) -> None:
        repo = PermanentSceneRepository()
        scene = PermanentScene(
            scene_id="scene-001",
            chapter_number=5,
            scene_number=1,
            excerpt="关键段落",
            impact_tags=["世界观颠覆"],
        )
        await repo.create(scene, project_id="proj-test")

        results = await repo.list_by_project("proj-test")
        assert len(results) == 1
        assert results[0].scene_id == "scene-001"
        assert results[0].impact_tags == ["世界观颠覆"]

    @pytest.mark.asyncio
    async def test_create_is_idempotent_for_same_scene_id(self) -> None:
        """同章重跑会复用 deterministic scene_id，应更新而不是 UNIQUE 失败."""
        repo = PermanentSceneRepository()
        first = PermanentScene(
            scene_id="scene-idempotent",
            chapter_number=5,
            scene_number=1,
            excerpt="旧段落",
            impact_tags=["旧标签"],
        )
        second = PermanentScene(
            scene_id="scene-idempotent",
            chapter_number=5,
            scene_number=1,
            excerpt="新段落",
            impact_tags=["新标签"],
        )
        await repo.create(first, project_id="proj-test")
        await repo.create(second, project_id="proj-test")

        results = await repo.list_by_project("proj-test")
        assert len(results) == 1
        assert results[0].excerpt == "新段落"
        assert results[0].impact_tags == ["新标签"]

    @pytest.mark.asyncio
    async def test_add_reference(self) -> None:
        repo = PermanentSceneRepository()
        scene = PermanentScene(
            scene_id="scene-ref",
            chapter_number=5,
            excerpt="test",
        )
        await repo.create(scene, project_id="proj-ref")
        await repo.add_reference("scene-ref", 10)

        results = await repo.list_by_project("proj-ref")
        assert 10 in results[0].referenced_by


# ---------------------------------------------------------------------------
# OpenThread Model
# ---------------------------------------------------------------------------
class TestOpenThread:
    def test_defaults(self) -> None:
        ot = OpenThread(
            thread_id="t1",
            description="线索",
            source_type="setting",
            source_chapter=5,
        )
        assert ot.priority == 0.5

    def test_custom_priority(self) -> None:
        ot = OpenThread(
            thread_id="t1",
            description="线索",
            source_type="foreshadowing",
            source_chapter=3,
            priority=0.9,
        )
        assert ot.priority == 0.9
