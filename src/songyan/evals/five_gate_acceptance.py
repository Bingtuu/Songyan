"""Five-gate acceptance tooling for Ch100 genre climb replay.

This module formalizes the V8 ``.tmp/vdim_compare.py`` logic without changing
the frozen gate semantics.  It is intentionally read-only: historical climb DBs
must not be migrated or modified while being evaluated.
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any, TypeAlias

from songyan.evals.consistency_ced import ReviewIssueReport, count_consistency_issues

CED_TOLERANCE = 1.15
DEFAULT_ALLOWED_GAP = 1

JsonScalar: TypeAlias = str | int | float | bool | None


class FiveGateToolError(RuntimeError):
    """Raised when a five-gate replay cannot be performed safely."""


@dataclass(frozen=True)
class CedMetric:
    """Consistency Error Density numerator and denominator."""

    ced_per_1k_words: float
    issue_count: int
    word_count: int

    def to_dict(self) -> dict[str, JsonScalar]:
        """Return a JSON-serializable representation."""
        return {
            "ced_per_1k_words": self.ced_per_1k_words,
            "issue_count": self.issue_count,
            "word_count": self.word_count,
        }


@dataclass(frozen=True)
class TargetMetrics:
    """Metrics collected from one target project DB for a bounded chapter range."""

    genre: str
    project_id: str
    up_to: int
    accepted: int
    budget_used_peak: float
    overdue_foreshadowing: int
    health_latest: float | None
    ced: CedMetric
    halt: str | None = None
    # Task 193.w F1: health 取值报告的章号（192.aw 型 stale health 鉴别证据）
    health_report_chapter: int | None = None

    @property
    def gap(self) -> int:
        """Return accepted gap against the requested ``up_to`` boundary."""
        return self.up_to - self.accepted

    def to_dict(self) -> dict[str, JsonScalar | dict[str, JsonScalar]]:
        """Return a JSON-serializable representation."""
        return {
            "genre": self.genre,
            "project_id": self.project_id,
            "up_to": self.up_to,
            "accepted": self.accepted,
            "gap": self.gap,
            "budget_used_peak": self.budget_used_peak,
            "overdue_foreshadowing": self.overdue_foreshadowing,
            "health_latest": self.health_latest,
            "health_report_chapter": self.health_report_chapter,
            "halt": self.halt,
            "ced": self.ced.to_dict(),
        }


@dataclass(frozen=True)
class BaselinePoint:
    """Sci-fi baseline point at a checkpoint or interpolated chapter boundary."""

    up_to: int
    accepted: int | None
    budget_used_peak: float
    overdue_foreshadowing: float
    health_latest: float | None
    ced_per_1k_words: float
    ced_issue_count: int | None = None
    ced_word_count: int | None = None
    context_emergency_count: int | None = None
    budget_used_before_emergency_peak: float | None = None
    legacy_ced_per_1k_words: float | None = None
    legacy_evidence_issue_count: int | None = None

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> BaselinePoint:
        """Create a baseline point from JSON data."""
        return cls(
            up_to=int(raw["up_to"]),
            accepted=_optional_int(raw.get("accepted")),
            budget_used_peak=float(raw["budget_used_peak"]),
            overdue_foreshadowing=float(raw["overdue_foreshadowing"]),
            health_latest=_optional_float(raw.get("health_latest")),
            ced_per_1k_words=float(raw["ced_per_1k_words"]),
            ced_issue_count=_optional_int(raw.get("ced_issue_count")),
            ced_word_count=_optional_int(raw.get("ced_word_count") or raw.get("ced_words")),
            context_emergency_count=_optional_int(raw.get("context_emergency_count")),
            budget_used_before_emergency_peak=_optional_float(
                raw.get("budget_used_before_emergency_peak")
            ),
            legacy_ced_per_1k_words=_optional_float(raw.get("legacy_ced_per_1k_words")),
            legacy_evidence_issue_count=_optional_int(raw.get("legacy_evidence_issue_count")),
        )

    def to_dict(self) -> dict[str, JsonScalar]:
        """Return a JSON-serializable representation."""
        return {
            "up_to": self.up_to,
            "accepted": self.accepted,
            "budget_used_peak": self.budget_used_peak,
            "overdue_foreshadowing": self.overdue_foreshadowing,
            "health_latest": self.health_latest,
            "ced_per_1k_words": self.ced_per_1k_words,
            "ced_issue_count": self.ced_issue_count,
            "ced_word_count": self.ced_word_count,
            "context_emergency_count": self.context_emergency_count,
            "budget_used_before_emergency_peak": self.budget_used_before_emergency_peak,
            "legacy_ced_per_1k_words": self.legacy_ced_per_1k_words,
            "legacy_evidence_issue_count": self.legacy_evidence_issue_count,
        }


@dataclass(frozen=True)
class GateResult:
    """One five-gate pass/fail result."""

    name: str
    passed: bool
    target: JsonScalar
    baseline: JsonScalar = None
    threshold: JsonScalar = None
    detail: str = ""

    def to_dict(self) -> dict[str, JsonScalar]:
        """Return a JSON-serializable representation."""
        return {
            "name": self.name,
            "passed": self.passed,
            "target": self.target,
            "baseline": self.baseline,
            "threshold": self.threshold,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class FiveGateReport:
    """Complete five-gate acceptance report."""

    metrics: TargetMetrics
    baseline: BaselinePoint
    gates: tuple[GateResult, ...]
    final: bool

    @property
    def verdict(self) -> str:
        """Return the overall PASS/FAIL verdict."""
        return "PASS" if all(gate.passed for gate in self.gates) else "FAIL"

    def to_dict(self) -> dict[str, JsonScalar | dict[str, Any] | list[dict[str, JsonScalar]]]:
        """Return a JSON-serializable representation."""
        return {
            "verdict": self.verdict,
            "final": self.final,
            "metrics": self.metrics.to_dict(),
            "baseline": self.baseline.to_dict(),
            "gates": [gate.to_dict() for gate in self.gates],
        }


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def open_readonly_db(db_path: Path) -> sqlite3.Connection:
    """Open an existing SQLite DB in URI read-only mode.

    ``sqlite3.connect("missing.db")`` silently creates an empty file, which is
    exactly what this tool must avoid when replaying historical evidence.
    """
    resolved = db_path.resolve()
    if not resolved.is_file():
        msg = f"SQLite DB does not exist: {db_path}"
        raise FiveGateToolError(msg)
    uri = f"{resolved.as_uri()}?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.Error as exc:
        msg = f"failed to open SQLite DB read-only: {db_path}"
        raise FiveGateToolError(msg) from exc
    conn.row_factory = sqlite3.Row
    return conn


def word_count(content: str) -> int:
    """Count Chinese characters and alphanumeric word-like tokens."""
    return len(re.findall(r"[\u4e00-\u9fff]", content)) + len(
        re.findall(r"[a-zA-Z0-9]+", content)
    )


def load_baseline(baseline_path: Path | None = None) -> tuple[BaselinePoint, ...]:
    """Load formal sci-fi baseline points.

    When ``baseline_path`` is omitted, the package resource is used.  This keeps
    Task 182 compatible with wheel installs and non-repository working dirs.
    """
    if baseline_path is None:
        raw_text = (
            files("songyan.evals").joinpath("baselines/scifi_ch100_baseline.json").read_text(
                encoding="utf-8"
            )
        )
    else:
        raw_text = baseline_path.read_text(encoding="utf-8")
    raw = json.loads(raw_text)
    rows = raw["points"] if isinstance(raw, dict) else raw
    if not isinstance(rows, list):
        msg = "baseline JSON must be a list or an object with a points list"
        raise FiveGateToolError(msg)
    points = tuple(sorted((BaselinePoint.from_mapping(row) for row in rows), key=lambda p: p.up_to))
    if not points:
        msg = "baseline JSON contains no points"
        raise FiveGateToolError(msg)
    return points


def baseline_at(points: tuple[BaselinePoint, ...], up_to: int) -> BaselinePoint:
    """Interpolate the sci-fi baseline at an arbitrary chapter count."""
    ordered = tuple(sorted(points, key=lambda point: point.up_to))
    if up_to <= ordered[0].up_to:
        return ordered[0]
    if up_to >= ordered[-1].up_to:
        return ordered[-1]
    for lo, hi in zip(ordered, ordered[1:]):
        if lo.up_to <= up_to <= hi.up_to:
            frac = (up_to - lo.up_to) / (hi.up_to - lo.up_to)
            return BaselinePoint(
                up_to=up_to,
                accepted=None,
                overdue_foreshadowing=lo.overdue_foreshadowing
                + frac * (hi.overdue_foreshadowing - lo.overdue_foreshadowing),
                ced_per_1k_words=lo.ced_per_1k_words
                + frac * (hi.ced_per_1k_words - lo.ced_per_1k_words),
                budget_used_peak=max(lo.budget_used_peak, hi.budget_used_peak),
                health_latest=lo.health_latest,
            )
    return ordered[-1]


def has_reports(cur: sqlite3.Cursor, version_id: str | None) -> bool:
    """Return whether a chapter version has any review reports."""
    if not version_id:
        return False
    cur.execute(
        "SELECT 1 FROM review_reports WHERE chapter_version_id = ? LIMIT 1",
        (version_id,),
    )
    return cur.fetchone() is not None


def review_source_version(cur: sqlite3.Cursor, accepted_version_id: str) -> str:
    """Find the reviewed source version for an accepted head."""
    if has_reports(cur, accepted_version_id):
        return accepted_version_id
    cur.execute(
        "SELECT parent_version_id FROM chapter_versions WHERE version_id = ?",
        (accepted_version_id,),
    )
    row = cur.fetchone()
    parent_id = str(row["parent_version_id"]) if row and row["parent_version_id"] else None
    if parent_id is not None and has_reports(cur, parent_id):
        return parent_id
    return accepted_version_id


def consistency_ced_for_accepted_heads(
    conn: sqlite3.Connection,
    project_id: str,
    up_to: int,
) -> CedMetric:
    """Calculate chapter-bounded consistency-only CED for accepted heads."""
    cur = conn.cursor()
    cur.execute(
        """SELECT ch.chapter_number, ch.accepted_version_id, cv.content
           FROM chapter_heads ch
           JOIN chapter_versions cv ON cv.version_id = ch.accepted_version_id
           WHERE ch.project_id = ? AND ch.accepted_version_id IS NOT NULL
             AND ch.chapter_number <= ?
           ORDER BY ch.chapter_number""",
        (project_id, up_to),
    )
    heads = cur.fetchall()
    total_words = sum(word_count(str(row["content"] or "")) for row in heads)
    issue_count = 0
    for row in heads:
        source_id = review_source_version(cur, str(row["accepted_version_id"]))
        cur.execute(
            """SELECT audit_type, issues FROM review_reports
               WHERE chapter_version_id = ?""",
            (source_id,),
        )
        reports = [
            ReviewIssueReport(audit_type=str(report["audit_type"]), issues_json=report["issues"])
            for report in cur.fetchall()
        ]
        issue_count += count_consistency_issues(reports)
    ced = round(issue_count / total_words * 1000, 4) if total_words else 0.0
    return CedMetric(ced_per_1k_words=ced, issue_count=issue_count, word_count=total_words)


def collect_metrics(
    db_path: Path,
    *,
    project_id: str,
    up_to: int,
    genre: str,
) -> TargetMetrics:
    """Collect target project metrics from a historical DB."""
    with open_readonly_db(db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT COUNT(*)
               FROM chapter_heads
               WHERE project_id = ? AND chapter_number <= ?
                 AND status = 'accepted' AND accepted_version_id IS NOT NULL""",
            (project_id, up_to),
        )
        accepted = int(cur.fetchone()[0])

        cur.execute(
            """SELECT budget_used FROM context_snapshots
               WHERE project_id = ? AND chapter_number BETWEEN 1 AND ?""",
            (project_id, up_to),
        )
        budget_peak = max((float(row["budget_used"] or 0.0) for row in cur.fetchall()), default=0.0)

        cur.execute(
            """SELECT COUNT(*) FROM foreshadowings
               WHERE project_id = ? AND expected_resolve_chapter IS NOT NULL
                 AND expected_resolve_chapter < ? AND status != 'resolved'""",
            (project_id, up_to),
        )
        overdue = int(cur.fetchone()[0])

        health_order = "checked_up_to_chapter DESC"
        if _column_exists(cur, "continuity_reports", "created_at"):
            health_order += ", datetime(created_at) DESC"
        health_order += ", rowid DESC"
        cur.execute(
            f"""SELECT overall_health_score, checked_up_to_chapter FROM continuity_reports
                WHERE project_id = ? AND checked_up_to_chapter <= ?
                ORDER BY {health_order} LIMIT 1""",
            (project_id, up_to),
        )
        health_row = cur.fetchone()
        health = (
            float(health_row["overall_health_score"])
            if health_row and health_row["overall_health_score"] is not None
            else None
        )
        health_report_chapter = (
            int(health_row["checked_up_to_chapter"]) if health_row else None
        )

        ced = consistency_ced_for_accepted_heads(conn, project_id, up_to)
        halt = detect_halt(conn, project_id, up_to)

    return TargetMetrics(
        genre=genre,
        project_id=project_id,
        up_to=up_to,
        accepted=accepted,
        budget_used_peak=round(budget_peak, 4),
        overdue_foreshadowing=overdue,
        health_latest=health,
        ced=ced,
        halt=halt,
        health_report_chapter=health_report_chapter,
    )


