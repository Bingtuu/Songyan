"""Task 182 tests for formal five-gate and segment-audit tools."""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from songyan.evals.five_gate_acceptance import (
    BaselinePoint,
    FiveGateToolError,
    baseline_at,
    collect_metrics,
    evaluate_project,
    load_baseline,
)
from songyan.evals.segment_audit import collect_segment_audit

ROOT = Path(__file__).resolve().parents[1]


def _issue(
    category: str,
    *,
    severity: str = "major",
    evidence: str = "证据",
    issue_id: str = "issue-1",
) -> dict[str, str]:
    return {
        "category": category,
        "severity": severity,
        "evidence_quote": evidence,
        "issue_id": issue_id,
    }


def _init_metric_db(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE chapter_heads (
            project_id TEXT,
            chapter_number INTEGER,
            accepted_version_id TEXT,
            status TEXT
        );
        CREATE TABLE chapter_versions (
            version_id TEXT,
            project_id TEXT,
            chapter_number INTEGER,
            content TEXT,
            parent_version_id TEXT
        );
        CREATE TABLE review_reports (
            chapter_version_id TEXT,
            audit_type TEXT,
            issues TEXT
        );
        CREATE TABLE context_snapshots (
            project_id TEXT,
            chapter_number INTEGER,
            budget_used REAL
        );
        CREATE TABLE foreshadowings (
            project_id TEXT,
            expected_resolve_chapter INTEGER,
            status TEXT
        );
        CREATE TABLE continuity_reports (
            project_id TEXT,
            checked_up_to_chapter INTEGER,
            overall_health_score REAL
        );
        """
    )
    conn.close()


def _seed_metric_rows(db_path: Path, *, project_id: str = "p1") -> None:
    conn = sqlite3.connect(db_path)
    text = "甲" * 1000
    conn.executemany(
        "INSERT INTO chapter_heads VALUES (?, ?, ?, ?)",
        [
            (project_id, 1, "v1-accepted", "accepted"),
            (project_id, 2, "v2-accepted", "accepted"),
        ],
    )
    conn.executemany(
        "INSERT INTO chapter_versions VALUES (?, ?, ?, ?, ?)",
        [
            ("v1-source", project_id, 1, text, None),
            ("v1-accepted", project_id, 1, text, "v1-source"),
            ("v2-accepted", project_id, 2, text, None),
        ],
    )
    conn.executemany(
        "INSERT INTO review_reports VALUES (?, ?, ?)",
        [
            (
                "v1-source",
                "llm",
                json.dumps([_issue("world_consistency"), _issue("show_dont_tell")]),
            ),
            (
                "v1-source",
                "merged",
                json.dumps(
                    [
                        _issue("world_consistency"),
                        _issue("character_behavior"),
                        _issue("show_dont_tell"),
                    ]
                ),
            ),
            ("v2-accepted", "rule", json.dumps([_issue("setting_conflict")])),
            (
                "v2-accepted",
                "llm",
                json.dumps(
                    [
                        _issue("dialogue_distinctness"),
                        _issue("world_consistency", issue_id="rule-mr-v2"),
                        _issue("world_consistency", evidence=""),
                    ]
                ),
            ),
        ],
    )
    conn.executemany(
        "INSERT INTO context_snapshots VALUES (?, ?, ?)",
        [(project_id, 1, 0.75), (project_id, 2, 0.9)],
    )
    conn.executemany(
        "INSERT INTO foreshadowings VALUES (?, ?, ?)",
        [(project_id, 1, "planted"), (project_id, 3, "planted"), (project_id, 1, "resolved")],
    )
    conn.execute("INSERT INTO continuity_reports VALUES (?, ?, ?)", (project_id, 2, 8.5))
    conn.commit()
    conn.close()


def _write_baseline(path: Path, *, ced: float = 3.0, overdue: int = 2) -> None:
    path.write_text(
        json.dumps(
            {
                "points": [
                    {
                        "up_to": 2,
                        "accepted": 2,
                        "budget_used_peak": 0.99,
                        "overdue_foreshadowing": overdue,
                        "health_latest": 10.0,
                        "ced_per_1k_words": ced,
                        "ced_issue_count": 6,
                        "ced_word_count": 2000,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


def test_default_baseline_uses_corrected_consistency_ced() -> None:
    point = baseline_at(load_baseline(), 100)

    assert point.ced_per_1k_words == 0.3976
    assert point.ced_issue_count == 157
    assert point.ced_word_count == 394839
    assert point.legacy_ced_per_1k_words == 9.1328


def test_baseline_interpolation_matches_vdim_rules() -> None:
    points = (
        BaselinePoint(
            up_to=25,
            accepted=25,
            budget_used_peak=0.8,
            overdue_foreshadowing=60,
            health_latest=9.0,
            ced_per_1k_words=0.3,
        ),
        BaselinePoint(
            up_to=50,
            accepted=50,
            budget_used_peak=0.9,
            overdue_foreshadowing=110,
            health_latest=9.5,
            ced_per_1k_words=0.4,
        ),
    )

    interpolated = baseline_at(points, 37)

    assert interpolated.overdue_foreshadowing == pytest.approx(84.0)
    assert interpolated.ced_per_1k_words == pytest.approx(0.348)
    assert interpolated.budget_used_peak == 0.9
    assert interpolated.health_latest == 9.0


def test_collect_metrics_uses_parent_source_and_consistency_only(tmp_path: Path) -> None:
    db_path = tmp_path / "metrics.db"
    _init_metric_db(db_path)
    _seed_metric_rows(db_path)

    metrics = collect_metrics(db_path, project_id="p1", up_to=2, genre="fixture")

    assert metrics.accepted == 2
    assert metrics.budget_used_peak == 0.9
    assert metrics.overdue_foreshadowing == 1
    assert metrics.health_latest == 8.5
    assert metrics.ced.issue_count == 4
    assert metrics.ced.word_count == 2000
    assert metrics.ced.ced_per_1k_words == 2.0


def test_missing_db_fails_without_creating_file(tmp_path: Path) -> None:
    db_path = tmp_path / "missing.db"

    with pytest.raises(FiveGateToolError, match="does not exist"):
        collect_metrics(db_path, project_id="p1", up_to=2, genre="fixture")

    assert not db_path.exists()


def test_evaluate_project_returns_json_ready_pass_report(tmp_path: Path) -> None:
    db_path = tmp_path / "metrics.db"
    baseline_path = tmp_path / "baseline.json"
    _init_metric_db(db_path)
    _seed_metric_rows(db_path)
    _write_baseline(baseline_path)

    report = evaluate_project(
        db_path,
        project_id="p1",
        genre="fixture",
        up_to=2,
        baseline_path=baseline_path,
    )

    payload = report.to_dict()
    assert report.verdict == "PASS"
    assert payload["metrics"]["ced"]["issue_count"] == 4
    assert [gate["name"] for gate in payload["gates"]] == [
        "budget",
        "CED",
        "overdue",
        "health",
        "completeness",
    ]


def test_evaluate_project_fails_budget_gate_when_halt_record_exists(tmp_path: Path) -> None:
    db_path = tmp_path / "metrics.db"
    baseline_path = tmp_path / "baseline.json"
    _init_metric_db(db_path)
    _seed_metric_rows(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE adaptive_halt_decisions (
            project_id TEXT,
            status TEXT,
            evaluated_at_chapter INTEGER,
            reasons_json TEXT
        )
        """
    )
    conn.execute(
        "INSERT INTO adaptive_halt_decisions VALUES (?, ?, ?, ?)",
        ("p1", "halt", 2, json.dumps(["context_emergency_budget_ratio_halt"])),
    )
    conn.commit()
    conn.close()
    _write_baseline(baseline_path)

    report = evaluate_project(
        db_path,
        project_id="p1",
        genre="fixture",
        up_to=2,
        baseline_path=baseline_path,
    )

    budget_gate = next(gate for gate in report.gates if gate.name == "budget")
    assert report.verdict == "FAIL"
    assert not budget_gate.passed
    assert report.metrics.halt == (
        'adaptive_halt@Ch2:["context_emergency_budget_ratio_halt"]'
    )


