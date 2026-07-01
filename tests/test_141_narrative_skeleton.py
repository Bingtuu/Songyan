"""Tests for Task 141 — narrative skeleton (StoryOutline / ArcPlan / PlotThread).

Layer 1: Pydantic 模型；Layer 2: schema/迁移；Layer 3: NarrativeRepository。
"""

from __future__ import annotations

from pathlib import Path

import aiosqlite
import pytest
from pydantic import ValidationError

from songyan.db.migrations import (
    _EXPECTED_TABLES,
    get_schema_version,
    init_schema,
    run_migrations,
    verify_schema,
)
from songyan.db.narrative_repo import (
    InvalidThreadTransitionError,
    NarrativeError,
    NarrativeRepository,
)
from songyan.db.repository import ProjectRepository
from songyan.models import ArcPlan, PlotThread, ProjectSetting, StoryOutline

_NARRATIVE_TABLES = ("story_outlines", "arc_plans", "plot_threads")


async def _seed_project(project_id: str = "proj-141") -> str:
    await ProjectRepository().create(
        ProjectSetting(genre_id="xuanhuan", protagonist_name="Test"),
        project_id,
    )
    return project_id


# --------------------------------------------------------------------------- #
# Layer 1: models
# --------------------------------------------------------------------------- #
class TestModels:
    def test_minimal_instantiation(self) -> None:
        outline = StoryOutline(project_id="p1")
        arc = ArcPlan(arc_id="a0", project_id="p1", arc_index=0, start_chapter=1, end_chapter=20)
        thread = PlotThread(thread_id="t1", project_id="p1")
        assert outline.project_id == "p1"
        assert arc.arc_index == 0
        assert thread.status == "planned"

    def test_full_instantiation(self) -> None:
        arc = ArcPlan(
            arc_id="a0",
            project_id="p1",
            arc_index=1,
            start_chapter=21,
            end_chapter=40,
            arc_goal="收束第一主线",
            threads_to_open=["t2"],
            threads_to_resolve=["t1"],
            is_mainline=True,
        )
        assert arc.is_mainline is True
        assert arc.threads_to_resolve == ["t1"]

    def test_invalid_status_raises(self) -> None:
        with pytest.raises(ValidationError):
            PlotThread(thread_id="t1", project_id="p1", status="bogus")  # type: ignore[arg-type]

    def test_arc_index_and_chapter_bounds(self) -> None:
        with pytest.raises(ValidationError):
            ArcPlan(arc_id="a", project_id="p", arc_index=-1, start_chapter=1, end_chapter=2)
        with pytest.raises(ValidationError):
            ArcPlan(arc_id="a", project_id="p", arc_index=0, start_chapter=0, end_chapter=2)

    def test_reexport_from_models_package(self) -> None:
        import songyan.models as m

        assert m.ArcPlan and m.PlotThread and m.StoryOutline
        assert m.PlotThreadStatus is not None


# --------------------------------------------------------------------------- #
# Layer 2: schema / migration
# --------------------------------------------------------------------------- #
class TestMigration:
    async def test_init_schema_creates_tables(self, tmp_path: Path) -> None:
        db_path = tmp_path / "init.db"
        await init_schema(str(db_path))
        async with aiosqlite.connect(str(db_path)) as conn:
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            names = {row[0] for row in await cursor.fetchall()}
        for table in _NARRATIVE_TABLES:
            assert table in names

    async def test_run_migrations_backfills_old_db(self, tmp_path: Path) -> None:
        db_path = tmp_path / "old.db"
        await init_schema(str(db_path))
        async with aiosqlite.connect(str(db_path)) as conn:
            # 模拟旧库：删掉三张骨架表 + 插入 projects 数据
            for table in _NARRATIVE_TABLES:
                await conn.execute(f"DROP TABLE {table}")
            await conn.execute(
                "INSERT INTO projects (project_id, genre_id, protagonist_name) "
                "VALUES ('p1', 'xuanhuan', 'A')"
            )
            await conn.commit()
            await run_migrations(conn)
            await conn.commit()
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            names = {row[0] for row in await cursor.fetchall()}
            for table in _NARRATIVE_TABLES:
                assert table in names
            # 旧数据完好
            cursor = await conn.execute("SELECT COUNT(*) FROM projects")
            assert (await cursor.fetchone())[0] == 1

    async def test_verify_and_version_include_new_tables(self, tmp_path: Path) -> None:
        db_path = tmp_path / "verify.db"
        await init_schema(str(db_path))
        async with aiosqlite.connect(str(db_path)) as conn:
            assert await verify_schema(conn) == []
            assert await get_schema_version(conn) == len(_EXPECTED_TABLES)
            for table in _NARRATIVE_TABLES:
                assert table in _EXPECTED_TABLES

    async def test_on_delete_cascade(self, tmp_path: Path) -> None:
        db_path = tmp_path / "cascade.db"
        await init_schema(str(db_path))
        async with aiosqlite.connect(str(db_path)) as conn:
            await conn.execute("PRAGMA foreign_keys = ON")
            await conn.execute(
                "INSERT INTO projects (project_id, genre_id, protagonist_name) "
                "VALUES ('p1', 'xuanhuan', 'A')"
            )
            await conn.execute(
                "INSERT INTO story_outlines (project_id) VALUES ('p1')"
            )
            await conn.execute(
                "INSERT INTO arc_plans (arc_id, project_id, arc_index, start_chapter, end_chapter) "
                "VALUES ('a0', 'p1', 0, 1, 20)"
            )
            await conn.execute(
                "INSERT INTO plot_threads (thread_id, project_id) VALUES ('t1', 'p1')"
            )
            await conn.commit()
            await conn.execute("DELETE FROM projects WHERE project_id = 'p1'")
            await conn.commit()
            for table in _NARRATIVE_TABLES:
                cursor = await conn.execute(f"SELECT COUNT(*) FROM {table}")
                assert (await cursor.fetchone())[0] == 0


