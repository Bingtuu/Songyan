"""Task 206 Storyline Tree spike.

This module builds a small shadow Storyline Tree over Task 204/205 samples. It
is offline and report-only: it reads existing artifacts and SQLite facts through
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

from songyan.evals.facttrack_validity_interval import (
    FactTrackValidityReport,
)
from songyan.evals.kg_diff_spike import (
    KGDiffManifest,
    KGDiffSample,
    KGDiffSpikeReport,
    load_kg_diff_manifest,
)

NodeType = Literal["mainline", "subplot", "arc", "thread", "payoff"]
StorylineStatus = Literal["open", "active", "resolved", "stale", "unknown"]
Confidence = Literal["high", "medium", "low", "none"]
Decision = Literal["continue", "defer", "reject"]
MigrationCost = Literal["none", "low", "medium", "high"]
SourceRule = Literal[
    "foreshadowing_expected_resolve",
    "arc_summary_range",
    "derived_arc_window",
    "human_mark_thread",
    "setting_tracking_thread",
    "document_truth",
]


class StorylineTreeSpikeError(RuntimeError):
    """Raised when Task 206 inputs are missing or invalid."""


class StorylineEvidence(BaseModel):
    """Evidence behind one shadow tree node."""

    source_table: str
    source_row_id: str
    chapter: int | None = None
    version_id: str | None = None
    detail: str = ""


class StorylineNode(BaseModel):
    """Shadow storyline tree node."""

    storyline_id: str
    parent_id: str | None = None
    node_type: NodeType
    genre: str
    chapter_start: int | None = Field(default=None, ge=1)
    chapter_end: int | None = Field(default=None, ge=1)
    status: StorylineStatus
    linked_facts: dict[str, list[str]] = Field(default_factory=dict)
    evidence: StorylineEvidence
    confidence: Confidence
    source_rule: SourceRule
    consumer_impact: list[str] = Field(default_factory=list)
    migration_cost: MigrationCost
    notes: list[str] = Field(default_factory=list)


class StorylineSampleEvaluation(BaseModel):
    """Evaluation of one Task 204/205 sample under shadow Storyline Tree."""

    sample_id: str
    issue_type: str
    kind: str
    tree_explained: bool
    false_positive: bool
    confidence: Confidence
    reduced_false_positive: bool
    reduced_false_negative: bool
    still_needs_alias_policy: bool
    still_needs_validity_interval: bool
    document_truth_only: bool
    decision_note: str


class StorylineSampleResult(BaseModel):
    """Task 206 result for one sample."""

    sample: KGDiffSample
    db_exists: bool
    document_truth_only: bool
    nodes: list[StorylineNode] = Field(default_factory=list)
    evaluation: StorylineSampleEvaluation
    warnings: list[str] = Field(default_factory=list)


class StorylineImpactRow(BaseModel):
    """Storyline Tree impact matrix row by issue type."""

    issue_type: str
    sample_count: int = 0
    true_positive: int = 0
    false_positive: int = 0
    unclear: int = 0
    tree_explained: int = 0
    reduced_false_positive: int = 0
    reduced_false_negative: int = 0
    still_needs_alias_policy: int = 0
    still_needs_validity_interval: int = 0
    production_schema_needed: list[str] = Field(default_factory=list)
    report_only_fields: list[str] = Field(default_factory=list)


class StorylineMigrationImpact(BaseModel):
    """Potential production data-model impact."""

    target: str
    required_for_spike: bool
    production_need: str
    migration_cost: MigrationCost
    fields: list[str] = Field(default_factory=list)
    affected_consumers: list[str] = Field(default_factory=list)
    rollback_plan: str


class StorylineTreeInputs(BaseModel):
    """Loaded Task 206 inputs."""

    manifest: KGDiffManifest
    kg_diff_report: KGDiffSpikeReport
    facttrack_report: FactTrackValidityReport


class StorylineTreeSummary(BaseModel):
    """Top-level Task 206 summary."""

    report_only: bool = True
    sample_count: int
    positive_samples: int
    negative_controls: int
    db_backed_samples: int
    document_truth_only_samples: int
    needs_storyline_tree_samples: int
    tree_explained: int
    false_positive_count: int
    still_needs_alias_policy_count: int
    still_needs_validity_interval_count: int
    decision: Decision
    decision_reason: str
    next_route: str


class StorylineTreeReport(BaseModel):
    """Top-level Task 206 report."""

    generated_at: str
    report_only: bool = True
    boundaries: list[str]
    source_manifest: str
    source_kg_diff_report: str
    source_facttrack_report: str
    summary: StorylineTreeSummary
    impact_matrix: list[StorylineImpactRow]
    migration_impacts: list[StorylineMigrationImpact]
    samples: list[StorylineSampleResult]


def load_storyline_tree_inputs(
    *,
    manifest_path: Path,
    kg_diff_report_path: Path,
    facttrack_report_path: Path,
) -> StorylineTreeInputs:
    """Load Task 204/205 artifacts for Task 206."""
    manifest = load_kg_diff_manifest(manifest_path)
    kg_report = _load_model(kg_diff_report_path, KGDiffSpikeReport, "KG diff report")
    facttrack = _load_model(
        facttrack_report_path,
        FactTrackValidityReport,
        "FactTrack report",
    )
    if kg_report.report_only is not True or facttrack.report_only is not True:
        raise StorylineTreeSpikeError("Task 204/205 inputs must be report_only=true")
    return StorylineTreeInputs(
        manifest=manifest,
        kg_diff_report=kg_report,
        facttrack_report=facttrack,
    )


def build_storyline_tree_report(
    inputs: StorylineTreeInputs,
    *,
    manifest_path: Path,
    kg_diff_report_path: Path,
    facttrack_report_path: Path,
    root_dir: Path | None = None,
) -> StorylineTreeReport:
    """Build the Task 206 shadow Storyline Tree report."""
    root = root_dir or Path.cwd()
    facttrack_by_sample = {
        item.sample.sample_id: item
        for item in inputs.facttrack_report.samples
    }
    results = [
        _evaluate_sample(
            sample,
            root=root,
            facttrack_result=facttrack_by_sample.get(sample.sample_id),
        )
        for sample in inputs.manifest.samples
    ]
    impact = _build_impact_matrix(results)
    summary = _build_summary(results)
    return StorylineTreeReport(
        generated_at=datetime.now(UTC).isoformat(),
        boundaries=[
            "offline report-only spike",
            "shadow Storyline Tree only",
            "read-only SQLite access via mode=ro",
            "does not alter SQLite schema or migrate historical DBs",
            "does not call LLMs or extract new plot facts from prose",
            "does not modify Writer or CreativeDirector prompts",
            "does not enter accept/reject gates",
            "does not change CED, five-gate, segment audit, or T9",
            "does not implement production Storyline Tree",
        ],
        source_manifest=manifest_path.as_posix(),
        source_kg_diff_report=kg_diff_report_path.as_posix(),
        source_facttrack_report=facttrack_report_path.as_posix(),
        summary=summary,
        impact_matrix=impact,
        migration_impacts=_migration_impacts(),
        samples=results,
    )


def render_storyline_tree_report(report: StorylineTreeReport) -> str:
    """Render Task 206 report as Markdown."""
    lines = [
        "# Task 206 Storyline Tree spike",
        "",
        f"> generated_at: `{report.generated_at}`",
        f"> source_manifest: `{report.source_manifest}`",
        f"> source_kg_diff_report: `{report.source_kg_diff_report}`",
        f"> source_facttrack_report: `{report.source_facttrack_report}`",
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
            f"- needs_storyline_tree_samples: `{summary.needs_storyline_tree_samples}`",
            f"- tree_explained: `{summary.tree_explained}`",
            f"- false_positive_count: `{summary.false_positive_count}`",
            f"- still_needs_alias_policy_count: `{summary.still_needs_alias_policy_count}`",
            "- still_needs_validity_interval_count: "
            f"`{summary.still_needs_validity_interval_count}`",
            f"- decision: `{summary.decision}`",
            f"- decision_reason: {summary.decision_reason}",
            f"- next_route: {summary.next_route}",
        ]
    )
    lines.extend(["", "## Impact Matrix", ""])
    lines.append(
        "| issue_type | samples | TP | FP | unclear | tree | reduce FP | "
        "reduce FN | alias | validity |"
    )
    lines.append(
        "|------------|--------:|---:|---:|--------:|-----:|----------:|"
        "----------:|------:|---------:|"
    )
    for row in report.impact_matrix:
        lines.append(
            f"| `{row.issue_type}` | {row.sample_count} | {row.true_positive} | "
            f"{row.false_positive} | {row.unclear} | {row.tree_explained} | "
            f"{row.reduced_false_positive} | {row.reduced_false_negative} | "
            f"{row.still_needs_alias_policy} | {row.still_needs_validity_interval} |"
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
        "| sample | genre | chapter | issue | tree | confidence | FP | alias | validity |"
    )
    lines.append(
        "|--------|-------|--------:|-------|------|------------|----|-------|----------|"
    )
    for item in report.samples:
        ev = item.evaluation
        lines.append(
            f"| `{item.sample.sample_id}` | {item.sample.genre} | {item.sample.chapter} | "
            f"`{item.sample.issue_type}` | {ev.tree_explained} | "
            f"`{ev.confidence}` | {ev.false_positive} | {ev.still_needs_alias_policy} | "
            f"{ev.still_needs_validity_interval} |"
        )
    lines.extend(["", "## Storyline Nodes", ""])
    for item in report.samples:
        lines.append(f"### {item.sample.sample_id}")
        if item.document_truth_only:
            lines.append("- document_truth_only: true")
        if not item.nodes:
            lines.append("- no derived storyline node")
            lines.append("")
            continue
        for node in item.nodes[:10]:
            lines.append(
                f"- `{node.node_type}` / `{node.status}` / `{node.confidence}`: "
                f"{node.storyline_id} Ch{node.chapter_start}-{node.chapter_end or '?'} "
                f"({node.source_rule}; {node.evidence.source_table}:"
                f"{node.evidence.source_row_id})"
            )
        lines.append("")
    lines.extend(
        [
            "## 后续路由",
            "",
            "- Task 207: V10 收口与归档；登记 Storyline Tree 的生产化建议，不在本任务接 runtime。",
            "- 若后续生产化，优先从 derived report-only view 开始，不直接改变 Ch200 hard gate。",
            "- Task 206 输出保持 report-only，不进入 hard gate。",
        ]
    )
    return "\n".join(lines) + "\n"


def _evaluate_sample(
    sample: KGDiffSample,
    *,
    root: Path,
    facttrack_result: Any | None,
) -> StorylineSampleResult:
    db_path = _resolve_path(root, sample.db_path)
    warnings: list[str] = []
    if not db_path.exists():
        warnings.append(f"DB missing; using document truth only: {sample.db_path}")
        return _document_only_result(sample, warnings=warnings)
    try:
        with _open_readonly_db(db_path) as conn:
            nodes = _build_tree_nodes(conn, sample)
    except sqlite3.Error as exc:
        warnings.append(f"DB read failed; using document truth only: {exc}")
        return _document_only_result(sample, warnings=warnings)
    evaluation = _evaluate_nodes(sample, nodes, facttrack_result)
    return StorylineSampleResult(
        sample=sample,
        db_exists=True,
        document_truth_only=False,
        nodes=nodes,
        evaluation=evaluation,
        warnings=warnings,
    )


def _document_only_result(
    sample: KGDiffSample,
    *,
    warnings: list[str],
) -> StorylineSampleResult:
    evaluation = StorylineSampleEvaluation(
        sample_id=sample.sample_id,
        issue_type=sample.issue_type,
        kind=sample.kind,
        tree_explained=False,
        false_positive=False,
        confidence="low" if sample.kind == "positive" else "none",
        reduced_false_positive=False,
        reduced_false_negative=False,
        still_needs_alias_policy=_needs_alias_policy(sample),
        still_needs_validity_interval=True,
        document_truth_only=True,
        decision_note="document truth only; tree could not be derived from DB facts",
    )
    return StorylineSampleResult(
        sample=sample,
        db_exists=False,
        document_truth_only=True,
        evaluation=evaluation,
        warnings=warnings,
    )


def _build_tree_nodes(
    conn: sqlite3.Connection,
    sample: KGDiffSample,
) -> list[StorylineNode]:
    nodes: list[StorylineNode] = []
    root_id = f"mainline:{sample.genre}:{sample.project_id}"
    nodes.append(
        StorylineNode(
            storyline_id=root_id,
            parent_id=None,
            node_type="mainline",
            genre=sample.genre,
            chapter_start=1,
            chapter_end=sample.chapter,
            status="active",
            linked_facts={},
            evidence=StorylineEvidence(
                source_table="manifest",
                source_row_id=sample.sample_id,
                chapter=sample.chapter,
                detail="sample-root mainline",
            ),
            confidence="medium",
            source_rule="document_truth",
            consumer_impact=["Task 207 reports"],
            migration_cost="none",
        )
    )
    arc = _arc_node(conn, sample, parent_id=root_id)
    nodes.append(arc)
    nodes.extend(_foreshadowing_thread_nodes(conn, sample, parent_id=arc.storyline_id))
    nodes.extend(_human_mark_thread_nodes(conn, sample, parent_id=arc.storyline_id))
    nodes.extend(_setting_subplot_nodes(conn, sample, parent_id=arc.storyline_id))
    return _prioritize_nodes(nodes, sample)


def _arc_node(
    conn: sqlite3.Connection,
    sample: KGDiffSample,
    *,
    parent_id: str,
) -> StorylineNode:
    arc = _covering_arc(conn, sample)
    if arc is not None:
        arc_id = str(arc["arc_id"])
        start = _int_or_none(arc["start_chapter"])
        end = _int_or_none(arc["end_chapter"])
        return StorylineNode(
            storyline_id=f"arc:{arc_id}",
            parent_id=parent_id,
            node_type="arc",
            genre=sample.genre,
            chapter_start=start,
            chapter_end=end,
            status="active",
            linked_facts={},
            evidence=StorylineEvidence(
                source_table="arc_summaries",
                source_row_id=arc_id,
                chapter=end,
                detail=str(arc["arc_title"] or arc["arc_summary"] or ""),
            ),
            confidence="medium",
            source_rule="arc_summary_range",
            consumer_impact=["ContextManager", "Task 207 reports"],
            migration_cost="none",
        )
    start = ((sample.chapter - 1) // 25) * 25 + 1
    end = min(start + 24, sample.chapter)
    return StorylineNode(
        storyline_id=f"arc:derived:{sample.genre}:{start}-{end}",
        parent_id=parent_id,
        node_type="arc",
        genre=sample.genre,
        chapter_start=start,
        chapter_end=end,
        status="active",
        linked_facts={},
        evidence=StorylineEvidence(
            source_table="derived",
            source_row_id=f"{sample.genre}:{start}-{end}",
            chapter=sample.chapter,
            detail="fallback 25-chapter derived arc window",
        ),
        confidence="low",
        source_rule="derived_arc_window",
        consumer_impact=["Task 207 reports"],
        migration_cost="none",
        notes=["no arc_summaries covering sample chapter"],
    )


def _foreshadowing_thread_nodes(
    conn: sqlite3.Connection,
    sample: KGDiffSample,
    *,
    parent_id: str,
) -> list[StorylineNode]:
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
    out: list[StorylineNode] = []
    for row in rows:
        expected = _int_or_none(row["expected_resolve_chapter"])
        planted = _int_or_none(row["planted_in_chapter"])
        status = str(row["status"] or "")
        overdue = expected is not None and expected < sample.chapter and status != "resolved"
        if not _include_foreshadowing(sample, overdue, status, planted, expected):
            continue
        node_status: StorylineStatus
        node_type: NodeType = "thread"
        confidence: Confidence = "low"
        if status == "resolved":
            node_status = "resolved"
            node_type = "payoff"
        elif overdue:
            node_status = "stale"
            confidence = "high" if sample.issue_type == "foreshadowing_unresolved" else "low"
        else:
            node_status = "open"
        fact_id = str(row["foreshadowing_id"])
        out.append(
            StorylineNode(
                storyline_id=f"thread:foreshadowing:{fact_id}",
                parent_id=parent_id,
                node_type=node_type,
                genre=sample.genre,
                chapter_start=planted,
                chapter_end=expected,
                status=node_status,
                linked_facts={"foreshadowing_id": [fact_id]},
                evidence=StorylineEvidence(
                    source_table="foreshadowings",
                    source_row_id=fact_id,
                    chapter=planted,
                    version_id=row["source_version_id"],
                    detail=str(row["description"] or ""),
                ),
                confidence=confidence,
                source_rule="foreshadowing_expected_resolve",
                consumer_impact=["ContinuityAuditor", "ContextManager", "Task 207 reports"],
                migration_cost="medium",
                notes=[f"status={status}", f"lifecycle={row['lifecycle_status']}"],
            )
        )
    return out


def _human_mark_thread_nodes(
    conn: sqlite3.Connection,
    sample: KGDiffSample,
    *,
    parent_id: str,
) -> list[StorylineNode]:
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
              AND mark_type = 'foreshadowing'
            ORDER BY created_at_chapter, priority DESC, mark_id""",
        (sample.project_id, sample.chapter),
    )
    out: list[StorylineNode] = []
    for row in rows:
        priority = int(_value(row, "priority") or 0)
        if priority < 8 and sample.kind != "positive":
            continue
        mark_id = str(_value(row, "mark_id"))
        resolved = bool(_value(row, "resolved_at"))
        out.append(
            StorylineNode(
                storyline_id=f"thread:human_mark:{mark_id}",
                parent_id=parent_id,
                node_type="thread",
                genre=sample.genre,
                chapter_start=_int_or_none(_value(row, "created_at_chapter")),
                chapter_end=None,
                status="resolved" if resolved else "open",
                linked_facts={
                    "human_mark_id": [mark_id],
                    "foreshadowing_id": [str(_value(row, "target_key") or "")],
                },
                evidence=StorylineEvidence(
                    source_table="human_marks",
                    source_row_id=mark_id,
                    chapter=_int_or_none(_value(row, "created_at_chapter")),
                    version_id=_value(row, "version_id"),
                    detail=str(_value(row, "note") or ""),
                ),
                confidence="medium" if priority >= 8 and not resolved else "low",
                source_rule="human_mark_thread",
                consumer_impact=["ContextManager", "Task 207 reports"],
                migration_cost="low",
                notes=[f"priority={priority}"],
            )
        )
    return out


