"""Task 137: 设定回收闭环机制测试."""

from __future__ import annotations

from typing import Any

import pytest

from songyan.agents.continuity_auditor import ContinuityAuditor
from songyan.agents.creative_director import (
    _format_active_settings_to_recycle,
    _load_active_settings_to_recycle,
)
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

    def test_allows_chinese_grammar_boundary_after_term(self) -> None:
        """Task 137: 术语后接“的”等语法边界时应刷新 last_mentioned."""
        settings = [
            {
                "tracking_id": "t1",
                "setting_key": "technology.quantum.entanglement_relay_communication",
                "setting_name": "量子纠缠中继通信",
                "status": "active",
            }
        ]

        refs = _detect_setting_references(
            "基频波形呈现标准的量子纠缠中继通信的相位偏移模式。",
            settings,
        )

        assert refs == {
            "t1": "technology.quantum.entanglement_relay_communication"
        }

    def test_matches_split_setting_name_aliases(self) -> None:
        """Task 137: 复合 setting_name 可由名称片段命中."""
        settings = [
            {
                "tracking_id": "t1",
                "setting_key": "organization.expedition.team_7",
                "setting_name": "第7远征队·静默节点",
                "status": "active",
            },
            {
                "tracking_id": "t2",
                "setting_key": "artifact.ruin.fibonacci_time_loop",
                "setting_name": "斐波那契周期循环（时间闭环）",
                "status": "active",
            },
        ]

        refs = _detect_setting_references(
            "第7远征队在时间闭环中死亡七次。",
            settings,
        )

        assert refs == {
            "t1": "organization.expedition.team_7",
            "t2": "artifact.ruin.fibonacci_time_loop",
        }

    def test_matches_e7_phase_channel_equivalent_codes(self) -> None:
        """Task 4A.3: E-7 通道相位节点支持 E-7-θ 编号刷新."""
        settings = [
            {
                "tracking_id": "t1",
                "setting_key": "ruin.e7.phase_channel_node",
                "setting_name": "E-7通道相位节点",
                "description": "相位节点位于E-7维护通道。",
                "status": "active",
            }
        ]

        refs = _detect_setting_references(
            "林凡把探针接入E-7-θ编号，墙上的相位噪声立刻回落。",
            settings,
        )

        assert refs == {"t1": "ruin.e7.phase_channel_node"}

    def test_matches_topology_and_self_repair_equivalent_terms(self) -> None:
        """Task 4A.3: 空间/相位拓扑、墙壁/材料自修复等价刷新."""
        settings = [
            {
                "tracking_id": "t1",
                "setting_key": "ruin.topology.space_phase",
                "setting_name": "空间/相位拓扑",
                "description": "遗迹空间拓扑与相位拓扑同步偏移。",
                "status": "active",
            },
            {
                "tracking_id": "t2",
                "setting_key": "ruin.material.wall_self_repair",
                "setting_name": "墙壁/材料自修复",
                "description": "墙壁材料会在受损后自修复。",
                "status": "active",
            },
        ]

        refs = _detect_setting_references(
            "相位拓扑重新闭合，材料自修复也沿着裂缝开始回填。",
            settings,
        )

        assert refs == {
            "t1": "ruin.topology.space_phase",
            "t2": "ruin.material.wall_self_repair",
        }

    def test_matches_chinese_seventh_expedition_alias(self) -> None:
        """Task 4A.3: 第7远征队与第七远征队视为等价提及."""
        settings = [
            {
                "tracking_id": "t1",
                "setting_key": "organization.expedition.team_7",
                "setting_name": "第7远征队·静默节点",
                "status": "active",
            }
        ]

        refs = _detect_setting_references("第七远征队的残留编号再次亮起。", settings)

        assert refs == {"t1": "organization.expedition.team_7"}

    def test_matches_task138c_canonical_alias_clusters(self) -> None:
        """Task 138c: 覆盖 Ch12 剩余 orphan 的窄同簇表达."""
        settings = [
            {
                "tracking_id": "t1",
                "setting_key": "artifact.mega_ruin.surface_material",
                "setting_name": "巨型遗迹表面材料特性",
                "description": "巨型遗迹表面的非欧几何合金。",
                "status": "active",
            },
            {
                "tracking_id": "t2",
                "setting_key": "location.perseus.arm_mega_ruin",
                "setting_name": "英仙臂外侧巨型遗迹",
                "description": "英仙臂外侧的巨型遗迹。",
                "status": "active",
            },
            {
                "tracking_id": "t3",
                "setting_key": "signal.fibonacci.frequency_hopping_sequence",
                "setting_name": "斐波那契频率跳变序列",
                "description": "斐波那契序列频率激活。",
                "status": "active",
            },
            {
                "tracking_id": "t4",
                "setting_key": "artifact.ruin.nonlocal_spacetime_marking",
                "setting_name": "非本地时空标记系统",
                "description": "遗迹系统的非本地时空标记。",
                "status": "active",
            },
            {
                "tracking_id": "t5",
                "setting_key": "artifact.mega_ruin.wall_living_properties",
                "setting_name": "遗迹墙壁活体特性",
                "description": "墙壁上的能量纹路会响应意识。",
                "status": "active",
            },
        ]

        refs = _detect_setting_references(
            "英仙臂外侧的巨型遗迹外层散出非欧几何合金碎片的气味。"
            "墙壁上的能量纹路开始闪烁，斐波那契序列频率重新激活。"
            "林凡确认这是欺骗遗迹系统的时空标记系统。",
            settings,
        )

        assert refs == {
            "t1": "artifact.mega_ruin.surface_material",
            "t2": "location.perseus.arm_mega_ruin",
            "t3": "signal.fibonacci.frequency_hopping_sequence",
            "t4": "artifact.ruin.nonlocal_spacetime_marking",
            "t5": "artifact.mega_ruin.wall_living_properties",
        }

    def test_task138c_aliases_do_not_match_broad_words(self) -> None:
        settings = [
            {
                "tracking_id": "t1",
                "setting_key": "signal.fibonacci.frequency_hopping_sequence",
                "setting_name": "斐波那契频率跳变序列",
                "description": "斐波那契序列频率激活。",
                "status": "active",
            },
            {
                "tracking_id": "t2",
                "setting_key": "artifact.mega_ruin.wall_living_properties",
                "setting_name": "遗迹墙壁活体特性",
                "description": "墙壁上的能量纹路会响应意识。",
                "status": "active",
            },
            {
                "tracking_id": "t3",
                "setting_key": "location.perseus.arm_mega_ruin",
                "setting_name": "英仙臂外侧巨型遗迹",
                "description": "英仙臂外侧的巨型遗迹。",
                "status": "active",
            },
            {
                "tracking_id": "t4",
                "setting_key": "artifact.mega_ruin.surface_material",
                "setting_name": "巨型遗迹表面材料特性",
                "description": "巨型遗迹表面的非欧几何合金碎片。",
                "status": "active",
            },
        ]

        refs = _detect_setting_references(
            "频率正在变化。墙壁很冷。远方有人提起巨型遗迹传闻。"
            "裸露的能量纹路并不能说明它的表面材料。",
            settings,
        )

        assert refs == {}

    def test_task138c_r2_surface_material_matches_only_narrow_aliases(self) -> None:
        settings = [
            {
                "tracking_id": "t1",
                "setting_key": "artifact.mega_ruin.surface_material",
                "setting_name": "巨型遗迹表面材料特性",
                "description": "巨型遗迹表面的非欧几何合金碎片。",
                "status": "active",
            }
        ]

        refs = _detect_setting_references(
            "非欧几何合金碎片的纹理与巨型遗迹表面的能量纹路互相咬合。",
            settings,
        )

        assert refs == {"t1": "artifact.mega_ruin.surface_material"}

    @pytest.mark.parametrize(
        "content",
        [
            "星图一层层地从表面材料下浮现出来。",
            "舰体表面的涂装在遗迹表面半流体材料的反光中扭曲变形。",
            "墙壁上的能量纹路在低温下变得更加明亮。",
            "遗迹表面的能量纹路与星图网络同步闪烁。",
        ],
    )
    def test_task138g_surface_material_ch12_evidence_refreshes(
        self,
        content: str,
    ) -> None:
        """Task 138g: Ch12 明确材料/纹路证据可刷新 surface_material."""
        settings = [
            {
                "tracking_id": "t1",
                "setting_key": "artifact.mega_ruin.surface_material",
                "setting_name": "巨型遗迹表面材料特性",
                "description": "遗迹表面材料为半流体，能根据压力改变密度。",
                "status": "active",
            }
        ]

        refs = _detect_setting_references(content, settings)

        assert refs == {"t1": "artifact.mega_ruin.surface_material"}

    @pytest.mark.parametrize(
        "content",
        [
            "巨型遗迹仍在远处沉默。",
            "他的手掌按在表面。",
            "裸露的能量纹路不断闪烁。",
            "金属表面刮出五道白痕。",
        ],
    )
    def test_task138g_surface_material_broad_terms_do_not_refresh(
        self,
        content: str,
    ) -> None:
        """Task 138g: 宽泛词不能伪刷新 surface_material."""
        settings = [
            {
                "tracking_id": "t1",
                "setting_key": "artifact.mega_ruin.surface_material",
                "setting_name": "巨型遗迹表面材料特性",
                "description": "遗迹表面材料为半流体，能根据压力改变密度。",
                "status": "active",
            }
        ]

        refs = _detect_setting_references(content, settings)

        assert refs == {}

    def test_task138g_phase_offset_does_not_refresh_phase_flush(self) -> None:
        """Task 138g: 弱相关“相位偏移”不能刷新相位冲刷机制."""
        settings = [
            {
                "tracking_id": "t1",
                "setting_key": "artifact.ruin.phase_flush_mechanism",
                "setting_name": "相位冲刷机制",
                "description": "每72分钟一次相位冲刷，纳米蜂群休眠。",
                "status": "active",
            }
        ]

        refs = _detect_setting_references(
            "SS-047在死前最后三秒感知到了空间折叠的触发信号，"
            "那是一种频率极其微弱的相位偏移。",
            settings,
        )

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

    @pytest.mark.asyncio
    async def test_duplicate_e7_phase_cluster_refreshes_existing_without_new_tracking(
        self, test_db: Any
    ) -> None:
        """Task 4A.3: E-7 同簇新设定不新增 orphan，只刷新 canonical."""
        project_id = "proj-e7-duplicate"
        await ProjectRepository().create(
            ProjectSetting(
                title="e7 duplicate",
                genre_id="sci_fi",
                protagonist_name="林凡",
            ),
            project_id,
        )
        await CharacterRepository().create(
            Character(
                character_id="char-e7",
                project_id=project_id,
                name="林凡",
                role_type="protagonist",
            )
        )
        existing = NewSetting(
            setting_name="E-7通道相位节点",
            description="E-7维护通道里的相位节点。",
            source_quote="E-7通道相位节点",
            setting_key="ruin.e7.phase_channel_node",
        )
        await SettingSnapshotRepository().create(
            existing, project_id, "set-e7-existing"
        )
        await SettingTrackingRepository().create(
            tracking_id="track-e7-existing",
            project_id=project_id,
            setting_key="ruin.e7.phase_channel_node",
            setting_name="E-7通道相位节点",
            description="E-7维护通道里的相位节点。",
            introduced_in_chapter=6,
            source_version_id="v-e7-old",
            category="technical",
        )

        settlement = StateSettlement(
            new_settings=[
                NewSetting(
                    setting_name="E-7-θ通道相位节点",
                    description="E-7-θ编号对应同一个通道相位节点。",
                    source_quote="E-7-θ编号",
                    setting_key="ruin.e7.theta_phase_node",
                )
            ]
        )

        async with get_db() as conn:
            await apply_settlement(
                settlement,
                project_id,
                chapter_number=12,
                version_id="v-e7-new",
                conn=conn,
                content="林凡再次校准E-7-θ编号。",
            )
            await conn.commit()

        tracking = await SettingTrackingRepository().list_by_project(project_id)
        assert len(tracking) == 1
        assert tracking[0]["setting_key"] == "ruin.e7.phase_channel_node"
        assert tracking[0]["last_mentioned_chapter"] == 12

        snapshots = await SettingSnapshotRepository().list_by_project(project_id)
        assert len(snapshots) == 1
        assert snapshots[0].setting_key == "ruin.e7.phase_channel_node"


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

    async def _add_setting(
        self,
        project_id: str,
        *,
        suffix: str,
        category: str,
        recovery_required: bool = False,
    ) -> None:
        key = f"{category}.{suffix}"
        await SettingSnapshotRepository().create(
            NewSetting(
                setting_name=f"{category}-{suffix}",
                description="长期沉寂设定",
                source_quote=f"{category}-{suffix}",
                setting_key=key,
            ),
            project_id,
            f"set-{suffix}",
        )
        await SettingTrackingRepository().create(
            tracking_id=f"track-{suffix}",
            project_id=project_id,
            setting_key=key,
            setting_name=f"{category}-{suffix}",
            description="长期沉寂设定",
            introduced_in_chapter=1,
            source_version_id="v-old",
            category=category,
        )
        if recovery_required:
            async with get_db() as conn:
                await conn.execute(
                    "UPDATE setting_tracking SET recovery_required = 1 "
                    "WHERE tracking_id = ?",
                    (f"track-{suffix}",),
                )
                await conn.commit()

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

    @pytest.mark.asyncio
    async def test_archive_long_silent_nonessential_only_archives_background_and_technical(
        self, sync_project: str
    ) -> None:
        project_id = sync_project
        await self._add_setting(project_id, suffix="tech-old", category="technical")
        await self._add_setting(project_id, suffix="critical-old", category="critical")
        await self._add_setting(project_id, suffix="recurring-old", category="recurring")
        await self._add_setting(
            project_id,
            suffix="background-required",
            category="background",
            recovery_required=True,
        )
        await HumanMarkRepository().create(
            HumanMark(
                mark_id="hm-protect-background",
                project_id=project_id,
                mark_type="setting",
                target_key="background.protected",
                source="human",
                priority=5,
            )
        )
        await self._add_setting(project_id, suffix="protected", category="background")
        await HumanMarkRepository().create(
            HumanMark(
                mark_id="hm-old-diagnostic",
                project_id=project_id,
                mark_type="setting",
                target_key="background.old-diagnostic",
                source="continuity_auditor",
                created_at_chapter=9,
                priority=5,
            )
        )
        await self._add_setting(project_id, suffix="old-diagnostic", category="background")
        await HumanMarkRepository().create(
            HumanMark(
                mark_id="hm-current-diagnostic",
                project_id=project_id,
                mark_type="setting",
                target_key="background.current-diagnostic",
                source="continuity_auditor",
                created_at_chapter=12,
                priority=5,
            )
        )
        await self._add_setting(
            project_id, suffix="current-diagnostic", category="background"
        )

        archived = await SettingTrackingRepository().archive_long_silent_nonessential(
            project_id, current_chapter=12
        )

        assert archived == 3
        async with get_db() as conn:
            cursor = await conn.execute(
                "SELECT setting_key, status FROM setting_tracking "
                "WHERE project_id = ? ORDER BY setting_key",
                (project_id,),
            )
            statuses = dict(await cursor.fetchall())
            assert statuses["xuanhuan.old_setting"] == "archived"
            assert statuses["technical.tech-old"] == "archived"
            assert statuses["critical.critical-old"] == "active"
            assert statuses["recurring.recurring-old"] == "active"
            assert statuses["background.background-required"] == "active"
            assert statuses["background.protected"] == "active"
            assert statuses["background.old-diagnostic"] == "active"
            assert statuses["background.current-diagnostic"] == "archived"

            cursor = await conn.execute(
                "SELECT setting_key, lifecycle_status FROM setting_snapshots "
                "WHERE project_id = ? ORDER BY setting_key",
                (project_id,),
            )
            snapshot_statuses = dict(await cursor.fetchall())
            assert snapshot_statuses["xuanhuan.old_setting"] == "archived"
            assert snapshot_statuses["technical.tech-old"] == "archived"
            assert snapshot_statuses["background.current-diagnostic"] == "archived"

    @pytest.mark.asyncio
    async def test_continuity_auditor_archives_long_silent_nonessential_before_orphan_scan(
        self, sync_project: str
    ) -> None:
        project_id = sync_project
        await self._add_setting(project_id, suffix="tech-old", category="technical")
        await self._add_setting(project_id, suffix="critical-old", category="critical")
        await self._add_setting(project_id, suffix="recurring-old", category="recurring")
        await self._add_setting(project_id, suffix="human-held", category="background")
        await self._add_setting(project_id, suffix="critical-marked", category="critical")
        await HumanMarkRepository().create(
            HumanMark(
                mark_id="hm-held-background",
                project_id=project_id,
                mark_type="setting",
                target_key="background.human-held",
                source="human",
                priority=5,
            )
        )
        await HumanMarkRepository().create(
            HumanMark(
                mark_id="hm-critical-marked",
                project_id=project_id,
                mark_type="setting",
                target_key="critical.critical-marked",
                source="human",
                priority=5,
            )
        )
        await self._add_setting(
            project_id, suffix="current-diagnostic", category="background"
        )
        await HumanMarkRepository().create(
            HumanMark(
                mark_id="hm-current-diagnostic",
                project_id=project_id,
                mark_type="setting",
                target_key="background.current-diagnostic",
                source="continuity_auditor",
                created_at_chapter=12,
                priority=5,
            )
        )

        report = await ContinuityAuditor().audit(project_id, up_to_chapter=12)

        orphaned_keys = {item.setting_key for item in report.orphaned_settings}
        assert "xuanhuan.old_setting" not in orphaned_keys
        assert "technical.tech-old" not in orphaned_keys
        assert "background.human-held" not in orphaned_keys
        assert "background.current-diagnostic" not in orphaned_keys
        assert "critical.critical-old" in orphaned_keys
        assert "critical.critical-marked" in orphaned_keys
        assert "recurring.recurring-old" in orphaned_keys


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

        async def mock_marks(*_args: Any, **_kwargs: Any) -> list[HumanMark]:
            return []

        monkeypatch.setattr(
            "songyan.agents.creative_director.SettingTrackingRepository.list_by_project",
            staticmethod(mock_list),  # type: ignore[arg-type]
        )
        monkeypatch.setattr(
            "songyan.agents.creative_director.HumanMarkRepository.list_by_project",
            staticmethod(mock_marks),  # type: ignore[arg-type]
        )
        result = await _load_active_settings_to_recycle("p1", 5, min_silent_chapters=2)
        keys = [r["setting_key"] for r in result]
        assert "silent.setting" in keys
        assert "just.mentioned" not in keys
        # 按 last_mentioned 升序，沉寂设定排在最前
        assert result[0]["setting_key"] == "silent.setting"

    @pytest.mark.asyncio
    async def test_load_recycle_prioritizes_critical_before_older_background(
        self, monkeypatch: Any
    ) -> None:
        rows = [
            {
                "setting_key": "background.old",
                "setting_name": "很旧背景",
                "status": "active",
                "category": "background",
                "introduced_in_chapter": 1,
                "last_mentioned_chapter": 1,
            },
            {
                "setting_key": "critical.recent",
                "setting_name": "较近关键设定",
                "status": "active",
                "category": "critical",
                "introduced_in_chapter": 8,
                "last_mentioned_chapter": 8,
            },
            {
                "setting_key": "critical.older",
                "setting_name": "更旧关键设定",
                "status": "active",
                "category": "critical",
                "introduced_in_chapter": 6,
                "last_mentioned_chapter": 6,
            },
        ]

        async def mock_list(_pid: str) -> list[dict]:
            return rows

        async def mock_marks(*_args: Any, **_kwargs: Any) -> list[HumanMark]:
            return []

        monkeypatch.setattr(
            "songyan.agents.creative_director.SettingTrackingRepository.list_by_project",
            staticmethod(mock_list),  # type: ignore[arg-type]
        )
        monkeypatch.setattr(
            "songyan.agents.creative_director.HumanMarkRepository.list_by_project",
            staticmethod(mock_marks),  # type: ignore[arg-type]
        )
        result = await _load_active_settings_to_recycle(
            "p1", 12, limit=3, min_silent_chapters=2
        )

        assert [r["setting_key"] for r in result] == [
            "critical.older",
            "critical.recent",
            "background.old",
        ]

    @pytest.mark.asyncio
    async def test_load_recycle_includes_active_human_mark_targets(
        self, monkeypatch: Any
    ) -> None:
        rows = [
            {
                "setting_key": "background.recent-human-held",
                "setting_name": "人工保留世界观前提",
                "status": "active",
                "category": "background",
                "introduced_in_chapter": 1,
                "last_mentioned_chapter": 11,
            },
            {
                "setting_key": "critical.recent-marked",
                "setting_name": "关键待回收项",
                "status": "active",
                "category": "critical",
                "introduced_in_chapter": 7,
                "last_mentioned_chapter": 11,
            },
            {
                "setting_key": "background.old",
                "setting_name": "沉寂背景",
                "status": "active",
                "category": "background",
                "introduced_in_chapter": 1,
                "last_mentioned_chapter": 1,
            },
        ]

        async def mock_list(_pid: str) -> list[dict]:
            return rows

        async def mock_marks(*_args: Any, **_kwargs: Any) -> list[HumanMark]:
            return [
                HumanMark(
                    mark_id="hm-critical",
                    project_id="p1",
                    mark_type="setting",
                    target_key="critical.recent-marked",
                    source="human",
                    priority=9,
                ),
                HumanMark(
                    mark_id="hm-human-held",
                    project_id="p1",
                    mark_type="setting",
                    target_key="background.recent-human-held",
                    source="human",
                    priority=6,
                ),
            ]

        monkeypatch.setattr(
            "songyan.agents.creative_director.SettingTrackingRepository.list_by_project",
            staticmethod(mock_list),  # type: ignore[arg-type]
        )
        monkeypatch.setattr(
            "songyan.agents.creative_director.HumanMarkRepository.list_by_project",
            staticmethod(mock_marks),  # type: ignore[arg-type]
        )

        result = await _load_active_settings_to_recycle(
            "p1", 12, limit=3, min_silent_chapters=2
        )

        assert [r["setting_key"] for r in result] == [
            "critical.recent-marked",
            "background.recent-human-held",
            "background.old",
        ]
        assert result[0]["human_mark_priority"] == 9

    @pytest.mark.asyncio
    async def test_load_recycle_ignores_current_diagnostic_mark_but_keeps_stale_critical(
        self, monkeypatch: Any
    ) -> None:
        rows = [
            {
                "setting_key": "critical.stale-gap",
                "setting_name": "关键真缺口",
                "status": "active",
                "category": "critical",
                "introduced_in_chapter": 7,
                "last_mentioned_chapter": 7,
            },
            {
                "setting_key": "background.current-diagnostic",
                "setting_name": "同章诊断背景项",
                "status": "active",
                "category": "background",
                "introduced_in_chapter": 4,
                "last_mentioned_chapter": 11,
            },
            {
                "setting_key": "background.old-human-held",
                "setting_name": "历史人工保留项",
                "status": "active",
                "category": "background",
                "introduced_in_chapter": 4,
                "last_mentioned_chapter": 11,
            },
        ]

        async def mock_list(_pid: str) -> list[dict]:
            return rows

        async def mock_marks(*_args: Any, **_kwargs: Any) -> list[HumanMark]:
            return [
                HumanMark(
                    mark_id="hm-current-diagnostic",
                    project_id="p1",
                    mark_type="setting",
                    target_key="background.current-diagnostic",
                    source="continuity_auditor",
                    created_at_chapter=12,
                    priority=9,
                ),
                HumanMark(
                    mark_id="hm-old-human-held",
                    project_id="p1",
                    mark_type="setting",
                    target_key="background.old-human-held",
                    source="continuity_auditor",
                    created_at_chapter=9,
                    priority=6,
                ),
            ]

        monkeypatch.setattr(
            "songyan.agents.creative_director.SettingTrackingRepository.list_by_project",
            staticmethod(mock_list),  # type: ignore[arg-type]
        )
        monkeypatch.setattr(
            "songyan.agents.creative_director.HumanMarkRepository.list_by_project",
            staticmethod(mock_marks),  # type: ignore[arg-type]
        )

        result = await _load_active_settings_to_recycle(
            "p1", 12, limit=5, min_silent_chapters=2
        )

        keys = [r["setting_key"] for r in result]
        assert keys == ["critical.stale-gap", "background.old-human-held"]
        assert result[0]["human_mark_priority"] == 0
        assert result[1]["human_mark_priority"] == 6

    def test_format_recycle_marks_stale_critical_as_p1(self) -> None:
        rendered = _format_active_settings_to_recycle(
            [
                {
                    "setting_key": "organization.expedition.team_7",
                    "setting_name": "第7远征队·静默节点",
                    "category": "critical",
                    "introduced_in_chapter": 4,
                    "last_mentioned_chapter": 7,
                    "current_chapter": 12,
                },
                {
                    "setting_key": "background.old",
                    "setting_name": "普通背景设定",
                    "category": "background",
                    "introduced_in_chapter": 1,
                    "last_mentioned_chapter": 4,
                    "current_chapter": 12,
                },
            ]
        )

        assert "第7远征队·静默节点" in rendered
        assert "严重级别：P1" in rendered
        assert "本章必须明确回收、提及、或给出无法回收的剧情原因" in rendered
        background_line = next(
            line for line in rendered.splitlines() if "普通背景设定" in line
        )
        assert "严重级别：P1" not in background_line


