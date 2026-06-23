"""Workflow 节点函数 — LangGraph 状态机的各个节点."""

from __future__ import annotations

import os
import subprocess
import tempfile
import uuid
from collections.abc import Callable
from typing import Any

import structlog
from langgraph.types import interrupt

from songyan.agents.context_manager import _build_genre_rules
from songyan.agents.creative_director import generate_creative_brief, generate_dialogue_style_cards
from songyan.agents.goal_planner import define_chapter_goal
from songyan.agents.literary_auditor import run_literary_audit, save_literary_audit
from songyan.agents.llm_auditor import run_llm_audit, save_llm_audit
from songyan.agents.revision_handler import (
    run_revision,
    save_revision_output,
)
from songyan.agents.rule_auditor import run_rule_audit, save_rule_audit
from songyan.agents.settlement_extractor import apply_settlement, extract_settlement
from songyan.agents.summary_writer import write_chapter_summary
from songyan.agents.writer import write_chapter
from songyan.creative_modes.registry import load_creative_mode_profile
from songyan.db.connection import get_db
from songyan.db.context_repo import SummaryRepository
from songyan.db.repository import (
    ChapterGoalRepository,
    ChapterHeadRepository,
    ChapterVersionRepository,
    CharacterRepository,
    ContextSnapshotRepository,
)
from songyan.db.review_repo import (
    CreativeBriefRepository,
    LiteraryObservationRepository,
    ReviewReportRepository,
)
from songyan.db.settlement_repo import SettingSnapshotRepository
from songyan.evals.score_aggregator import ScoreAggregator
from songyan.exceptions import LLMError, LLMResponseParseError, SettlementError
from songyan.genres.loader import load_genre_profile
from songyan.models import (
    ChapterHead,
    ChapterSummary,
    ChapterVersion,
    ContextPackage,
    ContextSnapshot,
    CreativeBrief,
    HumanInstruction,
    ReviewCategory,
    ReviewIssue,
)
from songyan.utils.scene_parser import parse_scenes as _parse_scenes
from songyan.utils.truncation import enforce_word_count as _enforce_word_count
from songyan.utils.truncation import hard_truncate_at_boundary as _hard_truncate_at_boundary
from songyan.utils.word_count import count_chinese_words as _count_chinese_words
from songyan.workflows._helpers import (
    _index_accepted_chapter,
    assemble_context_package,
    load_chapter_goal,
    load_creative_brief,
    load_latest_audits,
    load_merged_report,
    load_project,
    load_version,
    new_id,
    trigger_layered_summaries,
)
from songyan.workflows.review_merger import merge_reviews

logger = structlog.get_logger(__name__)

_REWRITE_ROLLBACK_SCORE_DELTA = 0.08


def _safe_best_min_score(chapter_number: int) -> float:
    """章节阶段感知的 safe-best 门槛：早期章节天然分数偏低。"""
    if chapter_number <= 20:
        return 0.75
    elif chapter_number <= 50:
        return 0.78
    else:
        return 0.82

_COHERENCE_CATEGORIES: set[ReviewCategory] = {
    ReviewCategory.WORLD_CONSISTENCY,
    ReviewCategory.CHARACTER_BEHAVIOR,
    ReviewCategory.TIMELINE,
    ReviewCategory.NEW_SETTING_UNREGISTERED,
}


def combine_revision_signals(
    *,
    merged_has_critical: bool,
    merged_has_major: bool,
    score_needs_revision: bool,
    score_has_critical: bool = False,
    score_has_major: bool = False,
) -> tuple[bool, bool, bool]:
    """合并审查与评分阻断信号，评分只能增强、不能覆盖 merged issue."""
    has_critical = merged_has_critical or score_has_critical
    has_major = merged_has_major or score_has_major
    needs_revision = has_critical or has_major or score_needs_revision
    return has_critical, has_major, needs_revision


def _has_non_coherence_major(issues: list[ReviewIssue]) -> bool:
    """非 coherence major 由 ReviewMerger 直接阻断；coherence major 走 110e 阈值."""
    return any(
        issue.severity == "major" and issue.category not in _COHERENCE_CATEGORIES
        for issue in issues
    )


async def _load_active_best_version(
    *,
    version_id: str | None,
    project_id: str,
    chapter_number: int,
) -> ChapterVersion | None:
    """加载可作为回滚目标的 best version，拒绝 abandoned 或跨章节版本."""
    if not version_id:
        return None

    version = await ChapterVersionRepository().get(version_id)
    if version is None:
        logger.warning(
            "workflow.best_version_missing",
            version_id=version_id,
            project_id=project_id,
            chapter_number=chapter_number,
        )
        return None

    if version.is_abandoned:
        logger.warning(
            "workflow.best_version_abandoned",
            version_id=version_id,
            project_id=project_id,
            chapter_number=chapter_number,
        )
        return None

    if version.project_id != project_id or version.chapter_number != chapter_number:
        logger.warning(
            "workflow.best_version_scope_mismatch",
            version_id=version_id,
            version_project_id=version.project_id,
            version_chapter_number=version.chapter_number,
            project_id=project_id,
            chapter_number=chapter_number,
        )
        return None

    return version


def _score_card_for_version(
    score_card_raw: dict[str, Any] | None,
    version_id: str,
) -> dict[str, Any] | None:
    """返回与 version_id 同源的 score_card；缺失 version_id 的旧数据按当前 best 补齐."""
    if not isinstance(score_card_raw, dict):
        return None

    score_version_id = score_card_raw.get("version_id")
    if score_version_id and score_version_id != version_id:
        logger.warning(
            "workflow.best_score_card_version_mismatch",
            version_id=version_id,
            score_card_version_id=score_version_id,
        )
        return None

    return {**score_card_raw, "version_id": version_id}


def _score_card_passes_quality_gate(score_card_raw: dict[str, Any] | None) -> bool:
    """判断 score_card 是否满足 QualityGate 的硬门条件."""
    if not isinstance(score_card_raw, dict):
        return False
    required_keys = {"length", "budget", "coherence", "momentum", "readability", "flags"}
    if not required_keys.issubset(score_card_raw):
        return False
    try:
        from songyan.models import ChapterScoreCard

        score_card = ChapterScoreCard.model_validate(score_card_raw)
    except Exception:
        logger.warning("workflow.invalid_quality_gate_score_card", exc_info=True)
        return False

    return (
        score_card.flags.length_ok
        and score_card.flags.budget_ok
        and not score_card.flags.coherence_critical
        and not score_card.flags.coherence_major
        and score_card.flags.momentum_present
        and score_card.flags.readability_ok
    )


def _score_card_overall(score_card_raw: dict[str, Any] | None) -> float | None:
    if not isinstance(score_card_raw, dict):
        return None
    try:
        return float(score_card_raw.get("overall_score", 0.0))
    except (TypeError, ValueError):
        return None


def _score_card_is_safe_best(score_card_raw: dict[str, Any] | None, chapter_number: int) -> bool:
    """判断 best 是否足够安全，可保护其不被低质量 rewrite 覆盖."""
    if not isinstance(score_card_raw, dict):
        return False
    try:
        from songyan.models import ChapterScoreCard

        score_card = ChapterScoreCard.model_validate(score_card_raw)
    except Exception:
        logger.warning("workflow.invalid_safe_best_score_card", exc_info=True)
        return False

    return (
        score_card.overall_score >= _safe_best_min_score(chapter_number)
        and score_card.flags.length_ok
        and score_card.flags.budget_ok
        and not score_card.flags.coherence_critical
    )


def _score_card_is_degraded_acceptable(score_card_raw: dict[str, Any] | None) -> bool:
    """判断 best 是否满足降级接受条件：分数尚可但 QG 未完全通过。"""
    if not isinstance(score_card_raw, dict):
        return False
    try:
        from songyan.models import ChapterScoreCard

        score_card = ChapterScoreCard.model_validate(score_card_raw)
    except Exception:
        logger.warning("workflow.invalid_degraded_accept_score_card", exc_info=True)
        return False

    return (
        score_card.overall_score >= 0.70
        and score_card.flags.length_ok
        and score_card.flags.budget_ok
        and not score_card.flags.coherence_critical
    )


def _reset_rewrite_scoped_state() -> dict[str, Any]:
    """清理只属于上一轮 revision / quality gate 的瞬时状态."""
    return {
        "_new_issues_introduced": [],
        "_new_issues_version_id": None,
        "_content_preservation_ratio": None,
        "_quality_gate_passed": None,
        "_quality_gate_failures": [],
        "_convergence_failed": False,
        "_skip_settlement": False,
        "_settlement_needs_human_review": False,
        "_score_card": None,
    }


def _new_issues_for_current_version(
    state: dict[str, Any],
    current_version_id: str,
) -> list[dict[str, Any]]:
    """返回归属于当前版本的 new issues，过滤跨版本 stale state."""
    new_issues = state.get("_new_issues_introduced")
    if not new_issues or not isinstance(new_issues, list):
        return []

    issues_version_id = state.get("_new_issues_version_id")
    if issues_version_id and issues_version_id != current_version_id:
        logger.warning(
            "quality_gate.ignored_stale_new_issues",
            current_version_id=current_version_id,
            issues_version_id=issues_version_id,
            issue_count=len(new_issues),
        )
        return []

    filtered: list[dict[str, Any]] = []
    for issue in new_issues:
        if not isinstance(issue, dict):
            filtered.append(issue)
            continue
        issue_version_id = issue.get("version_id") or issue.get("current_version_id")
        if issue_version_id and issue_version_id != current_version_id:
            continue
        filtered.append(issue)
    return filtered


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
        return {"error": f"Project not found: {state['project_id']}", "status": "goal_planner"}

    genre = load_genre_profile(project.genre_id)
    mode = load_creative_mode_profile(project.mode_id)
    try:
        goal = await define_chapter_goal(
            project_id=state["project_id"],
            project=project,
            genre_profile=genre,
            mode_profile=mode,
            chapter_number=state["chapter_number"],
            previous_summary=state.get("previous_summary", ""),
        )
        goal_id = new_id("gp")
        await ChapterGoalRepository().create(goal, goal_id, state["project_id"])
        return {"chapter_goal_id": goal_id, "status": "creative_direction"}
    except (LLMError, LLMResponseParseError) as exc:
        logger.warning(
            "goal_planner_node.llm_failed",
            error=str(exc),
            project_id=state["project_id"],
            chapter_number=state["chapter_number"],
        )
        return {"error": f"GoalPlanner LLM call failed: {exc}", "status": "goal_planner"}


