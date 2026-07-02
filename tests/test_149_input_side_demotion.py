"""Tests for Task 149 — 录入侧降级（超额 critical 转 candidate，非硬丢弃）.

覆盖：候选态写入/回升/不进 orphan、超额降级路由、T7 口径守约、无骨架项目兼容。
"""

from __future__ import annotations

from pathlib import Path

from songyan.db.continuity_repo import SettingTrackingRepository
from songyan.db.repository import ProjectRepository
from songyan.models import NewSetting, ProjectSetting, StateSettlement
from songyan.workflows._input_side_governance import (
    demote_overflow_new_settings,
    promote_candidate_settings_after_settlement,
)


async def _seed_project(project_id: str = "proj-149") -> str:
    await ProjectRepository().create(
        ProjectSetting(genre_id="xuanhuan", protagonist_name="英雄"),
        project_id,
    )
    return project_id


async def _create_tracking(
    project_id: str,
    key: str,
    *,
    chapter: int,
    category: str = "background",
    status: str = "active",
    name: str = "",
    description: str = "",
    version_id: str = "v0",
) -> None:
    await SettingTrackingRepository().create(
        tracking_id=f"track-{project_id}-{key}",
        project_id=project_id,
        setting_key=key,
        setting_name=name or key,
        description=description,
        introduced_in_chapter=chapter,
        source_version_id=version_id,
        category=category,
        status=status,
    )


class TestCandidateLifecycle:
    async def test_candidate_created_and_not_orphan(self, test_db: Path) -> None:
        pid = await _seed_project()
        await _create_tracking(
            pid,
            "candidate-setting",
            chapter=2,
            category="critical",
            status="candidate",
        )

        orphans = await SettingTrackingRepository().find_orphaned(pid, up_to_chapter=10)
        assert all(o["setting_key"] != "candidate-setting" for o in orphans)

        rows = await SettingTrackingRepository().list_by_project(pid)
        assert len(rows) == 1
        assert rows[0]["status"] == "candidate"

    async def test_promote_to_active(self, test_db: Path) -> None:
        pid = await _seed_project()
        await _create_tracking(
            pid,
            "promote-me",
            chapter=2,
            category="critical",
            status="candidate",
            version_id="v-old",
        )

        row = (await SettingTrackingRepository().list_by_project(pid))[0]
        await SettingTrackingRepository().promote_to_active(
            row["tracking_id"], chapter=5, source_version_id="v-new"
        )

        row = (await SettingTrackingRepository().list_by_project(pid))[0]
        assert row["status"] == "active"
        assert row["last_mentioned_chapter"] == 5
        assert row["source_version_id"] == "v-new"


class TestDemotionRouting:
    async def test_demote_overflow_routes_first_cap_active(self, test_db: Path) -> None:
        pid = await _seed_project()
        keys = [f"critical-{i}" for i in range(5)]
        for key in keys:
            await _create_tracking(pid, key, chapter=3, category="critical", status="active")

        # 索引 0/2/4 有 source_quote（证据完整），1/3 无
        settlement = StateSettlement(
            new_settings=[
                NewSetting(
                    setting_key=keys[i],
                    setting_name=keys[i],
                    description=f"desc {i}",
                    source_quote=f"quote {i}" if i % 2 == 0 else "",
                )
                for i in range(5)
            ]
        )

        demoted = await demote_overflow_new_settings(
            pid, chapter_number=3, version_id="v3", settlement=settlement, critical_cap=3
        )

        # 期望保留 0/2/4（有证据），降级 1/3
        assert demoted == [keys[1], keys[3]]

        rows = {r["setting_key"]: r for r in await SettingTrackingRepository().list_by_project(pid)}
        assert rows[keys[0]]["status"] == "active"
        assert rows[keys[2]]["status"] == "active"
        assert rows[keys[4]]["status"] == "active"
        assert rows[keys[1]]["status"] == "candidate"
        assert rows[keys[3]]["status"] == "candidate"

    async def test_no_demotion_when_under_cap(self, test_db: Path) -> None:
        pid = await _seed_project()
        keys = ["crit-a", "crit-b"]
        for key in keys:
            await _create_tracking(pid, key, chapter=4, category="critical", status="active")

        settlement = StateSettlement(
            new_settings=[
                NewSetting(setting_key=k, setting_name=k, description="d", source_quote="")
                for k in keys
            ]
        )

        demoted = await demote_overflow_new_settings(
            pid, chapter_number=4, version_id="v4", settlement=settlement, critical_cap=3
        )
        assert demoted == []

        rows = await SettingTrackingRepository().list_by_project(pid)
        assert all(r["status"] == "active" for r in rows)

    async def test_demotion_no_skeleton_project(self, test_db: Path) -> None:
        """候选机制不依赖叙事骨架，无骨架项目同样工作."""
        pid = await _seed_project()
        keys = [f"noskel-{i}" for i in range(4)]
        for key in keys:
            await _create_tracking(pid, key, chapter=1, category="critical", status="active")

        settlement = StateSettlement(
            new_settings=[
                NewSetting(setting_key=k, setting_name=k, description="d", source_quote="q")
                for k in keys
            ]
        )

        demoted = await demote_overflow_new_settings(
            pid, chapter_number=1, version_id="v1", settlement=settlement, critical_cap=2
        )
        assert len(demoted) == 2

        rows = {r["setting_key"]: r for r in await SettingTrackingRepository().list_by_project(pid)}
        active_count = sum(1 for r in rows.values() if r["status"] == "active")
        candidate_count = sum(1 for r in rows.values() if r["status"] == "candidate")
        assert active_count == 2
        assert candidate_count == 2


