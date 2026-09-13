"""Task 237-1: projects.lifecycle_status 迁移 + run 闸门单测."""

from __future__ import annotations

from pathlib import Path

import aiosqlite
import pytest

from songyan.db.migrations import (
    _migrate_projects_lifecycle_status,
    init_schema,
    run_migrations,
    verify_schema,
)
from songyan.db.repository import ProjectRepository
from songyan.models import ProjectSetting
from songyan.services.backup_service import _load_project
from songyan.services.doctor_service import (
    _REQUIRED_SCHEMA_COLUMNS,
    DoctorCheck,
    DoctorReport,
    run_run_preflight,
)

_PROJECT_ID = "proj-237"


def _new_project(**overrides: object) -> ProjectSetting:
    payload: dict[str, object] = {"genre_id": "scifi", "protagonist_name": "松烟"}
    payload.update(overrides)
    return ProjectSetting(**payload)  # type: ignore[arg-type]


async def _projects_columns(db_path: Path) -> set[str]:
    async with aiosqlite.connect(str(db_path)) as conn:
        cursor = await conn.execute("PRAGMA table_info(projects)")
        return {row[1] for row in await cursor.fetchall()}


class TestSchema:
    """新库路径：init_schema 后 projects 自带 lifecycle_status，默认 active."""

    pytestmark = pytest.mark.asyncio

    async def test_init_schema_projects_has_lifecycle_status(
        self, tmp_path: Path
    ) -> None:
        db_path = tmp_path / "init.db"
        await init_schema(str(db_path))

        columns = await _projects_columns(db_path)
        assert "lifecycle_status" in columns

        async with aiosqlite.connect(str(db_path)) as conn:
            assert await verify_schema(conn) == []

    async def test_new_project_defaults_to_active(self, test_db: Path) -> None:
        repo = ProjectRepository()
        await repo.create(_new_project(), _PROJECT_ID)

        loaded = await repo.get(_PROJECT_ID)
        assert loaded is not None
        assert loaded.lifecycle_status == "active"


class TestMigration:
    """迁移幂等：已有列再跑不报错；旧库（无列）迁移后补列且既有行 = 'active'."""

    pytestmark = pytest.mark.asyncio

    async def test_migration_idempotent_on_new_db(self, tmp_path: Path) -> None:
        db_path = tmp_path / "twice.db"
        await init_schema(str(db_path))
        await init_schema(str(db_path))

        async with aiosqlite.connect(str(db_path)) as conn:
            await run_migrations(conn)
            await conn.commit()
            assert await verify_schema(conn) == []
        assert "lifecycle_status" in await _projects_columns(db_path)

    async def test_migration_backfills_old_db(self, tmp_path: Path) -> None:
        """模拟旧库：最小 projects 表无 lifecycle_status 列 + 一行既有数据."""
        db_path = tmp_path / "old.db"
        async with aiosqlite.connect(str(db_path)) as conn:
            await conn.execute(
                "CREATE TABLE projects ("
                "project_id TEXT PRIMARY KEY, "
                "title TEXT, "
                "genre_id TEXT NOT NULL, "
                "protagonist_name TEXT NOT NULL"
                ")"
            )
            await conn.execute(
                "INSERT INTO projects (project_id, title, genre_id, protagonist_name) "
                "VALUES (?, ?, ?, ?)",
                (_PROJECT_ID, "旧项目", "scifi", "松烟"),
            )
            await conn.commit()
            assert "lifecycle_status" not in await _projects_columns(db_path)

            await _migrate_projects_lifecycle_status(conn)
            await conn.commit()

            assert "lifecycle_status" in await _projects_columns(db_path)
            cursor = await conn.execute(
                "SELECT lifecycle_status FROM projects WHERE project_id = ?",
                (_PROJECT_ID,),
            )
            row = await cursor.fetchone()
            assert row is not None
            assert row[0] == "active"

            # 幂等：已有列再跑迁移不报错
            await _migrate_projects_lifecycle_status(conn)
            await conn.commit()