async def creative_director_node(state: dict[str, Any]) -> dict[str, Any]:
    goal = await load_chapter_goal(state["chapter_goal_id"])
    if goal is None:
        return {"error": "ChapterGoal not found", "status": "creative_director"}

    project = await load_project(state["project_id"])
    genre = load_genre_profile(project.genre_id)
    mode = load_creative_mode_profile(project.mode_id)
    characters = await CharacterRepository().list_by_project(state["project_id"])
    seed_settings = await SettingSnapshotRepository().list_by_project(state["project_id"])

    try:
        brief = await generate_creative_brief(
            project_id=state["project_id"],
            project=project,
            chapter_goal=goal,
            genre_profile=genre,
            mode_profile=mode,
            characters=characters,
            seed_settings=seed_settings,
        )
        brief_id = new_id("cb")
        await CreativeBriefRepository().create(
            brief, brief_id, state["project_id"], state["chapter_number"]
        )

        # Task 074: 为没有风格卡的角色生成对话风格卡
        style_cards = await generate_dialogue_style_cards(characters, state["project_id"])
        if style_cards:
            repo = CharacterRepository()
            for card in style_cards:
                await repo.save_dialogue_style_card(card.character_id, card)

        return {"creative_brief_id": brief_id, "status": "context_assembly"}
    except (LLMError, LLMResponseParseError) as exc:
        logger.warning(
            "creative_director_node.llm_failed",
            error=str(exc),
            project_id=state["project_id"],
            chapter_number=state["chapter_number"],
        )
        return {"error": f"CreativeDirector LLM call failed: {exc}", "status": "creative_director"}


async def _get_context_package(state: dict[str, Any]) -> Any:
    """实时组装 ContextPackage，避免在 LangGraph state 长期保存业务对象."""
    if "context_package" in state:
        return state["context_package"]

    snapshot_id = state.get("context_snapshot_id")
    if snapshot_id:
        snapshot = await ContextSnapshotRepository().get(snapshot_id)
        if snapshot is None:
            raise ValueError(f"ContextSnapshot not found: {snapshot_id}")
        return ContextPackage.model_validate(snapshot.payload)

    return await _assemble_context_fallback(state)


async def _save_context_snapshot(
    *,
    state: dict[str, Any],
    ctx: ContextPackage,
) -> str:
    """保存裁剪后的上下文快照，只把 snapshot_id 放入 LangGraph state."""
    snapshot_id = new_id("ctx")
    snapshot = ContextSnapshot(
        snapshot_id=snapshot_id,
        project_id=state["project_id"],
        chapter_number=state["chapter_number"],
        chapter_goal_id=state.get("chapter_goal_id"),
        creative_brief_id=state.get("creative_brief_id"),
        budget_used=getattr(ctx, "budget_used", None),
        context_emergency=getattr(ctx, "context_emergency", False),
        budget_used_before_emergency=getattr(ctx, "budget_used_before_emergency", None),
        payload=ctx.model_dump(mode="json"),
    )
    await ContextSnapshotRepository().create(snapshot)
    return snapshot_id


async def _assemble_context_from_state(
    state: dict[str, Any],
    goal: Any,
    brief: CreativeBrief | None,
) -> ContextPackage:
    """按 CreativeBrief 动态字段组装 ContextPackage 并注入人类指令."""
    _nf = brief.narrative_fullness if brief else 0.0
    _cf = brief.character_focus if brief else None
    _fd = brief.foreshadowing_due if brief else None
    _fod = brief.focal_distance if brief else "mid"
    ctx = await assemble_context_package(
        state["project_id"],
        state["chapter_number"],
        goal,
        brief,
        narrative_fullness=_nf,
        character_focus=_cf,
        foreshadowing_due=_fd,
        focal_distance=_fod,
    )
    ctx.human_instructions = state.get("human_instructions", [])
    return ctx


async def _load_brief_from_state(state: dict[str, Any]) -> CreativeBrief | None:
    """按 state 中的 creative_brief_id 加载 CreativeBrief."""
    if state.get("creative_brief_id"):
        return await load_creative_brief(state["creative_brief_id"])
    return None


async def _assemble_context_fallback(state: dict[str, Any]) -> ContextPackage:
    """兼容未进入 ContextManager 的旧测试/旧调用路径."""
    goal = await load_chapter_goal(state["chapter_goal_id"])
    brief = await _load_brief_from_state(state)
    return await _assemble_context_from_state(state, goal, brief)


def _extract_context_metrics(ctx_pkg: Any) -> dict[str, Any]:
    """从 ContextPackage 提取轻量指标，供 state/checkpoint 保存."""
    return {
        "budget_used": getattr(ctx_pkg, "budget_used", None),
        "character_states_loaded": len(getattr(ctx_pkg, "character_states", [])),
        "soft_refs_loaded": len(getattr(ctx_pkg, "soft_references", [])),
        "context_emergency": getattr(ctx_pkg, "context_emergency", False),
        "budget_used_before_emergency": getattr(ctx_pkg, "budget_used_before_emergency", None),
        "context_pressure": getattr(ctx_pkg, "context_pressure", {}),
    }


def _budget_used_for_scoring(state: dict[str, Any]) -> float | None:
    """读取质量评分使用的预算指标，优先使用轻量 state metrics."""
    context_metrics = state.get("_context_metrics") or {}
    budget_used = context_metrics.get("budget_used")
    if budget_used is not None:
        return float(budget_used)
    ctx_pkg = state.get("context_package")
    return getattr(ctx_pkg, "budget_used", None) if ctx_pkg is not None else None


async def _write_fallback_chapter_summary(
    *,
    content: str,
    settlement: Any | None,
    project_id: str,
    chapter_number: int,
    db: SummaryRepository,
) -> str:
    """写入代码生成的兜底章节摘要，返回真实 summary_id."""
    summary_text = content[:300] + "..." if len(content) > 300 else content
    key_events: list[str] = ["章节推进"]
    characters: list[str] = []
    impact_score = 0.0
    if settlement is not None:
        key_events = []
        for update in getattr(settlement, "character_updates", [])[:3]:
            key_events.append(f"{update.character_id} 的 {update.field} 变为 {update.new_value}")
            characters.append(update.character_id)
        for setting in getattr(settlement, "new_settings", [])[:2]:
            key_events.append(f"揭示新设定：{setting.setting_name}")
        for foreshadowing in getattr(settlement, "foreshadowing_updates", [])[:2]:
            key_events.append(f"{foreshadowing.operation} 伏笔：{foreshadowing.description}")
        if not key_events:
            key_events = ["章节推进"]
        impact_score = float(getattr(settlement, "impact_score", 0.0) or 0.0)

    fallback_summary = ChapterSummary(
        summary=summary_text,
        chapter_number=chapter_number,
        key_events=key_events,
        characters_appeared=list(dict.fromkeys(characters)),
        emotional_tone="中性",
        impact_score=impact_score,
    )
    summary_id = new_id("sum")
    await db.create(fallback_summary, project_id, summary_id)
    return summary_id


async def _load_chapter_repair_state(
    project_id: str,
    chapter_number: int,
    current_version_id: str | None = None,
) -> tuple[int, bool]:
    """从 SQLite 计算当前章节自动修复状态，作为 LangGraph state 的硬兜底."""
    versions = await ChapterVersionRepository().list_by_chapter(
        project_id,
        chapter_number,
        include_abandoned=True,
    )

    if current_version_id:
        versions_by_id = {version.version_id: version for version in versions}
        lineage = []
        version = versions_by_id.get(current_version_id)
        visited: set[str] = set()
        while version and version.version_id not in visited:
            visited.add(version.version_id)
            lineage.append(version)
            parent_id = getattr(version, "parent_version_id", None)
            version = versions_by_id.get(parent_id) if parent_id else None

        if lineage:
            revision_count = sum(
                1
                for version in lineage
                if version.version_type == "revision" and not version.is_abandoned
            )
            was_rewritten = any(
                version.version_type == "draft"
                and bool(getattr(version, "parent_version_id", None))
                and not version.is_abandoned
                for version in lineage
            )
            return revision_count, was_rewritten

    revision_count = sum(
        1 for version in versions if version.version_type == "revision" and not version.is_abandoned
    )
    was_rewritten = any(
        version.version_type == "draft" and version.version_number > 1 and not version.is_abandoned
        for version in versions
    )
    return revision_count, was_rewritten


async def context_manager_node(state: dict[str, Any]) -> dict[str, Any]:
    goal = await load_chapter_goal(state["chapter_goal_id"])
    if goal is None:
        return {"error": "ChapterGoal not found", "status": "context_manager"}
    brief = await _load_brief_from_state(state)
    ctx = await _assemble_context_from_state(state, goal, brief)
    context_snapshot_id = await _save_context_snapshot(state=state, ctx=ctx)
    return {
        "status": "writing",
        "context_snapshot_id": context_snapshot_id,
        "_budget_was_enforced": ctx._budget_enforced,
        "_context_metrics": _extract_context_metrics(ctx),
    }


