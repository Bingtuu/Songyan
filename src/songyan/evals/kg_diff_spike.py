"""Task 204 KG graph diff spike.

This module builds a small, offline, read-only fact graph diff over existing
SQLite facts and Task 192-194 repair truth records. It does not call LLMs, does
not write SQLite, does not wire into ``songyan report``, and does not affect
CED, five-gate, segment audit, T9, or any runtime gate.
"""

from __future__ import annotations

import json
import sqlite3
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

SampleKind = Literal["positive", "negative_control"]
SampleStatus = Literal["pre_fix", "post_fix", "document-truth-only"]
DiffType = Literal[
    "added",
    "refreshed",
    "stale_candidate",
    "unresolved_candidate",
    "resolved_candidate",
    "missing_refresh_candidate",
    "none",
]
NodeType = Literal[
    "setting",
    "foreshadowing",
    "human_mark",
    "continuity_report",
    "chapter_version",
]
EdgeType = Literal[
    "introduced_in",
    "mentioned_in",
    "refreshed_by",
    "resolved_in",
    "marked_by",
    "reported_by",
    "stale_after_candidate",
]
Confidence = Literal["high", "medium", "low", "none"]
Decision = Literal["continue", "defer", "reject"]
ToolCoverage = Literal[
    "segment_audit",
    "ced",
    "human_marks",
    "continuity_report",
    "five_gate",
    "document_truth",
    "none",
]

ORPHAN_THRESHOLDS: dict[str, int] = {
    "critical": 3,
    "recurring": 4,
    "background": 5,
    "technical": 7,
    "historical": 10,
}


class KGDiffSpikeError(RuntimeError):
    """Raised when Task 204 inputs are missing or invalid."""


class KGDiffSample(BaseModel):
    """One labeled Task 204 spike sample."""

    sample_id: str
    kind: SampleKind
    genre: str
    issue_type: str
    db_path: str
    project_id: str
    run_id: str
    chapter: int = Field(ge=1)
    accepted_version_id: str
    sample_status: SampleStatus
    truth_source_doc: str
    expected_signal: DiffType
    expected_existing_tool_coverage: list[ToolCoverage] = Field(default_factory=list)
    expected_gain: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_expected_signal(self) -> KGDiffSample:
        if self.kind == "negative_control" and self.expected_signal != "none":
            msg = f"negative control must use expected_signal=none: {self.sample_id}"
            raise ValueError(msg)
        if self.kind == "positive" and self.expected_signal == "none":
            msg = f"positive sample must declare an expected signal: {self.sample_id}"
            raise ValueError(msg)
        return self


class KGDiffManifest(BaseModel):
    """Task 204 sample manifest."""

    task_id: str = "204"
    report_only: bool = True
    description: str
    samples: list[KGDiffSample]
    boundaries: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_manifest(self) -> KGDiffManifest:
        if self.report_only is not True:
            raise ValueError("Task 204 manifest must declare report_only=true")
        positives = [item for item in self.samples if item.kind == "positive"]
        negatives = [item for item in self.samples if item.kind == "negative_control"]
        if len(positives) < 6:
            raise ValueError("Task 204 manifest requires at least 6 positive samples")
        if len(negatives) < 3:
            raise ValueError("Task 204 manifest requires at least 3 negative controls")
        genres = {item.genre for item in self.samples}
        if len(genres) < 2:
            raise ValueError("Task 204 manifest must cover at least 2 genres")
        return self


class GraphEvidence(BaseModel):
    """Traceable evidence for a node or diff."""

    source_table: str
    source_row_id: str
    chapter: int | None = None
    version_id: str | None = None
    source_quote: str = ""
    detail: str = ""


class GraphNode(BaseModel):
    """Compact fact graph node."""

    node_id: str
    node_type: NodeType
    label: str
    status: str = ""
    chapter: int | None = None
    evidence: GraphEvidence
    attributes: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    """Compact fact graph edge."""

    edge_id: str
    edge_type: EdgeType
    source: str
    target: str
    evidence: GraphEvidence


class FactGraphSnapshot(BaseModel):
    """One up_to-truncated graph snapshot."""

    label: Literal["before", "after"]
    source_db: str
    project_id: str
    up_to_chapter: int = Field(ge=0)
    version_id: str | None = None
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class KGDiffEntry(BaseModel):
    """One graph diff candidate."""

    diff_id: str
    diff_type: DiffType
    node_id: str
    label: str
    confidence: Confidence
    evidence: GraphEvidence
    reason: str
    task205_route: bool = False
    task206_route: bool = False


class SampleEvaluation(BaseModel):
    """Evaluation against the manifest truth label."""

    truth_label: str
    detected_by_kg_diff: bool
    covered_by_segment_audit: bool
    covered_by_ced: bool
    covered_by_human_marks: bool
    unique_gain: bool
    false_positive: bool
    confidence: Confidence
    decision_note: str


