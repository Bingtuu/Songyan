"""Phase 1 单章闭环工作流 — LangGraph 状态机编排."""

from __future__ import annotations

import os
from typing import Any, TypedDict, cast

import structlog
from langgraph.graph import END, StateGraph
from langgraph.types import (
    Command,  # 仅用于 resume_human_confirm，conditional_edges 路由函数不支持 Command
)

from songyan.exceptions import LLMBudgetExceededError, LLMError, LLMResponseParseError
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
    _best_score_card: dict[str, Any] | None
    _current_issues_count: int | None
    _current_overall_score: float | None
    _revision_rebound: bool
    # Task 098: 跨 rewrite 的累计修订次数（不被 rewrite 重置）
    _total_revision_count: int
    # 058c: 内容保留率（RevisionHandler 截断检测）
    _content_preservation_ratio: float | None
    # 058d: revision 引入的新问题（序列化后的 ReviewIssue dict 列表）
    _new_issues_introduced: list[dict[str, Any]] | None
    _new_issues_version_id: str | None
    _settlement_needs_human_review: bool
    _settlement_version_id: str | None
    _settlement_validation_status: str | None
    _settlement_validation_errors: list[str]
    # 073: 截断重写标记
    _was_rewritten: bool
    _rewrite_reason: str | None
    # 077b: BudgetPruner 是否触发过硬断言
    _budget_was_enforced: bool
    # Task 111b: ContextPackage 不入 state，仅保留轻量指标
    _context_metrics: dict[str, Any]
    # 078: ContinuityAuditor 预算状态
    _deferred_constraints: list[str]
    _continuity_budget_exhausted: bool
    # Task 100b: 质量门状态
    _quality_gate_passed: bool | None
    _quality_gate_failures: list[str]
    # 当前 gate 类型
    _current_gate: str | None
    # Task 106: 统一评分体系
    _score_card: dict[str, Any] | None
    # Task 107: 收敛护栏
    _convergence_failed: bool
    _skip_settlement: bool
    # P0/P1: 审查矛盾检测 — 保存上一轮 merged issues
    _prev_merged_issues: list[dict[str, Any]] | None
    # Task 138h: 前置 mandatory reference 检查是否通过（revision 反弹后使用）
    _mandatory_reference_check_passed: bool | None
    # 单章 pipeline 允许的最大 revision 轮次
    _max_revision_rounds: int
    # 本次 pipeline 执行的 thread id（便于 resume）
    thread_id: str | None


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
        return "error"
    needs = state.get("_needs_revision", False)
    rround = int(state.get("revision_round", 0))
    was_rewritten = state.get("_was_rewritten", False)

    # rewrite 是最后一次自动修复；重写后不再进入 revision，避免同章循环生成。
    if was_rewritten:
        return "pass"
    # 修订反弹后也不再进入 revision，避免无限循环（如 Ch100）。
    # Task 139f: 但若回滚目标版本仍存在 mandatory reference 未通过，必须强制重写，
    # 否则 critical orphan 会被直接 accept，触发 enforce health_low_p1_halt。
    if state.get("_revision_rebound"):
        if state.get("_mandatory_reference_check_passed") is False:
            logger.warning(
                "revision_router.rebound_with_mandatory_reference_failure",
                project_id=state.get("project_id"),
                chapter_number=state.get("chapter_number"),
                current_version_id=state.get("current_version_id"),
            )
            return "rewrite"
        return "pass"
    max_r = int(state.get("_max_revision_rounds", _MAX_REVISION_ROUNDS))
    # AG-04: 显式检查 revision 是否引入了新问题
    new_issues = state.get("_new_issues_introduced")
    if new_issues and rround >= max_r:
        return "rewrite"
    if needs and rround >= max_r:
        return "rewrite"
    if needs and rround < max_r:
        return "revise"
    return "pass"


def quality_gate_router(state: Phase1State) -> str:
    """质量门后路由.

    Task 100b: 三联检失败时拦截，避免异常版本进入 human_confirm。
    Task 116: 修复 status=rewrite 时忽略 QG 通过状态的问题。
    只有当 status=rewrite 且 QG 未通过时才返回 rewrite。
    """
    if state.get("error"):
        return "blocked"
    # Task 116: 检查 QG 通过状态，避免低分 rewrite 覆盖高分 QG passed best
    if state.get("status") == "rewrite" and not state.get("_quality_gate_passed", False):
        return "rewrite"
    if state.get("status") == "rule_auditing":
        return "revision_needed"
    if state.get("status") == "human_review_required":
        return "blocked"
    return "pass"


