"""Tests for setting_snapshots + foreshadowings lifecycle — V4.0 Task 084."""

from __future__ import annotations

from pathlib import Path

import pytest

from songyan.db.connection import get_db
from songyan.db.migrations import init_schema
from songyan.db.settlement_repo import ForeshadowingRepository, SettingSnapshotRepository
from songyan.models import ForeshadowingItem, NewSetting

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def lifecycle_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """指向临时初始化数据库的 fixture."""
    import songyan.db.connection as conn_mod

    db_path = tmp_path / "lifecycle_sf.db"
    monkeypatch.setattr(
        conn_mod,
        "settings",
        type("S", (), {"database_url": f"sqlite:///{db_path}"})(),
    )
    await init_schema(db_path)
    async with get_db() as conn:
        await conn.execute(
            """INSERT INTO projects (project_id, title, genre_id, protagonist_name)
            VALUES (?, ?, ?, ?)""",
            ("p-1", "Test", "xuanhuan", "Lin"),
        )
        await conn.execute(
            """INSERT INTO chapter_versions (
                version_id, project_id, chapter_number, version_number, version_type
            ) VALUES (?, ?, ?, ?, ?)""",
            ("v-1", "p-1", 1, 1, "accepted"),
        )
        await conn.commit()
    return db_path


# ---------------------------------------------------------------------------
# ForeshadowingRepository Tests
# ---------------------------------------------------------------------------

class TestForeshadowingLifecycle:
    async def test_list_active_filters_lifecycle_status(self, lifecycle_db: Path) -> None:
        """list_active 只返回 lifecycle_status='active' 的记录."""
        repo = ForeshadowingRepository()
        await repo.create(
            ForeshadowingItem(
                foreshadowing_id="fs-1",
                description="active",
                planted_in_chapter=1,
                expected_resolve_chapter=10,
                status="planted",
            ),
            "p-1",
            "v-1",
        )
        await repo.create(
            ForeshadowingItem(
                foreshadowing_id="fs-2",
                description="resolved",
                planted_in_chapter=1,
                expected_resolve_chapter=10,
                status="resolved",
            ),
            "p-1",
            "v-1",
        )

        # 手动将 fs-2 的 lifecycle_status 改为 active（resolved 本应被 archive_resolved 处理）
        async with get_db() as conn:
            await conn.execute(
                "UPDATE foreshadowings SET lifecycle_status = 'active' WHERE foreshadowing_id = ?",
                ("fs-2",),
            )
            await conn.commit()

        active = await repo.list_active("p-1")
        ids = {fs.foreshadowing_id for fs in active}
        # fs-2 的 status='resolved'，被业务过滤排除
        assert "fs-1" in ids
        assert "fs-2" not in ids

    async def test_archive_overdue(self, lifecycle_db: Path) -> None:
        """overdue > 5 章 → dormant."""
        repo = ForeshadowingRepository()
        await repo.create(
            ForeshadowingItem(
                foreshadowing_id="fs-old",
                description="old",
                planted_in_chapter=1,
                expected_resolve_chapter=10,
                status="planted",
            ),
            "p-1",
            "v-1",
        )
        archived = await repo.archive_overdue("p-1", current_chapter=60, window=5)
        assert archived == 1

        active = await repo.list_active("p-1")
        ids = {fs.foreshadowing_id for fs in active}
        assert "fs-old" not in ids

    async def test_archive_overdue_does_not_touch_resolved(self, lifecycle_db: Path) -> None:
        """resolved 不被 archive_overdue 归档."""
        repo = ForeshadowingRepository()
        await repo.create(
            ForeshadowingItem(
                foreshadowing_id="fs-resolved",
                description="resolved",
                planted_in_chapter=1,
                expected_resolve_chapter=10,
                status="resolved",
            ),
            "p-1",
            "v-1",
        )
        archived = await repo.archive_overdue("p-1", current_chapter=60, window=5)
        assert archived == 0

    async def test_archive_very_overdue(self, lifecycle_db: Path) -> None:
        """dormant + overdue > 15 章 → archived."""
        repo = ForeshadowingRepository()
        await repo.create(
            ForeshadowingItem(
                foreshadowing_id="fs-very-old",
                description="very old",
                planted_in_chapter=1,
                expected_resolve_chapter=10,
                status="planted",
            ),
            "p-1",
            "v-1",
        )
        # 先 dormant
        await repo.archive_overdue("p-1", current_chapter=60, window=5)
        # 再 archived
        archived = await repo.archive_very_overdue("p-1", current_chapter=60, window=15)
        assert archived == 1

    async def test_archive_resolved(self, lifecycle_db: Path) -> None:
        """resolved → archived."""
        repo = ForeshadowingRepository()
        await repo.create(
            ForeshadowingItem(
                foreshadowing_id="fs-resolved",
                description="resolved",
                planted_in_chapter=1,
                expected_resolve_chapter=10,
                status="resolved",
            ),
            "p-1",
            "v-1",
        )
        archived = await repo.archive_resolved("p-1")
        assert archived == 1


