"""Tests for Task 152 — critical 设定显式 resolve / 作废出口.

覆盖：生命周期状态迁移与可追溯性、非法迁移拒绝、settlement 证据联动、
metrics 区分显式 resolve/abandon 与逾期归档、显式外部废弃信号。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from songyan.db.continuity_repo import SettingTrackingRepository
from songyan.db.repository import ProjectRepository
from songyan.evals.db_metrics import collect_setting_lifecycle_metrics
from songyan.models import ForeshadowingUpdate, NewSetting, ProjectSetting, StateSettlement
from songyan.workflows._input_side_governance import (
    abandon_setting_explicitly,
    resolve_settings_after_settlement,
)

PID = "proj-152"


async def _seed_project() -> None:
    await ProjectRepository().create(
        ProjectSetting(genre_id="xuanhuan", protagonist_name="英雄"),
        PID,
    )


async def _create_tracking(
    key: str,
    *,
    chapter: int,
    category: str = "critical",
    status: str = "active",
    name: str = "",
    description: str = "",
    version_id: str = "v0",
) -> None:
    await SettingTrackingRepository().create(
        tracking_id=f"track-{PID}-{key}",
        project_id=PID,
        setting_key=key,
        setting_name=name or key,
        description=description,
        introduced_in_chapter=chapter,
        source_version_id=version_id,
        category=category,
        status=status,
    )


class TestResolveSettingLifecycle:
    async def test_resolve_setting_transitions_and_traceability(self, test_db: Path) -> None:
        await _seed_project()
        await _create_tracking("resolve-me", chapter=2, status="active")

        row = (await SettingTrackingRepository().list_by_project(PID))[0]
        await SettingTrackingRepository().resolve_setting(
            row["tracking_id"], chapter=5, source_version_id="v5"
        )

        row = (await SettingTrackingRepository().list_by_project(PID))[0]
        assert row["status"] == "resolved"
        assert row["resolved_chapter"] == 5
        assert row["resolved_version_id"] == "v5"

        orphans = await SettingTrackingRepository().find_orphaned(
            PID, up_to_chapter=10, threshold=1
        )
        assert all(o["setting_key"] != "resolve-me" for o in orphans)

    async def test_resolve_rejects_invalid_transition(self, test_db: Path) -> None:
        await _seed_project()
        await _create_tracking("already-resolved", chapter=2, status="active")

        row = (await SettingTrackingRepository().list_by_project(PID))[0]
        await SettingTrackingRepository().resolve_setting(
            row["tracking_id"], chapter=3, source_version_id="v3"
        )

        with pytest.raises(ValueError):
            await SettingTrackingRepository().resolve_setting(
                row["tracking_id"], chapter=4, source_version_id="v4"
            )


class TestAbandonSettingLifecycle:
    async def test_abandon_setting_transitions_and_traceability(self, test_db: Path) -> None:
        await _seed_project()
        await _create_tracking("abandon-me", chapter=2, status="active")

        row = (await SettingTrackingRepository().list_by_project(PID))[0]
        await SettingTrackingRepository().abandon_setting(
            row["tracking_id"], chapter=7, reason="outline dropped"
        )

        row = (await SettingTrackingRepository().list_by_project(PID))[0]
        assert row["status"] == "abandoned"
        assert row["abandoned_chapter"] == 7
        assert row["abandoned_reason"] == "outline dropped"

        orphans = await SettingTrackingRepository().find_orphaned(
            PID, up_to_chapter=10, threshold=1
        )
        assert all(o["setting_key"] != "abandon-me" for o in orphans)

    async def test_abandon_rejects_invalid_transition(self, test_db: Path) -> None:
        await _seed_project()
        await _create_tracking("resolved-then-abandon", chapter=2, status="active")

        row = (await SettingTrackingRepository().list_by_project(PID))[0]
        await SettingTrackingRepository().resolve_setting(
            row["tracking_id"], chapter=3, source_version_id="v3"
        )

        with pytest.raises(ValueError):
            await SettingTrackingRepository().abandon_setting(
                row["tracking_id"], chapter=4, reason="too late"
            )


class TestResolveAfterSettlement:
    async def test_resolve_after_settlement_by_hook(self, test_db: Path) -> None:
        await _seed_project()
        await _create_tracking(
            "ancient-seal",
            chapter=2,
            status="active",
            name="上古封印",
            description="封印着远古恶魔的结界",
        )

        settlement = StateSettlement(
            resolved_hooks=["上古封印的真相揭开，ancient-seal 彻底消散"]
        )
        resolved = await resolve_settings_after_settlement(
            PID, chapter_number=5, version_id="v5", settlement=settlement
        )

        assert "ancient-seal" in resolved
        row = (await SettingTrackingRepository().list_by_project(PID))[0]
        assert row["status"] == "resolved"
        assert row["resolved_chapter"] == 5
        assert row["resolved_version_id"] == "v5"

    async def test_resolve_after_settlement_by_foreshadowing(self, test_db: Path) -> None:
        await _seed_project()
        await _create_tracking(
            "star-gate-key",
            chapter=2,
            status="active",
            name="星门密钥",
            description="开启星门的古老密钥",
        )

        settlement = StateSettlement(
            foreshadowing_updates=[
                ForeshadowingUpdate(
                    operation="resolve",
                    description="星门密钥在遗迹深处被回收",
                )
            ]
        )
        resolved = await resolve_settings_after_settlement(
            PID, chapter_number=6, version_id="v6", settlement=settlement
        )

        assert "star-gate-key" in resolved
        row = (await SettingTrackingRepository().list_by_project(PID))[0]
        assert row["status"] == "resolved"

    async def test_no_resolve_without_evidence(self, test_db: Path) -> None:
        await _seed_project()
        await _create_tracking("unreferenced", chapter=2, status="active", name="未提及设定")

        settlement = StateSettlement(
            new_settings=[
                NewSetting(
                    setting_key="other",
                    setting_name="无关设定",
                    description="与本章无关",
                    source_quote="",
                )
            ],
            resolved_hooks=["另一件事收束"],
        )
        resolved = await resolve_settings_after_settlement(
            PID, chapter_number=5, version_id="v5", settlement=settlement
        )

        assert resolved == []
        row = (await SettingTrackingRepository().list_by_project(PID))[0]
        assert row["status"] == "active"

    async def test_candidate_can_be_resolved(self, test_db: Path) -> None:
        await _seed_project()
        await _create_tracking(
            "candidate-key",
            chapter=2,
            status="candidate",
            name="候选设定",
        )

        settlement = StateSettlement(resolved_hooks=["候选设定在本章被交代收束"])
        resolved = await resolve_settings_after_settlement(
            PID, chapter_number=5, version_id="v5", settlement=settlement
        )

        assert "candidate-key" in resolved
        row = (await SettingTrackingRepository().list_by_project(PID))[0]
        assert row["status"] == "resolved"


class TestPrematureResolveHardening:
    """#2 回归：防止主线核心短名词在无关钩子里被裸子串误判 resolved（参照 Task 144）."""

    async def test_short_name_not_resolved_by_bare_substring(self, test_db: Path) -> None:
        await _seed_project()
        # 主线核心短名词"灰塔"（2 字），往期引入
        await _create_tracking("gray-tower", chapter=2, status="active", name="灰塔")

        # 章末钩子频繁提及"灰塔"，但并非真正收束该设定
        settlement = StateSettlement(
            resolved_hooks=["主角远远望见灰塔的轮廓，心中升起不安"]
        )
        resolved = await resolve_settings_after_settlement(
            PID, chapter_number=6, version_id="v6", settlement=settlement
        )

        # 短名词裸子串命中不应触发 resolve
        assert resolved == []
        row = (await SettingTrackingRepository().list_by_project(PID))[0]
        assert row["status"] == "active"

    async def test_long_name_still_resolved_by_substring(self, test_db: Path) -> None:
        await _seed_project()
        await _create_tracking(
            "ancient-seal", chapter=2, status="active", name="上古封印结界"
        )

        settlement = StateSettlement(
            resolved_hooks=["历经苦战，上古封印结界终于被彻底解除"]
        )
        resolved = await resolve_settings_after_settlement(
            PID, chapter_number=6, version_id="v6", settlement=settlement
        )
        assert "ancient-seal" in resolved

    async def test_current_chapter_critical_not_resolved_same_chapter(
        self, test_db: Path
    ) -> None:
        """本章刚引入的 critical 不在同一章被收束（避免开局即终态化）."""
        await _seed_project()
        await _create_tracking(
            "new-seal", chapter=5, status="active", name="本章新封印结界"
        )

        settlement = StateSettlement(resolved_hooks=["本章新封印结界被解除"])
        resolved = await resolve_settings_after_settlement(
            PID, chapter_number=5, version_id="v5", settlement=settlement
        )
        assert resolved == []
        row = (await SettingTrackingRepository().list_by_project(PID))[0]
        assert row["status"] == "active"


