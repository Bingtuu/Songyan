"""Task 205 FactTrack validity interval spike tests."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from songyan.evals.facttrack_validity_interval import (
    FactTrackInputs,
    build_facttrack_validity_report,
    load_facttrack_inputs,
    render_facttrack_validity_report,
)
from songyan.evals.kg_diff_spike import KGDiffManifest, KGDiffSpikeReport

ROOT = Path(__file__).resolve().parents[2]
REAL_MANIFEST = ROOT / "archive/v10/artifacts/204-kg-diff-sample-manifest.json"
REAL_KG_REPORT = ROOT / "archive/v10/artifacts/204-kg-diff-spike-report.json"


def _sample(
    sample_id: str,
    *,
    kind: str = "positive",
    issue_type: str = "setting_tracking_missing_refresh",
    db_path: str = "kg.db",
    chapter: int = 5,
    expected_signal: str = "missing_refresh_candidate",
    genre: str = "fixture",
    expected_gain: list[str] | None = None,
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


def _manifest(samples: list[dict[str, Any]]) -> KGDiffManifest:
    while len([item for item in samples if item["kind"] == "positive"]) < 6:
        idx = len(samples)
        samples.append(
            _sample(
                f"pos-extra-{idx}",
                db_path="kg.db",
                genre="fixture_b" if idx % 2 else "fixture",
            )
        )
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
                genre="fixture_b",
                expected_gain=[],
            )
        )
    return KGDiffManifest.model_validate(
        {
            "description": "fixture manifest",
            "report_only": True,
            "samples": samples,
        }
    )


def _kg_report(manifest: KGDiffManifest) -> KGDiffSpikeReport:
    samples = []
    for sample in manifest.samples:
        detected = sample.kind == "positive"
        confidence = "high" if detected else "none"
        samples.append(
            {
                "sample": sample.model_dump(mode="json"),
                "db_exists": True,
                "document_truth_only": False,
                "diffs": [],
                "evaluation": {
                    "truth_label": sample.issue_type,
                    "detected_by_kg_diff": detected,
                    "covered_by_segment_audit": "segment_audit"
                    in sample.expected_existing_tool_coverage,
                    "covered_by_ced": False,
                    "covered_by_human_marks": "human_marks"
                    in sample.expected_existing_tool_coverage,
                    "unique_gain": detected,
                    "false_positive": False,
                    "confidence": confidence,
                    "decision_note": "fixture",
                },
                "warnings": [],
            }
        )
    return KGDiffSpikeReport.model_validate(
        {
            "generated_at": "2026-01-01T00:00:00+00:00",
            "report_only": True,
            "boundaries": ["fixture"],
            "summary": {
                "report_only": True,
                "sample_count": len(samples),
                "positive_samples": sum(1 for item in manifest.samples if item.kind == "positive"),
                "negative_controls": sum(
                    1 for item in manifest.samples if item.kind == "negative_control"
                ),
                "db_backed_samples": len(samples),
                "document_truth_only_samples": 0,
                "high_confidence_detections": sum(
                    1 for item in manifest.samples if item.kind == "positive"
                ),
                "unique_gain_count": sum(
                    1 for item in manifest.samples if item.kind == "positive"
                ),
                "decision": "defer",
                "decision_reason": "fixture",
                "next_route": "Task 205",
            },
            "source_manifest": "fixture",
            "gain_matrix": [],
            "samples": samples,
        }
    )


def _inputs(manifest: KGDiffManifest) -> FactTrackInputs:
    return FactTrackInputs(manifest=manifest, kg_diff_report=_kg_report(manifest))


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
    for chapter in range(1, 11):
        conn.execute(
            "INSERT INTO chapter_versions VALUES (?, ?, ?, ?)",
            (f"v{chapter}", "p1", chapter, f"正文 {chapter}"),
        )
        conn.execute(
            "INSERT INTO chapter_heads VALUES (?, ?, ?, ?, ?)",
            ("p1", chapter, f"v{chapter}", f"v{chapter}", "accepted"),
        )
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
                ("cont-old", "p1", 5, "[]", "[]", "[]", "[]", "[]", 7.1, "2026-01-01"),
                ("cont-new", "p1", 5, "[]", "[]", "[]", "[]", "[]", 8.2, "2026-01-02"),
            ],
        )
    conn.commit()
    conn.close()


def test_loads_real_task204_manifest_and_report() -> None:
    inputs = load_facttrack_inputs(
        manifest_path=REAL_MANIFEST,
        kg_diff_report_path=REAL_KG_REPORT,
    )

    assert inputs.manifest.report_only is True
    assert inputs.kg_diff_report.summary.decision == "defer"


def test_setting_and_foreshadowing_intervals_explain_positive_samples(
    tmp_path: Path,
) -> None:
    _init_db(tmp_path / "kg.db")
    _init_db(tmp_path / "clean.db", clean=True)
    manifest = _manifest(
        [
            _sample("pos-setting", db_path="kg.db"),
            _sample(
                "pos-foreshadowing",
                issue_type="foreshadowing_unresolved",
                db_path="kg.db",
                expected_signal="unresolved_candidate",
                expected_gain=["foreshadowing_status_join"],
            ),
        ]
    )

    report = build_facttrack_validity_report(
        _inputs(manifest),
        manifest_path=tmp_path / "manifest.json",
        kg_diff_report_path=tmp_path / "kg-report.json",
        root_dir=tmp_path,
    )

    by_id = {item.sample.sample_id: item for item in report.samples}
    assert by_id["pos-setting"].evaluation.interval_explained is True
    assert by_id["pos-foreshadowing"].evaluation.interval_explained is True
    assert report.summary.interval_explained >= 2


def test_same_chapter_continuity_report_stale_ordering(tmp_path: Path) -> None:
    _init_db(tmp_path / "kg.db")
    _init_db(tmp_path / "clean.db", clean=True)
    manifest = _manifest(
        [
            _sample(
                "pos-stale",
                issue_type="stale_continuity_report",
                db_path="kg.db",
                expected_signal="stale_candidate",
                expected_gain=["same_chapter_report_collision"],
            )
        ]
    )

    report = build_facttrack_validity_report(
        _inputs(manifest),
        manifest_path=tmp_path / "manifest.json",
        kg_diff_report_path=tmp_path / "kg-report.json",
        root_dir=tmp_path,
    )

    sample = next(item for item in report.samples if item.sample.sample_id == "pos-stale")
    assert sample.evaluation.interval_explained is True
    assert any(
        interval.fact_type == "continuity_report"
        and interval.valid_status == "superseded"
        and interval.confidence == "high"
        for interval in sample.intervals
    )


def test_negative_controls_do_not_get_high_confidence_false_positive(
    tmp_path: Path,
) -> None:
    _init_db(tmp_path / "kg.db")
    _init_db(tmp_path / "clean.db", clean=True)
    manifest = _manifest([_sample("pos-setting", db_path="kg.db")])

    report = build_facttrack_validity_report(
        _inputs(manifest),
        manifest_path=tmp_path / "manifest.json",
        kg_diff_report_path=tmp_path / "kg-report.json",
        root_dir=tmp_path,
    )

    negatives = [item for item in report.samples if item.sample.kind == "negative_control"]
    assert negatives
    assert all(item.evaluation.false_positive is False for item in negatives)
    assert all(item.evaluation.confidence == "none" for item in negatives)


def test_impact_matrix_markdown_and_decision(tmp_path: Path) -> None:
    _init_db(tmp_path / "kg.db")
    _init_db(tmp_path / "clean.db", clean=True)
    manifest = _manifest(
        [
            _sample("pos-setting", db_path="kg.db"),
            _sample(
                "pos-foreshadowing",
                issue_type="foreshadowing_unresolved",
                db_path="kg.db",
                expected_signal="unresolved_candidate",
                expected_gain=["foreshadowing_status_join"],
            ),
        ]
    )

    report = build_facttrack_validity_report(
        _inputs(manifest),
        manifest_path=tmp_path / "manifest.json",
        kg_diff_report_path=tmp_path / "kg-report.json",
        root_dir=tmp_path,
    )
    markdown = render_facttrack_validity_report(report)

    assert report.impact_matrix
    assert report.summary.decision in {"continue", "defer"}
    assert "Task 205 FactTrack validity interval spike" in markdown
    assert "Migration Impact" in markdown


def test_missing_db_is_document_truth_only_and_does_not_create_file(
    tmp_path: Path,
) -> None:
    _init_db(tmp_path / "clean.db", clean=True)
    missing = tmp_path / "missing.db"
    manifest = _manifest([_sample("pos-missing", db_path=missing.name)])

    report = build_facttrack_validity_report(
        _inputs(manifest),
        manifest_path=tmp_path / "manifest.json",
        kg_diff_report_path=tmp_path / "kg-report.json",
        root_dir=tmp_path,
    )

    assert not missing.exists()
    sample = next(item for item in report.samples if item.sample.sample_id == "pos-missing")
    assert sample.document_truth_only is True
    assert sample.evaluation.confidence == "low"


def test_script_writes_json_and_markdown(tmp_path: Path) -> None:
    _init_db(tmp_path / "kg.db")
    _init_db(tmp_path / "clean.db", clean=True)
    manifest = _manifest([_sample("pos-setting", db_path="kg.db")])
    kg_report = _kg_report(manifest)
    manifest_path = tmp_path / "manifest.json"
    kg_path = tmp_path / "kg.json"
    json_path = tmp_path / "out.json"
    md_path = tmp_path / "out.md"
    manifest_path.write_text(
        json.dumps(manifest.model_dump(mode="json"), ensure_ascii=False),
        encoding="utf-8",
    )
    kg_path.write_text(
        json.dumps(kg_report.model_dump(mode="json"), ensure_ascii=False),
        encoding="utf-8",
    )

    from scripts.run_205_facttrack_validity_interval import main

    rc = main(
        [
            "--manifest",
            str(manifest_path),
            "--kg-diff-report",
            str(kg_path),
            "--output-json",
            str(json_path),
            "--output-md",
            str(md_path),
        ]
    )

    assert rc == 0
    assert json_path.exists()
    assert md_path.exists()