def detect_halt(conn: sqlite3.Connection, project_id: str, up_to: int) -> str | None:
    """Detect halt evidence relevant to the evaluated chapter boundary."""
    cur = conn.cursor()
    if _table_exists(cur, "adaptive_halt_decisions"):
        cur.execute(
            """SELECT evaluated_at_chapter, reasons_json FROM adaptive_halt_decisions
               WHERE project_id = ? AND status = 'halt' AND evaluated_at_chapter <= ?
               ORDER BY evaluated_at_chapter DESC LIMIT 1""",
            (project_id, up_to),
        )
        row = cur.fetchone()
        if row:
            reasons = str(row["reasons_json"] or "[]")
            return f"adaptive_halt@Ch{row['evaluated_at_chapter']}:{reasons}"

    if _table_exists(cur, "project_runs"):
        # Task 193.r: pause_reason 区分质量熔断与非质量暂停；旧库无此列时回退保守旧行为
        has_pause_reason = _column_exists(cur, "project_runs", "pause_reason")
        select_cols = (
            "status, current_chapter, pause_reason"
            if has_pause_reason
            else "status, current_chapter"
        )
        cur.execute(
            f"""SELECT {select_cols} FROM project_runs
               WHERE project_id = ? AND status IN ('paused', 'failed')
               ORDER BY updated_at DESC LIMIT 1""",
            (project_id,),
        )
        row = cur.fetchone()
        if row:
            current_chapter = int(row["current_chapter"] or 0)
            if current_chapter <= up_to:
                status = str(row["status"])
                if status == "failed":
                    return f"project_run_failed@Ch{current_chapter}"
                pause_reason = (
                    str(row["pause_reason"])
                    if has_pause_reason and row["pause_reason"]
                    else None
                )
                # 人工/成本/外部暂停不是质量熔断，不计 halt；
                # 无 reason 的历史行保持保守旧行为（计 halt）。
                if pause_reason is not None and not pause_reason.startswith("auto_halt"):
                    return None
                if pause_reason:
                    return f"project_run_paused@Ch{current_chapter}:{pause_reason}"
                return f"project_run_{status}@Ch{current_chapter}"
    return None


