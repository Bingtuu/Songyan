"""Tests for ReviewMerger — 058d new_issues_introduced merge + 060 word_count threshold."""

from __future__ import annotations

import pytest

from songyan.models import (
    LLMAuditResult,
    ReviewCategory,
    ReviewIssue,
    RuleAuditResult,
)
from songyan.workflows.review_merger import _convert_rule_to_issues, merge_reviews


class TestMergeReviewsPreviousNewIssues:
    """Tests for merge_reviews with previous_new_issues — 058d."""

    @pytest.fixture
    def rule_result(self) -> RuleAuditResult:
        return RuleAuditResult(
            ai_tell_count=0,
            fatigue_word_count=0,
            has_opening_hook=True,
            has_ending_hook=True,
        )

    @pytest.fixture
    def llm_result(self) -> LLMAuditResult:
        return LLMAuditResult(
            issues=[],
            summary="",
        )

    @pytest.mark.asyncio
    async def test_no_previous_issues(
        self, rule_result: RuleAuditResult, llm_result: LLMAuditResult
    ) -> None:
        from unittest.mock import AsyncMock

        db = AsyncMock()
        db.create = AsyncMock()
        merged = await merge_reviews(
            version_id="v1",
            content="正文",
            rule_result=rule_result,
            llm_result=llm_result,
            db=db,
            report_id="mr-test",
            previous_new_issues=None,
        )
        assert merged.issues == []

    @pytest.mark.asyncio
    async def test_merges_previous_new_issues(
        self, rule_result: RuleAuditResult, llm_result: LLMAuditResult
    ) -> None:
        from unittest.mock import AsyncMock

        prev_issue = ReviewIssue(
            issue_id="rev-ai_tell-abc123",
            category=ReviewCategory.SHOW_DONT_TELL,
            severity="major",
            evidence_quote="AI腔增加",
            evidence_location="revision后全文",
            issue_description="Revision 引入了新的 AI 腔",
            fix_type="patch",
        )

        db = AsyncMock()
        db.create = AsyncMock()
        merged = await merge_reviews(
            version_id="v1",
            content="正文",
            rule_result=rule_result,
            llm_result=llm_result,
            db=db,
            report_id="mr-test",
            previous_new_issues=[prev_issue],
        )
        assert len(merged.issues) == 1
        assert merged.issues[0].issue_id == "rev-ai_tell-abc123"

    @pytest.mark.asyncio
    async def test_merges_with_existing_issues(
        self, rule_result: RuleAuditResult, llm_result: LLMAuditResult
    ) -> None:
        from unittest.mock import AsyncMock

        llm_result_with_issue = LLMAuditResult(
            issues=[
                ReviewIssue(
                    issue_id="llm-1",
                    category=ReviewCategory.CHARACTER_BEHAVIOR,
                    severity="major",
                    evidence_quote="quote",
                    evidence_location="第2段",
                    issue_description="desc",
                    fix_type="patch",
                ),
            ],
            summary="",
        )

        prev_issue = ReviewIssue(
            issue_id="rev-fatigue-xyz789",
            category=ReviewCategory.DESCRIPTION_SENSORY,
            severity="major",
            evidence_quote="疲劳词增加",
            evidence_location="revision后全文",
            issue_description="Revision 引入了新的疲劳词",
            fix_type="patch",
        )

        db = AsyncMock()
        db.create = AsyncMock()
        merged = await merge_reviews(
            version_id="v1",
            content="正文",
            rule_result=rule_result,
            llm_result=llm_result_with_issue,
            db=db,
            report_id="mr-test",
            previous_new_issues=[prev_issue],
        )
        assert len(merged.issues) == 2
        issue_ids = {i.issue_id for i in merged.issues}
        assert "llm-1" in issue_ids
        assert "rev-fatigue-xyz789" in issue_ids


