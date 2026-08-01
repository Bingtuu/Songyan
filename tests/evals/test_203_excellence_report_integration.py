"""Task 203 integrated excellence report tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from songyan.evals.excellence_report_integration import (
    ExcellenceIntegrationError,
    build_integrated_excellence_report,
    load_integration_inputs,
    render_integrated_excellence_report,
)

ROOT = Path(__file__).resolve().parents[2]
SAMPLE_SET = ROOT / "tasks/196-excellence-sample-set.json"
ANNOTATIONS = ROOT / "tasks/196-excellence-annotations.json"
EXCELLENCE_REPORT = ROOT / "tasks/197-198-excellence-signals-report.json"
STYLE_REPORT = ROOT / "tasks/199-style-card-report.json"
VOICE_REPORT = ROOT / "tasks/200-character-voice-anchor-report.json"
JUDGE_REPORT = ROOT / "tasks/201-judge-bias-report.json"
READABILITY_REPORT = ROOT / "tasks/202-readability-feasibility-report.json"


def _load_real_report() -> Any:
    inputs = load_integration_inputs(
        sample_set_path=SAMPLE_SET,
        annotations_path=ANNOTATIONS,
        excellence_report_path=EXCELLENCE_REPORT,
        style_card_report_path=STYLE_REPORT,
        voice_anchor_report_path=VOICE_REPORT,
        judge_bias_report_path=JUDGE_REPORT,
        readability_report_path=READABILITY_REPORT,
    )
    return build_integrated_excellence_report(
        inputs,
        sample_set_path=SAMPLE_SET,
        annotations_path=ANNOTATIONS,
        excellence_report_path=EXCELLENCE_REPORT,
        style_card_report_path=STYLE_REPORT,
        voice_anchor_report_path=VOICE_REPORT,
        judge_bias_report_path=JUDGE_REPORT,
        readability_report_path=READABILITY_REPORT,
    )


def test_builds_chapter_and_signal_indexes_from_real_artifacts() -> None:
    report = _load_real_report()

    assert report.report_only is True
    assert report.task203_summary.chapter_view_count == 60
    assert report.task203_summary.signal_view_count >= 6
    assert {layer.layer for layer in report.signal_layers} == {
        "structure",
        "ai_tone",
        "style",
        "voice",
        "judge_bias",
        "readability",
    }
    assert any(item.layer == "structure" for item in report.signal_index)
    assert any(item.layer == "readability" for item in report.signal_index)


def test_calibration_truth_uses_agent_deep_read_not_prelabel() -> None:
    report = _load_real_report()

    assert report.calibration_truth.truth_records == 24
    assert report.calibration_truth.anchor_records == 12
    assert report.calibration_truth.spotcheck_records == 12
    assert report.calibration_truth.prelabel_records == 48
    assert "low-confidence comparison" in report.calibration_truth.prelabel_usage


def test_json_schema_has_no_hard_score_or_verdict_fields() -> None:
    report = _load_real_report()
    dumped = report.model_dump(mode="json")
    prohibited = {
        "excellence_total_score",
        "rank",
        "ranking",
        "pass_fail",
        "passfail",
        "hard_verdict",
    }

    def walk(value: Any) -> set[str]:
        found: set[str] = set()
        if isinstance(value, dict):
            for key, item in value.items():
                if key in prohibited:
                    found.add(key)
                found.update(walk(item))
        elif isinstance(value, list):
            for item in value:
                found.update(walk(item))
        return found

    assert walk(dumped) == set()


def test_report_only_false_input_fails(tmp_path: Path) -> None:
    broken = json.loads(EXCELLENCE_REPORT.read_text(encoding="utf-8"))
    broken["report_only"] = False
    broken_path = tmp_path / "broken-197.json"
    broken_path.write_text(json.dumps(broken, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ExcellenceIntegrationError, match="report_only=true"):
        load_integration_inputs(
            sample_set_path=SAMPLE_SET,
            annotations_path=ANNOTATIONS,
            excellence_report_path=broken_path,
            style_card_report_path=STYLE_REPORT,
            voice_anchor_report_path=VOICE_REPORT,
            judge_bias_report_path=JUDGE_REPORT,
            readability_report_path=READABILITY_REPORT,
        )


def test_missing_input_fails(tmp_path: Path) -> None:
    with pytest.raises(ExcellenceIntegrationError, match="failed to read"):
        load_integration_inputs(
            sample_set_path=SAMPLE_SET,
            annotations_path=ANNOTATIONS,
            excellence_report_path=EXCELLENCE_REPORT,
            style_card_report_path=STYLE_REPORT,
            voice_anchor_report_path=VOICE_REPORT,
            judge_bias_report_path=JUDGE_REPORT,
            readability_report_path=tmp_path / "missing.json",
        )


def test_markdown_declares_standalone_report_only_boundaries() -> None:
    report = _load_real_report()
    markdown = render_integrated_excellence_report(report)

    assert "standalone offline report" in markdown
    assert "not wired into songyan report" in markdown
    assert "does not enter accept/reject gates" in markdown
    assert "excellence_total_score" not in markdown