def _table_exists(cur: sqlite3.Cursor, table_name: str) -> bool:
    cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ? LIMIT 1",
        (table_name,),
    )
    return cur.fetchone() is not None


def _column_exists(cur: sqlite3.Cursor, table_name: str, column_name: str) -> bool:
    cur.execute(f"PRAGMA table_info({table_name})")
    return any(str(row["name"]) == column_name for row in cur.fetchall())


def evaluate_metrics(
    metrics: TargetMetrics,
    baseline: BaselinePoint,
    *,
    allow_gap: int = DEFAULT_ALLOWED_GAP,
) -> FiveGateReport:
    """Evaluate target metrics against the frozen five gates."""
    ced_threshold = baseline.ced_per_1k_words * CED_TOLERANCE
    gap = metrics.gap
    gates = (
        GateResult(
            name="budget",
            passed=metrics.budget_used_peak < 1.0 and not metrics.halt,
            target=metrics.budget_used_peak,
            baseline=baseline.budget_used_peak,
            threshold="<1.0 and no halt",
            detail="budget_used_peak must remain under 1.0",
        ),
        GateResult(
            name="CED",
            passed=metrics.ced.ced_per_1k_words <= ced_threshold,
            target=metrics.ced.ced_per_1k_words,
            baseline=baseline.ced_per_1k_words,
            threshold=round(ced_threshold, 4),
            detail=f"target <= sci-fi * {CED_TOLERANCE}",
        ),
        GateResult(
            name="overdue",
            passed=metrics.overdue_foreshadowing <= baseline.overdue_foreshadowing,
            target=metrics.overdue_foreshadowing,
            baseline=baseline.overdue_foreshadowing,
            threshold=baseline.overdue_foreshadowing,
            detail="target overdue must not exceed sci-fi same-chapter scale",
        ),
        GateResult(
            name="health",
            passed=metrics.health_latest is not None and metrics.health_latest >= 8.0,
            target=metrics.health_latest,
            baseline=baseline.health_latest,
            threshold=8.0,
            detail=(
                f"latest health must be >= 8.0 (report @Ch{metrics.health_report_chapter})"
                if metrics.health_report_chapter is not None
                else "latest health must be >= 8.0 (no continuity report)"
            ),
        ),
        GateResult(
            name="completeness",
            passed=gap <= allow_gap,
            target=metrics.accepted,
            baseline=metrics.up_to,
            threshold=f"gap <= {allow_gap}",
            detail=f"accepted {metrics.accepted}/{metrics.up_to}, gap {gap}",
        ),
    )
    return FiveGateReport(
        metrics=metrics,
        baseline=baseline,
        gates=gates,
        final=metrics.up_to >= 100,
    )


