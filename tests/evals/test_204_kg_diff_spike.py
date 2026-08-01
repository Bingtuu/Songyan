"""Task 204 KG graph diff spike tests."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from songyan.evals.kg_diff_spike import (
    KGDiffManifest,
    KGDiffSample,
    _build_snapshot,
    _open_readonly_db,
    build_kg_diff_spike_report,
    load_kg_diff_manifest,
    render_kg_diff_spike_report,
)

ROOT = Path(__file__).resolve().parents[2]
REAL_MANIFEST = ROOT / "archive/v10/artifacts/204-kg-diff-sample-manifest.json"


def _sample(
    sample_id: str,
    *,
    kind: str = "positive",
    issue_type: str = "setting_tracking_missing_refresh",
    db_path: str = "kg.db",
    chapter: int = 5,
    expected_signal: str = "missing_refresh_candidate",
    expected_gain: list[str] | None = None,
    genre: str = "fixture",
) -> dict[str, Any]:
    return {
        "sample_id": sample_id,
        "kind": kind,
        "genre": genre,
        "issue_type": issue_type,
        "db_path": db_path,
        "project_id": "p1",
        "run_id": "run-fixture",
        "chapter": chapter,
        "accepted_version_id": f"v{chapter}",
        "sample_status": "pre_fix" if kind == "positive" else "post_fix",
        "truth_source_doc": "tasks/fixture.md",
        "expected_signal": expected_signal,
        "expected_existing_tool_coverage": ["segment_audit"]
        if kind == "positive"
        else ["none"],
        "expected_gain": expected_gain or ["tracking_id_localization"],
        "notes": [],
    }


def _manifest(tmp_path: Path, samples: list[dict[str, Any]]) -> KGDiffManifest:
    while len([item for item in samples if item["kind"] == "positive"]) < 6:
        idx = len(samples)
        genre = "fixture_b" if idx % 2 else "fixture"
        samples.append(_sample(f"pos-extra-{idx}", db_path="kg.db", genre=genre))
    while len([item for item in samples if item["kind"] == "negative_control"]) < 3:
        idx = len(samples)
        samples.append(
            _sample(
                f"neg-extra-{idx}",
                kind="negative_control",
                issue_type="negative_control",
                db_path="clean.db",
                chapter=10,
                expected_signal="none",
                expected_gain=[],
                genre="fixture_b",
            )
        )
    return KGDiffManifest.model_validate(
        {
            "description": "fixture manifest",
            "report_only": True,
            "samples": samples,
        }
    )


def _init_db(db_path: Path, *, clean: bool = False) -> None:
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE chapter_heads (
            project_id TEXT,
            chapter_number INTEGER,
            current_version_id TEXT,
            accepted_version_id TEXT,
            status TEXT
        );
        CREATE TABLE chapter_versions (
            version_id TEXT,
            project_id TEXT,
            chapter_number INTEGER,
            content TEXT
        );
        CREATE TABLE setting_tracking (
            tracking_id TEXT,
            project_id TEXT,
            setting_key TEXT,
            setting_name TEXT,
            description TEXT,
            introduced_in_chapter INTEGER,
            last_mentioned_chapter INTEGER,
            expected_resolve_chapter INTEGER,
            status TEXT,
            source_version_id TEXT,
            category TEXT,
            resolved_chapter INTEGER,
            resolved_version_id TEXT
        );
        CREATE TABLE foreshadowings (
            foreshadowing_id TEXT,
            project_id TEXT,
            description TEXT,
            planted_in_chapter INTEGER,
            expected_resolve_chapter INTEGER,
            status TEXT,
            lifecycle_status TEXT,
            source_version_id TEXT
        );
        CREATE TABLE human_marks (
            mark_id TEXT,
            project_id TEXT,
            mark_type TEXT,
            target_key TEXT,
            note TEXT,
            priority INTEGER,
            created_at_chapter INTEGER,
            resolved_at TEXT,
            lifecycle_status TEXT,
            source TEXT,
            version_id TEXT,
            severity TEXT
        );
        CREATE TABLE continuity_reports (
            report_id TEXT,
            project_id TEXT,
            checked_up_to_chapter INTEGER,
            orphaned_settings TEXT,
            forgotten_items TEXT,
            state_mismatches TEXT,
            overdue_foreshadowings TEXT,
            suggested_marks TEXT,
            overall_health_score REAL,
            created_at TEXT
        );
        """
    )
    versions = [(f"v{i}", "p1", i, f"正文 {i}") for i in range(1, 11)]
    heads = [("p1", i, f"v{i}", f"v{i}", "accepted") for i in range(1, 11)]
    conn.executemany("INSERT INTO chapter_versions VALUES (?, ?, ?, ?)", versions)
    conn.executemany("INSERT INTO chapter_heads VALUES (?, ?, ?, ?, ?)", heads)
    if clean:
        conn.execute(
            "INSERT INTO continuity_reports VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("cont-clean", "p1", 10, "[]", "[]", "[]", "[]", "[]", 9.0, "2026-01-01"),
        )
    else:
        conn.execute(
            "INSERT INTO setting_tracking VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "track-critical",
                "p1",
                "setting.critical",
                "关键设定",
                "需要刷新",
                1,
                1,
                None,
                "active",
                "v1",
                "critical",
                None,
                None,
            ),
        )
        conn.execute(
            "INSERT INTO foreshadowings VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("fs-overdue", "p1", "旧伏笔", 1, 3, "overdue", "active", "v1"),
        )
        conn.execute(
            "INSERT INTO human_marks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "hm-overdue",
                "p1",
                "foreshadowing",
                "fs-overdue",
                "需要回收",
                9,
                5,
                None,
                "active",
                "continuity_auditor",
                "v5",
                "P2",
            ),
        )
        conn.executemany(
            "INSERT INTO continuity_reports VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    "cont-old",
                    "p1",
                    5,
                    "[]",
                    "[]",
                    "[]",
                    "[]",
                    "[]",
                    7.1,
                    "2026-01-01T00:00:00",
                ),
                (
                    "cont-new",
                    "p1",
                    5,
                    "[]",
                    "[]",
                    "[]",
                    "[]",
                    "[]",
                    8.2,
                    "2026-01-01T01:00:00",
                ),
            ],
        )
    conn.commit()
    conn.close()


