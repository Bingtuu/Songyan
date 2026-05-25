"""Workflow 节点函数 — LangGraph 状态机的各个节点."""

from __future__ import annotations

import os
import subprocess
import tempfile
from collections.abc import Callable
from typing import Any

import structlog
from langgraph.types import interrupt

from songyan.agents.creative_director import generate_creative_brief
from songyan.agents.goal_planner import define_chapter_goal
from songyan.agents.literary_auditor import run_literary_audit, save_literary_audit
from songyan.agents.llm_auditor import run_llm_audit, save_llm_audit
from songyan.agents.revision_handler import run_revision, save_revision_output
from songyan.agents.rule_auditor import run_rule_audit, save_rule_audit
from songyan.agents.settlement_extractor import apply_settlement, extract_settlement
from songyan.agents.summary_writer import write_chapter_summary
from songyan.agents.writer import write_chapter
from songyan.creative_modes.registry import load_creative_mode_profile
from songyan.db.context_repo import SummaryRepository
from songyan.db.repository import (
    ChapterGoalRepository,
    ChapterHeadRepository,
    ChapterVersionRepository,
    CharacterRepository,
)
from songyan.db.review_repo import (
    CreativeBriefRepository,
    LiteraryObservationRepository,
    ReviewReportRepository,
)
from songyan.genres.loader import load_genre_profile
from songyan.models import (
    ChapterHead,
    ChapterVersion,
)
from songyan.workflows._helpers import (
    assemble_context_package,
    load_chapter_goal,
    load_creative_brief,
    load_latest_audits,
    load_merged_report,
    load_project,
    load_version,
    new_id,
)
from songyan.workflows.review_merger import merge_reviews

logger = structlog.get_logger(__name__)

# =============================================================================
# Editor callable（可注入，用于测试）
# =============================================================================

_default_editor: Callable[[str], str] | None = None


def set_editor_callable(editor: Callable[[str], str] | None) -> None:
    global _default_editor
    _default_editor = editor


def _open_editor(content: str) -> str:
    if _default_editor is not None:
        return _default_editor(content)
    editor = os.environ.get("EDITOR", "notepad" if os.name == "nt" else "nano")
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(content)
        temp_path = f.name
    try:
        subprocess.run([editor, temp_path], check=True)
        with open(temp_path, encoding="utf-8") as f:
            return f.read()
    finally:
        os.unlink(temp_path)


# =============================================================================
# Pre-write 节点
# =============================================================================


async def goal_planner_node(state: dict[str, Any]) -> dict[str, Any]:
    project = await load_project(state["project_id"])
    if project is None:
        return {"error": f"Project not found: {state['project_id']}", "status": "error"}

    genre = load_genre_profile(project.genre_id)
    mode = load_creative_mode_profile(project.mode_id)
    goal = await define_chapter_goal(
        db=ChapterGoalRepository(),
        project_id=state["project_id"],
        project=project,
        genre_profile=genre,
        mode_profile=mode,
        chapter_number=state["chapter_number"],
    )
    goal_id = new_id("gp")
    await ChapterGoalRepository().create(goal, goal_id, state["project_id"])
    return {"chapter_goal_id": goal_id, "status": "creative_direction"}


async def creative_director_node(state: dict[str, Any]) -> dict[str, Any]:
    goal = await load_chapter_goal(state["chapter_goal_id"])
    if goal is None:
        return {"error": "ChapterGoal not found", "status": "error"}

    project = await load_project(state["project_id"])
    genre = load_genre_profile(project.genre_id)
    mode = load_creative_mode_profile(project.mode_id)
    characters = await CharacterRepository().list_by_project(state["project_id"])

    brief = await generate_creative_brief(
        db=CreativeBriefRepository(),
        project_id=state["project_id"],
        chapter_goal=goal,
        genre_profile=genre,
        mode_profile=mode,
        characters=characters,
    )
    brief_id = new_id("cb")
    await CreativeBriefRepository().create(
        brief, brief_id, state["project_id"], state["chapter_number"]
    )
    return {"creative_brief_id": brief_id, "status": "context_assembly"}


