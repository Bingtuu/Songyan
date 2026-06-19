"""Schema 初始化与验证 — 幂等执行."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

import structlog

from songyan.db.connection import get_db_path

if TYPE_CHECKING:
    import aiosqlite

logger = structlog.get_logger(__name__)


# 期望存在的所有表名（用于验证）
_EXPECTED_TABLES: list[str] = [
    "projects",
    "characters",
    "chapter_goals",
    "creative_briefs",
    "chapter_versions",
    "context_snapshots",
    "chapter_heads",
    "character_states",
    "literary_observations",
    "review_reports",
    "foreshadowings",
    "setting_snapshots",
    "numerical_ledgers",
    "summaries",
    "project_runs",
    # Phase 4 新增表
    "arc_summaries",
    "volume_summaries",
    "permanent_scenes",
    # Continuity tracking & HITL
    "setting_tracking",
    "inventory_tracker",
    "location_tracker",
    "continuity_reports",
    "human_instructions",
    # Phase 7: Human-Augmented Memory
    "human_marks",
    # Phase 8b: RAG 自动层
    "chapter_chunks",
    # V4.0: 数据生命周期管理
    "lifecycle_errors",
]


async def _migrate_continuity_tables(conn: aiosqlite.Connection) -> None:
    """添加连续性追踪表（v2.0.3）."""
    tables = [
        """CREATE TABLE IF NOT EXISTS setting_tracking (
            tracking_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            setting_key TEXT NOT NULL,
            setting_name TEXT,
            description TEXT,
            introduced_in_chapter INTEGER,
            last_mentioned_chapter INTEGER,
            expected_resolve_chapter INTEGER,
            status TEXT DEFAULT 'active',
            recovery_required INTEGER DEFAULT 0,
            source_version_id TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS inventory_tracker (
            track_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            character_id TEXT,
            item_name TEXT NOT NULL,
            item_description TEXT,
            acquired_in_chapter INTEGER,
            last_used_chapter INTEGER,
            status TEXT DEFAULT 'held',
            expected_usage_chapter INTEGER
        )""",
        """CREATE TABLE IF NOT EXISTS location_tracker (
            track_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            character_id TEXT NOT NULL,
            location TEXT NOT NULL,
            entered_in_chapter INTEGER,
            last_confirmed_chapter INTEGER
        )""",
        """CREATE TABLE IF NOT EXISTS continuity_reports (
            report_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            checked_up_to_chapter INTEGER,
            orphaned_settings TEXT DEFAULT '[]',
            forgotten_items TEXT DEFAULT '[]',
            state_mismatches TEXT DEFAULT '[]',
            overdue_foreshadowings TEXT DEFAULT '[]',
            overall_health_score REAL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        )""",
    ]
    for sql in tables:
        await conn.execute(sql)


async def _migrate_human_instructions(conn: aiosqlite.Connection) -> None:
    """添加 human_instructions 表（v2.0.2）."""
    cursor = await conn.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name='human_instructions'"
    )
    if not await cursor.fetchone():
        await conn.execute(
            """CREATE TABLE human_instructions (
                instruction_id  TEXT PRIMARY KEY,
                project_id      TEXT NOT NULL,
                chapter_number  INTEGER NOT NULL,
                gate_type       TEXT NOT NULL,
                action          TEXT NOT NULL,
                target_field    TEXT,
                content         TEXT NOT NULL,
                created_at      TEXT DEFAULT (datetime('now'))
            )"""
        )


async def _migrate_creative_briefs_punch(conn: aiosqlite.Connection) -> None:
    """为 creative_briefs 表添加 punch_points / emotion_arc 列（v2.0.1）."""
    cursor = await conn.execute("PRAGMA table_info(creative_briefs)")
    cols = {row[1] for row in await cursor.fetchall()}
    if "punch_points" not in cols:
        await conn.execute(
            "ALTER TABLE creative_briefs ADD COLUMN punch_points TEXT DEFAULT '[]'"
        )
    if "emotion_arc" not in cols:
        await conn.execute(
            "ALTER TABLE creative_briefs ADD COLUMN emotion_arc TEXT DEFAULT '[]'"
        )


# ---------------------------------------------------------------------------
# Phase 4 迁移
# ---------------------------------------------------------------------------

async def _migrate_summaries_impact_score(conn: aiosqlite.Connection) -> None:
    """为 summaries 表添加 impact_score 列（v2.0.4）."""
    cursor = await conn.execute("PRAGMA table_info(summaries)")
    cols = {row[1] for row in await cursor.fetchall()}
    if "impact_score" not in cols:
        await conn.execute(
            "ALTER TABLE summaries ADD COLUMN impact_score REAL DEFAULT 0"
        )


async def _migrate_project_arc_boundaries(conn: aiosqlite.Connection) -> None:
    """为 projects 表添加 arc_boundaries / volume_boundaries 列（v2.0.4）."""
    cursor = await conn.execute("PRAGMA table_info(projects)")
    cols = {row[1] for row in await cursor.fetchall()}
    if "arc_boundaries" not in cols:
        await conn.execute(
            "ALTER TABLE projects ADD COLUMN arc_boundaries TEXT DEFAULT '[]'"
        )
    if "volume_boundaries" not in cols:
        await conn.execute(
            "ALTER TABLE projects ADD COLUMN volume_boundaries TEXT DEFAULT '[]'"
        )


async def _migrate_layered_context_tables(conn: aiosqlite.Connection) -> None:
    """添加分层上下文表（v2.0.4）—— arc_summaries, volume_summaries, permanent_scenes."""
    tables = [
        """CREATE TABLE IF NOT EXISTS arc_summaries (
            arc_id          TEXT PRIMARY KEY,
            project_id      TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
            start_chapter   INTEGER NOT NULL,
            end_chapter     INTEGER NOT NULL,
            arc_title       TEXT DEFAULT '',
            arc_summary     TEXT DEFAULT '',
            key_events      TEXT DEFAULT '[]',
            resolved_threads TEXT DEFAULT '[]',
            new_threads     TEXT DEFAULT '[]',
            character_arcs  TEXT DEFAULT '{}',
            created_at      TEXT DEFAULT (datetime('now'))
        )""",
        """CREATE TABLE IF NOT EXISTS volume_summaries (
            volume_id       TEXT PRIMARY KEY,
            project_id      TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
            start_chapter   INTEGER NOT NULL,
            end_chapter     INTEGER NOT NULL,
            volume_title    TEXT DEFAULT '',
            volume_summary  TEXT DEFAULT '',
            major_revelations TEXT DEFAULT '[]',
            world_state     TEXT DEFAULT '',
            created_at      TEXT DEFAULT (datetime('now'))
        )""",
        """CREATE TABLE IF NOT EXISTS permanent_scenes (
            scene_id        TEXT PRIMARY KEY,
            project_id      TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
            chapter_number  INTEGER NOT NULL,
            scene_number    INTEGER NOT NULL DEFAULT 1,
            excerpt         TEXT DEFAULT '',
            impact_tags     TEXT DEFAULT '[]',
            referenced_by   TEXT DEFAULT '[]',
            created_at      TEXT DEFAULT (datetime('now'))
        )""",
    ]
    for sql in tables:
        await conn.execute(sql)
    # 创建索引
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_arc_project ON arc_summaries(project_id)",
        "CREATE INDEX IF NOT EXISTS idx_volume_project ON volume_summaries(project_id)",
        "CREATE INDEX IF NOT EXISTS idx_permanent_project ON permanent_scenes(project_id)",
        "CREATE INDEX IF NOT EXISTS idx_permanent_chapter "
        "ON permanent_scenes(project_id, chapter_number)",
    ]
    for sql in indexes:
        await conn.execute(sql)


async def _migrate_continuity_suggested_marks(conn: aiosqlite.Connection) -> None:
    """为 continuity_reports 添加 suggested_marks 列（Phase 7 v2.1.0）."""
    cursor = await conn.execute("PRAGMA table_info(continuity_reports)")
    cols = {row[1] for row in await cursor.fetchall()}
    if "suggested_marks" not in cols:
        await conn.execute(
            "ALTER TABLE continuity_reports ADD COLUMN suggested_marks TEXT DEFAULT '[]'"
        )


async def _migrate_human_marks(conn: aiosqlite.Connection) -> None:
    """添加 human_marks 表（Phase 7 v2.1.0）及 source 列（v2.2.0 Task 054）."""
    await conn.execute(
        """CREATE TABLE IF NOT EXISTS human_marks (
            mark_id             TEXT PRIMARY KEY,
            project_id          TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
            mark_type           TEXT NOT NULL,
            target_key          TEXT NOT NULL,
            note                TEXT DEFAULT '',
            priority            INTEGER DEFAULT 5,
            created_at_chapter  INTEGER,
            resolved_at         TEXT,
            created_at          TEXT DEFAULT (datetime('now')),
            source              TEXT DEFAULT 'human'
        )"""
    )
    await conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_human_marks_project ON human_marks(project_id)"
    )
    await conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_human_marks_project_priority "
        "ON human_marks(project_id, priority)"
    )
    # 为已有表添加 source 列（幂等：忽略已存在错误）
    try:
        await conn.execute(
            "ALTER TABLE human_marks ADD COLUMN source TEXT DEFAULT 'human'"
        )
    except sqlite3.OperationalError:
        pass  # 列已存在或表不存在


async def _migrate_project_seed_config(conn: aiosqlite.Connection) -> None:
    """为 projects 表添加 Phase 8a 种子配置列（v2.1.1）."""
    cursor = await conn.execute("PRAGMA table_info(projects)")
    cols = {row[1] for row in await cursor.fetchall()}
    if "estimated_chapters" not in cols:
        await conn.execute(
            "ALTER TABLE projects ADD COLUMN estimated_chapters INTEGER DEFAULT 30"
        )
    if "words_per_chapter" not in cols:
        await conn.execute(
            "ALTER TABLE projects ADD COLUMN words_per_chapter INTEGER DEFAULT 3000"
        )
    if "story_structure" not in cols:
        await conn.execute(
            "ALTER TABLE projects ADD COLUMN story_structure TEXT DEFAULT 'free'"
        )
    if "sub_genre_id" not in cols:
        await conn.execute(
            "ALTER TABLE projects ADD COLUMN sub_genre_id TEXT"
        )
    if "arc_boundaries_auto" not in cols:
        await conn.execute(
            "ALTER TABLE projects ADD COLUMN arc_boundaries_auto INTEGER DEFAULT 0"
        )


async def _migrate_dialogue_style_card(conn: aiosqlite.Connection) -> None:
    """为 characters 表添加对话风格卡列（Task 074）."""
    cursor = await conn.execute("PRAGMA table_info(characters)")
    cols = {row[1] for row in await cursor.fetchall()}
    if "dialogue_style_card" not in cols:
        await conn.execute(
            "ALTER TABLE characters ADD COLUMN dialogue_style_card TEXT DEFAULT '{}'"
        )


async def _migrate_chapter_chunks(conn: aiosqlite.Connection) -> None:
    """添加 chapter_chunks 表（Phase 8b v2.1.2）."""
    await conn.execute(
        """CREATE TABLE IF NOT EXISTS chapter_chunks (
            chunk_id        TEXT PRIMARY KEY,
            project_id      TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
            chapter_number  INTEGER NOT NULL,
            version_id      TEXT NOT NULL REFERENCES chapter_versions(version_id) ON DELETE CASCADE,
            chunk_index     INTEGER NOT NULL,
            text            TEXT NOT NULL,
            metadata_json   TEXT DEFAULT '{}',
            embedding_blob  BLOB,
            created_at      TEXT DEFAULT (datetime('now'))
        )"""
    )
    await conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_chunks_project "
        "ON chapter_chunks(project_id, chapter_number)"
    )


# ---------------------------------------------------------------------------
# V4.0 迁移 — 数据生命周期管理
# ---------------------------------------------------------------------------

async def _migrate_lifecycle_status(conn: aiosqlite.Connection) -> None:
    """为 5 张元数据表添加 lifecycle_status 字段（V4.0 Task 083）."""
    tables = [
        ("setting_snapshots", "idx_settings_lifecycle"),
        ("human_marks", "idx_human_marks_lifecycle"),
        ("character_states", "idx_states_lifecycle"),
        ("chapter_chunks", "idx_chunks_lifecycle"),
    ]
    for table, index_name in tables:
        cursor = await conn.execute(f"PRAGMA table_info({table})")
        cols = {row[1] for row in await cursor.fetchall()}
        if "lifecycle_status" not in cols:
            await conn.execute(
                f"ALTER TABLE {table} ADD COLUMN lifecycle_status TEXT DEFAULT 'active'"
            )
        cols = (
            "project_id, lifecycle_status"
            if table != "character_states"
            else "lifecycle_status"
        )
        await conn.execute(
            f"CREATE INDEX IF NOT EXISTS {index_name} ON {table}({cols})"
        )

    # foreshadowings 表已有 status 字段，需添加 lifecycle_status
    cursor = await conn.execute("PRAGMA table_info(foreshadowings)")
    cols = {row[1] for row in await cursor.fetchall()}
    if "lifecycle_status" not in cols:
        await conn.execute(
            "ALTER TABLE foreshadowings ADD COLUMN lifecycle_status TEXT DEFAULT 'active'"
        )
    await conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_foreshadowings_lifecycle "
        "ON foreshadowings(project_id, lifecycle_status)"
    )

    # lifecycle_errors 日志表
    await conn.execute(
        """CREATE TABLE IF NOT EXISTS lifecycle_errors (
            error_id        TEXT PRIMARY KEY,
            project_id      TEXT NOT NULL,
            table_name      TEXT NOT NULL,
            entity_id       TEXT,
            operation       TEXT NOT NULL,
            error_message   TEXT NOT NULL,
            created_at      TEXT DEFAULT (datetime('now'))
        )"""
    )
    await conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_lifecycle_errors_project ON lifecycle_errors(project_id)"
    )


async def _migrate_setting_category(conn: aiosqlite.Connection) -> None:
    """Task 094: 为 setting_tracking 表添加 category 列，并回填现有数据."""
    cursor = await conn.execute("PRAGMA table_info(setting_tracking)")
    cols = {row[1] for row in await cursor.fetchall()}
    if "category" not in cols:
        await conn.execute(
            "ALTER TABLE setting_tracking ADD COLUMN category TEXT DEFAULT 'background'"
        )
    # 回填现有数据（默认 background）
    await conn.execute(
        "UPDATE setting_tracking SET category = 'background' WHERE category IS NULL"
    )



async def _migrate_chapter_versions_score_card(conn: aiosqlite.Connection) -> None:
    """为 chapter_versions 表添加 score_card 列（Task 106 评分体系）."""
    cursor = await conn.execute(
        "SELECT name FROM pragma_table_info('chapter_versions')"
    )
    cols = {row[0] for row in await cursor.fetchall()}
    if "score_card" not in cols:
        await conn.execute(
            "ALTER TABLE chapter_versions ADD COLUMN score_card TEXT DEFAULT '{}'"
        )


async def _migrate_context_snapshots(conn: aiosqlite.Connection) -> None:
    """添加裁剪后上下文快照表（Task 111f）."""
    await conn.execute(
        """CREATE TABLE IF NOT EXISTS context_snapshots (
            snapshot_id        TEXT PRIMARY KEY,
            project_id         TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
            chapter_number     INTEGER NOT NULL,
            chapter_goal_id    TEXT,
            creative_brief_id  TEXT REFERENCES creative_briefs(brief_id) ON DELETE SET NULL,
            budget_used        REAL,
            context_emergency  INTEGER DEFAULT 0,
            payload            TEXT DEFAULT '{}',
            created_at         TEXT DEFAULT (datetime('now'))
        )"""
    )
    await conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_context_snapshots_project_chapter "
        "ON context_snapshots(project_id, chapter_number)"
    )


async def _migrate_setting_setting_key_index(conn: aiosqlite.Connection) -> None:
    """PERF-04: 为 setting_snapshots 添加 (project_id, setting_key) 索引.

    加速 ContextManager context 组装时的 setting 查找，避免全表扫描。
    已有记录: Ch50 ~80 条, Ch70 ~129 条, Ch100 ~180+ 条.
    """
    await conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_setting_snapshots_project_key "
        "ON setting_snapshots(project_id, setting_key)"
    )
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
        # Task 100a: 为旧表添加缺失列（必须在 executescript 之后，否则新数据库表不存在）
        await _migrate_lifecycle_status(conn)
        await _migrate_setting_category(conn)
        await _migrate_creative_briefs_punch(conn)
        await _migrate_human_instructions(conn)
        await _migrate_continuity_tables(conn)
        # Phase 4 迁移
        await _migrate_summaries_impact_score(conn)
        await _migrate_project_arc_boundaries(conn)
        await _migrate_layered_context_tables(conn)
        await _migrate_continuity_suggested_marks(conn)
        await _migrate_human_marks(conn)
        await _migrate_project_seed_config(conn)
        await _migrate_chapter_chunks(conn)
        await _migrate_dialogue_style_card(conn)
        await _migrate_chapter_versions_score_card(conn)
        await _migrate_context_snapshots(conn)
        await _migrate_setting_setting_key_index(conn)
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
        已创建的期望表数量
    """
    missing = await verify_schema(conn)
    return len(_EXPECTED_TABLES) - len(missing)

async def run_migrations(conn: aiosqlite.Connection) -> None:
    """按创建顺序执行所有待执行的数据库迁移."""
    await _migrate_continuity_tables(conn)
    await _migrate_human_instructions(conn)
    await _migrate_creative_briefs_punch(conn)
    await _migrate_summaries_impact_score(conn)
    await _migrate_project_arc_boundaries(conn)
    await _migrate_chapter_versions_score_card(conn)
    await _migrate_context_snapshots(conn)
    await _migrate_layered_context_tables(conn)
    await _migrate_continuity_suggested_marks(conn)
    await _migrate_human_marks(conn)
    await _migrate_project_seed_config(conn)
    await _migrate_dialogue_style_card(conn)
    await _migrate_chapter_chunks(conn)
    await _migrate_lifecycle_status(conn)
    await _migrate_setting_category(conn)
    await _migrate_chapter_versions_score_card(conn)
    await _migrate_setting_setting_key_index(conn)
    logger.info("migrations.run_all", status="complete")
