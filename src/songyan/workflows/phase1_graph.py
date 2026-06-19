"""Phase 1 单章闭环工作流 — LangGraph 状态机编排."""

from __future__ import annotations

import os
from typing import Any, TypedDict

import structlog
from langgraph.graph import END, StateGraph
from langgraph.types import (
    Command,  # 仅用于 resume_human_confirm，conditional_edges 路由函数不支持 Command
)

from songyan.exceptions import LLMError, LLMResponseParseError
from songyan.workflows._nodes import (
    context_manager_node,
    creative_director_node,
    goal_planner_node,
    human_confirm_node,
    literary_auditor_node,
    llm_auditor_node,
    quality_gate_node,
    review_merger_node,
    revision_handler_node,
    rewrite_node,
    rule_auditor_node,
    set_editor_callable,
    settlement_extractor_node,
    writer_node,
)
from songyan.workflows.checkpointer import (
    get_checkpointer as _get_checkpointer,
)
from songyan.workflows.checkpointer import (
    reset_checkpointer as _reset_checkpointer_instance,
)

# 允许通过环境变量控制最大 revision 轮次（验证/测试用）
_MAX_REVISION_ROUNDS = int(os.environ.get("SONGYAN_MAX_REVISION_ROUNDS", "2"))

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
    context_snapshot_id: str | None
    current_version_id: str | None
    review_report_id: str | None
    literary_observation_id: str | None
    settlement_id: str | None
    summary_id: str | None
    revision_round: int
    status: str
    human_decision: str | None
    error: str | None
    # 跨章状态传递
    previous_summary: str
    # 以下为小的路由控制标志（非业务对象）
    _needs_revision: bool
    _has_critical: bool
    _has_major: bool
    # Revision 反弹检测字段
    _best_issues_count: int | None
    _best_overall_score: float | None
    _best_version_id: str | None
    _best_report_id: str | None
    _best_score_card: dict | None
    _current_issues_count: int | None
    _current_overall_score: float | None
    _revision_rebound: bool
    # Task 098: 跨 rewrite 的累计修订次数（不被 rewrite 重置）
    _total_revision_count: int = 0
    # 058c: 内容保留率（RevisionHandler 截断检测）
    _content_preservation_ratio: float | None
    # 058d: revision 引入的新问题（序列化后的 ReviewIssue dict 列表）
    _new_issues_introduced: list[dict] | None
    _settlement_needs_human_review: bool
    # 073: 截断重写标记
    _was_rewritten: bool
    _rewrite_reason: str | None
    # 077b: BudgetPruner 是否触发过硬断言
    _budget_was_enforced: bool
    # Task 111b: ContextPackage 不入 state，仅保留轻量指标
    _context_metrics: dict
    # 078: ContinuityAuditor 预算状态
    _deferred_constraints: list[str]
    _continuity_budget_exhausted: bool
    # Task 100b: 质量门状态
    _quality_gate_passed: bool | None
    _quality_gate_failures: list[str]
    # 当前 gate 类型
    _current_gate: str | None
    # Task 106: 统一评分体系
    _score_card: dict | None
    # Task 107: 收敛护栏
    _convergence_failed: bool
    _skip_settlement: bool
    # P0/P1: 审查矛盾检测 — 保存上一轮 merged issues
    _prev_merged_issues: list[dict] | None


# =============================================================================
# 路由函数
# =============================================================================


def revision_router(state: Phase1State) -> str:
    """revision 路由：判断是否需要修订或重写.

    策略：
    - Round 0-1: 有 critical/major → revise
    - Round 2: 有 critical/major 且未重写 → rewrite（整章重写）
    - 已重写: 无论是否有 issue 都 pass（避免无限循环）
    """
