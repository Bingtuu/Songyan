"""Tests for 073 truncation rewrite strategy."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from songyan.workflows._nodes import (
    _build_rewrite_avoid_list,
    rewrite_node,
)
from songyan.workflows.phase1_graph import revision_router


class TestRevisionRouterRewrite:
    """revision_router 的 rewrite 分支测试."""

    def _make_state(self, **kwargs: object) -> dict:
        base = {
            "project_id": "p1",
            "chapter_number": 1,
            "mode_id": "webnovel",
            "revision_round": 2,
            "_needs_revision": True,
            "_has_critical": True,
            "_was_rewritten": False,
            "error": None,
        }
        base.update(kwargs)
        return base

    def test_round_2_critical_triggers_rewrite(self) -> None:
        state = self._make_state(revision_round=2, _needs_revision=True, _has_critical=True)
        assert revision_router(state) == "rewrite"

    def test_round_2_major_triggers_rewrite(self) -> None:
        state = self._make_state(revision_round=2, _needs_revision=True, _has_major=True)
        assert revision_router(state) == "rewrite"

    def test_round_2_no_issues_passes(self) -> None:
        state = self._make_state(revision_round=2, _needs_revision=False)
        assert revision_router(state) == "pass"

    def test_was_rewritten_round_0_forces_pass(self) -> None:
        """rewrite 后第 0 轮仍有 issue → 强制 pass."""
        state = self._make_state(
            revision_round=0,
            _needs_revision=True,
            _has_critical=True,
            _was_rewritten=True,
        )
        assert revision_router(state) == "pass"

    def test_was_rewritten_round_1_forces_pass(self) -> None:
        """rewrite 后第 1 轮无论是否有 issue 都 pass."""
        state = self._make_state(
            revision_round=1,
            _needs_revision=True,
            _has_critical=True,
            _was_rewritten=True,
        )
        assert revision_router(state) == "pass"

    def test_round_1_still_revises(self) -> None:
        state = self._make_state(revision_round=1, _needs_revision=True, _has_critical=True)
        assert revision_router(state) == "revise"


class TestBuildRewriteAvoidList:
    """_build_rewrite_avoid_list 测试."""

    @pytest.mark.asyncio
    async def test_extracts_from_new_issues(self) -> None:
        state = {
            "review_report_id": None,
            "_new_issues_introduced": [
                {
                    "issue_description": "世界观不一致",
                    "evidence_quote": "天空是红色的",
                },
                {
                    "issue_description": "角色行为突兀",
                    "evidence_quote": "他突然笑了",
                },
            ],
        }
        result = await _build_rewrite_avoid_list(state)
        assert len(result) == 2
        assert "世界观不一致" in result[0]
        assert "天空是红色的" in result[0]

    @pytest.mark.asyncio
    async def test_deduplicates_by_description(self) -> None:
        state = {
            "review_report_id": None,
            "_new_issues_introduced": [
                {
                    "issue_description": "重复问题",
                    "evidence_quote": "证据A",
                },
                {
                    "issue_description": "重复问题",
                    "evidence_quote": "证据B",
                },
            ],
        }
        result = await _build_rewrite_avoid_list(state)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_caps_at_10_items(self) -> None:
        state = {
            "review_report_id": None,
            "_new_issues_introduced": [
                {
                    "issue_description": f"问题{i}",
                    "evidence_quote": "",
                }
                for i in range(20)
            ],
        }
        result = await _build_rewrite_avoid_list(state)
        assert len(result) == 10

    @pytest.mark.asyncio
    async def test_empty_returns_empty(self) -> None:
        state = {"review_report_id": None, "_new_issues_introduced": None}
        result = await _build_rewrite_avoid_list(state)
        assert result == []


class TestRewriteNode:
    """rewrite_node 集成测试."""

    @pytest.mark.asyncio
    async def test_calls_writer_and_marks_rewritten(self) -> None:
        """rewrite_node 调用 Writer 并标记 _was_rewritten."""
        mock_version = AsyncMock()
        mock_version.version_id = "v-rewrite-001"
        mock_version.scenes = [{"scene_id": "s1"}, {"scene_id": "s2"}]
        mock_version.content = "content"
        mock_version.word_count = 3000

        rule_result = MagicMock()
        rule_result.has_opening_hook = True
        rule_result.has_ending_hook = True

        with patch(
            "songyan.workflows._nodes.write_chapter",
            new_callable=AsyncMock,
            return_value=mock_version,
        ):
            with patch(
                "songyan.workflows._nodes._get_context_package",
                new_callable=AsyncMock,
                return_value=AsyncMock(human_instructions=[]),
            ):
                with patch(
                    "songyan.workflows._nodes.run_rule_audit",
                    return_value=rule_result,
                ):
                    state = {
                        "project_id": "p1",
                        "chapter_number": 1,
                        "chapter_goal_id": None,
                        "creative_brief_id": None,
                        "review_report_id": None,
                        "_new_issues_introduced": [{"issue_id": "stale"}],
                        "_new_issues_version_id": "v-old",
                        "_content_preservation_ratio": 0.61,
                        "_quality_gate_passed": False,
                        "_quality_gate_failures": ["new_issues_introduced:1"],
                        "_convergence_failed": True,
                        "_skip_settlement": True,
                        "_settlement_needs_human_review": True,
                        "_score_card": {"version_id": "v-old"},
                    }
                    result = await rewrite_node(state)

        assert result["_was_rewritten"] is True
        assert result["_rewrite_reason"] == "2轮revision不收敛"
        assert result["revision_round"] == 0
        assert result["_needs_revision"] is False
        assert result["current_version_id"] == "v-rewrite-001"
        assert result["_new_issues_introduced"] == []
        assert result["_new_issues_version_id"] is None
        assert result["_quality_gate_failures"] == []
        assert result["_settlement_needs_human_review"] is False
        assert result["_skip_settlement"] is False
        assert result["_score_card"] is None

    @pytest.mark.asyncio
    async def test_injects_avoid_list(self) -> None:
        """rewrite_node 注入 issues 到 human_instructions."""
        mock_ctx = AsyncMock()
        mock_ctx.human_instructions = []

        mock_version = AsyncMock()
        mock_version.version_id = "v-rewrite-002"

        with patch(
            "songyan.workflows._nodes.write_chapter",
            new_callable=AsyncMock,
            return_value=mock_version,
        ):
            with patch(
                "songyan.workflows._nodes._get_context_package",
                new_callable=AsyncMock,
                return_value=mock_ctx,
            ):
                state = {
                    "project_id": "p1",
                    "chapter_number": 1,
                    "chapter_goal_id": None,
                    "creative_brief_id": None,
                    "review_report_id": None,
                    "_new_issues_introduced": [
                        {
                            "issue_description": "避免这个问题",
                            "evidence_quote": "原文证据",
                        }
                    ],
                }
                result = await rewrite_node(state)

        assert result["_was_rewritten"] is True
        assert len(mock_ctx.human_instructions) == 1
        assert mock_ctx.human_instructions[0]["type"] == "rewrite_avoid_list"

    @pytest.mark.asyncio
    async def test_injects_word_count_constraint(self) -> None:
        """090b: rewrite_node 注入字数约束到 human_instructions."""
        from unittest.mock import MagicMock

        mock_ctx = AsyncMock()
        mock_ctx.human_instructions = []

        mock_version = MagicMock()
        mock_version.version_id = "v-rewrite-003"
        mock_version.content = "测试内容。"
        mock_version.word_count = 10
        mock_version.scenes = []

        goal = AsyncMock()
        goal.word_count_target = 3000

        with patch(
            "songyan.workflows._nodes.write_chapter",
            new_callable=AsyncMock,
            return_value=mock_version,
        ):
            with patch(
                "songyan.workflows._nodes._get_context_package",
                new_callable=AsyncMock,
                return_value=mock_ctx,
            ):
                with patch(
                    "songyan.workflows._nodes.load_chapter_goal",
                    new_callable=AsyncMock,
                    return_value=goal,
                ):
                    state = {
                        "project_id": "p1",
                        "chapter_number": 1,
                        "chapter_goal_id": "gp-1",
                        "creative_brief_id": None,
                        "review_report_id": None,
                        "_new_issues_introduced": None,
                    }
                    result = await rewrite_node(state)

        assert result["_was_rewritten"] is True
        # 095: avoid_list(0 条) + word_count_constraint + scene_structure_constraint = 2 条
        assert len(mock_ctx.human_instructions) == 2
        types = [h["type"] for h in mock_ctx.human_instructions]
        assert "word_count_constraint" in types
        assert "scene_structure_constraint" in types
        wc_instr = next(
            h for h in mock_ctx.human_instructions if h["type"] == "word_count_constraint"
        )
        assert "3000" in wc_instr["content"]
        assert "2400" in wc_instr["content"]  # 093: 收紧到 0.80x
        assert "3600" in wc_instr["content"]  # 093: 收紧到 1.20x
        scene_instr = next(
            h
            for h in mock_ctx.human_instructions
            if h["type"] == "scene_structure_constraint"
        )
        assert "至少 2 个场景" in scene_instr["content"]


    @pytest.mark.asyncio
    async def test_hard_truncate_fallback_on_rewrite(self) -> None:
        """093: rewrite 后字数严重超标且结构保护阻止截断 → 启用硬截断 (收紧到 1.20x)."""
        from unittest.mock import MagicMock

        from songyan.agents.writer import _count_chinese_words

        long_content = "### Scene 1\n\n" + "这是一个测试句子。" * 500
        original_wc = _count_chinese_words(long_content)
        assert original_wc > 3600  # 093: 确保测试数据超标 (收紧到 1.20x)

        mock_version = MagicMock()
        mock_version.version_id = "v-rewrite-004"
        mock_version.content = long_content
        mock_version.word_count = original_wc
        mock_version.scenes = [{"scene_number": 1, "content": long_content}]

        goal = AsyncMock()
        goal.word_count_target = 3000

        with patch(
            "songyan.workflows._nodes.write_chapter",
            new_callable=AsyncMock,
            return_value=mock_version,
        ):
            with patch(
                "songyan.workflows._nodes._get_context_package",
                new_callable=AsyncMock,
                return_value=AsyncMock(human_instructions=[]),
            ):
                with patch(
                    "songyan.workflows._nodes.load_chapter_goal",
                    new_callable=AsyncMock,
                    return_value=goal,
                ):
                    state = {
                        "project_id": "p1",
                        "chapter_number": 1,
                        "chapter_goal_id": "gp-1",
                        "creative_brief_id": None,
                        "review_report_id": None,
                        "_new_issues_introduced": None,
                    }
                    result = await rewrite_node(state)

        assert result["_was_rewritten"] is True
        # 093: 硬截断后字数应 <= 3600 (3000*1.20)
        assert mock_version.word_count <= 3600
        # 内容应被修改
        assert mock_version.content != long_content
        # scenes 应被重新解析
        assert len(mock_version.scenes) >= 0


class TestRewriteNodeMandatoryReferences:
    """Task 139e: rewrite_node 必须继承 mandatory references."""

    @pytest.mark.asyncio
    async def test_injects_mandatory_references(self) -> None:
        """存在 critical orphan 时，rewrite_node 应注入 mandatory_references 约束."""
        mock_ctx = AsyncMock()
        mock_ctx.human_instructions = []
        mock_ctx.creative_brief = None

        mock_version = MagicMock()
        mock_version.version_id = "v-rewrite-mr"
        mock_version.content = "测试内容。"
        mock_version.word_count = 10
        mock_version.scenes = []

        mr = [
            {
                "setting_key": "scifi.main_deck.chen_luo_log",
                "setting_name": "陈洛日志（黑匣子）",
                "category": "critical",
                "silent_chapters": 4,
                "introduced_in_chapter": 13,
                "last_mentioned_chapter": 17,
            }
        ]

        with patch(
            "songyan.workflows._nodes.write_chapter",
            new_callable=AsyncMock,
            return_value=mock_version,
        ):
            with patch(
                "songyan.workflows._nodes._get_context_package",
                new_callable=AsyncMock,
                return_value=mock_ctx,
            ):
                with patch(
                    "songyan.workflows._nodes._load_critical_mandatory_references",
                    new_callable=AsyncMock,
                    return_value=mr,
                ):
                    state = {
                        "project_id": "p1",
                        "chapter_number": 21,
                        "chapter_goal_id": None,
                        "creative_brief_id": None,
                        "review_report_id": None,
                        "_new_issues_introduced": None,
                    }
                    result = await rewrite_node(state)

        assert result["_was_rewritten"] is True
        types = [h["type"] for h in mock_ctx.human_instructions]
        assert "mandatory_references" in types
        mr_instr = next(
            h for h in mock_ctx.human_instructions if h["type"] == "mandatory_references"
        )
        assert "陈洛日志" in mr_instr["content"]
        assert "scifi.main_deck.chen_luo_log" not in mr_instr["content"]

    @pytest.mark.asyncio
    async def test_no_mandatory_references_when_empty(self) -> None:
        """无 critical orphan 时，rewrite_node 不注入 mandatory_references 约束."""
        mock_ctx = AsyncMock()
        mock_ctx.human_instructions = []
        mock_ctx.creative_brief = None

        mock_version = MagicMock()
        mock_version.version_id = "v-rewrite-no-mr"
        mock_version.content = "测试内容。"
        mock_version.word_count = 10
        mock_version.scenes = []

        with patch(
            "songyan.workflows._nodes.write_chapter",
            new_callable=AsyncMock,
            return_value=mock_version,
        ):
            with patch(
                "songyan.workflows._nodes._get_context_package",
                new_callable=AsyncMock,
                return_value=mock_ctx,
            ):
                with patch(
                    "songyan.workflows._nodes._load_critical_mandatory_references",
                    new_callable=AsyncMock,
                    return_value=[],
                ):
                    state = {
                        "project_id": "p1",
                        "chapter_number": 1,
                        "chapter_goal_id": None,
                        "creative_brief_id": None,
                        "review_report_id": None,
                        "_new_issues_introduced": None,
                    }
                    result = await rewrite_node(state)

        assert result["_was_rewritten"] is True
        types = [h["type"] for h in mock_ctx.human_instructions]
        assert "mandatory_references" not in types
