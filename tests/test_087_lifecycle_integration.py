"""Tests for Task 087: LifecycleScheduler integration + evals lifecycle stats."""

from __future__ import annotations

from pathlib import Path

import pytest

from songyan.db import (
    ChapterVersionRepository,
    CharacterRepository,
    HumanMarkRepository,
    ProjectRepository,
    get_db,
)
from songyan.db.lifecycle_cleaners import (
    CharacterStateCleaner,
    ForeshadowingCleaner,
    HumanMarkCleaner,
    SettingSnapshotCleaner,
    get_default_scheduler,
)
from songyan.db.migrations import init_schema
from songyan.db.settlement_repo import (
    ForeshadowingRepository,
    SettingSnapshotRepository,
)
from songyan.models import (
    ChapterVersion,
    Character,
    CharacterState,
    ForeshadowingItem,
    HumanMark,
    NewSetting,
    ProjectSetting,
)

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def lifecycle_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point get_db() at a temporary initialized database."""
    import songyan.db.connection as conn_mod

    db_path = tmp_path / "lifecycle.db"
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


async def _seed_version(
    version_id: str, chapter_number: int = 1, project_id: str = "p1"
) -> None:
    await ChapterVersionRepository().create(
        ChapterVersion(
            version_id=version_id,
            project_id=project_id,
            chapter_number=chapter_number,
            version_number=1,
            content="test",
            word_count=100,
            scenes=[],
            generation_metadata={"source": "test"},
        )
    )


async def _seed_setting_tracking(
    project_id: str, setting_key: str, last_mentioned: int
) -> None:
    """Insert a setting_tracking record for testing archive logic."""
    async with get_db() as conn:
        await conn.execute(
            """INSERT INTO setting_tracking (
                tracking_id, project_id, setting_key, setting_name,
                last_mentioned_chapter, status
            ) VALUES (?, ?, ?, ?, ?, ?)""",
            (f"trk_{setting_key}", project_id, setting_key, setting_key, last_mentioned, "active"),
        )
        await conn.commit()


class TestLifecycleCleaners:
    async def test_setting_snapshot_cleaner(self, lifecycle_db: Path) -> None:
        await _seed_project("p1")
        repo = SettingSnapshotRepository()
        await repo.create(
            NewSetting(
                setting_name="name1",
                description="desc",
                source_quote="quote1",
                setting_key="key1",
            ),
            project_id="p1",
            setting_id="s1",
        )
        await repo.create(
            NewSetting(
                setting_name="name2",
                description="desc",
                source_quote="quote2",
                setting_key="key2",
            ),
            project_id="p1",
            setting_id="s2",
        )
        # setting_tracking provides last_mentioned_chapter for archive logic
        await _seed_setting_tracking("p1", "key1", last_mentioned=1)
        await _seed_setting_tracking("p1", "key2", last_mentioned=20)

        cleaner = SettingSnapshotCleaner()
        async with get_db() as conn:
            logs = await cleaner.cleanup(conn, "p1", current_chapter=15)
            await conn.commit()

        # s1: last_mentioned=1 < 15-10=5 -> dormant
        # s2: last_mentioned=20 >= 5 -> stays active
        assert len(logs) == 1
        assert logs[0].entity_id == "s1"
        assert logs[0].from_status == "active"
        assert logs[0].to_status == "dormant"

    async def test_foreshadowing_cleaner(self, lifecycle_db: Path) -> None:
        await _seed_project("p1")
        repo = ForeshadowingRepository()
        await repo.create(
            ForeshadowingItem(
                foreshadowing_id="f1",
                description="old",
                planted_in_chapter=1,
                expected_resolve_chapter=3,
                status="planted",
            ),
            project_id="p1",
        )
        await repo.create(
            ForeshadowingItem(
                foreshadowing_id="f2",
                description="resolved",
                planted_in_chapter=1,
                expected_resolve_chapter=3,
                status="resolved",
            ),
            project_id="p1",
        )

        cleaner = ForeshadowingCleaner()
        async with get_db() as conn:
            logs = await cleaner.cleanup(conn, "p1", current_chapter=10)
            await conn.commit()

        # f1: active, 10 - 3 = 7 > 5 -> dormant
        # f2: resolved -> archived
        assert len(logs) == 2
        statuses = {(log.entity_id, log.to_status) for log in logs}
        assert ("f1", "dormant") in statuses
        assert ("f2", "archived") in statuses

    async def test_human_mark_cleaner(self, lifecycle_db: Path) -> None:
        await _seed_project("p1")
        repo = HumanMarkRepository()
        await repo.create(
            HumanMark(
                mark_id="m1",
                project_id="p1",
                mark_type="setting",
                target_key="x",
                priority=5,
                created_at_chapter=1,
            )
        )

        cleaner = HumanMarkCleaner()
        async with get_db() as conn:
            logs = await cleaner.cleanup(conn, "p1", current_chapter=15)
            await conn.commit()

        # m1: created_at_chapter=1 < 15-6=9 -> dormant
        assert len(logs) == 1
        assert logs[0].entity_id == "m1"
        assert logs[0].to_status == "dormant"

    async def test_character_state_cleaner(self, lifecycle_db: Path) -> None:
        await _seed_project("p1")
        await CharacterRepository().create(
            Character(
                character_id="c1",
                project_id="p1",
                name="support",
                role_type="supporting",
                personality_traits=[],
                goals=[],
                relationships={},
            )
        )
        await _seed_version("v1", chapter_number=1)
        await CharacterRepository().add_state_snapshot(
            CharacterState(
                character_id="c1",
                field="mood",
                value="happy",
                source_version_id="v1",
            )
        )

        cleaner = CharacterStateCleaner()
        async with get_db() as conn:
            logs = await cleaner.cleanup(conn, "p1", current_chapter=50)
            await conn.commit()

        # c1 is supporting, source_version chapter=1 < 50-30=20 -> dormant
        assert len(logs) == 1
        assert logs[0].to_status == "dormant"

    async def test_scheduler_runs_all_cleaners(self, lifecycle_db: Path) -> None:
        await _seed_project("p1")
        await _seed_version("v1", chapter_number=1)

        # Seed data for all tables
        await SettingSnapshotRepository().create(
            NewSetting(
                setting_name="n1", description="d", source_quote="q", setting_key="k1",
            ),
            project_id="p1",
            setting_id="s1",
        )
        await _seed_setting_tracking("p1", "k1", last_mentioned=1)
        await ForeshadowingRepository().create(
            ForeshadowingItem(
                foreshadowing_id="f1", description="d",
                planted_in_chapter=1, expected_resolve_chapter=3, status="planted",
            ),
            project_id="p1",
        )
        await HumanMarkRepository().create(
            HumanMark(
                mark_id="m1", project_id="p1", mark_type="setting",
                target_key="x", priority=5, created_at_chapter=1,
            )
        )
        # character_states data
        await CharacterRepository().create(
            Character(
                character_id="c1", project_id="p1", name="support",
                role_type="supporting", personality_traits=[], goals=[], relationships={},
            )
        )
        await CharacterRepository().add_state_snapshot(
            CharacterState(
                character_id="c1", field="mood", value="happy", source_version_id="v1",
            )
        )

        scheduler = get_default_scheduler()
        result = await scheduler.run_cleanup("p1", current_chapter=15)

        # All cleaners should produce at least one transition each
        assert len(result.transitions) >= 3
        assert result.project_id == "p1"
        assert result.current_chapter == 15


class TestLifecycleStats:
    async def test_collect_lifecycle_stats(self, lifecycle_db: Path) -> None:
        await _seed_project("p1")

        from evals.runner import _collect_lifecycle_stats

        # Initially all counts should be 0
        stats = await _collect_lifecycle_stats("p1")
        assert stats["settings_active"] == 0
        assert stats["settings_dormant"] == 0
        assert stats["settings_archived"] == 0

        # Create some data
        await SettingSnapshotRepository().create(
            NewSetting(
                setting_name="n1", description="d", source_quote="q", setting_key="k1",
            ),
            project_id="p1",
            setting_id="s1",
        )
        await HumanMarkRepository().create(
            HumanMark(
                mark_id="m1", project_id="p1", mark_type="setting",
                target_key="x", priority=5, created_at_chapter=1,
            )
        )

        # Archive some
        async with get_db() as conn:
            await conn.execute(
                "UPDATE setting_snapshots SET lifecycle_status = 'dormant' WHERE setting_id = ?",
                ("s1",),
            )
            await conn.commit()

        stats = await _collect_lifecycle_stats("p1")
        assert stats["settings_active"] == 0
        assert stats["settings_dormant"] == 1
        assert stats["settings_archived"] == 0
        assert stats["marks_active"] == 1
