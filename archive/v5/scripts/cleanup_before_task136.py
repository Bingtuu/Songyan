"""Cleanup test residues before Task 136, preserving source evidence projects."""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

DB_PATH = Path("songyan.db")
KEEP_PROJECT_IDS = [
    "3cf71586df2a4b5c9170d9b1a5f059cf",  # Task 129 run-89d7a2d4 source
    "e95a1fa3",  # Task 121q run-a2bed648 source (if present)
]
KEEP_LOG_NAMES = {"run-89d7a2d4.jsonl", "run-a2bed648.jsonl"}

# Tables that have a project_id column and can be filtered directly.
PROJECT_TABLES = [
    "projects",
    "characters",
    "chapter_goals",
    "creative_briefs",
    "chapter_versions",
    "chapter_heads",
    "foreshadowings",
    "setting_snapshots",
    "summaries",
    "human_instructions",
    "setting_tracking",
    "inventory_tracker",
    "location_tracker",
    "continuity_reports",
    "arc_summaries",
    "volume_summaries",
    "permanent_scenes",
    "human_marks",
    "chapter_chunks",
    "lifecycle_errors",
    "context_snapshots",
]

# Tables that do not have project_id and must be filtered via linked ids.
LINKED_TABLES = {
    "character_states": ("character_id", "characters", "character_id"),
    "literary_observations": ("version_id", "chapter_versions", "version_id"),
    "review_reports": ("version_id", "chapter_versions", "version_id"),
}

# Run-level metadata tables.
RUN_TABLES = ["project_runs", "writes", "checkpoints"]


def _placeholders(n: int) -> str:
    return ",".join("?" * n)


def clean_database() -> None:
    """删除非保留项目的业务数据与运行元数据."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    keep_ph = _placeholders(len(KEEP_PROJECT_IDS))

    # 直接按 project_id 过滤的表
    for table in PROJECT_TABLES:
        try:
            c.execute(f"DELETE FROM {table} WHERE project_id NOT IN ({keep_ph})", KEEP_PROJECT_IDS)
            if c.rowcount:
                print(f"  Deleted {c.rowcount} rows from {table}")
        except Exception as exc:  # pragma: no cover
            print(f"  Skipped {table}: {exc}")

    # 通过外键关联过滤的表
    for table, (fk, parent, parent_pk) in LINKED_TABLES.items():
        try:
            if parent == "characters":
                c.execute(
                    f"SELECT {parent_pk} FROM {parent} WHERE project_id IN ({keep_ph})",
                    KEEP_PROJECT_IDS,
                )
            else:
                c.execute(
                    f"SELECT {parent_pk} FROM {parent} WHERE project_id IN ({keep_ph})",
                    KEEP_PROJECT_IDS,
                )
            keep_ids = {row[0] for row in c.fetchall()}
            if keep_ids:
                id_ph = _placeholders(len(keep_ids))
                c.execute(
                    f"DELETE FROM {table} WHERE {fk} NOT IN ({id_ph})",
                    list(keep_ids),
                )
                if c.rowcount:
                    print(f"  Deleted {c.rowcount} rows from {table}")
        except Exception as exc:  # pragma: no cover
            print(f"  Skipped {table}: {exc}")

    # 运行元数据：保留 Keeper 项目的 project_runs，其余清空
    for table in RUN_TABLES:
        try:
            c.execute(f"PRAGMA table_info({table})")
            cols = {row[1] for row in c.fetchall()}
            if "project_id" in cols:
                c.execute(
                    f"DELETE FROM {table} WHERE project_id NOT IN ({keep_ph})",
                    KEEP_PROJECT_IDS,
                )
            else:
                c.execute(f"DELETE FROM {table}")
            if c.rowcount:
                print(f"  Deleted {c.rowcount} rows from {table}")
        except Exception as exc:  # pragma: no cover
            print(f"  Skipped {table}: {exc}")

    conn.commit()
    conn.close()


def clean_logs() -> None:
    """清理 chapter_runs 日志与根日志，保留关键证据日志."""
    deleted = 0
    kept = 0
    log_root = Path("logs")
    for path in (log_root / "chapter_runs").glob("*.jsonl"):
        if path.name in KEEP_LOG_NAMES:
            kept += 1
            continue
        path.unlink()
        deleted += 1

    for path in log_root.glob("*.log"):
        if path.name == "app.log":
            kept += 1
            continue
        path.unlink()
        deleted += 1

    print(f"  Deleted {deleted} log files, kept {kept}")


def clean_eval_outputs() -> None:
    """清理 evals/output 测试产物."""
    output_dir = Path("evals/output")
    if not output_dir.exists():
        return
    deleted = 0
    for path in output_dir.iterdir():
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
            deleted += 1
        elif path.is_file():
            path.unlink()
            deleted += 1
    print(f"  Deleted {deleted} evals/output entries")


def clean_caches() -> None:
    """清理 pytest / ruff / python 缓存."""
    removed = 0
    for path in Path(".").rglob("__pycache__"):
        shutil.rmtree(path, ignore_errors=True)
        removed += 1
    for path in Path(".").rglob("*.pyc"):
        path.unlink(missing_ok=True)
        removed += 1
    for name in (".pytest_cache", ".ruff_cache"):
        p = Path(name)
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)
            removed += 1
    print(f"  Cleaned {removed} cache items")


def vacuum_db() -> None:
    """VACUUM 数据库并打印大小."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("VACUUM")
    conn.close()
    size_mb = DB_PATH.stat().st_size / 1024 / 1024
    print(f"  Database vacuumed: {size_mb:.2f} MB")


def verify_clean() -> None:
    """打印清理后关键表数量."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    print("\n  Verification:")
    for table in ("projects", "chapter_versions", "continuity_reports", "project_runs"):
        try:
            c.execute(f"SELECT COUNT(*) FROM {table}")
            print(f"    {table}: {c.fetchone()[0]}")
        except Exception as exc:  # pragma: no cover
            print(f"    {table}: error {exc}")
    conn.close()


def main() -> None:
    print("=== Cleanup before Task 136 ===")
    print("Database:")
    clean_database()
    print("Logs:")
    clean_logs()
    print("Eval outputs:")
    clean_eval_outputs()
    print("Caches:")
    clean_caches()
    vacuum_db()
    verify_clean()
    print("=== Cleanup complete ===")


if __name__ == "__main__":
    main()
