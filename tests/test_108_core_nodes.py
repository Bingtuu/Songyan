"""Tests for Task 108 core node modifications."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from songyan.models import ChapterVersion
from songyan.workflows._nodes import (
    _load_chapter_repair_state,
    review_merger_node,
    rewrite_node,
    settlement_extractor_node,
)


class TestSettlementExtractorNodeSkipSettlement:
    """settlement_extractor_node _skip_settlement=True 路径测试."""

    @pytest.mark.asyncio
    async def test_skips_llm_extraction_and_applies_fallback_summary(self) -> None:
        """skip_settlement=True 时跳过 settlement 提取，生成 fallback summary."""
        mock_version = MagicMock()
        mock_version.version_id = "v-skip-001"
        mock_version.content = "A" * 500
        mock_version.version_type = "accepted"
        mock_version.word_count = 100

        mock_project = MagicMock()
        mock_project.genre_id = "scifi"
        mock_project.mode_id = "webnovel"

        mock_summary_repo = AsyncMock()
        mock_summary_repo.create = AsyncMock()

        with patch(
            "songyan.workflows._nodes.load_version",
            new_callable=AsyncMock,
            return_value=mock_version,
        ):
            with patch(
                "songyan.workflows._nodes.load_project",
                new_callable=AsyncMock,
                return_value=mock_project,
            ):
                with patch(
                    "songyan.workflows._nodes.load_genre_profile",
                    return_value=None,
                ):
                    with patch(
                        "songyan.workflows._nodes.load_chapter_goal",
                        new_callable=AsyncMock,
                        return_value=None,
                    ):
                        with patch(
                            "songyan.workflows._nodes.extract_settlement",
                            new_callable=AsyncMock,
                        ) as mock_extract:
                            with patch(
                                "songyan.workflows._nodes.apply_settlement",
                                new_callable=AsyncMock,
                            ) as mock_apply:
                                with patch(
                                    "songyan.workflows._nodes.write_chapter_summary",
                                    new_callable=AsyncMock,
                                ) as mock_write_summary:
                                    with patch(
                                        "songyan.workflows._nodes._run_lifecycle_cleanup",
                                        new_callable=AsyncMock,
                                    ) as mock_lifecycle:
                                        with patch(
                                            "songyan.workflows._nodes._index_accepted_chapter",
                                            new_callable=AsyncMock,
                                        ):
                                            with patch(
                                            "songyan.agents.setting_evaporator.SettingEvaporator",
                                        ) as mock_evap_cls:
                                                mock_evap = AsyncMock()
                                                mock_evap.run = AsyncMock(return_value=[])
                                                mock_evap.merge_similar_settings = AsyncMock()
                                                mock_evap_cls.return_value = mock_evap
                                                with patch(
                                                    "songyan.workflows._nodes.trigger_layered_summaries",
                                                    new_callable=AsyncMock,
                                                ):
                                                    with patch(
                                                        "songyan.workflows._nodes.SummaryRepository",
                                                        return_value=mock_summary_repo,
                                                    ):
                                                        state = {
                                                            "project_id": "p1",
                                                            "chapter_number": 1,
                                                            "current_version_id": "v-skip-001",
                                                            "chapter_goal_id": None,
                                                            "_skip_settlement": True,
                                                        }
                                                        result = await settlement_extractor_node(
                                                            state
                                                        )

        mock_extract.assert_not_awaited()
        mock_apply.assert_not_awaited()
        mock_write_summary.assert_not_awaited()
        mock_lifecycle.assert_awaited_once()

        assert result["settlement_id"] is None
        assert result["summary_id"] is not None
        assert result["status"] == "done"
        assert result["_settlement_needs_human_review"] is False

        mock_summary_repo.create.assert_awaited_once()
        call_args = mock_summary_repo.create.await_args
        summary_obj, proj_id, summary_id = call_args[0]
        assert proj_id == "p1"
        assert summary_obj.chapter_number == 1
        assert summary_obj.summary == "A" * 300 + "..."
        assert summary_obj.impact_score == 0.0


class TestRewriteNodeSuccessPath:
    """rewrite_node success path 返回值测试."""

    @pytest.mark.asyncio
    async def test_returns_best_version_id_and_best_score_card(self) -> None:
        mock_version = MagicMock()
        mock_version.version_id = "v-rewrite-best"
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
                        "_new_issues_introduced": None,
                    }
                    result = await rewrite_node(state)

        assert result["_best_version_id"] == "v-rewrite-best"
        assert result["_best_score_card"] is None


class TestReviewMergerNodeLiteraryNeedsRevision:
    """review_merger_node 合并 literary _needs_revision 测试."""

    @pytest.mark.asyncio
    async def test_literary_needs_revision_overrides_score_card(self) -> None:
        """score_card flags 说不需要 revision，但 literary 说需要，则仍需 revision."""
        mock_version = MagicMock()
        mock_version.version_id = "v1"
        mock_version.content = "正文"

        mock_rule = MagicMock()
        mock_rule.has_opening_hook = True
        mock_rule.has_ending_hook = True
        mock_llm = MagicMock()
        mock_llm.issues = []

        mock_score_card = MagicMock()
        mock_score_card.flags.needs_revision = False
        mock_score_card.flags.coherence_critical = False
        mock_score_card.flags.coherence_major = False
        mock_score_card.overall_score = 0.8
        mock_score_card.model_dump.return_value = {"overall_score": 0.8}

        for dim_name in ("length", "budget", "coherence", "momentum", "readability"):
            dim_mock = MagicMock()
            dim_mock.score = 0.8
            setattr(mock_score_card, dim_name, dim_mock)

        with patch(
            "songyan.workflows._nodes.load_version",
            new_callable=AsyncMock,
            return_value=mock_version,
        ):
            with patch(
                "songyan.workflows._nodes.load_latest_audits",
                new_callable=AsyncMock,
                return_value=(mock_rule, mock_llm),
            ):
                with patch(
                    "songyan.workflows._nodes.merge_reviews",
                    new_callable=AsyncMock,
                ) as mock_merge:
                    merged_mock = MagicMock()
                    merged_mock.has_critical = False
                    merged_mock.has_major = False
                    merged_mock.issues = []
                    mock_merge.return_value = merged_mock

                    with patch(
                        "songyan.workflows._nodes.ScoreAggregator.aggregate",
                        return_value=mock_score_card,
                    ):
                        with patch(
                            "songyan.workflows._nodes.ChapterVersionRepository",
                        ) as mock_repo_cls:
                            mock_repo = AsyncMock()
                            mock_repo.update_score_card = AsyncMock()
                            mock_repo_cls.return_value = mock_repo
                            with patch(
                                "songyan.workflows._nodes._load_chapter_repair_state",
                                new_callable=AsyncMock,
                                return_value=(0, False),
                            ):
                                state = {
                                    "project_id": "p1",
                                    "chapter_number": 1,
                                    "current_version_id": "v1",
                                    "revision_round": 0,
                                    "_needs_revision": True,  # literary says needs revision
                                    "_total_revision_count": 0,
                                    "_was_rewritten": False,
                                }
                                result = await review_merger_node(state)

        assert result["_needs_revision"] is True
        assert result["_has_critical"] is False
        assert result["_has_major"] is False


class TestLoadChapterRepairStateExcludesAbandoned:
    """_load_chapter_repair_state 排除废弃 revision 测试."""

    @pytest.mark.asyncio
    async def test_excludes_abandoned_revisions(self) -> None:
        v1 = ChapterVersion(
            version_id="v1",
            project_id="p1",
            chapter_number=1,
            version_number=1,
            version_type="revision",
            is_abandoned=False,
            content="c1",
        )
        v2 = ChapterVersion(
            version_id="v2",
            project_id="p1",
            chapter_number=1,
            version_number=2,
            version_type="revision",
            is_abandoned=True,
            content="c2",
        )
        v3 = ChapterVersion(
            version_id="v3",
            project_id="p1",
            chapter_number=1,
            version_number=1,
            version_type="draft",
            is_abandoned=False,
            content="c3",
        )

        mock_repo = AsyncMock()
        mock_repo.list_by_chapter = AsyncMock(return_value=[v1, v2, v3])

        with patch(
            "songyan.workflows._nodes.ChapterVersionRepository",
            return_value=mock_repo,
        ):
            revision_count, was_rewritten = await _load_chapter_repair_state("p1", 1)

        assert revision_count == 1
        assert was_rewritten is False
        mock_repo.list_by_chapter.assert_awaited_once_with("p1", 1, include_abandoned=True)