async def writer_node(state: dict[str, Any]) -> dict[str, Any]:
    try:
        ctx = await _get_context_package(state)

        version = await write_chapter(
            db_version=ChapterVersionRepository(),
            db_head=ChapterHeadRepository(),
            project_id=state["project_id"],
            context_package=ctx,
            creative_brief_id=state.get("creative_brief_id"),
            context_snapshot_id=state.get("context_snapshot_id"),
        )
        return {"current_version_id": version.version_id, "status": "rule_auditing"}
    except (LLMError, LLMResponseParseError, ValueError) as exc:
        logger.warning(
            "writer_node.llm_failed",
            error=str(exc),
            project_id=state["project_id"],
            chapter_number=state["chapter_number"],
        )
        return {"error": f"Writer LLM call failed: {exc}", "status": "writer"}


async def rewrite_node(state: dict[str, Any]) -> dict[str, Any]:
    """截断重写 — 073：2 轮 revision 不收敛时整章重写.

    注入前 2 轮的所有 issues 作为禁止清单，调用 Writer 重新生成。
    090b: 同时注入字数约束，重写后允许 1 轮 revision 做最后修正。
    """
    ctx = await _get_context_package(state)

    # 收集前 2 轮的 issues 作为禁止清单
    avoid_list = await _build_rewrite_avoid_list(state)
    if avoid_list:
        ctx.human_instructions.append(
            {
                "type": "rewrite_avoid_list",
                "content": avoid_list,
            }
        )
        logger.info(
            "rewrite.injected_avoid_list",
            issue_count=len(avoid_list),
            project_id=state["project_id"],
            chapter_number=state["chapter_number"],
        )

    # 093: 注入字数硬约束 — rewrite 时目标收紧到 ±20%
    # 之前为 ±25%，导致达标初稿在 rewrite 后被破坏到超标状态
    goal = await load_chapter_goal(state.get("chapter_goal_id", ""))
    if goal and goal.word_count_target > 0:
        lower = int(goal.word_count_target * 0.80)
        upper = int(goal.word_count_target * 1.20)
        ctx.human_instructions.append(
            {
                "type": "word_count_constraint",
                "content": (
                    f"【重写约束】本章目标字数为 {goal.word_count_target}。 "
                    f"重写后正文必须严格控制在 {lower} ~ {upper} 字之间。 "
                    f"若场景展开后可能超标，优先减少场景数量或压缩描写，不要超额。"
                ),
            }
        )
        # Task 095: 注入场景结构约束
        ctx.human_instructions.append(
            {
                "type": "scene_structure_constraint",
                "content": (
                    "【场景结构约束】本章必须包含至少 2 个场景，推荐 3 个。 "
                    "每个场景字数不得超过总字数的 60%。 "
                    "场景之间应有清晰的叙事转折或时空切换。"
                ),
            }
        )
        logger.info(
            "rewrite.injected_word_count_constraint",
            word_count_target=goal.word_count_target,
            lower=lower,
            upper=upper,
            project_id=state["project_id"],
            chapter_number=state["chapter_number"],
        )

    rewrite_context_snapshot_id = None
    if state.get("context_snapshot_id"):
        rewrite_context_snapshot_id = await _save_context_snapshot(state=state, ctx=ctx)
    version = await write_chapter(
        db_version=ChapterVersionRepository(),
        db_head=ChapterHeadRepository(),
        project_id=state["project_id"],
        context_package=ctx,
        creative_brief_id=state.get("creative_brief_id"),
        context_snapshot_id=rewrite_context_snapshot_id,
    )

    # 093: 对 rewrite 结果追加硬截断回退（收紧到 ±20%）
    _goal = (
        goal if "goal" in locals() else await load_chapter_goal(state.get("chapter_goal_id", ""))
    )
    if _goal and _goal.word_count_target > 0:
        _upper_soft = int(_goal.word_count_target * 1.15)  # 收紧：之前 1.20
        _upper_hard = int(_goal.word_count_target * 1.20)  # 收紧：之前 1.25
        _lower_hard = int(_goal.word_count_target * 0.80)  # 新增下限保护
        _content = version.content
        _scenes = version.scenes
        _word_count = version.word_count

        (
            _trunc_content,
            _trunc_scenes,
            _trunc_wc,
            _was_truncated,
            _trunc_reason,
        ) = _enforce_word_count(
            _content, _scenes, _goal.word_count_target, _word_count, chapter_type=_goal.chapter_type
        )

        _new_content = _content
        _new_scenes = _scenes
        _new_wc = _word_count
        _truncation_applied = False

        if _was_truncated:
            _new_content = _trunc_content
            _new_scenes = _trunc_scenes
            _new_wc = _trunc_wc
            _truncation_applied = True
            logger.warning(
                "rewrite.word_count_truncated",
                project_id=state["project_id"],
                chapter_number=state["chapter_number"],
                original_word_count=_word_count,
                new_word_count=_new_wc,
                reason=_trunc_reason,
            )
        elif _word_count > _upper_hard:
            _hard_content = _hard_truncate_at_boundary(_content, _upper_hard)
            if _hard_content != _content:
                _new_content = _hard_content
                _new_scenes = _parse_scenes(_new_content)
                _new_wc = _count_chinese_words(_new_content)
                _truncation_applied = True
                logger.warning(
                    "rewrite.word_count_hard_truncated",
                    project_id=state["project_id"],
                    chapter_number=state["chapter_number"],
                    original_word_count=_word_count,
                    new_word_count=_new_wc,
                )
        elif _word_count < _lower_hard:
            # 093: 字数不足也触发回退 — 达标初稿不应被 rewrite 变短
            logger.warning(
                "rewrite.word_count_underflow",
                project_id=state["project_id"],
                chapter_number=state["chapter_number"],
                original_word_count=_word_count,
                lower_hard=_lower_hard,
                target=_goal.word_count_target,
            )
            # 不截断（无法自动扩展），但标记为需要 revision

        if _truncation_applied:
            # 同步更新内存对象（保持向后兼容）
            version.content = _new_content
            version.word_count = _new_wc
            version.scenes = _new_scenes

            # Rule 7: 禁止覆盖版本内容 — 创建新版本，废弃旧版本
            try:
                old_version_id = version.version_id
                new_version_number = await ChapterVersionRepository().get_next_version_number(
                    state["project_id"], state["chapter_number"]
                )
                new_version_id = new_id("cv")

                # 兼容测试中 mock 的 version 对象
                _cb_id = getattr(version, "creative_brief_id", None)
                _cb_id = _cb_id if isinstance(_cb_id, str) else None

                new_version = ChapterVersion(
                    version_id=new_version_id,
                    project_id=state["project_id"],
                    chapter_number=state["chapter_number"],
                    version_number=new_version_number,
                    version_type="draft",
                    is_abandoned=False,
                    content=_new_content,
                    word_count=_new_wc,
                    scenes=_new_scenes,
                    generation_metadata={
                        **version.generation_metadata,
                        "_rewrite_truncation_applied": True,
                        "_rewrite_truncation_reason": _trunc_reason,
                        "parent_version_id": old_version_id,
                    },
                    creative_brief_id=_cb_id,
                    parent_version_id=old_version_id,
                )

                await ChapterVersionRepository().create(new_version)
                await ChapterVersionRepository().mark_abandoned(old_version_id)

                # 更新 chapter_head
                head = await ChapterHeadRepository().get(
                    state["project_id"], state["chapter_number"]
                )
                if head:
                    head.current_version_id = new_version_id
                    await ChapterHeadRepository().update(head)

                version = new_version
            except Exception as exc:
                logger.warning(
                    "rewrite.version_create_failed",
                    error=str(exc),
                    project_id=state["project_id"],
                    chapter_number=state["chapter_number"],
                )
                # 回退：继续使用已更新的内存对象

    # Task 107: 结构完整性校验（scene_count >= 2 + hooks 完整）
    struct_ok = True
    struct_fail_reason = ""
    if len(version.scenes) < 2:
        struct_ok = False
        struct_fail_reason = f"scene_count={len(version.scenes)}<2"
    else:
        # 运行轻量 rule audit 检查 hooks
        _project = await load_project(state["project_id"])
        _genre = load_genre_profile(_project.genre_id) if _project else None
        _goal = await load_chapter_goal(state.get("chapter_goal_id", ""))
        _word_count_target = _goal.word_count_target if _goal else 3000
        _rule_check = run_rule_audit(
            content=version.content,
            genre_rules=_build_genre_rules(_genre, _project, _goal) if _genre else None,
            word_count_target=_word_count_target,
            chapter_type=_goal.chapter_type if _goal else None,
            scene_count_target=max(len(version.scenes), 2),
        )
        if not _rule_check.has_opening_hook:
            struct_ok = False
            struct_fail_reason = "missing_opening_hook"
        elif not _rule_check.has_ending_hook:
            struct_ok = False
            struct_fail_reason = "missing_ending_hook"

    if not struct_ok:
        logger.warning(
            "rewrite.struct_integrity_failed",
            version_id=version.version_id,
            reason=struct_fail_reason,
            project_id=state["project_id"],
            chapter_number=state["chapter_number"],
        )
        # 优先回滚到 QG 合格 best；若不存在 best，也必须废弃结构失败 rewrite，
        # 回到 rewrite 前版本，避免 head/state 指向 scene/hook 不完整版本。
        best_version_id = state.get("_best_version_id")
        best_version = await _load_active_best_version(
            version_id=best_version_id,
            project_id=state["project_id"],
            chapter_number=state["chapter_number"],
        )
        best_score_card = (
            _score_card_for_version(
                state.get("_best_score_card") or best_version.score_card,
                best_version.version_id,
            )
            if best_version
            else None
        )
        rollback_version = best_version
        rollback_source = "active_best" if best_version else None
        if rollback_version is None:
            previous_version_id = state.get("current_version_id")
            rollback_version = await _load_active_best_version(
                version_id=previous_version_id,
                project_id=state["project_id"],
                chapter_number=state["chapter_number"],
            )
            if rollback_version:
                rollback_source = "previous_version"
        if rollback_version and rollback_version.version_id != version.version_id:
            await ChapterVersionRepository().mark_abandoned(version.version_id)
            await ChapterHeadRepository().update(
                ChapterHead(
                    project_id=state["project_id"],
                    chapter_number=state["chapter_number"],
                    current_version_id=rollback_version.version_id,
                    accepted_version_id=None,
                    status="draft",
                )
            )
        elif not rollback_version:
            logger.warning(
                "rewrite.struct_integrity_no_rollback_target",
                version_id=version.version_id,
                project_id=state["project_id"],
                chapter_number=state["chapter_number"],
            )
        has_rollback_target = bool(
            rollback_version and rollback_version.version_id != version.version_id
        )
        # 使用回滚目标版本的 score_card 进行 QG 和 degraded_accept 判断
        rollback_score_card = best_score_card
        if rollback_score_card is None and rollback_version:
            rollback_score_card = _score_card_for_version(
                rollback_version.score_card,
                rollback_version.version_id,
            )
        recovered_with_qg_pass = bool(
            rollback_version
            and rollback_score_card
            and _score_card_passes_quality_gate(rollback_score_card)
        )
        degraded_accept = False
        if not recovered_with_qg_pass and rollback_score_card:
            degraded_accept = _score_card_is_degraded_acceptable(rollback_score_card)
        logger.info(
            "rewrite.struct_integrity_rollback_decision",
            project_id=state["project_id"],
            chapter_number=state["chapter_number"],
            failed_version_id=version.version_id,
            rollback_version_id=rollback_version.version_id if rollback_version else None,
            rollback_source=rollback_source,
            has_rollback_target=has_rollback_target,
            recovered_with_qg_pass=recovered_with_qg_pass,
            degraded_accept=degraded_accept,
            skip_settlement=not has_rollback_target,
            convergence_failed=not recovered_with_qg_pass,
        )
        return {
            "current_version_id": (
                rollback_version.version_id if rollback_version else version.version_id
            ),
            "revision_round": 0,
            **_reset_rewrite_scoped_state(),
            "_was_rewritten": True,
            "_rewrite_reason": f"struct_integrity_failed:{struct_fail_reason}",
            "_needs_revision": False,
            "_has_critical": False,
            "_has_major": False,
            "_convergence_failed": not recovered_with_qg_pass,
            "_skip_settlement": not has_rollback_target,
            "_settlement_needs_human_review": not has_rollback_target and not degraded_accept,
            "_quality_gate_passed": recovered_with_qg_pass,
            "_degraded_accept": degraded_accept,
            "_score_card": (
                rollback_score_card if (recovered_with_qg_pass or degraded_accept)
                else state.get("_score_card")
            ),
            "status": "human_confirm",
        }

    # 重置 revision 状态，标记已重写
    return {
        "current_version_id": version.version_id,
        "revision_round": 0,
        **_reset_rewrite_scoped_state(),
        "_was_rewritten": True,
        "_rewrite_reason": "2轮revision不收敛",
        "_needs_revision": False,
        "_has_critical": False,
        "_has_major": False,
        "status": "rule_auditing",
    }


