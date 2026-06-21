"""Tests for Task 107: Convergence Guardrail.

- rewrite_node 结构完整性校验（scene_count >= 2 + hooks）
- quality_gate_node 收敛终点判断（修复耗尽回滚 best_version）
- human_confirm_router skip_settlement 分支
- run_logger 记录 convergence_failed / skip_settlement
"""

from __future__ import annotations

from datetime import UTC
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from songyan.workflows._nodes import human_gate_node, quality_gate_node, rewrite_node
from songyan.workflows.phase1_graph import human_confirm_router

# ---------------------------------------------------------------------------
# rewrite_node 结构完整性校验
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rewrite_scene_count_too_low_triggers_rollback() -> None:
    """rewrite 结构失败但回滚到 best_version → 后续 accept 仍执行 settlement."""
    version = MagicMock()
    version.version_id = "v-rewrite"
    version.scenes = [{"scene_id": "s1"}]  # 仅 1 个场景
    version.content = "content"
    version.word_count = 3000
    best_version = MagicMock()
    best_version.version_id = "v-best"

    with (
        patch("songyan.workflows._nodes.write_chapter", new_callable=AsyncMock) as mock_write,
        patch("songyan.workflows._nodes._get_context_package", new_callable=AsyncMock) as mock_ctx,
        patch(
            "songyan.workflows._nodes._load_active_best_version",
            new_callable=AsyncMock,
            return_value=best_version,
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

    assert result["_convergence_failed"] is True
    assert result["_skip_settlement"] is False
    assert result["_settlement_needs_human_review"] is False
    assert result["status"] == "human_confirm"
    assert result["current_version_id"] == "v-best"
    assert "struct_integrity_failed" in result["_rewrite_reason"]
    mock_ver_repo.return_value.mark_abandoned.assert_awaited_once_with("v-rewrite")
    mock_head_repo.return_value.update.assert_awaited_once()


@pytest.mark.asyncio
async def test_rewrite_scene_count_too_low_without_best_rolls_back_previous() -> None:
    """Task 121c: 无 QG best 但可回滚前版本时，accept 后仍执行 settlement."""
    version = MagicMock()
    version.version_id = "v-rewrite"
    version.scenes = [{"scene_id": "s1"}]
    version.content = "content"
    version.word_count = 3000
    previous_version = MagicMock()
    previous_version.version_id = "v-prev"

    async def load_active_best(
        *,
        version_id: str | None,
        project_id: str,
        chapter_number: int,
    ) -> MagicMock | None:
        if version_id == "v-prev":
            return previous_version
        return None

    with (
        patch("songyan.workflows._nodes.write_chapter", new_callable=AsyncMock) as mock_write,
        patch("songyan.workflows._nodes._get_context_package", new_callable=AsyncMock) as mock_ctx,
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
                "revision_round": 2,
                "_total_revision_count": 2,
            }
        )

    assert result["current_version_id"] == "v-prev"
    assert result["_convergence_failed"] is True
    assert result["_skip_settlement"] is False
    assert result["_settlement_needs_human_review"] is False
    mock_ver_repo.return_value.mark_abandoned.assert_awaited_once_with("v-rewrite")
    mock_head_repo.return_value.update.assert_awaited_once()


@pytest.mark.asyncio
async def test_rewrite_missing_hooks_triggers_rollback() -> None:
    """rewrite 后缺失 ending_hook → 回滚 best，accept 后仍执行 settlement."""
    version = MagicMock()
    version.version_id = "v-rewrite"
    version.scenes = [{"scene_id": "s1"}, {"scene_id": "s2"}]
    version.content = "content"
    version.word_count = 3000
    best_version = MagicMock()
    best_version.version_id = "v-best"

    rule_result = MagicMock()
    rule_result.has_opening_hook = True
    rule_result.has_ending_hook = False

    with (
        patch("songyan.workflows._nodes.write_chapter", new_callable=AsyncMock) as mock_write,
        patch("songyan.workflows._nodes._get_context_package", new_callable=AsyncMock) as mock_ctx,
        patch("songyan.workflows._nodes.load_project", new_callable=AsyncMock) as mock_proj,
        patch("songyan.workflows._nodes.load_genre_profile", return_value=None),
        patch("songyan.workflows._nodes.load_chapter_goal", new_callable=AsyncMock) as mock_goal,
        patch("songyan.workflows._nodes.run_rule_audit", return_value=rule_result),
        patch(
            "songyan.workflows._nodes._load_active_best_version",
            new_callable=AsyncMock,
            return_value=best_version,
        ),
        patch("songyan.workflows._nodes.ChapterVersionRepository") as mock_ver_repo,
        patch("songyan.workflows._nodes.ChapterHeadRepository") as mock_head_repo,
    ):
        mock_write.return_value = version
        mock_ctx.return_value = MagicMock()
        mock_proj.return_value = MagicMock(genre_id="g1")
        mock_goal.return_value = MagicMock(word_count_target=3000)
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
            }
        )

    assert result["_convergence_failed"] is True
    assert result["_skip_settlement"] is False
    assert "missing_ending_hook" in result["_rewrite_reason"]


