"""Task 138n: mandatory reference 聚合、上限与专用 patch 路径测试."""

from __future__ import annotations

from typing import Any

import pytest

from songyan.agents.revision_handler import (
    MIN_CONTENT_RATIO,
    _patch_mandatory_reference_missing,
    run_revision,
)
from songyan.models import (
    AiTellMatch,
    FatigueWordMatch,
    LLMAuditResult,
    MergedReviewReport,
    ReviewCategory,
    ReviewIssue,
    RuleAuditResult,
)
from songyan.workflows._helpers import _load_critical_mandatory_references
from songyan.workflows.review_merger import _convert_rule_to_issues


class TestLoadCriticalMandatoryReferences:
    """C1: _load_critical_mandatory_references 上限与排序."""

    @pytest.mark.asyncio
    async def test_sort_by_silent_and_introduced(self, monkeypatch: Any) -> None:
        rows = [
            {
                "setting_key": "a.silent8",
                "setting_name": "A",
                "status": "active",
                "category": "critical",
                "last_mentioned_chapter": 2,
                "introduced_in_chapter": 1,
            },
            {
                "setting_key": "b.silent6",
                "setting_name": "B",
                "status": "active",
                "category": "critical",
                "last_mentioned_chapter": 4,
                "introduced_in_chapter": 2,
            },
            {
                "setting_key": "c.silent5_intro4",
                "setting_name": "C",
                "status": "active",
                "category": "critical",
                "last_mentioned_chapter": 5,
                "introduced_in_chapter": 4,
            },
            {
                "setting_key": "d.silent5_intro1",
                "setting_name": "D",
                "status": "active",
                "category": "critical",
                "last_mentioned_chapter": 5,
                "introduced_in_chapter": 1,
            },
        ]

        async def mock_list(self, _project_id: str) -> list[dict]:
            return rows

        monkeypatch.setattr(
            "songyan.workflows._helpers.SettingTrackingRepository.list_by_project",
            mock_list,
        )

        result = await _load_critical_mandatory_references("p1", 10)
        keys = [r["setting_key"] for r in result]
        assert keys == [
            "a.silent8",
            "b.silent6",
            "d.silent5_intro1",
            "c.silent5_intro4",
        ]

    @pytest.mark.asyncio
    async def test_default_cap_by_scenes_count(self, monkeypatch: Any) -> None:
        rows = [
            {
                "setting_key": f"k{i}",
                "setting_name": f"K{i}",
                "status": "active",
                "category": "critical",
                "last_mentioned_chapter": 1,
                "introduced_in_chapter": 1,
            }
            for i in range(8)
        ]

        async def mock_list(self, _project_id: str) -> list[dict]:
            return rows

        monkeypatch.setattr(
            "songyan.workflows._helpers.SettingTrackingRepository.list_by_project",
            mock_list,
        )

        # scenes_count=2 -> max = min(max(4, 6), 12) = 6
        result = await _load_critical_mandatory_references(
            "p1", 10, scenes_count=2
        )
        assert len(result) == 6
        assert all(r["setting_key"].startswith("k") for r in result)

    @pytest.mark.asyncio
    async def test_explicit_max_overrides_default(self, monkeypatch: Any) -> None:
        rows = [
            {
                "setting_key": f"k{i}",
                "setting_name": f"K{i}",
                "status": "active",
                "category": "critical",
                "last_mentioned_chapter": 1,
                "introduced_in_chapter": 1,
            }
            for i in range(4)
        ]

        async def mock_list(self, _project_id: str) -> list[dict]:
            return rows

        monkeypatch.setattr(
            "songyan.workflows._helpers.SettingTrackingRepository.list_by_project",
            mock_list,
        )

        result = await _load_critical_mandatory_references(
            "p1", 10, scenes_count=10, max_mandatory_references=2
        )
        assert len(result) == 2


