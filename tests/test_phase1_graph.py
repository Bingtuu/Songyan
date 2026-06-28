"""Tests for Phase 1 LangGraph workflow, ReviewMerger, and SummaryWriter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from songyan.models import (
    AiTellMatch,
    ChapterSummary,
    CharacterUpdate,
    FatigueWordMatch,
    LiteraryAuditResult,
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
    quality_gate_router,
    revision_router,
    rewrite_router,
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

    def test_new_issues_introduced_at_max_round_triggers_rewrite(self) -> None:
        """AG-04: revision 引入新问题时，达到最大轮次后触发 rewrite."""
        state = _base_revision_state(
            revision_round=2,
            _needs_revision=True,
            _new_issues_introduced=[{"issue_id": "new1", "severity": "major"}],
        )
        assert revision_router(state) == "rewrite"


class TestQualityGateRouter:
    def test_human_review_required_blocks_graph(self) -> None:
        state = _base_revision_state(status="human_review_required")
        assert quality_gate_router(state) == "blocked"


class TestRewriteRouter:
    def test_struct_failure_recovery_goes_to_human_confirm(self) -> None:
        """Task 114b2: rewrite 结构失败回滚 best 后不得继续审查失败稿."""
        state = _base_revision_state(status="human_confirm")
        assert rewrite_router(state) == "human_confirm"

    def test_struct_ok_rewrite_goes_to_audit(self) -> None:
        state = _base_revision_state(status="rule_auditing")
        assert rewrite_router(state) == "audit"

    def test_error_falls_back_to_audit_path(self) -> None:
        state = _base_revision_state(status="human_confirm", error="boom")
        assert rewrite_router(state) == "audit"


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
                    summary_id, summary = await write_chapter_summary(
                        content="chapter text here",
                        settlement=settlement,
                        project_id="p1",
                        chapter_number=1,
                        db=mock_db,
                    )

        assert summary_id.startswith("sum-p1-1-")
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
    async def test_populates_context_metrics_without_package(self) -> None:
        """context_manager_node 应只把轻量指标存入 state."""
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

        snapshot_repo = AsyncMock()
        snapshot_repo.create = AsyncMock()

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
        ), patch(
            "songyan.workflows._nodes.ContextSnapshotRepository",
            return_value=snapshot_repo,
        ):
            result = await context_manager_node(
                {
                    "project_id": "proj-test",
                    "chapter_number": 2,
                    "chapter_goal_id": "goal-1",
                    "human_instructions": [{"action": "revise", "content": "保留黑匣子"}],
                }
            )
        assert result["status"] == "writing"
        assert "context_package" not in result
        assert result["context_snapshot_id"].startswith("ctx-")
        assert result["_context_metrics"]["budget_used"] == ctx.budget_used
        assert result["_context_metrics"]["character_states_loaded"] == 0
        snapshot = snapshot_repo.create.await_args.args[0]
        assert snapshot.payload["human_instructions"][0]["content"] == "保留黑匣子"

    @pytest.mark.asyncio
    async def test_get_context_package_loads_snapshot(self) -> None:
        """Writer/Auditor 通过 context_snapshot_id 复用同一份上下文."""
        from songyan.models import ChapterGoal, ContextPackage, ContextSnapshot
        from songyan.workflows._nodes import _get_context_package

        goal = ChapterGoal(chapter_number=2, word_count_target=3000)
        ctx = ContextPackage(
            chapter_goal=goal,
            human_instructions=[{"action": "revise", "content": "保留黑匣子"}],
        )
        snapshot = ContextSnapshot(
            snapshot_id="ctx-1",
            project_id="proj-test",
            chapter_number=2,
            chapter_goal_id="goal-1",
            payload=ctx.model_dump(mode="json"),
        )
        snapshot_repo = AsyncMock()
        snapshot_repo.get = AsyncMock(return_value=snapshot)

        with patch(
            "songyan.workflows._nodes.ContextSnapshotRepository",
            return_value=snapshot_repo,
        ):
            loaded = await _get_context_package({"context_snapshot_id": "ctx-1"})

        assert loaded.human_instructions[0]["content"] == "保留黑匣子"
        snapshot_repo.get.assert_awaited_once_with("ctx-1")

    @pytest.mark.asyncio
    async def test_auditors_reuse_context_snapshot(self) -> None:
        """LLMAuditor 与 LiteraryAuditor 使用同一个 context_snapshot_id."""
        from songyan.models import ChapterGoal, ContextPackage, ContextSnapshot
        from songyan.workflows._nodes import literary_auditor_node, llm_auditor_node

        goal = ChapterGoal(chapter_number=2, word_count_target=3000)
        ctx = ContextPackage(
            chapter_goal=goal,
            human_instructions=[{"action": "inject", "content": "保留黑匣子"}],
        )
        snapshot = ContextSnapshot(
            snapshot_id="ctx-shared",
            project_id="proj-test",
            chapter_number=2,
            chapter_goal_id="goal-1",
            payload=ctx.model_dump(mode="json"),
        )
        snapshot_repo = AsyncMock()
        snapshot_repo.get = AsyncMock(return_value=snapshot)
        version = MagicMock(version_id="v1", content="正文")

        with (
            patch(
                "songyan.workflows._nodes.load_version",
                new_callable=AsyncMock,
                return_value=version,
            ),
            patch(
                "songyan.workflows._nodes.ContextSnapshotRepository",
                return_value=snapshot_repo,
            ),
            patch(
                "songyan.workflows._nodes.run_llm_audit",
                new_callable=AsyncMock,
                return_value=LLMAuditResult(),
            ) as mock_llm,
            patch(
                "songyan.workflows._nodes.run_literary_audit",
                new_callable=AsyncMock,
                return_value=LiteraryAuditResult(),
            ) as mock_literary,
            patch("songyan.workflows._nodes.save_llm_audit", new_callable=AsyncMock),
            patch(
                "songyan.workflows._nodes.save_literary_audit",
                new_callable=AsyncMock,
            ),
        ):
            llm_result = await llm_auditor_node(
                {"current_version_id": "v1", "context_snapshot_id": "ctx-shared"}
            )
            literary_result = await literary_auditor_node(
                {"current_version_id": "v1", "context_snapshot_id": "ctx-shared"}
            )

        assert llm_result["status"] == "review_merging"
        assert literary_result["status"] == "revision_routing"
        assert snapshot_repo.get.await_count == 2
        llm_ctx = mock_llm.await_args.kwargs["context_package"]
        literary_ctx = mock_literary.await_args.kwargs["context_package"]
        assert llm_ctx.human_instructions[0]["content"] == "保留黑匣子"
        assert literary_ctx.human_instructions[0]["content"] == "保留黑匣子"


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

    @pytest.mark.asyncio
    async def test_uses_context_metrics_budget_without_context_package(self) -> None:
        """review_merger_node 应从 _context_metrics 读取 budget_used."""
        from songyan.workflows._nodes import review_merger_node

        version = MagicMock(version_id="v-budget", content="正文")
        rule = RuleAuditResult(
            ai_tell_count=0,
            fatigue_word_count=0,
            has_opening_hook=True,
            has_ending_hook=True,
            paragraph_rhythm_score=8.0,
            word_count=3000,
            word_count_target=3000,
        )
        llm = LLMAuditResult(issues=[])
        merged = MagicMock(has_critical=False, has_major=False, issues=[])
        repo = AsyncMock()
        repo.update_score_card = AsyncMock()

        with (
            patch(
                "songyan.workflows._nodes.load_version",
                new_callable=AsyncMock,
                return_value=version,
            ),
            patch(
                "songyan.workflows._nodes.load_latest_audits",
                new_callable=AsyncMock,
                return_value=(rule, llm),
            ),
            patch(
                "songyan.workflows._nodes.merge_reviews",
                new_callable=AsyncMock,
                return_value=merged,
            ),
            patch(
                "songyan.workflows._nodes._load_chapter_repair_state",
                new_callable=AsyncMock,
                return_value=(0, False),
            ),
            patch("songyan.workflows._nodes.ChapterVersionRepository", return_value=repo),
        ):
            result = await review_merger_node(
                {
                    "project_id": "p1",
                    "chapter_number": 1,
                    "current_version_id": "v-budget",
                    "_context_metrics": {"budget_used": 1.1},
                }
            )

        assert result["_score_card"]["flags"]["budget_ok"] is False

    @pytest.mark.asyncio
    async def test_context_metrics_budget_passes_under_limit(self) -> None:
        """_context_metrics.budget_used=0.8 时预算维度正常通过."""
        from songyan.workflows._nodes import review_merger_node

        version = MagicMock(version_id="v-budget-ok", content="正文")
        rule = RuleAuditResult(
            ai_tell_count=0,
            fatigue_word_count=0,
            has_opening_hook=True,
            has_ending_hook=True,
            paragraph_rhythm_score=8.0,
            word_count=3000,
            word_count_target=3000,
        )
        llm = LLMAuditResult(issues=[])
        merged = MagicMock(has_critical=False, has_major=False, issues=[])
        repo = AsyncMock()
        repo.update_score_card = AsyncMock()

        with (
            patch(
                "songyan.workflows._nodes.load_version",
                new_callable=AsyncMock,
                return_value=version,
            ),
            patch(
                "songyan.workflows._nodes.load_latest_audits",
                new_callable=AsyncMock,
                return_value=(rule, llm),
            ),
            patch(
                "songyan.workflows._nodes.merge_reviews",
                new_callable=AsyncMock,
                return_value=merged,
            ),
            patch(
                "songyan.workflows._nodes._load_chapter_repair_state",
                new_callable=AsyncMock,
                return_value=(0, False),
            ),
            patch("songyan.workflows._nodes.ChapterVersionRepository", return_value=repo),
        ):
            result = await review_merger_node(
                {
                    "project_id": "p1",
                    "chapter_number": 1,
                    "current_version_id": "v-budget-ok",
                    "_context_metrics": {"budget_used": 0.8},
                }
            )

        assert result["_score_card"]["flags"]["budget_ok"] is True

    @pytest.mark.asyncio
    async def test_context_metrics_budget_passes_at_task112_hard_ceiling(self) -> None:
        """Task 112: budget_used <= 1.0 不应触发 QG budget 阻断."""
        from songyan.workflows._nodes import review_merger_node

        version = MagicMock(version_id="v-budget-ceiling", content="正文")
        rule = RuleAuditResult(
            ai_tell_count=0,
            fatigue_word_count=0,
            has_opening_hook=True,
            has_ending_hook=True,
            paragraph_rhythm_score=8.0,
            word_count=3000,
            word_count_target=3000,
        )
        llm = LLMAuditResult(issues=[])
        merged = MagicMock(has_critical=False, has_major=False, issues=[])
        repo = AsyncMock()
        repo.update_score_card = AsyncMock()

        with (
            patch(
                "songyan.workflows._nodes.load_version",
                new_callable=AsyncMock,
                return_value=version,
            ),
            patch(
                "songyan.workflows._nodes.load_latest_audits",
                new_callable=AsyncMock,
                return_value=(rule, llm),
            ),
            patch(
                "songyan.workflows._nodes.merge_reviews",
                new_callable=AsyncMock,
                return_value=merged,
            ),
            patch(
                "songyan.workflows._nodes._load_chapter_repair_state",
                new_callable=AsyncMock,
                return_value=(0, False),
            ),
            patch("songyan.workflows._nodes.ChapterVersionRepository", return_value=repo),
        ):
            result = await review_merger_node(
                {
                    "project_id": "p1",
                    "chapter_number": 1,
                    "current_version_id": "v-budget-ceiling",
                    "_context_metrics": {"budget_used": 0.959},
                }
            )

        assert result["_score_card"]["flags"]["budget_ok"] is True


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

    @pytest.mark.asyncio
    async def test_validation_failed_does_not_accept_or_apply(self) -> None:
        from songyan.workflows._nodes import settlement_extractor_node

        version = MagicMock(version_id="v-invalid", content="正文", version_type="draft")
        settlement = StateSettlement(
            validation_status="needs_human_review",
            validation_errors=["bad quote"],
        )

        with (
            patch(
                "songyan.workflows._nodes.load_version",
                new_callable=AsyncMock,
                return_value=version,
            ),
            patch(
                "songyan.workflows._nodes.load_project",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "songyan.workflows._nodes.load_chapter_goal",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "songyan.workflows._nodes.extract_settlement",
                new_callable=AsyncMock,
                return_value=settlement,
            ),
            patch(
                "songyan.workflows._nodes.accept_with_settlement_boundary",
                new_callable=AsyncMock,
            ) as mock_accept,
            patch(
                "songyan.workflows._nodes.write_chapter_summary",
                new_callable=AsyncMock,
            ) as mock_summary,
        ):
            result = await settlement_extractor_node(
                {
                    "project_id": "p1",
                    "chapter_number": 3,
                    "current_version_id": "v-invalid",
                    "chapter_goal_id": "goal-1",
                }
            )

        assert result["status"] == "settlement_review"
        assert result["_settlement_needs_human_review"] is True
        assert result["_settlement_version_id"] == "v-invalid"
        assert result["_settlement_validation_status"] == "needs_human_review"
        assert result["_settlement_validation_errors"] == ["bad quote"]
        assert result["settlement_id"] is None
        assert result["summary_id"] is None
        mock_accept.assert_not_called()
        mock_summary.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_real_summary_id_after_valid_settlement(self) -> None:
        from songyan.workflows._nodes import settlement_extractor_node

        version = MagicMock(version_id="v-valid", content="正文", version_type="draft")
        project = MagicMock(mode_id="webnovel", genre_id="scifi")
        settlement = StateSettlement()
        summary = ChapterSummary(
            chapter_number=3,
            summary="摘要",
            key_events=[],
            characters_appeared=[],
            emotional_tone="中性",
            impact_score=0.0,
        )

        with (
            patch(
                "songyan.workflows._nodes.load_version",
                new_callable=AsyncMock,
                return_value=version,
            ),
            patch(
                "songyan.workflows._nodes.load_project",
                new_callable=AsyncMock,
                return_value=project,
            ),
            patch(
                "songyan.workflows._nodes.load_chapter_goal",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch("songyan.workflows._nodes.load_genre_profile", return_value=None),
            patch(
                "songyan.workflows._nodes.extract_settlement",
                new_callable=AsyncMock,
                return_value=settlement,
            ),
            patch(
                "songyan.workflows._nodes.accept_with_settlement_boundary",
                new_callable=AsyncMock,
            ) as mock_accept,
            patch(
                "songyan.workflows._nodes.write_chapter_summary",
                new_callable=AsyncMock,
                return_value=("sum-real", summary),
            ),
            patch(
                "songyan.workflows._nodes._run_lifecycle_cleanup",
                new_callable=AsyncMock,
            ),
            patch(
                "songyan.workflows._nodes.load_creative_mode_profile",
                return_value=MagicMock(rag_config={}),
            ),
            patch("songyan.workflows._nodes._index_accepted_chapter", new_callable=AsyncMock),
            patch("songyan.workflows._nodes.trigger_layered_summaries", new_callable=AsyncMock),
        ):
            result = await settlement_extractor_node(
                {
                    "project_id": "p1",
                    "chapter_number": 3,
                    "current_version_id": "v-valid",
                    "chapter_goal_id": "goal-1",
                }
            )

        assert result["status"] == "done"
        assert result["_settlement_needs_human_review"] is False
        assert result["settlement_id"] is not None
        assert result["summary_id"] == "sum-real"
        mock_accept.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_summary_failure_writes_fallback_summary(self) -> None:
        from songyan.exceptions import LLMError
        from songyan.workflows._nodes import settlement_extractor_node

        version = MagicMock(version_id="v-valid", content="A" * 500, version_type="draft")
        project = MagicMock(mode_id="webnovel", genre_id="scifi")
        settlement = StateSettlement()
        summary_repo = AsyncMock()
        summary_repo.create = AsyncMock()

        with (
            patch(
                "songyan.workflows._nodes.load_version",
                new_callable=AsyncMock,
                return_value=version,
            ),
            patch(
                "songyan.workflows._nodes.load_project",
                new_callable=AsyncMock,
                return_value=project,
            ),
            patch(
                "songyan.workflows._nodes.load_chapter_goal",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch("songyan.workflows._nodes.load_genre_profile", return_value=None),
            patch(
                "songyan.workflows._nodes.extract_settlement",
                new_callable=AsyncMock,
                return_value=settlement,
            ),
            patch(
                "songyan.workflows._nodes.accept_with_settlement_boundary",
                new_callable=AsyncMock,
            ),
            patch(
                "songyan.workflows._nodes.write_chapter_summary",
                new_callable=AsyncMock,
                side_effect=LLMError("summary failed"),
            ),
            patch("songyan.workflows._nodes.SummaryRepository", return_value=summary_repo),
            patch(
                "songyan.workflows._nodes._run_lifecycle_cleanup",
                new_callable=AsyncMock,
            ),
            patch(
                "songyan.workflows._nodes.load_creative_mode_profile",
                return_value=MagicMock(rag_config={}),
            ),
            patch("songyan.workflows._nodes._index_accepted_chapter", new_callable=AsyncMock),
            patch("songyan.workflows._nodes.trigger_layered_summaries", new_callable=AsyncMock),
        ):
            result = await settlement_extractor_node(
                {
                    "project_id": "p1",
                    "chapter_number": 3,
                    "current_version_id": "v-valid",
                    "chapter_goal_id": "goal-1",
                }
            )

        assert result["status"] == "done"
        assert result["_settlement_needs_human_review"] is False
        assert result["summary_id"] is not None
        summary_repo.create.assert_awaited_once()
        summary_obj, project_id, summary_id = summary_repo.create.await_args.args
        assert project_id == "p1"
        assert summary_id == result["summary_id"]
        assert summary_obj.summary == "A" * 300 + "..."

    @pytest.mark.asyncio
    async def test_summary_and_fallback_failure_returns_review(self) -> None:
        from songyan.exceptions import LLMResponseParseError
        from songyan.workflows._nodes import settlement_extractor_node

        version = MagicMock(version_id="v-valid", content="正文", version_type="draft")
        project = MagicMock(mode_id="webnovel", genre_id="scifi")
        settlement = StateSettlement()
        summary_repo = AsyncMock()
        summary_repo.create = AsyncMock(side_effect=RuntimeError("db down"))

        with (
            patch(
                "songyan.workflows._nodes.load_version",
                new_callable=AsyncMock,
                return_value=version,
            ),
            patch(
                "songyan.workflows._nodes.load_project",
                new_callable=AsyncMock,
                return_value=project,
            ),
            patch(
                "songyan.workflows._nodes.load_chapter_goal",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch("songyan.workflows._nodes.load_genre_profile", return_value=None),
            patch(
                "songyan.workflows._nodes.extract_settlement",
                new_callable=AsyncMock,
                return_value=settlement,
            ),
            patch(
                "songyan.workflows._nodes.accept_with_settlement_boundary",
                new_callable=AsyncMock,
            ),
            patch(
                "songyan.workflows._nodes.write_chapter_summary",
                new_callable=AsyncMock,
                side_effect=LLMResponseParseError("bad json"),
            ),
            patch("songyan.workflows._nodes.SummaryRepository", return_value=summary_repo),
            patch(
                "songyan.workflows._nodes._run_lifecycle_cleanup",
                new_callable=AsyncMock,
            ),
            patch(
                "songyan.workflows._nodes.load_creative_mode_profile",
                return_value=MagicMock(rag_config={}),
            ),
            patch("songyan.workflows._nodes._index_accepted_chapter", new_callable=AsyncMock),
            patch("songyan.workflows._nodes.trigger_layered_summaries", new_callable=AsyncMock),
        ):
            result = await settlement_extractor_node(
                {
                    "project_id": "p1",
                    "chapter_number": 3,
                    "current_version_id": "v-valid",
                    "chapter_goal_id": "goal-1",
                }
            )

        assert result["status"] == "settlement_review"
        assert result["_settlement_needs_human_review"] is True
        assert result["summary_id"] is None
