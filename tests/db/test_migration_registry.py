"""Task 240: 迁移注册表一致性测试.

钉死单一事实源：``_MIGRATIONS`` 是 init_schema / run_migrations 共用的有序
注册表；两入口遍历同一注册表，注册表内无重复项（回归钉住 run_migrations 曾
重复调用 _migrate_chapter_versions_score_card 的缺陷）。
"""

from __future__ import annotations

from pathlib import Path

import aiosqlite
import pytest

import songyan.db.migrations as migrations_mod
from songyan.db.migrations import init_schema, run_migrations, verify_schema


def test_registry_exists_and_names_unique() -> None:
    """注册表存在、非空、无重复名称."""
    registry = migrations_mod._MIGRATIONS
    assert len(registry) > 0
    names = [name for name, _fn in registry]
    assert len(names) == len(set(names)), f"注册表存在重复迁移: {names}"


def test_registry_entries_callable_and_named() -> None:
    """每项为 (名称, 可调用)，名称与函数名一致."""
    for name, fn in migrations_mod._MIGRATIONS:
        assert isinstance(name, str) and name.startswith("_migrate_")
        assert callable(fn)
        assert fn.__name__ == name


@pytest.mark.asyncio
async def test_init_schema_traverses_registry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """init_schema 在 executescript 之后按注册表顺序逐项执行."""
    calls: list[str] = []

    def _make_stub(name: str):
        async def _stub(conn: aiosqlite.Connection) -> None:
            calls.append(name)

        return _stub

    stub_registry = [
        ("_migrate_stub_a", _make_stub("_migrate_stub_a")),
        ("_migrate_stub_b", _make_stub("_migrate_stub_b")),
        ("_migrate_stub_c", _make_stub("_migrate_stub_c")),
    ]
    monkeypatch.setattr(migrations_mod, "_MIGRATIONS", stub_registry)

    db_path = tmp_path / "stubbed_init.db"
    await init_schema(str(db_path))

    assert calls == ["_migrate_stub_a", "_migrate_stub_b", "_migrate_stub_c"]


@pytest.mark.asyncio
async def test_run_migrations_traverses_same_registry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """run_migrations 与 init_schema 遍历同一注册表（顺序一致）."""
    calls: list[str] = []

    def _make_stub(name: str):
        async def _stub(conn: aiosqlite.Connection) -> None:
            calls.append(name)

        return _stub

    stub_registry = [
        ("_migrate_stub_a", _make_stub("_migrate_stub_a")),
        ("_migrate_stub_b", _make_stub("_migrate_stub_b")),
    ]
    monkeypatch.setattr(migrations_mod, "_MIGRATIONS", stub_registry)

    db_path = tmp_path / "stubbed_run.db"
    await init_schema(str(db_path))
    calls.clear()

    async with aiosqlite.connect(str(db_path)) as conn:
        await run_migrations(conn)

    assert calls == ["_migrate_stub_a", "_migrate_stub_b"]


@pytest.mark.asyncio
async def test_init_schema_fresh_db_verify_clean(tmp_path: Path) -> None:
    """全新库 init_schema 后 verify_schema 无缺失."""
    db_path = tmp_path / "fresh.db"
    await init_schema(str(db_path))
    async with aiosqlite.connect(str(db_path)) as conn:
        assert await verify_schema(conn) == []


@pytest.mark.asyncio
async def test_init_schema_idempotent_double_run(tmp_path: Path) -> None:
    """注册表路径下 init_schema 重跑不报错且表集不变."""
    db_path = tmp_path / "idem.db"
    await init_schema(str(db_path))
    async with aiosqlite.connect(str(db_path)) as conn:
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables_before = [row[0] for row in await cursor.fetchall()]

    await init_schema(str(db_path))
    async with aiosqlite.connect(str(db_path)) as conn:
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables_after = [row[0] for row in await cursor.fetchall()]

    assert tables_before == tables_after


@pytest.mark.asyncio
async def test_run_migrations_backfills_dropped_table(tmp_path: Path) -> None:
    """旧库缺表时 run_migrations 补齐（以最新加入的 import_replay_marks 为例）."""
    db_path = tmp_path / "old.db"
    await init_schema(str(db_path))
    async with aiosqlite.connect(str(db_path)) as conn:
        await conn.execute("DROP TABLE import_replay_marks")
        await conn.commit()
        assert "import_replay_marks" in await verify_schema(conn)

        await run_migrations(conn)
        await conn.commit()
        assert await verify_schema(conn) == []
