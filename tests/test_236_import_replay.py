"""Task 236: V15 导入回放幂等标记表 — schema / 迁移 / repo / 模型单测."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import aiosqlite
import pytest
from pydantic import ValidationError

from songyan.db.import_replay_repo import ImportReplayRepository
from songyan.db.migrations import init_schema, run_migrations, verify_schema
from songyan.db.repository import (
    ChapterVersionRepository,
    CharacterRepository,
    ProjectRepository,
)
from songyan.exceptions import ImportReplayError
from songyan.models import Character, ProjectSetting
from songyan.models.import_manifest import ChapterBoundary, SegmentManifest
from songyan.models.import_replay import (
    ChapterReplayOutcome,
    ReplayMark,
    ReplayReport,
)
from songyan.services.import_replay_service import (
    get_or_create_import_draft,
    preflight_replay,
)
from songyan.workflows._helpers import ensure_protagonist_character

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


# ---------------------------------------------------------------------------
# Task 2: preflight + import draft 创建/复用
# ---------------------------------------------------------------------------


def _boundary(chapter_number: int = 1, title: str = "第一章 开端") -> ChapterBoundary:
    return ChapterBoundary(
        chapter_number=chapter_number,
        title=title,
        start_offset=0,
        end_offset=12,
        char_count=10,
        word_count=5,
        est_tokens=8,
        over_token_budget=False,
        body_sha256="c" * 64,
    )


def _manifest(boundaries: list[ChapterBoundary] | None = None) -> SegmentManifest:
    items = boundaries or [_boundary()]
    return SegmentManifest(
        source_path="novel.txt",
        source_sha256=_FP_A,
        normalized_sha256=_FP_B,
        encoding="utf-8",
        line_endings_normalized=False,
        token_budget=6000,
        chapter_count=len(items),
        has_prologue=False,
        prologue_chars=0,
        boundaries=items,
        status="confirmed",
        created_at=datetime.now(UTC),
        confirmed_at=datetime.now(UTC),
    )


async def _seed_project(
    project_id: str = "proj-1", *, with_protagonist: bool = False
) -> None:
    await ProjectRepository().create(
        ProjectSetting(title="测试项目", genre_id="scifi", protagonist_name="林凡"),
        project_id,
    )
    if with_protagonist:
        created = await ensure_protagonist_character(project_id)
        assert created, "测试种子应新建 protagonist 角色"


class TestPreflight:
    """回放前置检查：项目存在 + 主角档案已建档（F1 拦截）."""

    pytestmark = pytest.mark.asyncio

    async def test_missing_project_raises(self, test_db: Path) -> None:
        with pytest.raises(ImportReplayError, match="项目不存在"):
            await preflight_replay("no-such-project", _manifest())

    async def test_missing_protagonist_raises(self, test_db: Path) -> None:
        await _seed_project()
        with pytest.raises(ImportReplayError, match="主角"):
            await preflight_replay("proj-1", _manifest())

    async def test_supporting_only_does_not_satisfy(self, test_db: Path) -> None:
        await _seed_project()
        await CharacterRepository().create(
            Character(
                character_id="char-s1",
                project_id="proj-1",
                name="配角甲",
                role_type="supporting",
            )
        )
        with pytest.raises(ImportReplayError, match="主角"):
            await preflight_replay("proj-1", _manifest())

    async def test_with_protagonist_passes(self, test_db: Path) -> None:
        await _seed_project(with_protagonist=True)
        await preflight_replay("proj-1", _manifest())  # 不抛错即通过


class TestGetOrCreateImportDraft:
    """import draft 创建/复用：同章同指纹幂等复用，指纹变化新建版本."""

    pytestmark = pytest.mark.asyncio

    async def test_first_call_creates_draft_with_import_metadata(
        self, test_db: Path
    ) -> None:
        await _seed_project()
        body = "林凡睁开眼睛，发现自己躺在陌生的房间里。"
        version_id = await get_or_create_import_draft(
            "proj-1",
            _boundary(),
            body,
            source_fingerprint=_FP_A,
            confirmed_at="2026-09-08T10:00:00+00:00",
        )
        assert version_id.startswith("v-")

        version = await ChapterVersionRepository().get(version_id)
        assert version is not None
        assert version.version_number == 1
        assert version.version_type == "draft"
        assert version.chapter_number == 1
        assert version.content == body

        import_meta = version.generation_metadata["import"]
        assert import_meta["source_fingerprint"] == _FP_A
        assert import_meta["segment_chapter"] == 1
        assert import_meta["chapter_title"] == "第一章 开端"
        assert import_meta["confirmed_at"] == "2026-09-08T10:00:00+00:00"

        # 指纹必须可经 json_extract 查询（draft 复用查询依赖此口径）
        async with aiosqlite.connect(str(test_db)) as conn:
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM chapter_versions "
                "WHERE project_id = ? AND chapter_number = ? "
                "AND version_type = 'draft' "
                "AND json_extract(generation_metadata, "
                "'$.import.source_fingerprint') = ?",
                ("proj-1", 1, _FP_A),
            )
            row = await cursor.fetchone()
        assert row is not None and row[0] == 1

    async def test_same_fingerprint_reuses_existing_draft(self, test_db: Path) -> None:
        await _seed_project()
        body = "正文内容。"
        first = await get_or_create_import_draft(
            "proj-1", _boundary(), body,
            source_fingerprint=_FP_A, confirmed_at=None,
        )
        second = await get_or_create_import_draft(
            "proj-1", _boundary(), body,
            source_fingerprint=_FP_A, confirmed_at=None,
        )
        assert second == first
        versions = await ChapterVersionRepository().list_by_chapter("proj-1", 1)
        assert len(versions) == 1

    async def test_different_chapters_do_not_interfere(self, test_db: Path) -> None:
        await _seed_project()
        v1 = await get_or_create_import_draft(
            "proj-1", _boundary(1, "第一章 甲"), "正文一",
            source_fingerprint=_FP_A, confirmed_at=None,
        )
        v2 = await get_or_create_import_draft(
            "proj-1", _boundary(2, "第二章 乙"), "正文二",
            source_fingerprint=_FP_A, confirmed_at=None,
        )
        assert v1 != v2

        again = await get_or_create_import_draft(
            "proj-1", _boundary(1, "第一章 甲"), "正文一",
            source_fingerprint=_FP_A, confirmed_at=None,
        )
        assert again == v1
        assert len(await ChapterVersionRepository().list_by_chapter("proj-1", 1)) == 1
        assert len(await ChapterVersionRepository().list_by_chapter("proj-1", 2)) == 1

    async def test_different_fingerprint_creates_new_draft(
        self, test_db: Path
    ) -> None:
        await _seed_project()
        v1 = await get_or_create_import_draft(
            "proj-1", _boundary(), "正文旧",
            source_fingerprint=_FP_A, confirmed_at=None,
        )
        v2 = await get_or_create_import_draft(
            "proj-1", _boundary(), "正文新",
            source_fingerprint=_FP_B, confirmed_at=None,
        )
        assert v2 != v1

        versions = await ChapterVersionRepository().list_by_chapter("proj-1", 1)
        assert len(versions) == 2
        by_id = {v.version_id: v for v in versions}
        assert by_id[v1].version_number == 1
        assert by_id[v2].version_number == 2
