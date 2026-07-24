"""Segment-boundary audit helpers for Ch100 climb forensics."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeAlias

from songyan.evals.consistency_ced import parse_issues
from songyan.evals.five_gate_acceptance import FiveGateToolError, open_readonly_db

JsonScalar: TypeAlias = str | int | float | bool | None

ORPHAN_THRESHOLDS: dict[str, int] = {
    "critical": 3,
    "recurring": 4,
    "background": 5,
    "technical": 7,
    "historical": 10,
}


@dataclass(frozen=True)
class Hotspot:
    """Legacy evidence hotspot count for one chapter."""

    chapter_number: int
    issue_count: int

    def to_dict(self) -> dict[str, int]:
        """Return a JSON-serializable representation."""
        return {"chapter_number": self.chapter_number, "issue_count": self.issue_count}


@dataclass(frozen=True)
class HealthPoint:
    """One continuity health trajectory point."""

    checked_up_to_chapter: int
    health: float | None

    def to_dict(self) -> dict[str, JsonScalar]:
        """Return a JSON-serializable representation."""
        return {
            "checked_up_to_chapter": self.checked_up_to_chapter,
            "health": self.health,
        }


@dataclass(frozen=True)
class SegmentAuditReport:
    """Segment-boundary forensic report."""

    project_id: str
    up_to: int
    next_audit_chapter: int
    critical_orphans: int
    total_orphans: int
    hotspots: tuple[Hotspot, ...]
    health_trajectory: tuple[HealthPoint, ...]

    @property
    def halt_would_fire(self) -> bool:
        """Return whether the critical-orphan halt would fire."""
        return self.critical_orphans > 0

    def to_dict(
        self,
    ) -> dict[str, JsonScalar | list[dict[str, JsonScalar]] | list[dict[str, int]]]:
        """Return a JSON-serializable representation."""
        return {
            "project_id": self.project_id,
            "up_to": self.up_to,
            "next_audit_chapter": self.next_audit_chapter,
            "critical_orphans": self.critical_orphans,
            "total_orphans": self.total_orphans,
            "halt_would_fire": self.halt_would_fire,
            "hotspots": [hotspot.to_dict() for hotspot in self.hotspots],
            "health_trajectory": [point.to_dict() for point in self.health_trajectory],
        }


def collect_segment_audit(
    db_path: Path,
    *,
    project_id: str,
    up_to: int | None = None,
    top: int = 8,
) -> SegmentAuditReport:
    """Collect segment-boundary forensic signals from a historical DB."""
    if top < 1:
        msg = "top must be >= 1"
        raise FiveGateToolError(msg)
    with open_readonly_db(db_path) as conn:
        cur = conn.cursor()
        max_accepted = _max_accepted_chapter(cur, project_id)
        if max_accepted <= 0:
            msg = f"no accepted chapters found for project_id={project_id}"
            raise FiveGateToolError(msg)
        if up_to is None:
            resolved_up_to = max_accepted
        else:
            if up_to < 1:
                msg = "up_to must be >= 1"
                raise FiveGateToolError(msg)
            if up_to > max_accepted:
                msg = (
                    f"up_to={up_to} exceeds accepted boundary {max_accepted} "
                    f"for project_id={project_id}"
                )
                raise FiveGateToolError(msg)
            resolved_up_to = up_to

        hotspots = _collect_hotspots(cur, project_id, resolved_up_to, top=top)
        next_audit_chapter = ((resolved_up_to // 3) + 1) * 3
        critical_orphans, total_orphans = _predict_orphans(
            cur,
            project_id,
            resolved_up_to,
            next_audit_chapter,
        )
        health_trajectory = _collect_health_trajectory(cur, project_id, resolved_up_to)

    return SegmentAuditReport(
        project_id=project_id,
        up_to=resolved_up_to,
        next_audit_chapter=next_audit_chapter,
        critical_orphans=critical_orphans,
        total_orphans=total_orphans,
        hotspots=hotspots,
        health_trajectory=health_trajectory,
    )


def render_segment_audit(report: SegmentAuditReport) -> str:
    """Render a human-readable segment audit report."""
    lines = [f"=== segment deep audit @ Ch{report.up_to} ===", ""]
    lines.append("Legacy evidence hotspots (critical/major evidence issue count, all versions):")
    if report.hotspots:
        lines.extend(
            f"    Ch{hotspot.chapter_number:<3} {hotspot.issue_count}"
            for hotspot in report.hotspots
        )
    else:
        lines.append("    none")
    lines.append("")
    lines.append(
        f"Next continuity audit @Ch{report.next_audit_chapter}: "
        f"critical_orphans={report.critical_orphans} total_orphans={report.total_orphans} "
        f"-> halt would {'FIRE' if report.halt_would_fire else 'NOT fire'}"
    )
    lines.append("")
    trajectory = " ".join(
        f"Ch{point.checked_up_to_chapter}:{point.health}" for point in report.health_trajectory
    )
    lines.append(f"health trajectory: {trajectory or 'none'}")
    return "\n".join(lines)


def _max_accepted_chapter(cur: Any, project_id: str) -> int:
    cur.execute(
        """SELECT MAX(chapter_number) FROM chapter_heads
           WHERE project_id = ? AND accepted_version_id IS NOT NULL""",
        (project_id,),
    )
    row = cur.fetchone()
    return int(row[0] or 0)


def _collect_hotspots(cur: Any, project_id: str, up_to: int, *, top: int) -> tuple[Hotspot, ...]:
    cur.execute(
        """SELECT cv.chapter_number, rr.issues FROM review_reports rr
           JOIN chapter_versions cv ON cv.version_id = rr.chapter_version_id
           WHERE cv.project_id = ? AND cv.chapter_number <= ?""",
        (project_id, up_to),
    )
    per_chapter: dict[int, int] = {}
    for row in cur.fetchall():
        chapter_number = int(row["chapter_number"])
        for issue in parse_issues(row["issues"]):
            if _is_legacy_evidence_issue(issue):
                per_chapter[chapter_number] = per_chapter.get(chapter_number, 0) + 1
    return tuple(
        Hotspot(chapter_number=chapter, issue_count=count)
        for chapter, count in sorted(per_chapter.items(), key=lambda item: item[1], reverse=True)[
            :top
        ]
    )


def _is_legacy_evidence_issue(issue: dict[str, Any]) -> bool:
    severity = str(issue.get("severity", "")).lower()
    return severity in {"critical", "major"} and bool(issue.get("evidence_quote"))


def _predict_orphans(
    cur: Any,
    project_id: str,
    up_to: int,
    next_audit_chapter: int,
) -> tuple[int, int]:
    cur.execute(
        """SELECT last_mentioned_chapter, category FROM setting_tracking
           WHERE project_id = ? AND status = 'active'
             AND (last_mentioned_chapter IS NULL OR last_mentioned_chapter <= ?)""",
        (project_id, up_to),
    )
    critical_orphans = 0
    total_orphans = 0
    for row in cur.fetchall():
        last_mentioned = row["last_mentioned_chapter"]
        category = str(row["category"] or "background")
        threshold = ORPHAN_THRESHOLDS.get(category, ORPHAN_THRESHOLDS["background"])
        if last_mentioned is not None and (next_audit_chapter - int(last_mentioned)) > threshold:
            total_orphans += 1
            if category == "critical":
                critical_orphans += 1
    return critical_orphans, total_orphans


def _collect_health_trajectory(
    cur: Any,
    project_id: str,
    up_to: int,
) -> tuple[HealthPoint, ...]:
    cur.execute(
        """SELECT checked_up_to_chapter, overall_health_score FROM continuity_reports
           WHERE project_id = ? AND checked_up_to_chapter <= ?
           ORDER BY checked_up_to_chapter""",
        (project_id, up_to),
    )
    return tuple(
        HealthPoint(
            checked_up_to_chapter=int(row["checked_up_to_chapter"]),
            health=(
                float(row["overall_health_score"])
                if row["overall_health_score"] is not None
                else None
            ),
        )
        for row in cur.fetchall()
    )
