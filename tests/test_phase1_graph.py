"""Tests for Phase 1 LangGraph workflow, ReviewMerger, and SummaryWriter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from songyan.models import (
    AiTellMatch,
    ChapterSummary,
    CharacterUpdate,
    FatigueWordMatch,
    LLMAuditResult,
    MergedReviewReport,
    NewSetting,
    ReviewCategory,
    ReviewIssue,
    RuleAuditResult,
    StateSettlement,
)
from songyan.workflows.phase1_graph import (
    Phase1State,
    build_phase1_graph,
    human_confirm_router,
    revision_router,
)
from songyan.workflows.review_merger import (
    _compute_overall_score,
    _convert_rule_to_issues,
    _merge_summary,
    merge_reviews,
)

# =============================================================================
# ReviewMerger Tests
# =============================================================================


class TestComputeOverallScore:
    def test_perfect_score(self) -> None:
        rule = RuleAuditResult(
            ai_tell_count=0,
            fatigue_word_count=0,
            has_opening_hook=True,
            has_ending_hook=True,
            paragraph_rhythm_score=8.0,
        )
        llm = LLMAuditResult(dimension_scores={"world_consistency": 10.0})
        score = _compute_overall_score(rule, llm)
        assert score == 10.0 * 0.6 + 10.0 * 0.4

    def test_with_penalties(self) -> None:
        rule = RuleAuditResult(
            ai_tell_count=3,
            fatigue_word_count=5,
            has_opening_hook=False,
            has_ending_hook=False,
            paragraph_rhythm_score=3.0,
        )
        llm = LLMAuditResult(dimension_scores={"world_consistency": 8.0})
        score = _compute_overall_score(rule, llm)
        assert score < 8.0
        assert score >= 0.0


class TestMergeSummary:
    def test_output_contains_key_metrics(self) -> None:
        rule = RuleAuditResult(
            ai_tell_count=2,
            fatigue_word_count=1,
            has_opening_hook=True,
            has_ending_hook=False,
            word_count=3200,
            word_count_target=3000,
        )
        llm = LLMAuditResult(issues=[], summary="OK")
        summary = _merge_summary(rule, llm)
        assert "AI腔: 2处" in summary
        assert "疲劳词: 1处" in summary
        assert "首屏钩子: 有" in summary
        assert "章末钩子: 无" in summary
        assert "字数: 3200/3000" in summary


class TestMergeReviews:
    @pytest.mark.asyncio
    async def test_merges_rule_and_llm_results(self) -> None:
        rule = RuleAuditResult(
            ai_tell_count=1,
            fatigue_word_count=0,
            has_opening_hook=True,
            has_ending_hook=True,
        )
        llm = LLMAuditResult(
            issues=[
                ReviewIssue(
                    issue_id="i1",
                    category=ReviewCategory.WORLD_CONSISTENCY,
                    severity="major",
                    evidence_quote="quote",
                    evidence_location="loc",
                    issue_description="desc",
                ),
            ],
            dimension_scores={"world_consistency": 7.0},
        )
        mock_db = AsyncMock()

        report = await merge_reviews("v1", "some content", rule, llm, mock_db)

        assert isinstance(report, MergedReviewReport)
        assert report.chapter_version_id == "v1"
        assert report.ai_tell_count == 1
        assert report.fatigue_word_count == 0
        assert report.has_opening_hook is True
        assert len(report.issues) == 1
        assert report.issues[0].severity == "major"
        mock_db.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_rule_issues_injected_when_critical(self) -> None:
        """RuleAuditor 严重问题应被转化为 ReviewIssue 注入报告."""
        rule = RuleAuditResult(
            ai_tell_count=2,
            ai_tell_matches=[
                AiTellMatch(pattern="p1", matched_text="他很愤怒", location="第3段"),
                AiTellMatch(pattern="p2", matched_text="她很难过", location="第5段"),
            ],
            fatigue_word_count=3,
            fatigue_word_matches=[
                FatigueWordMatch(word="突然", count=3, locations=["第1段"]),
            ],
            has_opening_hook=False,
            has_ending_hook=False,
            paragraph_rhythm_score=3.0,
            rhythm_issues=["连续5段超过200字", "缺少短句变化"],
            word_count=4200,
            word_count_target=3000,
            word_count_ok=False,
        )
        llm = LLMAuditResult(issues=[], dimension_scores={})
        mock_db = AsyncMock()

        report = await merge_reviews("v1", "x" * 500, rule, llm, mock_db)

        # issues 应包含 LLM issues (0) + Rule issues
        assert len(report.issues) > 0
        categories = {i.category for i in report.issues}
        # critical 钩子问题必须存在
        assert ReviewCategory.NARRATIVE_HOOK in categories
        # 至少有一个 major 问题被注入
        major_categories = categories - {ReviewCategory.NARRATIVE_HOOK}
        assert len(major_categories) >= 1

        # 检查 critical 级别
        critical_count = sum(1 for i in report.issues if i.severity == "critical")
        assert critical_count == 2  # opening + ending hook

        # 所有 issues 的 fix_type 应为 patch
        for issue in report.issues:
            assert issue.fix_type == "patch"

    def test_convert_rule_to_issues_capped_at_5(self) -> None:
        """规则问题应被上限保护，避免 RevisionHandler 过载."""
        rule = RuleAuditResult(
            ai_tell_count=10,
            ai_tell_matches=[
                AiTellMatch(pattern="p", matched_text=f"match{i}", location=f"第{i}段")
                for i in range(10)
            ],
            fatigue_word_count=10,
            fatigue_word_matches=[
                FatigueWordMatch(word=f"w{i}", count=i, locations=[f"第{i}段"])
                for i in range(1, 11)
            ],
            has_opening_hook=False,
            has_ending_hook=False,
            word_count=5000,
            word_count_target=3000,
            word_count_ok=False,
            paragraph_rhythm_score=2.0,
            rhythm_issues=["节奏差"],
        )
        issues = _convert_rule_to_issues("x" * 500, rule, "v1")
        assert len(issues) <= 5


# =============================================================================
# Router Tests
# =============================================================================


def _base_revision_state(**overrides: object) -> Phase1State:
    """创建 revision_router 测试的基础状态."""
    state: Phase1State = {
        "project_id": "p1",
        "chapter_number": 1,
        "mode_id": "webnovel",
        "chapter_goal_id": None,
        "creative_brief_id": None,
        "current_version_id": None,
        "review_report_id": None,
        "literary_observation_id": None,
        "settlement_id": None,
        "summary_id": None,
        "revision_round": 0,
        "status": "revision_routing",
        "human_decision": None,
        "error": None,
        "previous_summary": "",
        "_needs_revision": False,
        "_has_critical": False,
        "_has_major": False,
        "_best_issues_count": None,
        "_best_overall_score": None,
        "_best_version_id": None,
        "_best_report_id": None,
        "_current_issues_count": None,
        "_current_overall_score": None,
        "_revision_rebound": False,
        "_content_preservation_ratio": None,
        "_new_issues_introduced": None,
        "_settlement_needs_human_review": False,
        "_was_rewritten": False,
        "_rewrite_reason": None,
    }
    state.update(overrides)  # type: ignore[typeddict-item]
    return state


class TestRevisionRouter:
    def test_critical_and_under_round_limit(self) -> None:
        state = _base_revision_state(
            revision_round=0,
            _needs_revision=True,
            _has_critical=True,
        )
        assert revision_router(state) == "revise"

    def test_major_and_under_round_limit(self) -> None:
        state = _base_revision_state(
            revision_round=1,
            _needs_revision=True,
            _has_major=True,
        )
        assert revision_router(state) == "revise"

    def test_over_round_limit_triggers_rewrite(self) -> None:
        """073: 2 轮后仍有 issue → 触发 rewrite."""
        state = _base_revision_state(
            revision_round=2,
            _needs_revision=True,
            _has_critical=True,
        )
        assert revision_router(state) == "rewrite"

    def test_over_round_limit_already_rewritten_passes(self) -> None:
        """073: 已重写的章节直接 pass."""
        state = _base_revision_state(
            revision_round=2,
            _needs_revision=True,
            _has_critical=True,
            _was_rewritten=True,
        )
        assert revision_router(state) == "pass"

    def test_was_rewritten_round_0_needs_revision(self) -> None:
        """rewrite 后第 0 轮仍有 issue → 直接 pass."""
        state = _base_revision_state(
            revision_round=0,
            _needs_revision=True,
            _has_critical=True,
            _was_rewritten=True,
        )
        assert revision_router(state) == "pass"

    def test_was_rewritten_round_1_needs_revision(self) -> None:
        """rewrite 后第 1 轮仍有 issue → 强制 pass."""
        state = _base_revision_state(
            revision_round=1,
            _needs_revision=True,
            _has_critical=True,
            _was_rewritten=True,
        )
        assert revision_router(state) == "pass"

    def test_was_rewritten_round_0_no_issues(self) -> None:
        """rewrite 后无 issue → 直接 pass."""
        state = _base_revision_state(
            revision_round=0,
            _needs_revision=False,
            _was_rewritten=True,
        )
        assert revision_router(state) == "pass"

    def test_no_issues(self) -> None:
        state = _base_revision_state(
            revision_round=0,
            _needs_revision=False,
        )
        assert revision_router(state) == "pass"

    def test_error_defaults_to_pass(self) -> None:
        state = _base_revision_state(
            revision_round=0,
            _needs_revision=True,
            _has_critical=True,
            error="something wrong",
        )
        assert revision_router(state) == "pass"


class TestHumanConfirmRouter:
    def test_accept(self) -> None:
        state: Phase1State = {
            "project_id": "p1",
            "chapter_number": 1,
            "mode_id": "webnovel",
            "chapter_goal_id": None,
            "creative_brief_id": None,
            "current_version_id": None,
            "review_report_id": None,
            "literary_observation_id": None,
            "settlement_id": None,
            "summary_id": None,
            "revision_round": 0,
            "status": "human_confirm",
            "human_decision": "accept",
            "error": None,
            "_needs_revision": False,
            "_has_critical": False,
            "_has_major": False,
        }
        assert human_confirm_router(state) == "accept"

    def test_edit(self) -> None:
        state = self._base_state()
        state["human_decision"] = "edit"
        # Task 100b: edit 后重走 Audit 流程
        assert human_confirm_router(state) == "edit_audit"

    def test_reject(self) -> None:
        state = self._base_state()
        state["human_decision"] = "reject"
        assert human_confirm_router(state) == "reject"

    def test_back(self) -> None:
        state = self._base_state()
        state["human_decision"] = "back"
        assert human_confirm_router(state) == "back"

    def test_defaults_to_accept(self) -> None:
        state = self._base_state()
        state["human_decision"] = None
        assert human_confirm_router(state) == "accept"

    def test_word_count_guard(self) -> None:
        state = self._base_state()
        state["human_decision"] = "word_count_guard"
        assert human_confirm_router(state) == "word_count_guard"

    @staticmethod
    def _base_state() -> Phase1State:
        return {
            "project_id": "p1",
            "chapter_number": 1,
            "mode_id": "webnovel",
            "chapter_goal_id": None,
            "creative_brief_id": None,
            "current_version_id": None,
            "review_report_id": None,
            "literary_observation_id": None,
            "settlement_id": None,
            "summary_id": None,
            "revision_round": 0,
            "status": "human_confirm",
            "human_decision": "accept",
            "error": None,
            "_needs_revision": False,
            "_has_critical": False,
            "_has_major": False,
        }


# =============================================================================
# Graph Structure Tests
# =============================================================================


class TestGraphStructure:
    @pytest.mark.anyio
    async def test_graph_compiles(self) -> None:
        graph = await build_phase1_graph()
        assert graph is not None

    @pytest.mark.anyio
    async def test_all_nodes_registered(self) -> None:
        graph = await build_phase1_graph()
        expected_nodes = {
            "goal_planner",
            "creative_director",
            "context_manager",
            "writer",
            "rule_auditor",
            "llm_auditor",
            "review_merger",
            "literary_auditor",
            "revision_handler",
            "quality_gate",
            "human_confirm",
            "settlement_extractor",
            "__start__",
            "__end__",
        }
        # LangGraph compiled graph exposes nodes via get_graph().nodes
        nodes = set(graph.get_graph().nodes.keys())
        assert expected_nodes <= nodes, f"Missing nodes: {expected_nodes - nodes}"


# =============================================================================
# SummaryWriter Tests
# =============================================================================


class TestSummaryWriter:
    @pytest.mark.asyncio
    async def test_extracts_from_settlement(self) -> None:
        from songyan.agents.summary_writer import (
            _extract_characters_from_settlement,
            _extract_key_events_from_settlement,
        )

        settlement = StateSettlement(
            character_updates=[
                CharacterUpdate(
                    character_id="char1",
                    field="location",
                    old_value="home",
                    new_value="forest",
                    source_quote="q",
                ),
            ],
            new_settings=[
                NewSetting(
                    setting_name="Ancient Temple",
                    description="A hidden temple",
                    source_quote="q",
                    setting_key="temple",
                ),
            ],
        )
        chars = _extract_characters_from_settlement(settlement)
        assert "char1" in chars

        events = _extract_key_events_from_settlement(settlement)
        assert any("char1" in e for e in events)
        assert any("Ancient Temple" in e for e in events)

    @pytest.mark.asyncio
    async def test_write_chapter_summary_mock_llm(self) -> None:
        from songyan.agents.summary_writer import write_chapter_summary

        settlement = StateSettlement(
            character_updates=[
                CharacterUpdate(
                    character_id="protagonist",
                    field="mood",
                    old_value="calm",
                    new_value="angry",
                    source_quote="q",
                ),
            ],
        )
        mock_db = AsyncMock()

        with patch(
            "songyan.agents.summary_writer.call_llm",
            new_callable=AsyncMock,
            return_value='{"plot_summary": "Test summary", "emotional_tone": "tense"}',
        ):
            with patch(
                "songyan.agents.summary_writer.parse_llm_response",
                return_value=MagicMock(
                    data={"plot_summary": "Test summary", "emotional_tone": "tense"}
                ),
            ):
                with patch(
                    "songyan.agents.summary_writer._save_summary",
                    new_callable=AsyncMock,
                ):
                    summary = await write_chapter_summary(
                        content="chapter text here",
                        settlement=settlement,
                        project_id="p1",
                        chapter_number=1,
                        db=mock_db,
                    )

        assert isinstance(summary, ChapterSummary)
        assert summary.chapter_number == 1
        assert "protagonist" in summary.characters_appeared
        assert summary.summary


# =============================================================================
# Node Tests with Mock
# =============================================================================


class TestGoalPlannerNode:
    @pytest.mark.asyncio
    async def test_error_when_project_not_found(self) -> None:
        from songyan.workflows._nodes import goal_planner_node

        with patch(
            "songyan.workflows._nodes.load_project",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await goal_planner_node(
                {"project_id": "missing", "chapter_number": 1}
            )
        assert result["status"] == "goal_planner"
        assert "not found" in result["error"]


class TestContextManagerNode:
    @pytest.mark.asyncio
    async def test_error_when_goal_not_found(self) -> None:
        from songyan.workflows._nodes import context_manager_node

        with patch(
            "songyan.workflows._nodes.load_chapter_goal",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await context_manager_node(
                {"chapter_goal_id": "missing"}
            )
        assert result["status"] == "context_manager"

    @pytest.mark.asyncio
    async def test_populates_context_package(self) -> None:
        """context_manager_node 应组装 ContextPackage 并存入 state."""
        from songyan.models import ChapterGoal, ContextPackage
        from songyan.workflows._nodes import context_manager_node

        goal = ChapterGoal(
            chapter_number=2,
            target_events=["测试事件"],
            emotional_arc="紧张",
            hooks=["悬念开场", "反转收尾"],
            obligations=["保持人设"],
            word_count_target=3000,
            chapter_type="opening",
        )
        ctx = ContextPackage(chapter_goal=goal)

        with patch(
            "songyan.workflows._nodes.load_chapter_goal",
            new_callable=AsyncMock,
            return_value=goal,
        ), patch(
            "songyan.workflows._nodes.load_creative_brief",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "songyan.workflows._nodes.assemble_context_package",
            new_callable=AsyncMock,
            return_value=ctx,
        ):
            result = await context_manager_node(
                {
                    "project_id": "proj-test",
                    "chapter_number": 2,
                    "chapter_goal_id": "goal-1",
                }
            )
        assert result["status"] == "writing"
        assert "context_package" in result
        assert isinstance(result["context_package"], ContextPackage)
        assert result["context_package"].chapter_goal.chapter_number == 2


class TestReviewMergerNode:
    @pytest.mark.asyncio
    async def test_error_when_audits_missing(self) -> None:
        from songyan.workflows._nodes import review_merger_node

        with patch(
            "songyan.workflows._nodes.load_version",
            new_callable=AsyncMock,
            return_value=MagicMock(version_id="v1"),
        ):
            with patch(
                "songyan.workflows._nodes.load_latest_audits",
                new_callable=AsyncMock,
                return_value=(None, None),
            ):
                result = await review_merger_node(
                    {"current_version_id": "v1"}
                )
        assert result["status"] == "review_merger"
        assert "Missing audit" in result["error"]


class TestSettlementExtractorNode:
    @pytest.mark.asyncio
    async def test_error_when_version_not_found(self) -> None:
        from songyan.workflows._nodes import settlement_extractor_node

        with patch(
            "songyan.workflows._nodes.load_version",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await settlement_extractor_node(
                {"current_version_id": "missing"}
            )
        assert result["status"] == "settlement_extractor"
