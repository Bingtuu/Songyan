"""058d Integration Test — new_issues_introduced end-to-end flow."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from songyan.agents.revision_handler import _detect_new_issues
from songyan.models import (
    LLMAuditResult,
    ReviewCategory,
    ReviewIssue,
    RuleAuditResult,
)
from songyan.workflows.review_merger import merge_reviews


class TestNewIssuesIntroducedFlow:
    """Integration test: new_issues_introduced flows from revision_handler_node
    to review_merger_node and gets merged into Round 2 issues.
    """

    @pytest.mark.asyncio
    async def test_merge_reviews_includes_previous_new_issues(self) -> None:
        """验证 Round 2 的 merge_reviews 正确合并上一轮的新问题."""
        rule_result = RuleAuditResult(
            ai_tell_count=0,
            fatigue_word_count=0,
            has_opening_hook=True,
            has_ending_hook=True,
        )
        llm_result = LLMAuditResult(
            issues=[],
            summary="",
        )

        # 模拟上一轮 revision 引入的新问题
        prev_new_issue = ReviewIssue(
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
            version_id="v-rev-1",
            content="正文",
            rule_result=rule_result,
            llm_result=llm_result,
            db=db,
            report_id="mr-test",
            previous_new_issues=[prev_new_issue],
        )

        assert len(merged.issues) == 1
        assert merged.issues[0].issue_id == "rev-ai_tell-abc123"
        assert merged.issues[0].severity == "major"
        # 合并后应重新计算 has_critical / has_major
        assert merged.has_critical is False
        assert merged.has_major is True

    @pytest.mark.asyncio
    async def test_merge_reviews_with_critical_new_issue(self) -> None:
        """验证 critical 级别的新问题被正确标记为 has_critical."""
        rule_result = RuleAuditResult(
            ai_tell_count=0,
            fatigue_word_count=0,
            has_opening_hook=True,
            has_ending_hook=True,
        )
        llm_result = LLMAuditResult(
            issues=[],
            summary="",
        )

        prev_new_issue = ReviewIssue(
            issue_id="rev-end_hook-xyz789",
            category=ReviewCategory.NARRATIVE_HOOK,
            severity="critical",
            evidence_quote="章末钩子丢失",
            evidence_location="章节末尾",
            issue_description="Revision 破坏了章末钩子",
            fix_type="patch",
        )

        db = AsyncMock()
        db.create = AsyncMock()
        merged = await merge_reviews(
            version_id="v-rev-2",
            content="正文",
            rule_result=rule_result,
            llm_result=llm_result,
            db=db,
            report_id="mr-test",
            previous_new_issues=[prev_new_issue],
        )

        assert len(merged.issues) == 1
        assert merged.has_critical is True

    def test_detect_new_issues_generates_review_issues(self) -> None:
        """验证 _detect_new_issues 生成符合 ReviewIssue 规范的 issue."""
        original = RuleAuditResult(
            ai_tell_count=1,
            fatigue_word_count=2,
            has_opening_hook=True,
            has_ending_hook=True,
        )
        revised = RuleAuditResult(
            ai_tell_count=5,
            fatigue_word_count=7,
            has_opening_hook=True,
            has_ending_hook=False,
        )

        issues = _detect_new_issues(original, revised)
        assert len(issues) == 3  # ai_tell + fatigue + ending_hook

        for issue in issues:
            assert issue.issue_id.startswith("rev-")
            assert issue.category in {
                ReviewCategory.SHOW_DONT_TELL,
                ReviewCategory.DESCRIPTION_SENSORY,
                ReviewCategory.NARRATIVE_HOOK,
            }
            assert issue.severity in {"major", "critical"}
            assert issue.fix_type == "patch"
            assert issue.confidence > 0

    def test_revision_output_model_accepts_new_issues(self) -> None:
        """验证 RevisionOutput 模型支持 new_issues_introduced 字段."""
        from songyan.models import RevisionOutput

        issue = ReviewIssue(
            issue_id="test-1",
            category=ReviewCategory.SHOW_DONT_TELL,
            severity="major",
            evidence_quote="test",
            evidence_location="loc",
            issue_description="desc",
            fix_type="patch",
        )

        output = RevisionOutput(
            new_version_id="v1",
            new_issues_introduced=[issue],
        )
        assert len(output.new_issues_introduced) == 1
        assert output.new_issues_introduced[0].issue_id == "test-1"
