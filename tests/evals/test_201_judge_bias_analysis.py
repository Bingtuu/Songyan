"""Task 201 judge bias analysis tests."""

from __future__ import annotations

from pathlib import Path

from songyan.evals.excellence_sampling import AnnotationRecord
from songyan.evals.excellence_signals import (
    ChapterSignalReport,
    EvidenceItem,
    ExcellenceSignalReport,
    LoadedChapter,
    SignalHit,
    Task197Metrics,
    Task198Metrics,
)
from songyan.evals.judge_bias_analysis import (
    build_judge_bias_report,
    render_judge_bias_report,
)
from songyan.evals.style_card_extraction import StyleCardReport
from songyan.evals.voice_anchor_extraction import VoiceAnchorReport


def _annotation(
    *,
    layer: str,
    annotator: str,
    overall: int,
    ai_tone: int,
    evidence_quotes: list[str] | None = None,
) -> AnnotationRecord:
    return AnnotationRecord(
        genre="scifi",
        chapter=84,
        version_id="v-84",
        sample_layer=layer,  # type: ignore[arg-type]
        annotator=annotator,  # type: ignore[arg-type]
        scores={
            "homogeneity": overall,
            "tension": overall,
            "ai_tone": ai_tone,
            "overall": overall,
        },
        evidence_quotes=evidence_quotes or [],
    )


def _chapter_report() -> ChapterSignalReport:
    return ChapterSignalReport(
        genre="scifi",
        chapter=84,
        version_id="v-84",
        segment=4,
        task197=Task197Metrics(
            scene_function="dialogue",
            scene_function_score=0.5,
            beat_signature="D-D-D-D",
            tension_average=0.1,
            tension_peak=1.0,
            tension_stdev=0.2,
            dominant_terms=[],
            segment_function_ratio=0.8,
        ),
        task198=Task198Metrics(engineering_residue_count=1),
        hits=[
            SignalHit(
                task="198",
                signal_id="engineering_residue",
                label="工程残留",
                severity="high",
                evidence=[EvidenceItem(chapter=84, location="第1段", quote="TODO")],
            ),
            SignalHit(
                task="197",
                signal_id="beat_rhythm_repetition",
                label="桥段节奏重复",
                severity="medium",
                evidence=[EvidenceItem(chapter=84, location="beat", quote="D-D-D-D")],
            ),
        ],
    )


def _excellence_report() -> ExcellenceSignalReport:
    return ExcellenceSignalReport(
        generated_at="2026-08-01T00:00:00+00:00",
        sample_set="sample.json",
        annotations="annotations.json",
        boundaries=["report-only"],
        summaries={},
        calibration=[],
        chapters=[_chapter_report()],
    )


def _style_report() -> StyleCardReport:
    return StyleCardReport(
        generated_at="2026-08-01T00:00:00+00:00",
        sample_set="sample.json",
        annotations="annotations.json",
        excellence_report="excellence.json",
        boundaries=["report-only"],
        cards=[],
        sanity_checks=[],
    )


def _voice_report() -> VoiceAnchorReport:
    return VoiceAnchorReport(
        generated_at="2026-08-01T00:00:00+00:00",
        sample_set="sample.json",
        annotations="annotations.json",
        excellence_report="excellence.json",
        style_card_report="style.json",
        boundaries=["report-only"],
        anchors=[],
        unknown_attribution=[],
        sanity_checks=[],
    )


def test_paired_prelabel_and_spotcheck_are_not_overwritten() -> None:
    chapter = LoadedChapter(
        genre="scifi",
        chapter=84,
        version_id="v-84",
        segment=4,
        content="真实证据。TODO",
    )
    annotations = [
        _annotation(
            layer="prelabel",
            annotator="llm-prelabel",
            overall=4,
            ai_tone=4,
            evidence_quotes=["不在正文里的引用"],
        ),
        _annotation(
            layer="spotcheck",
            annotator="agent-deep-read",
            overall=2,
            ai_tone=1,
            evidence_quotes=["真实证据"],
        ),
    ]

    report = build_judge_bias_report(
        [chapter],
        annotations,
        _excellence_report(),
        _style_report(),
        _voice_report(),
        sample_set_path=Path("sample.json"),
        annotations_path=Path("annotations.json"),
        excellence_report_path=Path("excellence.json"),
        style_card_report_path=Path("style.json"),
        voice_anchor_report_path=Path("voice.json"),
    )

    assert report.summary["prelabel_records"] == 1
    assert report.summary["paired_spotcheck_records"] == 1
    assert report.summary["major_deltas_ge_2"] >= 1
    leniency = next(item for item in report.findings if item.bias_id == "leniency_bias")
    assert leniency.status == "supported"


def test_evidence_fidelity_detects_non_verbatim_prelabel_quote() -> None:
    chapter = LoadedChapter("scifi", 84, "v-84", 4, "真实证据。TODO")
    annotations = [
        _annotation(
            layer="prelabel",
            annotator="llm-prelabel",
            overall=4,
            ai_tone=4,
            evidence_quotes=["不在正文里的引用"],
        ),
        _annotation(
            layer="spotcheck",
            annotator="agent-deep-read",
            overall=2,
            ai_tone=1,
            evidence_quotes=["真实证据"],
        ),
    ]

    report = build_judge_bias_report(
        [chapter],
        annotations,
        _excellence_report(),
        _style_report(),
        _voice_report(),
        sample_set_path=Path("sample.json"),
        annotations_path=Path("annotations.json"),
        excellence_report_path=Path("excellence.json"),
        style_card_report_path=Path("style.json"),
        voice_anchor_report_path=Path("voice.json"),
    )

    prelabel = next(item for item in report.evidence_fidelity if item.layer == "prelabel")
    assert prelabel.quote_count == 1
    assert prelabel.verbatim_count == 0
    assert prelabel.bad_examples


def test_markdown_declares_report_only_and_no_gate() -> None:
    chapter = LoadedChapter("scifi", 84, "v-84", 4, "真实证据。TODO")
    annotations = [
        _annotation(layer="prelabel", annotator="llm-prelabel", overall=4, ai_tone=4),
        _annotation(layer="spotcheck", annotator="agent-deep-read", overall=2, ai_tone=1),
    ]
    report = build_judge_bias_report(
        [chapter],
        annotations,
        _excellence_report(),
        _style_report(),
        _voice_report(),
        sample_set_path=Path("sample.json"),
        annotations_path=Path("annotations.json"),
        excellence_report_path=Path("excellence.json"),
        style_card_report_path=Path("style.json"),
        voice_anchor_report_path=Path("voice.json"),
    )

    markdown = render_judge_bias_report(report)

    assert "does not call LLM judges" in markdown
    assert "does not enter accept/reject gates" in markdown
    assert "Prelabel is comparison-only" in markdown