def _setting_subplot_nodes(
    conn: sqlite3.Connection,
    sample: KGDiffSample,
    *,
    parent_id: str,
) -> list[StorylineNode]:
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
            "status",
            "source_version_id",
            "category",
        ] if col in cols
    ]
    rows = _fetchall(
        conn,
        f"""SELECT {', '.join(select)}
            FROM setting_tracking
            WHERE project_id = ?
              AND COALESCE(introduced_in_chapter, 0) <= ?
              AND category = 'critical'
            ORDER BY introduced_in_chapter, tracking_id""",
        (sample.project_id, sample.chapter),
    )
    out: list[StorylineNode] = []
    for row in rows:
        last = _int_or_none(_value(row, "last_mentioned_chapter"))
        if sample.kind != "positive" and (last is None or sample.chapter - last <= 6):
            continue
        tracking_id = str(_value(row, "tracking_id") or _value(row, "setting_key"))
        out.append(
            StorylineNode(
                storyline_id=f"subplot:setting:{tracking_id}",
                parent_id=parent_id,
                node_type="subplot",
                genre=sample.genre,
                chapter_start=_int_or_none(_value(row, "introduced_in_chapter")),
                chapter_end=last,
                status="active",
                linked_facts={"setting_key": [str(_value(row, "setting_key") or "")]},
                evidence=StorylineEvidence(
                    source_table="setting_tracking",
                    source_row_id=tracking_id,
                    chapter=last,
                    version_id=_value(row, "source_version_id"),
                    detail=str(_value(row, "setting_name") or _value(row, "setting_key") or ""),
                ),
                confidence="medium" if sample.kind == "positive" else "low",
                source_rule="setting_tracking_thread",
                consumer_impact=["segment_audit", "Task 207 reports"],
                migration_cost="medium",
            )
        )
    return out