async def context_manager_node(state: dict[str, Any]) -> dict[str, Any]:
    goal = await load_chapter_goal(state["chapter_goal_id"])
    if goal is None:
        return {"error": "ChapterGoal not found", "status": "error"}
    return {"status": "writing"}


async def writer_node(state: dict[str, Any]) -> dict[str, Any]:
    goal = await load_chapter_goal(state["chapter_goal_id"])
    brief = None
    if state.get("creative_brief_id"):
        brief = await load_creative_brief(state["creative_brief_id"])
    ctx = await assemble_context_package(state["project_id"], state["chapter_number"], goal, brief)

    version = await write_chapter(
        db_version=ChapterVersionRepository(),
        db_head=ChapterHeadRepository(),
        project_id=state["project_id"],
        context_package=ctx,
        creative_brief_id=state.get("creative_brief_id"),
    )
    return {"current_version_id": version.version_id, "status": "rule_auditing"}


# =============================================================================
# Audit 节点
# =============================================================================


async def rule_auditor_node(state: dict[str, Any]) -> dict[str, Any]:
    version = await load_version(state["current_version_id"])
    if version is None:
        return {"error": "Version not found", "status": "error"}

    project = await load_project(state["project_id"])
    genre = load_genre_profile(project.genre_id) if project else None
    result = await run_rule_audit(
        content=version.content,
        genre_rules=genre.genre_rules if genre else None,
        word_count_target=version.word_count or 3000,
    )
    report_id = new_id("ra")
    await save_rule_audit(
        db=ReviewReportRepository(),
        version_id=version.version_id,
        result=result,
        report_id=report_id,
    )
    return {"_rule_report_id": report_id, "status": "llm_auditing"}


async def llm_auditor_node(state: dict[str, Any]) -> dict[str, Any]:
    version = await load_version(state["current_version_id"])
    if version is None:
        return {"error": "Version not found", "status": "error"}

    goal = await load_chapter_goal(state["chapter_goal_id"])
    brief = None
    if state.get("creative_brief_id"):
        brief = await load_creative_brief(state["creative_brief_id"])
    ctx = await assemble_context_package(state["project_id"], state["chapter_number"], goal, brief)

    result = await run_llm_audit(content=version.content, context_package=ctx)
    report_id = new_id("la")
    await save_llm_audit(
        db=ReviewReportRepository(),
        version_id=version.version_id,
        result=result,
        report_id=report_id,
    )
    return {"_llm_report_id": report_id, "status": "review_merging"}


async def review_merger_node(state: dict[str, Any]) -> dict[str, Any]:
    version = await load_version(state["current_version_id"])
    if version is None:
        return {"error": "Version not found", "status": "error"}

    rule_result, llm_result = await load_latest_audits(version.version_id)
    if rule_result is None or llm_result is None:
        return {"error": "Missing audit results", "status": "error"}

    merged = await merge_reviews(
        version_id=version.version_id,
        rule_result=rule_result,
        llm_result=llm_result,
        db=ReviewReportRepository(),
    )

    has_critical = merged.has_critical
    has_major = merged.has_major
    return {
        "review_report_id": f"mr-{version.version_id}",
        "_has_critical": has_critical,
        "_has_major": has_major,
        "_needs_revision": has_critical or has_major,
        "status": "literary_auditing",
    }


async def literary_auditor_node(state: dict[str, Any]) -> dict[str, Any]:
    version = await load_version(state["current_version_id"])
    if version is None:
        return {"error": "Version not found", "status": "error"}

    goal = await load_chapter_goal(state["chapter_goal_id"])
    brief = None
    if state.get("creative_brief_id"):
        brief = await load_creative_brief(state["creative_brief_id"])
    ctx = await assemble_context_package(state["project_id"], state["chapter_number"], goal, brief)

    result = await run_literary_audit(content=version.content, context_package=ctx)
    obs_id = new_id("lo")
    await save_literary_audit(
        db=LiteraryObservationRepository(),
        version_id=version.version_id,
        result=result,
        observation_id=obs_id,
    )
    return {"literary_observation_id": obs_id, "status": "revision_routing"}


