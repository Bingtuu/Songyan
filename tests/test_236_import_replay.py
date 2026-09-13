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


# ---------------------------------------------------------------------------
# Task 3: 回放循环核心（extract / summary 均 mock，零真实 LLM）
# ---------------------------------------------------------------------------

from unittest.mock import AsyncMock, patch  # noqa: E402

from songyan.db.repository import ChapterHeadRepository  # noqa: E402
from songyan.exceptions import LLMError  # noqa: E402
from songyan.models import StateSettlement  # noqa: E402
from songyan.models.settlement import CharacterUpdate  # noqa: E402
from songyan.services.import_replay_service import replay_import  # noqa: E402
from songyan.services.import_segment_service import (  # noqa: E402
    build_manifest,
    confirm_manifest,
    load_manifest,
    write_segment_artifacts,
)

_SOURCE_TEXT = (
    "第一章 荒山\n林凡睁开眼睛，发现自己躺在荒山之中。\n\n"
    "第二章 下山\n林凡拍了拍尘土，朝山下走去。\n\n"
    "第三章 小镇\n林凡走进小镇，听见远处的钟声。\n"
)


def _write_source(tmp_path: Path, text: str = _SOURCE_TEXT) -> Path:
    source = tmp_path / "novel.txt"
    source.write_text(text, encoding="utf-8")
    return source


def _confirmed_manifest(tmp_path: Path, out_name: str = "segment_out") -> Path:
    """用 Task 235 的真实产物链路造 3 章 confirmed 清单，返回 manifest 路径."""
    source = _write_source(tmp_path)
    manifest, normalized, bodies = build_manifest(source, token_budget=6000)
    manifest_path, _ = write_segment_artifacts(
        tmp_path / out_name, manifest, normalized, bodies
    )
    confirm_manifest(manifest_path)
    return manifest_path


def _canned_settlement(character_id: str) -> StateSettlement:
    return StateSettlement(
        character_updates=[
            CharacterUpdate(
                character_id=character_id,
                field="location",
                old_value="未知",
                new_value="荒山",
                source_quote="林凡睁开眼睛",
            )
        ],
        validation_status="valid",
        impact_score=0.5,
    )


async def _protagonist_id(project_id: str = "proj-1") -> str:
    characters = await CharacterRepository().list_by_project(project_id)
    return next(c.character_id for c in characters if c.role_type == "protagonist")


async def _state_snapshot_count(db_path: Path, character_id: str) -> int:
    async with aiosqlite.connect(str(db_path)) as conn:
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM character_states WHERE character_id = ?",
            (character_id,),
        )
        row = await cursor.fetchone()
        assert row is not None
        return int(row[0])