class TestT7Compliance:
    async def test_demote_does_not_filter_t7(self, test_db: Path) -> None:
        """new_settings_by_chapter 无 status 过滤，candidate critical 仍计入 T7 写入侧."""
        pid = await _seed_project()
        await _create_tracking(
            pid, "t7-crit", chapter=3, category="critical", status="candidate"
        )

        stats = await SettingTrackingRepository().new_settings_by_chapter(pid, 1, 5)
        critical_rows = [s for s in stats if s["category"] == "critical"]
        assert len(critical_rows) == 1
        assert critical_rows[0]["introduced_in_chapter"] == 3
        assert critical_rows[0]["count"] == 1


class TestCandidatePromotion:
    async def test_promote_candidate_on_evidence_match(self, test_db: Path) -> None:
        pid = await _seed_project()
        await _create_tracking(
            pid,
            "star-gate-key",
            chapter=2,
            category="critical",
            status="candidate",
            name="星门密钥",
            description="开启星门的古老密钥",
            version_id="v2",
        )

        settlement = StateSettlement(
            new_settings=[
                NewSetting(
                    setting_key="some-ref",
                    setting_name="伏笔提及",
                    description="本章再次提到星门密钥的下落",
                    source_quote="星门密钥落在废墟深处",
                )
            ]
        )

        promoted = await promote_candidate_settings_after_settlement(
            pid, chapter_number=5, version_id="v5", settlement=settlement
        )

        assert promoted == ["star-gate-key"]
        row = (await SettingTrackingRepository().list_by_project(pid))[0]
        assert row["status"] == "active"
        assert row["last_mentioned_chapter"] == 5
        assert row["source_version_id"] == "v5"

    async def test_no_promotion_without_evidence(self, test_db: Path) -> None:
        pid = await _seed_project()
        await _create_tracking(
            pid,
            "unreferenced",
            chapter=2,
            category="critical",
            status="candidate",
            name="未提及设定",
        )

        settlement = StateSettlement(
            new_settings=[
                NewSetting(
                    setting_key="other",
                    setting_name="无关设定",
                    description="与本章无关",
                    source_quote="",
                )
            ]
        )

        promoted = await promote_candidate_settings_after_settlement(
            pid, chapter_number=5, version_id="v5", settlement=settlement
        )
        assert promoted == []

        row = (await SettingTrackingRepository().list_by_project(pid))[0]
        assert row["status"] == "candidate"


class TestSameChapterDemotePromoteInteraction:
    """#1 回归：同一章 demote 后立刻 promote，本章刚降级的候选不得被当章回升抵消."""

    async def test_current_chapter_demotion_not_re_promoted(self, test_db: Path) -> None:
        pid = await _seed_project()
        keys = [f"crit-{i}" for i in range(5)]
        for key in keys:
            await _create_tracking(pid, key, chapter=3, category="critical", status="active")

        settlement = StateSettlement(
            new_settings=[
                NewSetting(
                    setting_key=keys[i],
                    setting_name=keys[i],
                    description=f"desc {i}",
                    source_quote=f"quote {i}" if i % 2 == 0 else "",
                )
                for i in range(5)
            ]
        )

        # 复现 _nodes.py 的真实接线顺序：先 demote，再用同一 settlement promote
        demoted = await demote_overflow_new_settings(
            pid, chapter_number=3, version_id="v3", settlement=settlement, critical_cap=3
        )
        assert len(demoted) == 2
        promoted = await promote_candidate_settings_after_settlement(
            pid, chapter_number=3, version_id="v3", settlement=settlement
        )

        # 本章刚降级的候选不应被当章回升
        assert promoted == []
        rows = {r["setting_key"]: r for r in await SettingTrackingRepository().list_by_project(pid)}
        candidates = sorted(k for k, r in rows.items() if r["status"] == "candidate")
        assert candidates == sorted(demoted)

    async def test_prior_chapter_candidate_still_promotable(self, test_db: Path) -> None:
        """往期遗留的候选在后续章证据命中时仍应回升（回升机制未被误关）."""
        pid = await _seed_project()
        await _create_tracking(
            pid,
            "old-candidate",
            chapter=2,
            category="critical",
            status="candidate",
            name="旧候选设定",
        )

        settlement = StateSettlement(
            new_settings=[
                NewSetting(
                    setting_key="ref",
                    setting_name="提及",
                    description="本章再次提到旧候选设定",
                    source_quote="旧候选设定重新登场",
                )
            ]
        )
        promoted = await promote_candidate_settings_after_settlement(
            pid, chapter_number=6, version_id="v6", settlement=settlement
        )
        assert promoted == ["old-candidate"]
