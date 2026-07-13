"""Checkpoint interrupt/resume tests."""

from __future__ import annotations

import pytest

from songyan.db.repository import ChapterHeadRepository, ChapterVersionRepository
from songyan.workflows.phase1_graph import (
    resume_human_confirm,
    run_chapter_pipeline,
)

from .conftest import (
    brief_resp,
    goal_resp,
    literary_resp,
    llm_clean_resp,
    seed_project,
    settlement_resp,
    summary_resp,
    writer_resp,
)

pytestmark = pytest.mark.performance


@pytest.mark.asyncio
async def test_checkpoint_resume_accept(test_db, mock_call_llm) -> None:
    """Interrupt before human_confirm, then resume with accept."""
    project_id = await seed_project()
    thread_id = "thread-check-1"

    mock_call_llm.responses = [  # type: ignore[attr-defined]
        goal_resp(),
        brief_resp(),
        writer_resp(),
        llm_clean_resp(),
        literary_resp(),
        settlement_resp(),
        summary_resp(),
    ]

    # First invoke — stops at interrupt
    state1 = await run_chapter_pipeline(project_id, 2, thread_id=thread_id)
    assert "__interrupt__" in state1
    assert state1["project_id"] == project_id
    assert state1["chapter_number"] == 2
    version_id_before = state1["current_version_id"]
    assert version_id_before is not None

    # Resume with a brand-new graph instance (simulates process restart)
    state2 = await resume_human_confirm(thread_id, "accept")
    assert state2["status"] == "done"
    # P0-2: accept 创建新的 accepted 版本，current_version_id 指向新版本
    assert state2["current_version_id"] is not None

    # Verify DB state
    head = await ChapterHeadRepository().get(project_id, 2)
    assert head is not None
    assert head.accepted_version_id is not None

    versions = await ChapterVersionRepository().list_by_chapter(project_id, 2)
    assert len(versions) == 2  # draft + accepted


@pytest.mark.asyncio
async def test_checkpoint_resume_reject(test_db, mock_call_llm) -> None:
    """Interrupt before human_confirm, then resume with reject."""
    project_id = await seed_project()
    thread_id = "thread-check-2"

    mock_call_llm.responses = [  # type: ignore[attr-defined]
        goal_resp(),
        brief_resp(),
        writer_resp(),
        llm_clean_resp(),
        literary_resp(),
        # 2nd round after reject
        goal_resp(),
        brief_resp(),
        writer_resp(),
        llm_clean_resp(),
        literary_resp(),
    ]

    state1 = await run_chapter_pipeline(project_id, 2, thread_id=thread_id)
    assert "__interrupt__" in state1

    state2 = await resume_human_confirm(thread_id, "reject")
    # After reject the graph re-runs and interrupts again
    assert "__interrupt__" in state2
    assert state2["revision_round"] == 0


@pytest.mark.asyncio
async def test_checkpoint_state_consistency(test_db, mock_call_llm) -> None:
    """Resumed state matches pre-interrupt state for key fields."""
    project_id = await seed_project()
    thread_id = "thread-check-3"

    mock_call_llm.responses = [  # type: ignore[attr-defined]
        goal_resp(),
        brief_resp(),
        writer_resp(),
        llm_clean_resp(),
        literary_resp(),
        settlement_resp(),
        summary_resp(),
    ]

    state1 = await run_chapter_pipeline(project_id, 2, thread_id=thread_id)
    assert "__interrupt__" in state1

    # Snapshot pre-interrupt fields
    pre = {
        "project_id": state1["project_id"],
        "chapter_number": state1["chapter_number"],
        "current_version_id": state1["current_version_id"],
        "revision_round": state1["revision_round"],
        "mode_id": state1["mode_id"],
    }

    state2 = await resume_human_confirm(thread_id, "accept")
    # P0-2: accept 后创建新版本，恢复后的关键字段仍需一致
    assert state2["project_id"] == pre["project_id"]
    assert state2["chapter_number"] == pre["chapter_number"]
    assert state2["revision_round"] == pre["revision_round"]
    assert state2["mode_id"] == pre["mode_id"]
    assert state2["current_version_id"] is not None
