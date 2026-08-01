"""Task 206 Storyline Tree spike tests."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from songyan.evals.facttrack_validity_interval import FactTrackValidityReport
from songyan.evals.kg_diff_spike import KGDiffManifest, KGDiffSpikeReport
from songyan.evals.storyline_tree_spike import (
    StorylineTreeInputs,
    build_storyline_tree_report,
    load_storyline_tree_inputs,
    render_storyline_tree_report,
)

ROOT = Path(__file__).resolve().parents[2]
REAL_MANIFEST = ROOT / "tasks/204-kg-diff-sample-manifest.json"
REAL_KG_REPORT = ROOT / "tasks/204-kg-diff-spike-report.json"
REAL_FACTTRACK_REPORT = ROOT / "tasks/205-facttrack-validity-interval-report.json"


def _sample(
    sample_id: str,
    *,
    kind: str = "positive",
    issue_type: str = "foreshadowing_unresolved",
    db_path: str = "story.db",
    chapter: int = 5,
    expected_signal: str = "unresolved_candidate",
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
        "expected_existing_tool_coverage": ["human_marks"]
        if kind == "positive"
        else ["none"],
        "expected_gain": ["foreshadowing_status_join", "validity_interval_needed"]
        if kind == "positive"
        else [],
        "notes": [],
    }


def _manifest(samples: list[dict[str, Any]]) -> KGDiffManifest:
    while len([item for item in samples if item["kind"] == "positive"]) < 6:
        idx = len(samples)
        samples.append(
            _sample(
                f"pos-extra-{idx}",
                db_path="story.db",
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
        samples.append(
            {
                "sample": sample.model_dump(mode="json"),
                "db_exists": True,
                "document_truth_only": False,
                "diffs": [],
                "evaluation": {
                    "truth_label": sample.issue_type,
                    "detected_by_kg_diff": detected,
                    "covered_by_segment_audit": False,
                    "covered_by_ced": False,
                    "covered_by_human_marks": detected,
                    "unique_gain": detected,
                    "false_positive": False,
                    "confidence": "high" if detected else "none",
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


def _facttrack_report(manifest: KGDiffManifest) -> FactTrackValidityReport:
    samples = []
    for sample in manifest.samples:
        explained = sample.kind == "positive"
        needs_story = sample.issue_type == "foreshadowing_unresolved"
        samples.append(
            {
                "sample": sample.model_dump(mode="json"),
                "db_exists": True,
                "document_truth_only": False,
                "intervals": [],
                "evaluation": {
                    "sample_id": sample.sample_id,
                    "issue_type": sample.issue_type,
                    "kind": sample.kind,
                    "interval_explained": explained,
                    "false_positive": False,
                    "confidence": "high" if explained else "none",
                    "reduced_false_positive": sample.kind == "negative_control",
                    "reduced_false_negative": explained,
                    "needs_alias_policy": False,
                    "needs_storyline_tree": needs_story,
                    "document_truth_only": False,
                    "decision_note": "fixture",
                },
                "warnings": [],
            }
        )
    return FactTrackValidityReport.model_validate(
        {
            "generated_at": "2026-01-01T00:00:00+00:00",
            "report_only": True,
            "boundaries": ["fixture"],
            "source_manifest": "fixture",
            "source_kg_diff_report": "fixture",
            "summary": {
                "report_only": True,
                "sample_count": len(samples),
                "positive_samples": sum(1 for item in manifest.samples if item.kind == "positive"),
                "negative_controls": sum(
                    1 for item in manifest.samples if item.kind == "negative_control"
                ),
                "db_backed_samples": len(samples),
                "document_truth_only_samples": 0,
                "interval_explained": sum(
                    1 for item in manifest.samples if item.kind == "positive"
                ),
                "false_positive_count": 0,
                "needs_alias_policy_count": 0,
                "needs_storyline_tree_count": sum(
                    1 for item in manifest.samples if item.issue_type == "foreshadowing_unresolved"
                ),
                "decision": "defer",
                "decision_reason": "fixture",
                "next_route": "Task 206",
            },
            "impact_matrix": [],
            "migration_impacts": [],
            "samples": samples,
        }
    )


def _inputs(manifest: KGDiffManifest) -> StorylineTreeInputs:
    return StorylineTreeInputs(
        manifest=manifest,
        kg_diff_report=_kg_report(manifest),
        facttrack_report=_facttrack_report(manifest),
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
        CREATE TABLE arc_summaries (
            arc_id TEXT,
            project_id TEXT,
            start_chapter INTEGER,
            end_chapter INTEGER,
            arc_title TEXT,
            arc_summary TEXT
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
            version_id TEXT,
            severity TEXT
        );
        CREATE TABLE setting_tracking (
            tracking_id TEXT,
            project_id TEXT,
            setting_key TEXT,
            setting_name TEXT,
            introduced_in_chapter INTEGER,
            last_mentioned_chapter INTEGER,
            status TEXT,
            source_version_id TEXT,
            category TEXT
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
    conn.execute(
        "INSERT INTO arc_summaries VALUES (?, ?, ?, ?, ?, ?)",
        ("arc-1", "p1", 1, 10, "第一弧", "主线推进"),
    )
    if clean:
        conn.execute(
            "INSERT INTO foreshadowings VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("fs-future", "p1", "未来伏笔", 8, 12, "planted", "active", "v8"),
        )
    else:
        conn.execute(
            "INSERT INTO foreshadowings VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("fs-overdue", "p1", "旧伏笔", 1, 3, "overdue", "active", "v1"),
        )
        conn.execute(
            "INSERT INTO human_marks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
                "v5",
                "P2",
            ),
        )
        conn.execute(
            "INSERT INTO setting_tracking VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "track-critical",
                "p1",
                "setting.critical",
                "关键设定",
                1,
                1,
                "active",
                "v1",
                "critical",
            ),
        )
    conn.commit()
    conn.close()


def test_loads_real_task204_and_task205_inputs() -> None:
    inputs = load_storyline_tree_inputs(
        manifest_path=REAL_MANIFEST,
        kg_diff_report_path=REAL_KG_REPORT,
        facttrack_report_path=REAL_FACTTRACK_REPORT,
    )

    assert inputs.manifest.report_only is True
    assert inputs.facttrack_report.summary.next_route == "Task 206 Storyline Tree spike"


def test_thread_nodes_explain_foreshadowing_unresolved(tmp_path: Path) -> None:
    _init_db(tmp_path / "story.db")
    _init_db(tmp_path / "clean.db", clean=True)
    manifest = _manifest([_sample("pos-thread", db_path="story.db")])

    report = build_storyline_tree_report(
        _inputs(manifest),
        manifest_path=tmp_path / "manifest.json",
        kg_diff_report_path=tmp_path / "kg.json",
        facttrack_report_path=tmp_path / "facttrack.json",
        root_dir=tmp_path,
    )

    sample = next(item for item in report.samples if item.sample.sample_id == "pos-thread")
    assert sample.evaluation.tree_explained is True
    assert any(node.node_type == "thread" and node.confidence == "high" for node in sample.nodes)


def test_negative_control_has_no_high_confidence_stale_storyline(tmp_path: Path) -> None:
    _init_db(tmp_path / "story.db")
    _init_db(tmp_path / "clean.db", clean=True)
    manifest = _manifest([_sample("pos-thread", db_path="story.db")])

    report = build_storyline_tree_report(
        _inputs(manifest),
        manifest_path=tmp_path / "manifest.json",
        kg_diff_report_path=tmp_path / "kg.json",
        facttrack_report_path=tmp_path / "facttrack.json",
        root_dir=tmp_path,
    )

    negatives = [item for item in report.samples if item.sample.kind == "negative_control"]
    assert negatives
    assert all(item.evaluation.false_positive is False for item in negatives)
    assert all(item.evaluation.confidence == "none" for item in negatives)


def test_impact_matrix_markdown_and_decision(tmp_path: Path) -> None:
    _init_db(tmp_path / "story.db")
    _init_db(tmp_path / "clean.db", clean=True)
    manifest = _manifest([_sample("pos-thread", db_path="story.db")])

    report = build_storyline_tree_report(
        _inputs(manifest),
        manifest_path=tmp_path / "manifest.json",
        kg_diff_report_path=tmp_path / "kg.json",
        facttrack_report_path=tmp_path / "facttrack.json",
        root_dir=tmp_path,
    )
    markdown = render_storyline_tree_report(report)

    assert report.impact_matrix
    assert report.summary.decision in {"continue", "defer"}
    assert "Task 206 Storyline Tree spike" in markdown
    assert "Migration Impact" in markdown


def test_missing_db_is_document_truth_only_and_does_not_create_file(tmp_path: Path) -> None:
    _init_db(tmp_path / "clean.db", clean=True)
    missing = tmp_path / "missing.db"
    manifest = _manifest([_sample("pos-missing", db_path=missing.name)])

    report = build_storyline_tree_report(
        _inputs(manifest),
        manifest_path=tmp_path / "manifest.json",
        kg_diff_report_path=tmp_path / "kg.json",
        facttrack_report_path=tmp_path / "facttrack.json",
        root_dir=tmp_path,
    )

    assert not missing.exists()
    sample = next(item for item in report.samples if item.sample.sample_id == "pos-missing")
    assert sample.document_truth_only is True
    assert sample.evaluation.confidence == "low"


def test_script_writes_json_and_markdown(tmp_path: Path) -> None:
    _init_db(tmp_path / "story.db")
    _init_db(tmp_path / "clean.db", clean=True)
    manifest = _manifest([_sample("pos-thread", db_path="story.db")])
    kg_report = _kg_report(manifest)
    facttrack = _facttrack_report(manifest)
    manifest_path = tmp_path / "manifest.json"
    kg_path = tmp_path / "kg.json"
    facttrack_path = tmp_path / "facttrack.json"
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
    facttrack_path.write_text(
        json.dumps(facttrack.model_dump(mode="json"), ensure_ascii=False),
        encoding="utf-8",
    )

    from scripts.run_206_storyline_tree_spike import main

    rc = main(
        [
            "--manifest",
            str(manifest_path),
            "--kg-diff-report",
            str(kg_path),
            "--facttrack-report",
            str(facttrack_path),
            "--output-json",
            str(json_path),
            "--output-md",
            str(md_path),
        ]
    )

    assert rc == 0
    assert json_path.exists()
    assert md_path.exists()