@pytest.mark.asyncio
async def test_rewrite_struct_ok_passes_through() -> None:
    """rewrite 后结构完整 → 正常返回 rule_auditing."""
    version = MagicMock()
    version.version_id = "v-rewrite"
    version.scenes = [{"scene_id": "s1"}, {"scene_id": "s2"}]
    version.content = "content"
    version.word_count = 3000

    rule_result = MagicMock()
    rule_result.has_opening_hook = True
    rule_result.has_ending_hook = True

    with (
        patch("songyan.workflows._nodes.write_chapter", new_callable=AsyncMock) as mock_write,
        patch("songyan.workflows._nodes._get_context_package", new_callable=AsyncMock) as mock_ctx,
        patch("songyan.workflows._nodes.load_project", new_callable=AsyncMock) as mock_proj,
        patch("songyan.workflows._nodes.load_genre_profile", return_value=None),
        patch("songyan.workflows._nodes.load_chapter_goal", new_callable=AsyncMock) as mock_goal,
        patch("songyan.workflows._nodes.run_rule_audit", return_value=rule_result),
        patch(
            "songyan.workflows._nodes._enforce_word_count",
            return_value=("c", [], 3000, False, ""),
        ),
    ):
        mock_write.return_value = version
        mock_ctx.return_value = MagicMock()
        mock_proj.return_value = MagicMock(genre_id="g1")
        mock_goal.return_value = MagicMock(word_count_target=3000)

        result = await rewrite_node(
            {
                "project_id": "p1",
                "chapter_number": 1,
                "current_version_id": "v-prev",
                "chapter_goal_id": "g1",
                "revision_round": 2,
            }
        )

    assert result["status"] == "rule_auditing"
    assert result.get("_convergence_failed", False) is False
    assert result.get("_skip_settlement", False) is False


# ---------------------------------------------------------------------------
# quality_gate_node 收敛终点判断
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_qg_after_rewrite_failure_rollback_best_version() -> None:
    """rewrite 后 QG 仍失败 → 回滚 best_version，但不跳过 settlement."""
    version = MagicMock()
    version.word_count = 3000
    best_version = MagicMock()
    best_version.version_id = "v-best"
    best_version.score_card = None

    with (
        patch("songyan.workflows._nodes.load_version", new_callable=AsyncMock) as mock_ver,
        patch(
            "songyan.workflows._nodes._load_chapter_repair_state",
            new_callable=AsyncMock,
            return_value=(2, True),
        ),
        patch(
            "songyan.workflows._nodes._load_active_best_version",
            new_callable=AsyncMock,
            return_value=best_version,
        ),
        patch("songyan.workflows._nodes.ChapterHeadRepository") as mock_head_repo,
    ):
        mock_ver.return_value = version
        mock_head_repo.return_value.update = AsyncMock()

        result = await quality_gate_node(
            {
                "project_id": "p1",
                "chapter_number": 1,
                "current_version_id": "v-current",
                "_was_rewritten": True,
                "_best_version_id": "v-best",
                "_best_score_card": {"version_id": "v-best", "overall_score": 0.8},
                "_score_card": {
                    "version_id": "v",
                    "overall_score": 0.5,
                    "length": {"score": 1.0},
                    "budget": {"score": 1.0},
                    "coherence": {"score": 0.5},
                    "momentum": {"score": 1.0},
                    "readability": {"score": 1.0},
                    "flags": {
                        "length_ok": True,
                        "budget_ok": True,
                        "coherence_critical": True,
                        "coherence_major": False,
                        "momentum_present": True,
                        "readability_ok": True,
                    },
                },
            }
        )

    assert result["status"] == "human_confirm"
    assert result["_convergence_failed"] is True
    assert result["_skip_settlement"] is False
    assert result["_settlement_needs_human_review"] is False
    assert result["current_version_id"] == "v-best"
    mock_head_repo.return_value.update.assert_awaited_once()


