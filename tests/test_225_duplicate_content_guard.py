"""Task 225: 脏版本（逐字重复句）不得成为 best / rollback 目标.

语料来源：.tmp/225_ch2_new.txt（rev-2-12 被误 accept 脏版）的逐字重复句。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from songyan.models import ReviewCategory, ReviewIssue
from songyan.workflows._nodes import (
    _version_has_duplicate_content,
    review_merger_node,
    rewrite_node,
)

_DUP_SENTENCE = "对话框关闭后，8.0kg的缺口没有扩大，反而被固定成一个可复测的间隔。"

# ch2_new 真实形态：两段共享逐字长句但段落整体相似度低于段落级阈值
_DIRTY_CONTENT = (
    f"然后他移动光标，选择了“否”。系统没有再次询问。{_DUP_SENTENCE}\n\n"
    f"系统没有再次询问。{_DUP_SENTENCE}"
    "本地终端在间隔两侧添加了测量基准点，使这段缺口可以被未来的任何复核操作精确复现。"
)
_CLEAN_CONTENT = (
    "沈砚把完整链路重新走了一遍，每一步都留下独立的时间戳。\n\n"
    "复核终端亮起绿色的状态灯，缺口数值保持稳定，没有任何漂移。"
)


def _qg_pass_dump(version_id: str, overall: float = 0.9) -> dict:
    return {
        "version_id": version_id,
        "overall_score": overall,
        "length": {"score": 0.9},
        "budget": {"score": 0.9},
        "coherence": {"score": 0.9},
        "momentum": {"score": 0.9},
        "readability": {"score": 0.9},
        "flags": {
            "length_ok": True,
            "budget_ok": True,
            "coherence_critical": False,
            "coherence_major": False,
            "momentum_present": True,
            "readability_ok": True,
            "needs_revision": True,
        },
    }


def _make_score_card(version_id: str, overall: float = 0.9) -> MagicMock:
    score_card = MagicMock()
    score_card.flags.needs_revision = True
    score_card.flags.coherence_critical = False
    score_card.flags.coherence_major = False
    score_card.overall_score = overall
    score_card.model_dump.return_value = _qg_pass_dump(version_id, overall)
    for dim_name in ("length", "budget", "coherence", "momentum", "readability"):
        dim = MagicMock()
        dim.score = 0.9
        setattr(score_card, dim_name, dim)
    return score_card


def _make_merged(issue_count: int = 1) -> MagicMock:
    merged = MagicMock()
    merged.has_critical = False
    merged.has_major = True
    merged.issues = [
        ReviewIssue(
            issue_id=f"i{i}",
            category=ReviewCategory.NARRATIVE_HOOK,
            severity="major",
            evidence_quote="quote",
            evidence_location="loc",
            issue_description="hook weak",
        )
        for i in range(issue_count)
    ]
    return merged


class TestVersionHasDuplicateContent:
    def test_dirty_content_detected(self) -> None:
        version = MagicMock()
        version.content = _DIRTY_CONTENT

        assert _version_has_duplicate_content(version) is True

    def test_clean_content_passes(self) -> None:
        version = MagicMock()
        version.content = _CLEAN_CONTENT

        assert _version_has_duplicate_content(version) is False

    def test_empty_or_missing_content_passes(self) -> None:
        empty = MagicMock()
        empty.content = ""
        none_content = MagicMock()
        none_content.content = None
        non_str = MagicMock()  # content 未设置时为 MagicMock，视为无正文

        assert _version_has_duplicate_content(empty) is False
        assert _version_has_duplicate_content(none_content) is False
        assert _version_has_duplicate_content(non_str) is False


class TestBestSaveSkipsDuplicateContent:
    """review_merger_node：脏版本不得写入 _best_version_id 等 best 字段."""

    async def _run(self, content: str) -> dict:
        version = MagicMock()
        version.version_id = "v-current"
        version.content = content

        with (
            patch(
                "songyan.workflows._nodes.load_version",
                new_callable=AsyncMock,
                return_value=version,
            ),
            patch(
                "songyan.workflows._nodes.load_latest_audits",
                new_callable=AsyncMock,
                return_value=(MagicMock(), MagicMock()),
            ),
            patch(
                "songyan.workflows._nodes.merge_reviews",
                new_callable=AsyncMock,
                return_value=_make_merged(),
            ),
            patch(
                "songyan.workflows._nodes.ScoreAggregator.aggregate",
                return_value=_make_score_card("v-current"),
            ),
            patch(
                "songyan.workflows._nodes._load_chapter_repair_state",
                new_callable=AsyncMock,
                return_value=(0, False),
            ),
            patch("songyan.workflows._nodes.ChapterVersionRepository") as mock_repo_cls,
        ):
            mock_repo = AsyncMock()
            mock_repo.update_score_card = AsyncMock()
            mock_repo_cls.return_value = mock_repo

            return await review_merger_node(
                {
                    "project_id": "p1",
                    "chapter_number": 1,
                    "current_version_id": "v-current",
                    "revision_round": 0,
                    "_needs_revision": False,
                    "_total_revision_count": 0,
                    "_was_rewritten": False,
                }
            )

    @pytest.mark.asyncio
    async def test_dirty_version_not_saved_as_best(self) -> None:
        result = await self._run(_DIRTY_CONTENT)

        assert result["_needs_revision"] is True
        assert "_best_version_id" not in result
        assert "_best_score_card" not in result

    @pytest.mark.asyncio
    async def test_clean_version_saved_as_best(self) -> None:
        result = await self._run(_CLEAN_CONTENT)

        assert result["_best_version_id"] == "v-current"


class TestBestUpdateSkipsDuplicateContent:
    """revision 未反弹分支：脏版本不得覆盖既有 best."""

    async def _run(self, content: str) -> dict:
        version = MagicMock()
        version.version_id = "v-current"
        version.content = content

        with (
            patch(
                "songyan.workflows._nodes.load_version",
                new_callable=AsyncMock,
                return_value=version,
            ),
            patch(
                "songyan.workflows._nodes.load_latest_audits",
                new_callable=AsyncMock,
                return_value=(MagicMock(), MagicMock()),
            ),
            patch(
                "songyan.workflows._nodes.merge_reviews",
                new_callable=AsyncMock,
                return_value=_make_merged(),
            ),
            patch(
                "songyan.workflows._nodes.ScoreAggregator.aggregate",
                return_value=_make_score_card("v-current"),
            ),
            patch(
                "songyan.workflows._nodes._load_chapter_repair_state",
                new_callable=AsyncMock,
                return_value=(1, False),
            ),
            patch("songyan.workflows._nodes.ChapterVersionRepository") as mock_repo_cls,
        ):
            mock_repo = AsyncMock()
            mock_repo.update_score_card = AsyncMock()
            mock_repo_cls.return_value = mock_repo

            return await review_merger_node(
                {
                    "project_id": "p1",
                    "chapter_number": 1,
                    "current_version_id": "v-current",
                    "revision_round": 1,
                    "_needs_revision": True,
                    "_total_revision_count": 1,
                    "_was_rewritten": False,
                    "_best_version_id": "v-best",
                    "_best_report_id": "rr-best",
                    "_best_issues_count": 1,
                    "_best_overall_score": 0.9,
                    "_best_score_card": _qg_pass_dump("v-best"),
                }
            )

    @pytest.mark.asyncio
    async def test_dirty_revision_does_not_replace_best(self) -> None:
        result = await self._run(_DIRTY_CONTENT)

        # 不更新 best：state 中既有 _best_version_id 保持不变（结果不含覆盖键）
        assert result["_needs_revision"] is True
        assert "_best_version_id" not in result

    @pytest.mark.asyncio
    async def test_clean_revision_updates_best(self) -> None:
        result = await self._run(_CLEAN_CONTENT)

        assert result["_best_version_id"] == "v-current"


class TestReboundRollbackSkipsDuplicateTarget:
    """revision 反弹回滚：脏 best 不得作为回滚目标，走原有 fallback（human_confirm）."""

    @pytest.mark.asyncio
    async def test_dirty_best_not_used_as_rollback_target(self) -> None:
        version = MagicMock()
        version.version_id = "v-current"
        version.content = "正文"

        best_version = MagicMock()
        best_version.version_id = "v-best"
        best_version.project_id = "p1"
        best_version.chapter_number = 1
        best_version.is_abandoned = False
        best_version.score_card = None
        best_version.content = _DIRTY_CONTENT

        score_card = MagicMock()
        score_card.flags.needs_revision = True
        score_card.flags.coherence_critical = False
        score_card.flags.coherence_major = True
        score_card.overall_score = 0.50
        score_card.model_dump.return_value = {
            "version_id": "v-current",
            "overall_score": 0.50,
        }
        for dim_name in ("length", "budget", "coherence", "momentum", "readability"):
            dim = MagicMock()
            dim.score = 0.50
            setattr(score_card, dim_name, dim)

        with (
            patch(
                "songyan.workflows._nodes.load_version",
                new_callable=AsyncMock,
                return_value=version,
            ),
            patch(
                "songyan.workflows._nodes.load_latest_audits",
                new_callable=AsyncMock,
                return_value=(MagicMock(), MagicMock()),
            ),
            patch(
                "songyan.workflows._nodes.merge_reviews",
                new_callable=AsyncMock,
                return_value=_make_merged(issue_count=3),
            ),
            patch(
                "songyan.workflows._nodes.ScoreAggregator.aggregate",
                return_value=score_card,
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

            result = await review_merger_node(
                {
                    "project_id": "p1",
                    "chapter_number": 1,
                    "current_version_id": "v-current",
                    "revision_round": 2,
                    "_best_version_id": "v-best",
                    "_best_report_id": "rr-best",
                    "_best_issues_count": 1,
                    "_best_overall_score": 0.92,
                    "_best_score_card": _qg_pass_dump("v-best", overall=0.92),
                }
            )

        # 脏 best 被跳过 → 无有效回滚目标 → human_confirm，不废弃当前版本
        assert result["status"] == "human_confirm"
        assert result["current_version_id"] == "v-current"
        assert result["_convergence_failed"] is True
        assert result["_revision_rebound"] is True
        mock_ver_repo.mark_abandoned.assert_not_awaited()
        mock_head_repo.update.assert_not_awaited()


class TestRewriteRollbackSkipsDuplicateTarget:
    """rewrite 结构失败回滚：脏 best 被跳过后回到无目标 fallback."""

    @pytest.mark.asyncio
    async def test_struct_failure_dirty_best_skipped(self) -> None:
        version = MagicMock()
        version.version_id = "v-rewrite"
        version.scenes = [{"scene_id": "s1"}]  # 仅 1 个场景 → 结构失败
        version.content = "content"
        version.word_count = 3000

        best_version = MagicMock()
        best_version.version_id = "v-best"
        best_version.content = _DIRTY_CONTENT
        best_version.score_card = None

        async def load_active_best(
            *,
            version_id: str | None,
            project_id: str,
            chapter_number: int,
        ) -> MagicMock | None:
            if version_id == "v-best":
                return best_version
            return None

        with (
            patch("songyan.workflows._nodes.write_chapter", new_callable=AsyncMock) as mock_write,
            patch(
                "songyan.workflows._nodes._get_context_package",
                new_callable=AsyncMock,
            ) as mock_ctx,
            patch(
                "songyan.workflows._nodes._load_active_best_version",
                new_callable=AsyncMock,
                side_effect=load_active_best,
            ),
            patch("songyan.workflows._nodes.ChapterVersionRepository") as mock_ver_repo,
            patch("songyan.workflows._nodes.ChapterHeadRepository") as mock_head_repo,
        ):
            mock_write.return_value = version
            mock_ctx.return_value = MagicMock()
            mock_ver_repo.return_value.mark_abandoned = AsyncMock()
            mock_head_repo.return_value.update = AsyncMock()

            result = await rewrite_node(
                {
                    "project_id": "p1",
                    "chapter_number": 1,
                    "current_version_id": "v-prev",
                    "chapter_goal_id": "g1",
                    "_best_version_id": "v-best",
                    "revision_round": 2,
                    "_total_revision_count": 2,
                }
            )

        # 脏 best 被跳过且无 previous 可回滚 → 保持 rewrite 版本，标人工
        assert "struct_integrity_failed" in result["_rewrite_reason"]
        assert result["current_version_id"] == "v-rewrite"
        assert result["status"] == "human_confirm"
        assert result["_skip_settlement"] is True
        mock_ver_repo.return_value.mark_abandoned.assert_not_awaited()
        mock_head_repo.return_value.update.assert_not_awaited()
