"""Tests for SettingDeduplicationService — Task 110."""

from __future__ import annotations

from pathlib import Path

import pytest

from songyan.db.connection import get_db
from songyan.db.migrations import init_schema
from songyan.db.repository import ProjectRepository
from songyan.db.settlement_repo import (
    SettingDeduplicationService,
    SettingSnapshotRepository,
)
from songyan.models import NewSetting, ProjectSetting


@pytest.fixture
async def dedup_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point get_db() at a temporary initialized database."""
    import songyan.db.connection as conn_mod

    db_path = tmp_path / "dedup.db"
    monkeypatch.setattr(
        conn_mod,
        "settings",
        type("S", (), {"database_url": f"sqlite:///{db_path}"})(),
    )
    await init_schema(db_path)
    return db_path


async def _seed_project(project_id: str = "p1") -> None:
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="scifi",
            mode_id="webnovel",
            protagonist_name="Lin Yuan",
        ),
        project_id,
    )


async def _insert_tracking(
    tracking_id: str,
    setting_key: str,
    setting_name: str,
    description: str,
    introduced: int,
    last_mentioned: int,
    project_id: str = "p1",
) -> None:
    async with get_db() as conn:
        await conn.execute(
            """INSERT INTO setting_tracking (
                tracking_id, project_id, setting_key, setting_name,
                description, introduced_in_chapter, last_mentioned_chapter, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'active')""",
            (
                tracking_id,
                project_id,
                setting_key,
                setting_name,
                description,
                introduced,
                last_mentioned,
            ),
        )
        await conn.commit()


async def _insert_snapshot(
    setting_id: str,
    setting_key: str,
    setting_name: str,
    description: str,
    project_id: str = "p1",
    lifecycle_status: str = "active",
) -> None:
    async with get_db() as conn:
        await conn.execute(
            """INSERT INTO setting_snapshots (
                setting_id, project_id, setting_key, setting_name,
                description, lifecycle_status
            ) VALUES (?, ?, ?, ?, ?, ?)""",
            (
                setting_id,
                project_id,
                setting_key,
                setting_name,
                description,
                lifecycle_status,
            ),
        )
        await conn.commit()


class TestSettingSnapshotRepository:
    async def test_archive_by_key_archives_active(self, dedup_db: Path) -> None:
        await _seed_project("p1")
        await _insert_snapshot("s1", "key-a", "灵石矿脉", "矿", lifecycle_status="active")
        await _insert_snapshot("s2", "key-a", "灵石矿脉", "矿 v2", lifecycle_status="active")

        repo = SettingSnapshotRepository()
        archived = await repo.archive_by_key("p1", "key-a")
        assert archived == 2

        async with get_db() as conn:
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM setting_snapshots WHERE project_id = ? AND setting_key = ? AND lifecycle_status = 'active'",
                ("p1", "key-a"),
            )
            row = await cursor.fetchone()
        assert row[0] == 0

    async def test_archive_by_key_ignores_other_keys(self, dedup_db: Path) -> None:
        await _seed_project("p1")
        await _insert_snapshot("s1", "key-a", "灵石矿脉", "矿", lifecycle_status="active")
        await _insert_snapshot("s2", "key-b", "灵石来源", "矿", lifecycle_status="active")

        repo = SettingSnapshotRepository()
        archived = await repo.archive_by_key("p1", "key-a")
        assert archived == 1

        async with get_db() as conn:
            cursor = await conn.execute(
                "SELECT lifecycle_status FROM setting_snapshots WHERE setting_id = ?",
                ("s2",),
            )
            row = await cursor.fetchone()
        assert row[0] == "active"

    async def test_create_and_list_active(self, dedup_db: Path) -> None:
        await _seed_project("p1")
        repo = SettingSnapshotRepository()
        setting = NewSetting(
            setting_name="测试设定",
            description="测试描述",
            source_quote="quote",
            setting_key="test.category.name",
        )
        await repo.create(setting, "p1", "s-new")

        active = await repo.list_by_project("p1")
        assert len(active) == 1
        assert active[0].setting_key == "test.category.name"


class TestSimilarity:
    def test_identical_strings(self) -> None:
        assert SettingDeduplicationService._similarity("abc", "abc") == 1.0

    def test_completely_different(self) -> None:
        assert SettingDeduplicationService._similarity("abc", "xyz") < 0.3

    def test_similar_names(self) -> None:
        a = "灵石矿脉"
        b = "灵石来源"
        sim = SettingDeduplicationService._similarity(a, b)
        assert 0.3 < sim < 0.8


class TestDeduplicate:
    async def test_detects_and_archives_duplicates(
        self, dedup_db: Path
    ) -> None:
        await _seed_project("p1")
        await _insert_tracking(
            "t1", "key-a", "灵石矿脉", "矿", 10, 15
        )
        await _insert_tracking(
            "t2", "key-b", "灵石来源", "矿", 20, 25
        )
        await _insert_snapshot("s1", "key-a", "灵石矿脉", "矿", lifecycle_status="active")
        await _insert_snapshot("s2", "key-b", "灵石来源", "矿", lifecycle_status="active")

        service = SettingDeduplicationService()
        archived = await service.deduplicate("p1", threshold=0.5)

        # Should archive t2 (similar to t1)
        assert archived == 1

        async with get_db() as conn:
            cursor = await conn.execute(
                "SELECT status FROM setting_tracking WHERE tracking_id = ?",
                ("t2",),
            )
            row = await cursor.fetchone()
        assert row[0] == "archived"

    async def test_preserves_oldest_master(self, dedup_db: Path) -> None:
        await _seed_project("p1")
        await _insert_tracking(
            "t1", "key-a", "灵石矿脉", "青云宗后山的矿", 10, 15
        )
        await _insert_tracking(
            "t2", "key-b", "灵石来源", "后山有一座灵石矿", 20, 25
        )
        await _insert_snapshot("s1", "key-a", "灵石矿脉", "矿")
        await _insert_snapshot("s2", "key-b", "灵石来源", "矿")

        service = SettingDeduplicationService()
        await service.deduplicate("p1", threshold=0.5)

        async with get_db() as conn:
            cursor = await conn.execute(
                "SELECT status FROM setting_tracking WHERE tracking_id = ?",
                ("t1",),
            )
            row = await cursor.fetchone()
        assert row[0] == "active"

    async def test_updates_master_last_mentioned(self, dedup_db: Path) -> None:
        await _seed_project("p1")
        await _insert_tracking(
            "t1", "key-a", "灵石矿脉", "矿", 10, 15
        )
        await _insert_tracking(
            "t2", "key-b", "灵石来源", "矿", 20, 25
        )
        await _insert_snapshot("s1", "key-a", "灵石矿脉", "矿")
        await _insert_snapshot("s2", "key-b", "灵石来源", "矿")

        service = SettingDeduplicationService()
        await service.deduplicate("p1", threshold=0.5)

        async with get_db() as conn:
            cursor = await conn.execute(
                "SELECT last_mentioned_chapter FROM setting_tracking WHERE tracking_id = ?",
                ("t1",),
            )
            row = await cursor.fetchone()
        assert row[0] == 25

    async def test_archives_snapshot_too(self, dedup_db: Path) -> None:
        await _seed_project("p1")
        await _insert_tracking(
            "t1", "key-a", "灵石矿脉", "矿", 10, 15
        )
        await _insert_tracking(
            "t2", "key-b", "灵石来源", "矿", 20, 25
        )
        await _insert_snapshot("s1", "key-a", "灵石矿脉", "矿")
        await _insert_snapshot("s2", "key-b", "灵石来源", "矿")

        service = SettingDeduplicationService()
        await service.deduplicate("p1", threshold=0.5)

        async with get_db() as conn:
            cursor = await conn.execute(
                "SELECT lifecycle_status FROM setting_snapshots WHERE setting_id = ?",
                ("s2",),
            )
            row = await cursor.fetchone()
        assert row[0] == "archived"

    async def test_no_false_positives(self, dedup_db: Path) -> None:
        await _seed_project("p1")
        await _insert_tracking(
            "t1", "key-a", "灵石矿脉", "矿", 10, 15
        )
        await _insert_tracking(
            "t2", "key-b", "飞船引擎", "曲率驱动核心", 20, 25
        )
        await _insert_snapshot("s1", "key-a", "灵石矿脉", "矿")
        await _insert_snapshot("s2", "key-b", "飞船引擎", "核心")

        service = SettingDeduplicationService()
        archived = await service.deduplicate("p1", threshold=0.5)

        assert archived == 0

    async def test_skips_already_archived(self, dedup_db: Path) -> None:
        await _seed_project("p1")
        await _insert_tracking(
            "t1", "key-a", "灵石矿脉", "矿", 10, 15
        )
        await _insert_tracking(
            "t2", "key-b", "灵石来源", "矿", 20, 25
        )
        await _insert_snapshot("s1", "key-a", "灵石矿脉", "矿")
        await _insert_snapshot("s2", "key-b", "灵石来源", "矿")

        service = SettingDeduplicationService()
        archived1 = await service.deduplicate("p1", threshold=0.5)
        assert archived1 == 1

        # Second run should not find anything new
        archived2 = await service.deduplicate("p1", threshold=0.5)
        assert archived2 == 0


async def _insert_foreshadowing(
    foreshadowing_id: str,
    description: str,
    planted_in_chapter: int,
    expected_resolve_chapter: int | None,
    status: str,
    project_id: str = "p1",
) -> None:
    async with get_db() as conn:
        await conn.execute(
            """INSERT INTO foreshadowings (
                foreshadowing_id, project_id, description,
                planted_in_chapter, expected_resolve_chapter, status
            ) VALUES (?, ?, ?, ?, ?, ?)""",
            (
                foreshadowing_id,
                project_id,
                description,
                planted_in_chapter,
                expected_resolve_chapter,
                status,
            ),
        )
        await conn.commit()


class TestForeshadowingPressure:
    async def test_mark_overdue(self, dedup_db: Path) -> None:
        await _seed_project("p1")
        await _insert_foreshadowing(
            "fs1", "伏笔1", 10, 30, "planted"
        )
        await _insert_foreshadowing(
            "fs2", "伏笔2", 20, 40, "due"
        )

        from songyan.db.settlement_repo import ForeshadowingRepository

        repo = ForeshadowingRepository()
        updated = await repo.mark_overdue("p1", current_chapter=35)
        assert updated == 1  # fs1 overdue

        async with get_db() as conn:
            cursor = await conn.execute(
                "SELECT status FROM foreshadowings WHERE foreshadowing_id = ?",
                ("fs1",),
            )
            row = await cursor.fetchone()
        assert row[0] == "overdue"

        async with get_db() as conn:
            cursor = await conn.execute(
                "SELECT status FROM foreshadowings WHERE foreshadowing_id = ?",
                ("fs2",),
            )
            row = await cursor.fetchone()
        assert row[0] == "due"

    async def test_get_unresolved_ratio(self, dedup_db: Path) -> None:
        await _seed_project("p1")
        await _insert_foreshadowing("fs1", "伏笔1", 10, 30, "planted")
        await _insert_foreshadowing("fs2", "伏笔2", 20, 40, "due")
        await _insert_foreshadowing("fs3", "伏笔3", 30, 50, "resolved")

        from songyan.db.settlement_repo import ForeshadowingRepository

        repo = ForeshadowingRepository()
        ratio = await repo.get_unresolved_ratio("p1", current_chapter=50)
        assert ratio == 2 / 50  # planted + due = 2
