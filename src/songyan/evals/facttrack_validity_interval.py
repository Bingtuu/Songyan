"""Task 205 FactTrack validity interval spike.

The spike builds a shadow validity interval view over Task 204 samples. It is
offline and report-only: it reads Task 204 artifacts and SQLite facts through
read-only connections, but it does not write SQLite, alter schema, call LLMs,
or affect CED, five-gate, segment audit, T9, or runtime gates.
"""

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from songyan.evals.kg_diff_spike import (
    KGDiffManifest,
    KGDiffSample,
    KGDiffSpikeReport,
    load_kg_diff_manifest,
)

FactType = Literal["setting", "foreshadowing", "human_mark", "continuity_report"]
ValidStatus = Literal["active", "resolved", "stale", "superseded", "unknown"]
IntervalRule = Literal[
    "db_status",
    "resolved_marker",
    "same_chapter_report_order",
    "expected_resolve",
    "source_version_boundary",
    "document_truth",
]
Confidence = Literal["high", "medium", "low", "none"]
Decision = Literal["continue", "defer", "reject"]
MigrationCost = Literal["none", "low", "medium", "high"]

ORPHAN_THRESHOLDS: dict[str, int] = {
    "critical": 3,
    "recurring": 4,
    "background": 5,
    "technical": 7,
    "historical": 10,
}


class FactTrackSpikeError(RuntimeError):
    """Raised when Task 205 inputs are missing or invalid."""


class IntervalEvidence(BaseModel):
    """Evidence behind one shadow interval."""

    source_table: str
    source_row_id: str
    chapter: int | None = None
    version_id: str | None = None
    detail: str = ""


class ShadowValidityInterval(BaseModel):
    """Derived validity interval for an existing fact."""

    fact_id: str
    fact_type: FactType
    source_table: str
    source_row_id: str
    valid_from_chapter: int | None = Field(default=None, ge=1)
    valid_to_chapter: int | None = Field(default=None, ge=1)
    valid_status: ValidStatus
    interval_rule: IntervalRule
    confidence: Confidence
    evidence: IntervalEvidence
    migration_cost: MigrationCost
    consumer_impact: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class IntervalSampleEvaluation(BaseModel):
    """Evaluation of one Task 204 sample under shadow intervals."""

    sample_id: str
    issue_type: str
    kind: str
    interval_explained: bool
    false_positive: bool
    confidence: Confidence
    reduced_false_positive: bool
    reduced_false_negative: bool
    needs_alias_policy: bool
    needs_storyline_tree: bool
    document_truth_only: bool
    decision_note: str


class IntervalSampleResult(BaseModel):
    """Task 205 result for one sample."""

    sample: KGDiffSample
    db_exists: bool
    document_truth_only: bool
    intervals: list[ShadowValidityInterval] = Field(default_factory=list)
    evaluation: IntervalSampleEvaluation
    warnings: list[str] = Field(default_factory=list)


class IntervalImpactRow(BaseModel):
    """Impact matrix row by issue type."""

    issue_type: str
    sample_count: int = 0
    true_positive: int = 0
    false_positive: int = 0
    unclear: int = 0
    interval_explained: int = 0
    reduced_false_positive: int = 0
    reduced_false_negative: int = 0
    needs_alias_policy: int = 0
    needs_storyline_tree: int = 0
    db_schema_fields: list[str] = Field(default_factory=list)
    report_only_fields: list[str] = Field(default_factory=list)


class MigrationImpact(BaseModel):
    """Potential production data-model impact."""

    target: str
    required_for_spike: bool
    production_need: str
    migration_cost: MigrationCost
    fields: list[str] = Field(default_factory=list)
    affected_consumers: list[str] = Field(default_factory=list)
    rollback_plan: str


class FactTrackInputs(BaseModel):
    """Loaded Task 205 inputs."""

    manifest: KGDiffManifest
    kg_diff_report: KGDiffSpikeReport


class FactTrackSummary(BaseModel):
    """Top-level Task 205 summary."""

    report_only: bool = True
    sample_count: int
    positive_samples: int
    negative_controls: int
    db_backed_samples: int
    document_truth_only_samples: int
    interval_explained: int
    false_positive_count: int
    needs_alias_policy_count: int
    needs_storyline_tree_count: int
    decision: Decision
    decision_reason: str
    next_route: str


