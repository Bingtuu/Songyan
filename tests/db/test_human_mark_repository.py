"""Tests for HumanMarkRepository."""

from __future__ import annotations

from pathlib import Path

import pytest

from songyan.db import HumanMarkRepository, ProjectRepository, get_db
from songyan.db.migrations import init_schema
from songyan.models import HumanMark, ProjectSetting

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def mark_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point get_db() at a temporary initialized database."""
    import songyan.db.connection as conn_mod

    db_path = tmp_path / "mark.db"
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


class TestHumanMarkRepository:
    async def test_create_and_get_round_trip(self, mark_db: Path) -> None:
        await _seed_project("p1")
        repo = HumanMarkRepository()
        mark = HumanMark(
            mark_id="m1",
            project_id="p1",
            mark_type="setting",
            target_key="120Hz干扰器",
            note="核心道具，结局必须回收",
            priority=9,
            created_at_chapter=8,
        )

        await repo.create(mark)
        fetched = await repo.get("m1")

        assert fetched is not None
        assert fetched.target_key == "120Hz干扰器"
        assert fetched.priority == 9
        assert fetched.created_at_chapter == 8

    async def test_get_missing_returns_none(self, mark_db: Path) -> None:
        assert await HumanMarkRepository().get("missing") is None

    async def test_list_by_project_filters(self, mark_db: Path) -> None:
        await _seed_project("p1")
        repo = HumanMarkRepository()

        await repo.create(
            HumanMark(
                mark_id="m1",
                project_id="p1",
                mark_type="setting",
                target_key="认知补丁",
                priority=9,
            )
        )
        await repo.create(
            HumanMark(
                mark_id="m2",
                project_id="p1",
                mark_type="character",
                target_key="林渊",
                priority=5,
            )
        )
        await repo.create(
            HumanMark(
                mark_id="m3",
                project_id="p1",
                mark_type="setting",
                target_key="电磁干扰器",
                priority=7,
            )
        )

        all_marks = await repo.list_by_project("p1")
        assert len(all_marks) == 3
        # Ordered by priority DESC, created_at DESC
        assert [m.mark_id for m in all_marks] == ["m1", "m3", "m2"]

        high_priority = await repo.list_by_project("p1", min_priority=8)
        assert len(high_priority) == 1
        assert high_priority[0].mark_id == "m1"

        settings_only = await repo.list_by_project("p1", mark_type="setting")
        assert len(settings_only) == 2
        assert {m.mark_id for m in settings_only} == {"m1", "m3"}

    async def test_remove(self, mark_db: Path) -> None:
        await _seed_project("p1")
        repo = HumanMarkRepository()
        await repo.create(
            HumanMark(
                mark_id="m1",
                project_id="p1",
                mark_type="setting",
                target_key="x",
                priority=5,
            )
        )

        assert await repo.remove("m1") is True
        assert await repo.get("m1") is None
        assert await repo.remove("m1") is False

    async def test_update_priority(self, mark_db: Path) -> None:
        await _seed_project("p1")
        repo = HumanMarkRepository()
        await repo.create(
            HumanMark(
                mark_id="m1",
                project_id="p1",
                mark_type="setting",
                target_key="x",
                priority=5,
            )
        )

        assert await repo.update_priority("m1", 10) is True
        fetched = await repo.get("m1")
        assert fetched is not None
        assert fetched.priority == 10

        assert await repo.update_priority("missing", 10) is False

    async def test_resolve_excludes_from_default_list(self, mark_db: Path) -> None:
        await _seed_project("p1")
        repo = HumanMarkRepository()
        await repo.create(
            HumanMark(
                mark_id="m1",
                project_id="p1",
                mark_type="setting",
                target_key="x",
                priority=9,
            )
        )

        active = await repo.list_by_project("p1")
        assert len(active) == 1

        assert await repo.resolve("m1") is True
        resolved = await repo.get("m1")
        assert resolved is not None
        # resolved_at is not parsed back in _row_to_mark, so we verify via raw SQL
        async with get_db() as conn:
            cursor = await conn.execute(
                "SELECT resolved_at FROM human_marks WHERE mark_id = ?",
                ("m1",),
            )
            row = await cursor.fetchone()
        assert row[0] is not None

        # Default list excludes resolved
        active_after = await repo.list_by_project("p1")
        assert len(active_after) == 0

        # include_resolved brings it back
        with_resolved = await repo.list_by_project("p1", include_resolved=True)
        assert len(with_resolved) == 1

    async def test_foreign_key_violation(self, mark_db: Path) -> None:
        repo = HumanMarkRepository()
        with pytest.raises(Exception):
            await repo.create(
                HumanMark(
                    mark_id="m1",
                    project_id="missing_project",
                    mark_type="setting",
                    target_key="x",
                    priority=5,
                )
            )
