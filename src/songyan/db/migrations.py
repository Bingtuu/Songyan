"""Schema 初始化与验证 — 幂等执行."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from songyan.db.connection import get_db_path

if TYPE_CHECKING:
    import aiosqlite


# 期望存在的所有表名（用于验证）
_EXPECTED_TABLES: list[str] = [
    "projects",
    "characters",
    "chapter_goals",
    "creative_briefs",
    "chapter_versions",
    "chapter_heads",
    "character_states",
    "literary_observations",
    "review_reports",
    "foreshadowings",
    "setting_snapshots",
    "numerical_ledgers",
    "summaries",
]


async def init_schema(db_path: str | Path | None = None) -> None:
    """读取 schema.sql 并执行，幂等（所有 CREATE 带 IF NOT EXISTS）.

    Args:
        db_path: 数据库文件路径。None 时从 settings 解析。
    """
    if db_path is None:
        db_path = get_db_path()
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # schema.sql 与 migrations.py 同目录
    schema_file = Path(__file__).with_name("schema.sql")
    sql = schema_file.read_text(encoding="utf-8")

    import aiosqlite

    async with aiosqlite.connect(db_path) as conn:
        await conn.executescript(sql)
        await conn.commit()


async def verify_schema(conn: aiosqlite.Connection) -> list[str]:
    """验证所有期望的表是否存在.

    Returns:
        缺失的表名列表。空列表表示全部存在。
    """
    cursor = await conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    )
    rows = await cursor.fetchall()
    existing = {row[0] for row in rows}
    missing = [t for t in _EXPECTED_TABLES if t not in existing]
    return missing


async def get_schema_version(conn: aiosqlite.Connection) -> int:
    """获取当前 schema 版本（通过统计已创建表数）.

    Returns:
        已创建的期望表数量（0-13）
    """
    missing = await verify_schema(conn)
    return len(_EXPECTED_TABLES) - len(missing)
