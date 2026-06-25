"""Full cleanup of all test residues before a clean full rerun."""
from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path("songyan.db")

LOG_PATTERNS = [
    "logs/chapter_runs/*.jsonl",
    "logs/task121g/*.log",
    "logs/task121g/*.txt",
    "logs/task121q/*.log",
    "logs/task121q/*.txt",
    "logs/task121q/*.marker",
    "logs/task121q/.last_*",
    "logs/*.log",
]

KEEP_LOGS = [
    "logs/app.log",
]

# Tables that may contain test data keyed by project_id
PROJECT_TABLES = [
    "projects", "characters", "chapter_goals", "creative_briefs",
    "chapter_versions", "chapter_heads", "character_states",
    "literary_observations", "review_reports", "foreshadowings",
    "setting_snapshots", "numerical_ledgers", "summaries",
    "human_instructions", "setting_tracking", "inventory_tracker",
    "location_tracker", "continuity_reports", "arc_summaries",
    "volume_summaries", "permanent_scenes", "human_marks",
    "chapter_chunks", "lifecycle_errors", "context_snapshots",
]

# Non-project tables to also clear
RUN_TABLES = ["project_runs", "run_logs"]


def clean_database() -> None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    total_deleted = 0

    for table in PROJECT_TABLES:
        try:
            cursor.execute(f"DELETE FROM {table}")
            if cursor.rowcount and cursor.rowcount > 0:
                total_deleted += cursor.rowcount
                print(f"  Deleted {cursor.rowcount} rows from {table}")
        except Exception as e:
            print(f"  Skipped {table}: {e}")

    for table in RUN_TABLES:
        try:
            cursor.execute(f"DELETE FROM {table}")
            if cursor.rowcount and cursor.rowcount > 0:
                total_deleted += cursor.rowcount
                print(f"  Deleted {cursor.rowcount} rows from {table}")
        except Exception as e:
            print(f"  Skipped {table}: {e}")

    conn.commit()
    conn.close()
    print(f"Database cleanup done. Total rows deleted: {total_deleted}")


def clean_logs() -> None:
    kept = []
    deleted = []

    for pattern in LOG_PATTERNS:
        for path in Path(".").glob(pattern):
            rel = str(path).replace("\\", "/")
            if any(rel.endswith(k.replace("logs/", "")) for k in KEEP_LOGS):
                kept.append(rel)
                continue
            try:
                path.unlink()
                deleted.append(rel)
            except Exception as e:
                print(f"Failed to delete {rel}: {e}")

    print(f"Deleted {len(deleted)} log files")
    if kept:
        print(f"Kept {len(kept)} log files")


def clean_cache() -> None:
    count = 0
    for pyc in Path(".").rglob("*.pyc"):
        try:
            pyc.unlink()
            count += 1
        except Exception:
            pass
    for pycache in Path(".").rglob("__pycache__"):
        try:
            pycache.rmdir()
            count += 1
        except Exception:
            pass
    print(f"Cleaned {count} cache items")


def vacuum_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("VACUUM")
    conn.close()
    size = DB_PATH.stat().st_size
    print(f"Database vacuumed. Size: {size / 1024 / 1024:.2f} MB")


def verify_clean() -> None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM projects")
    print(f"  projects: {cursor.fetchone()[0]}")
    cursor.execute("SELECT COUNT(*) FROM chapter_versions")
    print(f"  chapter_versions: {cursor.fetchone()[0]}")
    cursor.execute("SELECT COUNT(*) FROM chapter_heads")
    print(f"  chapter_heads: {cursor.fetchone()[0]}")
    cursor.execute("SELECT COUNT(*) FROM project_runs")
    print(f"  project_runs: {cursor.fetchone()[0]}")
    conn.close()


def main() -> None:
    print("=== Full Cleanup Start ===")
    clean_database()
    clean_logs()
    clean_cache()
    vacuum_db()
    print("\n=== Verification ===")
    verify_clean()
    print("=== Full Cleanup Complete ===")


if __name__ == "__main__":
    main()