# ---------------------------------------------------------------------------
# 060: Word Count Threshold Tests
# ---------------------------------------------------------------------------
class TestWordCountThreshold:
    """Tests for word_count_ratio >= 1.20 triggering violation — Task 060."""

    def test_word_count_ratio_1_19_no_violation(self) -> None:
        """119% 不触发字数 violation."""
        rule_result = RuleAuditResult(
            word_count=3570,
            word_count_target=3000,
            word_count_ratio=1.19,
            word_count_ok=False,
        )
        issues = _convert_rule_to_issues("正文", rule_result, "v1")
        word_count_issues = [i for i in issues if "字数严重超标" in i.issue_description]
        assert len(word_count_issues) == 0

    def test_word_count_ratio_1_20_triggers_violation(self) -> None:
        """120% 恰好触发字数 violation."""
        rule_result = RuleAuditResult(
            word_count=3600,
            word_count_target=3000,
            word_count_ratio=1.20,
            word_count_ok=False,
        )
        issues = _convert_rule_to_issues("正文", rule_result, "v1")
        word_count_issues = [i for i in issues if "字数严重超标" in i.issue_description]
        assert len(word_count_issues) == 1
        assert word_count_issues[0].severity == "major"
        assert "20%" in word_count_issues[0].evidence_quote

    def test_word_count_ratio_1_30_triggers_violation(self) -> None:
        """130% 触发字数 violation."""
        rule_result = RuleAuditResult(
            word_count=3900,
            word_count_target=3000,
            word_count_ratio=1.30,
            word_count_ok=False,
        )
        issues = _convert_rule_to_issues("正文", rule_result, "v1")
        word_count_issues = [i for i in issues if "字数严重超标" in i.issue_description]
        assert len(word_count_issues) == 1
        assert word_count_issues[0].severity == "major"
        assert "30%" in word_count_issues[0].evidence_quote

    def test_word_count_ratio_none_no_crash(self) -> None:
        """word_count_target=0 时不抛异常."""
        rule_result = RuleAuditResult(
            word_count=100,
            word_count_target=0,
            word_count_ratio=0.0,
            word_count_ok=False,
        )
        issues = _convert_rule_to_issues("正文", rule_result, "v1")
        # 不抛异常即通过
        assert isinstance(issues, list)

    def test_word_count_ratio_1_20_with_other_issues(self) -> None:
        """120% + 其他 violation 时合并正确."""
        rule_result = RuleAuditResult(
            has_opening_hook=False,
            has_ending_hook=False,
            word_count=3600,
            word_count_target=3000,
            word_count_ratio=1.20,
            word_count_ok=False,
        )
        issues = _convert_rule_to_issues("正文", rule_result, "v1")
        # 应有：首屏钩子(critical) + 章末钩子(critical) + 字数(major)
        assert len(issues) == 3
        severities = [i.severity for i in issues]
        assert severities.count("critical") == 2
        assert severities.count("major") == 1


# ---------------------------------------------------------------------------
# Task 095: Scene Structure Issues
# ---------------------------------------------------------------------------
class TestSceneStructureIssues:
    """Tests for Task 095: scene structure issue conversion."""

    def test_single_scene_major_issue(self) -> None:
        # Task 133: 字数 >1500 且单场景才触发 major scene_split issue
        rule_result = RuleAuditResult(
            word_count=2000,
            scene_count=1,
            scene_count_ok=False,
        )
        issues = _convert_rule_to_issues("正文", rule_result, "v1")
        scene_issues = [i for i in issues if "仅有 1 个场景" in i.issue_description]
        assert len(scene_issues) == 1
        assert scene_issues[0].severity == "major"
        assert scene_issues[0].fix_type == "scene_split"

    def test_short_single_scene_no_issue(self) -> None:
        # Task 133: 字数 <=1500 的单章节不触发场景结构问题
        rule_result = RuleAuditResult(
            word_count=1200,
            scene_count=1,
            scene_count_ok=False,
        )
        issues = _convert_rule_to_issues("正文", rule_result, "v1")
        scene_issues = [i for i in issues if "仅有 1 个场景" in i.issue_description]
        assert len(scene_issues) == 0

    def test_too_many_scenes_minor_issue(self) -> None:
        rule_result = RuleAuditResult(
            scene_count=5,
            scene_count_ok=False,
        )
        issues = _convert_rule_to_issues("正文", rule_result, "v1")
        scene_issues = [i for i in issues if "场景数过多" in i.issue_description]
        assert len(scene_issues) == 1
        assert scene_issues[0].severity == "minor"
        assert scene_issues[0].fix_type == "patch"

    def test_normal_scenes_no_issue(self) -> None:
        rule_result = RuleAuditResult(
            scene_count=3,
            scene_count_ok=True,
        )
        issues = _convert_rule_to_issues("正文", rule_result, "v1")
        scene_issues = [i for i in issues if "场景" in i.issue_description]
        assert len(scene_issues) == 0