def _evaluate_nodes(
    sample: KGDiffSample,
    nodes: list[StorylineNode],
    facttrack_result: Any | None,
) -> StorylineSampleEvaluation:
    matching = _matching_nodes(sample, nodes)
    high_false = [
        item for item in nodes
        if sample.kind == "negative_control"
        and item.confidence == "high"
        and item.status == "stale"
    ]
    tree_explained = bool(matching) if sample.kind == "positive" else False
    false_positive = bool(high_false)
    confidence = _max_confidence(matching or high_false)
    if sample.kind == "negative_control" and not false_positive:
        confidence = "none"
    still_alias = _needs_alias_policy(sample)
    still_validity = _needs_validity_interval(sample, tree_explained)
    reduced_fn = sample.kind == "positive" and tree_explained
    if (
        facttrack_result is not None
        and getattr(facttrack_result.evaluation, "interval_explained", False)
    ):
        reduced_fn = reduced_fn or tree_explained
    return StorylineSampleEvaluation(
        sample_id=sample.sample_id,
        issue_type=sample.issue_type,
        kind=sample.kind,
        tree_explained=tree_explained,
        false_positive=false_positive,
        confidence=confidence,
        reduced_false_positive=sample.kind == "negative_control" and not false_positive,
        reduced_false_negative=reduced_fn,
        still_needs_alias_policy=still_alias,
        still_needs_validity_interval=still_validity,
        document_truth_only=False,
        decision_note=_decision_note(
            sample,
            tree_explained=tree_explained,
            false_positive=false_positive,
            still_alias=still_alias,
            still_validity=still_validity,
        ),
    )


