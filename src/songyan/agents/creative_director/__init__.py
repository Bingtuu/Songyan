"""CreativeDirector Agent — 创作导演，生成 CreativeBrief."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog

from songyan.agents.continuity_auditor._scanners import ORPHANED_THRESHOLDS
from songyan.db.continuity_repo import SettingTrackingRepository
from songyan.db.human_mark_repo import HumanMarkRepository
from songyan.evals.concept_budget import build_concept_budget_constraint
from songyan.exceptions import LLMError, LLMResponseParseError
from songyan.llm.client import call_llm
from songyan.models.chapter import ChapterGoal
from songyan.models.character import Character, DialogueStyleCard
from songyan.models.creative_mode import (
    CreativeBrief,
    CreativeModeProfile,
)
from songyan.models.genre import GenreProfile
from songyan.models.project import ProjectSetting
from songyan.models.settlement import NewSetting

if TYPE_CHECKING:
    from songyan.workflows._narrative_context import NarrativeGoalContext

from ._brief_builder import (
    DEFAULT_FORBIDDEN_PATTERNS as DEFAULT_FORBIDDEN_PATTERNS,
)
from ._brief_builder import (
    MIN_FORBIDDEN_PATTERNS as MIN_FORBIDDEN_PATTERNS,
)
from ._brief_builder import (
    _build_creative_brief,
    _parse_llm_response,
)
from ._brief_builder import (
    _ensure_forbidden_patterns as _ensure_forbidden_patterns,
)
from ._brief_builder import (
    _extract_json as _extract_json,
)
from ._brief_builder import (
    _validate_tension as _validate_tension,
)

logger = structlog.get_logger(__name__)

PROMPT_PATH = Path(__file__).parent.parent.parent.parent / "prompts" / "creative_director.md"


def _load_prompt_template() -> str:
    """加载 CreativeDirector Prompt 模板 — 已迁移到工艺卡系统."""
    from songyan.prompts import get_prompt_loader

    return get_prompt_loader().load_card("creative_director").system_prompt


def _format_thread_constraints(narrative_ctx: NarrativeGoalContext) -> str:
    """构建线索经济约束文本（本章应推进/应收束线索、非必要不开新线）."""
    def _fmt(threads: list[dict]) -> str:
        if not threads:
            return "（无）"
        return "\n".join(
            f"- [{t.get('thread_id', '')}] {t.get('title', '') or '（未命名线索）'}"
            f"（{'主线' if t.get('is_mainline') else '支线'}，状态 {t.get('status', '')}）"
            for t in threads
        )

    return (
        f"本章应推进的线索（优先通过角色行动/冲突推进，而非旁白交代）：\n"
        f"{_fmt(narrative_ctx.open_threads)}\n"
        f"本章应收束的线索：\n"
        f"{_fmt(narrative_ctx.threads_to_resolve)}\n"
        "**线索经济要求**：优先推进/收束上述已开启线索；"
        "除非剧情必需，非必要不开启新线索、不引入新的 critical 设定；"
        "新开线索必须服务于当前弧目标。"
    )


async def _render_prompt(
    *,
    project_id: str,
    project: ProjectSetting,
    chapter_goal: ChapterGoal,
    genre_profile: GenreProfile,
    mode_profile: CreativeModeProfile,
    characters: list[Character],
    previous_summary: str,
    seed_settings: list[NewSetting],
    narrative_ctx: NarrativeGoalContext | None = None,
) -> str:
    """渲染 CreativeDirector Prompt.

    有骨架且存在待推进/收束线索时用工艺卡 1.0.6 注入线索经济约束；否则用 1.0.5
    （与历史行为逐字节等价，保证无骨架回退零差异）。
    """
    from songyan.prompts import render_agent_prompt

    active_settings = await _load_active_settings_to_recycle(
        project_id, chapter_goal.chapter_number
    )
    active_settings_text = _format_active_settings_to_recycle(active_settings)
    concept_budget_constraint = await build_concept_budget_constraint(
        project_id, chapter_goal.chapter_number
    )
    if concept_budget_constraint:
        active_settings_text = f"{active_settings_text}\n\n{concept_budget_constraint}"

    variables = {
        "mode_id": mode_profile.id,
        "genre_name": genre_profile.name,
        "mode_name": mode_profile.name,
        "protagonist_name": _get_protagonist_name(characters),
        "core_hook": project.core_hook or genre_profile.name,
        "tone": project.tone or genre_profile.name,
        "genre_satisfaction_types": ", ".join(genre_profile.satisfaction_types)
        if genre_profile.satisfaction_types
        else "无",
        "genre_pacing_rule": genre_profile.pacing_rule or "无特殊规则",
        "genre_taboos": ", ".join(genre_profile.taboos) if genre_profile.taboos else "无",
        "chapter_goal_json": chapter_goal.model_dump_json(indent=2),
        "recent_summaries": previous_summary or "（本章为开篇章节，无前置剧情）",
        "character_states": _format_characters(characters),
        "seed_settings_json": _format_seed_settings(seed_settings),
        "active_settings_to_recycle": active_settings_text,
        "mode_constraints": _format_mode_constraints(mode_profile),
        "punch_engine_enabled": mode_profile.id == "webnovel_intense",
    }

    has_threads = narrative_ctx is not None and narrative_ctx.has_skeleton and (
        narrative_ctx.open_threads or narrative_ctx.threads_to_resolve
    )
    if has_threads:
        variables["thread_constraints"] = _format_thread_constraints(narrative_ctx)
        return render_agent_prompt("creative_director", variables, version="1.0.6")

    return render_agent_prompt("creative_director", variables, version="1.0.5")


def _get_protagonist_name(characters: list[Character]) -> str:
    """从角色列表中提取主角名字."""
    for char in characters:
        if char.role_type == "protagonist":
            return char.name
    return characters[0].name if characters else "主角"


def _format_characters(characters: list[Character]) -> str:
    """格式化角色状态为文本."""
    if not characters:
        return "暂无角色信息"
    lines = []
    for char in characters:
        lines.append(f"- {char.name}（{char.role_type}）: {char.background or '背景未设定'}")
        if char.personality_traits:
            lines.append(f"  性格: {', '.join(char.personality_traits)}")
        if char.goals:
            lines.append(f"  目标: {', '.join(char.goals)}")
    return "\n".join(lines)


def _format_seed_settings(seed_settings: list[NewSetting]) -> str:
    """将种子设定列表格式化为文本."""
    if not seed_settings:
        return "（暂无种子设定）"
    lines = []
    for s in seed_settings:
        lines.append(f"- **{s.setting_name}**（{s.setting_key}）：{s.description}")
    return "\n".join(lines)


async def _load_active_settings_to_recycle(
    project_id: str,
    chapter_number: int,
    limit: int = 10,
    min_silent_chapters: int = 2,
) -> list[dict]:
    """加载近期活跃且未被回收的设定，供 CreativeDirector 提示 Writer 回收.

    Task 137: 优先展示即将成为 orphan 的设定（已沉寂 >= min_silent_chapters 章），
    按类别优先级与沉寂章数排序，帮助 Writer 形成回收闭环。
    """
    category_priority = {
        "critical": 0,
        "recurring": 1,
        "technical": 2,
        "background": 3,
        "historical": 4,
    }
    rows = await SettingTrackingRepository().list_by_project(project_id)
    active_marks = {
        mark.target_key: mark.priority
        for mark in await HumanMarkRepository().list_by_project(
            project_id, mark_type="setting", include_resolved=False
        )
        if mark.source != "continuity_auditor"
        or mark.created_at_chapter is None
        or mark.created_at_chapter < chapter_number
    }
    active = [
        {
            **dict(r),
            "human_mark_priority": active_marks.get(str(r.get("setting_key") or ""), 0),
            "current_chapter": chapter_number,
        }
        for r in rows
        if r.get("status") == "active"
        and (
            chapter_number - (r.get("last_mentioned_chapter") or 0) >= min_silent_chapters
            or str(r.get("setting_key") or "") in active_marks
        )
    ]
    # 优先 critical/recurring 与 active human mark，再按沉寂章数从高到低排序。
    active.sort(
        key=lambda r: (
            category_priority.get(str(r.get("category") or "background"), 9),
            -(int(r.get("human_mark_priority") or 0)),
            -(chapter_number - (r.get("last_mentioned_chapter") or 0)),
            r.get("introduced_in_chapter") or 0,
            r.get("setting_key") or "",
        )
    )
    return active[:limit]


def _format_active_settings_to_recycle(settings: list[dict]) -> str:
    """格式化需要回收的活跃设定列表."""
    if not settings:
        return "（无近期活跃设定）"
    lines = []
    for s in settings:
        name = s.get("setting_name") or s.get("setting_key") or "未命名设定"
        key = s.get("setting_key") or "无 key"
        category = s.get("category", "background")
        introduced = s.get("introduced_in_chapter", 0)
        last = s.get("last_mentioned_chapter", 0)
        mark_priority = int(s.get("human_mark_priority") or 0)
        mark_note = f"，人工标记优先级：{mark_priority}" if mark_priority > 0 else ""
        silent_chapters = int(s.get("current_chapter", 0) or 0) - int(last or 0)
        critical_note = ""
        if (
            category == "critical"
            and silent_chapters >= ORPHANED_THRESHOLDS["critical"]
        ):
            critical_note = (
                "，严重级别：P1，处理要求：本章必须明确回收、提及、"
                "或给出无法回收的剧情原因"
            )
        lines.append(
            f"- {name}（{key}，类别：{category}，"
            f"引入第{introduced}章，最近提及第{last}章"
            f"{mark_note}{critical_note}）"
        )
    return "\n".join(lines)


def _format_mode_constraints(mode_profile: CreativeModeProfile) -> str:
    """将 CreativeModeProfile 格式化为约束文本."""
    lines = []
    lines.append(f"- 创作模式: {mode_profile.name}")
    lines.append(f"- 修订策略: {mode_profile.revision_policy}")
    if mode_profile.tolerance:
        for key, value in mode_profile.tolerance.items():
            lines.append(f"- 容忍阈值 {key}: {value}")
    if mode_profile.active_audit_dimensions:
        lines.append(f"- 审查维度: {', '.join(mode_profile.active_audit_dimensions)}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main Entry
# ---------------------------------------------------------------------------
async def generate_creative_brief(
    project_id: str,
    project: ProjectSetting,
    chapter_goal: ChapterGoal,
    genre_profile: GenreProfile,
    mode_profile: CreativeModeProfile,
    characters: list[Character],
    previous_summary: str = "",
    seed_settings: list[NewSetting] | None = None,
    narrative_ctx: NarrativeGoalContext | None = None,
    *,
    temperature: float = 0.7,
) -> CreativeBrief:
    """生成本章创作导演简报.

    1. 加载并渲染 Prompt 模板
    2. 调用 LLM（temperature=0.7）
    3. 解析 JSON 输出为 CreativeBrief
    4. 返回 CreativeBrief（由调用方负责持久化）

    Args:
        project_id: 项目唯一标识
        project: 项目设定（含 core_hook、tone 等）
        chapter_goal: 章节目标（来自 GoalPlanner）
        genre_profile: 题材规则
        mode_profile: 创作模式约束
        characters: 出场角色列表
        previous_summary: 最近剧情摘要

    Returns:
        生成的创作导演简报

    Raises:
        LLMError: LLM 调用失败
        LLMResponseParseError: 响应解析失败
    """
    logger.info(
        "creative_director.start",
        chapter_number=chapter_goal.chapter_number,
        project_id=project_id,
        genre=genre_profile.id,
        mode=mode_profile.id,
    )

    # 加载并渲染 Prompt
    prompt = await _render_prompt(
        project_id=project_id,
        project=project,
        chapter_goal=chapter_goal,
        genre_profile=genre_profile,
        mode_profile=mode_profile,
        characters=characters,
        previous_summary=previous_summary,
        seed_settings=seed_settings or [],
        narrative_ctx=narrative_ctx,
    )

    # 调用 LLM
    try:
        response_text = await call_llm(prompt, temperature=temperature, max_retries=3)
    except LLMError:
        logger.error(
            "creative_director.llm_failed",
            chapter_number=chapter_goal.chapter_number,
        )
        raise

    # 解析响应
    try:
        data = _parse_llm_response(response_text)
    except LLMResponseParseError:
        logger.error(
            "creative_director.parse_failed",
            chapter_number=chapter_goal.chapter_number,
            raw_response=response_text[:500],
        )
        raise

    # 构建 CreativeBrief（含字段验证和修正）
    brief = _build_creative_brief(data, mode_profile.id, chapter_goal)

    logger.info(
        "creative_director.complete",
        chapter_number=chapter_goal.chapter_number,
        tension_count=len(brief.required_tensions),
        forbidden_count=len(brief.forbidden_patterns),
    )

    return brief


# ---------------------------------------------------------------------------
# Task 074: Dialogue Style Card Generation
# ---------------------------------------------------------------------------

_DIALOGUE_STYLE_PROMPT_TEMPLATE = """\
你是 Songyan 的角色对话设计师。请为以下角色生成对话风格卡。