def test_real_manifest_schema_is_valid() -> None:
    manifest = load_kg_diff_manifest(REAL_MANIFEST)

    assert manifest.report_only is True
    assert sum(1 for item in manifest.samples if item.kind == "positive") == 6
    assert sum(1 for item in manifest.samples if item.kind == "negative_control") == 3


def test_snapshot_excludes_future_setting_tracking_state(tmp_path: Path) -> None:
    db_path = tmp_path / "kg.db"
    _init_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO setting_tracking VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "track-future",
            "p1",
            "setting.future",
            "未来设定",
            "未来刷新",
            1,
            9,
            None,
            "active",
            "v9",
            "critical",
            None,
            None,
        ),
    )
    conn.commit()
    conn.close()

    sample = KGDiffSample.model_validate(_sample("pos", db_path=str(db_path), chapter=5))
    with _open_readonly_db(db_path) as readonly:
        snapshot = _build_snapshot(
            readonly,
            sample=sample,
            source_db=str(db_path),
            label="after",
            up_to=5,
        )

    assert "setting:track-critical" in {node.node_id for node in snapshot.nodes}
    assert "setting:track-future" not in {node.node_id for node in snapshot.nodes}


def test_positive_fixture_hits_missing_refresh_and_unresolved(tmp_path: Path) -> None:
    db_path = tmp_path / "kg.db"
    clean_path = tmp_path / "clean.db"
    _init_db(db_path)
    _init_db(clean_path, clean=True)
    manifest = _manifest(
        tmp_path,
        [
            _sample("pos-missing", db_path=db_path.name),
            _sample(
                "pos-unresolved",
                issue_type="foreshadowing_unresolved",
                db_path=db_path.name,
                expected_signal="unresolved_candidate",
                expected_gain=["foreshadowing_status_join", "validity_interval_needed"],
            ),
        ],
    )

    report = build_kg_diff_spike_report(
        manifest,
        manifest_path=tmp_path / "manifest.json",
        root_dir=tmp_path,
    )

    by_id = {item.sample.sample_id: item for item in report.samples}
    assert by_id["pos-missing"].evaluation.detected_by_kg_diff is True
    assert by_id["pos-unresolved"].evaluation.detected_by_kg_diff is True
    assert report.summary.unique_gain_count >= 2


def test_negative_control_has_no_high_confidence_false_positive(tmp_path: Path) -> None:
    db_path = tmp_path / "kg.db"
    clean_path = tmp_path / "clean.db"
    _init_db(db_path)
    _init_db(clean_path, clean=True)
    manifest = _manifest(tmp_path, [_sample("pos-missing", db_path=db_path.name)])

    report = build_kg_diff_spike_report(
        manifest,
        manifest_path=tmp_path / "manifest.json",
        root_dir=tmp_path,
    )

    negatives = [item for item in report.samples if item.sample.kind == "negative_control"]
    assert negatives
    assert all(item.evaluation.false_positive is False for item in negatives)
    assert all(item.evaluation.confidence == "none" for item in negatives)


def test_gain_matrix_and_markdown_rendering(tmp_path: Path) -> None:
    db_path = tmp_path / "kg.db"
    clean_path = tmp_path / "clean.db"
    _init_db(db_path)
    _init_db(clean_path, clean=True)
    manifest = _manifest(tmp_path, [_sample("pos-missing", db_path=db_path.name)])

    report = build_kg_diff_spike_report(
        manifest,
        manifest_path=tmp_path / "manifest.json",
        root_dir=tmp_path,
    )
    markdown = render_kg_diff_spike_report(report)

    assert report.gain_matrix
    assert "Task 204 KG 图 diff spike" in markdown
    assert "Gain Matrix" in markdown
    assert "does not write SQLite" in markdown


def test_missing_db_does_not_create_file_and_is_document_truth_only(tmp_path: Path) -> None:
    missing = tmp_path / "missing.db"
    clean_path = tmp_path / "clean.db"
    _init_db(clean_path, clean=True)
    manifest = _manifest(
        tmp_path,
        [_sample("pos-missing-db", db_path=missing.name)],
    )

    report = build_kg_diff_spike_report(
        manifest,
        manifest_path=tmp_path / "manifest.json",
        root_dir=tmp_path,
    )

    assert not missing.exists()
    sample = next(item for item in report.samples if item.sample.sample_id == "pos-missing-db")
    assert sample.document_truth_only is True
    assert sample.evaluation.confidence == "low"
