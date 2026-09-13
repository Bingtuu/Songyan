"""Task 236: V15 导入回放幂等标记表 — schema / 迁移 / repo / 模型单测."""

from __future__ import annotations

from pathlib import Path

import aiosqlite
import pytest
from pydantic import ValidationError

from songyan.db.import_replay_repo import ImportReplayRepository
from songyan.db.migrations import init_schema, run_migrations, verify_schema
from songyan.exceptions import ImportReplayError
from songyan.models.import_replay import (
    ChapterReplayOutcome,
    ReplayMark,
    ReplayReport,
)

_FP_A = "a" * 64
_FP_B = "b" * 64


def _mark(**overrides: object) -> ReplayMark:
    payload: dict[str, object] = {
        "project_id": "proj-1",
        "run_id": "run-1",
        "chapter_number": 1,
        "draft_version_id": "draft-v1",
        "accepted_version_id": "acc-v1",
        "summary_id": "sum-1",
        "source_fingerprint": _FP_A,
    }
    payload.update(overrides)
    return ReplayMark(**payload)  # type: ignore[arg-type]


async def _insert_project(conn: aiosqlite.Connection, project_id: str = "proj-1") -> None:
    await conn.execute(
        "INSERT INTO projects (project_id, title, genre_id, protagonist_name) "
        "VALUES (?, ?, ?, ?)",
        (project_id, "测试项目", "scifi", "松烟"),
    )
    await conn.commit()


async def _mark_count(db_path: Path) -> int:
    async with aiosqlite.connect(str(db_path)) as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM import_replay_marks")
        row = await cursor.fetchone()
        assert row is not None
        return int(row[0])


class TestSchema:
    """新库路径：init_schema 直接建表，列与 UNIQUE 约束齐全."""

    pytestmark = pytest.mark.asyncio

    async def test_init_schema_creates_table_with_columns_and_unique(
        self, tmp_path: Path
    ) -> None:
        db_path = tmp_path / "init.db"
        await init_schema(str(db_path))

        async with aiosqlite.connect(str(db_path)) as conn:
            cursor = await conn.execute(
                "SELECT sql FROM sqlite_master "
                "WHERE type = 'table' AND name = 'import_replay_marks'"
            )
            row = await cursor.fetchone()
            assert row is not None, "import_replay_marks 表应存在"
            table_sql = row[0]
            assert "UNIQUE(project_id, chapter_number)" in table_sql

            cursor = await conn.execute("PRAGMA table_info(import_replay_marks)")
            columns = {r[1] for r in await cursor.fetchall()}
            assert {
                "id",
                "project_id",
                "run_id",
                "chapter_number",
                "draft_version_id",
                "accepted_version_id",
                "summary_id",
                "source_fingerprint",
                "created_at",
            } <= columns

            assert await verify_schema(conn) == []

    async def test_unique_constraint_enforced(self, tmp_path: Path) -> None:
        """同一 (project_id, chapter_number) 裸插入第二行应触发 IntegrityError."""
        import sqlite3

        db_path = tmp_path / "unique.db"
        await init_schema(str(db_path))

        async with aiosqlite.connect(str(db_path)) as conn:
            await conn.execute(
                "INSERT INTO import_replay_marks ("
                "project_id, run_id, chapter_number, draft_version_id,"
                " accepted_version_id, source_fingerprint"
                ") VALUES (?, ?, ?, ?, ?, ?)",
                ("proj-1", "run-1", 1, "d1", "a1", _FP_A),
            )
            await conn.commit()
            with pytest.raises(sqlite3.IntegrityError):
                await conn.execute(
                    "INSERT INTO import_replay_marks ("
                    "project_id, run_id, chapter_number, draft_version_id,"
                    " accepted_version_id, source_fingerprint"
                    ") VALUES (?, ?, ?, ?, ?, ?)",
                    ("proj-1", "run-2", 1, "d2", "a2", _FP_B),
                )


class TestMigration:
    """迁移幂等：重复 init_schema 不报错；旧库（缺表）能被 run_migrations 补上."""

    pytestmark = pytest.mark.asyncio

    async def test_init_schema_idempotent(self, tmp_path: Path) -> None:
        db_path = tmp_path / "twice.db"
        await init_schema(str(db_path))
        await init_schema(str(db_path))

        async with aiosqlite.connect(str(db_path)) as conn:
            assert await verify_schema(conn) == []

    async def test_run_migrations_backfills_old_db(self, tmp_path: Path) -> None:
        """模拟旧库：删掉该表后 run_migrations 能补回来."""
        db_path = tmp_path / "old.db"
        await init_schema(str(db_path))

        async with aiosqlite.connect(str(db_path)) as conn:
            await conn.execute("DROP TABLE import_replay_marks")
            await conn.commit()
            assert "import_replay_marks" in await verify_schema(conn)

            await run_migrations(conn)
            await conn.commit()

            cursor = await conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name = 'import_replay_marks'"
            )
            assert await cursor.fetchone() is not None
            assert await verify_schema(conn) == []


