"""Task 191 tests for the V10 Ch200 harness control plane."""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_v10_ch200_climb.py"


def _run_harness(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def _write_inventory(path: Path, source_db: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "task": "190",
                "genres": {
                    "xuanhuan": {
                        "verdict": "REBUILD_REQUIRED",
                        "db_path": ".tmp/task172b_xuanhuan_ch100.db",
                        "project_id": "xuanhuan-p",
                    },
                    "wuxia": {
                        "verdict": "BLOCKED_DIRTY_SAMPLE",
                        "db_path": ".tmp/task172b_wuxia_ch100.db",
                        "project_id": "wuxia-p",
                    },
                    "urban": {
                        "verdict": "CONTINUE_READY",
                        "db_path": source_db.as_posix(),
                        "project_id": "urban-p",
                        "run_id": "run-urban-ch100",
                    },
                },
            }
        ),
        encoding="utf-8",
    )


def _init_sqlite(
    path: Path,
    *,
    project_id: str = "urban-p",
    genre_id: str = "urban",
    accepted_count: int = 100,
    content: str = "干净正文",
) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE projects (
            project_id TEXT PRIMARY KEY,
            genre_id TEXT NOT NULL
        );
        CREATE TABLE chapter_versions (
            version_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            chapter_number INTEGER NOT NULL,
            content TEXT NOT NULL
        );
        CREATE TABLE chapter_heads (
            project_id TEXT NOT NULL,
            chapter_number INTEGER NOT NULL,
            current_version_id TEXT,
            accepted_version_id TEXT,
            status TEXT DEFAULT 'draft',
            PRIMARY KEY(project_id, chapter_number)
        );
        CREATE TABLE project_runs (
            run_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            chapter_range_start INTEGER NOT NULL,
            chapter_range_end INTEGER NOT NULL,
            current_chapter INTEGER DEFAULT 0,
            completed_chapters TEXT DEFAULT '[]',
            failed_chapters TEXT DEFAULT '[]',
            accumulated_summary TEXT DEFAULT '',
            total_cost REAL DEFAULT 0.0,
            status TEXT DEFAULT 'running',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
        """
    )
    conn.execute("INSERT INTO projects(project_id, genre_id) VALUES (?, ?)", (project_id, genre_id))
    conn.executemany(
        "INSERT INTO chapter_versions VALUES (?, ?, ?, ?)",
        [
            (f"v{chapter}", project_id, chapter, content)
            for chapter in range(1, accepted_count + 1)
        ],
    )
    conn.executemany(
        "INSERT INTO chapter_heads VALUES (?, ?, ?, ?, ?)",
        [
            (project_id, chapter, f"v{chapter}", f"v{chapter}", "accepted")
            for chapter in range(1, accepted_count + 1)
        ],
    )
    conn.commit()
    conn.close()


def _json_stdout(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_init_from_source_dry_run_applies_task190_verdict_gate(tmp_path: Path) -> None:
    source_db = tmp_path / "urban_ch100.db"
    _init_sqlite(source_db)
    inventory = tmp_path / "inventory.json"
    _write_inventory(inventory, source_db)

    urban = _json_stdout(
        _run_harness(
            "--init-from-source",
            "--genre",
            "urban",
            "--inventory",
            inventory.as_posix(),
            "--work-dir",
            tmp_path.as_posix(),
            "--dry-run",
            "--format",
            "json",
        )
    )
    assert urban["allowed"] is True
    assert urban["source"]["verdict"] == "CONTINUE_READY"
    assert urban["target"]["db"].endswith("task_v10_urban_ch200.db")

    wuxia = _json_stdout(
        _run_harness(
            "--init-from-source",
            "--genre",
            "wuxia",
            "--inventory",
            inventory.as_posix(),
            "--work-dir",
            tmp_path.as_posix(),
            "--dry-run",
            "--format",
            "json",
        )
    )
    assert wuxia["allowed"] is False
    assert "BLOCKED_DIRTY_SAMPLE" in wuxia["blocker"]

    xuanhuan = _json_stdout(
        _run_harness(
            "--init-from-source",
            "--genre",
            "xuanhuan",
            "--inventory",
            inventory.as_posix(),
            "--work-dir",
            tmp_path.as_posix(),
            "--dry-run",
            "--format",
            "json",
        )
    )
    assert xuanhuan["allowed"] is False
    assert "REBUILD_REQUIRED" in xuanhuan["blocker"]


def test_init_dry_run_prepares_path_contract_without_source_gate(tmp_path: Path) -> None:
    payload = _json_stdout(
        _run_harness(
            "--init",
            "--genre",
            "urban",
            "--inventory",
            (tmp_path / "missing_inventory.json").as_posix(),
            "--work-dir",
            tmp_path.as_posix(),
            "--dry-run",
            "--format",
            "json",
        )
    )

    assert payload["allowed"] is True
    assert payload["action"] == "init"
    assert payload["target"]["db"].endswith("task_v10_urban_ch200.db")
    assert payload["next_step"] == "use --init-from-source with a CONTINUE_READY source"


def test_init_from_source_copies_db_and_writes_v10_metadata(tmp_path: Path) -> None:
    source_db = tmp_path / "urban_ch100.db"
    _init_sqlite(source_db)
    inventory = tmp_path / "inventory.json"
    _write_inventory(inventory, source_db)

    payload = _json_stdout(
        _run_harness(
            "--init-from-source",
            "--genre",
            "urban",
            "--inventory",
            inventory.as_posix(),
            "--work-dir",
            tmp_path.as_posix(),
            "--format",
            "json",
        )
    )

    target_db = Path(payload["target"]["db"])
    project_file = Path(payload["target"]["project_file"])
    segment_log = Path(payload["target"]["segment_log"])
    assert target_db.exists()
    assert project_file.exists()
    assert segment_log.exists()
    project = json.loads(project_file.read_text(encoding="utf-8"))
    assert project["project_id"] == "urban-p"
    assert project["run_id"].startswith("run-v10-urban-")
    assert project["source_verdict"] == "CONTINUE_READY"
    conn = sqlite3.connect(target_db)
    run_row = conn.execute(
        "SELECT project_id, chapter_range_start, chapter_range_end, current_chapter, status "
        "FROM project_runs WHERE run_id = ?",
        (project["run_id"],),
    ).fetchone()
    conn.close()
    assert run_row == ("urban-p", 1, 200, 101, "running")
    assert json.loads(segment_log.read_text(encoding="utf-8").strip())["event"] == (
        "init_from_source"
    )


def test_init_from_source_rejects_non_ch100_source_db(tmp_path: Path) -> None:
    bad_source = tmp_path / "urban_bad_source.db"
    _init_sqlite(bad_source, accepted_count=99)
    inventory = tmp_path / "inventory.json"
    _write_inventory(inventory, bad_source)

    payload = _json_stdout(
        _run_harness(
            "--init-from-source",
            "--genre",
            "urban",
            "--inventory",
            inventory.as_posix(),
            "--work-dir",
            tmp_path.as_posix(),
            "--dry-run",
            "--format",
            "json",
        )
    )

    assert payload["allowed"] is False
    assert "not a clean Ch100 accepted source" in payload["blocker"]


def test_init_from_source_rejects_source_override_not_matching_inventory(
    tmp_path: Path,
) -> None:
    expected_source = tmp_path / "urban_expected.db"
    override_source = tmp_path / "urban_override.db"
    _init_sqlite(expected_source)
    _init_sqlite(override_source)
    inventory = tmp_path / "inventory.json"
    _write_inventory(inventory, expected_source)

    payload = _json_stdout(
        _run_harness(
            "--init-from-source",
            "--genre",
            "urban",
            "--source-db",
            override_source.as_posix(),
            "--inventory",
            inventory.as_posix(),
            "--work-dir",
            tmp_path.as_posix(),
            "--dry-run",
            "--format",
            "json",
        )
    )

    assert payload["allowed"] is False
    assert "does not match Task 190 inventory" in payload["blocker"]


def test_init_from_source_rejects_genre_mismatch(tmp_path: Path) -> None:
    source_db = tmp_path / "urban_wrong_genre.db"
    _init_sqlite(source_db, genre_id="wuxia")
    inventory = tmp_path / "inventory.json"
    _write_inventory(inventory, source_db)

    payload = _json_stdout(
        _run_harness(
            "--init-from-source",
            "--genre",
            "urban",
            "--inventory",
            inventory.as_posix(),
            "--work-dir",
            tmp_path.as_posix(),
            "--dry-run",
            "--format",
            "json",
        )
    )

    assert payload["allowed"] is False
    assert "source genre mismatch" in payload["blocker"]


def test_init_from_source_rejects_t9_dirty_source(tmp_path: Path) -> None:
    source_db = tmp_path / "urban_dirty.db"
    _init_sqlite(source_db, content="\n\n……\n\n")
    inventory = tmp_path / "inventory.json"
    _write_inventory(inventory, source_db)

    payload = _json_stdout(
        _run_harness(
            "--init-from-source",
            "--genre",
            "urban",
            "--inventory",
            inventory.as_posix(),
            "--work-dir",
            tmp_path.as_posix(),
            "--dry-run",
            "--format",
            "json",
        )
    )

    assert payload["allowed"] is False
    assert "not T9 clean" in payload["blocker"]


def test_audit_dry_run_pins_task189_ch200_baseline(tmp_path: Path) -> None:
    project_file = tmp_path / "task_v10_urban_project.json"
    project_file.write_text(
        json.dumps(
            {
                "project_id": "urban-p",
                "run_id": "run-v10-urban-test",
                "db": (tmp_path / "task_v10_urban_ch200.db").as_posix(),
            }
        ),
        encoding="utf-8",
    )

    payload = _json_stdout(
        _run_harness(
            "--audit",
            "--genre",
            "urban",
            "--up-to",
            "150",
            "--baseline",
            "tasks/189-scifi-ch200-baseline.json",
            "--work-dir",
            tmp_path.as_posix(),
            "--dry-run",
            "--format",
            "json",
        )
    )

    five_gate = payload["commands"]["five_gate"]
    assert "--baseline" in five_gate
    assert "tasks/189-scifi-ch200-baseline.json" in five_gate
    assert "--up-to" in five_gate
    assert "150" in five_gate
    assert payload["environment"]["DATABASE_URL"].endswith("task_v10_urban_ch200.db")


def test_missing_tmp_inventory_reports_canonical_source_and_next_step(
    tmp_path: Path,
) -> None:
    canonical = tmp_path / "minimal_done.md"
    canonical.write_text(
        "| 体裁 | 判定 | 说明 |\n"
        "|------|------|------|\n"
        "| urban | **CONTINUE_READY** | summary only |\n",
        encoding="utf-8",
    )
    payload = _json_stdout(
        _run_harness(
            "--init-from-source",
            "--genre",
            "urban",
            "--inventory",
            (tmp_path / "missing_inventory.json").as_posix(),
            "--canonical-inventory",
            canonical.as_posix(),
            "--work-dir",
            tmp_path.as_posix(),
            "--dry-run",
            "--format",
            "json",
        )
    )

    assert payload["allowed"] is False
    assert payload["inventory"]["work_copy_available"] is False
    assert "minimal_done.md" in payload["inventory"]["source"]
    assert "pass --source-db" in payload["next_step"]


def test_audit_requires_project_id_for_real_run(tmp_path: Path) -> None:
    result = _run_harness(
        "--audit",
        "--genre",
        "urban",
        "--up-to",
        "150",
        "--work-dir",
        tmp_path.as_posix(),
        "--format",
        "json",
    )

    assert result.returncode == 2
    assert "missing project_id" in result.stderr