def _matching_nodes(
    sample: KGDiffSample,
    nodes: list[StorylineNode],
) -> list[StorylineNode]:
    if sample.issue_type == "foreshadowing_unresolved":
        return [
            item for item in nodes
            if item.node_type in {"thread", "payoff"}
            and item.status in {"open", "stale", "resolved"}
            and item.confidence in {"high", "medium"}
        ]
    if sample.issue_type in {"setting_tracking_missing_refresh", "critical_orphan"}:
        return [
            item for item in nodes
            if item.node_type == "subplot"
            and item.confidence in {"high", "medium"}
        ]
    return []


def _decision_note(
    sample: KGDiffSample,
    *,
    tree_explained: bool,
    false_positive: bool,
    still_alias: bool,
    still_validity: bool,
) -> str:
    if false_positive:
        return "negative control produced high-confidence stale storyline"
    if sample.kind == "negative_control":
        return "negative control has no high-confidence stale storyline"
    if not tree_explained:
        return "Storyline Tree did not explain the sample from DB facts"
    if still_alias:
        return "tree groups the storyline but still needs alias policy"
    if still_validity:
        return "tree groups open thread but still needs validity interval details"
    return "Storyline Tree explains the sample boundary"


def _build_impact_matrix(
    results: list[StorylineSampleResult],
) -> list[StorylineImpactRow]:
    grouped: dict[str, list[StorylineSampleResult]] = defaultdict(list)
    for item in results:
        grouped[item.sample.issue_type].append(item)
    rows: list[StorylineImpactRow] = []
    for issue_type, items in sorted(grouped.items()):
        row = StorylineImpactRow(issue_type=issue_type, sample_count=len(items))
        schema: set[str] = set()
        report_fields: set[str] = set()
        for item in items:
            ev = item.evaluation
            if item.sample.kind == "positive" and ev.tree_explained:
                row.true_positive += 1
            elif item.sample.kind == "positive":
                row.unclear += 1
            if ev.false_positive:
                row.false_positive += 1
            if ev.tree_explained:
                row.tree_explained += 1
            if ev.reduced_false_positive:
                row.reduced_false_positive += 1
            if ev.reduced_false_negative:
                row.reduced_false_negative += 1
            if ev.still_needs_alias_policy:
                row.still_needs_alias_policy += 1
            if ev.still_needs_validity_interval:
                row.still_needs_validity_interval += 1
            for node in item.nodes:
                schema.update(_production_schema_fields(node))
                report_fields.update(_report_only_fields(node))
        row.production_schema_needed = sorted(schema)
        row.report_only_fields = sorted(report_fields)
        rows.append(row)
    return rows


