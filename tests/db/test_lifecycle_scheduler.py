"""Tests for lifecycle scheduler — V4.0 Task 083."""

from __future__ import annotations

from pathlib import Path

import aiosqlite
import pytest

from songyan.db.connection import get_db
from songyan.db.lifecycle_scheduler import (
    LifecycleCleanupResult,
    LifecycleScheduler,
    LifecycleStatus,
    TransitionLog,
    _primary_key_column,
)
from songyan.db.migrations import init_schema


@pytest.fixture
async def lifecycle_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """指向临时初始化数据库的 fixture."""
    import songyan.db.connection as conn_mod

    db_path = tmp_path / "lifecycle.db"
    monkeypatch.setattr(
        conn_mod,
        "settings",
        type("S", (), {"database_url": f"sqlite:///{db_path}"})(),
    )
    await init_schema(db_path)
    # 创建基础 project 记录，供外键引用
    async with get_db() as conn:
        await conn.execute(
            """INSERT INTO projects (project_id, title, genre_id, protagonist_name)
            VALUES (?, ?, ?, ?)""",
            ("p-1", "Test", "xuanhuan", "Lin"),
        )
        await conn.commit()
    return db_path


class TestLifecycleStatus:
    """Layer 1: 模型测试（同步测试）."""

    def test_lifecycle_status_literal(self) -> None:
        valid: list[LifecycleStatus] = ["active", "dormant", "archived"]
        for s in valid:
            assert s in ("active", "dormant", "archived")

    def test_transition_log_serialization(self) -> None:
        log = TransitionLog(
            table="setting_snapshots",
            entity_id="s-1",
            from_status="active",
            to_status="dormant",
            reason="10 chapters stale",
        )
        assert log.table == "setting_snapshots"
        assert log.from_status == "active"
        assert log.to_status == "dormant"

    def test_cleanup_result_serialization(self) -> None:
        result = LifecycleCleanupResult(
            project_id="proj-1",
            current_chapter=50,
            transitions=[
                TransitionLog(
                    table="setting_snapshots",
                    entity_id="s-1",
                    from_status="active",
                    to_status="dormant",
                    reason="test",
                )
            ],
            errors=["mock error"],
        )
        assert result.project_id == "proj-1"
        assert len(result.transitions) == 1
        assert len(result.errors) == 1


class TestLifecycleScheduler:
    """Layer 2: 模块测试."""

    @pytest.fixture
    def scheduler(self) -> LifecycleScheduler:
        return LifecycleScheduler()

    @pytest.mark.asyncio
    async def test_transition_happy_path(
        self, scheduler: LifecycleScheduler, lifecycle_db: Path
    ) -> None:
        """正向：插入数据后 Scheduler.transition() 正常状态流转."""
        async with get_db() as conn:
            # 插入一条 setting_snapshots 记录
            await conn.execute(
                """INSERT INTO setting_snapshots
                    (setting_id, project_id, setting_name, lifecycle_status)
                VALUES (?, ?, ?, ?)""",
                ("s-1", "p-1", "Test Setting", "active"),
            )
            await conn.commit()

            # 执行转换
            log = await scheduler.transition(
                conn, "setting_snapshots", "s-1", "active", "dormant", "10 chapters stale"
            )
            assert log is not None
            assert log.from_status == "active"
            assert log.to_status == "dormant"
            assert log.reason == "10 chapters stale"

            # 验证 DB 状态
            cursor = await conn.execute(
                "SELECT lifecycle_status FROM setting_snapshots WHERE setting_id = ?",
                ("s-1",),
            )
            row = await cursor.fetchone()
            assert row is not None
            assert row[0] == "dormant"

    @pytest.mark.asyncio
    async def test_transition_status_mismatch(
        self, scheduler: LifecycleScheduler, lifecycle_db: Path
    ) -> None:
        """异常：from_status ≠ 当前状态 → 拒绝转换."""
        async with get_db() as conn:
            await conn.execute(
                """INSERT INTO setting_snapshots
                    (setting_id, project_id, setting_name, lifecycle_status)
                VALUES (?, ?, ?, ?)""",
                ("s-2", "p-1", "Test Setting 2", "active"),
            )
            await conn.commit()

            log = await scheduler.transition(
                conn, "setting_snapshots", "s-2", "dormant", "archived", "wrong from"
            )
            assert log is None  # 拒绝转换

    @pytest.mark.asyncio
    async def test_transition_entity_not_found(
        self, scheduler: LifecycleScheduler, lifecycle_db: Path
    ) -> None:
        """异常：entity 不存在 → 返回 None."""
        async with get_db() as conn:
            log = await scheduler.transition(
                conn, "setting_snapshots", "nonexistent", "active", "dormant", "test"
            )
            assert log is None

    @pytest.mark.asyncio
    async def test_run_cleanup_empty_cleaners(
        self, scheduler: LifecycleScheduler, lifecycle_db: Path
    ) -> None:
        """空 cleaners 时不报错."""
        result = await scheduler.run_cleanup("p-1", 50)
        assert result.project_id == "p-1"
        assert result.current_chapter == 50
        assert len(result.transitions) == 0
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_run_cleanup_single_table_failure_not_cascading(
        self, scheduler: LifecycleScheduler, lifecycle_db: Path
    ) -> None:
        """单表失败不级联影响其他表."""

        class FailingCleaner:
            @property
            def table_name(self) -> str:
                return "failing_table"

            async def cleanup(self, conn, project_id, current_chapter):
                raise RuntimeError("simulated failure")

        class SuccessCleaner:
            @property
            def table_name(self) -> str:
                return "success_table"

            async def cleanup(self, conn, project_id, current_chapter):
                return [
                    TransitionLog(
                        table="success_table",
                        entity_id="e-1",
                        from_status="active",
                        to_status="dormant",
                        reason="ok",
                    )
                ]

        scheduler.register_cleaner(FailingCleaner())
        scheduler.register_cleaner(SuccessCleaner())

        result = await scheduler.run_cleanup("p-1", 50)
        assert len(result.errors) == 1
        assert "simulated failure" in result.errors[0]
        assert len(result.transitions) == 1
        assert result.transitions[0].table == "success_table"

    def test_primary_key_column_mapping(self) -> None:
        assert _primary_key_column("setting_snapshots") == "setting_id"
        assert _primary_key_column("foreshadowings") == "foreshadowing_id"
        assert _primary_key_column("human_marks") == "mark_id"
        assert _primary_key_column("character_states") == "state_id"
        assert _primary_key_column("chapter_chunks") == "chunk_id"
        assert _primary_key_column("unknown") == "id"

    def test_register_cleaner(self, scheduler: LifecycleScheduler) -> None:
        class MockCleaner:
            @property
            def table_name(self) -> str:
                return "mock_table"

            async def cleanup(self, conn, project_id, current_chapter):
                return []

        scheduler.register_cleaner(MockCleaner())
        assert len(scheduler._cleaners) == 1


