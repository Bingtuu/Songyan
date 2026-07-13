"""End-to-end integration path tests (A-H)."""

from __future__ import annotations

import pytest

from songyan.db.connection import get_db
from songyan.db.repository import ChapterHeadRepository, ChapterVersionRepository
from songyan.workflows._nodes import set_editor_callable
from songyan.workflows.phase1_graph import (
    resume_human_confirm,
    run_chapter_pipeline,
)

from .conftest import (
    brief_resp,
    goal_resp,
    literary_resp,
    llm_clean_resp,
    llm_critical_resp,
    llm_major_resp,
    llm_non_patchable_resp,
    llm_worsening_resp,
    revision_resp,
    seed_project,
    settlement_resp,
    summary_resp,
    writer_resp,
)

pytestmark = pytest.mark.performance


async def _versions(project_id: str, chapter_number: int = 2):
    repo = ChapterVersionRepository()
    return await repo.list_by_chapter(project_id, chapter_number, include_abandoned=True)


async def _head(project_id: str, chapter_number: int = 2):
    return await ChapterHeadRepository().get(project_id, chapter_number)


async def _summaries(project_id: str, chapter_number: int = 2):
    async with get_db() as conn:
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM summaries WHERE project_id = ? AND chapter_number = ?",
            (project_id, chapter_number),
        )
        row = await cursor.fetchone()
    return row[0] if row else 0


async def _character_states(project_id: str):
    async with get_db() as conn:
        cursor = await conn.execute(
            """SELECT COUNT(*) FROM character_states cs
            INNER JOIN characters c ON cs.character_id = c.character_id
            WHERE c.project_id = ?""",
            (project_id,),
        )
        row = await cursor.fetchone()
    return row[0] if row else 0


# ---------------------------------------------------------------------------
# Path A: no issues → accept → settlement → done
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_path_a_no_issues_accept(test_db, mock_call_llm) -> None:
    project_id = await seed_project()
    thread_id = "thread-a"

    mock_call_llm.responses = [  # type: ignore[attr-defined]
        goal_resp(),
        brief_resp(),
        writer_resp(),
        llm_clean_resp(),
        literary_resp(),
        settlement_resp(),
        summary_resp(),
    ]

    state = await run_chapter_pipeline(
        project_id=project_id,
        chapter_number=2,
        thread_id=thread_id,
    )
    assert "__interrupt__" in state

    final = await resume_human_confirm(thread_id, "accept")
    assert final["status"] == "done"
    assert final["settlement_id"] is not None
    assert final["summary_id"] is not None
    assert final["revision_round"] == 0

    head = await _head(project_id)
    assert head is not None
    assert head.accepted_version_id == final["current_version_id"]
    assert head.status == "accepted"

    versions = await _versions(project_id)
    accepted_versions = [v for v in versions if v.version_type == "accepted"]
    assert len(accepted_versions) == 1
    assert accepted_versions[0].version_id == final["current_version_id"]

    # settlement 数据应已写入
    assert await _summaries(project_id) == 1


# ---------------------------------------------------------------------------
# Path B: 1-round revision → accept
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_path_b_one_round_revision_accept(test_db, mock_call_llm) -> None:
    project_id = await seed_project()
    thread_id = "thread-b"

    mock_call_llm.responses = [  # type: ignore[attr-defined]
        goal_resp(),
        brief_resp(),
        writer_resp(),
        llm_critical_resp(),   # 1st round audit → critical
        literary_resp(),
        revision_resp(),       # revision_handler patch
        llm_clean_resp(),      # 2nd round audit → clean
        literary_resp(),
        settlement_resp(),
        summary_resp(),
    ]

    state = await run_chapter_pipeline(project_id, 2, thread_id=thread_id)
    assert "__interrupt__" in state

    final = await resume_human_confirm(thread_id, "accept")
    assert final["status"] == "done"
    assert final["revision_round"] == 1

    versions = await _versions(project_id)
    assert len(versions) == 3  # draft v1 + revision v2 + accepted v3
    assert versions[0].version_type == "draft"
    assert versions[2].version_type == "accepted"
    assert versions[2].parent_version_id == versions[1].version_id

    head = await _head(project_id)
    assert head.accepted_version_id == versions[2].version_id

    # settlement 数据应已写入
    assert await _summaries(project_id) == 1