class TestMetricsAndExplicitSignal:
    async def test_metrics_distinguish_resolved_abandoned_archived(self, test_db: Path) -> None:
        await _seed_project()
        # active orphan
        await _create_tracking("active-orphan", chapter=1, status="active")
        # resolved
        await _create_tracking("resolved-one", chapter=1, status="active")
        resolved_row = (await SettingTrackingRepository().list_by_project(PID))[1]
        await SettingTrackingRepository().resolve_setting(
            resolved_row["tracking_id"], chapter=3, source_version_id="v3"
        )
        # abandoned
        await _create_tracking("abandoned-one", chapter=1, status="active")
        abandoned_row = (await SettingTrackingRepository().list_by_project(PID))[2]
        await SettingTrackingRepository().abandon_setting(
            abandoned_row["tracking_id"], chapter=3, reason="outline dropped"
        )
        # archived
        await _create_tracking("archived-one", chapter=1, status="archived")

        orphans = await SettingTrackingRepository().find_orphaned(
            PID, up_to_chapter=10, threshold=1
        )
        assert len(orphans) == 1
        assert orphans[0]["setting_key"] == "active-orphan"

        metrics = await collect_setting_lifecycle_metrics(PID)
        assert metrics.active_count == 1
        assert metrics.resolved_count == 1
        assert metrics.abandoned_count == 1
        assert metrics.archived_count == 1

    async def test_abandon_explicit_signal(self, test_db: Path) -> None:
        await _seed_project()
        await _create_tracking("abandon-signal", chapter=2, status="active")

        await abandon_setting_explicitly(
            PID,
            setting_key="abandon-signal",
            chapter_number=7,
            reason="arc plan removed",
        )

        row = (await SettingTrackingRepository().list_by_project(PID))[0]
        assert row["status"] == "abandoned"
        assert row["abandoned_chapter"] == 7
        assert row["abandoned_reason"] == "arc plan removed"