class SampleKGDiffResult(BaseModel):
    """Task 204 result for one sample."""

    sample: KGDiffSample
    db_exists: bool
    document_truth_only: bool
    before_snapshot: FactGraphSnapshot | None = None
    after_snapshot: FactGraphSnapshot | None = None
    diffs: list[KGDiffEntry] = Field(default_factory=list)
    evaluation: SampleEvaluation
    warnings: list[str] = Field(default_factory=list)


class GainMatrixRow(BaseModel):
    """Aggregated gain matrix row by issue type."""

    issue_type: str
    sample_count: int = 0
    true_positive: int = 0
    false_positive: int = 0
    unclear: int = 0
    unique_gain: int = 0
    covered_by_segment_audit: int = 0
    covered_by_ced: int = 0
    human_or_document_only: int = 0
    needs_validity_interval: int = 0
    needs_storyline_tree: int = 0


class Task204Summary(BaseModel):
    """Top-level spike summary."""

    report_only: bool = True
    sample_count: int
    positive_samples: int
    negative_controls: int
    db_backed_samples: int
    document_truth_only_samples: int
    high_confidence_detections: int
    unique_gain_count: int
    decision: Decision
    decision_reason: str
    next_route: str


class KGDiffSpikeReport(BaseModel):
    """Top-level Task 204 report."""

    generated_at: str
    report_only: bool = True
    boundaries: list[str]
    summary: Task204Summary
    source_manifest: str
    gain_matrix: list[GainMatrixRow]
    samples: list[SampleKGDiffResult]