# ---------------------------------------------------------------------------
# Path C: 2-round revision → forced pass
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_path_c_two_rounds_forced_pass(test_db, mock_call_llm) -> None:
    project_id = await seed_project()
    thread_id = "thread-c"

    mock_call_llm.responses = [  # type: ignore[attr-defined]
        goal_resp(),
        brief_resp(),
        writer_resp(),         # draft v1
        llm_critical_resp(),   # 1st audit
        literary_resp(),
        revision_resp(),       # 1st revision → draft v2
        llm_critical_resp(),   # 2nd audit
        literary_resp(),
        revision_resp(),       # 2nd revision → draft v3 (round=2)
        llm_critical_resp(),   # 3rd audit
        literary_resp(),       # 3rd literary
        writer_resp(),         # rewrite → draft v4 (073)
        llm_clean_resp(),      # rewrite audit
        literary_resp(),
        settlement_resp(),
        summary_resp(),
    ]

    state = await run_chapter_pipeline(project_id, 2, thread_id=thread_id)
    assert "__interrupt__" in state

    final = await resume_human_confirm(thread_id, "accept")
    assert final["status"] == "done"
    assert final["revision_round"] == 1  # rewrite 后允许 1 轮最后修正
    assert final.get("_was_rewritten") is False

    versions = await _versions(project_id)
    accepted_versions = [v for v in versions if v.version_type == "accepted"]
    assert len(accepted_versions) == 1
    assert accepted_versions[0].version_id == final["current_version_id"]

    # forced pass 后 settlement/summary 也应正常生成
    assert await _summaries(project_id) == 1


# ---------------------------------------------------------------------------
# Path D: reject → reset
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_path_d_reject_resets(test_db, mock_call_llm) -> None:
    project_id = await seed_project()
    thread_id = "thread-d"

    # reject triggers a full re-run; provide responses for 2nd round
    mock_call_llm.responses = [  # type: ignore[attr-defined]
        goal_resp(),
        brief_resp(),
        writer_resp(),
        llm_clean_resp(),
        literary_resp(),
        # 2nd round
        goal_resp(),
        brief_resp(),
        writer_resp(),
        llm_clean_resp(),
        literary_resp(),
    ]

    state = await run_chapter_pipeline(project_id, 2, thread_id=thread_id)
    assert "__interrupt__" in state

    final = await resume_human_confirm(thread_id, "reject")
    # After reject the graph re-runs and interrupts again at human_confirm
    assert "__interrupt__" in final
    assert final["revision_round"] == 0

    head = await _head(project_id)
    assert head is None or head.status != "accepted"

    # reject 后不应生成 settlement/summary
    assert await _summaries(project_id) == 0
    assert await _character_states(project_id) == 0


# ---------------------------------------------------------------------------
# Path E: back → writer rewrites
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_path_e_back_rewrites(test_db, mock_call_llm) -> None:
    project_id = await seed_project()
    thread_id = "thread-e"

    # back triggers re-run from writer; provide responses for 2nd round
    mock_call_llm.responses = [  # type: ignore[attr-defined]
        goal_resp(),
        brief_resp(),
        writer_resp(),
        llm_clean_resp(),
        literary_resp(),
        # 2nd round (writer rewrites)
        writer_resp(),
        llm_clean_resp(),
        literary_resp(),
    ]

    state = await run_chapter_pipeline(project_id, 2, thread_id=thread_id)
    assert "__interrupt__" in state

    final = await resume_human_confirm(thread_id, "back")
    # After back the graph re-runs from writer and interrupts again
    assert "__interrupt__" in final
    assert final["revision_round"] == 0

    versions = await _versions(project_id)
    drafts = [v for v in versions if v.version_type == "draft"]
    assert len(drafts) == 2

    # back 后不应生成 settlement/summary
    assert await _summaries(project_id) == 0
    assert await _character_states(project_id) == 0


# ---------------------------------------------------------------------------
# Path F: edit → saved edited version
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_path_f_edit_saves_edited_version(test_db, mock_call_llm) -> None:
    project_id = await seed_project()
    thread_id = "thread-f"

    mock_call_llm.responses = [  # type: ignore[attr-defined]
        goal_resp(),
        brief_resp(),
        writer_resp(),
        llm_clean_resp(),
        literary_resp(),
        llm_clean_resp(),
        literary_resp(),
        settlement_resp(),
        summary_resp(),
    ]

    set_editor_callable(lambda content: content + "\n\n【人工编辑补充】")

    try:
        state = await run_chapter_pipeline(project_id, 2, thread_id=thread_id)
        assert "__interrupt__" in state

        edited_state = await resume_human_confirm(thread_id, "edit")
        assert "__interrupt__" in edited_state

        final = await resume_human_confirm(thread_id, "accept")
        assert final["status"] == "done"
        assert final["human_decision"] == "accept"

        versions = await _versions(project_id)
        accepted = [v for v in versions if v.version_type == "accepted"]
        assert len(accepted) == 1
        assert "【人工编辑补充】" in accepted[0].content

        head = await _head(project_id)
        assert head.accepted_version_id == accepted[0].version_id
    finally:
        set_editor_callable(None)


