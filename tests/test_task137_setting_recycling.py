"""Task 137: 设定回收闭环机制测试."""

from __future__ import annotations

from typing import Any

import pytest

from songyan.agents.creative_director import _load_active_settings_to_recycle
from songyan.agents.setting_evaporator import _calculate_resolve_confidence
from songyan.agents.settlement_extractor._apply import (
    _detect_setting_references,
    _resolve_recycled_continuity_marks,
    apply_settlement,
)
from songyan.db.connection import get_db
from songyan.db.continuity_repo import SettingTrackingRepository
from songyan.db.human_mark_repo import HumanMarkRepository
from songyan.db.repository import CharacterRepository, ProjectRepository
from songyan.db.settlement_repo import SettingSnapshotRepository
from songyan.models import Character, NewSetting, ProjectSetting, StateSettlement
from songyan.models.human_mark import HumanMark


class TestDetectSettingReferences:
    """测试正文设定提及扫描."""

    def test_matches_standalone_setting_name(self) -> None:
        settings = [
            {
                "tracking_id": "t1",
                "setting_key": "xuanhuan.tian_jian",
                "setting_name": "天剑",
                "status": "active",
            }
        ]
        refs = _detect_setting_references("他握紧了天剑，目光如电。", settings)
        assert refs == {"t1": "xuanhuan.tian_jian"}

    def test_avoids_substring_inside_longer_word(self) -> None:
        settings = [
            {
                "tracking_id": "t1",
                "setting_key": "xuanhuan.tian_jian",
                "setting_name": "天剑",
                "status": "active",
            }
        ]
        refs = _detect_setting_references("天剑宗弟子正在巡逻。", settings)
        assert refs == {}

    def test_empty_content_returns_empty(self) -> None:
        settings = [
            {
                "tracking_id": "t1",
                "setting_key": "k",
                "setting_name": "name",
                "status": "active",
            }
        ]
        assert _detect_setting_references("", settings) == {}
        assert _detect_setting_references("正文", []) == {}


class TestResolveRecycledContinuityMarks:
    """测试 human_mark 自动 resolve."""

    @pytest.fixture
    async def mark_project(self, test_db: Any) -> str:
        project_id = "proj-mark"
        project = ProjectSetting(
            title="mark test", genre_id="xuanhuan", protagonist_name="林凡"
        )
        await ProjectRepository().create(project, project_id)
        return project_id

    @pytest.mark.asyncio
    async def test_resolve_only_continuity_auditor_setting_marks(
        self, mark_project: str
    ) -> None:
        repo = HumanMarkRepository()
        mark = HumanMark(
            mark_id="m1",
            project_id=mark_project,
            mark_type="setting",
            target_key="xuanhuan.tian_jian",
            source="continuity_auditor",
            priority=5,
        )
        await repo.create(mark)

        resolved = await _resolve_recycled_continuity_marks(
            mark_project, {"xuanhuan.tian_jian"}, repo, conn=None
        )
        assert resolved == 1
        unresolved = await repo.list_by_project(mark_project, include_resolved=False)
        assert len(unresolved) == 0

    @pytest.mark.asyncio
    async def test_ignores_non_matching_source_or_type(
        self, mark_project: str
    ) -> None:
        repo = HumanMarkRepository()
        await repo.create(
            HumanMark(
                mark_id="m1",
                project_id=mark_project,
                mark_type="setting",
                target_key="k1",
                source="human",
                priority=5,
            )
        )
        await repo.create(
            HumanMark(
                mark_id="m2",
                project_id=mark_project,
                mark_type="character",
                target_key="k1",
                source="continuity_auditor",
                priority=5,
            )
        )
        resolved = await _resolve_recycled_continuity_marks(
            mark_project, {"k1"}, repo, conn=None
        )
        assert resolved == 0


