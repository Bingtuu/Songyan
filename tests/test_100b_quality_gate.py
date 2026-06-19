"""Tests for Task 100b: Quality Gate + Edit Audit.

- quality_gate_node 三联检（字数/保留率/新问题）
- quality_gate_router 路由
- human_gate_node edit 分支重走 Audit
- human_confirm_router edit_audit 映射
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from songyan.workflows._nodes import human_gate_node, quality_gate_node
from songyan.workflows.phase1_graph import human_confirm_router, quality_gate_router

# ---------------------------------------------------------------------------
# quality_gate_node 三联检
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_quality_gate_error_stage_missing_version() -> None:
    """quality_gate_node returns status='quality_gate' when version missing."""
    with patch("songyan.workflows._nodes.load_version", new_callable=AsyncMock) as mock:
        mock.return_value = None
        result = await quality_gate_node({"current_version_id": "missing"})
    assert result["status"] == "quality_gate"
    assert result["error"] is not None


@pytest.mark.asyncio
async def test_quality_gate_word_count_too_high() -> None:
    """字数 > 1.30x → 路由到 rewrite."""
    version = MagicMock()
    version.word_count = 4500
    goal = MagicMock()
    goal.word_count_target = 3000
    with (
        patch("songyan.workflows._nodes.load_version", new_callable=AsyncMock) as mock_ver,
        patch("songyan.workflows._nodes.load_chapter_goal", new_callable=AsyncMock) as mock_goal,
        patch(
            "songyan.workflows._nodes._load_chapter_repair_state",
            new_callable=AsyncMock,
            return_value=(0, False),
        ),
    ):
        mock_ver.return_value = version
        mock_goal.return_value = goal
        result = await quality_gate_node({
            "project_id": "p1",
            "chapter_number": 1,
            "current_version_id": "v-1",
        })
    assert result["_quality_gate_passed"] is False
    assert any("word_count_too_high" in f for f in result["_quality_gate_failures"])
    assert result["status"] == "rewrite"


@pytest.mark.asyncio
async def test_quality_gate_word_count_too_high_after_rewrite_stops_loop() -> None:
    """已重写后仍超字数 → 不再 rewrite，进入 human_confirm 收束."""
    version = MagicMock()
    version.word_count = 4500
    goal = MagicMock()
    goal.word_count_target = 3000
    with (
        patch("songyan.workflows._nodes.load_version", new_callable=AsyncMock) as mock_ver,
        patch("songyan.workflows._nodes.load_chapter_goal", new_callable=AsyncMock) as mock_goal,
        patch(
            "songyan.workflows._nodes._load_chapter_repair_state",
            new_callable=AsyncMock,
            return_value=(2, True),
        ),
    ):
        mock_ver.return_value = version
        mock_goal.return_value = goal
        result = await quality_gate_node({
            "project_id": "p1",
            "chapter_number": 1,
            "current_version_id": "v-1",
            "_was_rewritten": True,
        })
    assert result["_quality_gate_passed"] is False
    assert any("word_count_too_high" in f for f in result["_quality_gate_failures"])
    assert result["status"] == "human_confirm"
    assert result["_needs_revision"] is False


@pytest.mark.asyncio
async def test_quality_gate_non_word_failure_after_rewrite_stops_loop() -> None:
    """已重写后保留率失败 → 不再绕过 router 进入 revision_handler."""
    version = MagicMock()
    version.word_count = 3000
    goal = MagicMock()
    goal.word_count_target = 3000
    with (
        patch("songyan.workflows._nodes.load_version", new_callable=AsyncMock) as mock_ver,
        patch("songyan.workflows._nodes.load_chapter_goal", new_callable=AsyncMock) as mock_goal,
        patch(
            "songyan.workflows._nodes._load_chapter_repair_state",
            new_callable=AsyncMock,
            return_value=(2, True),
        ),
    ):
        mock_ver.return_value = version
        mock_goal.return_value = goal
        result = await quality_gate_node({
            "project_id": "p1",
            "chapter_number": 1,
            "current_version_id": "v-1",
            "_was_rewritten": True,
            "_content_preservation_ratio": 0.50,
        })
    assert result["_quality_gate_passed"] is False
    assert any("preservation_too_low" in f for f in result["_quality_gate_failures"])
    assert result["status"] == "human_confirm"
    assert result["_needs_revision"] is False


@pytest.mark.asyncio
async def test_quality_gate_non_word_failure_after_two_revisions_stops_loop() -> None:
    """DB 已有 2 轮 revision 后保留率失败 → 不再继续 revision."""
    version = MagicMock()
    version.word_count = 3000
    goal = MagicMock()
    goal.word_count_target = 3000
    with (
        patch("songyan.workflows._nodes.load_version", new_callable=AsyncMock) as mock_ver,
        patch("songyan.workflows._nodes.load_chapter_goal", new_callable=AsyncMock) as mock_goal,
        patch(
            "songyan.workflows._nodes._load_chapter_repair_state",
            new_callable=AsyncMock,
            return_value=(2, False),
        ),
    ):
        mock_ver.return_value = version
        mock_goal.return_value = goal
        result = await quality_gate_node({
            "project_id": "p1",
            "chapter_number": 1,
            "current_version_id": "v-1",
            "_content_preservation_ratio": 0.50,
        })
    assert result["_quality_gate_passed"] is False
    assert any("preservation_too_low" in f for f in result["_quality_gate_failures"])
    assert result["status"] == "human_confirm"
    assert result["_needs_revision"] is False
    assert result["revision_round"] == 2


@pytest.mark.asyncio
async def test_quality_gate_word_count_too_low() -> None:
    """字数 < 0.80x → 标记 revision_needed."""
    version = MagicMock()
    version.word_count = 1500
    goal = MagicMock()
    goal.word_count_target = 3000
    with (
        patch("songyan.workflows._nodes.load_version", new_callable=AsyncMock) as mock_ver,
        patch("songyan.workflows._nodes.load_chapter_goal", new_callable=AsyncMock) as mock_goal,
        patch(
            "songyan.workflows._nodes._load_chapter_repair_state",
            new_callable=AsyncMock,
            return_value=(0, False),
        ),
    ):
        mock_ver.return_value = version
        mock_goal.return_value = goal
        result = await quality_gate_node({
            "project_id": "p1",
            "chapter_number": 1,
            "current_version_id": "v-1",
        })
    assert result["_quality_gate_passed"] is False
    assert any("word_count_too_low" in f for f in result["_quality_gate_failures"])
    assert result["status"] == "rule_auditing"
    assert result["_needs_revision"] is True


@pytest.mark.asyncio
async def test_quality_gate_preservation_too_low() -> None:
    """保留率 < 0.70 → 标记 revision_needed."""
    version = MagicMock()
    version.word_count = 3000
    goal = MagicMock()
    goal.word_count_target = 3000
    with (
        patch("songyan.workflows._nodes.load_version", new_callable=AsyncMock) as mock_ver,
        patch("songyan.workflows._nodes.load_chapter_goal", new_callable=AsyncMock) as mock_goal,
        patch(
            "songyan.workflows._nodes._load_chapter_repair_state",
            new_callable=AsyncMock,
            return_value=(0, False),
        ),
    ):
        mock_ver.return_value = version
        mock_goal.return_value = goal
        result = await quality_gate_node({
            "project_id": "p1",
            "chapter_number": 1,
            "current_version_id": "v-1",
            "_content_preservation_ratio": 0.60,
        })
    assert result["_quality_gate_passed"] is False
    assert any("preservation_too_low" in f for f in result["_quality_gate_failures"])
    assert result["status"] == "rule_auditing"
    assert result["_needs_revision"] is True


@pytest.mark.asyncio
async def test_quality_gate_new_issues_introduced() -> None:
    """新问题非空 → 停止自动修订，进入人工复核/失败态。"""
    version = MagicMock()
    version.word_count = 3000
    goal = MagicMock()
    goal.word_count_target = 3000
    with (
        patch("songyan.workflows._nodes.load_version", new_callable=AsyncMock) as mock_ver,
        patch("songyan.workflows._nodes.load_chapter_goal", new_callable=AsyncMock) as mock_goal,
        patch(
            "songyan.workflows._nodes._load_chapter_repair_state",
            new_callable=AsyncMock,
            return_value=(0, False),
        ),
    ):
        mock_ver.return_value = version
        mock_goal.return_value = goal
        result = await quality_gate_node({
            "project_id": "p1",
            "chapter_number": 1,
            "current_version_id": "v-1",
            "_new_issues_introduced": [{"issue_id": "i-1"}],
        })
    assert result["_quality_gate_passed"] is False
    assert any("new_issues_introduced" in f for f in result["_quality_gate_failures"])
    assert result["status"] == "human_review_required"
    assert result["_needs_revision"] is False
    assert result["_convergence_failed"] is True
    assert result["_skip_settlement"] is False
    assert result["_settlement_needs_human_review"] is True


@pytest.mark.asyncio
async def test_quality_gate_all_pass() -> None:
    """全部通过 → 进入 human_confirm."""
    version = MagicMock()
    version.word_count = 3000
    goal = MagicMock()
    goal.word_count_target = 3000
    with (
        patch("songyan.workflows._nodes.load_version", new_callable=AsyncMock) as mock_ver,
        patch("songyan.workflows._nodes.load_chapter_goal", new_callable=AsyncMock) as mock_goal,
    ):
        mock_ver.return_value = version
        mock_goal.return_value = goal
        result = await quality_gate_node({
            "current_version_id": "v-1",
            "_content_preservation_ratio": 0.95,
            "_new_issues_introduced": [],
        })
    assert result["_quality_gate_passed"] is True
    assert result["_quality_gate_failures"] == []
    assert result["status"] == "human_confirm"


# ---------------------------------------------------------------------------
# quality_gate_router
# ---------------------------------------------------------------------------


def test_quality_gate_router_rewrite() -> None:
    """状态为 rewrite → 路由到 rewrite."""
    assert quality_gate_router({"status": "rewrite"}) == "rewrite"


def test_quality_gate_router_revision_needed() -> None:
    """状态为 rule_auditing → 路由到 revision_needed."""
    assert quality_gate_router({"status": "rule_auditing"}) == "revision_needed"


def test_quality_gate_router_pass() -> None:
    """无异常 → 路由到 pass."""
    assert quality_gate_router({"status": "human_confirm"}) == "pass"


def test_quality_gate_router_error_fallback() -> None:
    """error 存在 → 路由到 pass（容错）."""
    assert quality_gate_router({"error": "something", "status": "rewrite"}) == "pass"


# ---------------------------------------------------------------------------
# human_confirm_router
# ---------------------------------------------------------------------------


def test_human_confirm_router_edit_audit() -> None:
    """edit 决策 → 路由到 edit_audit（重走 Audit）."""
    assert human_confirm_router({"human_decision": "edit"}) == "edit_audit"


def test_human_confirm_router_accept() -> None:
    """accept 决策 → 路由到 accept."""
    assert human_confirm_router({"human_decision": "accept"}) == "accept"


def test_human_confirm_router_word_count_guard() -> None:
    """word_count_guard 决策 → 路由到 rewrite."""
    assert human_confirm_router({"human_decision": "word_count_guard"}) == "word_count_guard"


# ---------------------------------------------------------------------------
# human_gate_node edit 分支
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_human_gate_edit_routes_to_audit() -> None:
    """edit 后创建新版本并返回 rule_auditing，不直接 accepted."""
    version = MagicMock()
    version.version_id = "v-parent"
    version.content = "original content"
    edited = "edited content"

    with (
        patch("songyan.workflows._nodes.load_version", new_callable=AsyncMock) as mock_ver,
        patch("songyan.workflows._nodes._open_editor", return_value=edited) as _,
        patch("songyan.workflows._nodes.ChapterVersionRepository", autospec=True) as mock_repo_cls,
        patch("songyan.workflows._nodes.ChapterHeadRepository", autospec=True) as mock_head_cls,
        patch("songyan.workflows._nodes.interrupt", return_value="edit") as _,
    ):
        mock_ver.return_value = version
        mock_repo = mock_repo_cls.return_value
        mock_repo.list_by_chapter = AsyncMock()
        mock_repo.get_next_version_number = AsyncMock(return_value=3)
        mock_repo.create = AsyncMock()
        mock_head = mock_head_cls.return_value
        mock_head.update = AsyncMock()

        result = await human_gate_node({
            "current_version_id": "v-parent",
            "project_id": "proj-1",
            "chapter_number": 1,
            "human_instructions": [],
            "revision_round": 2,
            "_revision_rebound": False,
        })

    assert result["human_decision"] == "edit"
    assert result["status"] == "rule_auditing"
    # 不应直接 accepted
    mock_head.update.assert_called_once()
    call_args = mock_head.update.call_args[0][0]
    assert call_args.status == "draft"
    assert call_args.accepted_version_id is None
    # audit 状态应被清空
    assert result.get("review_report_id") is None
    assert result.get("_has_critical") is False
    assert result.get("_new_issues_introduced") is None
    assert result.get("_content_preservation_ratio") is None
