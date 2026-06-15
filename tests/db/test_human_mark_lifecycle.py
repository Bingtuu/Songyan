"""Tests for HumanMarkRepository lifecycle methods (Task 085)."""

from __future__ import annotations

from pathlib import Path

import pytest

from songyan.db import (
    HumanMarkRepository,
    ProjectRepository,
    get_db,
)
from songyan.db.migrations import init_schema
from songyan.models import HumanMark, ProjectSetting

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def mark_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point get_db() at a temporary initialized database."""
    import songyan.db.connection as conn_mod

    db_path = tmp_path / "mark_lifecycle.db"
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


class TestHumanMarkLifecycle:
    async def _create_mark(
        self,
        mark_id: str,
        project_id: str = "p1",
        priority: int = 5,
        created_at_chapter: int = 1,
        resolved_at: str | None = None,
        lifecycle_status: str = "active",
    ) -> None:
        """Helper to insert a mark directly via SQL for full control."""
        repo = HumanMarkRepository()
        mark = HumanMark(
            mark_id=mark_id,
            project_id=project_id,
            mark_type="setting",
            target_key=f"target_{mark_id}",
            priority=priority,
            created_at_chapter=created_at_chapter,
        )
        await repo.create(mark)
        if resolved_at is not None or lifecycle_status != "active":
            async with get_db() as conn:
                if resolved_at is not None:
                    await conn.execute(
                        "UPDATE human_marks SET resolved_at = ? WHERE mark_id = ?",
                        (resolved_at, mark_id),
                    )
                if lifecycle_status != "active":
                    await conn.execute(
                        "UPDATE human_marks SET lifecycle_status = ? WHERE mark_id = ?",
                        (lifecycle_status, mark_id),
                    )
                await conn.commit()

    async def test_archive_stale_unresolved_older_than_window(self, mark_db: Path) -> None:
        await _seed_project("p1")
        await self._create_mark("m1", created_at_chapter=1, priority=5)
        await self._create_mark("m2", created_at_chapter=5, priority=5)

        repo = HumanMarkRepository()
        archived = await repo.archive_stale("p1", current_chapter=15, window=10)

        # m1: created_at_chapter=1 < 15-10=5 -> archived
        # m2: created_at_chapter=5 is NOT < 5 -> stays active
        assert archived == 1

        async with get_db() as conn:
            cursor = await conn.execute(
                "SELECT lifecycle_status FROM human_marks WHERE mark_id = ?", ("m1",)
            )
            row = await cursor.fetchone()
        assert row[0] == "dormant"

        # m2 still active
        m2 = await repo.get("m2")
        assert m2 is not None
        assert m2.lifecycle_status == "active"

    async def test_archive_stale_skips_high_priority(self, mark_db: Path) -> None:
        await _seed_project("p1")
        await self._create_mark("m1", created_at_chapter=1, priority=9)

        repo = HumanMarkRepository()
        archived = await repo.archive_stale("p1", current_chapter=15, window=10)

        assert archived == 0
        m1 = await repo.get("m1")
        assert m1 is not None
        assert m1.lifecycle_status == "active"

    async def test_archive_stale_skips_resolved(self, mark_db: Path) -> None:
        await _seed_project("p1")
        await self._create_mark(
            "m1", created_at_chapter=1, priority=5, resolved_at="2024-01-01"
        )

        repo = HumanMarkRepository()
        archived = await repo.archive_stale("p1", current_chapter=15, window=10)

        assert archived == 0

    async def test_archive_very_stale_resolved(self, mark_db: Path) -> None:
        await _seed_project("p1")
        await self._create_mark(
            "m1", created_at_chapter=1, priority=5, resolved_at="2024-01-01"
        )

        repo = HumanMarkRepository()
        archived = await repo.archive_very_stale("p1", current_chapter=25, window=20)

        assert archived == 1
        async with get_db() as conn:
            cursor = await conn.execute(
                "SELECT lifecycle_status FROM human_marks WHERE mark_id = ?", ("m1",)
            )
            row = await cursor.fetchone()
        assert row[0] == "archived"

    async def test_archive_very_stale_by_age(self, mark_db: Path) -> None:
        await _seed_project("p1")
        await self._create_mark("m1", created_at_chapter=1, priority=5)

        repo = HumanMarkRepository()
        archived = await repo.archive_very_stale("p1", current_chapter=25, window=20)

        assert archived == 1
        async with get_db() as conn:
            cursor = await conn.execute(
                "SELECT lifecycle_status FROM human_marks WHERE mark_id = ?", ("m1",)
            )
            row = await cursor.fetchone()
        assert row[0] == "archived"

    async def test_archive_very_stale_skips_high_priority(self, mark_db: Path) -> None:
        await _seed_project("p1")
        await self._create_mark("m1", created_at_chapter=1, priority=9)

        repo = HumanMarkRepository()
        archived = await repo.archive_very_stale("p1", current_chapter=25, window=20)

        assert archived == 0

    async def test_list_by_project_excludes_dormant(self, mark_db: Path) -> None:
        await _seed_project("p1")
        await self._create_mark("m1", created_at_chapter=1, priority=5)
        await self._create_mark(
            "m2", created_at_chapter=1, priority=5, lifecycle_status="dormant"
        )

        repo = HumanMarkRepository()
        marks = await repo.list_by_project("p1")

        # m2 is dormant (priority<8) → excluded
        assert len(marks) == 1
        assert marks[0].mark_id == "m1"

    async def test_list_by_project_includes_dormant_high_priority(self, mark_db: Path) -> None:
        await _seed_project("p1")
        await self._create_mark(
            "m1", created_at_chapter=1, priority=9, lifecycle_status="dormant"
        )

        repo = HumanMarkRepository()
        marks = await repo.list_by_project("p1")

        # priority>=8 overrides dormancy
        assert len(marks) == 1
        assert marks[0].mark_id == "m1"

    async def test_archive_stale_ignores_archived(self, mark_db: Path) -> None:
        await _seed_project("p1")
        await self._create_mark(
            "m1", created_at_chapter=1, priority=5, lifecycle_status="archived"
        )

        repo = HumanMarkRepository()
        archived = await repo.archive_stale("p1", current_chapter=15, window=10)
        assert archived == 0
