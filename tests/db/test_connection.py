"""数据库连接管理测试."""

from __future__ import annotations

from pathlib import Path

import pytest

from songyan.db.connection import get_db, get_db_path
from songyan.db.migrations import init_schema

class TestGetDbPath:
    """get_db_path() 解析测试."""

    def test_relative_path(self, monkeypatch) -> None:
        """sqlite:///relative/path.db 解析为相对路径."""
        monkeypatch.setattr(
            "songyan.db.connection.settings",
            type("S", (), {"database_url": "sqlite:///data/songyan.db"})(),
        )
        path = get_db_path()
        assert path == Path("data/songyan.db")

    def test_absolute_path(self, monkeypatch) -> None:
        """sqlite:////absolute/path.db 解析为绝对路径."""
        monkeypatch.setattr(
            "songyan.db.connection.settings",
            type("S", (), {"database_url": "sqlite:////tmp/songyan.db"})(),
        )
        path = get_db_path()
        assert path == Path("/tmp/songyan.db")

    def test_unsupported_url_raises(self, monkeypatch) -> None:
        """非 sqlite:/// 前缀抛 ValueError."""
        monkeypatch.setattr(
            "songyan.db.connection.settings",
            type("S", (), {"database_url": "postgres://localhost/db"})(),
        )
        with pytest.raises(ValueError, match="Unsupported"):
            get_db_path()


@pytest.mark.asyncio
class TestGetDb:
    """get_db() 异步上下文管理器测试."""

    async def test_context_manager_opens_and_closes(self, tmp_path: Path) -> None:
        """上下文管理器正常开关连接."""
        async with get_db() as conn:
            cursor = await conn.execute("SELECT 1")
            row = await cursor.fetchone()
            assert row[0] == 1

        # 连接应已关闭
        assert not conn._running  # type: ignore[union-attr]

    async def test_pragma_foreign_keys(self, tmp_path: Path) -> None:
        """连接自动启用外键."""
        async with get_db() as conn:
            cursor = await conn.execute("PRAGMA foreign_keys")
            row = await cursor.fetchone()
            assert row[0] == 1

    async def test_pragma_wal_mode(self, tmp_path: Path) -> None:
        """连接使用 WAL 模式."""
        async with get_db() as conn:
            cursor = await conn.execute("PRAGMA journal_mode")
            row = await cursor.fetchone()
            assert row[0].lower() == "wal"

    async def test_auto_creates_parent_dir(self, tmp_path: Path) -> None:
        """数据库父目录不存在时自动创建."""
        db_path = tmp_path / "nested" / "deep" / "test.db"

        # 临时修改 settings.database_url
        import songyan.db.connection as conn_mod

        original_settings = conn_mod.settings
        conn_mod.settings = type(
            "S", (), {"database_url": f"sqlite:///{db_path}"}
        )()

        try:
            async with get_db() as conn:
                await conn.execute("SELECT 1")
            assert db_path.parent.exists()
        finally:
            conn_mod.settings = original_settings


@pytest.mark.asyncio
class TestConnectionWithSchema:
    """连接 + Schema 集成测试."""

    async def test_init_and_query(self, tmp_path: Path) -> None:
        """初始化 schema 后可通过连接查询."""
        import songyan.db.connection as conn_mod

        db_path = tmp_path / "integrated.db"
        original_settings = conn_mod.settings
        conn_mod.settings = type(
            "S", (), {"database_url": f"sqlite:///{db_path}"}
        )()

        try:
            await init_schema()

            async with get_db() as conn:
                cursor = await conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
                rows = await cursor.fetchall()
                tables = {r[0] for r in rows}
                assert "projects" in tables
                assert "chapter_versions" in tables
        finally:
            conn_mod.settings = original_settings
