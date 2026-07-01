"""Extract final metrics for Task 139d V5.2 acceptance package.

Run after Ch83-Ch150 continuation and Ch80 rerun complete.
"""

from __future__ import annotations

import json
import sqlite3
import sys


def _safe_json_loads(value: str | None) -> list | dict | None:
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def main(db_path: str, project_id: str, run_id: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Chapter statuses
    rows = conn.execute(
        """
        SELECT h.chapter_number, h.status, h.accepted_version_id, v.word_count
        FROM chapter_heads h
        LEFT JOIN chapter_versions v ON v.version_id = h.current_version_id
        WHERE h.project_id = ?
        ORDER BY h.chapter_number
        """,
        (project_id,),
    ).fetchall()

    accepted = [r["chapter_number"] for r in rows if r["status"] == "accepted"]
    not_accepted = [
        {"chapter": r["chapter_number"], "status": r["status"], "word_count": r["word_count"]}
        for r in rows
        if r["status"] != "accepted"
    ]

    # Run summary
    run = conn.execute(
        "SELECT * FROM project_runs WHERE run_id = ?", (run_id,)
    ).fetchone()

    # Latest continuity report
    cont = conn.execute(
        """
        SELECT *
        FROM continuity_reports
        WHERE project_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (project_id,),
    ).fetchone()

    continuity_report = None
    if cont:
        continuity_report = {
            "checked_up_to_chapter": cont["checked_up_to_chapter"],
            "overall_health_score": cont["overall_health_score"],
            "orphaned_settings": _safe_json_loads(cont["orphaned_settings"]),
            "forgotten_items": _safe_json_loads(cont["forgotten_items"]),
            "state_mismatches": _safe_json_loads(cont["state_mismatches"]),
            "overdue_foreshadowings": _safe_json_loads(cont["overdue_foreshadowings"]),
            "suggested_marks": _safe_json_loads(cont["suggested_marks"]),
        }

    result = {
        "project_id": project_id,
        "run_id": run_id,
        "total_chapters": len(rows),
        "accepted_count": len(accepted),
        "not_accepted": not_accepted,
        "failed_chapters": json.loads(run["failed_chapters"]) if run else [],
        "run_status": run["status"] if run else None,
        "continuity_report": continuity_report,
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python scripts/extract_139d_final_metrics.py <db_path> <project_id> <run_id>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2], sys.argv[3])
