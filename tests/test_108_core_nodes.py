"""Tests for Task 108 core node modifications."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from songyan.models import (
    ChapterVersion,
    LiteraryAuditResult,
    LiteraryObservation,
    ReviewCategory,
    ReviewIssue,
)
from songyan.workflows._nodes import (
    _load_chapter_repair_state,
    combine_revision_signals,
    literary_auditor_node,
    review_merger_node,
    rewrite_node,
    settlement_extractor_node,
)


class TestSettlementExtractorNodeSkipSettlement:
    """settlement_extractor_node _skip_settlement=True 路径测试."""

    @pytest.mark.asyncio
    async def test_skip_settlement_requires_review_without_accept(self) -> None:
        """skip_settlement=True 时不 accepted，不生成 summary，进入复核态."""
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
                                            "songyan.workflows._nodes.accept_with_settlement_boundary",
                                            new_callable=AsyncMock,
                                        ) as mock_accept:
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
                                                            node = settlement_extractor_node
                                                            result = await node(state)

        mock_extract.assert_not_awaited()
        mock_apply.assert_not_awaited()
        mock_write_summary.assert_not_awaited()
        mock_lifecycle.assert_not_awaited()
        mock_accept.assert_not_awaited()

        assert result["settlement_id"] is None
        assert result["summary_id"] is None
        assert result["status"] == "settlement_review"
        assert result["_settlement_needs_human_review"] is True
        mock_summary_repo.create.assert_not_awaited()


class TestRewriteNodeSuccessPath:
    """rewrite_node success path 返回值测试."""

    @pytest.mark.asyncio
    async def test_rewrite_draft_does_not_overwrite_existing_best(self) -> None:
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
                        "_best_version_id": "v-existing-best",
                        "_best_score_card": {"version_id": "v-existing-best"},
                    }
                    result = await rewrite_node(state)

        assert result["current_version_id"] == "v-rewrite-best"
        assert "_best_version_id" not in result
        assert "_best_score_card" not in result


class TestReviewMergerNodeRevisionSignals:
    """review_merger_node 合并审查与评分阻断信号测试."""

    def test_combine_revision_signals_preserves_merged_major(self) -> None:
        has_critical, has_major, needs_revision = combine_revision_signals(
            merged_has_critical=False,
            merged_has_major=True,
            score_needs_revision=False,
            score_has_critical=False,
            score_has_major=False,
        )
        assert has_critical is False
        assert has_major is True
        assert needs_revision is True

    @pytest.mark.asyncio
    async def test_merged_major_overrides_clean_score_card(self) -> None:
        """score_card flags 说不需要 revision，但 merged 有 major，则仍需 revision."""
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
                    merged_mock.has_major = True
                    merged_mock.issues = [
                        ReviewIssue(
                            issue_id="i1",
                            category=ReviewCategory.NARRATIVE_HOOK,
                            severity="major",
                            evidence_quote="quote",
                            evidence_location="loc",
                            issue_description="hook weak",
                        )
                    ]
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
                                    "_needs_revision": False,
                                    "_total_revision_count": 0,
                                    "_was_rewritten": False,
                                }
                                result = await review_merger_node(state)

        assert result["_needs_revision"] is True
        assert result["_has_critical"] is False
        assert result["_has_major"] is True

    @pytest.mark.asyncio
    async def test_rebound_rolls_back_to_active_best_and_syncs_score_card(self) -> None:
        """Ch101 形态：高分 best 后的劣化 rewrite 反弹，应回滚 active best."""
        mock_version = MagicMock()
        mock_version.version_id = "v-current"
        mock_version.content = "正文"

        best_version = MagicMock()
        best_version.version_id = "v-best"
        best_version.project_id = "p1"
        best_version.chapter_number = 1
        best_version.is_abandoned = False
        best_version.score_card = None

        mock_rule = MagicMock()
        mock_llm = MagicMock()

        mock_score_card = MagicMock()
        mock_score_card.flags.needs_revision = True
        mock_score_card.flags.coherence_critical = False
        mock_score_card.flags.coherence_major = True
        mock_score_card.overall_score = 0.50
        mock_score_card.model_dump.return_value = {
            "version_id": "v-current",
            "overall_score": 0.50,
        }
        for dim_name in ("length", "budget", "coherence", "momentum", "readability"):
            dim_mock = MagicMock()
            dim_mock.score = 0.50
            setattr(mock_score_card, dim_name, dim_mock)

        best_score_card = {
            "version_id": "v-best",
            "overall_score": 0.92,
            "length": {"score": 0.90},
            "budget": {"score": 0.90},
            "coherence": {"score": 0.90},
            "momentum": {"score": 0.90},
            "readability": {"score": 0.90},
            "flags": {
                "length_ok": True,
                "budget_ok": True,
                "coherence_critical": False,
                "coherence_major": False,
                "momentum_present": True,
                "readability_ok": True,
            },
        }

        merged_mock = MagicMock()
        merged_mock.has_critical = False
        merged_mock.has_major = True
        merged_mock.issues = [
            ReviewIssue(
                issue_id=f"i{i}",
                category=ReviewCategory.NARRATIVE_HOOK,
                severity="major",
                evidence_quote="quote",
                evidence_location="loc",
                issue_description="hook weak",
            )
            for i in range(3)
        ]

        with (
            patch(
                "songyan.workflows._nodes.load_version",
                new_callable=AsyncMock,
                return_value=mock_version,
            ),
            patch(
                "songyan.workflows._nodes.load_latest_audits",
                new_callable=AsyncMock,
                return_value=(mock_rule, mock_llm),
            ),
            patch(
                "songyan.workflows._nodes.merge_reviews",
                new_callable=AsyncMock,
                return_value=merged_mock,
            ),
            patch(
                "songyan.workflows._nodes.ScoreAggregator.aggregate",
                return_value=mock_score_card,
            ),
            patch(
                "songyan.workflows._nodes._load_chapter_repair_state",
                new_callable=AsyncMock,
                return_value=(2, True),
            ),
            patch("songyan.workflows._nodes.ChapterVersionRepository") as mock_ver_repo_cls,
            patch("songyan.workflows._nodes.ChapterHeadRepository") as mock_head_repo_cls,
        ):
            mock_ver_repo = AsyncMock()
            mock_ver_repo.update_score_card = AsyncMock()
            mock_ver_repo.get = AsyncMock(return_value=best_version)
            mock_ver_repo.mark_abandoned = AsyncMock()
            mock_ver_repo_cls.return_value = mock_ver_repo
            mock_head_repo = AsyncMock()
            mock_head_repo.update = AsyncMock()
            mock_head_repo_cls.return_value = mock_head_repo

            result = await review_merger_node({
                "project_id": "p1",
                "chapter_number": 1,
                "current_version_id": "v-current",
                "revision_round": 2,
                "_best_version_id": "v-best",
                "_best_report_id": "rr-best",
                "_best_issues_count": 1,
                "_best_overall_score": 0.92,
                "_best_score_card": best_score_card,
            })

        assert result["current_version_id"] == "v-best"
        assert result["_best_version_id"] == "v-best"
        assert result["_score_card"] == best_score_card
        assert result["_best_score_card"] == best_score_card
        mock_ver_repo.mark_abandoned.assert_awaited_once_with("v-current")
        mock_head_repo.update.assert_awaited_once()


class TestLiteraryAuditorNodeNonBlocking:
    """literary_auditor_node 只输出诊断，不改变修订决策."""

    @pytest.mark.asyncio
    async def test_critical_observation_does_not_set_needs_revision(self) -> None:
        mock_version = MagicMock()
        mock_version.version_id = "v1"
        mock_version.content = "正文"
        audit = LiteraryAuditResult(
            observations=[
                LiteraryObservation(
                    observation_id="lo-1",
                    observation_type="conceptual_idling",
                    description="概念空转",
                    severity="critical",
                )
            ]
        )
        with (
            patch(
                "songyan.workflows._nodes.load_version",
                new_callable=AsyncMock,
                return_value=mock_version,
            ),
            patch(
                "songyan.workflows._nodes._get_context_package",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "songyan.workflows._nodes.run_literary_audit",
                new_callable=AsyncMock,
                return_value=audit,
            ),
            patch(
                "songyan.workflows._nodes.save_literary_audit",
                new_callable=AsyncMock,
            ),
        ):
            result = await literary_auditor_node({
                "current_version_id": "v1",
                "_needs_revision": False,
            })

        assert result["status"] == "revision_routing"
        assert "literary_observation_id" in result
        assert "_needs_revision" not in result

    @pytest.mark.asyncio
    async def test_existing_observation_skips_literary_llm(self) -> None:
        mock_version = MagicMock()
        mock_version.version_id = "v1"
        mock_version.content = "正文"
        repo = AsyncMock()
        repo.get_latest_id_by_version = AsyncMock(return_value="lo-existing")

        with (
            patch(
                "songyan.workflows._nodes.load_version",
                new_callable=AsyncMock,
                return_value=mock_version,
            ),
            patch("songyan.workflows._nodes.LiteraryObservationRepository", return_value=repo),
            patch(
                "songyan.workflows._nodes._get_context_package",
                new_callable=AsyncMock,
            ) as mock_context,
            patch(
                "songyan.workflows._nodes.run_literary_audit",
                new_callable=AsyncMock,
            ) as mock_audit,
        ):
            result = await literary_auditor_node({"current_version_id": "v1"})

        assert result == {
            "literary_observation_id": "lo-existing",
            "status": "revision_routing",
        }
        mock_context.assert_not_called()
        mock_audit.assert_not_called()
        assert "_needs_revision" not in result


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

    @pytest.mark.asyncio
    async def test_current_lineage_excludes_previous_run_revisions(self) -> None:
        """Task 114b2: 新回放 draft 不应继承历史 run 的 revision/rewrite 计数."""
        old_draft = ChapterVersion(
            version_id="old-draft",
            project_id="p1",
            chapter_number=1,
            version_number=1,
            version_type="draft",
            is_abandoned=False,
            content="old",
        )
        old_revision_1 = ChapterVersion(
            version_id="old-rev-1",
            project_id="p1",
            chapter_number=1,
            version_number=2,
            version_type="revision",
            is_abandoned=False,
            content="old revision 1",
            parent_version_id="old-draft",
        )
        old_revision_2 = ChapterVersion(
            version_id="old-rev-2",
            project_id="p1",
            chapter_number=1,
            version_number=3,
            version_type="revision",
            is_abandoned=False,
            content="old revision 2",
            parent_version_id="old-rev-1",
        )
        fresh_rerun_draft = ChapterVersion(
            version_id="fresh-draft",
            project_id="p1",
            chapter_number=1,
            version_number=4,
            version_type="draft",
            is_abandoned=False,
            content="fresh",
            parent_version_id=None,
        )

        mock_repo = AsyncMock()
        mock_repo.list_by_chapter = AsyncMock(
            return_value=[old_draft, old_revision_1, old_revision_2, fresh_rerun_draft]
        )

        with patch(
            "songyan.workflows._nodes.ChapterVersionRepository",
            return_value=mock_repo,
        ):
            revision_count, was_rewritten = await _load_chapter_repair_state(
                "p1",
                1,
                "fresh-draft",
            )

        assert revision_count == 0
        assert was_rewritten is False
        mock_repo.list_by_chapter.assert_awaited_once_with("p1", 1, include_abandoned=True)

    @pytest.mark.asyncio
    async def test_current_lineage_counts_current_revision_chain(self) -> None:
        """Task 114b2: 当前 parent 链上的 revision 仍应计入收敛状态."""
        draft = ChapterVersion(
            version_id="draft",
            project_id="p1",
            chapter_number=1,
            version_number=1,
            version_type="draft",
            is_abandoned=False,
            content="draft",
        )
        revision = ChapterVersion(
            version_id="revision",
            project_id="p1",
            chapter_number=1,
            version_number=2,
            version_type="revision",
            is_abandoned=False,
            content="revision",
            parent_version_id="draft",
        )
        rewrite = ChapterVersion(
            version_id="rewrite",
            project_id="p1",
            chapter_number=1,
            version_number=3,
            version_type="draft",
            is_abandoned=False,
            content="rewrite",
            parent_version_id="revision",
        )

        mock_repo = AsyncMock()
        mock_repo.list_by_chapter = AsyncMock(return_value=[draft, revision, rewrite])

        with patch(
            "songyan.workflows._nodes.ChapterVersionRepository",
            return_value=mock_repo,
        ):
            revision_count, was_rewritten = await _load_chapter_repair_state(
                "p1",
                1,
                "rewrite",
            )

        assert revision_count == 1
        assert was_rewritten is True
        mock_repo.list_by_chapter.assert_awaited_once_with("p1", 1, include_abandoned=True)