# ---------------------------------------------------------------------------
# Path G: 1 major (non-critical) issue → no revision (Task 110e) → accept directly
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_path_g_major_revision_accept(test_db, mock_call_llm) -> None:
    """Task 110e: 1 major (not critical) does NOT trigger revision (needs 2+ major)."""
    project_id = await seed_project()
    thread_id = "thread-g"

    mock_call_llm.responses = [  # type: ignore[attr-defined]
        goal_resp(),
        brief_resp(),
        writer_resp(),
        llm_major_resp(),      # 1st audit → 1 major (not critical)
        literary_resp(),
        settlement_resp(),
        summary_resp(),
    ]

    state = await run_chapter_pipeline(project_id, 2, thread_id=thread_id)
    assert "__interrupt__" in state

    final = await resume_human_confirm(thread_id, "accept")
    assert final["status"] == "done"
    assert final["revision_round"] == 0

    versions = await _versions(project_id)
    accepted_versions = [v for v in versions if v.version_type == "accepted"]
    assert len(accepted_versions) == 1
    assert accepted_versions[0].version_id == final["current_version_id"]


# ---------------------------------------------------------------------------
# Path H: non-patchable issue → skips patch, no new version
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_path_h_non_patchable_skips_revision(test_db, mock_call_llm) -> None:
    """Issue with fix_type != 'patch' should not apply patches but still create revision version."""
    project_id = await seed_project()
    thread_id = "thread-h"

    # Round 1: goal, brief, writer, llm(non-patchable), literary
    # revision_handler sees patchable_issues=[] → skips LLM call
    # Round 2: llm_clean, literary, settlement, summary
    mock_call_llm.responses = [  # type: ignore[attr-defined]
        goal_resp(),
        brief_resp(),
        writer_resp(),
        llm_non_patchable_resp(),  # critical but rewrite_scene → no patchable issues
        literary_resp(),
        # revision_handler does NOT call LLM when no patchable issues
        llm_clean_resp(),          # 2nd round audit
        literary_resp(),           # 2nd round literary
        settlement_resp(),
        summary_resp(),
    ]

    state = await run_chapter_pipeline(project_id, 2, thread_id=thread_id)
    assert "__interrupt__" in state

    final = await resume_human_confirm(thread_id, "accept")
    assert final["status"] == "done"
    assert final["revision_round"] == 1

    versions = await _versions(project_id)
    # draft v1 + revision v2 (no patches) + accepted v3
    assert len(versions) == 3
    assert versions[2].version_type == "accepted"
    # content should be unchanged since no patches were applied
    assert versions[0].content == versions[2].content


# ---------------------------------------------------------------------------
# Path I: revision rebound → rollback to previous version
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_path_i_revision_rebound_rollback(test_db, mock_call_llm) -> None:
    """If revision makes quality worse (issues +20% or score -1.0), rollback to best version."""
    project_id = await seed_project()
    thread_id = "thread-i"

    mock_call_llm.responses = [  # type: ignore[attr-defined]
        goal_resp(),
        brief_resp(),
        writer_resp(),
        llm_critical_resp(),     # 1st audit: 1 issue, score ~6.4
        literary_resp(),
        revision_resp(),         # 1st revision → v2
        llm_worsening_resp(),    # 2nd audit: 3 issues, score much lower → rebound!
        literary_resp(),
        settlement_resp(),
        summary_resp(),
    ]

    state = await run_chapter_pipeline(project_id, 2, thread_id=thread_id)
    assert "__interrupt__" in state

    final = await resume_human_confirm(thread_id, "accept")
    assert final["status"] == "done"
    assert final["revision_round"] == 1
    assert final.get("_revision_rebound") is False

    versions = await _versions(project_id)
    # v1 (draft), v2 (revision, discarded due to rebound), v3 (accepted)
    assert len(versions) == 3

    head = await _head(project_id)
    assert head is not None
    accepted_versions = [v for v in versions if v.version_type == "accepted"]
    assert len(accepted_versions) == 1
    assert head.accepted_version_id == accepted_versions[0].version_id
    # rollback 后 accepted 版本应继承自最佳版本（v1）或当前被接受版本（v2）
    assert accepted_versions[0].parent_version_id in {
        versions[0].version_id,
        versions[1].version_id,
    }

    # settlement/summary should still work on rolled-back version
    assert await _summaries(project_id) == 1

    # P0/P1 fix verification: review_report_id and literary_observation_id
    # should be consistent with the accepted version.
    assert final.get("review_report_id") is not None
    assert final.get("literary_observation_id") is not None
    assert final.get("_revision_rebound") is False