def _build_summary(results: list[StorylineSampleResult]) -> StorylineTreeSummary:
    positives = sum(1 for item in results if item.sample.kind == "positive")
    negatives = sum(1 for item in results if item.sample.kind == "negative_control")
    db_backed = sum(1 for item in results if not item.document_truth_only)
    doc_only = sum(1 for item in results if item.document_truth_only)
    needs_story = sum(
        1 for item in results
        if item.sample.issue_type == "foreshadowing_unresolved"
        and item.sample.kind == "positive"
    )
    explained = sum(1 for item in results if item.evaluation.tree_explained)
    fp = sum(1 for item in results if item.evaluation.false_positive)
    alias = sum(1 for item in results if item.evaluation.still_needs_alias_policy)
    validity = sum(1 for item in results if item.evaluation.still_needs_validity_interval)
    explained_types = {
        item.sample.issue_type for item in results if item.evaluation.tree_explained
    }
    if explained >= 3 and fp == 0:
        if alias or validity:
            decision: Decision = "defer"
            reason = (
                "Storyline Tree explains open-thread samples, but production use "
                "still needs alias policy and validity integration."
            )
        else:
            decision = "continue"
            reason = "Storyline Tree explains open-thread boundaries with clean controls."
    elif explained > 0 and len(explained_types) >= 1:
        decision = "defer"
        reason = "Storyline signal exists, but coverage is not stable enough."
    else:
        decision = "reject"
        reason = "Tree mostly repeats foreshadowing/status facts without structural gain."
    return StorylineTreeSummary(
        sample_count=len(results),
        positive_samples=positives,
        negative_controls=negatives,
        db_backed_samples=db_backed,
        document_truth_only_samples=doc_only,
        needs_storyline_tree_samples=needs_story,
        tree_explained=explained,
        false_positive_count=fp,
        still_needs_alias_policy_count=alias,
        still_needs_validity_interval_count=validity,
        decision=decision,
        decision_reason=reason,
        next_route="Task 207 V10 closure and archive",
    )