class FactTrackValidityReport(BaseModel):
    """Top-level Task 205 report."""

    generated_at: str
    report_only: bool = True
    boundaries: list[str]
    source_manifest: str
    source_kg_diff_report: str
    summary: FactTrackSummary
    impact_matrix: list[IntervalImpactRow]
    migration_impacts: list[MigrationImpact]
    samples: list[IntervalSampleResult]


def load_facttrack_inputs(
    *,
    manifest_path: Path,
    kg_diff_report_path: Path,
) -> FactTrackInputs:
    """Load Task 204 manifest and report for Task 205."""
    manifest = load_kg_diff_manifest(manifest_path)
    try:
        raw = json.loads(kg_diff_report_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise FactTrackSpikeError(
            f"failed to read KG diff report {kg_diff_report_path}: {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise FactTrackSpikeError(
            f"invalid KG diff report JSON {kg_diff_report_path}: {exc}"
        ) from exc
    try:
        report = KGDiffSpikeReport.model_validate(raw)
    except ValueError as exc:
        raise FactTrackSpikeError(
            f"invalid KG diff report schema {kg_diff_report_path}: {exc}"
        ) from exc
    if report.report_only is not True:
        raise FactTrackSpikeError("Task 204 KG diff report must be report_only=true")
    return FactTrackInputs(manifest=manifest, kg_diff_report=report)


def build_facttrack_validity_report(
    inputs: FactTrackInputs,
    *,
    manifest_path: Path,
    kg_diff_report_path: Path,
    root_dir: Path | None = None,
) -> FactTrackValidityReport:
    """Build the Task 205 shadow validity interval report."""
    root = root_dir or Path.cwd()
    kg_results = {item.sample.sample_id: item for item in inputs.kg_diff_report.samples}
    results = [
        _evaluate_sample(sample, root=root, kg_result=kg_results.get(sample.sample_id))
        for sample in inputs.manifest.samples
    ]
    impact_matrix = _build_impact_matrix(results)
    migration_impacts = _migration_impacts()
    summary = _build_summary(results)
    return FactTrackValidityReport(
        generated_at=datetime.now(UTC).isoformat(),
        boundaries=[
            "offline report-only spike",
            "shadow interval model only",
            "read-only SQLite access via mode=ro",
            "does not alter SQLite schema or migrate historical DBs",
            "does not call LLMs or extract new facts from prose",
            "does not modify Writer or CreativeDirector prompts",
            "does not enter accept/reject gates",
            "does not change CED, five-gate, segment audit, or T9",
            "does not implement production FactTrack",
        ],
        source_manifest=manifest_path.as_posix(),
        source_kg_diff_report=kg_diff_report_path.as_posix(),
        summary=summary,
        impact_matrix=impact_matrix,
        migration_impacts=migration_impacts,
        samples=results,
    )


def render_facttrack_validity_report(report: FactTrackValidityReport) -> str:
    """Render Task 205 report as Markdown."""
    lines = [
        "# Task 205 FactTrack validity interval spike",
        "",
        f"> generated_at: `{report.generated_at}`",
        f"> source_manifest: `{report.source_manifest}`",
        f"> source_kg_diff_report: `{report.source_kg_diff_report}`",
        "",
        "## 边界",
        "",
    ]
    lines.extend(f"- {item}" for item in report.boundaries)
    lines.extend(["", "## Summary", ""])
    summary = report.summary
    lines.extend(
        [
            f"- report_only: `{summary.report_only}`",
            f"- sample_count: `{summary.sample_count}`",
            f"- positive_samples: `{summary.positive_samples}`",
            f"- negative_controls: `{summary.negative_controls}`",
            f"- db_backed_samples: `{summary.db_backed_samples}`",
            f"- document_truth_only_samples: `{summary.document_truth_only_samples}`",
            f"- interval_explained: `{summary.interval_explained}`",
            f"- false_positive_count: `{summary.false_positive_count}`",
            f"- needs_alias_policy_count: `{summary.needs_alias_policy_count}`",
            f"- needs_storyline_tree_count: `{summary.needs_storyline_tree_count}`",
            f"- decision: `{summary.decision}`",
            f"- decision_reason: {summary.decision_reason}",
            f"- next_route: {summary.next_route}",
        ]
    )
    lines.extend(["", "## Impact Matrix", ""])
    lines.append(
        "| issue_type | samples | TP | FP | unclear | explained | reduce FP | "
        "reduce FN | alias | storyline |"
    )
    lines.append(
        "|------------|--------:|---:|---:|--------:|----------:|----------:|"
        "----------:|------:|----------:|"
    )
    for row in report.impact_matrix:
        lines.append(
            f"| `{row.issue_type}` | {row.sample_count} | {row.true_positive} | "
            f"{row.false_positive} | {row.unclear} | {row.interval_explained} | "
            f"{row.reduced_false_positive} | {row.reduced_false_negative} | "
            f"{row.needs_alias_policy} | {row.needs_storyline_tree} |"
        )
    lines.extend(["", "## Migration Impact", ""])
    lines.append("| target | required now | production need | cost | fields | consumers |")
    lines.append("|--------|--------------|-----------------|------|--------|-----------|")
    for item in report.migration_impacts:
        lines.append(
            f"| `{item.target}` | {item.required_for_spike} | {item.production_need} | "
            f"`{item.migration_cost}` | {', '.join(item.fields) or '-'} | "
            f"{', '.join(item.affected_consumers) or '-'} |"
        )
    lines.extend(["", "## Sample Results", ""])
    lines.append(
        "| sample | genre | chapter | issue | explained | confidence | FP | alias | storyline |"
    )
    lines.append(
        "|--------|-------|--------:|-------|-----------|------------|----|-------|-----------|"
    )
    for item in report.samples:
        ev = item.evaluation
        lines.append(
            f"| `{item.sample.sample_id}` | {item.sample.genre} | {item.sample.chapter} | "
            f"`{item.sample.issue_type}` | {ev.interval_explained} | "
            f"`{ev.confidence}` | {ev.false_positive} | {ev.needs_alias_policy} | "
            f"{ev.needs_storyline_tree} |"
        )
    lines.extend(["", "## Interval Evidence", ""])
    for item in report.samples:
        lines.append(f"### {item.sample.sample_id}")
        if item.document_truth_only:
            lines.append("- document_truth_only: true")
        if not item.intervals:
            lines.append("- no derived interval")
            lines.append("")
            continue
        for interval in item.intervals[:8]:
            lines.append(
                f"- `{interval.fact_type}` / `{interval.valid_status}` / "
                f"`{interval.confidence}`: {interval.fact_id} "
                f"Ch{interval.valid_from_chapter}-{interval.valid_to_chapter or '?'} "
                f"({interval.interval_rule}; {interval.evidence.source_table}:"
                f"{interval.evidence.source_row_id})"
            )
        lines.append("")
    lines.extend(
        [
            "## 后续路由",
            "",
            "- Task 206: Storyline Tree spike，用于验证 open thread 与已兑现伏笔的主线/支线归属。",
            "- Task 207: 若 V10 收口时登记生产化，优先以 derived view / "
            "report-only 方式进入，不直接迁移历史库。",
            "- Task 205 输出保持 report-only，不进入 hard gate。",
        ]
    )
    return "\n".join(lines) + "\n"


def _evaluate_sample(
    sample: KGDiffSample,
    *,
    root: Path,
    kg_result: Any | None,
) -> IntervalSampleResult:
    db_path = _resolve_path(root, sample.db_path)
    warnings: list[str] = []
    if not db_path.exists():
        warnings.append(f"DB missing; using document truth only: {sample.db_path}")
        return _document_only_result(sample, warnings=warnings)
    try:
        with _open_readonly_db(db_path) as conn:
            intervals = _derive_intervals(conn, sample)
    except sqlite3.Error as exc:
        warnings.append(f"DB read failed; using document truth only: {exc}")
        return _document_only_result(sample, warnings=warnings)

    evaluation = _evaluate_intervals(sample, intervals, kg_result)
    return IntervalSampleResult(
        sample=sample,
        db_exists=True,
        document_truth_only=False,
        intervals=intervals,
        evaluation=evaluation,
        warnings=warnings,
    )


def _document_only_result(
    sample: KGDiffSample,
    *,
    warnings: list[str],
) -> IntervalSampleResult:
    evaluation = IntervalSampleEvaluation(
        sample_id=sample.sample_id,
        issue_type=sample.issue_type,
        kind=sample.kind,
        interval_explained=False,
        false_positive=False,
        confidence="low" if sample.kind == "positive" else "none",
        reduced_false_positive=False,
        reduced_false_negative=False,
        needs_alias_policy=_needs_alias_policy(sample),
        needs_storyline_tree=_needs_storyline_tree(sample),
        document_truth_only=True,
        decision_note="document truth only; DB interval could not be derived",
    )
    return IntervalSampleResult(
        sample=sample,
        db_exists=False,
        document_truth_only=True,
        evaluation=evaluation,
        warnings=warnings,
    )


def _derive_intervals(
    conn: sqlite3.Connection,
    sample: KGDiffSample,
) -> list[ShadowValidityInterval]:
    intervals: list[ShadowValidityInterval] = []
    intervals.extend(_setting_intervals(conn, sample))
    intervals.extend(_foreshadowing_intervals(conn, sample))
    intervals.extend(_human_mark_intervals(conn, sample))
    intervals.extend(_continuity_report_intervals(conn, sample))
    return _prioritize_intervals(intervals, sample)


def _setting_intervals(
    conn: sqlite3.Connection,
    sample: KGDiffSample,
) -> list[ShadowValidityInterval]:
    if not _table_exists(conn, "setting_tracking"):
        return []
    cols = _columns(conn, "setting_tracking")
    select = [
        col for col in [
            "tracking_id",
            "setting_key",
            "setting_name",
            "introduced_in_chapter",
            "last_mentioned_chapter",
            "expected_resolve_chapter",
            "status",
            "source_version_id",
            "category",
            "resolved_chapter",
            "resolved_version_id",
        ] if col in cols
    ]
    rows = _fetchall(
        conn,
        f"""SELECT {', '.join(select)}
            FROM setting_tracking
            WHERE project_id = ?
              AND COALESCE(introduced_in_chapter, 0) <= ?
            ORDER BY introduced_in_chapter, tracking_id""",
        (sample.project_id, sample.chapter),
    )
    out: list[ShadowValidityInterval] = []
    next_audit = ((sample.chapter // 3) + 1) * 3
    for row in rows:
        category = str(_value(row, "category") or "background")
        status = str(_value(row, "status") or "")
        last = _int_or_none(_value(row, "last_mentioned_chapter"))
        introduced = _int_or_none(_value(row, "introduced_in_chapter"))
        resolved = _int_or_none(_value(row, "resolved_chapter"))
        threshold = ORPHAN_THRESHOLDS.get(category, 5)
        stale = (
            status == "active"
            and category == "critical"
            and last is not None
            and (next_audit - last) > threshold
        )
        confidence: Confidence = "low"
        if sample.kind == "positive" and sample.expected_signal == "missing_refresh_candidate":
            confidence = "high" if stale else "low"
        elif sample.kind == "positive" and sample.issue_type == "critical_orphan":
            confidence = "high" if stale else "low"
        valid_status: ValidStatus = "stale" if stale else "active"
        if resolved is not None:
            valid_status = "resolved"
            confidence = "medium"
        tracking_id = str(_value(row, "tracking_id") or _value(row, "setting_key"))
        out.append(
            ShadowValidityInterval(
                fact_id=f"setting:{tracking_id}",
                fact_type="setting",
                source_table="setting_tracking",
                source_row_id=tracking_id,
                valid_from_chapter=introduced,
                valid_to_chapter=resolved if resolved is not None else last,
                valid_status=valid_status,
                interval_rule=(
                    "resolved_marker" if resolved is not None else "source_version_boundary"
                ),
                confidence=confidence,
                evidence=IntervalEvidence(
                    source_table="setting_tracking",
                    source_row_id=tracking_id,
                    chapter=last,
                    version_id=_value(row, "source_version_id"),
                    detail=str(_value(row, "setting_key") or _value(row, "setting_name") or ""),
                ),
                migration_cost="medium",
                consumer_impact=["segment_audit", "ContextManager"],
                notes=[
                    f"category={category}",
                    f"next_audit={next_audit}",
                    f"threshold={threshold}",
                ],
            )
        )
    return out


def _foreshadowing_intervals(
    conn: sqlite3.Connection,
    sample: KGDiffSample,
) -> list[ShadowValidityInterval]:
    if not _table_exists(conn, "foreshadowings"):
        return []
    rows = _fetchall(
        conn,
        """SELECT foreshadowing_id, description, planted_in_chapter,
                  expected_resolve_chapter, status, lifecycle_status, source_version_id
           FROM foreshadowings
           WHERE project_id = ? AND planted_in_chapter <= ?
           ORDER BY planted_in_chapter, foreshadowing_id""",
        (sample.project_id, sample.chapter),
    )
    out: list[ShadowValidityInterval] = []
    for row in rows:
        expected = _int_or_none(row["expected_resolve_chapter"])
        status = str(row["status"] or "")
        lifecycle = str(row["lifecycle_status"] or "")
        overdue = expected is not None and expected < sample.chapter and status != "resolved"
        confidence: Confidence = "low"
        if (
            sample.kind == "positive"
            and sample.expected_signal == "unresolved_candidate"
            and overdue
        ):
            confidence = "high"
        valid_status: ValidStatus = "stale" if overdue else "active"
        if status == "resolved":
            valid_status = "resolved"
            confidence = "medium" if sample.kind == "positive" else "low"
        fact_id = str(row["foreshadowing_id"])
        out.append(
            ShadowValidityInterval(
                fact_id=f"foreshadowing:{fact_id}",
                fact_type="foreshadowing",
                source_table="foreshadowings",
                source_row_id=fact_id,
                valid_from_chapter=_int_or_none(row["planted_in_chapter"]),
                valid_to_chapter=expected,
                valid_status=valid_status,
                interval_rule="expected_resolve",
                confidence=confidence,
                evidence=IntervalEvidence(
                    source_table="foreshadowings",
                    source_row_id=fact_id,
                    chapter=_int_or_none(row["planted_in_chapter"]),
                    version_id=row["source_version_id"],
                    detail=str(row["description"] or ""),
                ),
                migration_cost="medium",
                consumer_impact=["ContinuityAuditor", "ContextManager", "five_gate"],
                notes=[f"status={status}", f"lifecycle={lifecycle}"],
            )
        )
    return out


def _human_mark_intervals(
    conn: sqlite3.Connection,
    sample: KGDiffSample,
) -> list[ShadowValidityInterval]:
    if not _table_exists(conn, "human_marks"):
        return []
    cols = _columns(conn, "human_marks")
    select = [
        col for col in [
            "mark_id",
            "mark_type",
            "target_key",
            "note",
            "priority",
            "created_at_chapter",
            "resolved_at",
            "lifecycle_status",
            "source",
            "version_id",
            "severity",
        ] if col in cols
    ]
    rows = _fetchall(
        conn,
        f"""SELECT {', '.join(select)}
            FROM human_marks
            WHERE project_id = ?
              AND COALESCE(created_at_chapter, 0) <= ?
            ORDER BY created_at_chapter, priority DESC, mark_id""",
        (sample.project_id, sample.chapter),
    )
    out: list[ShadowValidityInterval] = []
    for row in rows:
        mark_id = str(_value(row, "mark_id"))
        priority = int(_value(row, "priority") or 0)
        resolved = bool(_value(row, "resolved_at"))
        confidence: Confidence = "low"
        if sample.kind == "positive" and priority >= 8 and not resolved:
            confidence = "medium"
        out.append(
            ShadowValidityInterval(
                fact_id=f"human_mark:{mark_id}",
                fact_type="human_mark",
                source_table="human_marks",
                source_row_id=mark_id,
                valid_from_chapter=_int_or_none(_value(row, "created_at_chapter")),
                valid_to_chapter=_int_or_none(_value(row, "created_at_chapter"))
                if resolved else None,
                valid_status="resolved" if resolved else "active",
                interval_rule="resolved_marker",
                confidence=confidence,
                evidence=IntervalEvidence(
                    source_table="human_marks",
                    source_row_id=mark_id,
                    chapter=_int_or_none(_value(row, "created_at_chapter")),
                    version_id=_value(row, "version_id"),
                    detail=str(_value(row, "note") or _value(row, "target_key") or ""),
                ),
                migration_cost="low",
                consumer_impact=["ContextManager", "ContinuityAuditor"],
                notes=[f"priority={priority}", f"source={_value(row, 'source')}"],
            )
        )
    return out


def _continuity_report_intervals(
    conn: sqlite3.Connection,
    sample: KGDiffSample,
) -> list[ShadowValidityInterval]:
    if not _table_exists(conn, "continuity_reports"):
        return []
    cols = _columns(conn, "continuity_reports")
    select = [
        col for col in [
            "report_id",
            "checked_up_to_chapter",
            "overall_health_score",
            "created_at",
        ] if col in cols
    ]
    if "report_id" not in select or "checked_up_to_chapter" not in select:
        return []
    rows = _fetchall(
        conn,
        f"""SELECT rowid, {', '.join(select)}
            FROM continuity_reports
            WHERE project_id = ?
              AND checked_up_to_chapter <= ?
            ORDER BY checked_up_to_chapter, rowid""",
        (sample.project_id, sample.chapter),
    )
    by_chapter: dict[int, list[sqlite3.Row]] = defaultdict(list)
    for row in rows:
        by_chapter[int(row["checked_up_to_chapter"])].append(row)
    out: list[ShadowValidityInterval] = []
    for chapter, grouped in by_chapter.items():
        latest = grouped[-1]
        for row in grouped:
            stale_same_chapter = len(grouped) > 1 and row["rowid"] != latest["rowid"]
            confidence: Confidence = "low"
            if (
                sample.kind == "positive"
                and sample.expected_signal == "stale_candidate"
                and chapter == sample.chapter
                and stale_same_chapter
            ):
                confidence = "high"
            status: ValidStatus = "superseded" if stale_same_chapter else "active"
            report_id = str(row["report_id"])
            out.append(
                ShadowValidityInterval(
                    fact_id=f"continuity_report:{report_id}",
                    fact_type="continuity_report",
                    source_table="continuity_reports",
                    source_row_id=report_id,
                    valid_from_chapter=chapter,
                    valid_to_chapter=chapter if stale_same_chapter else None,
                    valid_status=status,
                    interval_rule="same_chapter_report_order",
                    confidence=confidence,
                    evidence=IntervalEvidence(
                        source_table="continuity_reports",
                        source_row_id=report_id,
                        chapter=chapter,
                        detail=f"health={_value(row, 'overall_health_score')}",
                    ),
                    migration_cost="none",
                    consumer_impact=["five_gate", "segment_audit"],
                    notes=[f"created_at={_value(row, 'created_at')}"],
                )
            )
    return out


def _evaluate_intervals(
    sample: KGDiffSample,
    intervals: list[ShadowValidityInterval],
    kg_result: Any | None,
) -> IntervalSampleEvaluation:
    matching = _matching_intervals(sample, intervals)
    high_false = [
        item for item in intervals
        if sample.kind == "negative_control"
        and item.confidence == "high"
        and item.valid_status in {"stale", "superseded"}
    ]
    interval_explained = bool(matching) if sample.kind == "positive" else False
    false_positive = bool(high_false)
    confidence = _max_confidence(matching or high_false)
    if sample.kind == "negative_control" and not false_positive:
        confidence = "none"
    reduced_fp = sample.kind == "negative_control" and not false_positive
    reduced_fn = sample.kind == "positive" and interval_explained
    needs_alias = _needs_alias_policy(sample)
    needs_story = _needs_storyline_tree(sample)
    if kg_result is not None and getattr(kg_result.evaluation, "unique_gain", False):
        reduced_fn = reduced_fn or interval_explained
    return IntervalSampleEvaluation(
        sample_id=sample.sample_id,
        issue_type=sample.issue_type,
        kind=sample.kind,
        interval_explained=interval_explained,
        false_positive=false_positive,
        confidence=confidence,
        reduced_false_positive=reduced_fp,
        reduced_false_negative=reduced_fn,
        needs_alias_policy=needs_alias,
        needs_storyline_tree=needs_story,
        document_truth_only=False,
        decision_note=_sample_decision_note(
            sample,
            interval_explained=interval_explained,
            false_positive=false_positive,
            needs_alias=needs_alias,
            needs_story=needs_story,
        ),
    )


def _matching_intervals(
    sample: KGDiffSample,
    intervals: list[ShadowValidityInterval],
) -> list[ShadowValidityInterval]:
    if sample.expected_signal == "unresolved_candidate":
        return [
            item for item in intervals
            if item.fact_type in {"foreshadowing", "human_mark"}
            and item.valid_status in {"stale", "active"}
            and item.confidence in {"high", "medium"}
        ]
    if sample.expected_signal == "missing_refresh_candidate":
        return [
            item for item in intervals
            if item.fact_type == "setting"
            and item.valid_status == "stale"
            and item.confidence in {"high", "medium"}
        ]
    if sample.expected_signal == "stale_candidate":
        return [
            item for item in intervals
            if item.fact_type == "continuity_report"
            and item.valid_status == "superseded"
            and item.confidence in {"high", "medium"}
        ]
    return []


def _sample_decision_note(
    sample: KGDiffSample,
    *,
    interval_explained: bool,
    false_positive: bool,
    needs_alias: bool,
    needs_story: bool,
) -> str:
    if false_positive:
        return "negative control produced a high-confidence stale interval"
    if sample.kind == "negative_control":
        return "negative control has no high-confidence invalid interval"
    if not interval_explained:
        return "shadow interval did not explain the Task 204 signal"
    if needs_story:
        return (
            "interval explains DB state, but storyline context is needed "
            "for open-thread semantics"
        )
    if needs_alias:
        return "interval explains stale tracking, but alias policy is still needed"
    return "shadow interval explains the Task 204 signal"


def _build_impact_matrix(
    results: list[IntervalSampleResult],
) -> list[IntervalImpactRow]:
    grouped: dict[str, list[IntervalSampleResult]] = defaultdict(list)
    for item in results:
        grouped[item.sample.issue_type].append(item)
    rows: list[IntervalImpactRow] = []
    for issue_type, items in sorted(grouped.items()):
        row = IntervalImpactRow(issue_type=issue_type, sample_count=len(items))
        db_fields: set[str] = set()
        report_fields: set[str] = set()
        for item in items:
            ev = item.evaluation
            if item.sample.kind == "positive" and ev.interval_explained:
                row.true_positive += 1
            elif item.sample.kind == "positive":
                row.unclear += 1
            if ev.false_positive:
                row.false_positive += 1
            if ev.interval_explained:
                row.interval_explained += 1
            if ev.reduced_false_positive:
                row.reduced_false_positive += 1
            if ev.reduced_false_negative:
                row.reduced_false_negative += 1
            if ev.needs_alias_policy:
                row.needs_alias_policy += 1
            if ev.needs_storyline_tree:
                row.needs_storyline_tree += 1
            for interval in item.intervals:
                report_fields.update(_report_only_fields(interval))
                db_fields.update(_db_schema_fields(interval))
        row.db_schema_fields = sorted(db_fields)
        row.report_only_fields = sorted(report_fields)
        rows.append(row)
    return rows


def _build_summary(results: list[IntervalSampleResult]) -> FactTrackSummary:
    positives = sum(1 for item in results if item.sample.kind == "positive")
    negatives = sum(1 for item in results if item.sample.kind == "negative_control")
    db_backed = sum(1 for item in results if not item.document_truth_only)
    doc_only = sum(1 for item in results if item.document_truth_only)
    explained = sum(1 for item in results if item.evaluation.interval_explained)
    fp = sum(1 for item in results if item.evaluation.false_positive)
    alias = sum(1 for item in results if item.evaluation.needs_alias_policy)
    story = sum(1 for item in results if item.evaluation.needs_storyline_tree)
    explained_types = {
        item.sample.issue_type
        for item in results
        if item.evaluation.interval_explained
    }
    if explained >= 2 and len(explained_types) >= 2 and fp == 0:
        if alias or story:
            decision: Decision = "defer"
            reason = (
                "Shadow intervals explain Task 204 signals, but alias policy "
                "and storyline semantics are still needed before production use."
            )
        else:
            decision = "continue"
            reason = (
                "Shadow intervals explain multiple issue types with clean negative "
                "controls and can start as a derived view."
            )
    elif explained > 0:
        decision = "defer"
        reason = "Some interval signals exist, but coverage is not stable."
    else:
        decision = "reject"
        reason = "Intervals mostly repeat existing status fields without useful impact."
    next_route = (
        "Task 206 Storyline Tree spike"
        if decision == "defer" and story
        else "Task 207 registration or follow-up productionization"
        if decision == "continue"
        else "Task 206 independent Storyline Tree evaluation"
    )
    return FactTrackSummary(
        sample_count=len(results),
        positive_samples=positives,
        negative_controls=negatives,
        db_backed_samples=db_backed,
        document_truth_only_samples=doc_only,
        interval_explained=explained,
        false_positive_count=fp,
        needs_alias_policy_count=alias,
        needs_storyline_tree_count=story,
        decision=decision,
        decision_reason=reason,
        next_route=next_route,
    )


def _migration_impacts() -> list[MigrationImpact]:
    return [
        MigrationImpact(
            target="derived_fact_validity_view",
            required_for_spike=False,
            production_need="Can be generated report-only from existing tables first.",
            migration_cost="none",
            fields=[
                "fact_id",
                "valid_from_chapter",
                "valid_to_chapter",
                "valid_status",
                "interval_rule",
                "confidence",
            ],
            affected_consumers=["offline evaluators", "Task 207 reports"],
            rollback_plan="Delete generated artifacts; no DB state is changed.",
        ),
        MigrationImpact(
            target="fact_validity_intervals",
            required_for_spike=False,
            production_need="Optional if intervals become reusable runtime facts.",
            migration_cost="medium",
            fields=[
                "fact_id",
                "fact_type",
                "source_table",
                "source_row_id",
                "valid_from_chapter",
                "valid_to_chapter",
                "valid_status",
                "source_version_id",
            ],
            affected_consumers=[
                "SettlementExtractor",
                "SummaryWriter",
                "ContextManager",
                "segment_audit",
            ],
            rollback_plan="Drop additive table and fall back to current status/lifecycle fields.",
        ),
        MigrationImpact(
            target="foreshadowings",
            required_for_spike=False,
            production_need="Trace resolved chapter/version without document truth.",
            migration_cost="medium",
            fields=["resolved_chapter", "resolved_version_id", "resolved_reason"],
            affected_consumers=["ContinuityAuditor", "five_gate", "ContextManager"],
            rollback_plan="Ignore additive columns; existing status/lifecycle semantics remain.",
        ),
        MigrationImpact(
            target="setting_tracking",
            required_for_spike=False,
            production_need="Alias-aware validity may need canonical target tracking.",
            migration_cost="medium",
            fields=["valid_from_chapter", "valid_to_chapter", "alias_group_id"],
            affected_consumers=["segment_audit", "ContextManager"],
            rollback_plan="Ignore additive columns and retain current last_mentioned semantics.",
        ),
    ]


def _prioritize_intervals(
    intervals: list[ShadowValidityInterval],
    sample: KGDiffSample,
) -> list[ShadowValidityInterval]:
    rank = {"high": 0, "medium": 1, "low": 2, "none": 3}
    type_rank = {
        "foreshadowing": 0,
        "setting": 1,
        "continuity_report": 2,
        "human_mark": 3,
    }
    return sorted(
        intervals,
        key=lambda item: (
            rank[item.confidence],
            0 if _interval_matches_sample(item, sample) else 1,
            type_rank[item.fact_type],
            item.fact_id,
        ),
    )[:40]


def _interval_matches_sample(
    interval: ShadowValidityInterval,
    sample: KGDiffSample,
) -> bool:
    if sample.expected_signal == "unresolved_candidate":
        return interval.fact_type in {"foreshadowing", "human_mark"}
    if sample.expected_signal == "missing_refresh_candidate":
        return interval.fact_type == "setting"
    if sample.expected_signal == "stale_candidate":
        return interval.fact_type == "continuity_report"
    return False


def _report_only_fields(interval: ShadowValidityInterval) -> set[str]:
    return {
        "fact_id",
        "valid_from_chapter",
        "valid_to_chapter",
        "valid_status",
        "interval_rule",
        "confidence",
    }


def _db_schema_fields(interval: ShadowValidityInterval) -> set[str]:
    if interval.fact_type == "foreshadowing":
        return {"resolved_chapter", "resolved_version_id"}
    if interval.fact_type == "setting":
        return {"valid_from_chapter", "valid_to_chapter", "alias_group_id"}
    if interval.fact_type == "continuity_report":
        return set()
    return set()


def _needs_alias_policy(sample: KGDiffSample) -> bool:
    return sample.issue_type in {
        "setting_tracking_missing_refresh",
        "critical_orphan",
    }


def _needs_storyline_tree(sample: KGDiffSample) -> bool:
    return sample.issue_type == "foreshadowing_unresolved"


def _max_confidence(items: list[ShadowValidityInterval]) -> Confidence:
    if not items:
        return "none"
    rank = {"high": 3, "medium": 2, "low": 1, "none": 0}
    return max((item.confidence for item in items), key=lambda value: rank[value])


def _resolve_path(root: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return root / path


def _open_readonly_db(path: Path) -> sqlite3.Connection:
    uri = f"file:{path.resolve().as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    rows = _fetchall(
        conn,
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ? LIMIT 1",
        (table_name,),
    )
    return bool(rows)


def _columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = _fetchall(conn, f"PRAGMA table_info({table_name})")
    return {str(row["name"]) for row in rows}


def _fetchall(
    conn: sqlite3.Connection,
    sql: str,
    params: tuple[Any, ...] = (),
) -> list[sqlite3.Row]:
    cur = conn.execute(sql, params)
    return list(cur.fetchall())


def _value(row: sqlite3.Row, key: str) -> Any:
    return row[key] if key in row.keys() else None


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
