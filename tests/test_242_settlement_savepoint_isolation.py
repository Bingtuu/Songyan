"""Task 242: settlement 降级块 SAVEPOINT 隔离与事务死亡上抛.

真实 SQLite 场景（AsyncMock 连接测不到事务语义）：
- 降级块中途失败 → 块内已写部分回滚到 savepoint，核心写入完好；
- 事务被 SQLite 整体回滚（FULL/IOERR 类）→ SettlementError 上抛，
  阻止章节带着损坏事实库进入 accepted / 写幂等标记。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import AsyncMock

import aiosqlite
import pytest
from structlog.testing import capture_logs

import songyan.agents.settlement_extractor._apply as apply_mod
from songyan.agents.settlement_extractor._apply import apply_settlement
from songyan.db.connection import get_db
from songyan.db.repository import ChapterVersionRepository, CharacterRepository, ProjectRepository
from songyan.exceptions import SettlementError
from songyan.models import (
    ChapterVersion,
    CharacterUpdate,
    NewSetting,
    ProjectSetting,
    StateSettlement,
)
from songyan.workflows._helpers import ensure_protagonist_character


async def _seed(test_db: Path) -> str:
    """建项目 + 主角 + 版本 v1，返回 protagonist character_id."""
    await ProjectRepository().create(
        ProjectSetting(title="测试项目", genre_id="scifi", protagonist_name="林凡"),
        "proj-1",
    )
    assert await ensure_protagonist_character("proj-1")
    await ChapterVersionRepository().create(
        ChapterVersion(
            version_id="v1",
            project_id="proj-1",
            chapter_number=1,
            version_number=1,
            version_type="draft",
            content="正文",
            word_count=2,
        )
    )
    characters = await CharacterRepository().list_by_project("proj-1")
    return next(c.character_id for c in characters if c.role_type == "protagonist")


def _settlement(pid: str) -> StateSettlement:
    return StateSettlement(
        character_updates=[
            CharacterUpdate(
                character_id=pid,
                field="location",
                old_value="未知",
                new_value="荒山",
                source_quote="q",
            )
        ],
        new_settings=[
            NewSetting(
                setting_name="星门网络",
                description="跨越星系的通道网络",
                source_quote="q",
                setting_key="scifi.tech.stargate_network",
            )
        ],
        validation_status="valid",
    )


async def _count(db_path: Path, table: str) -> int:
    async with aiosqlite.connect(str(db_path)) as conn:
        cursor = await conn.execute(f"SELECT COUNT(*) FROM {table}")
        row = await cursor.fetchone()
        assert row is not None
        return int(row[0])


class _FailingLocationRepo:
    """create 抛 sqlite3.OperationalError（模拟块内中途失败）."""

    async def create(self, *args: object, **kwargs: object) -> None:
        raise sqlite3.OperationalError("database is locked")


class _TransactionKillerLocationRepo:
    """create 先 ROLLBACK 整个事务（模拟 SQLite 整体回滚）再抛 IOERR 类错误."""

    async def create(self, *args: object, **kwargs: object) -> None:
        conn = kwargs.get("conn")
        assert conn is not None
        await conn.execute("ROLLBACK")
        raise sqlite3.OperationalError("disk I/O error")


class TestDegradedBlockSavepointIsolation:
    pytestmark = pytest.mark.asyncio

    async def test_partial_writes_of_degraded_block_rolled_back(
        self, test_db: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """continuity 块中途失败：块内已写的 setting_tracking 行回滚，核心写入完好."""
        pid = await _seed(test_db)
        monkeypatch.setattr(
            apply_mod, "LocationTrackerRepository", _FailingLocationRepo
        )

        async with get_db() as conn:
            with capture_logs() as logs:
                await apply_settlement(
                    _settlement(pid), "proj-1", 1, "v1", conn=conn
                )
            await conn.commit()

        events = [log["event"] for log in logs]
        assert "settlement.continuity_tracking_failed" in events
        # 降级块回滚：setting_tracking 无该设定行
        assert await _count(test_db, "setting_tracking") == 0
        assert await _count(test_db, "location_tracker") == 0
        # 核心写入完好：setting_snapshots / character_states 各自入库
        assert await _count(test_db, "setting_snapshots") == 1
        assert await _count(test_db, "character_states") == 1

    async def test_transaction_death_reraises_settlement_error(
        self, test_db: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """事务被整体回滚（FULL/IOERR 类）→ SettlementError 上抛，核心写入已丢."""
        pid = await _seed(test_db)
        monkeypatch.setattr(
            apply_mod, "LocationTrackerRepository", _TransactionKillerLocationRepo
        )

        async with get_db() as conn:
            with pytest.raises(SettlementError):
                await apply_settlement(
                    _settlement(pid), "proj-1", 1, "v1", conn=conn
                )

        # 事务已整体回滚：核心写入（character_states / setting_snapshots）不存在
        assert await _count(test_db, "character_states") == 0
        assert await _count(test_db, "setting_snapshots") == 0

    async def test_mock_conn_still_swallows_degraded_failure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AsyncMock conn（in_transaction truthy）保持 Task 239 的 warn-and-continue."""

        async def _boom(**kwargs: object) -> None:
            raise sqlite3.OperationalError("disk I/O error")

        monkeypatch.setattr(apply_mod, "_update_continuity_tracking", _boom)
        with capture_logs() as logs:
            await apply_settlement(
                StateSettlement(),
                "p1",
                3,
                "v1",
                conn=AsyncMock(),
                char_repo=AsyncMock(),
                setting_repo=AsyncMock(),
                foreshadowing_repo=AsyncMock(),
                numerical_repo=AsyncMock(),
            )
        events = [log["event"] for log in logs]
        assert "settlement.continuity_tracking_failed" in events