class TestRepository:
    """ImportReplayRepository roundtrip 与幂等插入语义."""

    pytestmark = pytest.mark.asyncio

    async def test_insert_then_get_roundtrip(self, test_db: Path) -> None:
        async with aiosqlite.connect(str(test_db)) as conn:
            await _insert_project(conn)

        repo = ImportReplayRepository()
        mark = _mark()
        await repo.insert_mark(mark)

        loaded = await repo.get_mark("proj-1", 1)
        assert loaded is not None
        assert loaded == mark

    async def test_insert_roundtrip_with_null_summary(self, test_db: Path) -> None:
        async with aiosqlite.connect(str(test_db)) as conn:
            await _insert_project(conn)

        repo = ImportReplayRepository()
        mark = _mark(summary_id=None)
        await repo.insert_mark(mark)

        loaded = await repo.get_mark("proj-1", 1)
        assert loaded is not None
        assert loaded.summary_id is None
        assert loaded == mark

    async def test_get_missing_returns_none(self, test_db: Path) -> None:
        repo = ImportReplayRepository()
        assert await repo.get_mark("proj-1", 99) is None

    async def test_insert_same_fingerprint_is_noop(self, test_db: Path) -> None:
        async with aiosqlite.connect(str(test_db)) as conn:
            await _insert_project(conn)

        repo = ImportReplayRepository()
        await repo.insert_mark(_mark())
        await repo.insert_mark(_mark(run_id="run-2", draft_version_id="draft-v2"))

        assert await _mark_count(test_db) == 1
        loaded = await repo.get_mark("proj-1", 1)
        assert loaded is not None
        # 重复插入被整体忽略，保留首行内容
        assert loaded.run_id == "run-1"
        assert loaded.draft_version_id == "draft-v1"

    async def test_insert_different_fingerprint_raises(self, test_db: Path) -> None:
        async with aiosqlite.connect(str(test_db)) as conn:
            await _insert_project(conn)

        repo = ImportReplayRepository()
        await repo.insert_mark(_mark())

        with pytest.raises(ImportReplayError, match="fingerprint"):
            await repo.insert_mark(_mark(source_fingerprint=_FP_B))

        assert await _mark_count(test_db) == 1

    async def test_insert_with_external_conn_uses_caller_transaction(
        self, test_db: Path
    ) -> None:
        """传入 conn 时 repo 不自行 commit；调用方 commit 后其他连接可见."""
        repo = ImportReplayRepository()
        async with aiosqlite.connect(str(test_db)) as conn:
            await _insert_project(conn)
            await repo.insert_mark(_mark(), conn=conn)
            # 未 commit：同一连接内可见，其他连接不可见
            assert await repo.get_mark("proj-1", 1, conn=conn) is not None
            assert await _mark_count(test_db) == 0
            await conn.commit()

        assert await _mark_count(test_db) == 1


class TestModels:
    """ReplayReport.by_status 过滤与模型约束."""

    def test_by_status_filters(self) -> None:
        report = ReplayReport(
            run_id="run-1",
            project_id="proj-1",
            outcomes=[
                ChapterReplayOutcome(
                    chapter_number=1, title="第一章", status="applied",
                    accepted_version_id="acc-v1",
                ),
                ChapterReplayOutcome(
                    chapter_number=2, title="第二章", status="skipped",
                ),
                ChapterReplayOutcome(
                    chapter_number=3, title="第三章", status="failed",
                    error="boom",
                ),
                ChapterReplayOutcome(
                    chapter_number=4, title="第四章", status="applied",
                    accepted_version_id="acc-v4", summary_missing_facts=2,
                    over_token_budget=True,
                ),
            ],
        )
        assert [o.chapter_number for o in report.by_status("applied")] == [1, 4]
        assert [o.chapter_number for o in report.by_status("skipped")] == [2]
        assert [o.chapter_number for o in report.by_status("failed")] == [3]
        assert report.by_status("nonexistent") == []

    def test_fingerprint_length_constraint(self) -> None:
        with pytest.raises(ValidationError):
            _mark(source_fingerprint="a" * 63)
        with pytest.raises(ValidationError):
            _mark(source_fingerprint="a" * 65)

    def test_chapter_number_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            _mark(chapter_number=0)

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ReplayMark(
                project_id="p",
                run_id="r",
                chapter_number=1,
                draft_version_id="d",
                accepted_version_id="a",
                source_fingerprint=_FP_A,
                unexpected_field="x",  # type: ignore[call-arg]
            )
        with pytest.raises(ValidationError):
            ReplayReport(
                run_id="r",
                project_id="p",
                unexpected_field="x",  # type: ignore[call-arg]
            )
