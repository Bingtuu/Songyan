"""Task 241: foreshadowings resolve 可追溯列（resolved_chapter / resolved_version_id）.

新列只写不读：人确认销账（canon confirm promise）时回填回收发生的章号与版本，
不改任何 SELECT 口径；due/overdue 自动翻转不回填；历史行保持 NULL。

注（2026-11 评审修复，tech-m2 §3.2/§4.3.3/B3）：apply_settlement / import 回放
对模型声称的 resolve 只留提案，不再写 resolved——本文件 TestApplyResolveTrace /
TestReplayResolveTrace 已按提案语义改写；repo 层 update_status 行为不变。
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import aiosqlite
import pytest

from songyan.db.import_replay_repo import ImportReplayRepository
from songyan.db.migrations import init_schema, run_migrations
from songyan.db.repository import (
    ChapterVersionRepository,
    ProjectRepository,
)
from songyan.db.settlement_repo import ForeshadowingRepository
from songyan.models import (
    ChapterVersion,
    ForeshadowingItem,
    ForeshadowingUpdate,
    ProjectSetting,
    StateSettlement,
)


async def _seed_project(project_id: str = "proj-1") -> None:
    await ProjectRepository().create(
        ProjectSetting(title="测试项目", genre_id="scifi", protagonist_name="林凡"),
        project_id,
    )


async def _seed_version(version_id: str, project_id: str = "proj-1") -> None:
    await ChapterVersionRepository().create(
        ChapterVersion(
            version_id=version_id,
            project_id=project_id,
            chapter_number=1,
            version_number=1,
            version_type="accepted",
            content="正文",
            word_count=2,
        )
    )


async def _seed_foreshadowing(
    foreshadowing_id: str = "fs-1",
    project_id: str = "proj-1",
    source_version_id: str = "v-plant",
) -> None:
    await ForeshadowingRepository().create(
        ForeshadowingItem(
            foreshadowing_id=foreshadowing_id,
            description="山门之谜",
            planted_in_chapter=1,
            expected_resolve_chapter=None,
            status="planted",
        ),
        project_id,
        source_version_id,
    )


async def _read_foreshadowing(
    db_path: Path, foreshadowing_id: str
) -> tuple[str, int | None, str | None]:
    async with aiosqlite.connect(str(db_path)) as conn:
        cursor = await conn.execute(
            "SELECT status, resolved_chapter, resolved_version_id "
            "FROM foreshadowings WHERE foreshadowing_id = ?",
            (foreshadowing_id,),
        )
        row = await cursor.fetchone()
    assert row is not None
    return (str(row[0]), row[1], row[2])


class TestSchema:
    """新库/旧库两条路径都应有可追溯列；历史行保持 NULL."""

    pytestmark = pytest.mark.asyncio

    async def test_fresh_schema_has_resolved_columns(self, tmp_path: Path) -> None:
        db_path = tmp_path / "fresh.db"
        await init_schema(str(db_path))
        async with aiosqlite.connect(str(db_path)) as conn:
            cursor = await conn.execute("PRAGMA table_info(foreshadowings)")
            columns = {row[1] for row in await cursor.fetchall()}
        assert "resolved_chapter" in columns
        assert "resolved_version_id" in columns

    async def test_migration_backfills_old_db(self, tmp_path: Path) -> None:
        """旧库（无新列）跑迁移后补列，既有行 resolved_* 保持 NULL."""
        db_path = tmp_path / "old.db"
        await init_schema(str(db_path))
        async with aiosqlite.connect(str(db_path)) as conn:
            await conn.execute("DROP TABLE foreshadowings")
            await conn.execute(
                """CREATE TABLE foreshadowings (
                    foreshadowing_id        TEXT PRIMARY KEY,
                    project_id              TEXT NOT NULL,
                    description             TEXT NOT NULL,
                    planted_in_chapter      INTEGER NOT NULL,
                    expected_resolve_chapter INTEGER,
                    status                  TEXT DEFAULT 'planted',
                    lifecycle_status        TEXT DEFAULT 'active',
                    source_version_id       TEXT NOT NULL,
                    created_at              TEXT DEFAULT (datetime('now'))
                )"""
            )
            await conn.execute(
                "INSERT INTO foreshadowings ("
                "foreshadowing_id, project_id, description, planted_in_chapter,"
                " status, source_version_id"
                ") VALUES ('fs-old', 'proj-1', '旧伏笔', 1, 'resolved', 'v-old')"
            )
            await conn.commit()

            await run_migrations(conn)
            await conn.commit()

            cursor = await conn.execute("PRAGMA table_info(foreshadowings)")
            columns = {row[1] for row in await cursor.fetchall()}
            assert "resolved_chapter" in columns
            assert "resolved_version_id" in columns

            cursor = await conn.execute(
                "SELECT resolved_chapter, resolved_version_id "
                "FROM foreshadowings WHERE foreshadowing_id = 'fs-old'"
            )
            row = await cursor.fetchone()
            assert row is not None
            # 历史 resolve 时刻不可考，不回填、不猜测
            assert row[0] is None
            assert row[1] is None


class TestUpdateStatusBackfill:
    """repo 层：resolve 回填；非 resolve 状态翻转不回填."""

    pytestmark = pytest.mark.asyncio

    async def test_resolve_backfills_trace_columns(self, test_db: Path) -> None:
        await _seed_project()
        await _seed_version("v-plant")
        await _seed_foreshadowing()

        await ForeshadowingRepository().update_status(
            "fs-1", "resolved", resolved_chapter=5, resolved_version_id="v-resolve"
        )

        status, resolved_chapter, resolved_version_id = await _read_foreshadowing(
            test_db, "fs-1"
        )
        assert status == "resolved"
        assert resolved_chapter == 5
        assert resolved_version_id == "v-resolve"

    async def test_non_resolve_status_flip_leaves_trace_null(
        self, test_db: Path
    ) -> None:
        await _seed_project()
        await _seed_version("v-plant")
        await _seed_foreshadowing()

        await ForeshadowingRepository().update_status("fs-1", "overdue")

        status, resolved_chapter, resolved_version_id = await _read_foreshadowing(
            test_db, "fs-1"
        )
        assert status == "overdue"
        assert resolved_chapter is None
        assert resolved_version_id is None

    async def test_mark_overdue_leaves_trace_null(self, test_db: Path) -> None:
        await _seed_project()
        await _seed_version("v-plant")
        await _seed_foreshadowing()
        await ForeshadowingRepository().update_status("fs-1", "due")

        await ForeshadowingRepository().mark_overdue("proj-1", 10)

        status, resolved_chapter, resolved_version_id = await _read_foreshadowing(
            test_db, "fs-1"
        )
        assert status == "due"  # expected_resolve_chapter=None 不触发翻转
        assert resolved_chapter is None
        assert resolved_version_id is None


class TestApplyResolveTrace:
    """apply 层：resolve 只是提案——不调 update_status，只留痕（tech-m2 B3）。"""

    pytestmark = pytest.mark.asyncio

    async def test_apply_resolve_records_proposal_only(self) -> None:
        from songyan.agents.settlement_extractor._apply import apply_settlement

        foreshadowing_repo = AsyncMock()
        settlement = StateSettlement(
            foreshadowing_updates=[
                ForeshadowingUpdate(
                    foreshadowing_id="fs-1",
                    operation="resolve",
                    description="山门之谜",
                )
            ],
            validation_status="valid",
        )
        await apply_settlement(
            settlement,
            "p1",
            3,
            "v1",
            conn=AsyncMock(),
            char_repo=AsyncMock(),
            setting_repo=AsyncMock(),
            foreshadowing_repo=foreshadowing_repo,
            numerical_repo=AsyncMock(),
        )
        foreshadowing_repo.update_status.assert_not_called()
        assert settlement.observation_counts["foreshadowing_resolve_proposed"] == 1


class TestReplayResolveTrace:
    """回放路径：resolve 只进提案（open 集不变），resolved 唯有人确认销账可写。"""

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

    async def test_replay_resolve_records_proposal_keeps_open_set(
        self, test_db: Path, tmp_path: Path, mock_extract, mock_summary
    ) -> None:
        from songyan.services.import_replay_service import replay_import
        from songyan.services.import_segment_service import (
            build_manifest,
            confirm_manifest,
            write_segment_artifacts,
        )
        from songyan.workflows._helpers import ensure_protagonist_character

        def _settlement_by_chapter(chapter: int) -> StateSettlement:
            if chapter == 1:
                return StateSettlement(
                    foreshadowing_updates=[
                        ForeshadowingUpdate(
                            foreshadowing_id="fs-trace",
                            operation="plant",
                            description="山门之谜",
                        )
                    ],
                    validation_status="valid",
                )
            if chapter == 2:
                return StateSettlement(
                    foreshadowing_updates=[
                        ForeshadowingUpdate(
                            foreshadowing_id="fs-trace",
                            operation="resolve",
                            description="山门之谜",
                        )
                    ],
                    validation_status="valid",
                )
            return StateSettlement(validation_status="valid")

        mock_extract.side_effect = lambda *args, **kwargs: _settlement_by_chapter(
            args[2]
        )

        await _seed_project()
        assert await ensure_protagonist_character("proj-1")

        source = tmp_path / "novel.txt"
        source.write_text(
            "第一章 荒山\n林凡睁开眼睛，发现自己躺在荒山之中。\n\n"
            "第二章 下山\n林凡拍了拍尘土，朝山下走去。\n\n"
            "第三章 小镇\n林凡走进小镇，听见远处的钟声。\n",
            encoding="utf-8",
        )
        manifest, normalized, bodies = build_manifest(source, token_budget=6000)
        manifest_path, _ = write_segment_artifacts(
            tmp_path / "segment_out", manifest, normalized, bodies
        )
        confirm_manifest(manifest_path)

        report = await replay_import("proj-1", manifest_path)
        assert [o.status for o in report.outcomes] == ["applied"] * 3

        # 提案语义：回放不直写 resolved；行仍在 open 集，追溯列为 NULL
        status, resolved_chapter, resolved_version_id = await _read_foreshadowing(
            test_db, "fs-trace"
        )
        assert status in ("planted", "due", "overdue")
        assert resolved_chapter is None
        assert resolved_version_id is None
        mark = await ImportReplayRepository().get_mark("proj-1", 2)
        assert mark is not None
