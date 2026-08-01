"""Task 203 integrated excellence report.

The report is an offline, report-only integration over Task 197-202 artifacts.
It does not call LLMs, does not write SQLite, does not join ``songyan report``,
and does not affect Writer / CreativeDirector prompts, CED, five-gate,
segment audit, T9, or any runtime gate.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from songyan.evals.excellence_sampling import AnnotationRecord
from songyan.evals.excellence_signals import (
    CalibrationSummary,
    ChapterSignalReport,
    ExcellenceSignalReport,
    SignalHit,
)
from songyan.evals.judge_bias_analysis import JudgeBiasReport
from songyan.evals.readability_feasibility import (
    ReadabilityFeasibilityReport,
)
from songyan.evals.style_card_extraction import StyleCardReport
from songyan.evals.voice_anchor_extraction import (
    UnknownAttributionSummary,
    VoiceAnchorObservation,
    VoiceAnchorReport,
)

LayerId = Literal["structure", "ai_tone", "style", "voice", "judge_bias", "readability"]
ArtifactType = Literal["calibration_data", "report"]
AdoptionStatus = Literal["report-only", "defer", "future-experiment", "guardrail-only"]

PROHIBITED_KEYS = {
    "excellence_total_score",
    "rank",
    "ranking",
    "pass_fail",
    "passfail",
    "hard_verdict",
}


class ExcellenceIntegrationError(RuntimeError):
    """Raised when Task 203 inputs are missing or invalid."""


class SourceArtifact(BaseModel):
    """Traceable input artifact."""

    task_id: str
    path: str
    artifact_type: ArtifactType
    generated_at: str | None = None
    report_only: bool | None = None
    notes: list[str] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)


class EvidenceSummary(BaseModel):
    """Compact evidence reference carried into the integrated report."""

    source_task: str
    layer: LayerId
    signal_id: str
    label: str
    genre: str | None = None
    chapter: int | None = Field(default=None, ge=1)
    severity: str | None = None
    location: str = ""
    quote: str = ""
    detail: str = ""


class ChapterLayerEntry(BaseModel):
    """One report-only layer inside a chapter view."""

    layer: LayerId
    signal_count: int
    signals: list[str] = Field(default_factory=list)
    evidence: list[EvidenceSummary] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ChapterIndexEntry(BaseModel):
    """Chapter-oriented integrated view."""

    genre: str
    chapter: int = Field(ge=1)
    version_id: str
    calibration_layer: str | None = None
    calibration_source: str | None = None
    layers: dict[LayerId, ChapterLayerEntry] = Field(default_factory=dict)
    confidence_notes: list[str] = Field(default_factory=list)


class SignalIndexEntry(BaseModel):
    """Signal-oriented integrated view."""

    layer: LayerId
    signal_id: str
    label: str
    source_task: str
    adoption_status: AdoptionStatus
    chapter_count: int = 0
    evidence_count: int = 0
    calibration: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    examples: list[EvidenceSummary] = Field(default_factory=list)


class SignalLayerSummary(BaseModel):
    """Layer-level summary for Task 203."""

    layer: LayerId
    source_tasks: list[str]
    adoption_status: AdoptionStatus
    signal_count: int
    chapter_count: int
    confidence_notes: list[str] = Field(default_factory=list)


class CalibrationTruthSummary(BaseModel):
    """Task 196 truth contract."""

    truth_source: str
    truth_records: int
    anchor_records: int
    spotcheck_records: int
    prelabel_records: int
    prelabel_usage: str
    notes: list[str] = Field(default_factory=list)


class ConfidenceNote(BaseModel):
    """Known confidence boundary from upstream tasks."""

    source_task: str
    layer: LayerId
    note: str


class Task203Summary(BaseModel):
    """Top-level summary without hard scoring."""

    report_only: bool = True
    source_artifact_count: int
    chapter_view_count: int
    signal_view_count: int
    hard_quality_gate_policy: str
    no_hard_score_policy: str
    next_route: str


class IntegratedExcellenceReport(BaseModel):
    """Top-level Task 203 report."""

    generated_at: str
    report_only: bool = True
    boundaries: list[str]
    task203_summary: Task203Summary
    source_artifacts: list[SourceArtifact]
    calibration_truth: CalibrationTruthSummary
    signal_layers: list[SignalLayerSummary]
    confidence_notes: list[ConfidenceNote]
    chapter_index: list[ChapterIndexEntry]
    signal_index: list[SignalIndexEntry]


class IntegrationInputs(BaseModel):
    """Loaded Task 203 inputs."""

    sample_set: dict[str, Any]
    annotations: list[AnnotationRecord]
    excellence_report: ExcellenceSignalReport
    style_report: StyleCardReport
    voice_report: VoiceAnchorReport
    judge_report: JudgeBiasReport
    readability_report: ReadabilityFeasibilityReport

    model_config = {"arbitrary_types_allowed": True}


def load_integration_inputs(
    *,
    sample_set_path: Path,
    annotations_path: Path,
    excellence_report_path: Path,
    style_card_report_path: Path,
    voice_anchor_report_path: Path,
    judge_bias_report_path: Path,
    readability_report_path: Path,
) -> IntegrationInputs:
    """Load and validate Task 196-202 artifacts."""
    sample_set = _load_json_object(sample_set_path)
    annotations = _load_annotations(annotations_path)
    excellence = _load_report(
        excellence_report_path,
        ExcellenceSignalReport,
        task_id="197/198",
    )
    style = _load_report(style_card_report_path, StyleCardReport, task_id="199")
    voice = _load_report(voice_anchor_report_path, VoiceAnchorReport, task_id="200")
    judge = _load_report(judge_bias_report_path, JudgeBiasReport, task_id="201")
    readability = _load_report(
        readability_report_path,
        ReadabilityFeasibilityReport,
        task_id="202",
    )
    return IntegrationInputs(
        sample_set=sample_set,
        annotations=annotations,
        excellence_report=excellence,
        style_report=style,
        voice_report=voice,
        judge_report=judge,
        readability_report=readability,
    )


def build_integrated_excellence_report(
    inputs: IntegrationInputs,
    *,
    sample_set_path: Path,
    annotations_path: Path,
    excellence_report_path: Path,
    style_card_report_path: Path,
    voice_anchor_report_path: Path,
    judge_bias_report_path: Path,
    readability_report_path: Path,
) -> IntegratedExcellenceReport:
    """Build Task 203 integrated report-only excellence view."""
    truth = _truth_annotations(inputs.annotations)
    prelabels = _prelabel_annotations(inputs.annotations)
    artifacts = _source_artifacts(
        inputs,
        sample_set_path=sample_set_path,
        annotations_path=annotations_path,
        excellence_report_path=excellence_report_path,
        style_card_report_path=style_card_report_path,
        voice_anchor_report_path=voice_anchor_report_path,
        judge_bias_report_path=judge_bias_report_path,
        readability_report_path=readability_report_path,
        truth=truth,
        prelabels=prelabels,
    )
    chapter_index = _build_chapter_index(inputs, truth)
    signal_index = _build_signal_index(inputs)
    signal_layers = _signal_layers(signal_index)
    confidence_notes = _confidence_notes(inputs)
    report = IntegratedExcellenceReport(
        generated_at=datetime.now(UTC).isoformat(),
        boundaries=[
            "report-only / observe-only",
            "standalone offline report; not wired into songyan report",
            "does not call LLMs or regenerate prose",
            "does not write SQLite",
            "does not modify Writer or CreativeDirector prompts",
            "does not enter accept/reject gates",
            "does not change CED, five-gate, segment audit, or T9",
            "does not generate an excellence total score, chapter ordering, or binary verdict",
        ],
        task203_summary=Task203Summary(
            source_artifact_count=len(artifacts),
            chapter_view_count=len(chapter_index),
            signal_view_count=len(signal_index),
            hard_quality_gate_policy=(
                "Ch200 hard gates remain external five-gate / T9 / segment audit facts; "
                "this report only references excellence observations."
            ),
            no_hard_score_policy=(
                "No integrated excellence total score, chapter ordering, "
                "or binary verdict is produced."
            ),
            next_route="Task 204 KG graph diff spike; CLI integration is deferred to Task 207.",
        ),
        source_artifacts=artifacts,
        calibration_truth=_calibration_truth(truth, prelabels),
        signal_layers=signal_layers,
        confidence_notes=confidence_notes,
        chapter_index=chapter_index,
        signal_index=signal_index,
    )
    _assert_no_prohibited_keys(report)
    return report


def render_integrated_excellence_report(report: IntegratedExcellenceReport) -> str:
    """Render Task 203 report as Markdown."""
    lines = [
        "# Task 203 优秀度报告整合",
        "",
        f"> generated_at: `{report.generated_at}`",
        "",
        "## 边界",
        "",
    ]
    lines.extend(f"- {item}" for item in report.boundaries)
    lines.extend(["", "## Summary", ""])
    lines.extend(
        [
            f"- report_only: `{report.task203_summary.report_only}`",
            f"- source_artifact_count: `{report.task203_summary.source_artifact_count}`",
            f"- chapter_view_count: `{report.task203_summary.chapter_view_count}`",
            f"- signal_view_count: `{report.task203_summary.signal_view_count}`",
            f"- hard_quality_gate_policy: {report.task203_summary.hard_quality_gate_policy}",
            f"- no_hard_score_policy: {report.task203_summary.no_hard_score_policy}",
            f"- next_route: {report.task203_summary.next_route}",
        ]
    )
    lines.extend(["", "## Source Artifacts", ""])
    lines.append("| task | type | report_only | generated_at | path |")
    lines.append("|------|------|-------------|--------------|------|")
    for item in report.source_artifacts:
        lines.append(
            f"| {item.task_id} | {item.artifact_type} | {item.report_only} | "
            f"{item.generated_at or '-'} | `{item.path}` |"
        )

    lines.extend(["", "## Calibration Truth", ""])
    truth = report.calibration_truth
    lines.extend(
        [
            f"- truth_source: {truth.truth_source}",
            f"- truth_records: `{truth.truth_records}`",
            f"- anchor_records: `{truth.anchor_records}`",
            f"- spotcheck_records: `{truth.spotcheck_records}`",
            f"- prelabel_records: `{truth.prelabel_records}`",
            f"- prelabel_usage: {truth.prelabel_usage}",
        ]
    )

    lines.extend(["", "## Signal Layers", ""])
    lines.append("| layer | tasks | status | signals | chapters | notes |")
    lines.append("|-------|-------|--------|--------:|---------:|-------|")
    for layer in report.signal_layers:
        lines.append(
            f"| {layer.layer} | {', '.join(layer.source_tasks)} | "
            f"`{layer.adoption_status}` | {layer.signal_count} | {layer.chapter_count} | "
            f"{'<br>'.join(layer.confidence_notes) or '-'} |"
        )

    lines.extend(["", "## Signal View", ""])
    lines.append("| layer | signal | task | status | chapters | evidence | calibration / notes |")
    lines.append("|-------|--------|------|--------|---------:|---------:|---------------------|")
    for item in report.signal_index:
        calibration = _format_mapping(item.calibration)
        limitations = "; ".join(item.limitations[:2])
        notes = calibration or limitations or "-"
        lines.append(
            f"| {item.layer} | `{item.signal_id}` | {item.source_task} | "
            f"`{item.adoption_status}` | {item.chapter_count} | {item.evidence_count} | "
            f"{notes} |"
        )

    lines.extend(["", "## Chapter View", ""])
    lines.append("| genre | chapter | calibration | layers | notes |")
    lines.append("|-------|---------|-------------|--------|-------|")
    for chapter in report.chapter_index:
        layer_bits = []
        for layer, entry in chapter.layers.items():
            if entry.signal_count:
                layer_bits.append(f"{layer}:{entry.signal_count}")
        lines.append(
            f"| {chapter.genre} | {chapter.chapter} | "
            f"{chapter.calibration_layer or '-'} | "
            f"{', '.join(layer_bits) or '-'} | "
            f"{'; '.join(chapter.confidence_notes) or '-'} |"
        )

    lines.extend(["", "## Confidence Notes", ""])
    for note in report.confidence_notes:
        lines.append(f"- **{note.source_task} / {note.layer}**: {note.note}")

    lines.extend(
        [
            "",
            "## 后续路由",
            "",
            "- Task 204: KG 图 diff spike。",
            "- Task 207: 决定是否把本独立报告入口收编到 CLI / `songyan report`。",
            "- 本报告保持 report-only，不成为任何 hard gate 输入。",
        ]
    )
    return "\n".join(lines) + "\n"


def _source_artifacts(
    inputs: IntegrationInputs,
    *,
    sample_set_path: Path,
    annotations_path: Path,
    excellence_report_path: Path,
    style_card_report_path: Path,
    voice_anchor_report_path: Path,
    judge_bias_report_path: Path,
    readability_report_path: Path,
    truth: list[AnnotationRecord],
    prelabels: list[AnnotationRecord],
) -> list[SourceArtifact]:
    return [
        SourceArtifact(
            task_id="196-sample",
            path=sample_set_path.as_posix(),
            artifact_type="calibration_data",
            notes=["Task 196 sample source; not a report artifact."],
            summary={
                "sample_count": len(inputs.sample_set.get("samples", [])),
                "source_count": len(inputs.sample_set.get("sources", [])),
            },
        ),
        SourceArtifact(
            task_id="196-annotations",
            path=annotations_path.as_posix(),
            artifact_type="calibration_data",
            notes=["Only agent-deep-read anchor + spotcheck are calibration truth."],
            summary={
                "truth_records": len(truth),
                "prelabel_records": len(prelabels),
            },
        ),
        _report_artifact("197/198", excellence_report_path, inputs.excellence_report),
        _report_artifact("199", style_card_report_path, inputs.style_report),
        _report_artifact("200", voice_anchor_report_path, inputs.voice_report),
        _report_artifact("201", judge_bias_report_path, inputs.judge_report),
        _report_artifact("202", readability_report_path, inputs.readability_report),
    ]


def _report_artifact(task_id: str, path: Path, report: BaseModel) -> SourceArtifact:
    generated_at = getattr(report, "generated_at", None)
    report_only = getattr(report, "report_only", None)
    return SourceArtifact(
        task_id=task_id,
        path=path.as_posix(),
        artifact_type="report",
        generated_at=generated_at,
        report_only=report_only,
        summary=_compact_report_summary(task_id, report),
    )


def _compact_report_summary(task_id: str, report: BaseModel) -> dict[str, Any]:
    if task_id == "197/198":
        obj = report  # type: ignore[assignment]
        return {
            "chapters": len(getattr(obj, "chapters", [])),
            "calibration": [
                item.model_dump(mode="json") for item in getattr(obj, "calibration", [])
            ],
        }
    if task_id == "199":
        return {"cards": len(getattr(report, "cards", []))}
    if task_id == "200":
        return {
            "anchors": len(getattr(report, "anchors", [])),
            "unknown_attribution": [
                item.model_dump(mode="json")
                for item in getattr(report, "unknown_attribution", [])[:3]
            ],
        }
    if task_id == "201":
        return dict(getattr(report, "summary", {}))
    if task_id == "202":
        return dict(getattr(report, "summaries", {}))
    return {}


def _build_chapter_index(
    inputs: IntegrationInputs,
    truth: list[AnnotationRecord],
) -> list[ChapterIndexEntry]:
    chapter_map: dict[tuple[str, int], ChapterIndexEntry] = {}
    truth_by_version = {record.version_id: record for record in truth}
    for chapter in inputs.excellence_report.chapters:
        record = truth_by_version.get(chapter.version_id)
        chapter_map[(chapter.genre, chapter.chapter)] = ChapterIndexEntry(
            genre=chapter.genre,
            chapter=chapter.chapter,
            version_id=chapter.version_id,
            calibration_layer=record.sample_layer if record else None,
            calibration_source=record.annotator if record else None,
        )
    for chapter in inputs.excellence_report.chapters:
        entry = chapter_map[(chapter.genre, chapter.chapter)]
        for hit in chapter.hits:
            layer: LayerId = "structure" if hit.task == "197" else "ai_tone"
            _add_chapter_evidence(entry, _hit_to_evidence(chapter, hit, layer))
    _add_style_to_chapters(chapter_map, inputs.style_report)
    _add_voice_to_chapters(chapter_map, inputs.voice_report)
    _add_judge_to_chapters(chapter_map, inputs.judge_report)
    _add_readability_to_chapters(chapter_map, inputs.readability_report)
    for entry in chapter_map.values():
        if entry.calibration_layer:
            entry.confidence_notes.append("calibration truth from agent-deep-read")
    return sorted(chapter_map.values(), key=lambda item: (item.genre, item.chapter))


def _add_chapter_evidence(entry: ChapterIndexEntry, evidence: EvidenceSummary) -> None:
    layer_entry = entry.layers.get(evidence.layer)
    if layer_entry is None:
        layer_entry = ChapterLayerEntry(layer=evidence.layer, signal_count=0)
        entry.layers[evidence.layer] = layer_entry
    layer_entry.evidence.append(evidence)
    if evidence.signal_id not in layer_entry.signals:
        layer_entry.signals.append(evidence.signal_id)
    layer_entry.signal_count = len(layer_entry.signals)


def _hit_to_evidence(
    chapter: ChapterSignalReport,
    hit: SignalHit,
    layer: LayerId,
) -> EvidenceSummary:
    source = "197" if hit.task == "197" else "198"
    item = hit.evidence[0] if hit.evidence else None
    return EvidenceSummary(
        source_task=source,
        layer=layer,
        signal_id=hit.signal_id,
        label=hit.label,
        genre=chapter.genre,
        chapter=chapter.chapter,
        severity=hit.severity,
        location=item.location if item else "",
        quote=_shorten(item.quote, 120) if item else "",
        detail=hit.detail or (item.detail if item else ""),
    )


def _add_style_to_chapters(
    chapter_map: dict[tuple[str, int], ChapterIndexEntry],
    report: StyleCardReport,
) -> None:
    for card in report.cards:
        for label in card.source_chapters:
            parsed = _parse_chapter_label(label)
            if parsed is None or parsed not in chapter_map:
                continue
            _add_chapter_evidence(
                chapter_map[parsed],
                EvidenceSummary(
                    source_task="199",
                    layer="style",
                    signal_id=f"style_card:{card.scope}",
                    label="style card scope membership",
                    genre=parsed[0],
                    chapter=parsed[1],
                    detail=card.usage_note,
                ),
            )


def _add_voice_to_chapters(
    chapter_map: dict[tuple[str, int], ChapterIndexEntry],
    report: VoiceAnchorReport,
) -> None:
    for anchor in report.anchors:
        for line in anchor.sample_lines:
            key = (line.genre, line.chapter)
            if key not in chapter_map:
                continue
            _add_chapter_evidence(
                chapter_map[key],
                EvidenceSummary(
                    source_task="200",
                    layer="voice",
                    signal_id="voice_anchor",
                    label=anchor.character_name,
                    genre=line.genre,
                    chapter=line.chapter,
                    location=line.location,
                    quote=_shorten(line.text, 120),
                    detail=f"attribution={line.attribution}",
                ),
            )
    for item in report.unknown_attribution:
        for line in item.sample_lines:
            key = (line.genre, line.chapter)
            if key not in chapter_map:
                continue
            _add_chapter_evidence(
                chapter_map[key],
                EvidenceSummary(
                    source_task="200",
                    layer="voice",
                    signal_id="unknown_attribution",
                    label="unknown attribution",
                    genre=line.genre,
                    chapter=line.chapter,
                    location=line.location,
                    quote=_shorten(line.text, 120),
                    detail="unattributed dialogue preserved",
                ),
            )


def _add_judge_to_chapters(
    chapter_map: dict[tuple[str, int], ChapterIndexEntry],
    report: JudgeBiasReport,
) -> None:
    for finding in report.findings:
        for raw in finding.evidence:
            parsed = _parse_chapter_label(raw)
            if parsed is None or parsed not in chapter_map:
                continue
            _add_chapter_evidence(
                chapter_map[parsed],
                EvidenceSummary(
                    source_task="201",
                    layer="judge_bias",
                    signal_id=finding.bias_id,
                    label=finding.bias_id,
                    genre=parsed[0],
                    chapter=parsed[1],
                    detail=_shorten(raw, 160),
                ),
            )


def _add_readability_to_chapters(
    chapter_map: dict[tuple[str, int], ChapterIndexEntry],
    report: ReadabilityFeasibilityReport,
) -> None:
    for chapter in report.chapters:
        key = (chapter.genre, chapter.chapter)
        if key not in chapter_map:
            continue
        for flag in chapter.risk_flags:
            _add_chapter_evidence(
                chapter_map[key],
                EvidenceSummary(
                    source_task="202",
                    layer="readability",
                    signal_id=flag,
                    label=flag,
                    genre=chapter.genre,
                    chapter=chapter.chapter,
                    detail="readability proxy flag",
                ),
            )


def _build_signal_index(inputs: IntegrationInputs) -> list[SignalIndexEntry]:
    signals: dict[tuple[LayerId, str], SignalIndexEntry] = {}
    calibration_by_task = {
        item.task: item for item in inputs.excellence_report.calibration
    }
    for chapter in inputs.excellence_report.chapters:
        for hit in chapter.hits:
            layer: LayerId = "structure" if hit.task == "197" else "ai_tone"
            key = (layer, hit.signal_id)
            entry = signals.get(key)
            if entry is None:
                entry = SignalIndexEntry(
                    layer=layer,
                    signal_id=hit.signal_id,
                    label=hit.label,
                    source_task="197" if hit.task == "197" else "198",
                    adoption_status="report-only",
                    calibration=_calibration_dict(calibration_by_task.get(hit.task)),
                    limitations=_task197_198_limitations(hit.task),
                )
                signals[key] = entry
            entry.evidence_count += max(1, len(hit.evidence))
            _append_example(
                entry,
                _hit_to_evidence(chapter, hit, layer),
            )
    for entry in signals.values():
        entry.chapter_count = _signal_chapter_count(inputs.excellence_report, entry.signal_id)

    _add_style_signal_index(signals, inputs.style_report)
    _add_voice_signal_index(signals, inputs.voice_report)
    _add_judge_signal_index(signals, inputs.judge_report)
    _add_readability_signal_index(signals, inputs.readability_report)
    return sorted(signals.values(), key=lambda item: (item.layer, item.signal_id))


def _add_style_signal_index(
    signals: dict[tuple[LayerId, str], SignalIndexEntry],
    report: StyleCardReport,
) -> None:
    for card in report.cards:
        key = ("style", f"style_card:{card.scope}")
        signals[key] = SignalIndexEntry(
            layer="style",
            signal_id=key[1],
            label=f"style card {card.scope}",
            source_task="199",
            adoption_status="report-only",
            chapter_count=len(card.source_chapters),
            evidence_count=len(card.anti_patterns),
            calibration={"sanity": _style_sanity(report, card.scope)},
            limitations=[
                "style card is an observed profile, not a prompt constraint",
                "strong samples may still contain style risks",
            ],
            examples=[
                EvidenceSummary(
                    source_task="199",
                    layer="style",
                    signal_id=key[1],
                    label=card.scope,
                    detail=card.usage_note,
                )
            ],
        )
    for card in report.cards:
        for anti in card.anti_patterns:
            key = ("style", f"anti_pattern:{anti.signal_id}")
            entry = signals.get(key)
            if entry is None:
                entry = SignalIndexEntry(
                    layer="style",
                    signal_id=key[1],
                    label=anti.label,
                    source_task="199",
                    adoption_status="report-only",
                    limitations=["anti-patterns are aggregated from Task 197/198 hits"],
                )
                signals[key] = entry
            entry.evidence_count += anti.count
            entry.chapter_count = max(entry.chapter_count, anti.count)
            for example in anti.examples[:2]:
                parsed = _parse_chapter_label(example)
                entry.examples.append(
                    EvidenceSummary(
                        source_task="199",
                        layer="style",
                        signal_id=key[1],
                        label=anti.label,
                        genre=parsed[0] if parsed else None,
                        chapter=parsed[1] if parsed else None,
                        detail=_shorten(example, 160),
                    )
                )


def _add_voice_signal_index(
    signals: dict[tuple[LayerId, str], SignalIndexEntry],
    report: VoiceAnchorReport,
) -> None:
    voice_key = ("voice", "voice_anchor")
    all_anchor_chapters = {
        (line.genre, line.chapter)
        for anchor in report.anchors
        for line in anchor.sample_lines
    }
    signals[voice_key] = SignalIndexEntry(
        layer="voice",
        signal_id="voice_anchor",
        label="character voice anchors",
        source_task="200",
        adoption_status="report-only",
        chapter_count=len(all_anchor_chapters),
        evidence_count=sum(len(anchor.sample_lines) for anchor in report.anchors),
        calibration={"sanity": [item.model_dump(mode="json") for item in report.sanity_checks]},
        limitations=[
            "speaker attribution is heuristic",
            "not DialogueStyleCard and not written back to character profiles",
        ],
        examples=_voice_examples(report.anchors),
    )
    unknown = next(
        (item for item in report.unknown_attribution if item.scope == "all"),
        None,
    )
    unknown_chapters = {
        (line.genre, line.chapter)
        for line in (unknown.sample_lines if unknown else [])
    }
    signals[("voice", "unknown_attribution")] = SignalIndexEntry(
        layer="voice",
        signal_id="unknown_attribution",
        label="unknown dialogue attribution",
        source_task="200",
        adoption_status="report-only",
        chapter_count=len(unknown_chapters),
        evidence_count=unknown.line_count if unknown else 0,
        calibration={"ratio": unknown.ratio if unknown else None},
        limitations=["unknown is preserved instead of fabricated"],
        examples=_unknown_examples(unknown),
    )


def _add_judge_signal_index(
    signals: dict[tuple[LayerId, str], SignalIndexEntry],
    report: JudgeBiasReport,
) -> None:
    for finding in report.findings:
        key = ("judge_bias", finding.bias_id)
        parsed_chapters = {
            parsed for raw in finding.evidence
            if (parsed := _parse_chapter_label(raw)) is not None
        }
        signals[key] = SignalIndexEntry(
            layer="judge_bias",
            signal_id=finding.bias_id,
            label=finding.definition,
            source_task="201",
            adoption_status=(
                "future-experiment"
                if finding.status == "negative"
                else "report-only"
            ),
            chapter_count=len(parsed_chapters),
            evidence_count=len(finding.evidence),
            calibration=finding.statistics,
            limitations=finding.limitations or ["protocol output; not judge v2"],
            examples=[
                EvidenceSummary(
                    source_task="201",
                    layer="judge_bias",
                    signal_id=finding.bias_id,
                    label=finding.bias_id,
                    genre=parsed[0] if (parsed := _parse_chapter_label(raw)) else None,
                    chapter=parsed[1] if parsed else None,
                    detail=_shorten(raw, 160),
                )
                for raw in finding.evidence[:4]
            ],
        )


def _add_readability_signal_index(
    signals: dict[tuple[LayerId, str], SignalIndexEntry],
    report: ReadabilityFeasibilityReport,
) -> None:
    decision_by_signal = {item.signal_id: item for item in report.decisions}
    flag_counter: Counter[str] = Counter()
    flag_chapters: dict[str, set[tuple[str, int]]] = defaultdict(set)
    for chapter in report.chapters:
        for flag in chapter.risk_flags:
            flag_counter[flag] += 1
            flag_chapters[flag].add((chapter.genre, chapter.chapter))
    for signal_id, decision in decision_by_signal.items():
        key = ("readability", signal_id)
        signals[key] = SignalIndexEntry(
            layer="readability",
            signal_id=signal_id,
            label=decision.definition,
            source_task="202",
            adoption_status=decision.decision,
            chapter_count=int(decision.sample_summary.get("chapters_with_signal", 0) or 0),
            evidence_count=int(decision.sample_summary.get("chapters_with_signal", 0) or 0),
            calibration=decision.sample_summary,
            limitations=decision.limitations,
            examples=[
                EvidenceSummary(
                    source_task="202",
                    layer="readability",
                    signal_id=signal_id,
                    label=signal_id,
                    detail=_shorten(example, 160),
                )
                for example in decision.evidence[:4]
            ],
        )
    for flag, count in flag_counter.items():
        key = ("readability", f"flag:{flag}")
        signals[key] = SignalIndexEntry(
            layer="readability",
            signal_id=key[1],
            label=flag,
            source_task="202",
            adoption_status="report-only",
            chapter_count=len(flag_chapters[flag]),
            evidence_count=count,
            limitations=["readability proxy flag; not a quality defect by itself"],
        )


def _signal_layers(signal_index: list[SignalIndexEntry]) -> list[SignalLayerSummary]:
    by_layer: dict[LayerId, list[SignalIndexEntry]] = defaultdict(list)
    for item in signal_index:
        by_layer[item.layer].append(item)
    notes = {
        "structure": ["Task 197 precision=0.40, recall=0.80"],
        "ai_tone": ["Task 198 precision=0.65, recall=1.00"],
        "style": ["style card is observation-only"],
        "voice": ["unknown attribution ratio remains material"],
        "judge_bias": ["protocol output, not an online judge improvement"],
        "readability": ["true perplexity deferred; proxy false positives expected"],
    }
    source_tasks = {
        "structure": ["197"],
        "ai_tone": ["198"],
        "style": ["199"],
        "voice": ["200"],
        "judge_bias": ["201"],
        "readability": ["202"],
    }
    out: list[SignalLayerSummary] = []
    for layer in ("structure", "ai_tone", "style", "voice", "judge_bias", "readability"):
        items = by_layer.get(layer, [])
        statuses = {item.adoption_status for item in items}
        status: AdoptionStatus = "defer" if statuses == {"defer"} else "report-only"
        out.append(
            SignalLayerSummary(
                layer=layer,
                source_tasks=source_tasks[layer],
                adoption_status=status,
                signal_count=len(items),
                chapter_count=max((item.chapter_count for item in items), default=0),
                confidence_notes=notes[layer],
            )
        )
    return out


def _calibration_truth(
    truth: list[AnnotationRecord],
    prelabels: list[AnnotationRecord],
) -> CalibrationTruthSummary:
    anchor = sum(1 for item in truth if item.sample_layer == "anchor")
    spotcheck = sum(1 for item in truth if item.sample_layer == "spotcheck")
    return CalibrationTruthSummary(
        truth_source="Task 196 anchor + spotcheck agent-deep-read",
        truth_records=len(truth),
        anchor_records=anchor,
        spotcheck_records=spotcheck,
        prelabel_records=len(prelabels),
        prelabel_usage="low-confidence comparison only; never calibration truth",
        notes=[
            "Task 196 prelabel evidence fidelity is lower than agent-deep-read.",
            "Precision/recall in this report refers to upstream offline calibration only.",
        ],
    )


def _confidence_notes(inputs: IntegrationInputs) -> list[ConfidenceNote]:
    notes: list[ConfidenceNote] = []
    for cal in inputs.excellence_report.calibration:
        layer: LayerId = "structure" if cal.task == "197" else "ai_tone"
        notes.append(
            ConfidenceNote(
                source_task=cal.task,
                layer=layer,
                note=(
                    f"precision={cal.precision}, recall={cal.recall}; "
                    f"truth_rule={cal.truth_rule}"
                ),
            )
        )
    unknown = next(
        (item for item in inputs.voice_report.unknown_attribution if item.scope == "all"),
        None,
    )
    if unknown:
        notes.append(
            ConfidenceNote(
                source_task="200",
                layer="voice",
                note=f"unknown attribution ratio={unknown.ratio}; do not fabricate speakers",
            )
        )
    notes.append(
        ConfidenceNote(
            source_task="202",
            layer="readability",
            note=(
                "true perplexity is deferred; readability proxies have "
                f"{inputs.readability_report.summaries.get('strong_proxy_false_positive_pressure')}"
                " strong-sample hit pressure"
            ),
        )
    )
    notes.append(
        ConfidenceNote(
            source_task="201",
            layer="judge_bias",
            note="prelabel is comparison-only and must not become truth",
        )
    )
    return notes


def _truth_annotations(annotations: list[AnnotationRecord]) -> list[AnnotationRecord]:
    return [
        item for item in annotations
        if item.annotator == "agent-deep-read"
        and item.sample_layer in {"anchor", "spotcheck"}
    ]


def _prelabel_annotations(annotations: list[AnnotationRecord]) -> list[AnnotationRecord]:
    return [item for item in annotations if item.sample_layer == "prelabel"]


def _load_annotations(path: Path) -> list[AnnotationRecord]:
    data = _load_json_object(path)
    annotations = data.get("annotations")
    if not isinstance(annotations, list):
        raise ExcellenceIntegrationError(f"expected annotations list: {path}")
    return [
        AnnotationRecord.model_validate(item)
        for item in annotations
        if isinstance(item, dict)
    ]


def _load_report(path: Path, model_type: Any, *, task_id: str) -> Any:
    data = _load_json_object(path)
    report = model_type.model_validate(data)
    if getattr(report, "report_only", None) is not True:
        raise ExcellenceIntegrationError(
            f"Task {task_id} report must declare report_only=true: {path}"
        )
    if not getattr(report, "generated_at", None):
        raise ExcellenceIntegrationError(
            f"Task {task_id} report must include generated_at: {path}"
        )
    return report


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ExcellenceIntegrationError(f"failed to read {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ExcellenceIntegrationError(f"expected JSON object: {path}")
    return data


def _calibration_dict(calibration: CalibrationSummary | None) -> dict[str, Any]:
    if calibration is None:
        return {}
    return {
        "truth_rule": calibration.truth_rule,
        "evaluated": calibration.evaluated,
        "precision": calibration.precision,
        "recall": calibration.recall,
        "false_positive": calibration.false_positive,
        "false_negative": calibration.false_negative,
    }


def _task197_198_limitations(task: str) -> list[str]:
    if task == "197":
        return ["structure signal precision is low; report-only"]
    return ["AI-tone rules have false positives; report-only"]


def _signal_chapter_count(report: ExcellenceSignalReport, signal_id: str) -> int:
    return len({
        (chapter.genre, chapter.chapter)
        for chapter in report.chapters
        if any(hit.signal_id == signal_id for hit in chapter.hits)
    })


def _append_example(entry: SignalIndexEntry, evidence: EvidenceSummary) -> None:
    if len(entry.examples) < 8:
        entry.examples.append(evidence)


def _style_sanity(report: StyleCardReport, scope: str) -> dict[str, Any]:
    check = next((item for item in report.sanity_checks if item.scope == scope), None)
    return check.model_dump(mode="json") if check else {}


def _voice_examples(anchors: list[VoiceAnchorObservation]) -> list[EvidenceSummary]:
    examples: list[EvidenceSummary] = []
    for anchor in anchors[:8]:
        line = anchor.sample_lines[0] if anchor.sample_lines else None
        examples.append(
            EvidenceSummary(
                source_task="200",
                layer="voice",
                signal_id="voice_anchor",
                label=anchor.character_name,
                genre=line.genre if line else None,
                chapter=line.chapter if line else None,
                quote=_shorten(line.text, 120) if line else "",
                detail=f"distinctiveness={anchor.distinctiveness_score}",
            )
        )
    return examples


def _unknown_examples(
    unknown: UnknownAttributionSummary | None,
) -> list[EvidenceSummary]:
    if unknown is None:
        return []
    return [
        EvidenceSummary(
            source_task="200",
            layer="voice",
            signal_id="unknown_attribution",
            label="unknown",
            genre=line.genre,
            chapter=line.chapter,
            quote=_shorten(line.text, 120),
            detail=line.location,
        )
        for line in unknown.sample_lines[:6]
    ]


def _parse_chapter_label(value: str) -> tuple[str, int] | None:
    match = re.search(r"\b(scifi|xuanhuan|wuxia|urban)\s+Ch(\d+)\b", value)
    if not match:
        return None
    return match.group(1), int(match.group(2))


def _format_mapping(value: dict[str, Any]) -> str:
    parts = []
    for key, item in value.items():
        if isinstance(item, (str, int, float, bool)) or item is None:
            parts.append(f"{key}={item}")
    return ", ".join(parts[:4])


def _assert_no_prohibited_keys(report: IntegratedExcellenceReport) -> None:
    dumped = report.model_dump(mode="json")
    bad = _find_prohibited_keys(dumped)
    if bad:
        raise ExcellenceIntegrationError(
            "integrated report contains prohibited hard-score fields: "
            + ", ".join(sorted(bad))
        )


def _find_prohibited_keys(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key in PROHIBITED_KEYS:
                found.add(key)
            found.update(_find_prohibited_keys(item))
    elif isinstance(value, list):
        for item in value:
            found.update(_find_prohibited_keys(item))
    return found


def _shorten(text: str, limit: int) -> str:
    collapsed = re.sub(r"\s+", " ", text.strip())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 1] + "…"
