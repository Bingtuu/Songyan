"""异步数据库连接管理 — aiosqlite + PRAGMA 配置."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from songyan.config import settings

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    import aiosqlite


def get_db_path() -> Path:
    """从 settings.database_url 解析数据库文件路径.

    Supports:
        sqlite:///relative/path.db  → 相对路径
        sqlite:////absolute/path.db → 绝对路径
    """
    url = settings.database_url
    prefix = "sqlite:///"
    if url.startswith(prefix):
        path_str = url[len(prefix) :]
        return Path(path_str)
    msg = f"Unsupported database_url: {url}"
    raise ValueError(msg)


@asynccontextmanager
async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """异步上下文管理器，提供已配置 PRAGMA 的数据库连接.

    Usage::
        async with get_db() as conn:
            row = await conn.execute_one("SELECT 1")
    """
    import aiosqlite

    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(db_path) as conn:
        await conn.execute("PRAGMA foreign_keys = ON")
        await conn.execute("PRAGMA journal_mode = WAL")
        await conn.execute("PRAGMA synchronous = NORMAL")
        yield conn