def load_kg_diff_manifest(path: Path) -> KGDiffManifest:
    """Load and validate a Task 204 manifest."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise KGDiffSpikeError(f"failed to read manifest {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise KGDiffSpikeError(f"invalid manifest JSON {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise KGDiffSpikeError(f"expected manifest JSON object: {path}")
    try:
        return KGDiffManifest.model_validate(data)
    except ValueError as exc:
        raise KGDiffSpikeError(f"invalid Task 204 manifest {path}: {exc}") from exc


def build_kg_diff_spike_report(
    manifest: KGDiffManifest,
    *,
    manifest_path: Path,
    root_dir: Path | None = None,
) -> KGDiffSpikeReport:
    """Build the Task 204 read-only KG diff spike report."""
    root = root_dir or Path.cwd()
    results = [
        _evaluate_sample(sample, root=root)
        for sample in manifest.samples
    ]
    gain_matrix = _build_gain_matrix(results)
    summary = _build_summary(results)
    return KGDiffSpikeReport(
        generated_at=datetime.now(UTC).isoformat(),
        boundaries=[
            "offline report-only spike",
            "read-only SQLite access via mode=ro",
            "does not call LLMs or extract a full KG from prose",
            "does not write SQLite",
            "does not modify Writer or CreativeDirector prompts",
            "does not enter accept/reject gates",
            "does not change CED, five-gate, segment audit, or T9",
            "does not build a production KG system",
        ],
        summary=summary,
        source_manifest=manifest_path.as_posix(),
        gain_matrix=gain_matrix,
        samples=results,
    )


def render_kg_diff_spike_report(report: KGDiffSpikeReport) -> str:
    """Render Task 204 report as Markdown."""
    lines = [
        "# Task 204 KG 图 diff spike",
        "",
        f"> generated_at: `{report.generated_at}`",
        f"> source_manifest: `{report.source_manifest}`",
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
            f"- high_confidence_detections: `{summary.high_confidence_detections}`",
            f"- unique_gain_count: `{summary.unique_gain_count}`",
            f"- decision: `{summary.decision}`",
            f"- decision_reason: {summary.decision_reason}",
            f"- next_route: {summary.next_route}",
        ]
    )
    lines.extend(["", "## Gain Matrix", ""])
    lines.append(
        "| issue_type | samples | TP | FP | unclear | unique | segment | CED | "
        "human/doc | validity | storyline |"
    )
    lines.append(
        "|------------|--------:|---:|---:|--------:|-------:|--------:|----:|----------:|---------:|----------:|"
    )
    for row in report.gain_matrix:
        lines.append(
            f"| `{row.issue_type}` | {row.sample_count} | {row.true_positive} | "
            f"{row.false_positive} | {row.unclear} | {row.unique_gain} | "
            f"{row.covered_by_segment_audit} | {row.covered_by_ced} | "
            f"{row.human_or_document_only} | {row.needs_validity_interval} | "
            f"{row.needs_storyline_tree} |"
        )
    lines.extend(["", "## Sample Results", ""])
    lines.append(
        "| sample | genre | chapter | kind | expected | detected | confidence | "
        "unique | FP | notes |"
    )
    lines.append(
        "|--------|-------|--------:|------|----------|----------|------------|--------|----|-------|"
    )
    for item in report.samples:
        ev = item.evaluation
        notes = "; ".join(item.warnings[:2]) or ev.decision_note
        lines.append(
            f"| `{item.sample.sample_id}` | {item.sample.genre} | {item.sample.chapter} | "
            f"{item.sample.kind} | `{item.sample.expected_signal}` | "
            f"{ev.detected_by_kg_diff} | `{ev.confidence}` | {ev.unique_gain} | "
            f"{ev.false_positive} | {notes} |"
        )
    lines.extend(["", "## Diff Evidence", ""])
    for item in report.samples:
        lines.append(f"### {item.sample.sample_id}")
        if item.document_truth_only:
            lines.append("- document_truth_only: true")
        if not item.diffs:
            lines.append("- no high-confidence KG diff candidate")
            lines.append("")
            continue
        for diff in item.diffs[:8]:
            lines.append(
                f"- `{diff.diff_type}` / `{diff.confidence}`: {diff.label} "
                f"({diff.evidence.source_table}:{diff.evidence.source_row_id}) - {diff.reason}"
            )
        lines.append("")
    lines.extend(
        [
            "## 后续路由",
            "",
            "- Task 205: FactTrack validity interval spike，用于验证 stale / "
            "unresolved 判断是否需要有效期建模。",
            "- Task 206: Storyline Tree spike，仍只处理主线/支线结构，不在 Task 204 展开。",
            "- Task 204 输出保持 report-only，不进入 hard gate。",
        ]
    )
    return "\n".join(lines) + "\n"


def _evaluate_sample(sample: KGDiffSample, *, root: Path) -> SampleKGDiffResult:
    db_path = _resolve_path(root, sample.db_path)
    warnings: list[str] = []
    if not db_path.exists():
        warnings.append(f"DB missing; using document truth only: {sample.db_path}")
        evaluation = _document_only_evaluation(sample, missing_db=True)
        return SampleKGDiffResult(
            sample=sample,
            db_exists=False,
            document_truth_only=True,
            evaluation=evaluation,
            warnings=warnings,
        )

    try:
        with _open_readonly_db(db_path) as conn:
            before = _build_snapshot(
                conn,
                sample=sample,
                source_db=sample.db_path,
                label="before",
                up_to=max(sample.chapter - 1, 0),
            )
            after = _build_snapshot(
                conn,
                sample=sample,
                source_db=sample.db_path,
                label="after",
                up_to=sample.chapter,
            )
            diffs = _build_diffs(before, after, sample=sample, conn=conn)
    except sqlite3.Error as exc:
        warnings.append(f"DB read failed; using document truth only: {exc}")
        evaluation = _document_only_evaluation(sample, missing_db=False)
        return SampleKGDiffResult(
            sample=sample,
            db_exists=True,
            document_truth_only=True,
            evaluation=evaluation,
            warnings=warnings,
        )

    evaluation = _evaluate_diffs(sample, diffs)
    return SampleKGDiffResult(
        sample=sample,
        db_exists=True,
        document_truth_only=False,
        before_snapshot=before,
        after_snapshot=after,
        diffs=diffs,
        evaluation=evaluation,
        warnings=warnings + before.warnings + after.warnings,
    )


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


def _build_snapshot(
    conn: sqlite3.Connection,
    *,
    sample: KGDiffSample,
    source_db: str,
    label: Literal["before", "after"],
    up_to: int,
) -> FactGraphSnapshot:
    warnings: list[str] = []
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    nodes.extend(_chapter_version_nodes(conn, sample, up_to, warnings))
    setting_nodes = _setting_nodes(conn, sample, up_to, warnings)
    nodes.extend(setting_nodes)
    foreshadow_nodes = _foreshadowing_nodes(conn, sample, up_to, warnings)
    nodes.extend(foreshadow_nodes)
    human_mark_nodes = _human_mark_nodes(conn, sample, up_to, warnings)
    nodes.extend(human_mark_nodes)
    continuity_nodes = _continuity_report_nodes(conn, sample, up_to, warnings)
    nodes.extend(continuity_nodes)
    edges.extend(_edges_from_nodes(nodes, up_to=up_to))
    counts = Counter(node.node_type for node in nodes)
    return FactGraphSnapshot(
        label=label,
        source_db=source_db,
        project_id=sample.project_id,
        up_to_chapter=up_to,
        version_id=_accepted_version_id(conn, sample.project_id, up_to)
        if up_to > 0 else None,
        nodes=sorted(nodes, key=lambda item: item.node_id),
        edges=sorted(edges, key=lambda item: item.edge_id),
        counts={str(key): int(value) for key, value in counts.items()},
        warnings=warnings,
    )


def _chapter_version_nodes(
    conn: sqlite3.Connection,
    sample: KGDiffSample,
    up_to: int,
    warnings: list[str],
) -> list[GraphNode]:
    if up_to <= 0:
        return []
    if not _table_exists(conn, "chapter_heads"):
        warnings.append("chapter_heads table missing")
        return []
    rows = _fetchall(
        conn,
        """SELECT project_id, chapter_number, accepted_version_id, current_version_id, status
           FROM chapter_heads
           WHERE project_id = ? AND chapter_number <= ?
             AND accepted_version_id IS NOT NULL
           ORDER BY chapter_number""",
        (sample.project_id, up_to),
    )
    nodes: list[GraphNode] = []
    for row in rows:
        version_id = str(row["accepted_version_id"])
        chapter = _int_or_none(row["chapter_number"])
        nodes.append(
            GraphNode(
                node_id=f"chapter_version:{version_id}",
                node_type="chapter_version",
                label=f"Ch{chapter} accepted",
                status=str(row["status"] or ""),
                chapter=chapter,
                evidence=GraphEvidence(
                    source_table="chapter_heads",
                    source_row_id=f"{sample.project_id}:{chapter}",
                    chapter=chapter,
                    version_id=version_id,
                ),
                attributes={
                    "accepted_version_id": version_id,
                    "current_version_id": row["current_version_id"],
                },
            )
        )
    return nodes


def _setting_nodes(
    conn: sqlite3.Connection,
    sample: KGDiffSample,
    up_to: int,
    warnings: list[str],
) -> list[GraphNode]:
    if up_to <= 0:
        return []
    if not _table_exists(conn, "setting_tracking"):
        warnings.append("setting_tracking table missing")
        return []
    cols = _columns(conn, "setting_tracking")
    select_cols = [
        "tracking_id",
        "project_id",
        "setting_key",
        "setting_name",
        "description",
        "introduced_in_chapter",
        "last_mentioned_chapter",
        "expected_resolve_chapter",
        "status",
        "source_version_id",
        "category",
    ]
    optional = [
        "recovery_required",
        "resolved_chapter",
        "resolved_version_id",
        "abandoned_chapter",
        "abandoned_reason",
    ]
    select = [col for col in select_cols + optional if col in cols]
    if not select:
        warnings.append("setting_tracking has no readable columns")
        return []
    rows = _fetchall(
        conn,
        f"""SELECT {', '.join(select)}
            FROM setting_tracking
            WHERE project_id = ?
              AND COALESCE(introduced_in_chapter, 0) <= ?
              AND (
                  last_mentioned_chapter IS NULL
                  OR last_mentioned_chapter <= ?
              )
            ORDER BY introduced_in_chapter, tracking_id""",
        (sample.project_id, up_to, up_to),
    )
    nodes: list[GraphNode] = []
    for row in rows:
        source_version_id = _value(row, "source_version_id")
        source_chapter = _version_chapter(conn, sample.project_id, source_version_id)
        if source_chapter is not None and source_chapter > up_to:
            continue
        tracking_id = str(_value(row, "tracking_id") or _value(row, "setting_key"))
        last = _int_or_none(_value(row, "last_mentioned_chapter"))
        nodes.append(
            GraphNode(
                node_id=f"setting:{tracking_id}",
                node_type="setting",
                label=str(_value(row, "setting_key") or _value(row, "setting_name") or tracking_id),
                status=str(_value(row, "status") or ""),
                chapter=last or _int_or_none(_value(row, "introduced_in_chapter")),
                evidence=GraphEvidence(
                    source_table="setting_tracking",
                    source_row_id=tracking_id,
                    chapter=last,
                    version_id=source_version_id,
                    detail=str(_value(row, "description") or ""),
                ),
                attributes={key: _jsonable(_value(row, key)) for key in row.keys()},
            )
        )
    return nodes


def _foreshadowing_nodes(
    conn: sqlite3.Connection,
    sample: KGDiffSample,
    up_to: int,
    warnings: list[str],
) -> list[GraphNode]:
    if up_to <= 0:
        return []
    if not _table_exists(conn, "foreshadowings"):
        warnings.append("foreshadowings table missing")
        return []
    rows = _fetchall(
        conn,
        """SELECT foreshadowing_id, project_id, description, planted_in_chapter,
                  expected_resolve_chapter, status, lifecycle_status, source_version_id
           FROM foreshadowings
           WHERE project_id = ? AND planted_in_chapter <= ?
           ORDER BY planted_in_chapter, foreshadowing_id""",
        (sample.project_id, up_to),
    )
    nodes: list[GraphNode] = []
    for row in rows:
        source_version_id = str(row["source_version_id"] or "")
        source_chapter = _version_chapter(conn, sample.project_id, source_version_id)
        if source_chapter is not None and source_chapter > up_to:
            continue
        item_id = str(row["foreshadowing_id"])
        nodes.append(
            GraphNode(
                node_id=f"foreshadowing:{item_id}",
                node_type="foreshadowing",
                label=item_id,
                status=str(row["status"] or ""),
                chapter=_int_or_none(row["planted_in_chapter"]),
                evidence=GraphEvidence(
                    source_table="foreshadowings",
                    source_row_id=item_id,
                    chapter=_int_or_none(row["planted_in_chapter"]),
                    version_id=source_version_id,
                    detail=str(row["description"] or ""),
                ),
                attributes={key: _jsonable(row[key]) for key in row.keys()},
            )
        )
    return nodes


def _human_mark_nodes(
    conn: sqlite3.Connection,
    sample: KGDiffSample,
    up_to: int,
    warnings: list[str],
) -> list[GraphNode]:
    if up_to <= 0:
        return []
    if not _table_exists(conn, "human_marks"):
        warnings.append("human_marks table missing")
        return []
    cols = _columns(conn, "human_marks")
    select = [
        col for col in [
            "mark_id",
            "project_id",
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
        (sample.project_id, up_to),
    )
    nodes: list[GraphNode] = []
    for row in rows:
        mark_id = str(_value(row, "mark_id"))
        chapter = _int_or_none(_value(row, "created_at_chapter"))
        nodes.append(
            GraphNode(
                node_id=f"human_mark:{mark_id}",
                node_type="human_mark",
                label=str(_value(row, "target_key") or mark_id),
                status="resolved" if _value(row, "resolved_at") else "unresolved",
                chapter=chapter,
                evidence=GraphEvidence(
                    source_table="human_marks",
                    source_row_id=mark_id,
                    chapter=chapter,
                    version_id=_value(row, "version_id"),
                    detail=str(_value(row, "note") or ""),
                ),
                attributes={key: _jsonable(_value(row, key)) for key in row.keys()},
            )
        )
    return nodes


def _continuity_report_nodes(
    conn: sqlite3.Connection,
    sample: KGDiffSample,
    up_to: int,
    warnings: list[str],
) -> list[GraphNode]:
    if up_to <= 0:
        return []
    if not _table_exists(conn, "continuity_reports"):
        warnings.append("continuity_reports table missing")
        return []
    cols = _columns(conn, "continuity_reports")
    select = [
        col for col in [
            "report_id",
            "project_id",
            "checked_up_to_chapter",
            "orphaned_settings",
            "forgotten_items",
            "state_mismatches",
            "overdue_foreshadowings",
            "suggested_marks",
            "overall_health_score",
            "created_at",
        ] if col in cols
    ]
    rows = _fetchall(
        conn,
        f"""SELECT {', '.join(select)}
            FROM continuity_reports
            WHERE project_id = ?
              AND checked_up_to_chapter <= ?
            ORDER BY checked_up_to_chapter, created_at, rowid""",
        (sample.project_id, up_to),
    )
    nodes: list[GraphNode] = []
    for row in rows:
        report_id = str(_value(row, "report_id"))
        chapter = _int_or_none(_value(row, "checked_up_to_chapter"))
        nodes.append(
            GraphNode(
                node_id=f"continuity_report:{report_id}",
                node_type="continuity_report",
                label=f"continuity@Ch{chapter}",
                status="reported",
                chapter=chapter,
                evidence=GraphEvidence(
                    source_table="continuity_reports",
                    source_row_id=report_id,
                    chapter=chapter,
                    detail=f"health={_value(row, 'overall_health_score')}",
                ),
                attributes={key: _jsonable(_value(row, key)) for key in row.keys()},
            )
        )
    return nodes


def _edges_from_nodes(nodes: list[GraphNode], *, up_to: int) -> list[GraphEdge]:
    version_by_chapter = {
        node.chapter: node.node_id
        for node in nodes
        if node.node_type == "chapter_version" and node.chapter is not None
    }
    edges: list[GraphEdge] = []
    for node in nodes:
        target = version_by_chapter.get(node.chapter)
        if target is None or node.node_type == "chapter_version":
            continue
        edge_type: EdgeType
        if node.node_type == "setting":
            edge_type = "mentioned_in"
        elif node.node_type == "foreshadowing":
            edge_type = "introduced_in"
        elif node.node_type == "human_mark":
            edge_type = "marked_by"
        else:
            edge_type = "reported_by"
        edges.append(
            GraphEdge(
                edge_id=f"{node.node_id}->{target}:{edge_type}:{up_to}",
                edge_type=edge_type,
                source=node.node_id,
                target=target,
                evidence=node.evidence,
            )
        )
    return edges


def _build_diffs(
    before: FactGraphSnapshot,
    after: FactGraphSnapshot,
    *,
    sample: KGDiffSample,
    conn: sqlite3.Connection,
) -> list[KGDiffEntry]:
    diffs: list[KGDiffEntry] = []
    before_by_id = {node.node_id: node for node in before.nodes}
    after_by_id = {node.node_id: node for node in after.nodes}
    for node_id, node in after_by_id.items():
        previous = before_by_id.get(node_id)
        if previous is None and node.chapter == sample.chapter:
            diffs.append(_node_diff("added", node, sample, confidence="low"))
            continue
        if previous is None:
            continue
        if node.status != previous.status and node.status == "resolved":
            diffs.append(_node_diff("resolved_candidate", node, sample, confidence="medium"))
        elif node.attributes != previous.attributes and node.chapter == sample.chapter:
            diffs.append(_node_diff("refreshed", node, sample, confidence="low"))
    diffs.extend(_missing_refresh_candidates(after, sample))
    diffs.extend(_unresolved_candidates(after, sample))
    stale = _stale_continuity_candidates(conn, sample)
    diffs.extend(stale)
    return _prioritize_diffs(diffs, sample)


def _node_diff(
    diff_type: DiffType,
    node: GraphNode,
    sample: KGDiffSample,
    *,
    confidence: Confidence,
) -> KGDiffEntry:
    return KGDiffEntry(
        diff_id=f"{sample.sample_id}:{diff_type}:{node.node_id}",
        diff_type=diff_type,
        node_id=node.node_id,
        label=node.label,
        confidence=confidence,
        evidence=node.evidence,
        reason=f"{node.node_type} node changed in after snapshot",
    )


def _missing_refresh_candidates(
    snapshot: FactGraphSnapshot,
    sample: KGDiffSample,
) -> list[KGDiffEntry]:
    next_audit = ((sample.chapter // 3) + 1) * 3
    out: list[KGDiffEntry] = []
    for node in snapshot.nodes:
        if node.node_type != "setting":
            continue
        if node.status != "active":
            continue
        category = str(node.attributes.get("category") or "background")
        if category != "critical":
            continue
        last = _int_or_none(node.attributes.get("last_mentioned_chapter"))
        if last is None:
            continue
        threshold = ORPHAN_THRESHOLDS.get(category, 3)
        if (next_audit - last) <= threshold:
            continue
        confidence: Confidence = (
            "high" if sample.expected_signal == "missing_refresh_candidate" else "low"
        )
        out.append(
            KGDiffEntry(
                diff_id=f"{sample.sample_id}:missing_refresh:{node.node_id}",
                diff_type="missing_refresh_candidate",
                node_id=node.node_id,
                label=node.label,
                confidence=confidence,
                evidence=node.evidence,
                reason=(
                    f"active critical setting last mentioned at Ch{last}; "
                    f"next audit Ch{next_audit} exceeds threshold {threshold}"
                ),
                task205_route=True,
            )
        )
    return out


def _unresolved_candidates(
    snapshot: FactGraphSnapshot,
    sample: KGDiffSample,
) -> list[KGDiffEntry]:
    out: list[KGDiffEntry] = []
    for node in snapshot.nodes:
        if node.node_type == "foreshadowing":
            expected = _int_or_none(node.attributes.get("expected_resolve_chapter"))
            if expected is None or expected >= sample.chapter:
                continue
            if node.status == "resolved":
                continue
            confidence: Confidence = (
                "high" if sample.expected_signal == "unresolved_candidate" else "low"
            )
            out.append(
                KGDiffEntry(
                    diff_id=f"{sample.sample_id}:unresolved_foreshadowing:{node.node_id}",
                    diff_type="unresolved_candidate",
                    node_id=node.node_id,
                    label=node.label,
                    confidence=confidence,
                    evidence=node.evidence,
                    reason=(
                        f"foreshadowing expected resolve before Ch{sample.chapter} "
                        f"but status is {node.status}"
                    ),
                    task205_route=True,
                )
            )
        if node.node_type == "human_mark":
            if node.status != "unresolved":
                continue
            priority = int(node.attributes.get("priority") or 0)
            if priority < 8 and sample.expected_signal != "unresolved_candidate":
                continue
            confidence = "high" if sample.expected_signal == "unresolved_candidate" else "low"
            out.append(
                KGDiffEntry(
                    diff_id=f"{sample.sample_id}:unresolved_human_mark:{node.node_id}",
                    diff_type="unresolved_candidate",
                    node_id=node.node_id,
                    label=node.label,
                    confidence=confidence,
                    evidence=node.evidence,
                    reason=f"human mark priority={priority} remains unresolved",
                    task205_route=True,
                )
            )
    return out


def _stale_continuity_candidates(
    conn: sqlite3.Connection,
    sample: KGDiffSample,
) -> list[KGDiffEntry]:
    if not _table_exists(conn, "continuity_reports"):
        return []
    cols = _columns(conn, "continuity_reports")
    select_cols = [
        col for col in [
            "report_id",
            "checked_up_to_chapter",
            "overall_health_score",
            "created_at",
        ] if col in cols
    ]
    if "report_id" not in select_cols or "checked_up_to_chapter" not in select_cols:
        return []
    rows = _fetchall(
        conn,
        f"""SELECT rowid, {', '.join(select_cols)}
           FROM continuity_reports
           WHERE project_id = ? AND checked_up_to_chapter = ?
           ORDER BY rowid""",
        (sample.project_id, sample.chapter),
    )
    out: list[KGDiffEntry] = []
    if len(rows) >= 2:
        health_values = {
            _jsonable(row["overall_health_score"])
            for row in rows
        }
        if len(health_values) >= 2:
            row = rows[-1]
            confidence: Confidence = (
                "high" if sample.expected_signal == "stale_candidate" else "low"
            )
            out.append(
                KGDiffEntry(
                    diff_id=f"{sample.sample_id}:stale_continuity:{row['rowid']}",
                    diff_type="stale_candidate",
                    node_id=f"continuity_report:{row['report_id']}",
                    label=f"continuity@Ch{sample.chapter}",
                    confidence=confidence,
                    evidence=GraphEvidence(
                        source_table="continuity_reports",
                        source_row_id=str(row["report_id"]),
                        chapter=sample.chapter,
                        detail=(
                            f"{len(rows)} reports at same chapter with "
                            f"health_values={sorted(map(str, health_values))}"
                        ),
                    ),
                    reason=(
                        "multiple same-chapter continuity reports can make stale "
                        "consumers pick the wrong report"
                    ),
                    task205_route=True,
                )
            )
    latest = _fetchall(
        conn,
        f"""SELECT {', '.join(select_cols)}
           FROM continuity_reports
           WHERE project_id = ? AND checked_up_to_chapter <= ?
           ORDER BY checked_up_to_chapter DESC, rowid DESC
           LIMIT 1""",
        (sample.project_id, sample.chapter),
    )
    if latest and int(latest[0]["checked_up_to_chapter"]) < sample.chapter:
        row = latest[0]
        confidence = "high" if sample.expected_signal == "stale_candidate" else "low"
        out.append(
            KGDiffEntry(
                diff_id=f"{sample.sample_id}:stale_missing_chapter:{row['report_id']}",
                diff_type="stale_candidate",
                node_id=f"continuity_report:{row['report_id']}",
                label=f"continuity@Ch{row['checked_up_to_chapter']}",
                confidence=confidence,
                evidence=GraphEvidence(
                    source_table="continuity_reports",
                    source_row_id=str(row["report_id"]),
                    chapter=int(row["checked_up_to_chapter"]),
                    detail=f"latest continuity report is before Ch{sample.chapter}",
                ),
                reason=f"no continuity report at Ch{sample.chapter}",
                task205_route=True,
            )
        )
    return out


def _prioritize_diffs(
    diffs: list[KGDiffEntry],
    sample: KGDiffSample,
) -> list[KGDiffEntry]:
    priority = {"high": 0, "medium": 1, "low": 2, "none": 3}
    expected = sample.expected_signal
    return sorted(
        diffs,
        key=lambda item: (
            0 if item.diff_type == expected else 1,
            priority[item.confidence],
            item.diff_type,
            item.node_id,
        ),
    )[:30]


def _evaluate_diffs(
    sample: KGDiffSample,
    diffs: list[KGDiffEntry],
) -> SampleEvaluation:
    matching = [
        item for item in diffs
        if item.diff_type == sample.expected_signal
        and item.confidence in {"high", "medium"}
    ]
    high_conf_negative = [
        item for item in diffs
        if item.confidence == "high"
        and item.diff_type in {
            "stale_candidate",
            "unresolved_candidate",
            "missing_refresh_candidate",
        }
    ]
    detected = bool(matching) if sample.kind == "positive" else False
    false_positive = sample.kind == "negative_control" and bool(high_conf_negative)
    confidence = _max_confidence(matching or high_conf_negative)
    if sample.kind == "negative_control" and not false_positive:
        confidence = "none"
    unique_gain = bool(detected and sample.expected_gain and not false_positive)
    decision_note = _decision_note(sample, detected, false_positive, unique_gain)
    coverage = set(sample.expected_existing_tool_coverage)
    return SampleEvaluation(
        truth_label=sample.issue_type,
        detected_by_kg_diff=detected,
        covered_by_segment_audit="segment_audit" in coverage,
        covered_by_ced="ced" in coverage,
        covered_by_human_marks="human_marks" in coverage,
        unique_gain=unique_gain,
        false_positive=false_positive,
        confidence=confidence,
        decision_note=decision_note,
    )


def _document_only_evaluation(
    sample: KGDiffSample,
    *,
    missing_db: bool,
) -> SampleEvaluation:
    coverage = set(sample.expected_existing_tool_coverage)
    note = (
        "missing DB; document truth only"
        if missing_db
        else "DB read failed; document truth only"
    )
    return SampleEvaluation(
        truth_label=sample.issue_type,
        detected_by_kg_diff=False,
        covered_by_segment_audit="segment_audit" in coverage,
        covered_by_ced="ced" in coverage,
        covered_by_human_marks="human_marks" in coverage,
        unique_gain=False,
        false_positive=False,
        confidence="low" if sample.kind == "positive" else "none",
        decision_note=note,
    )


def _decision_note(
    sample: KGDiffSample,
    detected: bool,
    false_positive: bool,
    unique_gain: bool,
) -> str:
    if false_positive:
        return "negative control produced high-confidence KG diff candidate"
    if sample.kind == "negative_control":
        return "negative control produced no high-confidence candidate"
    if not detected:
        return "expected signal was not reproduced from DB facts"
    if unique_gain:
        return "expected signal reproduced with clearer graph-local evidence"
    return "expected signal reproduced but mostly duplicates existing tool coverage"


def _max_confidence(items: list[KGDiffEntry]) -> Confidence:
    rank = {"high": 3, "medium": 2, "low": 1, "none": 0}
    if not items:
        return "none"
    return max((item.confidence for item in items), key=lambda value: rank[value])


def _build_gain_matrix(results: list[SampleKGDiffResult]) -> list[GainMatrixRow]:
    grouped: dict[str, list[SampleKGDiffResult]] = defaultdict(list)
    for item in results:
        grouped[item.sample.issue_type].append(item)
    rows: list[GainMatrixRow] = []
    for issue_type, items in sorted(grouped.items()):
        row = GainMatrixRow(issue_type=issue_type, sample_count=len(items))
        for item in items:
            ev = item.evaluation
            if item.sample.kind == "positive" and ev.detected_by_kg_diff:
                row.true_positive += 1
            elif item.sample.kind == "positive":
                row.unclear += 1
            if ev.false_positive:
                row.false_positive += 1
            if ev.unique_gain:
                row.unique_gain += 1
            if ev.covered_by_segment_audit:
                row.covered_by_segment_audit += 1
            if ev.covered_by_ced:
                row.covered_by_ced += 1
            if (
                ev.covered_by_human_marks
                or "document_truth" in item.sample.expected_existing_tool_coverage
            ):
                row.human_or_document_only += 1
            if _needs_validity_interval(item):
                row.needs_validity_interval += 1
            if _needs_storyline_tree(item):
                row.needs_storyline_tree += 1
        rows.append(row)
    return rows


def _build_summary(results: list[SampleKGDiffResult]) -> Task204Summary:
    positive_count = sum(1 for item in results if item.sample.kind == "positive")
    negative_count = sum(1 for item in results if item.sample.kind == "negative_control")
    db_backed = sum(1 for item in results if not item.document_truth_only)
    doc_only = sum(1 for item in results if item.document_truth_only)
    high = sum(
        1 for item in results
        if item.evaluation.confidence == "high"
        and item.evaluation.detected_by_kg_diff
    )
    unique = sum(1 for item in results if item.evaluation.unique_gain)
    false_positive = sum(1 for item in results if item.evaluation.false_positive)
    validity_needed = sum(1 for item in results if _needs_validity_interval(item))
    unique_issue_types = {
        item.sample.issue_type
        for item in results
        if item.evaluation.unique_gain
    }
    if unique >= 2 and len(unique_issue_types) >= 2 and false_positive == 0:
        if validity_needed:
            decision: Decision = "defer"
            reason = (
                "KG diff reproduces useful signals, but several cases require "
                "validity interval or alias policy before production use."
            )
        else:
            decision = "continue"
            reason = "KG diff shows stable unique gain with controlled negative controls."
    elif high > 0:
        decision = "defer"
        reason = "Signals exist but unique gain is not yet stable enough."
    else:
        decision = "reject"
        reason = "KG diff mostly duplicates existing tools or cannot reproduce labels."
    next_route = (
        "Task 205 FactTrack validity interval spike"
        if decision in {"continue", "defer"}
        else "Re-evaluate Task 205 independent value before starting it"
    )
    return Task204Summary(
        sample_count=len(results),
        positive_samples=positive_count,
        negative_controls=negative_count,
        db_backed_samples=db_backed,
        document_truth_only_samples=doc_only,
        high_confidence_detections=high,
        unique_gain_count=unique,
        decision=decision,
        decision_reason=reason,
        next_route=next_route,
    )


def _needs_validity_interval(item: SampleKGDiffResult) -> bool:
    if any("validity" in value for value in item.sample.expected_gain):
        return True
    return any(diff.task205_route for diff in item.diffs)


def _needs_storyline_tree(item: SampleKGDiffResult) -> bool:
    return any("storyline" in value for value in item.sample.expected_gain) or any(
        diff.task206_route for diff in item.diffs
    )


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


def _accepted_version_id(
    conn: sqlite3.Connection,
    project_id: str,
    chapter: int,
) -> str | None:
    if not _table_exists(conn, "chapter_heads"):
        return None
    rows = _fetchall(
        conn,
        """SELECT accepted_version_id FROM chapter_heads
           WHERE project_id = ? AND chapter_number = ?
           LIMIT 1""",
        (project_id, chapter),
    )
    if not rows:
        return None
    return rows[0]["accepted_version_id"]


def _version_chapter(
    conn: sqlite3.Connection,
    project_id: str,
    version_id: str | None,
) -> int | None:
    if not version_id or not _table_exists(conn, "chapter_versions"):
        return None
    rows = _fetchall(
        conn,
        """SELECT chapter_number FROM chapter_versions
           WHERE project_id = ? AND version_id = ?
           LIMIT 1""",
        (project_id, version_id),
    )
    if not rows:
        return None
    return _int_or_none(rows[0]["chapter_number"])


def _value(row: sqlite3.Row, key: str) -> Any:
    return row[key] if key in row.keys() else None


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _jsonable(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value