async def _build_rewrite_avoid_list(state: dict[str, Any]) -> list[str]:
    """从 state 中提取前 2 轮 revision 的 issues，构建禁止清单.

    返回格式化后的 issue 描述列表，供 Writer Prompt 注入。
    """
    avoid_items: list[str] = []
    seen_descriptions: set[str] = set()

    def _add_item(desc: str, evidence: str = "") -> None:
        if not desc or desc in seen_descriptions:
            return
        seen_descriptions.add(desc)
        item = desc
        if evidence:
            item += f' — 证据："{evidence[:50]}"'
        avoid_items.append(item)

    # 1. 从 _new_issues_introduced 提取
    new_issues_raw = state.get("_new_issues_introduced")
    if new_issues_raw and isinstance(new_issues_raw, list):
        for raw in new_issues_raw:
            if isinstance(raw, dict):
                _add_item(
                    raw.get("issue_description", ""),
                    raw.get("evidence_quote", ""),
                )

    # 2. 从 review report 加载所有 issues
    report_id = state.get("review_report_id")
    if report_id:
        try:
            report = await load_merged_report(report_id)
            if report and report.issues:
                for issue in report.issues:
                    desc = getattr(issue, "issue_description", str(issue))
                    evidence = getattr(issue, "evidence_quote", "")
                    _add_item(desc, evidence)
        except (ValueError, TypeError, KeyError, AttributeError):
            logger.warning("rewrite.failed_to_load_report", report_id=report_id, exc_info=True)

    return avoid_items[:10]  # 最多 10 条，避免 prompt 过长


# =============================================================================
# Audit 节点
# =============================================================================


