"""Task 172b.q: consistency CED metric helper tests."""

from __future__ import annotations

import json

from songyan.evals.consistency_ced import (
    ReviewIssueReport,
    count_consistency_issues,
    count_evidence_issues,
    is_consistency_issue,
)


def _issue(category: str, *, severity: str = "major", evidence: bool = True) -> dict:
    return {
        "category": category,
        "severity": severity,
        "evidence_quote": "证据句" if evidence else "",
        "message": f"{category} issue",
    }


def _report(audit_type: str, issues: list[dict]) -> ReviewIssueReport:
    return ReviewIssueReport(audit_type=audit_type, issues_json=json.dumps(issues))


def test_craft_categories_do_not_count_as_consistency_ced() -> None:
    assert not is_consistency_issue(_issue("show_dont_tell"))
    assert not is_consistency_issue(_issue("narrative_pacing"))
    assert not is_consistency_issue(_issue("dialogue_subtext"))


def test_character_and_world_consistency_categories_count() -> None:
    assert is_consistency_issue(_issue("character_behavior"))
    assert is_consistency_issue(_issue("dialogue_distinctness"))
    assert is_consistency_issue(_issue("world_consistency"))


def test_requires_major_or_critical_evidence() -> None:
    assert not is_consistency_issue(_issue("world_consistency", severity="minor"))
    assert not is_consistency_issue(_issue("world_consistency", evidence=False))


def test_merged_report_prevents_llm_double_counting() -> None:
    llm = _report(
        "llm",
        [
            _issue("character_behavior"),
            _issue("show_dont_tell"),
        ],
    )
    merged = _report(
        "merged",
        [
            _issue("character_behavior"),
            _issue("dialogue_distinctness"),
            _issue("show_dont_tell"),
        ],
    )

    assert count_consistency_issues([llm, merged]) == 2
    assert count_evidence_issues([llm, merged]) == 3


def test_falls_back_to_source_reports_when_no_merged_report_exists() -> None:
    rule = _report("rule", [_issue("world_consistency")])
    llm = _report("llm", [_issue("dialogue_distinctness"), _issue("narrative_pacing")])

    assert count_consistency_issues([rule, llm]) == 2
    assert count_evidence_issues([rule, llm]) == 3


def test_invalid_issue_payload_is_ignored() -> None:
    broken = ReviewIssueReport(audit_type="merged", issues_json="{not json")

    assert count_consistency_issues([broken]) == 0
    assert count_evidence_issues([broken]) == 0
