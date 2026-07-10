"""Tests for RevisionHandler literary patch path (Task 170g Phase2)."""

from __future__ import annotations

from songyan.agents.revision_handler import (
    _build_literary_issues,
    _readability_driven,
)
from songyan.models import (
    ExpositionCarrierMatch,
    LLMAuditResult,
    MergedReviewReport,
    ReviewCategory,
    RuleAuditResult,
)


class TestReadabilityDrivenLiteraryTriggers:
    def test_exposition_carrier_count_triggers(self) -> None:
        report = MergedReviewReport(
            chapter_version_id="v1",
            rule_audit=RuleAuditResult(exposition_carrier_count=1),
        )
        assert _readability_driven(report, score_card=None) is True

    def test_no_exposition_carrier_no_trigger(self) -> None:
        report = MergedReviewReport(
            chapter_version_id="v1",
            rule_audit=RuleAuditResult(
                exposition_carrier_count=0,
                paragraph_rhythm_score=5.0,
            ),
        )
        assert _readability_driven(report, score_card=None) is False

    def test_dialogue_distinctness_low_triggers(self) -> None:
        report = MergedReviewReport(
            chapter_version_id="v1",
            rule_audit=RuleAuditResult(),
            llm_audit=LLMAuditResult(dimension_scores={"dialogue_distinctness": 4.0}),
        )
        assert _readability_driven(report, score_card=None) is True

    def test_info_dump_low_triggers(self) -> None:
        report = MergedReviewReport(
            chapter_version_id="v1",
            rule_audit=RuleAuditResult(),
            llm_audit=LLMAuditResult(dimension_scores={"info_dump": 3.5}),
        )
        assert _readability_driven(report, score_card=None) is True

    def test_voice_low_triggers(self) -> None:
        report = MergedReviewReport(
            chapter_version_id="v1",
            rule_audit=RuleAuditResult(),
            llm_audit=LLMAuditResult(dimension_scores={"voice": 2.5}),
        )
        assert _readability_driven(report, score_card=None) is True

    def test_exposition_low_triggers(self) -> None:
        report = MergedReviewReport(
            chapter_version_id="v1",
            rule_audit=RuleAuditResult(),
            llm_audit=LLMAuditResult(dimension_scores={"exposition": 2.0}),
        )
        assert _readability_driven(report, score_card=None) is True

    def test_dimension_scores_ok_no_trigger(self) -> None:
        report = MergedReviewReport(
            chapter_version_id="v1",
            rule_audit=RuleAuditResult(paragraph_rhythm_score=5.0),
            llm_audit=LLMAuditResult(
                dimension_scores={
                    "dialogue_distinctness": 6.0,
                    "info_dump": 5.5,
                    "voice": 5.0,
                    "exposition": 5.0,
                }
            ),
        )
        assert _readability_driven(report, score_card=None) is False