class TestUpdateLifecycleStatus:
    """ProjectRepository.update_lifecycle_status 值域校验与往返语义."""

    pytestmark = pytest.mark.asyncio

    async def test_importing_active_roundtrip(self, test_db: Path) -> None:
        repo = ProjectRepository()
        await repo.create(_new_project(), _PROJECT_ID)

        await repo.update_lifecycle_status(_PROJECT_ID, "importing")
        loaded = await repo.get(_PROJECT_ID)
        assert loaded is not None
        assert loaded.lifecycle_status == "importing"

        await repo.update_lifecycle_status(_PROJECT_ID, "active")
        loaded = await repo.get(_PROJECT_ID)
        assert loaded is not None
        assert loaded.lifecycle_status == "active"

    async def test_out_of_domain_raises_value_error(self, test_db: Path) -> None:
        repo = ProjectRepository()
        await repo.create(_new_project(), _PROJECT_ID)

        with pytest.raises(ValueError, match="lifecycle_status"):
            await repo.update_lifecycle_status(_PROJECT_ID, "archived")  # type: ignore[arg-type]

        loaded = await repo.get(_PROJECT_ID)
        assert loaded is not None
        assert loaded.lifecycle_status == "active"

    async def test_missing_project_is_noop(self, test_db: Path) -> None:
        """沿用 update_seed_config 惯例：UPDATE 未命中行不报错."""
        repo = ProjectRepository()
        await repo.update_lifecycle_status("no-such-project", "importing")


class TestRunGate:
    """run_run_preflight 的 project.published 闸门."""

    pytestmark = pytest.mark.asyncio

    def _published_checks(self, report: DoctorReport) -> list[DoctorCheck]:
        return [check for check in report.checks if check.id == "project.published"]

    async def test_active_project_passes(self, test_db: Path) -> None:
        repo = ProjectRepository()
        await repo.create(_new_project(), _PROJECT_ID)

        report = await run_run_preflight(_PROJECT_ID)
        checks = self._published_checks(report)
        assert len(checks) == 1
        assert checks[0].status == "pass"

    async def test_importing_project_fails_with_hint(self, test_db: Path) -> None:
        repo = ProjectRepository()
        await repo.create(_new_project(lifecycle_status="importing"), _PROJECT_ID)

        report = await run_run_preflight(_PROJECT_ID)
        checks = self._published_checks(report)
        assert len(checks) == 1
        assert checks[0].status == "fail"
        assert "import publish" in checks[0].hint

        # publish 后闸门放开
        await repo.update_lifecycle_status(_PROJECT_ID, "active")
        report = await run_run_preflight(_PROJECT_ID)
        checks = self._published_checks(report)
        assert len(checks) == 1
        assert checks[0].status == "pass"

    async def test_missing_project_no_double_fail(self, test_db: Path) -> None:
        report = await run_run_preflight("no-such-project")
        project_checks = [
            check for check in report.checks if check.id.startswith("project.")
        ]
        failed = [check for check in project_checks if check.status == "fail"]
        assert len(failed) == 1
        assert failed[0].id == "project.exists"
        published = self._published_checks(report)
        assert len(published) == 1
        assert published[0].status == "pass"


class TestDoctorSchemaColumns:
    """doctor schema drift 可见性：projects 必含 lifecycle_status."""

    def test_required_schema_columns_includes_lifecycle_status(self) -> None:
        assert "lifecycle_status" in _REQUIRED_SCHEMA_COLUMNS["projects"]


class TestBackupMapping:
    """backup _load_project 不丢 lifecycle_status 列."""

    pytestmark = pytest.mark.asyncio

    async def test_load_project_carries_lifecycle_status(self, test_db: Path) -> None:
        repo = ProjectRepository()
        await repo.create(_new_project(lifecycle_status="importing"), _PROJECT_ID)

        loaded = _load_project(test_db, _PROJECT_ID)
        assert loaded["lifecycle_status"] == "importing"
