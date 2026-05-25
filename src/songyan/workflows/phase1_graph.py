"""Phase 1 单章闭环工作流 — LangGraph 状态机编排."""

from __future__ import annotations

from typing import Any, TypedDict

import structlog
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.types import Command

from songyan.workflows._nodes import (
    context_manager_node,
    creative_director_node,
    goal_planner_node,
    human_confirm_node,
    literary_auditor_node,
    llm_auditor_node,
    review_merger_node,
    revision_handler_node,
    rule_auditor_node,
    set_editor_callable,
    settlement_extractor_node,
    writer_node,
)

logger = structlog.get_logger(__name__)


# =============================================================================
# State 定义
# =============================================================================


class Phase1State(TypedDict):
    """LangGraph 状态 — 只存 ID 和控制字段（铁律）."""

    project_id: str
    chapter_number: int
    mode_id: str
    chapter_goal_id: str | None
    creative_brief_id: str | None
    current_version_id: str | None
    review_report_id: str | None
    literary_observation_id: str | None
    settlement_id: str | None
    summary_id: str | None
    revision_round: int
    status: str
    human_decision: str | None
    error: str | None
    # 以下为小的路由控制标志（非业务对象）
    _needs_revision: bool
    _has_critical: bool
    _has_major: bool


# =============================================================================
# 路由函数
# =============================================================================


def revision_router(state: Phase1State) -> str:
    """revision 路由：判断是否需要修订."""
    if state.get("error"):
        return "pass"
    needs = state.get("_needs_revision", False)
    rround = state.get("revision_round", 0)
    if needs and rround < 2:
        return "revise"
    return "pass"


def human_confirm_router(state: Phase1State) -> str:
    """human_confirm 后路由."""
    decision = state.get("human_decision")
    if decision == "accept":
        return "accept"
    if decision == "edit":
        return "edit"
    if decision == "reject":
        return "reject"
    if decision == "back":
        return "back"
    return "accept"


# =============================================================================
# 图编译
# =============================================================================


def build_phase1_graph() -> Any:
    """构建 Phase 1 工作流图.

    Returns:
        编译后的 LangGraph 图（含 MemorySaver checkpoint）
    """
    builder = StateGraph(Phase1State)

    # 注册节点
    builder.add_node("goal_planner", goal_planner_node)
    builder.add_node("creative_director", creative_director_node)
    builder.add_node("context_manager", context_manager_node)
    builder.add_node("writer", writer_node)
    builder.add_node("rule_auditor", rule_auditor_node)
    builder.add_node("llm_auditor", llm_auditor_node)
    builder.add_node("review_merger", review_merger_node)
    builder.add_node("literary_auditor", literary_auditor_node)
    builder.add_node("revision_handler", revision_handler_node)
    builder.add_node("human_confirm", human_confirm_node)
    builder.add_node("settlement_extractor", settlement_extractor_node)

    # 顺序边
    builder.set_entry_point("goal_planner")
    builder.add_edge("goal_planner", "creative_director")
    builder.add_edge("creative_director", "context_manager")
    builder.add_edge("context_manager", "writer")
    builder.add_edge("writer", "rule_auditor")
    builder.add_edge("rule_auditor", "llm_auditor")
    builder.add_edge("llm_auditor", "review_merger")
    builder.add_edge("review_merger", "literary_auditor")

    # 条件边：revision 路由
    builder.add_conditional_edges(
        "literary_auditor",
        revision_router,
        {"revise": "revision_handler", "pass": "human_confirm"},
    )

    # revision_handler → rule_auditor（循环）
    builder.add_edge("revision_handler", "rule_auditor")

    # 条件边：human_confirm 路由
    builder.add_conditional_edges(
        "human_confirm",
        human_confirm_router,
        {
            "accept": "settlement_extractor",
            "edit": "settlement_extractor",
            "reject": "goal_planner",
            "back": "writer",
        },
    )

    # settlement_extractor → 结束
    builder.add_edge("settlement_extractor", END)

    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)


# =============================================================================
# 公共 API
# =============================================================================


async def run_chapter_pipeline(
    project_id: str,
    chapter_number: int,
    mode_id: str = "webnovel",
    thread_id: str | None = None,
) -> Phase1State:
    """运行完整单章闭环工作流.

    返回最终状态。如果 human_confirm 中断，返回含 __interrupt__ 的状态。
    外部通过 resume_human_confirm() 恢复。
    """
    from songyan.workflows._helpers import new_id

    graph = build_phase1_graph()
    if thread_id is None:
        thread_id = new_id("thread")

    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 100,
    }

    initial_state: Phase1State = {
        "project_id": project_id,
        "chapter_number": chapter_number,
        "mode_id": mode_id,
        "chapter_goal_id": None,
        "creative_brief_id": None,
        "current_version_id": None,
        "review_report_id": None,
        "literary_observation_id": None,
        "settlement_id": None,
        "summary_id": None,
        "revision_round": 0,
        "status": "idle",
        "human_decision": None,
        "error": None,
        "_needs_revision": False,
        "_has_critical": False,
        "_has_major": False,
    }

    return await graph.ainvoke(initial_state, config=config)


async def resume_human_confirm(
    thread_id: str,
    decision: str,
    edited_content: str | None = None,
) -> Phase1State:
    """恢复 human_confirm 中断，传入用户决策."""
    graph = build_phase1_graph()
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 100,
    }
    if edited_content is not None:
        set_editor_callable(lambda _c: edited_content)
    return await graph.ainvoke(Command(resume=decision), config=config)