class TestApplySettlementRecycling:
    """测试 settlement apply 触发设定回收闭环."""

    @pytest.fixture
    async def recycling_project(self, test_db: Any) -> str:
        """创建包含角色、设定与 tracking 的测试项目."""
        project_id = "proj-recycle"
        project = ProjectSetting(
            title="recycle test",
            genre_id="xuanhuan",
            protagonist_name="林凡",
        )
        await ProjectRepository().create(project, project_id)
        char = Character(
            character_id="char-recycle",
            project_id=project_id,
            name="林凡",
            role_type="protagonist",
        )
        await CharacterRepository().create(char)

        setting = NewSetting(
            setting_name="天剑",
            description="上古神兵",
            source_quote="天剑出鞘",
            setting_key="xuanhuan.tian_jian",
        )
        await SettingSnapshotRepository().create(
            setting, project_id, "set-recycle-1"
        )
        await SettingTrackingRepository().create(
            tracking_id="track-recycle-1",
            project_id=project_id,
            setting_key="xuanhuan.tian_jian",
            setting_name="天剑",
            description="上古神兵",
            introduced_in_chapter=2,
            source_version_id="v-old",
            category="background",
        )
        return project_id

    @pytest.mark.asyncio
    async def test_content_reference_refreshes_last_mentioned(
        self, recycling_project: str
    ) -> None:
        project_id = recycling_project
        mark = HumanMark(
            mark_id="hm-recycle-1",
            project_id=project_id,
            mark_type="setting",
            target_key="xuanhuan.tian_jian",
            source="continuity_auditor",
            priority=5,
        )
        await HumanMarkRepository().create(mark)

        settlement = StateSettlement()
        content = "林凡再次举起天剑，剑光划破长空。"

        async with get_db() as conn:
            await apply_settlement(
                settlement,
                project_id,
                chapter_number=5,
                version_id="v-recycle",
                conn=conn,
                content=content,
            )
            await conn.commit()

        tracking = await SettingTrackingRepository().list_by_project(project_id)
        assert len(tracking) == 1
        assert tracking[0]["last_mentioned_chapter"] == 5

        unresolved = await HumanMarkRepository().list_by_project(
            project_id, include_resolved=False
        )
        assert len(unresolved) == 0

    @pytest.mark.asyncio
    async def test_recycled_settings_field_refreshes_tracking(
        self, recycling_project: str
    ) -> None:
        project_id = recycling_project
        settlement = StateSettlement(recycled_settings=["xuanhuan.tian_jian"])

        async with get_db() as conn:
            await apply_settlement(
                settlement,
                project_id,
                chapter_number=7,
                version_id="v-recycle-2",
                conn=conn,
                content="无关正文。",
            )
            await conn.commit()

        tracking = await SettingTrackingRepository().list_by_project(project_id)
        assert tracking[0]["last_mentioned_chapter"] == 7