class TestReplayImport:
    """回放主循环：happy path / 幂等 / 断点续跑 / 隔离 / 闸门拒绝."""

    pytestmark = pytest.mark.asyncio

    @pytest.fixture
    def mock_extract(self):
        with patch(
            "songyan.services.import_replay_service.extract_settlement",
            new_callable=AsyncMock,
        ) as mock:
            yield mock

    @pytest.fixture
    def mock_summary(self):
        with patch(
            "songyan.services.import_replay_service.write_chapter_summary_with_fact_check",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = ("sum-test", None, [])
            yield mock

    async def test_happy_path_applies_all_chapters(
        self, test_db: Path, tmp_path: Path, mock_extract, mock_summary
    ) -> None:
        await _seed_project(with_protagonist=True)
        pid = await _protagonist_id()
        mock_extract.side_effect = lambda *args, **kwargs: _canned_settlement(pid)
        manifest_path = _confirmed_manifest(tmp_path)
        fingerprint = load_manifest(manifest_path).source_sha256

        report = await replay_import("proj-1", manifest_path)

        assert report.project_id == "proj-1"
        assert report.run_id.startswith("run-")
        assert [o.status for o in report.outcomes] == ["applied"] * 3
        assert [o.chapter_number for o in report.outcomes] == [1, 2, 3]
        assert all(o.accepted_version_id for o in report.outcomes)
        assert mock_extract.await_count == 3
        assert mock_summary.await_count == 3

        # chapter_heads：3 章 accepted
        heads = await ChapterHeadRepository().list_by_project("proj-1")
        assert len(heads) == 3
        assert all(h.status == "accepted" for h in heads)
        by_chapter = {h.chapter_number: h for h in heads}
        for outcome in report.outcomes:
            head = by_chapter[outcome.chapter_number]
            assert head.accepted_version_id == outcome.accepted_version_id
            assert head.current_version_id == outcome.accepted_version_id

        # 幂等标记：3 行，绑定清单指纹与本 run
        assert await _mark_count(test_db) == 3
        mark = await ImportReplayRepository().get_mark("proj-1", 1)
        assert mark is not None
        assert mark.run_id == report.run_id
        assert mark.source_fingerprint == fingerprint
        assert mark.summary_id == "sum-test"

        # 事实库：主角状态快照已写入
        assert await _state_snapshot_count(test_db, pid) == 3

        # accepted 版本行存在，且继承 draft 的 import 来源标记（可溯源自径）
        for outcome in report.outcomes:
            version = await ChapterVersionRepository().get(
                outcome.accepted_version_id or ""
            )
            assert version is not None
            assert version.version_type == "accepted"
            import_meta = version.generation_metadata["import"]
            assert import_meta["source_fingerprint"] == fingerprint
            assert import_meta["segment_chapter"] == outcome.chapter_number

    async def test_chapters_filter_limits_scope(
        self, test_db: Path, tmp_path: Path, mock_extract, mock_summary
    ) -> None:
        await _seed_project(with_protagonist=True)
        pid = await _protagonist_id()
        mock_extract.side_effect = lambda *args, **kwargs: _canned_settlement(pid)
        manifest_path = _confirmed_manifest(tmp_path)

        report = await replay_import("proj-1", manifest_path, chapters={1, 3})

        assert [o.chapter_number for o in report.outcomes] == [1, 3]
        assert mock_extract.await_count == 2
        assert await _mark_count(test_db) == 2
        assert await ChapterHeadRepository().get("proj-1", 2) is None

    async def test_rerun_is_idempotent_with_zero_llm_calls(
        self, test_db: Path, tmp_path: Path, mock_extract, mock_summary
    ) -> None:
        await _seed_project(with_protagonist=True)
        pid = await _protagonist_id()
        mock_extract.side_effect = lambda *args, **kwargs: _canned_settlement(pid)
        manifest_path = _confirmed_manifest(tmp_path)

        first = await replay_import("proj-1", manifest_path)
        assert len(first.by_status("applied")) == 3

        mock_extract.reset_mock()
        mock_summary.reset_mock()
        second = await replay_import("proj-1", manifest_path, run_id="run-resume")

        assert [o.status for o in second.outcomes] == ["skipped"] * 3
        assert second.run_id == "run-resume"
        # 断点续跑核心承诺：已应用章零 LLM 调用
        assert mock_extract.await_count == 0
        assert mock_summary.await_count == 0
        assert await _mark_count(test_db) == 3
        # skipped outcome 仍携带已 accepted 的版本引用
        assert all(o.accepted_version_id for o in second.outcomes)

    async def test_resume_after_chapter_llm_failure(
        self, test_db: Path, tmp_path: Path, mock_extract, mock_summary
    ) -> None:
        await _seed_project(with_protagonist=True)
        pid = await _protagonist_id()
        manifest_path = _confirmed_manifest(tmp_path)

        def _fail_chapter_2(*args: object, **kwargs: object) -> StateSettlement:
            if args[2] == 2:
                raise LLMError("mock llm down")
            return _canned_settlement(pid)

        mock_extract.side_effect = _fail_chapter_2
        first = await replay_import("proj-1", manifest_path)

        assert [o.status for o in first.outcomes] == ["applied", "failed", "applied"]
        failed = first.by_status("failed")
        assert len(failed) == 1
        assert failed[0].chapter_number == 2
        assert "mock llm down" in (failed[0].error or "")
        # 失败章：无 accepted head、无幂等标记
        assert await ChapterHeadRepository().get("proj-1", 2) is None
        assert await ImportReplayRepository().get_mark("proj-1", 2) is None
        assert await _mark_count(test_db) == 2

        # 重跑：只对第 2 章发起 LLM 调用，其余章幂等跳过
        mock_extract.reset_mock()
        mock_extract.side_effect = lambda *args, **kwargs: _canned_settlement(pid)
        second = await replay_import("proj-1", manifest_path)

        assert [o.status for o in second.outcomes] == ["skipped", "applied", "skipped"]
        assert mock_extract.await_count == 1
        assert mock_extract.call_args.args[2] == 2
        assert await _mark_count(test_db) == 3
        heads = await ChapterHeadRepository().list_by_project("proj-1")
        assert len(heads) == 3
        assert all(h.status == "accepted" for h in heads)

    async def test_needs_human_review_isolates_chapter(
        self, test_db: Path, tmp_path: Path, mock_extract, mock_summary
    ) -> None:
        await _seed_project(with_protagonist=True)
        pid = await _protagonist_id()

        def _invalid_chapter_2(*args: object, **kwargs: object) -> StateSettlement:
            if args[2] == 2:
                return StateSettlement(
                    validation_status="needs_human_review",
                    validation_errors=["角色旧值与 DB 当前值不一致"],
                )
            return _canned_settlement(pid)

        mock_extract.side_effect = _invalid_chapter_2
        manifest_path = _confirmed_manifest(tmp_path)

        report = await replay_import("proj-1", manifest_path)

        assert [o.status for o in report.outcomes] == ["applied", "failed", "applied"]
        failed = report.by_status("failed")[0]
        assert failed.chapter_number == 2
        assert "needs_human_review" in (failed.error or "")
        assert "角色旧值" in (failed.error or "")
        # 非 valid settlement 不进事务：无版本被 accept、无标记
        assert await ChapterHeadRepository().get("proj-1", 2) is None
        assert await ImportReplayRepository().get_mark("proj-1", 2) is None
        assert await _mark_count(test_db) == 2
        versions = await ChapterVersionRepository().list_by_chapter("proj-1", 2)
        assert all(v.version_type != "accepted" for v in versions)
        # 失败章的 summary 不应生成
        assert mock_summary.await_count == 2

    async def test_fingerprint_change_rejected(
        self, test_db: Path, tmp_path: Path, mock_extract, mock_summary
    ) -> None:
        await _seed_project(with_protagonist=True)
        pid = await _protagonist_id()
        mock_extract.side_effect = lambda *args, **kwargs: _canned_settlement(pid)
        manifest_path = _confirmed_manifest(tmp_path)

        first = await replay_import("proj-1", manifest_path)
        assert len(first.by_status("applied")) == 3

        # 源文件变更后重新 segment + confirm（指纹随之变化）
        _write_source(tmp_path, text=_SOURCE_TEXT + "\n第四章 进城\n林凡进了城。\n")
        source = tmp_path / "novel.txt"
        manifest, normalized, bodies = build_manifest(source, token_budget=6000)
        new_manifest_path, _ = write_segment_artifacts(
            tmp_path / "segment_out_v2", manifest, normalized, bodies
        )
        confirm_manifest(new_manifest_path)

        mock_extract.reset_mock()
        with pytest.raises(ImportReplayError, match="指纹"):
            await replay_import("proj-1", new_manifest_path)
        assert mock_extract.await_count == 0
        assert await _mark_count(test_db) == 3

    async def test_missing_protagonist_rejected_before_extract(
        self, test_db: Path, tmp_path: Path, mock_extract, mock_summary
    ) -> None:
        await _seed_project(with_protagonist=False)
        manifest_path = _confirmed_manifest(tmp_path)

        with pytest.raises(ImportReplayError, match="主角"):
            await replay_import("proj-1", manifest_path)
        mock_extract.assert_not_called()
        assert await _mark_count(test_db) == 0

    async def test_summary_failure_does_not_block_apply(
        self, test_db: Path, tmp_path: Path, mock_extract, mock_summary
    ) -> None:
        await _seed_project(with_protagonist=True)
        pid = await _protagonist_id()
        mock_extract.side_effect = lambda *args, **kwargs: _canned_settlement(pid)
        mock_summary.side_effect = LLMError("summary boom")
        manifest_path = _confirmed_manifest(tmp_path)

        report = await replay_import("proj-1", manifest_path)

        # 摘要失败不阻断 accept（对齐 _nodes.py fallback 语义）
        assert [o.status for o in report.outcomes] == ["applied"] * 3
        assert await _mark_count(test_db) == 3
        heads = await ChapterHeadRepository().list_by_project("proj-1")
        assert len(heads) == 3
        mark = await ImportReplayRepository().get_mark("proj-1", 1)
        assert mark is not None
        assert mark.summary_id is None