@pytest.mark.asyncio
async def test_qg_after_two_revisions_failure_rollback() -> None:
    """2 轮 revision 后 QG 仍失败 → 回滚 best_version 并继续 settlement."""
    version = MagicMock()
    version.word_count = 3000
    best_version = MagicMock()
    best_version.version_id = "v-best"
    best_version.score_card = None

    with (
        patch("songyan.workflows._nodes.load_version", new_callable=AsyncMock) as mock_ver,
        patch(
            "songyan.workflows._nodes._load_chapter_repair_state",
            new_callable=AsyncMock,
            return_value=(2, False),
        ),
        patch(
            "songyan.workflows._nodes._load_active_best_version",
            new_callable=AsyncMock,
            return_value=best_version,
        ),
        patch("songyan.workflows._nodes.ChapterHeadRepository") as mock_head_repo,
    ):
        mock_ver.return_value = version
        mock_head_repo.return_value.update = AsyncMock()

        result = await quality_gate_node(
            {
                "project_id": "p1",
                "chapter_number": 1,
                "current_version_id": "v-current",
                "_best_version_id": "v-best",
                "_best_score_card": {"version_id": "v-best", "overall_score": 0.8},
                "_content_preservation_ratio": 0.50,
            }
        )

    assert result["status"] == "human_confirm"
    assert result["_convergence_failed"] is True
    assert result["_skip_settlement"] is False
    assert result["_settlement_needs_human_review"] is False
    assert result["current_version_id"] == "v-best"


@pytest.mark.asyncio
async def test_qg_convergence_recovers_with_qg_pass_best_version() -> None:
    """Task 114b2: 若存在 QG 合格 best，收敛失败应回滚并继续 settlement."""
    version = MagicMock()
    version.version_id = "v-current"
    version.version_type = "revision"
    version.word_count = 4100
    best_version = MagicMock()
    best_version.version_id = "v-best"
    best_version.score_card = None

    qg_pass_score_card = {
        "version_id": "v-best",
        "overall_score": 0.8,
        "length": {"score": 0.6},
        "budget": {"score": 1.0},
        "coherence": {"score": 0.85},
        "momentum": {"score": -1.0},
        "readability": {"score": 0.7},
        "flags": {
            "length_ok": True,
            "budget_ok": True,
            "coherence_critical": False,
            "coherence_major": False,
            "momentum_present": True,
            "readability_ok": True,
        },
    }

    with (
        patch("songyan.workflows._nodes.load_version", new_callable=AsyncMock) as mock_ver,
        patch(
            "songyan.workflows._nodes._load_chapter_repair_state",
            new_callable=AsyncMock,
            return_value=(2, False),
        ),
        patch(
            "songyan.workflows._nodes._load_active_best_version",
            new_callable=AsyncMock,
            return_value=best_version,
        ),
        patch("songyan.workflows._nodes.ChapterHeadRepository") as mock_head_repo,
    ):
        mock_ver.return_value = version
        mock_head_repo.return_value.update = AsyncMock()

        result = await quality_gate_node(
            {
                "project_id": "p1",
                "chapter_number": 1,
                "current_version_id": "v-current",
                "_was_rewritten": True,
                "_best_version_id": "v-best",
                "_best_score_card": qg_pass_score_card,
                "_score_card": {
                    "version_id": "v-current",
                    "overall_score": 0.5,
                    "length": {"score": 0.44},
                    "budget": {"score": 1.0},
                    "coherence": {"score": 0.85},
                    "momentum": {"score": -1.0},
                    "readability": {"score": 0.7},
                    "flags": {
                        "length_ok": False,
                        "budget_ok": True,
                        "coherence_critical": False,
                        "coherence_major": False,
                        "momentum_present": True,
                        "readability_ok": True,
                    },
                },
            }
        )

    assert result["status"] == "human_confirm"
    assert result["_quality_gate_passed"] is True
    assert result["_convergence_failed"] is False
    assert result["_skip_settlement"] is False
    assert result["current_version_id"] == "v-best"
    mock_head_repo.return_value.update.assert_awaited_once()