class TestSchemaMigration:
    """Schema 迁移测试 — 验证 5 张表 lifecycle_status 字段."""

    async def _check_column(
        self, conn: aiosqlite.Connection, table: str, column: str
    ) -> bool:
        cursor = await conn.execute(f"PRAGMA table_info({table})")
        cols = {row[1] for row in await cursor.fetchall()}
        return column in cols

    @pytest.mark.asyncio
    async def test_setting_snapshots_has_lifecycle_status(
        self, lifecycle_db: Path
    ) -> None:
        async with get_db() as conn:
            assert await self._check_column(conn, "setting_snapshots", "lifecycle_status")

    @pytest.mark.asyncio
    async def test_foreshadowings_has_lifecycle_status(
        self, lifecycle_db: Path
    ) -> None:
        async with get_db() as conn:
            assert await self._check_column(conn, "foreshadowings", "lifecycle_status")

    @pytest.mark.asyncio
    async def test_human_marks_has_lifecycle_status(
        self, lifecycle_db: Path
    ) -> None:
        async with get_db() as conn:
            assert await self._check_column(conn, "human_marks", "lifecycle_status")

    @pytest.mark.asyncio
    async def test_character_states_has_lifecycle_status(
        self, lifecycle_db: Path
    ) -> None:
        async with get_db() as conn:
            assert await self._check_column(conn, "character_states", "lifecycle_status")

    @pytest.mark.asyncio
    async def test_chapter_chunks_has_lifecycle_status(
        self, lifecycle_db: Path
    ) -> None:
        async with get_db() as conn:
            assert await self._check_column(conn, "chapter_chunks", "lifecycle_status")

    @pytest.mark.asyncio
    async def test_default_value_is_active(self, lifecycle_db: Path) -> None:
        """新插入数据默认 lifecycle_status = 'active'."""
        async with get_db() as conn:
            await conn.execute(
                """INSERT INTO setting_snapshots (setting_id, project_id, setting_name)
                VALUES (?, ?, ?)""",
                ("s-default", "p-1", "Default Test"),
            )
            await conn.commit()
            cursor = await conn.execute(
                "SELECT lifecycle_status FROM setting_snapshots WHERE setting_id = ?",
                ("s-default",),
            )
            row = await cursor.fetchone()
            assert row is not None
            assert row[0] == "active"

    @pytest.mark.asyncio
    async def test_lifecycle_errors_table_exists(self, lifecycle_db: Path) -> None:
        async with get_db() as conn:
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='lifecycle_errors'"
            )
            row = await cursor.fetchone()
            assert row is not None
