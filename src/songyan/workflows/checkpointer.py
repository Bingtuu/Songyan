"""Checkpointer 工厂 — 统一入口，支持 memory / sqlite 两种实现."""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

from songyan.config import settings
from songyan.db.connection import get_db_path

if TYPE_CHECKING:
    import aiosqlite

# 模块级单例缓存（保持与旧行为一致：同进程内复用）
_checkpointer_instance: BaseCheckpointSaver | None = None


async def get_checkpointer() -> BaseCheckpointSaver:
    """根据 settings.checkpointer_mode 返回对应实现.

    - "memory" → MemorySaver（测试 / Windows 验证环境，无文件锁）
    - "sqlite" → AsyncSqliteSaver（生产环境，持久化 checkpoint）

    同进程内多次调用返回同一实例（单例）。
    """
    global _checkpointer_instance
    if _checkpointer_instance is not None:
        return _checkpointer_instance

    mode = settings.checkpointer_mode
    if mode == "memory":
        _checkpointer_instance = MemorySaver()
        return _checkpointer_instance

    if mode == "sqlite":
        import aiosqlite
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

        db_path = str(get_db_path())
        conn: aiosqlite.Connection = await aiosqlite.connect(db_path)
        await conn.execute("PRAGMA foreign_keys = ON")
        await conn.execute("PRAGMA busy_timeout = 5000")
        saver = AsyncSqliteSaver(conn)
        await saver.setup()
        _checkpointer_instance = saver
        return _checkpointer_instance

    raise ValueError(f"Unsupported checkpointer_mode: {mode!r}")


async def reset_checkpointer_instance(cp: BaseCheckpointSaver | None) -> None:
    """彻底释放 checkpointer 资源.

    步骤：
    1. 关闭底层连接（如果是 AsyncSqliteSaver）
    2. 清空模块级单例引用
    3. 强制垃圾回收，确保后台线程退出
    """
    global _checkpointer_instance

    if cp is not None:
        # AsyncSqliteSaver 持有 aiosqlite 连接
        conn = getattr(cp, "conn", None)
        if conn is not None:
            try:
                await conn.close()
            except (OSError, ConnectionError):
                pass

    _checkpointer_instance = None
    gc.collect()


async def reset_checkpointer() -> None:
    """兼容旧接口：重置共享 checkpointer（测试用）."""
    global _checkpointer_instance
    await reset_checkpointer_instance(_checkpointer_instance)