# --------------------------------------------------------------------------- #
# Layer 3: repository (真实临时 SQLite)
# --------------------------------------------------------------------------- #
class TestRepository:
    async def test_outline_upsert_and_get(self, test_db: Path) -> None:
        pid = await _seed_project()
        repo = NarrativeRepository()
        await repo.upsert_outline(
            StoryOutline(project_id=pid, core_conflict="A vs B", themes=["复仇"])
        )
        got = await repo.get_outline(pid)
        assert got is not None
        assert got.core_conflict == "A vs B"
        assert got.themes == ["复仇"]

        # upsert 覆盖
        await repo.upsert_outline(
            StoryOutline(project_id=pid, core_conflict="C vs D")
        )
        got2 = await repo.get_outline(pid)
        assert got2 is not None
        assert got2.core_conflict == "C vs D"

    async def test_get_outline_missing(self, test_db: Path) -> None:
        assert await NarrativeRepository().get_outline("nope") is None

    async def test_arc_plan_crud_and_lookup(self, test_db: Path) -> None:
        pid = await _seed_project()
        repo = NarrativeRepository()
        await repo.add_arc_plan(
            ArcPlan(arc_id="a0", project_id=pid, arc_index=0, start_chapter=1, end_chapter=20)
        )
        await repo.add_arc_plan(
            ArcPlan(
                arc_id="a1", project_id=pid, arc_index=1,
                start_chapter=21, end_chapter=40, is_mainline=True,
            )
        )
        arcs = await repo.list_arc_plans(pid)
        assert [a.arc_index for a in arcs] == [0, 1]

        arc = await repo.get_arc_for_chapter(pid, 5)
        assert arc is not None and arc.arc_index == 0
        arc2 = await repo.get_arc_for_chapter(pid, 25)
        assert arc2 is not None and arc2.arc_index == 1 and arc2.is_mainline is True
        assert await repo.get_arc_for_chapter(pid, 99) is None

    async def test_thread_lifecycle_legal_chain(self, test_db: Path) -> None:
        pid = await _seed_project()
        repo = NarrativeRepository()
        await repo.add_thread(
            PlotThread(thread_id="t1", project_id=pid, is_mainline=True)
        )
        await repo.advance_thread_status("t1", "opened", 3, "v-ch3")
        t = await repo.get_thread("t1")
        assert t is not None and t.status == "opened"
        assert t.opened_chapter == 3
        assert t.last_status_chapter == 3
        assert t.last_status_version_id == "v-ch3"

        await repo.advance_thread_status("t1", "advanced", 5, "v-ch5")
        await repo.advance_thread_status("t1", "advanced", 7, "v-ch7")
        await repo.advance_thread_status("t1", "resolved", 9, "v-ch9")
        t = await repo.get_thread("t1")
        assert t is not None and t.status == "resolved"
        assert t.last_status_version_id == "v-ch9"
        assert t.opened_chapter == 3  # 不被后续变更覆盖

    async def test_illegal_transition_raises(self, test_db: Path) -> None:
        pid = await _seed_project()
        repo = NarrativeRepository()
        await repo.add_thread(PlotThread(thread_id="t1", project_id=pid))
        await repo.advance_thread_status("t1", "opened", 1, "v1")
        await repo.advance_thread_status("t1", "resolved", 2, "v2")
        with pytest.raises(InvalidThreadTransitionError):
            await repo.advance_thread_status("t1", "opened", 3, "v3")

    async def test_abandon_from_any_state(self, test_db: Path) -> None:
        pid = await _seed_project()
        repo = NarrativeRepository()
        await repo.add_thread(PlotThread(thread_id="t1", project_id=pid))
        await repo.advance_thread_status("t1", "abandoned", 1, "v1")
        t = await repo.get_thread("t1")
        assert t is not None and t.status == "abandoned"

    async def test_advance_missing_thread_raises(self, test_db: Path) -> None:
        await _seed_project()
        with pytest.raises(NarrativeError):
            await NarrativeRepository().advance_thread_status("ghost", "opened", 1, "v1")

    async def test_list_threads_filter_and_count(self, test_db: Path) -> None:
        pid = await _seed_project()
        repo = NarrativeRepository()
        await repo.add_thread(PlotThread(thread_id="t1", project_id=pid))
        await repo.add_thread(PlotThread(thread_id="t2", project_id=pid))
        await repo.advance_thread_status("t2", "opened", 1, "v1")

        planned = await repo.list_threads(pid, status="planned")
        assert {t.thread_id for t in planned} == {"t1"}
        opened = await repo.list_threads(pid, status="opened")
        assert {t.thread_id for t in opened} == {"t2"}
        assert len(await repo.list_threads(pid)) == 2

        counts = await repo.count_threads_by_status(pid)
        assert counts == {"planned": 1, "opened": 1}