class TestTask138hMandatoryReferences:
    """Task 138h: critical orphan 强制回收闭环测试."""

    @pytest.mark.asyncio
    async def test_load_critical_mandatory_references_filters_and_sorts(
        self,
        monkeypatch: Any,
    ) -> None:
        """_load_critical_mandatory_references 返回 active+critical+达阈值项，按沉寂降序."""
        from songyan.workflows._helpers import _load_critical_mandatory_references

        mock_rows = [
            {
                "setting_key": "artifact.mega_ruin.surface_material",
                "setting_name": "巨型遗迹表面材料特性",
                "status": "active",
                "category": "critical",
                "last_mentioned_chapter": 3,
                "introduced_in_chapter": 3,
            },
            {
                "setting_key": "artifact.ruin.phase_flush_mechanism",
                "setting_name": "相位冲刷机制",
                "status": "active",
                "category": "critical",
                "last_mentioned_chapter": 7,
                "introduced_in_chapter": 7,
            },
            {
                "setting_key": "background.old",
                "setting_name": "普通背景设定",
                "status": "active",
                "category": "background",
                "last_mentioned_chapter": 2,
                "introduced_in_chapter": 1,
            },
            {
                "setting_key": "archived.setting",
                "setting_name": "已归档设定",
                "status": "archived",
                "category": "critical",
                "last_mentioned_chapter": 1,
                "introduced_in_chapter": 1,
            },
        ]

        async def mock_list(self, _project_id: str) -> list[dict]:
            return mock_rows

        monkeypatch.setattr(
            "songyan.workflows._helpers.SettingTrackingRepository.list_by_project",
            mock_list,
        )

        result = await _load_critical_mandatory_references("proj-test", 12)

        assert len(result) == 2
        # surface_material: 12 - 3 = 9 章沉寂
        # phase_flush: 12 - 7 = 5 章沉寂
        # 按降序排列
        assert result[0]["setting_key"] == "artifact.mega_ruin.surface_material"
        assert result[0]["silent_chapters"] == 9
        assert result[1]["setting_key"] == "artifact.ruin.phase_flush_mechanism"
        assert result[1]["silent_chapters"] == 5

    @pytest.mark.asyncio
    async def test_load_critical_mandatory_references_excludes_below_threshold(
        self,
        monkeypatch: Any,
    ) -> None:
        """沉寂章数 < ORPHANED_THRESHOLDS['critical']（默认 3）的项应被排除."""
        from songyan.workflows._helpers import _load_critical_mandatory_references

        mock_rows = [
            {
                "setting_key": "just.below.threshold",
                "setting_name": "刚好低于阈值",
                "status": "active",
                "category": "critical",
                "last_mentioned_chapter": 10,  # 12 - 10 = 2 < 3
                "introduced_in_chapter": 8,
            },
        ]

        async def mock_list(self, _project_id: str) -> list[dict]:
            return mock_rows

        monkeypatch.setattr(
            "songyan.workflows._helpers.SettingTrackingRepository.list_by_project",
            mock_list,
        )

        result = await _load_critical_mandatory_references("proj-test", 12)
        assert result == []

    def test_render_prompt_includes_mandatory_references(self) -> None:
        """Writer _render_prompt 应在输出中包含 mandatory_references 块."""
        from songyan.agents.writer import _render_prompt
        from songyan.models import ChapterGoal, ContextPackage

        goal = ChapterGoal(
            chapter_number=12,
            word_count_target=3000,
            target_events=["测试事件"],
            hooks=["测试钩子"],
            obligations=["测试义务"],
        )
        ctx = ContextPackage(
            chapter_goal=goal,
            mandatory_references=[
                {
                    "setting_key": "artifact.mega_ruin.surface_material",
                    "setting_name": "巨型遗迹表面材料特性",
                    "silent_chapters": 9,
                }
            ],
        )

        prompt = _render_prompt(ctx)

        assert "强制连续性约束" in prompt
        assert "巨型遗迹表面材料特性" in prompt
        assert "已沉寂 9 章" in prompt
        assert "不是建议，而是强制约束" in prompt

    def test_render_prompt_omits_empty_mandatory_references(self) -> None:
        """当 mandatory_references 为空时，prompt 中不应出现该块."""
        from songyan.agents.writer import _render_prompt
        from songyan.models import ChapterGoal, ContextPackage

        goal = ChapterGoal(
            chapter_number=12,
            word_count_target=3000,
            target_events=["测试事件"],
            hooks=["测试钩子"],
            obligations=["测试义务"],
        )
        ctx = ContextPackage(chapter_goal=goal)

        prompt = _render_prompt(ctx)

        assert "强制连续性约束" not in prompt

    def test_check_mandatory_references_detects_missing(self) -> None:
        """_check_mandatory_references 应检测到正文中未提及的 reference."""
        from songyan.agents.rule_auditor import _check_mandatory_references

        content = "这是一段普通正文，没有任何设定提及。"
        refs = [
            {
                "setting_key": "artifact.mega_ruin.surface_material",
                "setting_name": "巨型遗迹表面材料特性",
                "silent_chapters": 9,
            },
        ]
        passed, issues = _check_mandatory_references(content, refs)
        assert passed is False
        assert len(issues) == 1
        assert issues[0]["setting_name"] == "巨型遗迹表面材料特性"

    def test_check_mandatory_references_detects_present_by_name(self) -> None:
        """正文中出现 setting_name 时应视为已回收."""
        from songyan.agents.rule_auditor import _check_mandatory_references

        content = "遗迹表面材料特性一致，非欧几何合金碎片在钻探点周围大量分布。"
        refs = [
            {
                "setting_key": "artifact.mega_ruin.surface_material",
                "setting_name": "表面材料特性",
                "silent_chapters": 9,
            },
        ]
        passed, issues = _check_mandatory_references(content, refs)
        assert passed is True
        assert issues == []

    def test_check_mandatory_references_detects_present_by_key_alias(self) -> None:
        """正文中出现 key 的最后一个 segment（如 surface_material）时应视为已回收."""
        from songyan.agents.rule_auditor import _check_mandatory_references

        content = "这次钻探发现 surface_material 与之前一致。"
        refs = [
            {
                "setting_key": "artifact.mega_ruin.surface_material",
                "setting_name": "巨型遗迹表面材料特性",
                "silent_chapters": 9,
            },
        ]
        passed, issues = _check_mandatory_references(content, refs)
        assert passed is True
        assert issues == []

    def test_run_rule_audit_with_mandatory_references(self) -> None:
        """run_rule_audit 传入 mandatory_references 后应正确反映检查结果."""
        from songyan.agents.rule_auditor import (
            _compute_overall_score,
            run_rule_audit,
        )

        content = "普通正文，没有提及任何设定。"
        refs = [
            {
                "setting_key": "artifact.mega_ruin.surface_material",
                "setting_name": "巨型遗迹表面材料特性",
                "silent_chapters": 9,
            },
            {
                "setting_key": "artifact.ruin.phase_flush_mechanism",
                "setting_name": "相位冲刷机制",
                "silent_chapters": 5,
            },
        ]
        result = run_rule_audit(content, mandatory_references=refs)
        assert result.mandatory_reference_check_passed is False
        assert len(result.mandatory_reference_issues) == 2
        assert "巨型遗迹表面材料特性" == result.mandatory_reference_issues[0]["setting_name"]
        assert "相位冲刷机制" == result.mandatory_reference_issues[1]["setting_name"]
        # 扣分验证：每个 -1.5，最多 -3
        score = _compute_overall_score(result)
        assert score <= 7.0


