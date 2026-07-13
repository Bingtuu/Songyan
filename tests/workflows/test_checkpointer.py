"""Checkpointer 工厂测试 — Task 075."""

from __future__ import annotations

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from songyan.config import settings
from songyan.workflows.checkpointer import (
    get_checkpointer,
    reset_checkpointer,
    reset_checkpointer_instance,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.performance]


class TestGetCheckpointer:
    async def test_returns_memory_saver_when_mode_is_memory(self) -> None:
        original = settings.checkpointer_mode
        settings.checkpointer_mode = "memory"
        await reset_checkpointer()
        try:
            cp = await get_checkpointer()
            assert isinstance(cp, MemorySaver)
            # 单例：第二次返回同一实例
            cp2 = await get_checkpointer()
            assert cp2 is cp
        finally:
            settings.checkpointer_mode = original
            await reset_checkpointer()

    async def test_returns_async_sqlite_saver_when_mode_is_sqlite(self, test_db) -> None:
        original = settings.checkpointer_mode
        settings.checkpointer_mode = "sqlite"
        await reset_checkpointer()
        try:
            cp = await get_checkpointer()
            assert isinstance(cp, AsyncSqliteSaver)
            cp2 = await get_checkpointer()
            assert cp2 is cp
        finally:
            settings.checkpointer_mode = original
            await reset_checkpointer()

    async def test_invalid_mode_raises_value_error(self) -> None:
        original = settings.checkpointer_mode
        settings.checkpointer_mode = "invalid"  # type: ignore[assignment]
        await reset_checkpointer()
        try:
            with pytest.raises(ValueError, match="Unsupported checkpointer_mode"):
                await get_checkpointer()
        finally:
            settings.checkpointer_mode = original
            await reset_checkpointer()


class TestResetCheckpointer:
    async def test_reset_clears_singleton(self) -> None:
        settings.checkpointer_mode = "memory"
        await reset_checkpointer()
        cp1 = await get_checkpointer()
        await reset_checkpointer()
        cp2 = await get_checkpointer()
        assert cp1 is not cp2, "reset 后应创建新实例"

    async def test_reset_closes_sqlite_connection(self, test_db) -> None:
        original = settings.checkpointer_mode
        settings.checkpointer_mode = "sqlite"
        await reset_checkpointer()
        try:
            cp = await get_checkpointer()
            await reset_checkpointer()
            # 连接关闭后再操作应失败
            with pytest.raises(Exception):
                await cp.conn.execute("SELECT 1")
        finally:
            settings.checkpointer_mode = original
            await reset_checkpointer()


class TestResetCheckpointerInstance:
    async def test_none_input_is_safe(self) -> None:
        await reset_checkpointer_instance(None)
        # 不应抛出异常

    async def test_memory_saver_cleanup(self) -> None:
        cp = MemorySaver()
        await reset_checkpointer_instance(cp)
        # MemorySaver 没有 conn，直接释放引用即可