# ---------------------------------------------------------------------------
# SettingSnapshotRepository Tests
# ---------------------------------------------------------------------------

class TestSettingSnapshotLifecycle:
    async def _seed_setting_tracking(self, setting_key: str, last_mentioned: int) -> None:
        async with get_db() as conn:
            await conn.execute(
                """INSERT INTO setting_tracking
                    (tracking_id, project_id, setting_key, setting_name, description,
                     introduced_in_chapter, last_mentioned_chapter)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    f"tr-{setting_key}", "p-1", setting_key, setting_key,
                    "desc", 1, last_mentioned,
                ),
            )
            await conn.commit()

    async def test_list_by_project_filters_lifecycle_status(self, lifecycle_db: Path) -> None:
        """list_by_project 只返回 lifecycle_status='active' 的记录."""
        repo = SettingSnapshotRepository()
        await repo.create(
            NewSetting(setting_name="s1", description="d1", source_quote="q1", setting_key="k1"),
            "p-1", "ss-1",
        )
        await repo.create(
            NewSetting(setting_name="s2", description="d2", source_quote="q2", setting_key="k2"),
            "p-1", "ss-2",
        )
        # 手动将 ss-2 标记为 dormant
        async with get_db() as conn:
            await conn.execute(
                "UPDATE setting_snapshots SET lifecycle_status = 'dormant' WHERE setting_id = ?",
                ("ss-2",),
            )
            await conn.commit()

        active = await repo.list_by_project("p-1")
        names = {s.setting_name for s in active}
        assert "s1" in names
        assert "s2" not in names

    async def test_archive_stale(self, lifecycle_db: Path) -> None:
        """10 章未提及 → dormant（通过 setting_tracking）."""
        repo = SettingSnapshotRepository()
        await repo.create(
            NewSetting(
                setting_name="stale", description="d", source_quote="q",
                setting_key="stale-key",
            ),
            "p-1", "ss-stale",
        )
        await self._seed_setting_tracking("stale-key", last_mentioned=10)

        archived = await repo.archive_stale("p-1", current_chapter=25, window=10)
        assert archived == 1  # 25 - 10 = 15 > 10

    async def test_archive_stale_does_not_touch_critical(self, lifecycle_db: Path) -> None:
        """is_critical（human_marks priority>=8）不被归档."""
        repo = SettingSnapshotRepository()
        await repo.create(
            NewSetting(
                setting_name="critical", description="d", source_quote="q",
                setting_key="critical-key",
            ),
            "p-1", "ss-critical",
        )
        await self._seed_setting_tracking("critical-key", last_mentioned=10)
        # 创建 priority=8 的 human_mark
        async with get_db() as conn:
            await conn.execute(
                """INSERT INTO human_marks
                    (mark_id, project_id, mark_type, target_key, priority, lifecycle_status)
                VALUES (?, ?, ?, ?, ?, ?)""",
                ("hm-1", "p-1", "setting", "critical-key", 8, "active"),
            )
            await conn.commit()

        archived = await repo.archive_stale("p-1", current_chapter=25, window=10)
        assert archived == 0

    async def test_archive_stale_boundary(self, lifecycle_db: Path) -> None:
        """边界：刚好 10 章 → 不归档；第 11 章 → 归档."""
        repo = SettingSnapshotRepository()
        await repo.create(
            NewSetting(
                setting_name="boundary", description="d", source_quote="q",
                setting_key="boundary-key",
            ),
            "p-1", "ss-boundary",
        )
        await self._seed_setting_tracking("boundary-key", last_mentioned=15)

        # current=25, window=10, threshold=15 → 25-15=10，不大于 10
        archived = await repo.archive_stale("p-1", current_chapter=25, window=10)
        assert archived == 0

        # current=26, threshold=15 → 26-15=11 > 10
        archived = await repo.archive_stale("p-1", current_chapter=26, window=10)
        assert archived == 1