class TestTask138jRecycleHints:
    """Task 138j: Writer 回收提示测试."""

    def test_infer_recycle_hint_known_alias(self) -> None:
        """_infer_recycle_hint 对已知 key_alias 返回正确提示."""
        from songyan.workflows._helpers import _infer_recycle_hint

        assert "环境描写" in _infer_recycle_hint("surface_material")
        assert "技术原理" in _infer_recycle_hint("phase_flush_mechanism")
        assert "团队行动" in _infer_recycle_hint("team_7")
        assert "空间环境描写" in _infer_recycle_hint("core_space")
        assert "墙壁的异常行为" in _infer_recycle_hint("living_wall")

    def test_infer_recycle_hint_unknown_alias(self) -> None:
        """_infer_recycle_hint 对未知 key_alias 返回兜底提示."""
        from songyan.workflows._helpers import _infer_recycle_hint

        hint = _infer_recycle_hint("unknown_setting_key")
        assert "角色对话回顾" in hint
        assert "环境细节呼应" in hint
        assert "剧情事件直接触发" in hint

    @pytest.mark.asyncio
    async def test_load_critical_mandatory_references_includes_recycle_hint(
        self,
        monkeypatch: Any,
    ) -> None:
        """_load_critical_mandatory_references 返回的结果应包含 recycle_hint."""
        from songyan.workflows._helpers import _load_critical_mandatory_references

        mock_rows = [
            {
                "setting_key": "artifact.mega_ruin.surface_material",
                "setting_name": "巨型遗迹表面材料特性",
                "status": "active",
                "category": "critical",
                "last_mentioned_chapter": 3,
                "introduced_in_chapter": 3,
            },
        ]

        async def mock_list(self, _project_id: str) -> list[dict]:
            return mock_rows

        monkeypatch.setattr(
            "songyan.workflows._helpers.SettingTrackingRepository.list_by_project",
            mock_list,
        )

        result = await _load_critical_mandatory_references("proj-test", 12)

        assert len(result) == 1
        assert "recycle_hint" in result[0]
        assert "环境描写" in result[0]["recycle_hint"]

    def test_render_prompt_includes_recycle_hint(self) -> None:
        """Writer _render_prompt 应在输出中包含 recycle_hint."""
        from songyan.agents.writer import _render_prompt
        from songyan.models import ChapterGoal, ContextPackage

        goal = ChapterGoal(
            chapter_number=12,
            word_count_target=3000,
            target_events=["测试事件"],
            hooks=["测试钩子"],
            obligations=["测试义务"],
        )
        ctx = ContextPackage(
            chapter_goal=goal,
            mandatory_references=[
                {
                    "setting_key": "artifact.mega_ruin.surface_material",
                    "setting_name": "巨型遗迹表面材料特性",
                    "silent_chapters": 9,
                    "recycle_hint": "可通过环境描写（触感、视觉观察）来回收",
                }
            ],
        )

        prompt = _render_prompt(ctx)

        assert "【建议】" in prompt
        assert "环境描写（触感、视觉观察）" in prompt
        assert "巨型遗迹表面材料特性" in prompt