# SEC-01: 入口校验 — 确保必需字段合法（TypedDict 无运行时校验的补偿）
    errors: list[str] = []
    _project_id = state.get("project_id")
    if not _project_id or not isinstance(_project_id, str) or not _project_id.strip():
        errors.append("project_id 必须为非空字符串")
    _chapter_number = state.get("chapter_number")
    if not isinstance(_chapter_number, int) or _chapter_number < 1:
        errors.append(f"chapter_number 必须为 >=1 的整数，实际: {repr(_chapter_number)}")
    _mode_id = state.get("mode_id") or ""
    if not _mode_id or not isinstance(_mode_id, str) or not _mode_id.strip():
        errors.append("mode_id 必须为非空字符串")
    if errors:
        raise ValueError(f"Pipeline 输入校验失败: {'; '.join(errors)}")

    if state.get("error"):
        return "pass"
    needs = state.get("_needs_revision", False)
    rround = state.get("revision_round", 0)
    was_rewritten = state.get("_was_rewritten", False)

    # rewrite 是最后一次自动修复；重写后不再进入 revision，避免同章循环生成。
    if was_rewritten:
        return "pass"
    # 修订反弹后也不再进入 revision，避免无限循环（如 Ch100）
    if state.get("_revision_rebound"):
        return "pass"
    max_r = state.get("_max_revision_rounds", _MAX_REVISION_ROUNDS)
    if needs and rround >= max_r:
        return "rewrite"
    if needs and rround < max_r:
        return "revise"
    return "pass"


def quality_gate_router(state: Phase1State) -> str:
    """质量门后路由.

    Task 100b: 三联检失败时拦截，避免异常版本进入 human_confirm。
    """
    if state.get("error"):
        return "pass"
    status = state.get("status", "")
    if status == "rewrite":
        return "rewrite"
    if status == "rule_auditing":
        return "revision_needed"
    if status == "human_review_required":
        return "blocked"
    return "pass"


def human_confirm_router(state: Phase1State) -> str:
    """human_confirm 后路由."""
    decision = state.get("human_decision")
    if decision == "accept" or decision is None:
        return "accept"
    # Task 100b: edit 后重走 Audit 流程
    if decision == "edit":
        return "edit_audit"
    if decision == "reject":
        return "reject"
    if decision == "back":
        return "back"
    # Task 098: Accept 路径字数守卫 → 路由到 rewrite
    if decision == "word_count_guard":
        return "word_count_guard"
    # 未知决策 — 记录警告并进入错误处理路径
    logger.warning("human_confirm.unknown_decision", decision=decision)
    return "error"


# =============================================================================
# 图编译
# =============================================================================


# 模块级编译后图缓存（避免重复编译）
_compiled_graph: Any | None = None

async def reset_checkpointer() -> None:
    """重置共享 checkpointer 和编译后图缓存（测试用）."""
    global _compiled_graph
    await _reset_checkpointer_instance()
    _compiled_graph = None


