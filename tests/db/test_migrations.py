"""Tests for schema migrations — idempotency and verification."""

from __future__ import annotations

from pathlib import Path

import pytest

from songyan.db.migrations import get_schema_version, init_schema, run_migrations, verify_schema


@pytest.mark.asyncio
async def test_init_schema_idempotent(tmp_path: Path) -> None:
    """init_schema 应幂等：重复执行不报错."""
    db_path = tmp_path / "test_migrations.db"

    # 第一次初始化
    await init_schema(str(db_path))
    assert db_path.exists()

    # 第二次初始化（不应抛出异常）
    await init_schema(str(db_path))


@pytest.mark.asyncio
async def test_verify_schema_detects_missing_tables(tmp_path: Path) -> None:
    """verify_schema 应正确检测缺失的表."""
    import aiosqlite

    db_path = tmp_path / "test_verify.db"
    await init_schema(str(db_path))

    async with aiosqlite.connect(str(db_path)) as conn:
        missing = await verify_schema(conn)
        assert missing == []

        # 删除一个表后再验证
        await conn.execute("DROP TABLE setting_tracking")
        await conn.commit()

        missing = await verify_schema(conn)
        assert "setting_tracking" in missing


@pytest.mark.asyncio
async def test_get_schema_version(tmp_path: Path) -> None:
    """get_schema_version 应返回正确的表数量."""
    import aiosqlite

    db_path = tmp_path / "test_version.db"
    await init_schema(str(db_path))

    async with aiosqlite.connect(str(db_path)) as conn:
        version = await get_schema_version(conn)
        # 所有期望的表都已创建
        from songyan.db.migrations import _EXPECTED_TABLES

        assert version == len(_EXPECTED_TABLES)

        # 删除一个表后版本应减少
        await conn.execute("DROP TABLE inventory_tracker")
        await conn.commit()

        version = await get_schema_version(conn)
        assert version == len(_EXPECTED_TABLES) - 1


@pytest.mark.asyncio
async def test_run_migrations_creates_profile_history_table(tmp_path: Path) -> None:
    """run_migrations 应补齐 profile history 表."""
    import aiosqlite

    db_path = tmp_path / "test_profile_history_migration.db"
    await init_schema(str(db_path))

    async with aiosqlite.connect(str(db_path)) as conn:
        await conn.execute("DROP TABLE genre_runtime_profile_history")
        await conn.commit()
        missing = await verify_schema(conn)
        assert "genre_runtime_profile_history" in missing

        await run_migrations(conn)
        await conn.commit()

        assert await verify_schema(conn) == []