# =============================================================================
# Revision 节点
# =============================================================================


async def revision_handler_node(state: dict[str, Any]) -> dict[str, Any]:
    version = await load_version(state["current_version_id"])
    if version is None:
        return {"error": "Version not found", "status": "error"}

    report = await load_merged_report(version.version_id)
    if report is None:
        return {"error": "Review report not found", "status": "error"}

    literary_result = None
    if state.get("literary_observation_id"):
        literary_result = await LiteraryObservationRepository().get_by_version(version.version_id)

    output, revised_content = await run_revision(
        content=version.content,
        report=report,
        literary_result=literary_result,
    )
    new_version_id = await save_revision_output(
        version_db=ChapterVersionRepository(),
        head_db=ChapterHeadRepository(),
        project_id=state["project_id"],
        chapter_number=state["chapter_number"],
        output=output,
        revised_content=revised_content,
        parent_version=version,
    )
    return {
        "current_version_id": new_version_id,
        "revision_round": state["revision_round"] + 1,
        "status": "rule_auditing",
    }


# =============================================================================
# Confirm & Settlement 节点
# =============================================================================


async def human_confirm_node(state: dict[str, Any]) -> dict[str, Any]:
    version = await load_version(state["current_version_id"])
    if version is None:
        return {"error": "Version not found", "status": "error"}

    decision = interrupt({
        "version_id": version.version_id,
        "content_preview": (
            version.content[:500] + "..."
            if len(version.content) > 500
            else version.content
        ),
        "options": ["accept", "edit", "reject", "back"],
    })

    if decision == "edit":
        edited_content = _open_editor(version.content)
        edited_version = ChapterVersion(
            version_id=new_id("v"),
            project_id=state["project_id"],
            chapter_number=state["chapter_number"],
            version_type="edited",
            content=edited_content,
            word_count=len(edited_content),
            parent_version_id=version.version_id,
        )
        await ChapterVersionRepository().create(edited_version)
        await ChapterHeadRepository().update(
            ChapterHead(
                project_id=state["project_id"],
                chapter_number=state["chapter_number"],
                current_version_id=edited_version.version_id,
                accepted_version_id=edited_version.version_id,
                status="accepted",
            )
        )
        return {
            "current_version_id": edited_version.version_id,
            "human_decision": "edit",
            "status": "settlement",
        }

    if decision == "accept":
        await ChapterHeadRepository().update(
            ChapterHead(
                project_id=state["project_id"],
                chapter_number=state["chapter_number"],
                current_version_id=version.version_id,
                accepted_version_id=version.version_id,
                status="accepted",
            )
        )
        return {"human_decision": "accept", "status": "settlement"}

    if decision == "reject":
        return {"human_decision": "reject", "revision_round": 0, "status": "goal_planning"}

    if decision == "back":
        return {"human_decision": "back", "revision_round": 0, "status": "writing"}

    return {"error": f"Unknown decision: {decision}", "status": "error"}


async def settlement_extractor_node(state: dict[str, Any]) -> dict[str, Any]:
    version = await load_version(state["current_version_id"])
    if version is None:
        return {"error": "Version not found", "status": "error"}

    project = await load_project(state["project_id"])
    genre = load_genre_profile(project.genre_id) if project else None

    settlement = await extract_settlement(
        content=version.content,
        project_id=state["project_id"],
        chapter_number=state["chapter_number"],
        version_id=version.version_id,
        genre_rules=genre.genre_rules if genre else None,
    )
    await apply_settlement(
        settlement=settlement,
        project_id=state["project_id"],
        chapter_number=state["chapter_number"],
        version_id=version.version_id,
    )
    await write_chapter_summary(
        content=version.content,
        settlement=settlement,
        project_id=state["project_id"],
        chapter_number=state["chapter_number"],
        db=SummaryRepository(),
    )
    return {
        "settlement_id": new_id("st"),
        "summary_id": new_id("sum"),
        "status": "done",
    }