async def build_phase1_graph() -> Any:
    global _compiled_graph
    if _compiled_graph is not None:
        return _compiled_graph
    """构建 Phase 1 工作流图.

    Returns:
        编译后的 LangGraph 图（含 AsyncSqliteSaver checkpoint）
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
    builder.add_node("rewrite", rewrite_node)
    builder.add_node("quality_gate", quality_gate_node)
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

    # 条件边：revision 路由（073 新增 rewrite 分支）
    # Task 100b: pass → quality_gate（不再直接进入 human_confirm）
    builder.add_conditional_edges(
        "literary_auditor",
        revision_router,
        {"revise": "revision_handler", "pass": "quality_gate", "rewrite": "rewrite"},
    )

    # revision_handler → rule_auditor（循环）
    builder.add_edge("revision_handler", "rule_auditor")

    # rewrite → rule_auditor（重写后仍需 audit，但不再 revision）
    builder.add_edge("rewrite", "rule_auditor")

    # Task 100b: 质量门条件边
    builder.add_conditional_edges(
        "quality_gate",
        quality_gate_router,
        {
            "pass": "human_confirm",
            "rewrite": "rewrite",
            "revision_needed": "revision_handler",
            "blocked": END,
        },
    )

    # 条件边：human_confirm 路由
    # Task 100b: edit → rule_auditor（重走 Audit）
    builder.add_conditional_edges(
        "human_confirm",
        human_confirm_router,
        {
            "accept": "settlement_extractor",
            "edit_audit": "rule_auditor",
            "reject": "goal_planner",
            "back": "writer",
            "word_count_guard": "rewrite",
            "error": END,
        },
    )

    # settlement_extractor → 结束
    builder.add_edge("settlement_extractor", END)

    _compiled_graph = builder.compile(checkpointer=await _get_checkpointer())
    return _compiled_graph


# =============================================================================
# 公共 API
# =============================================================================


async def run_chapter_pipeline(
    project_id: str,
    chapter_number: int,
    mode_id: str = "webnovel",
    thread_id: str | None = None,
    max_revision_rounds: int = 2,
    previous_summary: str = "",
) -> Phase1State:
    """运行完整单章闭环工作流.

    返回最终状态。如果 human_confirm 中断，返回含 __interrupt__ 的状态。
    外部通过 resume_human_confirm() 恢复。
    """
    from songyan.workflows._helpers import new_id

    graph = await build_phase1_graph()
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
        "context_snapshot_id": None,
        "current_version_id": None,
        "review_report_id": None,
        "literary_observation_id": None,
        "settlement_id": None,
        "summary_id": None,
        "revision_round": 0,
        "status": "idle",
        "human_decision": None,
        "error": None,
        "previous_summary": previous_summary,
        "_needs_revision": False,
        "_has_critical": False,
        "_has_major": False,
        "_best_issues_count": None,
        "_best_overall_score": None,
        "_best_version_id": None,
        "_best_report_id": None,
        "_best_score_card": None,
        "_current_issues_count": None,
        "_current_overall_score": None,
        "_revision_rebound": False,
        "_content_preservation_ratio": None,
        "_new_issues_introduced": None,
        "_settlement_needs_human_review": False,
        "_was_rewritten": False,
        "_rewrite_reason": None,
        "_budget_was_enforced": False,
        "_context_metrics": {},
        "_deferred_constraints": [],
        "_continuity_budget_exhausted": False,
        "_total_revision_count": 0,
        "_quality_gate_passed": None,
        "_quality_gate_failures": [],
        "_current_gate": None,
        "_score_card": None,
        "_convergence_failed": False,
        "_max_revision_rounds": max_revision_rounds,
        "_skip_settlement": False,
    }

    try:
        result = await graph.ainvoke(initial_state, config=config)
        result["thread_id"] = thread_id
        return result
    except (LLMError, LLMResponseParseError) as exc:
        logger.error(
            "run_chapter_pipeline.llm_failed",
            error=str(exc),
            project_id=project_id,
            chapter_number=chapter_number,
        )
        return {
            **initial_state,
            "error": f"Pipeline LLM failure: {exc}",
            "status": "failed",
            "thread_id": thread_id,
        }
    except Exception as exc:
        logger.error(
            "run_chapter_pipeline.failed",
            error=str(exc),
            project_id=project_id,
            chapter_number=chapter_number,
        )
        return {
            **initial_state,
            "error": f"Pipeline failure: {exc}",
            "status": "failed",
            "thread_id": thread_id,
        }


async def resume_human_confirm(
    thread_id: str,
    decision: str,
    edited_content: str | None = None,
) -> Phase1State:
    """恢复 human_confirm 中断，传入用户决策."""
    graph = await build_phase1_graph()
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 100,
    }
    if edited_content is not None:
        set_editor_callable(lambda _c: edited_content)
    try:
        return await graph.ainvoke(Command(resume=decision), config=config)
    finally:
        if edited_content is not None:
            set_editor_callable(None)