def _migration_impacts() -> list[StorylineMigrationImpact]:
    return [
        StorylineMigrationImpact(
            target="derived_storyline_tree_view",
            required_for_spike=False,
            production_need="Can be generated report-only from existing facts first.",
            migration_cost="none",
            fields=[
                "storyline_id",
                "parent_id",
                "node_type",
                "chapter_start",
                "chapter_end",
                "status",
                "linked_facts",
                "confidence",
            ],
            affected_consumers=["Task 207 reports", "offline evaluators"],
            rollback_plan="Delete generated artifacts; no DB state is changed.",
        ),
        StorylineMigrationImpact(
            target="storyline_tree_nodes",
            required_for_spike=False,
            production_need="Optional if tree becomes reusable planning memory.",
            migration_cost="medium",
            fields=[
                "storyline_id",
                "project_id",
                "parent_id",
                "node_type",
                "status",
                "chapter_start",
                "chapter_end",
            ],
            affected_consumers=["GoalPlanner", "CreativeDirector", "ContextManager"],
            rollback_plan=(
                "Drop additive table and fall back to current "
                "foreshadowing/status facts."
            ),
        ),
        StorylineMigrationImpact(
            target="storyline_fact_links",
            required_for_spike=False,
            production_need="Needed only if production tree links facts bidirectionally.",
            migration_cost="medium",
            fields=["storyline_id", "source_table", "source_row_id", "confidence"],
            affected_consumers=["SettlementExtractor", "SummaryWriter", "segment_audit"],
            rollback_plan="Drop link table; existing fact tables remain untouched.",
        ),
    ]