async def rule_auditor_node(state: dict[str, Any]) -> dict[str, Any]:
    version = await load_version(state["current_version_id"])
    if version is None:
        return {"error": "Version not found", "status": "rule_auditor"}

    project = await load_project(state["project_id"])
    genre = load_genre_profile(project.genre_id) if project else None
    # 从 chapter_goal 获取目标字数，而不是用实际字数
    goal = await load_chapter_goal(state.get("chapter_goal_id", ""))
    word_count_target = goal.word_count_target if goal else 3000

    # 获取 punch_points（Punch Engine）
    punch_points = None
    if state.get("creative_brief_id"):
        brief = await load_creative_brief(state["creative_brief_id"])
        if brief:
            punch_points = brief.punch_points

    result = run_rule_audit(
        content=version.content,
        genre_rules=_build_genre_rules(genre, project, goal) if genre else None,
        word_count_target=word_count_target,
        chapter_type=goal.chapter_type if goal else None,
        scene_count_target=max(len(version.scenes), 2) if version.scenes else 2,
        punch_points=punch_points,
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
        return {"error": "Version not found", "status": "llm_auditor"}

    try:
        ctx = await _get_context_package(state)
    except ValueError as exc:
        logger.warning(
            "llm_auditor_node.context_snapshot_missing",
            error=str(exc),
            version_id=version.version_id,
        )
        return {"error": str(exc), "status": "llm_auditor"}

    try:
        result = await run_llm_audit(content=version.content, context_package=ctx)
    except (LLMError, LLMResponseParseError) as exc:
        logger.warning(
            "llm_auditor_node.audit_failed",
            error=str(exc),
            version_id=version.version_id,
        )
        return {"error": f"LLM audit failed: {exc}", "status": "llm_auditor"}

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
        return {"error": "Version not found", "status": "review_merger"}

    rule_result, llm_result = await load_latest_audits(version.version_id)
    if rule_result is None or llm_result is None:
        logger.warning(
            "review_merger.missing_audits",
            version_id=version.version_id,
            has_rule=rule_result is not None,
            has_llm=llm_result is not None,
        )
        return {"error": "Missing audit results", "status": "review_merger"}

    # 058d: 反序列化上一轮 revision 引入的新问题
    prev_new_issues_raw = _new_issues_for_current_version(state, version.version_id)
    previous_new_issues: list[ReviewIssue] = []
    if prev_new_issues_raw and isinstance(prev_new_issues_raw, list):
        for raw in prev_new_issues_raw:
            try:
                previous_new_issues.append(ReviewIssue.model_validate(raw))
            except (ValueError, TypeError):
                logger.warning("review_merger.invalid_prev_new_issue", raw=raw)

    report_id = f"mr-{version.version_id}-{uuid.uuid4().hex[:8]}"

    # P0/P1: 加载上一轮 merged issues 用于审查矛盾检测
    prev_merged_issues_raw = state.get("_prev_merged_issues", [])
    previous_all_issues: list[ReviewIssue] | None = None
    if prev_merged_issues_raw and isinstance(prev_merged_issues_raw, list):
        previous_all_issues = []
        for raw in prev_merged_issues_raw:
            try:
                previous_all_issues.append(ReviewIssue.model_validate(raw))
            except (ValueError, TypeError):
                logger.warning("review_merger.invalid_prev_merged_issue", raw=raw)

    merged = await merge_reviews(
        version_id=version.version_id,
        content=version.content,
        rule_result=rule_result,
        llm_result=llm_result,
        db=ReviewReportRepository(),
        report_id=report_id,
        previous_new_issues=previous_new_issues if previous_new_issues else None,
        previous_all_issues=previous_all_issues,
    )

    merged_has_critical = merged.has_critical
    merged_has_major = _has_non_coherence_major(merged.issues)
    current_issues = len(merged.issues)
    db_revision_count, db_was_rewritten = await _load_chapter_repair_state(
        state["project_id"],
        state["chapter_number"],
        version.version_id,
    )
    rround = max(state.get("revision_round", 0), db_revision_count)
    total_revision_count = max(
        state.get("_total_revision_count", 0),
        db_revision_count,
    )
    was_rewritten = state.get("_was_rewritten", False) or db_was_rewritten

    # Task 106 + 111d: 统一评分聚合，预算指标来自轻量 _context_metrics。
    budget_used = _budget_used_for_scoring(state)
    score_card = ScoreAggregator.aggregate(
        version_id=version.version_id,
        rule_result=rule_result,
        llm_result=llm_result,
        budget_used=budget_used,
    )
    has_critical, has_major, needs_revision = combine_revision_signals(
        merged_has_critical=merged_has_critical,
        merged_has_major=merged_has_major,
        score_needs_revision=score_card.flags.needs_revision,
        score_has_critical=score_card.flags.coherence_critical,
        score_has_major=score_card.flags.coherence_major,
    )

    # 统一使用 score_card 口径（Task 106-patch）
    current_score = score_card.overall_score

    best_issues = state.get("_best_issues_count")
    best_score = state.get("_best_overall_score")
    best_version = state.get("_best_version_id")
    best_report_id = state.get("_best_report_id")
    best_score_card_raw = state.get("_best_score_card")

    # 将 score_card 持久化到版本记录（Task 106-patch）
    version.score_card = score_card.model_dump()
    try:
        await ChapterVersionRepository().update_score_card(version.version_id, version.score_card)
    except Exception as exc:
        logger.warning(
            "review_merger.save_score_card_failed",
            error=str(exc),
            version_id=version.version_id,
        )

    if was_rewritten and best_version and best_version != version.version_id:
        active_best = await _load_active_best_version(
            version_id=best_version,
            project_id=state["project_id"],
            chapter_number=state["chapter_number"],
        )
        active_best_score_card = (
            _score_card_for_version(best_score_card_raw, active_best.version_id)
            if active_best
            else None
        )
        best_overall = _score_card_overall(active_best_score_card)
        if (
            active_best
            and active_best_score_card
            and _score_card_is_safe_best(active_best_score_card, state["chapter_number"])
            and best_overall is not None
            and current_score < best_overall - _REWRITE_ROLLBACK_SCORE_DELTA
        ):
            logger.warning(
                "rewrite.low_quality_result_rollback",
                project_id=state["project_id"],
                chapter_number=state["chapter_number"],
                failed_version_id=version.version_id,
                recovered_version_id=active_best.version_id,
                current_score=current_score,
                best_score=best_overall,
                delta=_REWRITE_ROLLBACK_SCORE_DELTA,
            )
            await ChapterVersionRepository().mark_abandoned(version.version_id)
            await ChapterHeadRepository().update(
                ChapterHead(
                    project_id=state["project_id"],
                    chapter_number=state["chapter_number"],
                    current_version_id=active_best.version_id,
                    accepted_version_id=None,
                    status="draft",
                )
            )
            return {
                "review_report_id": best_report_id,
                "revision_round": rround,
                "_total_revision_count": total_revision_count,
                "_was_rewritten": was_rewritten,
                "_has_critical": False,
                "_has_major": False,
                "_needs_revision": False,
                "_new_issues_introduced": [],
                "_new_issues_version_id": None,
                "_content_preservation_ratio": None,
                "_quality_gate_failures": [],
                "_quality_gate_passed": True,
                "_convergence_failed": False,
                "_skip_settlement": False,
                "_settlement_needs_human_review": False,
                "_current_issues_count": state.get("_best_issues_count"),
                "_current_overall_score": best_overall,
                "_revision_rebound": True,
                "_best_version_id": active_best.version_id,
                "_best_report_id": best_report_id,
                "_best_score_card": active_best_score_card,
                "current_version_id": active_best.version_id,
                "literary_observation_id": None,
                "_score_card": active_best_score_card,
                "_prev_merged_issues": [],
                "status": "literary_auditing",
            }

    # Revision 反弹检测（Task 106-patch）:
    # - issues 增加 >20%
    # - overall_score 下降 >0.3（统一为 score_card 口径）
    # - 任一维度下降 >0.3（新增维度级劣化检测）
    if rround > 0 and best_issues is not None and needs_revision:
        issues_increased = current_issues > best_issues * 1.2
        score_dropped = best_score is not None and current_score < best_score - 0.3

        dim_degraded = False
        degraded_dim = ""
        if best_score_card_raw:
            try:
                from songyan.models import ChapterScoreCard

                best_card = ChapterScoreCard.model_validate(best_score_card_raw)
                for dim_name in ("length", "budget", "coherence", "momentum", "readability"):
                    cur_dim = getattr(score_card, dim_name)
                    best_dim = getattr(best_card, dim_name)
                    if cur_dim.score >= 0.0 and best_dim.score >= 0.0:
                        if cur_dim.score < best_dim.score - 0.3:
                            dim_degraded = True
                            degraded_dim = dim_name
                            break
            except Exception:
                logger.warning("review_merger.invalid_best_score_card", exc_info=True)

        if issues_increased or score_dropped or dim_degraded:
            active_best = await _load_active_best_version(
                version_id=best_version,
                project_id=state["project_id"],
                chapter_number=state["chapter_number"],
            )
            active_best_score_card = (
                _score_card_for_version(best_score_card_raw, active_best.version_id)
                if active_best
                else None
            )
            logger.warning(
                "revision_rebound_detected",
                prev_issues=best_issues,
                current_issues=current_issues,
                prev_score=best_score,
                current_score=current_score,
                degraded_dimension=degraded_dim,
                rollback_version=best_version,
                revision_round=rround,
                rollback_valid=bool(active_best and active_best_score_card),
            )
            if not active_best or not active_best_score_card:
                return {
                    "review_report_id": report_id,
                    "revision_round": rround,
                    "_total_revision_count": total_revision_count,
                    "_was_rewritten": was_rewritten,
                    "_has_critical": has_critical,
                    "_has_major": has_major,
                    "_needs_revision": False,
                    "_current_issues_count": current_issues,
                    "_current_overall_score": current_score,
                    "_revision_rebound": True,
                    "_convergence_failed": True,
                    "_skip_settlement": True,
                    "current_version_id": version.version_id,
                    "_score_card": score_card.model_dump(),
                    "_prev_merged_issues": [i.model_dump() for i in merged.issues],
                    "status": "human_confirm",
                }

            await ChapterVersionRepository().mark_abandoned(version.version_id)
            await ChapterHeadRepository().update(
                ChapterHead(
                    project_id=state["project_id"],
                    chapter_number=state["chapter_number"],
                    current_version_id=active_best.version_id,
                    accepted_version_id=None,
                    status="draft",
                )
            )
            return {
                "review_report_id": best_report_id,
                "revision_round": rround,
                "_total_revision_count": total_revision_count,
                "_was_rewritten": was_rewritten,
                "_has_critical": False,
                "_has_major": False,
                "_needs_revision": False,
                "_new_issues_introduced": [],
                "_content_preservation_ratio": None,
                "_quality_gate_failures": [],
                "_convergence_failed": False,
                "_skip_settlement": False,
                "_settlement_needs_human_review": False,
                "_current_issues_count": best_issues,
                "_current_overall_score": best_score or 0.0,
                "_revision_rebound": True,
                "_best_version_id": active_best.version_id,
                "_best_score_card": active_best_score_card,
                "current_version_id": active_best.version_id,
                "literary_observation_id": None,
                "_score_card": active_best_score_card,
                "_prev_merged_issues": [i.model_dump() for i in merged.issues],
                "status": "literary_auditing",
            }
        # 未反弹，只有通过 QG 硬门的版本才能作为 settlement 前回滚目标。
        # 否则会把 length/readability 等失败版本写入 best，导致收敛终点
        # 回滚到仍然不能结算的版本。
        if not _score_card_passes_quality_gate(score_card.model_dump()):
            logger.info(
                "review_merger.round_summary",
                version_id=version.version_id,
                revision_round=rround,
                overall_score=current_score,
                issues_count=current_issues,
                has_critical=has_critical,
                has_major=has_major,
                action="keep_best_qg_failed",
            )
            return {
                "review_report_id": report_id,
                "revision_round": rround,
                "_total_revision_count": total_revision_count,
                "_was_rewritten": was_rewritten,
                "_has_critical": has_critical,
                "_has_major": has_major,
                "_needs_revision": True,
                "_current_issues_count": current_issues,
                "_current_overall_score": current_score,
                "_score_card": score_card.model_dump(),
                "_prev_merged_issues": [i.model_dump() for i in merged.issues],
                "status": "literary_auditing",
            }

        # 未反弹，更新 best 为当前版本
        logger.info(
            "review_merger.round_summary",
            version_id=version.version_id,
            revision_round=rround,
            overall_score=current_score,
            issues_count=current_issues,
            has_critical=has_critical,
            has_major=has_major,
            action="update_best",
        )
        return {
            "review_report_id": report_id,
            "revision_round": rround,
            "_total_revision_count": total_revision_count,
            "_was_rewritten": was_rewritten,
            "_has_critical": has_critical,
            "_has_major": has_major,
            "_needs_revision": True,
            "_current_issues_count": current_issues,
            "_current_overall_score": current_score,
            "_best_issues_count": current_issues,
            "_best_overall_score": current_score,
            "_best_version_id": version.version_id,
            "_best_report_id": report_id,
            "_best_score_card": score_card.model_dump(),
            "_score_card": score_card.model_dump(),
            "_prev_merged_issues": [i.model_dump() for i in merged.issues],
            "status": "literary_auditing",
        }

    # 初稿或不需要 revision：保存 best 供后续对比（如果需要 revision）
    logger.info(
        "review_merger.round_summary",
        version_id=version.version_id,
        revision_round=rround,
        overall_score=current_score,
        issues_count=current_issues,
        has_critical=has_critical,
        has_major=has_major,
        needs_revision=needs_revision,
        action="save_best" if needs_revision and rround == 0 else "pass",
    )
    result: dict[str, Any] = {
        "review_report_id": report_id,
        "revision_round": rround,
        "_total_revision_count": total_revision_count,
        "_was_rewritten": was_rewritten,
        "_has_critical": has_critical,
        "_has_major": has_major,
        "_needs_revision": needs_revision,
        "_current_issues_count": current_issues,
        "_current_overall_score": current_score,
        "_score_card": score_card.model_dump(),
        "_prev_merged_issues": [i.model_dump() for i in merged.issues],
        "status": "literary_auditing",
    }
    _should_save_best = (
        (needs_revision and rround == 0) or not state.get("_best_version_id")
    ) and _score_card_passes_quality_gate(score_card.model_dump())
    if _should_save_best:
        result["_best_issues_count"] = current_issues
        result["_best_overall_score"] = current_score
        result["_best_version_id"] = version.version_id
        result["_best_report_id"] = report_id
        result["_best_score_card"] = score_card.model_dump()
    return result


async def literary_auditor_node(state: dict[str, Any]) -> dict[str, Any]:
    version = await load_version(state["current_version_id"])
    if version is None:
        return {"error": "Version not found", "status": "literary_auditor"}

    cached_observation_id = await LiteraryObservationRepository().get_latest_id_by_version(
        version.version_id
    )
    if cached_observation_id:
        logger.info(
            "literary_auditor_node.cache_hit",
            version_id=version.version_id,
            observation_id=cached_observation_id,
        )
        return {
            "literary_observation_id": cached_observation_id,
            "status": "revision_routing",
        }

    try:
        ctx = await _get_context_package(state)
    except ValueError as exc:
        logger.warning(
            "literary_auditor_node.context_snapshot_missing",
            error=str(exc),
            version_id=version.version_id,
        )
        return {"error": str(exc), "status": "literary_auditor"}

    try:
        result = await run_literary_audit(content=version.content, context_package=ctx)
    except (LLMError, LLMResponseParseError) as exc:
        logger.warning(
            "literary_auditor_node.audit_failed",
            error=str(exc),
            version_id=version.version_id,
        )
        return {
            "error": f"Literary audit failed: {exc}",
            "status": "literary_auditor",
        }

    obs_id = new_id("lo")
    await save_literary_audit(
        db=LiteraryObservationRepository(),
        version_id=version.version_id,
        result=result,
        observation_id=obs_id,
    )
    return_state: dict[str, Any] = {
        "literary_observation_id": obs_id,
        "status": "revision_routing",
    }
    return return_state


# =============================================================================
# Revision 节点
# =============================================================================


async def revision_handler_node(state: dict[str, Any]) -> dict[str, Any]:
    version = await load_version(state["current_version_id"])
    if version is None:
        return {"error": "Version not found", "status": "revision_handler"}

    report = await load_merged_report(version.version_id)
    if report is None:
        return {"error": "Review report not found", "status": "revision_handler"}

    literary_result = None
    if state.get("literary_observation_id"):
        literary_result = await LiteraryObservationRepository().get_by_version(version.version_id)

    # 058d: 获取原始 RuleAuditResult（用于新问题检测）
    original_rule_report = await ReviewReportRepository().get_by_version(
        version.version_id, audit_type="rule"
    )
    original_rule_result = original_rule_report.rule_audit if original_rule_report else None

    # 068: 获取上一轮 LLMAuditor 的 issues 用于 feedback 注入
    previous_issues: list[ReviewIssue] | None = None
    rround = state.get("revision_round", 0)
    if rround > 0 and version.parent_version_id:
        parent_report = await load_merged_report(version.parent_version_id)
        if parent_report and parent_report.llm_audit:
            previous_issues = parent_report.llm_audit.issues

    # V4.0 Task 088: 传入目标字数用于 revision 后硬约束
    goal = await load_chapter_goal(state.get("chapter_goal_id", ""))
    word_count_target = goal.word_count_target if goal else 3000

    output, revised_content = await run_revision(
        content=version.content,
        report=report,
        literary_result=literary_result,
        previous_issues=previous_issues,
        word_count_target=word_count_target,
    )

    # 截断检测：若内容保留率 < 50%，跳过 revision，回退到原始版本
    ratio = output.content_preservation_ratio
    if ratio < 0.5:
        logger.warning(
            "revision_handler.truncated_skip",
            version_id=version.version_id,
            ratio=ratio,
            original_len=len(version.content),
            revised_len=len(revised_content),
        )
        return {
            "current_version_id": version.version_id,
            "revision_round": state["revision_round"] + 1,
            "_total_revision_count": state.get("_total_revision_count", 0) + 1,
            "_content_preservation_ratio": ratio,
            "_new_issues_introduced": [],
            "status": "rule_auditing",
        }

    new_version_id = await save_revision_output(
        version_db=ChapterVersionRepository(),
        head_db=ChapterHeadRepository(),
        project_id=state["project_id"],
        chapter_number=state["chapter_number"],
        output=output,
        revised_content=revised_content,
        parent_version=version,
    )

    # 058d: 对新版本运行 RuleAudit，获取修订后的 RuleAuditResult
    project = await load_project(state["project_id"])
    genre = load_genre_profile(project.genre_id) if project else None
    goal = await load_chapter_goal(state.get("chapter_goal_id", ""))
    word_count_target = goal.word_count_target if goal else 3000

    punch_points = None
    if state.get("creative_brief_id"):
        brief = await load_creative_brief(state["creative_brief_id"])
        if brief:
            punch_points = brief.punch_points

    revised_rule_result = run_rule_audit(
        content=revised_content,
        genre_rules=_build_genre_rules(genre, project, goal) if genre else None,
        word_count_target=word_count_target,
        chapter_type=goal.chapter_type if goal else None,
        scene_count_target=max(len(output.patches_applied), 2),
        punch_points=punch_points,
    )

    # 058d: 重新构建 RevisionOutput，传入前后 RuleAuditResult
    # 从 output 反推 data dict 供 _build_revision_output 解析
    data: dict[str, Any] = {"patches": []}
    for p in output.patches_applied:
        data["patches"].append(
            {
                "issue_id": p.issue_id,
                "original_text": p.original_text,
                "revised_text": p.revised_text,
                "location": p.location,
            }
        )
    from songyan.agents.revision_handler import _build_revision_output

    output = _build_revision_output(
        data=data,
        original_issues=report.patchable_issues,
        content=version.content,
        new_version_id=new_version_id,
        original_rule_result=original_rule_result,
        revised_rule_result=revised_rule_result,
    )
    output.content_preservation_ratio = ratio

    return {
        "current_version_id": new_version_id,
        "revision_round": state["revision_round"] + 1,
        "_total_revision_count": state.get("_total_revision_count", 0) + 1,
        "_content_preservation_ratio": ratio,
        "_new_issues_introduced": [
            {**i.model_dump(), "version_id": new_version_id}
            for i in output.new_issues_introduced
        ],
        "_new_issues_version_id": new_version_id,
        "status": "rule_auditing",
    }


# =============================================================================
# Confirm & Settlement 节点
# =============================================================================


async def quality_gate_node(state: dict[str, Any]) -> dict[str, Any]:
    """综合质量门 — accept 前的最后一道自动检查（Task 100b + Task 106）.

    基于 _score_card 五维检查 + 保留率/新问题（revision 链路特有）。
    """
    version = await load_version(state["current_version_id"])
    if version is None:
        return {"error": "Version not found", "status": "quality_gate"}

    failures: list[str] = []

    # Task 106: 优先使用 score_card 做维度检查
    score_card_raw = state.get("_score_card")
    has_score_card = False
    if score_card_raw:
        try:
            from songyan.models import ChapterScoreCard

            score_card = ChapterScoreCard.model_validate(score_card_raw)
            has_score_card = True
            if not score_card.flags.length_ok:
                failures.append(f"length_score:{score_card.length.score:.3f}")
            if not score_card.flags.budget_ok:
                failures.append(f"budget_score:{score_card.budget.score:.3f}")
            if score_card.flags.coherence_critical:
                failures.append("coherence_critical")
            if score_card.flags.coherence_major:
                failures.append("coherence_major")
            if not score_card.flags.momentum_present:
                failures.append(f"momentum_score:{score_card.momentum.score:.3f}")
            if not score_card.flags.readability_ok:
                failures.append(f"readability_score:{score_card.readability.score:.3f}")
        except Exception:
            logger.warning("quality_gate.invalid_score_card", exc_info=True)

    # Fallback：无 score_card 时使用原始字数检查
    if not has_score_card:
        goal = await load_chapter_goal(state.get("chapter_goal_id", ""))
        target = goal.word_count_target if goal else 3000
        ratio = version.word_count / target if target > 0 else 1.0
        if ratio > 1.30:
            failures.append(f"word_count_too_high:{version.word_count}:{target}:{ratio:.3f}")
        elif ratio < 0.80:
            failures.append(f"word_count_too_low:{version.word_count}:{target}:{ratio:.3f}")

    # 保留率检查（仅对 revision 产出，score_card 未覆盖）
    preservation = state.get("_content_preservation_ratio")
    if preservation is not None and preservation < 0.70:
        failures.append(f"preservation_too_low:{preservation:.3f}")

    # 新问题检查（revision 链路特有）
    new_issues = _new_issues_for_current_version(state, version.version_id)
    has_new_issues = len(new_issues) > 0
    if has_new_issues:
        failures.append(f"new_issues_introduced:{len(new_issues)}")

    if failures:
        db_revision_count, db_was_rewritten = await _load_chapter_repair_state(
            state["project_id"],
            state["chapter_number"],
            version.version_id,
        )
        was_rewritten = state.get("_was_rewritten", False) or db_was_rewritten

        # Task 107: 判断修复手段是否耗尽
        repair_exhausted = was_rewritten or db_revision_count >= 2

        # rewrite 是最后一次自动修复。重写后无论质量门因何失败，
        # 都交给 human gate/auto-confirm 收束，避免绕过 revision_router 继续修订。
        if has_new_issues:
            next_status = "human_review_required"
        elif was_rewritten:
            next_status = "human_confirm"
        elif any(f.startswith(("word_count_too_high:", "length_score:")) for f in failures):
            next_status = "rewrite"
        elif db_revision_count >= 2:
            next_status = "human_confirm"
        else:
            next_status = "rule_auditing"

            # Task 121c: _skip_settlement 只表示没有可安全结算的正文版本。
            # 修复耗尽且 QG 仍失败时，如果能回滚到 active best，后续 accept 仍必须
            # 执行 settlement；QG 失败由 _convergence_failed / _quality_gate_passed 记录。
        result: dict[str, Any] = {
            "_quality_gate_passed": False,
            "_quality_gate_failures": failures,
            "revision_round": max(state.get("revision_round", 0), db_revision_count),
            "_total_revision_count": max(
                state.get("_total_revision_count", 0),
                db_revision_count,
            ),
            "_was_rewritten": was_rewritten,
            "_needs_revision": next_status == "rule_auditing",
            "status": next_status,
        }

        if has_new_issues:
            result["_convergence_failed"] = True
            result["_skip_settlement"] = False
            result["_settlement_needs_human_review"] = True
            return result

        if repair_exhausted and next_status == "human_confirm":
            best_version_id = state.get("_best_version_id")
            active_best = await _load_active_best_version(
                version_id=best_version_id,
                project_id=state["project_id"],
                chapter_number=state["chapter_number"],
            )
            active_best_score_card = (
                _score_card_for_version(
                    state.get("_best_score_card") or active_best.score_card,
                    active_best.version_id,
                )
                if active_best
                else None
            )
            logger.warning(
                "quality_gate.convergence_failed",
                project_id=state["project_id"],
                chapter_number=state["chapter_number"],
                failures=failures,
                rollback_version=best_version_id,
                rollback_valid=bool(active_best and active_best_score_card),
            )
            if active_best and active_best_score_card:
                await ChapterHeadRepository().update(
                    ChapterHead(
                        project_id=state["project_id"],
                        chapter_number=state["chapter_number"],
                        current_version_id=active_best.version_id,
                        accepted_version_id=None,
                        status="draft",
                    )
                )
                result["current_version_id"] = active_best.version_id
                result["_best_version_id"] = active_best.version_id
                result["_best_score_card"] = active_best_score_card
                result["_score_card"] = active_best_score_card
                result["_skip_settlement"] = False
                result["_settlement_needs_human_review"] = False

                if _score_card_passes_quality_gate(active_best_score_card):
                    logger.warning(
                        "quality_gate.recovered_by_best_version",
                        project_id=state["project_id"],
                        chapter_number=state["chapter_number"],
                        failed_version_id=version.version_id,
                        recovered_version_id=active_best.version_id,
                        failures=failures,
                    )
                    result["_quality_gate_passed"] = True
                    result["_quality_gate_failures"] = []
                    result["_convergence_failed"] = False
                    result["_needs_revision"] = False
                    return result

                # Task 121q: degraded accept 路径 — 分数尚可但 QG 未完全通过
                if _score_card_is_degraded_acceptable(active_best_score_card):
                    logger.warning(
                        "quality_gate.degraded_accept",
                        project_id=state["project_id"],
                        chapter_number=state["chapter_number"],
                        failed_version_id=version.version_id,
                        recovered_version_id=active_best.version_id,
                        failures=failures,
                    )
                    result["_quality_gate_passed"] = False
                    result["_convergence_failed"] = True
                    result["_degraded_accept"] = True
                    result["_skip_settlement"] = False
                    result["_settlement_needs_human_review"] = False
                    return result

            else:
                result["_skip_settlement"] = True
                result["_settlement_needs_human_review"] = True

            result["_convergence_failed"] = True

        return result

    return {
        "_quality_gate_passed": True,
        "_quality_gate_failures": [],
        "status": "human_confirm",
    }


async def human_gate_node(state: dict[str, Any]) -> dict[str, Any]:
    """通用 Human Gate 节点 — 支持 accept/edit/reject/back.

    改造自 human_confirm_node，增强为深度协作接口。
    """
    version = await load_version(state["current_version_id"])
    if version is None:
        return {"error": "Version not found", "status": "human_confirm"}

    gate_type = state.get("_current_gate") or "human_confirm"
    existing_instructions = state.get("human_instructions", [])

    decision = interrupt(
        {
            "version_id": version.version_id,
            "gate_type": gate_type,
            "content_preview": (
                version.content[:500] + "..." if len(version.content) > 500 else version.content
            ),
            "options": ["accept", "edit", "reject", "back"],
            "human_instructions": existing_instructions,
        }
    )

    if decision == "edit":
        edited_content = _open_editor(version.content)
        await ChapterVersionRepository().list_by_chapter(
            state["project_id"], state["chapter_number"]
        )
        next_version_number = await ChapterVersionRepository().get_next_version_number(
            state["project_id"], state["chapter_number"]
        )
        edited_version = ChapterVersion(
            version_id=new_id("v"),
            project_id=state["project_id"],
            chapter_number=state["chapter_number"],
            version_number=next_version_number,
            version_type="edited",
            content=edited_content,
            word_count=_count_chinese_words(edited_content),
            parent_version_id=version.version_id,
        )
        await ChapterVersionRepository().create(edited_version)
        # Task 100b: edit 后不直接 accepted，更新 current_version_id 并路由到 Audit
        await ChapterHeadRepository().update(
            ChapterHead(
                project_id=state["project_id"],
                chapter_number=state["chapter_number"],
                current_version_id=edited_version.version_id,
                accepted_version_id=None,
                status="draft",
            )
        )
        # 记录 rewrite 类型的人类指令
        instruction = HumanInstruction(
            instruction_id=f"inst_{uuid.uuid4().hex[:8]}",
            gate_type=gate_type,
            action="rewrite",
            content=edited_content[:500] + "..." if len(edited_content) > 500 else edited_content,
        )
        logger.info(
            "human_gate.decision",
            project_id=state["project_id"],
            chapter_number=state["chapter_number"],
            decision="edit",
            version_id=edited_version.version_id,
            parent_version_id=version.version_id,
            revision_round=state.get("revision_round", 0),
        )
        return {
            "current_version_id": edited_version.version_id,
            "human_decision": "edit",
            "human_instructions": existing_instructions + [instruction.model_dump()],
            "_revision_rebound": state.get("_revision_rebound", False),
            # 清空 audit 状态，重走 Audit 流程
            "review_report_id": None,
            "_rule_report_id": None,
            "_llm_report_id": None,
            "_has_critical": False,
            "_has_major": False,
            "_needs_revision": False,
            "_new_issues_introduced": None,
            "_content_preservation_ratio": None,
            "status": "rule_auditing",
        }

    if decision == "accept":
        # Task 105: 提取上下文指标供流式验证收集
        _context_metrics: dict[str, Any] = state.get("_context_metrics", {})
        _ctx_pkg = state.get("context_package")
        if _ctx_pkg is not None:
            _context_metrics = _extract_context_metrics(_ctx_pkg)
        previous_qg_passed = state.get("_quality_gate_passed")
        review_passed = not state.get("_has_critical", False) and not state.get("_has_major", False)
        _qg_passed = review_passed if previous_qg_passed is None else bool(previous_qg_passed)

        _rround = state.get("revision_round", 0)
        logger.info(
            "human_gate.decision",
            project_id=state["project_id"],
            chapter_number=state["chapter_number"],
            decision="accept",
            version_id=version.version_id,
            revision_round=_rround,
            skip_settlement=state.get("_skip_settlement", False),
            convergence_failed=state.get("_convergence_failed", False),
            quality_gate_passed=_qg_passed,
            settlement_needs_human_review=state.get(
                "_settlement_needs_human_review", False
            ),
        )
        return {
            "human_decision": "accept",
            "human_instructions": existing_instructions,
            "_revision_rebound": state.get("_revision_rebound", False),
            "_context_metrics": _context_metrics,
            "_quality_gate_passed": _qg_passed,
            "_score_card": state.get("_score_card"),
            "_convergence_failed": state.get("_convergence_failed", False),
            "_skip_settlement": state.get("_skip_settlement", False),
            "status": "settlement",
        }

    if decision == "reject":
        logger.info(
            "human_gate.decision",
            project_id=state["project_id"],
            chapter_number=state["chapter_number"],
            decision="reject",
            version_id=version.version_id,
            revision_round=state.get("revision_round", 0),
        )
        return {
            "human_decision": "reject",
            "revision_round": 0,
            "human_instructions": existing_instructions,
            "_revision_rebound": state.get("_revision_rebound", False),
            "status": "goal_planning",
        }

    if decision == "back":
        logger.info(
            "human_gate.decision",
            project_id=state["project_id"],
            chapter_number=state["chapter_number"],
            decision="back",
            version_id=version.version_id,
            revision_round=state.get("revision_round", 0),
        )
        return {
            "human_decision": "back",
            "revision_round": 0,
            "human_instructions": existing_instructions,
            "_revision_rebound": state.get("_revision_rebound", False),
            "status": "writing",
        }

    return {"error": f"Unknown decision: {decision}", "status": "human_confirm"}


# 保留旧名作为别名，兼容现有代码
human_confirm_node = human_gate_node


async def _run_lifecycle_cleanup(project_id: str, chapter_number: int) -> None:
    """V4.0: 生命周期清理 — 统一调度所有表的 archive 策略（Task 087）."""
    try:
        from songyan.db.lifecycle_cleaners import get_default_scheduler

        scheduler = get_default_scheduler()
        result = await scheduler.run_cleanup(project_id, chapter_number)
        if result.transitions:
            logger.info(
                "lifecycle_cleanup.done",
                project_id=project_id,
                chapter_number=chapter_number,
                transitions=len(result.transitions),
                errors=len(result.errors),
            )
        if result.errors:
            logger.warning(
                "lifecycle_cleanup.errors",
                project_id=project_id,
                chapter_number=chapter_number,
                errors=result.errors,
            )
    except (RuntimeError, OSError, ConnectionError) as exc:
        logger.warning(
            "lifecycle_cleanup.failed",
            error=str(exc),
            project_id=project_id,
            chapter_number=chapter_number,
        )


async def accept_with_settlement_boundary(
    *,
    project_id: str,
    chapter_number: int,
    version_id: str,
    settlement: Any | None,
) -> None:
    """在同一事务内完成 settlement apply 与 accept 状态更新."""
    if settlement is not None and settlement.validation_status != "valid":
        raise SettlementError(f"Settlement validation status is {settlement.validation_status}")

    async with get_db() as conn:
        try:
            if settlement is not None:
                await apply_settlement(
                    settlement=settlement,
                    project_id=project_id,
                    chapter_number=chapter_number,
                    version_id=version_id,
                    conn=conn,
                )
            await ChapterVersionRepository().accept_version(version_id, conn=conn)
            await ChapterHeadRepository().update(
                ChapterHead(
                    project_id=project_id,
                    chapter_number=chapter_number,
                    current_version_id=version_id,
                    accepted_version_id=version_id,
                    status="accepted",
                ),
                conn=conn,
            )
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise


async def settlement_extractor_node(state: dict[str, Any]) -> dict[str, Any]:
    version = await load_version(state["current_version_id"])
    if version is None:
        return {"error": "Version not found", "status": "settlement_extractor"}

    project = await load_project(state["project_id"])
    genre = load_genre_profile(project.genre_id) if project else None

    # 067: 加载 chapter_goal 以按需过滤 genre_rules
    goal = await load_chapter_goal(state.get("chapter_goal_id", ""))

    settlement = None
    settlement_needs_review = False
    settlement_applied = False
    accepted_for_postprocessing = False
    summary_id = None

    logger.info(
        "settlement_extractor_node.contract_snapshot",
        project_id=state["project_id"],
        chapter_number=state["chapter_number"],
        version_id=version.version_id,
        skip_settlement=state.get("_skip_settlement", False),
        convergence_failed=state.get("_convergence_failed", False),
        quality_gate_passed=state.get("_quality_gate_passed"),
        settlement_needs_human_review=state.get(
            "_settlement_needs_human_review", False
        ),
    )

    # Task 121m: QG false 版本禁止进入 settlement，防止劣质上下文污染
    _qg_passed = state.get("_quality_gate_passed")
    _degraded_accept = state.get("_degraded_accept", False)
    if _qg_passed is False and not _degraded_accept:
        logger.warning(
            "settlement_extractor_node.qg_false_blocked",
            project_id=state["project_id"],
            chapter_number=state["chapter_number"],
            version_id=version.version_id,
        )
        return {
            "settlement_id": None,
            "summary_id": None,
            "status": "settlement_review",
            "_settlement_needs_human_review": True,
        }

    if _degraded_accept:
        logger.warning(
            "settlement_extractor_node.degraded_accept_continue",
            project_id=state["project_id"],
            chapter_number=state["chapter_number"],
            version_id=version.version_id,
        )

    # Task 111d: skipped settlement 不能再伪装为 accepted/done。
    if state.get("_skip_settlement", False):
        logger.info(
            "settlement_extractor_node.skipping_settlement",
            project_id=state["project_id"],
            chapter_number=state["chapter_number"],
            version_id=version.version_id,
        )
        settlement_needs_review = True
        return {
            "settlement_id": None,
            "summary_id": None,
            "status": "settlement_review",
            "_settlement_needs_human_review": settlement_needs_review,
        }
    else:
        # 1. 提取并应用 settlement（核心操作）
        try:
            settlement = await extract_settlement(
                content=version.content,
                project_id=state["project_id"],
                chapter_number=state["chapter_number"],
                version_id=version.version_id,
                genre_rules=_build_genre_rules(genre, project, goal) if genre else None,
            )
            if settlement.validation_status != "valid":
                logger.warning(
                    "settlement_extractor_node.validation_failed_needs_review",
                    project_id=state["project_id"],
                    chapter_number=state["chapter_number"],
                    version_id=version.version_id,
                    validation_status=settlement.validation_status,
                    validation_errors=settlement.validation_errors,
                )
                settlement_needs_review = True
            else:
                await accept_with_settlement_boundary(
                    project_id=state["project_id"],
                    chapter_number=state["chapter_number"],
                    version_id=version.version_id,
                    settlement=settlement,
                )
                settlement_applied = True
                accepted_for_postprocessing = True
                logger.info(
                    "settlement_extractor_node.settlement_applied",
                    project_id=state["project_id"],
                    chapter_number=state["chapter_number"],
                    version_id=version.version_id,
                    character_updates=len(settlement.character_updates),
                    new_settings=len(settlement.new_settings),
                    foreshadowing_updates=len(settlement.foreshadowing_updates),
                    numerical_updates=len(settlement.numerical_updates),
                )
        except (LLMError, LLMResponseParseError, SettlementError) as exc:
            logger.warning(
                "settlement_extractor_node.settlement_failed_needs_review",
                error=str(exc),
                project_id=state["project_id"],
                chapter_number=state["chapter_number"],
            )
            settlement_needs_review = True

        # 2. 生成章节摘要（非阻塞：失败不导致 settlement 回滚）
        if settlement_applied and settlement is not None:
            try:
                summary_id, _summary = await write_chapter_summary(
                    content=version.content,
                    settlement=settlement,
                    project_id=state["project_id"],
                    chapter_number=state["chapter_number"],
                    db=SummaryRepository(),
                )
            except (LLMError, LLMResponseParseError) as exc:
                logger.warning(
                    "settlement_extractor_node.summary_failed",
                    error=str(exc),
                    project_id=state["project_id"],
                    chapter_number=state["chapter_number"],
                )
                try:
                    summary_id = await _write_fallback_chapter_summary(
                        content=version.content,
                        settlement=settlement,
                        project_id=state["project_id"],
                        chapter_number=state["chapter_number"],
                        db=SummaryRepository(),
                    )
                except Exception as fallback_exc:
                    logger.warning(
                        "settlement_extractor_node.fallback_summary_failed",
                        error=str(fallback_exc),
                        project_id=state["project_id"],
                        chapter_number=state["chapter_number"],
                    )
                    settlement_needs_review = True

    # V4.0: 生命周期清理 — 统一调度所有表的 archive 策略（Task 087）
    if accepted_for_postprocessing:
        await _run_lifecycle_cleanup(state["project_id"], state["chapter_number"])

    # 3. RAG 向量索引（非阻塞：失败不导致 settlement 回滚）
    # Task 114a: 仅在本次 accept + settlement 事务成功后触发，禁止通过历史 version_type 旁路
    if accepted_for_postprocessing:
        try:
            mode = load_creative_mode_profile(project.mode_id)
            await _index_accepted_chapter(
                project_id=state["project_id"],
                chapter_number=state["chapter_number"],
                version_id=version.version_id,
                content=version.content,
                rag_config=mode.rag_config,
            )
        except (RuntimeError, OSError, TimeoutError) as exc:
            logger.warning(
                "settlement_extractor_node.rag_index_failed",
                error=str(exc),
                project_id=state["project_id"],
                chapter_number=state["chapter_number"],
            )

    # 4. SettingEvaporator（Task 103：语义相关性蒸发，纯规则，不调用 LLM）
    # Task 114a: 仅在本次 accept + settlement 事务成功后触发，禁止通过历史 version_type 旁路
    if accepted_for_postprocessing:
        try:
            from songyan.agents.setting_evaporator import SettingEvaporator

            evaporator = SettingEvaporator()
            archived_keys = await evaporator.run(
                project_id=state["project_id"],
                current_chapter=state["chapter_number"],
                chapter_goal=goal,
            )
            logger.info(
                "settlement_extractor_node.evaporator_done",
                project_id=state["project_id"],
                chapter_number=state["chapter_number"],
                archived_count=len(archived_keys),
                archived_keys=(archived_keys[:5] + (["..."] if len(archived_keys) > 5 else [])),
            )
            # 每 50 章执行一次合并扫描
            if state["chapter_number"] % 50 == 0:
                await evaporator.merge_similar_settings(
                    state["project_id"],
                    current_chapter=state["chapter_number"],
                )
        except (RuntimeError, OSError) as exc:
            logger.warning(
                "settlement_extractor_node.evaporator_failed",
                error=str(exc),
                project_id=state["project_id"],
                chapter_number=state["chapter_number"],
            )

    # 5. 分层摘要生成（069b：accept 后触发弧/卷摘要更新）
    # Task 114a: 仅在本次 accept + settlement 事务成功后触发，禁止通过历史 version_type 旁路
    if accepted_for_postprocessing:
        try:
            await trigger_layered_summaries(
                project_id=state["project_id"],
                chapter_number=state["chapter_number"],
                project=project,
            )
        except (RuntimeError, OSError, ConnectionError) as exc:
            logger.warning(
                "settlement_extractor_node.layered_summary_failed",
                error=str(exc),
                project_id=state["project_id"],
                chapter_number=state["chapter_number"],
            )

    return {
        "settlement_id": new_id("st") if settlement_applied else None,
        "summary_id": summary_id,
        "status": "settlement_review" if settlement_needs_review else "done",
        "_settlement_needs_human_review": settlement_needs_review,
    }
