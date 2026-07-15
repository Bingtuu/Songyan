"""Consistency Error Density helpers for V8 genre comparison.

CED is about consistency errors, not general literary craft observations.  The
helpers here keep the metric narrow and avoid double-counting the same issue
through both source auditor reports and ReviewMerger output.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

CONSISTENCY_CATEGORIES: frozenset[str] = frozenset(
    {
        "world_consistency",
        "character_behavior",
        "dialogue_distinctness",
        "supporting_character_goal_presence",
        "continuity",
        "state_mismatch",
        "setting_conflict",
    }
)

EVIDENCE_SEVERITIES: frozenset[str] = frozenset({"critical", "major"})


@dataclass(frozen=True)
class ReviewIssueReport:
    """A normalized review report payload used by CED helpers."""

    audit_type: str
    issues_json: str | None


def issue_category(issue: Mapping[str, Any]) -> str:
    """Return the most stable category-like field exposed by review issues."""
    for key in ("category", "artifact_type", "check_name", "type", "issue_type"):
        value = issue.get(key)
        if value:
            return str(value)
    return ""


def is_evidence_issue(issue: Mapping[str, Any]) -> bool:
    """True for critical/major issues that carry concrete evidence."""
    severity = str(issue.get("severity", "")).lower()
    return severity in EVIDENCE_SEVERITIES and bool(issue.get("evidence_quote"))


def is_mandatory_reference_aggregate(issue: Mapping[str, Any]) -> bool:
    """True for RuleAuditor's aggregate mandatory-reference work item.

    `rule-mr-*` issues list missing setting keys so RevisionHandler can patch
    them.  They are important control-flow issues, but their evidence quote is
    not a body-text quote and should not inflate Consistency Error Density.
    """
    issue_id = str(issue.get("issue_id", ""))
    return issue_id.startswith("rule-mr-")


def is_consistency_issue(issue: Mapping[str, Any]) -> bool:
    """True when an evidence issue belongs to the CED consistency taxonomy."""
    return (
        is_evidence_issue(issue)
        and not is_mandatory_reference_aggregate(issue)
        and issue_category(issue) in CONSISTENCY_CATEGORIES
    )


def is_ced_evidence_issue(issue: Mapping[str, Any]) -> bool:
    """True for evidence issues eligible for CED helper totals."""
    return is_evidence_issue(issue) and not is_mandatory_reference_aggregate(issue)


def parse_issues(issues_json: str | None) -> list[dict[str, Any]]:
    """Parse a review report issues payload defensively."""
    if not issues_json:
        return []
    try:
        raw = json.loads(issues_json)
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def select_ced_reports(
    reports: Iterable[ReviewIssueReport],
) -> list[ReviewIssueReport]:
    """Select report payloads for CED without auditor/merger double counting.

    ReviewMerger output is the canonical combined diagnostic for a version.  If
    any merged report exists for the version/report set being measured, use only
    merged reports.  Otherwise fall back to source auditor reports so old or
    partial data remains measurable.
    """
    materialized = list(reports)
    merged = [report for report in materialized if report.audit_type == "merged"]
    return merged or materialized


def count_consistency_issues(reports: Iterable[ReviewIssueReport]) -> int:
    """Count consistency evidence issues from selected CED reports."""
    count = 0
    for report in select_ced_reports(reports):
        count += sum(1 for issue in parse_issues(report.issues_json) if is_consistency_issue(issue))
    return count


def count_evidence_issues(reports: Iterable[ReviewIssueReport]) -> int:
    """Count all critical/major evidence issues from selected CED reports."""
    count = 0
    for report in select_ced_reports(reports):
        count += sum(
            1 for issue in parse_issues(report.issues_json) if is_ced_evidence_issue(issue)
        )
    return count