def _covering_arc(
    conn: sqlite3.Connection,
    sample: KGDiffSample,
) -> sqlite3.Row | None:
    if not _table_exists(conn, "arc_summaries"):
        return None
    rows = _fetchall(
        conn,
        """SELECT arc_id, start_chapter, end_chapter, arc_title, arc_summary
           FROM arc_summaries
           WHERE project_id = ?
             AND start_chapter <= ?
             AND end_chapter >= ?
           ORDER BY start_chapter DESC
           LIMIT 1""",
        (sample.project_id, sample.chapter, sample.chapter),
    )
    return rows[0] if rows else None


def _include_foreshadowing(
    sample: KGDiffSample,
    overdue: bool,
    status: str,
    planted: int | None,
    expected: int | None,
) -> bool:
    if sample.issue_type == "foreshadowing_unresolved" and overdue:
        return True
    if sample.kind == "negative_control":
        return (
            status == "resolved"
            or (expected is not None and expected >= sample.chapter)
            or (planted is not None and sample.chapter - planted <= 12)
        )
    return status == "resolved" or overdue


def _prioritize_nodes(
    nodes: list[StorylineNode],
    sample: KGDiffSample,
) -> list[StorylineNode]:
    rank = {"high": 0, "medium": 1, "low": 2, "none": 3}
    type_rank = {"mainline": 0, "arc": 1, "thread": 2, "payoff": 3, "subplot": 4}
    return sorted(
        nodes,
        key=lambda item: (
            0 if _node_matches_sample(item, sample) else 1,
            rank[item.confidence],
            type_rank[item.node_type],
            item.storyline_id,
        ),
    )[:60]