class TestTransactionBoundary:
    """Task 243: SAVEPOINT 自成最外层事务时 RELEASE 即提交——事务必须提前打开."""

    pytestmark = pytest.mark.asyncio

    async def test_empty_settlement_leaves_transaction_open(
        self, test_db: Path
    ) -> None:
        """空 settlement（核心块零写入）apply 后事务仍打开，留给调用方 commit.

        修复前：第一个 SAVEPOINT 成为最外层事务，RELEASE 直接提交，
        in_transaction 回落为 False，后续 accept/幂等标记失去原子性。
        """
        await _seed(test_db)
        async with get_db() as conn:
            await apply_settlement(
                StateSettlement(validation_status="valid"),
                "proj-1",
                1,
                "v1",
                conn=conn,
            )
            assert conn.in_transaction is True
            await conn.commit()

    async def test_no_double_begin_when_transaction_already_open(
        self, test_db: Path
    ) -> None:
        """连接已在事务中时不重复 BEGIN（不抛 cannot start a transaction）."""
        pid = await _seed(test_db)
        async with get_db() as conn:
            # 先写一行打开事务
            await conn.execute(
                "INSERT INTO location_tracker (track_id, project_id, character_id,"
                " location) VALUES ('loc-pre', 'proj-1', ?, '荒山')",
                (pid,),
            )
            assert conn.in_transaction is True
            await apply_settlement(
                StateSettlement(validation_status="valid"),
                "proj-1",
                1,
                "v1",
                conn=conn,
            )
            await conn.commit()
        assert await _count(test_db, "location_tracker") == 1

    async def test_caller_rollback_leaves_no_residue(self, test_db: Path) -> None:
        """空 settlement apply 后调用方 rollback：无任何残留（RELEASE 未提前提交）."""
        await _seed(test_db)
        async with get_db() as conn:
            await apply_settlement(
                StateSettlement(validation_status="valid"),
                "proj-1",
                1,
                "v1",
                conn=conn,
            )
            await conn.rollback()
        # 降级块未被提前提交：本场景本无写入，断言无异常即通过；
        # 真正的原子性证据是上一个测试的 in_transaction 仍为 True。
        assert await _count(test_db, "setting_tracking") == 0
