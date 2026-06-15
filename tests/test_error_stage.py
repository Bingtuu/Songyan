"""Tests for error_stage field — Task 070 JSONL diagnostics enhancement.

Verify that each node returns a meaningful stage name in `status` when error occurs,
so that phase2_graph can capture it as `error_stage` in the run log.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

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
async def test_creative_director_error_stage() -> None:
    """creative_director_node returns status='creative_director' on error."""
    with patch("songyan.workflows._nodes.load_chapter_goal", new_callable=AsyncMock) as mock:
        mock.return_value = None
        result = await creative_director_node({"chapter_goal_id": "missing"})
    assert result["status"] == "creative_director"
    assert result["error"] is not None


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
        with patch("songyan.workflows._nodes.interrupt", return_value="invalid") as mock_int:
            result = await human_gate_node({"current_version_id": "v-1"})
    assert result["status"] == "human_confirm"
    assert result["error"] is not None
