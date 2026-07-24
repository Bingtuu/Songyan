"""Tests for error_stage field — Task 070 JSONL diagnostics enhancement.

Verify that each node returns a meaningful stage name in `status` when error occurs,
so that phase2_graph can capture it as `error_stage` in the run log.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from songyan.exceptions import LLMError, LLMResponseParseError
from songyan.workflows._nodes import (
    context_manager_node,
    creative_director_node,
    goal_planner_node,
    human_gate_node,
    literary_auditor_node,
    llm_auditor_node,
    review_merger_node,
    revision_handler_node,
    rule_auditor_node,
    settlement_extractor_node,
)

# ---------------------------------------------------------------------------
# Pre-write nodes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_goal_planner_error_stage() -> None:
    """goal_planner_node returns status='goal_planner' on error."""
    with patch("songyan.workflows._nodes.load_project", new_callable=AsyncMock) as mock:
        mock.return_value = None
        result = await goal_planner_node({"project_id": "nonexistent"})
    assert result["status"] == "goal_planner"
    assert result["error"] is not None


@pytest.mark.asyncio
async def test_goal_planner_success_clears_stale_error() -> None:
    """A successful structured node must clear any previous diagnostic error."""
    project = MagicMock(genre_id="xuanhuan", mode_id="webnovel_intense")
    narrative_ctx = MagicMock(scheduled_items=[])
    repo = MagicMock()
    repo.create = AsyncMock()

    with (
        patch("songyan.workflows._nodes.load_project", new_callable=AsyncMock) as mock_project,
        patch("songyan.workflows._nodes.load_genre_profile", return_value=MagicMock()),
        patch("songyan.workflows._nodes.load_creative_mode_profile", return_value=MagicMock()),
        patch(
            "songyan.workflows._nodes.load_narrative_goal_context",
            new_callable=AsyncMock,
        ) as mock_narrative,
        patch("songyan.workflows._nodes.define_chapter_goal", new_callable=AsyncMock),
        patch("songyan.workflows._nodes.ChapterGoalRepository", return_value=repo),
    ):
        mock_project.return_value = project
        mock_narrative.return_value = narrative_ctx
        result = await goal_planner_node(
            {
                "project_id": "p-1",
                "chapter_number": 1,
                "mode_id": "webnovel_intense",
                "previous_summary": "",
                "error": "old parse error",
            }
        )

    assert result["status"] == "creative_direction"
    assert result["error"] is None


@pytest.mark.asyncio
async def test_creative_director_error_stage() -> None:
    """creative_director_node returns status='creative_director' on error."""
    with patch("songyan.workflows._nodes.load_chapter_goal", new_callable=AsyncMock) as mock:
        mock.return_value = None
        result = await creative_director_node({"chapter_goal_id": "missing"})
    assert result["status"] == "creative_director"
    assert result["error"] is not None


@pytest.mark.asyncio
async def test_creative_director_success_clears_stale_error() -> None:
    """CreativeDirector success must not leave an older LLM parse error in state."""
    project = MagicMock(genre_id="xuanhuan", mode_id="webnovel_intense")
    character_repo = MagicMock()
    character_repo.list_by_project = AsyncMock(return_value=[])
    setting_repo = MagicMock()
    setting_repo.list_by_project = AsyncMock(return_value=[])
    brief_repo = MagicMock()
    brief_repo.create = AsyncMock()

    with (
        patch("songyan.workflows._nodes.load_chapter_goal", new_callable=AsyncMock) as mock_goal,
        patch("songyan.workflows._nodes.load_project", new_callable=AsyncMock) as mock_project,
        patch("songyan.workflows._nodes.load_genre_profile", return_value=MagicMock()),
        patch("songyan.workflows._nodes.load_creative_mode_profile", return_value=MagicMock()),
        patch("songyan.workflows._nodes.CharacterRepository", return_value=character_repo),
        patch("songyan.workflows._nodes.SettingSnapshotRepository", return_value=setting_repo),
        patch(
            "songyan.workflows._nodes.load_narrative_goal_context",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "songyan.workflows._nodes.generate_creative_brief",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ),
        patch("songyan.workflows._nodes.CreativeBriefRepository", return_value=brief_repo),
        patch(
            "songyan.workflows._nodes.generate_dialogue_style_cards",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        mock_goal.return_value = MagicMock()
        mock_project.return_value = project
        result = await creative_director_node(
            {
                "project_id": "p-1",
                "chapter_number": 1,
                "chapter_goal_id": "goal-1",
                "mode_id": "webnovel_intense",
                "error": "CreativeDirector LLM call failed: parse error",
            }
        )

    assert result["status"] == "context_assembly"
    assert result["error"] is None


@pytest.mark.asyncio
async def test_context_manager_error_stage() -> None:
    """context_manager_node returns status='context_manager' on error."""
    with patch("songyan.workflows._nodes.load_chapter_goal", new_callable=AsyncMock) as mock:
        mock.return_value = None
        result = await context_manager_node({"chapter_goal_id": "missing"})
    assert result["status"] == "context_manager"
    assert result["error"] is not None


# ---------------------------------------------------------------------------
# Audit nodes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rule_auditor_error_stage() -> None:
    """rule_auditor_node returns status='rule_auditor' on error."""
    with patch("songyan.workflows._nodes.load_version", new_callable=AsyncMock) as mock:
        mock.return_value = None
        result = await rule_auditor_node({"current_version_id": "missing"})
    assert result["status"] == "rule_auditor"
    assert result["error"] is not None


@pytest.mark.asyncio
async def test_llm_auditor_error_stage() -> None:
    """llm_auditor_node returns status='llm_auditor' on error."""
    with patch("songyan.workflows._nodes.load_version", new_callable=AsyncMock) as mock:
        mock.return_value = None
        result = await llm_auditor_node({"current_version_id": "missing"})
    assert result["status"] == "llm_auditor"
    assert result["error"] is not None


@pytest.mark.asyncio
async def test_llm_auditor_llm_error_returns_diagnostic_state() -> None:
    """llm_auditor_node catches LLM failures instead of raising."""
    version = MagicMock()
    version.version_id = "v-1"
    version.content = "正文"
    with (
        patch("songyan.workflows._nodes.load_version", new_callable=AsyncMock) as mock_ver,
        patch("songyan.workflows._nodes._get_context_package", new_callable=AsyncMock) as mock_ctx,
        patch("songyan.workflows._nodes.run_llm_audit", new_callable=AsyncMock) as mock_audit,
    ):
        mock_ver.return_value = version
        mock_ctx.return_value = None
        mock_audit.side_effect = LLMResponseParseError("bad response")
        result = await llm_auditor_node({"current_version_id": "v-1"})
    assert result["status"] == "llm_auditor"
    assert result["error"] is not None


@pytest.mark.asyncio
async def test_llm_auditor_success_clears_stale_error() -> None:
    """LLMAuditor success must clear an older audit parse failure."""
    version = MagicMock()
    version.version_id = "v-1"
    version.content = "正文"

    with (
        patch("songyan.workflows._nodes.load_version", new_callable=AsyncMock) as mock_ver,
        patch("songyan.workflows._nodes._get_context_package", new_callable=AsyncMock) as mock_ctx,
        patch(
            "songyan.workflows._nodes.run_llm_audit",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ),
        patch("songyan.workflows._nodes.save_llm_audit", new_callable=AsyncMock),
    ):
        mock_ver.return_value = version
        mock_ctx.return_value = None
        result = await llm_auditor_node(
            {"current_version_id": "v-1", "error": "LLM audit failed: parse error"}
        )

    assert result["status"] == "review_merging"
    assert result["error"] is None


@pytest.mark.asyncio
async def test_review_merger_error_stage_missing_version() -> None:
    """review_merger_node returns status='review_merger' when version missing."""
    with patch("songyan.workflows._nodes.load_version", new_callable=AsyncMock) as mock:
        mock.return_value = None
        result = await review_merger_node({"current_version_id": "missing"})
    assert result["status"] == "review_merger"
    assert result["error"] is not None


@pytest.mark.asyncio
async def test_review_merger_error_stage_missing_audits() -> None:
    """review_merger_node returns status='review_merger' when audits missing."""
    version = AsyncMock()
    version.version_id = "v-1"
    with (
        patch("songyan.workflows._nodes.load_version", new_callable=AsyncMock) as mock_ver,
        patch("songyan.workflows._nodes.load_latest_audits", new_callable=AsyncMock) as mock_audits,
    ):
        mock_ver.return_value = version
        mock_audits.return_value = (None, None)
        result = await review_merger_node({"current_version_id": "v-1"})
    assert result["status"] == "review_merger"
    assert result["error"] is not None


@pytest.mark.asyncio
async def test_literary_auditor_error_stage() -> None:
    """literary_auditor_node returns status='literary_auditor' on error."""
    with patch("songyan.workflows._nodes.load_version", new_callable=AsyncMock) as mock:
        mock.return_value = None
        result = await literary_auditor_node({"current_version_id": "missing"})
    assert result["status"] == "literary_auditor"
    assert result["error"] is not None


@pytest.mark.asyncio
async def test_literary_auditor_llm_error_returns_diagnostic_state() -> None:
    """literary_auditor_node catches LLM failures instead of raising."""
    version = MagicMock()
    version.version_id = "v-1"
    version.content = "正文"
    with (
        patch("songyan.workflows._nodes.load_version", new_callable=AsyncMock) as mock_ver,
        patch("songyan.workflows._nodes._get_context_package", new_callable=AsyncMock) as mock_ctx,
        patch("songyan.workflows._nodes.run_literary_audit", new_callable=AsyncMock) as mock_audit,
    ):
        mock_ver.return_value = version
        mock_ctx.return_value = None
        mock_audit.side_effect = LLMError("api failed")
        result = await literary_auditor_node({"current_version_id": "v-1"})
    assert result["status"] == "literary_auditor"
    assert result["error"] is not None


# ---------------------------------------------------------------------------
# Revision & Settlement nodes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_revision_handler_error_stage_missing_version() -> None:
    """revision_handler_node returns status='revision_handler' when version missing."""
    with patch("songyan.workflows._nodes.load_version", new_callable=AsyncMock) as mock:
        mock.return_value = None
        result = await revision_handler_node({"current_version_id": "missing"})
    assert result["status"] == "revision_handler"
    assert result["error"] is not None


@pytest.mark.asyncio
async def test_revision_handler_error_stage_missing_report() -> None:
    """revision_handler_node returns status='revision_handler' when report missing."""
    version = AsyncMock()
    version.version_id = "v-1"
    with (
        patch("songyan.workflows._nodes.load_version", new_callable=AsyncMock) as mock_ver,
        patch("songyan.workflows._nodes.load_merged_report", new_callable=AsyncMock) as mock_report,
    ):
        mock_ver.return_value = version
        mock_report.return_value = None
        result = await revision_handler_node({"current_version_id": "v-1"})
    assert result["status"] == "revision_handler"
    assert result["error"] is not None


@pytest.mark.asyncio
async def test_settlement_extractor_error_stage() -> None:
    """settlement_extractor_node returns status='settlement_extractor' on error."""
    with patch("songyan.workflows._nodes.load_version", new_callable=AsyncMock) as mock:
        mock.return_value = None
        result = await settlement_extractor_node({"current_version_id": "missing"})
    assert result["status"] == "settlement_extractor"
    assert result["error"] is not None


# ---------------------------------------------------------------------------
# Human gate node
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_human_gate_error_stage_missing_version() -> None:
    """human_gate_node returns status='human_confirm' when version missing."""
    with patch("songyan.workflows._nodes.load_version", new_callable=AsyncMock) as mock:
        mock.return_value = None
        result = await human_gate_node({"current_version_id": "missing"})
    assert result["status"] == "human_confirm"
    assert result["error"] is not None


@pytest.mark.asyncio
async def test_human_gate_error_stage_unknown_decision() -> None:
    """human_gate_node returns status='human_confirm' on unknown decision."""
    version = AsyncMock()
    version.version_id = "v-1"
    version.content = "test"
    with patch("songyan.workflows._nodes.load_version", new_callable=AsyncMock) as mock:
        mock.return_value = version
        with patch("songyan.workflows._nodes.interrupt", return_value="invalid"):
            result = await human_gate_node({"current_version_id": "v-1"})
    assert result["status"] == "human_confirm"
    assert result["error"] is not None


@pytest.mark.asyncio
async def test_human_gate_options_do_not_expose_inject() -> None:
    """HumanGate 不暴露未接入路由的 inject 选项."""
    version = AsyncMock()
    version.version_id = "v-1"
    version.content = "test"
    with (
        patch(
            "songyan.workflows._nodes.load_version",
            new_callable=AsyncMock,
            return_value=version,
        ),
        patch("songyan.workflows._nodes.interrupt", return_value="reject") as mock_interrupt,
    ):
        await human_gate_node(
            {"current_version_id": "v-1", "project_id": "p1", "chapter_number": 1}
        )

    payload = mock_interrupt.call_args.args[0]
    assert "inject" not in payload["options"]