class TestBuildLiteraryIssues:
    def test_exposition_carrier_match_creates_issue(self) -> None:
        report = MergedReviewReport(
            chapter_version_id="v1",
            rule_audit=RuleAuditResult(
                exposition_carrier_count=1,
                exposition_carrier_matches=[
                    ExpositionCarrierMatch(
                        carrier_type="direct_revelation_monologue",
                        matched_text="方舟是牢笼",
                        location="第3段",
                    )
                ],
            ),
        )
        issues = _build_literary_issues(report)
        assert len(issues) == 1
        issue = issues[0]
        assert issue.issue_id == "rh-exposition-0"
        assert issue.category == ReviewCategory.SHOW_DONT_TELL
        assert issue.severity == "major"
        assert "方舟是牢笼" in issue.evidence_quote
        assert issue.fix_type == "patch"

    def test_multiple_exposition_matches_capped(self) -> None:
        matches = [
            ExpositionCarrierMatch(
                carrier_type="info_delivery_dialogue",
                matched_text=f"命中{i}",
                location=f"第{i}段",
            )
            for i in range(5)
        ]
        report = MergedReviewReport(
            chapter_version_id="v1",
            rule_audit=RuleAuditResult(
                exposition_carrier_count=5,
                exposition_carrier_matches=matches,
            ),
        )
        issues = _build_literary_issues(report)
        assert len(issues) == 3
        assert issues[0].issue_id == "rh-exposition-0"
        assert issues[2].issue_id == "rh-exposition-2"

    def test_llm_dimension_low_creates_fallback_issue(self) -> None:
        report = MergedReviewReport(
            chapter_version_id="v1",
            rule_audit=RuleAuditResult(),
            llm_audit=LLMAuditResult(
                dimension_scores={
                    "dialogue_distinctness": 4.0,
                    "info_dump": 3.5,
                }
            ),
        )
        issues = _build_literary_issues(report)
        ids = {i.issue_id for i in issues}
        assert "rh-dialogue-distinctness-0" in ids
        assert "rh-info-dump-0" in ids
        dialogue_issue = next(
            i for i in issues if i.issue_id == "rh-dialogue-distinctness-0"
        )
        assert dialogue_issue.category == ReviewCategory.DIALOGUE_DISTINCTNESS
        info_issue = next(i for i in issues if i.issue_id == "rh-info-dump-0")
        assert info_issue.category == ReviewCategory.INFO_DUMP

    def test_voice_exposition_low_creates_fallback_issues(self) -> None:
        report = MergedReviewReport(
            chapter_version_id="v1",
            rule_audit=RuleAuditResult(),
            llm_audit=LLMAuditResult(
                dimension_scores={
                    "voice": 2.5,
                    "exposition": 2.0,
                }
            ),
        )
        issues = _build_literary_issues(report)
        ids = {i.issue_id for i in issues}
        assert "rh-voice-0" in ids
        assert "rh-exposition-0" in ids
        voice_issue = next(i for i in issues if i.issue_id == "rh-voice-0")
        assert voice_issue.category == ReviewCategory.VOICE
        exposition_issue = next(i for i in issues if i.issue_id == "rh-exposition-0")
        assert exposition_issue.category == ReviewCategory.EXPOSITION
        assert voice_issue.fix_type == "patch"
        assert exposition_issue.fix_type == "patch"
        assert "认知冲突" in exposition_issue.suggested_fix

    def test_unconflicted_revelation_creates_exposition_issue(self) -> None:
        report = MergedReviewReport(
            chapter_version_id="v1",
            rule_audit=RuleAuditResult(
                exposition_carrier_count=1,
                exposition_carrier_matches=[
                    ExpositionCarrierMatch(
                        carrier_type="unconflicted_revelation",
                        matched_text="方舟是牢笼",
                        location="第3段",
                    )
                ],
            ),
        )
        issues = _build_literary_issues(report)
        assert len(issues) == 1
        assert issues[0].category == ReviewCategory.EXPOSITION
        assert "对立判断" in issues[0].suggested_fix

    def test_human_voice_homogeneity_creates_dialogue_issue(self) -> None:
        report = MergedReviewReport(
            chapter_version_id="v1",
            rule_audit=RuleAuditResult(
                exposition_carrier_count=1,
                exposition_carrier_matches=[
                    ExpositionCarrierMatch(
                        carrier_type="human_voice_homogeneity",
                        matched_text="陈薇与林渊对白趋同",
                        location="场景2",
                    )
                ],
            ),
        )
        issues = _build_literary_issues(report)
        assert len(issues) == 1
        assert issues[0].category == ReviewCategory.DIALOGUE_DISTINCTNESS
        assert "声纹同质化" in issues[0].issue_description

    def test_protagonist_summary_tell_creates_show_dont_tell_issue(self) -> None:
        report = MergedReviewReport(
            chapter_version_id="v1",
            rule_audit=RuleAuditResult(
                exposition_carrier_count=1,
                exposition_carrier_matches=[
                    ExpositionCarrierMatch(
                        carrier_type="protagonist_summary_tell",
                        matched_text="他终于懂了",
                        location="第5段",
                    )
                ],
            ),
        )
        issues = _build_literary_issues(report)
        assert len(issues) == 1
        assert issues[0].category == ReviewCategory.SHOW_DONT_TELL
        assert "主角总结容器" in issues[0].issue_description

    def test_no_rule_audit_no_crash(self) -> None:
        report = MergedReviewReport(
            chapter_version_id="v1",
            llm_audit=LLMAuditResult(),
        )
        issues = _build_literary_issues(report)
        assert issues == []

    def test_no_llm_audit_no_crash(self) -> None:
        report = MergedReviewReport(
            chapter_version_id="v1",
            rule_audit=RuleAuditResult(exposition_carrier_count=0),
        )
        issues = _build_literary_issues(report)
        assert issues == []