class TestSettingTrackingLifecycleSync:
    """测试 setting_tracking 与 setting_snapshots 生命周期同步."""

    @pytest.fixture
    async def sync_project(self, test_db: Any) -> str:
        project_id = "proj-sync"
        project = ProjectSetting(
            title="sync test", genre_id="xuanhuan", protagonist_name="林凡"
        )
        await ProjectRepository().create(project, project_id)

        setting = NewSetting(
            setting_name="旧设定",
            description="很久没出现",
            source_quote="旧设定",
            setting_key="xuanhuan.old_setting",
        )
        await SettingSnapshotRepository().create(setting, project_id, "set-sync-1")
        await SettingTrackingRepository().create(
            tracking_id="track-sync-1",
            project_id=project_id,
            setting_key="xuanhuan.old_setting",
            setting_name="旧设定",
            description="很久没出现",
            introduced_in_chapter=1,
            source_version_id="v-old",
            category="background",
        )
        return project_id

    @pytest.mark.asyncio
    async def test_archive_stale_syncs_tracking_status(
        self, sync_project: str
    ) -> None:
        project_id = sync_project
        repo = SettingSnapshotRepository()
        await repo.archive_stale(project_id, current_chapter=15, window=10)

        async with get_db() as conn:
            conn.row_factory = None
            cursor = await conn.execute(
                "SELECT lifecycle_status FROM setting_snapshots WHERE project_id = ?",
                (project_id,),
            )
            row = await cursor.fetchone()
            assert row[0] == "dormant"

            cursor = await conn.execute(
                "SELECT status FROM setting_tracking WHERE project_id = ?",
                (project_id,),
            )
            row = await cursor.fetchone()
            assert row[0] == "dormant"

    @pytest.mark.asyncio
    async def test_archive_by_confidence_syncs_tracking_status(
        self, sync_project: str
    ) -> None:
        project_id = sync_project
        repo = SettingSnapshotRepository()
        await repo.archive_by_confidence(project_id, ["xuanhuan.old_setting"])

        async with get_db() as conn:
            cursor = await conn.execute(
                "SELECT lifecycle_status FROM setting_snapshots WHERE project_id = ?",
                (project_id,),
            )
            row = await cursor.fetchone()
            assert row[0] == "archived"

            cursor = await conn.execute(
                "SELECT status FROM setting_tracking WHERE project_id = ?",
                (project_id,),
            )
            row = await cursor.fetchone()
            assert row[0] == "archived"


class TestSettingEvaporatorTimeDecay:
    """测试按类别调整的时间衰减分母."""

    def test_background_decay_faster_than_critical(self) -> None:
        row = {
            "setting_name": "旧设定",
            "setting_key": "old_setting",
            "last_mentioned_chapter": 10,
            "category": "background",
        }
        conf_bg = _calculate_resolve_confidence(row, current_chapter=60, chapter_goal=None)

        row["category"] = "critical"
        conf_critical = _calculate_resolve_confidence(row, current_chapter=60, chapter_goal=None)

        # background 分母 25，50 章未引用已衰减到 0；critical 分母 100，仍有 0.5
        assert conf_bg < conf_critical
        assert conf_bg < 0.2
        assert conf_critical > 0.2

    def test_long_unmentioned_background_archives_earlier(self) -> None:
        row = {
            "setting_name": "背景设定",
            "setting_key": "bg_setting",
            "last_mentioned_chapter": 1,
            "category": "background",
        }
        conf = _calculate_resolve_confidence(row, current_chapter=20, chapter_goal=None)
        # 19 章未引用，background 分母 25 => time_factor = 1 - 19/25 = 0.24
        # conf = 0.5*0.24 + 0.09 = 0.21 > 0.15；20 章时下降到 ~0.19
        assert conf < 0.25


class TestCreativeDirectorRecycleFilter:
    """测试 CreativeDirector 优先展示沉寂设定."""

    @pytest.mark.asyncio
    async def test_load_recycle_filters_by_silent_chapters(self, monkeypatch: Any) -> None:
        rows = [
            {
                "setting_key": "just.mentioned",
                "setting_name": "刚提及",
                "status": "active",
                "introduced_in_chapter": 1,
                "last_mentioned_chapter": 5,
            },
            {
                "setting_key": "silent.setting",
                "setting_name": "沉寂设定",
                "status": "active",
                "introduced_in_chapter": 1,
                "last_mentioned_chapter": 2,
            },
        ]

        async def mock_list(_pid: str) -> list[dict]:
            return rows

        monkeypatch.setattr(
            "songyan.agents.creative_director.SettingTrackingRepository.list_by_project",
            staticmethod(mock_list),  # type: ignore[arg-type]
        )
        result = await _load_active_settings_to_recycle("p1", 5, min_silent_chapters=2)
        keys = [r["setting_key"] for r in result]
        assert "silent.setting" in keys
        assert "just.mentioned" not in keys
        # 按 last_mentioned 升序，沉寂设定排在最前
        assert result[0]["setting_key"] == "silent.setting"