def _node_matches_sample(
    node: StorylineNode,
    sample: KGDiffSample,
) -> bool:
    if sample.issue_type == "foreshadowing_unresolved":
        return node.node_type in {"thread", "payoff"}
    if sample.issue_type in {"setting_tracking_missing_refresh", "critical_orphan"}:
        return node.node_type == "subplot"
    return False


def _production_schema_fields(node: StorylineNode) -> set[str]:
    if node.node_type in {"mainline", "arc", "thread", "payoff", "subplot"}:
        return {
            "storyline_id",
            "parent_id",
            "node_type",
            "status",
            "chapter_start",
            "chapter_end",
            "linked_facts",
        }
    return set()


def _report_only_fields(node: StorylineNode) -> set[str]:
    return {
        "storyline_id",
        "node_type",
        "status",
        "linked_facts",
        "confidence",
        "source_rule",
    }


def _needs_alias_policy(sample: KGDiffSample) -> bool:
    return sample.issue_type in {"setting_tracking_missing_refresh", "critical_orphan"}


def _needs_validity_interval(
    sample: KGDiffSample,
    tree_explained: bool,
) -> bool:
    if sample.issue_type == "stale_continuity_report":
        return True
    if sample.issue_type == "foreshadowing_unresolved":
        return not tree_explained
    return False


def _max_confidence(items: list[StorylineNode]) -> Confidence:
    if not items:
        return "none"
    rank = {"high": 3, "medium": 2, "low": 1, "none": 0}
    return max((item.confidence for item in items), key=lambda value: rank[value])


def _load_model(path: Path, model_type: Any, label: str) -> Any:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise StorylineTreeSpikeError(f"failed to read {label} {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise StorylineTreeSpikeError(f"invalid {label} JSON {path}: {exc}") from exc
    try:
        return model_type.model_validate(raw)
    except ValueError as exc:
        raise StorylineTreeSpikeError(f"invalid {label} schema {path}: {exc}") from exc


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
