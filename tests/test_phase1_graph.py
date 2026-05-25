"""Tests for Phase 1 LangGraph workflow, ReviewMerger, and SummaryWriter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from songyan.models import (
    ChapterSummary,
    CharacterUpdate,
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
from songyan.workflows.review_merger import _compute_overall_score, _merge_summary, merge_reviews

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

        report = await merge_reviews("v1", rule, llm, mock_db)

        assert isinstance(report, MergedReviewReport)
        assert report.chapter_version_id == "v1"
        assert report.ai_tell_count == 1
        assert report.fatigue_word_count == 0
        assert report.has_opening_hook is True
        assert len(report.issues) == 1
        assert report.issues[0].severity == "major"
        mock_db.create.assert_awaited_once()


# =============================================================================
# Router Tests
# =============================================================================


class TestRevisionRouter:
    def test_critical_and_under_round_limit(self) -> None:
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
            "_needs_revision": True,
            "_has_critical": True,
            "_has_major": False,
        }
        assert revision_router(state) == "revise"

    def test_major_and_under_round_limit(self) -> None:
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
            "revision_round": 1,
            "status": "revision_routing",
            "human_decision": None,
            "error": None,
            "_needs_revision": True,
            "_has_critical": False,
            "_has_major": True,
        }
        assert revision_router(state) == "revise"

    def test_over_round_limit(self) -> None:
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
            "revision_round": 2,
            "status": "revision_routing",
            "human_decision": None,
            "error": None,
            "_needs_revision": True,
            "_has_critical": True,
            "_has_major": False,
        }
        assert revision_router(state) == "pass"

    def test_no_issues(self) -> None:
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
            "_needs_revision": False,
            "_has_critical": False,
            "_has_major": False,
        }
        assert revision_router(state) == "pass"

    def test_error_defaults_to_pass(self) -> None:
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
            "status": "error",
            "human_decision": None,
            "error": "something wrong",
            "_needs_revision": True,
            "_has_critical": True,
            "_has_major": False,
        }
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
        assert human_confirm_router(state) == "edit"

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
    def test_graph_compiles(self) -> None:
        graph = build_phase1_graph()
        assert graph is not None

    def test_all_nodes_registered(self) -> None:
        graph = build_phase1_graph()
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
        assert result["status"] == "error"
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
        assert result["status"] == "error"


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
        assert result["status"] == "error"
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
        assert result["status"] == "error"
