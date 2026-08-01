"""Task 201 offline judge bias analysis and countermeasure protocol.

This module only consumes existing report artifacts.  It does not call LLMs,
does not add prompt cards, and does not affect Writer / CreativeDirector,
runtime gates, CED, five-gate, segment audit, or T9.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any, Literal

from pydantic import BaseModel, Field

from songyan.evals.excellence_sampling import AnnotationRecord
from songyan.evals.excellence_signals import (
    ChapterSignalReport,
    ExcellenceSignalReport,
    LoadedChapter,
    load_task196_inputs,
)
from songyan.evals.style_card_extraction import StyleCardReport
from songyan.evals.voice_anchor_extraction import VoiceAnchorReport

BiasId = Literal[
    "leniency_bias",
    "low_score_blindness",
    "evidence_drift",
    "engineering_artifact_blindness",
    "style_vs_quality_confusion",
    "voice_homogeneity_blindness",
]

DIMENSIONS = ("homogeneity", "tension", "ai_tone", "overall")
ENGINEERING_SIGNALS = {
    "engineering_residue",
    "chapter_self_reference",
    "verbatim_sentence_repeat",
    "verbatim_paragraph_repeat",
    "cross_chapter_verbatim_repeat",
    "setting_patch_segment",
}
STYLE_RISK_SIGNALS = {
    "beat_rhythm_repetition",
    "scene_function_homogeneity",
    "tension_flatline",
    "motif_reuse_density",
    "template_rhetoric_density",
    "not_but_template",
}
VOICE_RISK_SIGNALS = {
    "template_rhetoric_density",
    "verbatim_sentence_repeat",
    "verbatim_paragraph_repeat",
}


class JudgeBiasError(RuntimeError):
    """Raised when Task 201 inputs cannot be loaded."""


class ScoreDelta(BaseModel):
    """Score delta between LLM prelabel and agent-deep-read truth."""

    genre: str
    chapter: int = Field(ge=1)
    dimension: str
    prelabel: int
    truth: int
    delta: int


class EvidenceFidelitySummary(BaseModel):
    """Verbatim evidence quote fidelity for one annotation layer."""

    layer: str
    quote_count: int
    verbatim_count: int
    fidelity_ratio: float | None
    bad_examples: list[str] = Field(default_factory=list)


class BiasFinding(BaseModel):
    """One bias category with statistics and evidence."""

    bias_id: BiasId
    definition: str
    status: Literal["supported", "partial", "negative"]
    statistics: dict[str, Any] = Field(default_factory=dict)
    evidence: list[str] = Field(default_factory=list)
    countermeasures: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class CountermeasureProtocol(BaseModel):
    """Report-only judge countermeasure protocol."""

    protocol_id: str
    title: str
    steps: list[str]
    applies_to: list[BiasId]
    status: Literal["recommended", "future-experiment", "guardrail-only"]
    notes: list[str] = Field(default_factory=list)


class JudgeBiasReport(BaseModel):
    """Top-level Task 201 judge bias report."""

    generated_at: str
    sample_set: str
    annotations: str
    excellence_report: str
    style_card_report: str
    voice_anchor_report: str
    report_only: bool = True
    boundaries: list[str]
    summary: dict[str, Any]
    score_deltas: list[ScoreDelta]
    evidence_fidelity: list[EvidenceFidelitySummary]
    findings: list[BiasFinding]
    protocols: list[CountermeasureProtocol]


def load_judge_bias_inputs(
    sample_set_path: Path,
    annotations_path: Path,
    excellence_report_path: Path,
    style_card_report_path: Path,
    voice_anchor_report_path: Path,
) -> tuple[
    list[LoadedChapter],
    list[AnnotationRecord],
    ExcellenceSignalReport,
    StyleCardReport,
    VoiceAnchorReport,
]:
    """Load Task 196/197/198/199/200 report-only artifacts."""
    try:
        chapters, _annotations_by_version = load_task196_inputs(
            sample_set_path, annotations_path
        )
    except Exception as exc:
        raise JudgeBiasError(f"failed to load Task 196 inputs: {exc}") from exc
    return (
        chapters,
        _load_annotations(annotations_path),
        _load_model(excellence_report_path, ExcellenceSignalReport),
        _load_model(style_card_report_path, StyleCardReport),
        _load_model(voice_anchor_report_path, VoiceAnchorReport),
    )


def build_judge_bias_report(
    chapters: list[LoadedChapter],
    annotations: list[AnnotationRecord],
    excellence_report: ExcellenceSignalReport,
    style_card_report: StyleCardReport,
    voice_anchor_report: VoiceAnchorReport,
    *,
    sample_set_path: Path,
    annotations_path: Path,
    excellence_report_path: Path,
    style_card_report_path: Path,
    voice_anchor_report_path: Path,
) -> JudgeBiasReport:
    """Build Task 201 report-only judge bias report."""
    content_by_version = {chapter.version_id: chapter.content for chapter in chapters}
    truth_records = _truth_records(annotations)
    prelabels = _prelabel_records(annotations)
    deltas = _score_deltas(truth_records, prelabels)
    evidence_fidelity = _evidence_fidelity(annotations, content_by_version)
    report_by_version = {
        chapter.version_id: chapter for chapter in excellence_report.chapters
    }
    findings = _build_findings(
        truth_records,
        prelabels,
        deltas,
        evidence_fidelity,
        report_by_version,
        style_card_report,
        voice_anchor_report,
    )
    return JudgeBiasReport(
        generated_at=datetime.now(UTC).isoformat(),
        sample_set=sample_set_path.as_posix(),
        annotations=annotations_path.as_posix(),
        excellence_report=excellence_report_path.as_posix(),
        style_card_report=style_card_report_path.as_posix(),
        voice_anchor_report=voice_anchor_report_path.as_posix(),
        boundaries=[
            "report-only / observe-only",
            "does not call LLM judges",
            "does not treat prelabel scores as truth",
            "does not modify Writer or CreativeDirector prompts",
            "does not enter accept/reject gates",
            "does not change CED, five-gate, segment audit, or T9",
        ],
        summary=_summary(truth_records, prelabels, deltas, findings, evidence_fidelity),
        score_deltas=deltas,
        evidence_fidelity=evidence_fidelity,
        findings=findings,
        protocols=_protocols(),
    )


def render_judge_bias_report(report: JudgeBiasReport) -> str:
    """Render Task 201 judge bias report as Markdown."""
    lines = [
        "# Task 201 Judge 偏差对策报告",
        "",
        f"> generated_at: `{report.generated_at}`",
        f"> sample_set: `{report.sample_set}`",
        f"> annotations: `{report.annotations}`",
        f"> excellence_report: `{report.excellence_report}`",
        f"> style_card_report: `{report.style_card_report}`",
        f"> voice_anchor_report: `{report.voice_anchor_report}`",
        "",
        "## 边界",
        "",
    ]
    lines.extend(f"- {item}" for item in report.boundaries)
    lines.extend(["", "## 总览", ""])
    for key, value in report.summary.items():
        lines.append(f"- {key}: `{value}`")

    lines.extend(["", "## Score Delta（prelabel - truth）", ""])
    lines.append("| dimension | count | positive | negative | zero | mean_delta | major_delta>=2 |")
    lines.append("|-----------|------:|---------:|---------:|-----:|-----------:|---------------:|")
    for dim in DIMENSIONS:
        rows = [delta for delta in report.score_deltas if delta.dimension == dim]
        if not rows:
            continue
        lines.append(
            f"| {dim} | {len(rows)} | {sum(1 for r in rows if r.delta > 0)} | "
            f"{sum(1 for r in rows if r.delta < 0)} | "
            f"{sum(1 for r in rows if r.delta == 0)} | "
            f"{mean([r.delta for r in rows]):.2f} | "
            f"{sum(1 for r in rows if r.delta >= 2)} |"
        )

    lines.extend(["", "## Evidence Fidelity", ""])
    lines.append("| layer | quote_count | verbatim_count | fidelity | examples |")
    lines.append("|-------|------------:|---------------:|---------:|----------|")
    for item in report.evidence_fidelity:
        ratio = "-" if item.fidelity_ratio is None else f"{item.fidelity_ratio:.3f}"
        examples = "<br>".join(_shorten(example, 70) for example in item.bad_examples[:3])
        lines.append(
            f"| {item.layer} | {item.quote_count} | {item.verbatim_count} | "
            f"{ratio} | {examples or '-'} |"
        )

    lines.extend(["", "## Bias Findings", ""])
    for finding in report.findings:
        lines.extend(
            [
                f"### {finding.bias_id}",
                "",
                f"- status: `{finding.status}`",
                f"- definition: {finding.definition}",
                "- statistics:",
            ]
        )
        for key, value in finding.statistics.items():
            lines.append(f"  - {key}: `{value}`")
        if finding.evidence:
            lines.append("- evidence:")
            lines.extend(f"  - {item}" for item in finding.evidence[:6])
        if finding.countermeasures:
            lines.append("- countermeasures:")
            lines.extend(f"  - {item}" for item in finding.countermeasures)
        if finding.limitations:
            lines.append("- limitations:")
            lines.extend(f"  - {item}" for item in finding.limitations)
        lines.append("")

    lines.extend(["## Countermeasure Protocol", ""])
    for protocol in report.protocols:
        lines.extend(
            [
                f"### {protocol.protocol_id}: {protocol.title}",
                "",
                f"- status: `{protocol.status}`",
                f"- applies_to: {', '.join(protocol.applies_to)}",
                "- steps:",
            ]
        )
        lines.extend(f"  - {step}" for step in protocol.steps)
        if protocol.notes:
            lines.append("- notes:")
            lines.extend(f"  - {note}" for note in protocol.notes)
        lines.append("")

    lines.extend(
        [
            "## 局限",
            "",
            "- 本报告只使用 Task 196 的 24 章 agent-deep-read 真值做方向性分析。",
            "- 未调用新 judge，不声明 judge v2 已改善。",
            "- 所有对策均为协议建议；任何接入 prompt 或 gate 的尝试必须另立任务。",
        ]
    )
    return "\n".join(lines) + "\n"


def _truth_records(
    annotations: list[AnnotationRecord],
) -> dict[str, AnnotationRecord]:
    return {
        record.version_id: record
        for record in annotations
        if record.annotator == "agent-deep-read"
        and record.sample_layer in {"anchor", "spotcheck"}
    }


def _prelabel_records(
    annotations: list[AnnotationRecord],
) -> dict[str, AnnotationRecord]:
    return {
        record.version_id: record
        for record in annotations
        if record.sample_layer == "prelabel"
    }


def _score_deltas(
    truth_records: dict[str, AnnotationRecord],
    prelabels: dict[str, AnnotationRecord],
) -> list[ScoreDelta]:
    deltas: list[ScoreDelta] = []
    for version_id, truth in sorted(truth_records.items(), key=lambda item: item[1].chapter):
        prelabel = prelabels.get(version_id)
        if prelabel is None:
            continue
        truth_scores = truth.scores.model_dump(mode="json")
        pre_scores = prelabel.scores.model_dump(mode="json")
        for dimension in DIMENSIONS:
            deltas.append(
                ScoreDelta(
                    genre=truth.genre,
                    chapter=truth.chapter,
                    dimension=dimension,
                    prelabel=int(pre_scores[dimension]),
                    truth=int(truth_scores[dimension]),
                    delta=int(pre_scores[dimension]) - int(truth_scores[dimension]),
                )
            )
    return deltas


def _evidence_fidelity(
    annotations: list[AnnotationRecord],
    content_by_version: dict[str, str],
) -> list[EvidenceFidelitySummary]:
    by_layer: dict[str, list[tuple[str, str, int]]] = defaultdict(list)
    for record in annotations:
        version_id = record.version_id
        content = content_by_version.get(version_id, "")
        for quote in record.evidence_quotes:
            by_layer[record.sample_layer].append((version_id, quote, record.chapter))
    summaries: list[EvidenceFidelitySummary] = []
    for layer, rows in sorted(by_layer.items()):
        verbatim = 0
        bad_examples: list[str] = []
        for version_id, quote, chapter in rows:
            content = content_by_version.get(version_id, "")
            if _quote_in_content(quote, content):
                verbatim += 1
            else:
                bad_examples.append(f"Ch{chapter}: {quote}")
        summaries.append(
            EvidenceFidelitySummary(
                layer=layer,
                quote_count=len(rows),
                verbatim_count=verbatim,
                fidelity_ratio=round(verbatim / len(rows), 3) if rows else None,
                bad_examples=bad_examples[:8],
            )
        )
    return summaries


def _build_findings(
    truth_records: dict[str, AnnotationRecord],
    prelabels: dict[str, AnnotationRecord],
    deltas: list[ScoreDelta],
    evidence_fidelity: list[EvidenceFidelitySummary],
    report_by_version: dict[str, ChapterSignalReport],
    style_card_report: StyleCardReport,
    voice_anchor_report: VoiceAnchorReport,
) -> list[BiasFinding]:
    return [
        _leniency_bias(deltas),
        _low_score_blindness(truth_records, prelabels),
        _evidence_drift(evidence_fidelity),
        _engineering_blindness(truth_records, prelabels, report_by_version),
        _style_quality_confusion(truth_records, report_by_version, style_card_report),
        _voice_homogeneity_blindness(deltas, voice_anchor_report),
    ]


def _leniency_bias(deltas: list[ScoreDelta]) -> BiasFinding:
    positive = sum(1 for delta in deltas if delta.delta > 0)
    negative = sum(1 for delta in deltas if delta.delta < 0)
    major = sum(1 for delta in deltas if delta.delta >= 2)
    mean_delta = round(mean([delta.delta for delta in deltas]), 3) if deltas else 0.0
    return BiasFinding(
        bias_id="leniency_bias",
        definition="LLM prelabel scores are systematically higher than agent-deep-read truth.",
        status="supported" if positive > negative and major else "partial",
        statistics={
            "compared_dimensions": len(deltas),
            "positive_delta": positive,
            "negative_delta": negative,
            "major_delta_ge_2": major,
            "mean_delta": mean_delta,
        },
        evidence=[
            f"{delta.genre} Ch{delta.chapter} {delta.dimension}: "
            f"prelabel={delta.prelabel}, truth={delta.truth}"
            for delta in deltas
            if delta.delta >= 2
        ][:8],
        countermeasures=[
            "anchor_example_injection",
            "prelabel_downweighting",
            "blind_review_protocol",
        ],
    )


def _low_score_blindness(
    truth_records: dict[str, AnnotationRecord],
    prelabels: dict[str, AnnotationRecord],
) -> BiasFinding:
    prelabel_scores = [
        score
        for record in prelabels.values()
        for score in record.scores.model_dump(mode="json").values()
    ]
    truth_scores = [
        score
        for record in truth_records.values()
        for score in record.scores.model_dump(mode="json").values()
    ]
    prelabel_low = sum(1 for score in prelabel_scores if score <= 2)
    truth_low = sum(1 for score in truth_scores if score <= 2)
    blind_spot = [
        record
        for version_id, record in truth_records.items()
        if record.scores.overall <= 2
        and (version_id not in prelabels or prelabels[version_id].scores.overall >= 4)
    ]
    return BiasFinding(
        bias_id="low_score_blindness",
        definition="The judge avoids or misses the low-score region proven by deep-read labels.",
        status="supported" if prelabel_low == 0 and truth_low > 0 else "partial",
        statistics={
            "prelabel_low_scores_le_2": prelabel_low,
            "truth_low_scores_le_2": truth_low,
            "truth_records": len(truth_records),
            "blind_spot_chapters": len(blind_spot),
        },
        evidence=[f"{record.genre} Ch{record.chapter} truth overall={record.scores.overall}"
                  for record in blind_spot[:8]],
        countermeasures=[
            "force_1_2_score_examples",
            "require_low_score_checklist_before_scoring",
        ],
    )


def _evidence_drift(evidence_fidelity: list[EvidenceFidelitySummary]) -> BiasFinding:
    prelabel = next((item for item in evidence_fidelity if item.layer == "prelabel"), None)
    ratio = prelabel.fidelity_ratio if prelabel else None
    status: Literal["supported", "partial", "negative"]
    if ratio is None:
        status = "negative"
    elif ratio < 0.9:
        status = "supported"
    else:
        status = "partial"
    return BiasFinding(
        bias_id="evidence_drift",
        definition=(
            "Judge evidence quotes may be paraphrased, stitched, "
            "or absent from accepted prose."
        ),
        status=status,
        statistics={
            "prelabel_quote_count": prelabel.quote_count if prelabel else 0,
            "prelabel_verbatim_count": prelabel.verbatim_count if prelabel else 0,
            "prelabel_fidelity_ratio": ratio,
        },
        evidence=(prelabel.bad_examples if prelabel else [])[:8],
        countermeasures=[
            "verbatim_evidence_check",
            "reject_or_downweight_non_verbatim_quotes",
        ],
    )


def _engineering_blindness(
    truth_records: dict[str, AnnotationRecord],
    prelabels: dict[str, AnnotationRecord],
    report_by_version: dict[str, ChapterSignalReport],
) -> BiasFinding:
    explained = []
    missed = []
    for version_id, truth in truth_records.items():
        report = report_by_version.get(version_id)
        if report is None:
            continue
        signals = {hit.signal_id for hit in report.hits}
        has_engineering = bool(signals & ENGINEERING_SIGNALS)
        prelabel = prelabels.get(version_id)
        prelabel_high = prelabel is not None and (
            prelabel.scores.ai_tone >= 4 or prelabel.scores.overall >= 4
        )
        if has_engineering and truth.scores.ai_tone <= 2:
            signal_text = ", ".join(sorted(signals & ENGINEERING_SIGNALS))
            label = f"{truth.genre} Ch{truth.chapter}: {signal_text}"
            if prelabel_high:
                missed.append(label)
            explained.append(label)
    return BiasFinding(
        bias_id="engineering_artifact_blindness",
        definition=(
            "Judge misses generated/procedural artifacts such as "
            "self-reference and residue."
        ),
        status="supported" if explained else "negative",
        statistics={
            "truth_low_ai_tone_with_engineering_signal": len(explained),
            "prelabel_high_despite_engineering_signal": len(missed),
        },
        evidence=(missed or explained)[:8],
        countermeasures=[
            "mandatory_engineering_artifact_checklist",
            "consume_task198_hard_evidence_as_report_context",
        ],
    )


def _style_quality_confusion(
    truth_records: dict[str, AnnotationRecord],
    report_by_version: dict[str, ChapterSignalReport],
    style_card_report: StyleCardReport,
) -> BiasFinding:
    strong_with_style_risk = []
    for version_id, truth in truth_records.items():
        report = report_by_version.get(version_id)
        if report is None or truth.scores.overall < 4:
            continue
        risks = [hit.signal_id for hit in report.hits if hit.signal_id in STYLE_RISK_SIGNALS]
        if risks:
            strong_with_style_risk.append(
                f"{truth.genre} Ch{truth.chapter}: {', '.join(sorted(set(risks)))}"
            )
    style_cards = len(style_card_report.cards)
    return BiasFinding(
        bias_id="style_vs_quality_confusion",
        definition=(
            "Observed style traits and repeated style risks are not "
            "equivalent to quality defects."
        ),
        status="supported" if strong_with_style_risk else "partial",
        statistics={
            "style_cards": style_cards,
            "strong_truth_records_with_style_risks": len(strong_with_style_risk),
            "report_only": style_card_report.report_only,
        },
        evidence=strong_with_style_risk[:8],
        countermeasures=[
            "separate_style_profile_from_quality_score",
            "label_style_card_as_observation_only",
        ],
        limitations=["Style card does not produce per-chapter quality truth."],
    )


def _voice_homogeneity_blindness(
    deltas: list[ScoreDelta],
    voice_anchor_report: VoiceAnchorReport,
) -> BiasFinding:
    ai_tone_major = [
        delta for delta in deltas
        if delta.dimension == "ai_tone" and delta.delta >= 2
    ]
    all_unknown = next(
        (item for item in voice_anchor_report.unknown_attribution if item.scope == "all"),
        None,
    )
    all_sanity = next(
        (item for item in voice_anchor_report.sanity_checks if item.scope == "all"),
        None,
    )
    return BiasFinding(
        bias_id="voice_homogeneity_blindness",
        definition="Judge under-detects dialogue voice sameness and attribution uncertainty.",
        status="supported" if ai_tone_major and all_sanity else "partial",
        statistics={
            "ai_tone_major_delta_ge_2": len(ai_tone_major),
            "voice_anchor_count": len(voice_anchor_report.anchors),
            "unknown_attribution_ratio_all": all_unknown.ratio if all_unknown else None,
            "weak_with_voice_evidence": all_sanity.weak_with_voice_evidence if all_sanity else None,
            "weak_samples": all_sanity.weak_samples if all_sanity else None,
        },
        evidence=[
            f"{delta.genre} Ch{delta.chapter}: "
            f"ai_tone prelabel={delta.prelabel}, truth={delta.truth}"
            for delta in ai_tone_major[:8]
        ],
        countermeasures=[
            "voice_homogeneity_checklist",
            "unknown_attribution_warning",
            "do_not_convert_voice_report_to_dialogue_style_card",
        ],
    )


def _summary(
    truth_records: dict[str, AnnotationRecord],
    prelabels: dict[str, AnnotationRecord],
    deltas: list[ScoreDelta],
    findings: list[BiasFinding],
    evidence_fidelity: list[EvidenceFidelitySummary],
) -> dict[str, Any]:
    prelabel = next((item for item in evidence_fidelity if item.layer == "prelabel"), None)
    return {
        "truth_records": len(truth_records),
        "prelabel_records": len(prelabels),
        "paired_spotcheck_records": len({(d.genre, d.chapter) for d in deltas}),
        "major_deltas_ge_2": sum(1 for delta in deltas if delta.delta >= 2),
        "supported_biases": sum(1 for item in findings if item.status == "supported"),
        "prelabel_evidence_fidelity": prelabel.fidelity_ratio if prelabel else None,
    }


def _protocols() -> list[CountermeasureProtocol]:
    return [
        CountermeasureProtocol(
            protocol_id="anchor_example_injection",
            title="Anchor examples for judge calibration",
            status="recommended",
            applies_to=["leniency_bias", "low_score_blindness"],
            steps=[
                "Use Task 196 strong/weak anchor examples as rubric references.",
                "Include at least one overall=2 and one ai_tone=1 example in offline judge trials.",
                "Keep examples outside Writer / CreativeDirector prompts "
                "unless separately approved.",
            ],
            notes=["Protocol only; Task 201 does not add or run a new prompt card."],
        ),
        CountermeasureProtocol(
            protocol_id="forced_checklist",
            title="Mandatory artifact/style/voice checklist",
            status="recommended",
            applies_to=[
                "engineering_artifact_blindness",
                "style_vs_quality_confusion",
                "voice_homogeneity_blindness",
            ],
            steps=[
                "Before scoring ai_tone, check Task 198 engineering artifact classes.",
                "Before scoring homogeneity, inspect Task 197 structure risks.",
                "Before scoring voice, inspect Task 200 unknown attribution and voice anchors.",
            ],
        ),
        CountermeasureProtocol(
            protocol_id="verbatim_evidence_check",
            title="Evidence quote verification",
            status="guardrail-only",
            applies_to=["evidence_drift"],
            steps=[
                "Every evidence quote must be searched in accepted prose.",
                "Non-verbatim evidence is rejected or clearly downweighted.",
                "No automatic revision may consume non-verbatim judge evidence.",
            ],
        ),
        CountermeasureProtocol(
            protocol_id="prelabel_downweighting",
            title="Prelabel is comparison-only",
            status="recommended",
            applies_to=["leniency_bias", "low_score_blindness"],
            steps=[
                "Do not use prelabel scores as truth labels.",
                "Use prelabel only for broad coverage and disagreement discovery.",
                "Task 203 should display prelabel as low-confidence context.",
            ],
        ),
        CountermeasureProtocol(
            protocol_id="blind_review_protocol",
            title="Future multi-judge blind review",
            status="future-experiment",
            applies_to=["leniency_bias", "low_score_blindness"],
            steps=[
                "Run multiple judge cards on the same anchor + spotcheck set.",
                "Hide provenance labels during scoring.",
                "Report inter-judge variance and do not convert aggregate score into a gate.",
            ],
            notes=["Not executed in Task 201."],
        ),
        CountermeasureProtocol(
            protocol_id="goodhart_guardrail",
            title="Goodhart risk statement",
            status="guardrail-only",
            applies_to=[
                "leniency_bias",
                "style_vs_quality_confusion",
                "voice_homogeneity_blindness",
            ],
            steps=[
                "Do not optimize generation directly against judge scores.",
                "Separate observation reports from acceptance criteria.",
                "Any future gate proposal requires separate calibration and regression.",
            ],
        ),
    ]


def _quote_in_content(quote: str, content: str) -> bool:
    if not quote:
        return False
    if quote in content:
        return True
    return _normalize(quote) in _normalize(content)


def _normalize(value: str) -> str:
    return re.sub(r"\s+", "", value)


def _load_model(path: Path, model_type: Any) -> Any:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise JudgeBiasError(f"failed to read {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise JudgeBiasError(f"expected JSON object: {path}")
    return model_type.model_validate(raw)


def _load_annotations(path: Path) -> list[AnnotationRecord]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise JudgeBiasError(f"failed to read {path}: {exc}") from exc
    if not isinstance(raw, dict) or not isinstance(raw.get("annotations"), list):
        raise JudgeBiasError(f"expected annotations list: {path}")
    return [
        AnnotationRecord.model_validate(item)
        for item in raw["annotations"]
        if isinstance(item, dict)
    ]


def _shorten(text: str, limit: int) -> str:
    collapsed = re.sub(r"\s+", " ", text.strip())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[:limit - 1] + "…"