class TestReviewMergerMRAggregation:
    """A1: ReviewMerger 将 MR 缺失聚合成单个 issue 且不受 cap 影响."""

    def test_aggregate_mandatory_reference_issues(self) -> None:
        missing = [
            {
                "setting_key": f"world.core.missing_{i}",
                "setting_name": f"缺失设定{i}",
                "silent_chapters": i + 3,
                "message": f"强制连续性约束未回收：缺失设定{i}",
            }
            for i in range(8)
        ]
        rule_result = RuleAuditResult(
            mandatory_reference_check_passed=False,
            mandatory_reference_issues=missing,
            has_ending_hook=False,  # 产生另一个 rule issue
        )
        issues = _convert_rule_to_issues("正文", rule_result, "v1")

        mr_issues = [i for i in issues if i.issue_id.startswith("rule-mr-")]
        assert len(mr_issues) == 1
        mr = mr_issues[0]
        assert mr.category == ReviewCategory.WORLD_CONSISTENCY
        assert mr.severity == "critical"
        assert mr.fix_type == "patch"
        for i in range(8):
            assert f"world.core.missing_{i}" in mr.evidence_quote
        # MR 聚合 issue 放在最前面
        assert issues[0].issue_id == mr.issue_id

    def test_cap_does_not_drop_aggregated_mr(self) -> None:
        # 构造 8 个 MR + 多个其他 rule issues，总 issues > 5
        missing = [
            {
                "setting_key": f"world.core.missing_{i}",
                "setting_name": f"缺失设定{i}",
                "silent_chapters": i + 3,
                "message": f"强制连续性约束未回收：缺失设定{i}",
            }
            for i in range(8)
        ]
        rule_result = RuleAuditResult(
            mandatory_reference_check_passed=False,
            mandatory_reference_issues=missing,
            has_opening_hook=False,
            has_ending_hook=False,
            ai_tell_count=2,
            ai_tell_matches=[
                AiTellMatch(matched_text="a", pattern="p", location="")
                for _ in range(2)
            ],
            fatigue_word_count=3,
            fatigue_word_matches=[
                FatigueWordMatch(word="w", count=3, locations=[])
                for _ in range(3)
            ],
        )
        issues = _convert_rule_to_issues("正文", rule_result, "v1")
        assert issues[0].issue_id.startswith("rule-mr-")
        # MR issue 始终保留，其他问题受 cap 限制为 5 个
        assert len(issues) <= 6


class TestMRPatch:
    """A2: MR 专用 patch 路径."""

    @pytest.mark.asyncio
    async def test_patch_inserts_missing_refs(self, monkeypatch: Any) -> None:
        content = "林渊走进遗迹大厅，脚步声在空旷中回荡。"
        missing_refs = [
            {
                "setting_key": "ruins.core.memory_city",
                "setting_name": "记忆之城",
            },
            {
                "setting_key": "ruins.core.light_deflection",
                "setting_name": "光线偏折",
            },
        ]

        async def fake_llm(prompt: str, **kwargs: object) -> str:
            # 简单模拟 LLM 在正文后追加自然提及
            return (
                content
                + " 他抬头瞥见记忆之城的全息投影，"
                "光线偏折让墙壁像水波一样晃动。"
            )

        monkeypatch.setattr(
            "songyan.agents.revision_handler.call_llm", fake_llm
        )

        revised, fixed = await _patch_mandatory_reference_missing(
            content, missing_refs, word_count_target=3000
        )

        assert "记忆之城" in revised
        assert "光线偏折" in revised
        assert len(fixed) == 2
        preservation_ratio = len(revised) / len(content)
        assert preservation_ratio >= MIN_CONTENT_RATIO

    @pytest.mark.asyncio
    async def test_run_revision_routes_mr_issue(self, monkeypatch: Any) -> None:
        content = "林渊走进遗迹大厅，脚步声在空旷中回荡。"
        missing_refs = [
            {
                "setting_key": "ruins.core.memory_city",
                "setting_name": "记忆之城",
            }
        ]

        async def fake_llm(prompt: str, **kwargs: object) -> str:
            return content + " 记忆之城的投影在角落闪烁。"

        monkeypatch.setattr(
            "songyan.agents.revision_handler.call_llm", fake_llm
        )

        rule_audit = RuleAuditResult(
            mandatory_reference_check_passed=False,
            mandatory_reference_issues=missing_refs,
        )
        report = MergedReviewReport(
            chapter_version_id="v1",
            rule_audit=rule_audit,
            llm_audit=LLMAuditResult(),
            issues=[
                ReviewIssue(
                    issue_id="rule-mr-v1",
                    category=ReviewCategory.WORLD_CONSISTENCY,
                    severity="critical",
                    evidence_quote="ruins.core.memory_city",
                    evidence_location="全章",
                    issue_description="缺失 1 个 critical 设定",
                    fix_type="patch",
                )
            ],
        )

        output, revised = await run_revision(content, report)

        assert "记忆之城" in revised
        assert "rule-mr-v1" in output.issues_fixed
        assert "rule-mr-v1" not in output.issues_remaining
        assert output.content_preservation_ratio is not None
        assert output.content_preservation_ratio >= MIN_CONTENT_RATIO
