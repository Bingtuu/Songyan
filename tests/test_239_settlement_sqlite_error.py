"""Task 239: settlement 写入路径统一捕获 sqlite3.Error.

四处 try/except 块（核心写入 / 伏笔压力 / 设定回收 / continuity tracking）的
catch 列表原本不含 ``sqlite3.Error``：aiosqlite 抛出的 OperationalError /
IntegrityError 直接继承 ``Exception``，会绕过结构化日志。本文件钉死修复后
语义——核心块记 ``settlement.failed`` 后原样上抛；三个降级块记 warning 后继续。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from structlog.testing import capture_logs

import songyan.agents.settlement_extractor._apply as apply_mod
from songyan.agents.settlement_extractor._apply import apply_settlement
from songyan.models import Character, CharacterUpdate, StateSettlement


def _char_repo_with_protagonist() -> AsyncMock:
    repo = AsyncMock()
    repo.list_by_project.return_value = [
        Character(character_id="c1", project_id="p1", name="Test", role_type="protagonist")
    ]
    return repo


def _settlement_with_char_update() -> StateSettlement:
    return StateSettlement(
        character_updates=[
            CharacterUpdate(
                character_id="c1",
                field="mood",
                old_value="a",
                new_value="b",
                source_quote="q",
            )
        ]
    )


class TestCoreBlockSqliteError:
    """核心写入块：sqlite3.Error 记 settlement.failed 后原样上抛."""

    async def test_integrity_error_logged_and_reraised(self) -> None:
        char_repo = _char_repo_with_protagonist()
        char_repo.add_state_snapshot.side_effect = sqlite3.IntegrityError(
            "UNIQUE constraint failed: character_states"
        )
        with capture_logs() as logs, pytest.raises(sqlite3.IntegrityError):
            await apply_settlement(
                _settlement_with_char_update(),
                "p1",
                3,
                "v1",
                conn=AsyncMock(),
                char_repo=char_repo,
                setting_repo=AsyncMock(),
                foreshadowing_repo=AsyncMock(),
                numerical_repo=AsyncMock(),
            )
        events = [log["event"] for log in logs]
        assert "settlement.failed" in events

    async def test_operational_locked_error_logged_and_reraised(self) -> None:
        char_repo = _char_repo_with_protagonist()
        char_repo.add_state_snapshot.side_effect = sqlite3.OperationalError(
            "database is locked"
        )
        with capture_logs() as logs, pytest.raises(sqlite3.OperationalError):
            await apply_settlement(
                _settlement_with_char_update(),
                "p1",
                3,
                "v1",
                conn=AsyncMock(),
                char_repo=char_repo,
                setting_repo=AsyncMock(),
                foreshadowing_repo=AsyncMock(),
                numerical_repo=AsyncMock(),
            )
        events = [log["event"] for log in logs]
        assert "settlement.failed" in events


class TestDegradedBlocksSqliteError:
    """三个降级块：sqlite3.Error 记 warning 后不阻塞主流程."""

    async def test_pressure_block_sqlite_error_degrades(self, test_db: Path) -> None:
        foreshadowing_repo = AsyncMock()
        foreshadowing_repo.mark_overdue.side_effect = sqlite3.OperationalError(
            "database is locked"
        )
        with capture_logs() as logs:
            await apply_settlement(
                StateSettlement(),
                "p1",
                3,
                "v1",
                conn=AsyncMock(),
                char_repo=AsyncMock(),
                setting_repo=AsyncMock(),
                foreshadowing_repo=foreshadowing_repo,
                numerical_repo=AsyncMock(),
            )
        events = [log["event"] for log in logs]
        assert "settlement.foreshadowing_pressure_failed" in events

    async def test_recycling_block_sqlite_error_degrades(
        self, test_db: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        class _FailingTrackingRepo:
            async def list_by_project(self, project_id: str) -> list[dict]:
                raise sqlite3.OperationalError("database is locked")

        monkeypatch.setattr(
            apply_mod, "SettingTrackingRepository", lambda: _FailingTrackingRepo()
        )
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
                content="某章正文内容",
            )
        events = [log["event"] for log in logs]
        assert "settlement.recycling_detection_failed" in events

    async def test_continuity_block_sqlite_error_degrades(
        self, test_db: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
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