def evaluate_project(
    db_path: Path,
    *,
    project_id: str,
    genre: str,
    up_to: int,
    baseline_path: Path | None = None,
    allow_gap: int = DEFAULT_ALLOWED_GAP,
) -> FiveGateReport:
    """Collect and evaluate one target project against the formal baseline."""
    baseline_points = load_baseline(baseline_path)
    if baseline_path is not None and up_to < baseline_points[0].up_to:
        msg = (
            f"baseline {baseline_path} starts at Ch{baseline_points[0].up_to}; "
            f"cannot evaluate Ch{up_to}. Use a baseline that covers this chapter range."
        )
        raise FiveGateToolError(msg)
    baseline = baseline_at(baseline_points, up_to)
    metrics = collect_metrics(db_path, project_id=project_id, up_to=up_to, genre=genre)
    return evaluate_metrics(metrics, baseline, allow_gap=allow_gap)


def render_text_report(report: FiveGateReport) -> str:
    """Render a human-readable five-gate report."""
    metrics = report.metrics
    baseline = report.baseline
    gate_map = {gate.name: gate for gate in report.gates}
    lines = [
        (
            f"=== five-gate check @ Ch{metrics.up_to} "
            f"({metrics.genre} accepted={metrics.accepted}) ==="
        ),
        (
            f"  budget_peak : {metrics.genre} {metrics.budget_used_peak:.3f} "
            f"vs scifi {baseline.budget_used_peak:.3f} -> {_label(gate_map['budget'])}"
        ),
        (
            f"  CED/1k      : {metrics.genre} {metrics.ced.ced_per_1k_words:.4f} "
            f"vs scifi {baseline.ced_per_1k_words:.4f} "
            f"(tol x{CED_TOLERANCE}) -> {_label(gate_map['CED'])}"
        ),
        (
            "               consistency-only, merged/source; "
            f"issues target={metrics.ced.issue_count} scifi={baseline.ced_issue_count}"
        ),
        (
            f"  overdue     : {metrics.genre} {metrics.overdue_foreshadowing} "
            f"vs scifi {baseline.overdue_foreshadowing:.0f} -> {_label(gate_map['overdue'])}"
        ),
        (
            f"  health      : {metrics.genre} {metrics.health_latest} "
            f"(report @Ch{metrics.health_report_chapter}) "
            f"-> {_label(gate_map['health'])} (need >=8.0)"
        ),
        (
            f"  completeness: accepted {metrics.accepted}/{metrics.up_to} "
            f"(gap {metrics.gap}) -> {_label(gate_map['completeness'])}"
        ),
        f"  --- gate verdict: {report.verdict} (final={report.final}) ---",
    ]
    if not report.final:
        lines.append("  NOTE: partial climb; verdict is an early-warning read.")
    return "\n".join(lines)


def _label(gate: GateResult) -> str:
    return "PASS" if gate.passed else "FAIL"