{character_descriptions}

## 要求

1. **角色区分度**：每个角色的对话风格必须与其他角色有明显差异，
   读者应能通过对话内容识别说话者（即使不标注说话人）
2. **性格一致性**：句式偏好、情绪表达模式必须与角色背景和性格一致
3. **具体模式**：情绪表达必须是具体行为模式，不是笼统描述。例如："愤怒时冷笑+反问"而非"生气时大声"
4. **口头禅**：每个角色至少给出 2 个口头禅或常用开头语
5. **社会背景**：语言习惯必须反映角色的教育水平、社会地位和成长环境

## 输出格式

请输出严格的 JSON（不要包含 markdown 代码块标记）：

{{
  "style_cards": [
    {{
      "character_id": "角色ID",
      "sentence_length_preference": "short|medium|long|mixed",
      "common_openers": ["口头禅1", "口头禅2"],
      "common_closers": ["结尾习惯1"],
      "anger_expression": "具体的愤怒表达模式",
      "fear_expression": "具体的恐惧表达模式",
      "joy_expression": "具体的喜悦表达模式",
      "sadness_expression": "具体的悲伤表达模式",
      "metaphor_frequency": "rare|moderate|frequent",
      "irony_usage": true,
      "rhetorical_question_habit": true,
      "interrupt_frequency": "rare|moderate|frequent",
      "pause_habit": "停顿习惯描述",
      "education_level_hint": "语言教育背景暗示",
      "social_role_speech_pattern": "社会角色语气模式"
    }}
  ]
}}
"""


def _format_characters_for_style_card(characters: list[Character]) -> str:
    """格式化角色信息用于风格卡生成 Prompt."""
    lines = []
    for i, char in enumerate(characters, 1):
        lines.append(f"### 角色 {i}: {char.name}（ID: {char.character_id}）")
        lines.append(f"- 定位: {char.role_type}")
        if char.background:
            lines.append(f"- 背景: {char.background}")
        if char.personality_traits:
            lines.append(f"- 性格: {', '.join(char.personality_traits)}")
        if char.goals:
            lines.append(f"- 目标: {', '.join(char.goals)}")
        lines.append("")
    return "\n".join(lines)


async def generate_dialogue_style_cards(
    characters: list[Character],
    project_id: str,
    temperature: float = 0.7,
) -> list[DialogueStyleCard]:
    """为角色生成对话风格卡.

    为 protagonist + antagonist + 关键 supporting 角色生成风格卡。
    已存在风格卡的角色将被跳过。

    Args:
        characters: 角色列表
        project_id: 项目 ID
        temperature: LLM 温度

    Returns:
        新生成的对话风格卡列表（已存在风格卡的角色不产生新卡片）
    """
    # 过滤已存在风格卡的角色
    chars_needing_card = [c for c in characters if c.dialogue_style_card is None]
    if not chars_needing_card:
        return []

    logger.info(
        "creative_director.dialogue_style.start",
        project_id=project_id,
        character_count=len(chars_needing_card),
    )

    prompt = _DIALOGUE_STYLE_PROMPT_TEMPLATE.format(
        character_descriptions=_format_characters_for_style_card(chars_needing_card),
    )

    try:
        response_text = await call_llm(prompt, temperature=temperature, max_tokens=2048)
    except (RuntimeError, OSError, ConnectionError, ValueError, TypeError):
        logger.error("creative_director.dialogue_style.llm_failed", project_id=project_id)
        return []

    try:
        data = _parse_llm_response(response_text)
    except (ValueError, TypeError, KeyError):
        logger.error(
            "creative_director.dialogue_style.parse_failed",
            project_id=project_id,
            raw_response=response_text[:500],
        )
        return []

    raw_cards = data.get("style_cards", [])
    if not isinstance(raw_cards, list):
        logger.warning("creative_director.dialogue_style.invalid_format", project_id=project_id)
        return []

    style_cards: list[DialogueStyleCard] = []
    for raw in raw_cards:
        if not isinstance(raw, dict):
            continue
        card = _build_dialogue_style_card(raw, project_id)
        if card is not None:
            style_cards.append(card)

    logger.info(
        "creative_director.dialogue_style.complete",
        project_id=project_id,
        generated_count=len(style_cards),
    )
    return style_cards


def _build_dialogue_style_card(data: dict[str, Any], project_id: str) -> DialogueStyleCard | None:
    """从 LLM 响应构建 DialogueStyleCard，处理缺失字段和越界值."""
    character_id = data.get("character_id", "")
    if not character_id:
        return None

    from datetime import datetime

    # 验证枚举值
    sentence_len = data.get("sentence_length_preference", "mixed")
    if sentence_len not in {"short", "medium", "long", "mixed"}:
        sentence_len = "mixed"

    metaphor_freq = data.get("metaphor_frequency", "moderate")
    if metaphor_freq not in {"rare", "moderate", "frequent"}:
        metaphor_freq = "moderate"

    interrupt_freq = data.get("interrupt_frequency", "moderate")
    if interrupt_freq not in {"rare", "moderate", "frequent"}:
        interrupt_freq = "moderate"

    def _str_or_empty(val: Any) -> str:
        return str(val) if isinstance(val, str) else ""

    def _str_list(val: Any) -> list[str]:
        if isinstance(val, list):
            return [str(v) for v in val if isinstance(v, (str, int, float))]
        return []

    return DialogueStyleCard(
        character_id=character_id,
        project_id=project_id,
        sentence_length_preference=sentence_len,
        common_openers=_str_list(data.get("common_openers")),
        common_closers=_str_list(data.get("common_closers")),
        anger_expression=_str_or_empty(data.get("anger_expression")),
        fear_expression=_str_or_empty(data.get("fear_expression")),
        joy_expression=_str_or_empty(data.get("joy_expression")),
        sadness_expression=_str_or_empty(data.get("sadness_expression")),
        metaphor_frequency=metaphor_freq,
        irony_usage=bool(data.get("irony_usage", False)),
        rhetorical_question_habit=bool(data.get("rhetorical_question_habit", False)),
        interrupt_frequency=interrupt_freq,
        pause_habit=_str_or_empty(data.get("pause_habit")),
        education_level_hint=_str_or_empty(data.get("education_level_hint")),
        social_role_speech_pattern=_str_or_empty(data.get("social_role_speech_pattern")),
        generated_at=datetime.now().isoformat(),
    )