def rewrite_router(state: Phase1State) -> str:
    """rewrite 后路由.

    结构完整性失败时 rewrite_node 会回滚到 best version 并进入 human_confirm；
    结构完整时才继续审查重写稿。
    """
    if state.get("error"):
        return "error"
    if state.get("status") == "human_confirm":
        return "human_confirm"
    return "audit"


def stop_on_error_router(state: Phase1State) -> str:
    """Route sequential edges to END when a node returned a diagnostic error."""
    if state.get("error"):
        return "error"
    return "next"


def human_confirm_router(state: Phase1State) -> str:
    """human_confirm 后路由."""
    if state.get("error"):
        return "error"
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
    builder.add_node("goal_planner", goal_planner_node)  # type: ignore[type-var]
    builder.add_node("creative_director", creative_director_node)  # type: ignore[type-var]
    builder.add_node("context_manager", context_manager_node)  # type: ignore[type-var]
    builder.add_node("writer", writer_node)  # type: ignore[type-var]
    builder.add_node("rule_auditor", rule_auditor_node)  # type: ignore[type-var]
    builder.add_node("llm_auditor", llm_auditor_node)  # type: ignore[type-var]
    builder.add_node("review_merger", review_merger_node)  # type: ignore[type-var]
    builder.add_node("literary_auditor", literary_auditor_node)  # type: ignore[type-var]
    builder.add_node("revision_handler", revision_handler_node)  # type: ignore[type-var]
    builder.add_node("rewrite", rewrite_node)  # type: ignore[type-var]
    builder.add_node("quality_gate", quality_gate_node)  # type: ignore[type-var]
    builder.add_node("human_confirm", human_confirm_node)  # type: ignore[type-var]
    builder.add_node("settlement_extractor", settlement_extractor_node)  # type: ignore[type-var]

    # 顺序边。任何节点返回 error 时必须终止本章，避免错误状态继续
    # 流入后续节点并污染 clean rerun 样本。
    builder.set_entry_point("goal_planner")
    builder.add_conditional_edges(
        "goal_planner",
        stop_on_error_router,
        {"next": "creative_director", "error": END},
    )
    builder.add_conditional_edges(
        "creative_director",
        stop_on_error_router,
        {"next": "context_manager", "error": END},
    )
    builder.add_conditional_edges(
        "context_manager",
        stop_on_error_router,
        {"next": "writer", "error": END},
    )
    builder.add_conditional_edges(
        "writer",
        stop_on_error_router,
        {"next": "rule_auditor", "error": END},
    )
    builder.add_conditional_edges(
        "rule_auditor",
        stop_on_error_router,
        {"next": "llm_auditor", "error": END},
    )
    builder.add_conditional_edges(
        "llm_auditor",
        stop_on_error_router,
        {"next": "review_merger", "error": END},
    )
    builder.add_conditional_edges(
        "review_merger",
        stop_on_error_router,
        {"next": "literary_auditor", "error": END},
    )

    # 条件边：revision 路由（073 新增 rewrite 分支）
    # Task 100b: pass → quality_gate（不再直接进入 human_confirm）
    builder.add_conditional_edges(
        "literary_auditor",
        revision_router,
        {
            "revise": "revision_handler",
            "pass": "quality_gate",
            "rewrite": "rewrite",
            "error": END,
        },
    )

    # revision_handler → rule_auditor（循环）；修订失败时立即终止本章。
    builder.add_conditional_edges(
        "revision_handler",
        stop_on_error_router,
        {"next": "rule_auditor", "error": END},
    )

    # rewrite → 条件路由：结构失败回滚 best 后直接进入 human_confirm；
    # 结构完整的重写稿仍需 audit，但不再 revision。
    builder.add_conditional_edges(
        "rewrite",
        rewrite_router,
        {"audit": "rule_auditor", "human_confirm": "human_confirm", "error": END},
    )

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
        "metadata": {"project_id": project_id, "chapter_number": chapter_number},
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
        "_new_issues_version_id": None,
        "_settlement_needs_human_review": False,
        "_settlement_version_id": None,
        "_settlement_validation_status": None,
        "_settlement_validation_errors": [],
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
        "_prev_merged_issues": None,
        "_mandatory_reference_check_passed": None,
        "thread_id": None,
    }

    try:
        result = cast(Phase1State, await graph.ainvoke(initial_state, config=config))
        result["thread_id"] = thread_id
        return result
    except LLMBudgetExceededError:
        # 预算熔断必须原样传播到 phase2 的 pause 路径（_pause_run_for_auto_halt），
        # 不得包装为章节失败——否则 run 变 failed 而非 paused，丧失提额 resume 语义。
        raise
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
        return cast(Phase1State, await graph.ainvoke(Command(resume=decision), config=config))
    finally:
        if edited_content is not None:
            set_editor_callable(None)