@pytest.mark.asyncio
async def test_qg_without_best_version_no_rollback() -> None:
    """修复耗尽但无 best_version → 明确阻断 settlement，不尝试回滚."""
    version = MagicMock()
    version.word_count = 3000

    with (
        patch("songyan.workflows._nodes.load_version", new_callable=AsyncMock) as mock_ver,
        patch(
            "songyan.workflows._nodes._load_chapter_repair_state",
            new_callable=AsyncMock,
            return_value=(2, True),
        ),
        patch("songyan.workflows._nodes.ChapterHeadRepository") as mock_head_repo,
    ):
        mock_ver.return_value = version
        mock_head_repo.return_value.update = AsyncMock()

        result = await quality_gate_node(
            {
                "project_id": "p1",
                "chapter_number": 1,
                "current_version_id": "v-current",
                "_was_rewritten": True,
                "_best_version_id": None,
                "_content_preservation_ratio": 0.50,
            }
        )

    assert result["status"] == "human_confirm"
    assert result["_convergence_failed"] is True
    assert result["_skip_settlement"] is True
    mock_head_repo.return_value.update.assert_not_awaited()


# ---------------------------------------------------------------------------
# human_confirm_router skip_settlement 分支
# ---------------------------------------------------------------------------


def test_human_confirm_router_skip_settlement() -> None:
    """_skip_settlement=True 时 accept 路由到 skip_settlement（END）."""
    state = {
        "human_decision": "accept",
        "_skip_settlement": True,
    }
    assert human_confirm_router(state) == "accept"


def test_human_confirm_router_accept_without_skip() -> None:
    """_skip_settlement=False 时 accept 正常路由到 settlement."""
    state = {
        "human_decision": "accept",
        "_skip_settlement": False,
    }
    assert human_confirm_router(state) == "accept"


def test_human_confirm_router_none_decision_with_skip() -> None:
    """decision=None 且 _skip_settlement=True 也路由到 skip_settlement."""
    state = {
        "human_decision": None,
        "_skip_settlement": True,
    }
    assert human_confirm_router(state) == "accept"


# ---------------------------------------------------------------------------
# human_gate_node 透传 skip_settlement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_human_gate_accept_transmits_skip_settlement() -> None:
    """accept 路径透传 _convergence_failed 和 _skip_settlement."""
    version = MagicMock()
    version.version_id = "v1"
    version.content = "test"
    version.word_count = 3000

    with (
        patch("songyan.workflows._nodes.load_version", new_callable=AsyncMock) as mock_ver,
        patch("songyan.workflows._nodes.interrupt", return_value="accept"),
        patch("songyan.workflows._nodes.ChapterHeadRepository") as mock_head,
        patch("songyan.workflows._nodes.ChapterVersionRepository") as mock_ver_repo,
        patch("songyan.workflows._nodes.load_chapter_goal", new_callable=AsyncMock) as mock_goal,
    ):
        mock_ver.return_value = version
        mock_head.return_value.update = AsyncMock()
        mock_ver_repo.return_value.accept_version = AsyncMock()
        mock_goal.return_value = MagicMock(word_count_target=3000)

        result = await human_gate_node(
            {
                "project_id": "p1",
                "chapter_number": 1,
                "current_version_id": "v1",
                "_convergence_failed": True,
                "_skip_settlement": True,
                "_quality_gate_passed": True,
                "_has_major": True,
            }
        )

    assert result["_convergence_failed"] is True
    assert result["_skip_settlement"] is True
    assert result["_quality_gate_passed"] is True


# ---------------------------------------------------------------------------
# run_logger 记录收敛状态
# ---------------------------------------------------------------------------


def test_run_logger_records_convergence_flags() -> None:
    """build_chapter_run_log 正确提取 state 中的 convergence_failed / skip_settlement."""
    from datetime import datetime

    from songyan.workflows._run_logger import build_chapter_run_log

    now = datetime.now(UTC)
    log = build_chapter_run_log(
        run_id="r1",
        project_id="p1",
        chapter_number=1,
        started_at=now,
        finished_at=now,
        success=True,
        final_state={
            "_convergence_failed": True,
            "_skip_settlement": True,
            "_quality_gate_passed": False,
        },
    )
    assert log.convergence_failed is True
    assert log.skip_settlement is True