def _init_segment_db(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE chapter_heads (
            project_id TEXT,
            chapter_number INTEGER,
            accepted_version_id TEXT
        );
        CREATE TABLE chapter_versions (
            version_id TEXT,
            project_id TEXT,
            chapter_number INTEGER
        );
        CREATE TABLE review_reports (
            chapter_version_id TEXT,
            issues TEXT
        );
        CREATE TABLE setting_tracking (
            project_id TEXT,
            last_mentioned_chapter INTEGER,
            category TEXT,
            status TEXT
        );
        CREATE TABLE continuity_reports (
            project_id TEXT,
            checked_up_to_chapter INTEGER,
            overall_health_score REAL
        );
        """
    )
    conn.close()


def test_segment_audit_collects_hotspots_orphans_and_health(tmp_path: Path) -> None:
    db_path = tmp_path / "segment.db"
    _init_segment_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.executemany(
        "INSERT INTO chapter_heads VALUES (?, ?, ?)",
        [("p1", 1, "v1"), ("p1", 2, "v2"), ("p1", 3, "v3")],
    )
    conn.executemany(
        "INSERT INTO chapter_versions VALUES (?, ?, ?)",
        [("v1", "p1", 1), ("v2", "p1", 2), ("v3", "p1", 3)],
    )
    conn.executemany(
        "INSERT INTO review_reports VALUES (?, ?)",
        [
            ("v1", json.dumps([_issue("show_dont_tell"), _issue("world_consistency")])),
            ("v2", json.dumps([_issue("world_consistency", severity="minor")])),
            ("v3", json.dumps([_issue("dialogue_distinctness")])),
        ],
    )
    conn.executemany(
        "INSERT INTO setting_tracking VALUES (?, ?, ?, ?)",
        [
            ("p1", 1, "critical", "active"),
            ("p1", 0, "background", "active"),
            ("p1", 2, "critical", "archived"),
        ],
    )
    conn.executemany(
        "INSERT INTO continuity_reports VALUES (?, ?, ?)",
        [("p1", 1, 8.1), ("p1", 3, 8.7)],
    )
    conn.commit()
    conn.close()

    report = collect_segment_audit(db_path, project_id="p1", up_to=3, top=2)

    assert report.next_audit_chapter == 6
    assert report.critical_orphans == 1
    assert report.total_orphans == 2
    assert report.halt_would_fire
    assert [hotspot.to_dict() for hotspot in report.hotspots] == [
        {"chapter_number": 1, "issue_count": 2},
        {"chapter_number": 3, "issue_count": 1},
    ]
    assert [point.health for point in report.health_trajectory] == [8.1, 8.7]


def test_segment_audit_rejects_unknown_project_even_with_up_to(tmp_path: Path) -> None:
    db_path = tmp_path / "segment.db"
    _init_segment_db(db_path)

    with pytest.raises(FiveGateToolError, match="no accepted chapters"):
        collect_segment_audit(db_path, project_id="missing", up_to=3)


def test_segment_audit_rejects_up_to_beyond_accepted_boundary(tmp_path: Path) -> None:
    db_path = tmp_path / "segment.db"
    _init_segment_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute("INSERT INTO chapter_heads VALUES (?, ?, ?)", ("p1", 3, "v3"))
    conn.commit()
    conn.close()

    with pytest.raises(FiveGateToolError, match="exceeds accepted boundary"):
        collect_segment_audit(db_path, project_id="p1", up_to=4)


def test_five_gate_script_json_smoke(tmp_path: Path) -> None:
    db_path = tmp_path / "metrics.db"
    baseline_path = tmp_path / "baseline.json"
    _init_metric_db(db_path)
    _seed_metric_rows(db_path)
    _write_baseline(baseline_path)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/five_gate_check.py",
            "--genre",
            "fixture",
            "--db",
            str(db_path),
            "--project-id",
            "p1",
            "--up-to",
            "2",
            "--baseline",
            str(baseline_path),
            "--format",
            "json",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    payload: dict[str, Any] = json.loads(result.stdout)
    assert payload["verdict"] == "PASS"
    assert payload["metrics"]["genre"] == "fixture"
