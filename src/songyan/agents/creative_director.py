"""CreativeDirector Agent — 创作导演，生成 CreativeBrief."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import structlog

from songyan.db.review_repo import CreativeBriefRepository
from songyan.exceptions import LLMError, LLMResponseParseError
from songyan.llm.client import call_llm
from songyan.models.chapter import ChapterGoal
from songyan.models.character import Character
from songyan.models.creative_mode import CreativeBrief, CreativeModeProfile, Tension
from songyan.models.genre import GenreProfile

logger = structlog.get_logger(__name__)

PROMPT_PATH = (
    Path(__file__).parent.parent.parent.parent / "prompts" / "creative_director.md"
)

VALID_TENSION_TYPES = {
    "value_conflict",
    "information_asymmetry",
    "power_imbalance",
    "emotional_contrast",
    "temporal_pressure",
}

MIN_FORBIDDEN_PATTERNS = 3
DEFAULT_FORBIDDEN_PATTERNS = [
    "避免使用陈词滥调的表达方式",
    "禁止空洞的环境描写堆砌",
    "不要让角色做出毫无铺垫的行为转变",
]


def _load_prompt_template() -> str:
    """加载 CreativeDirector Prompt 模板."""
    if not PROMPT_PATH.exists():
        msg = f"Prompt 模板未找到: {PROMPT_PATH}"
        raise FileNotFoundError(msg)
    return PROMPT_PATH.read_text(encoding="utf-8")


def _render_prompt(
    template: str,
    *,
    chapter_goal: ChapterGoal,
    genre_profile: GenreProfile,
    mode_profile: CreativeModeProfile,
    characters: list[Character],
    previous_summary: str,
) -> str:
    """用 Jinja2 渲染 Prompt 模板."""
    try:
        from jinja2 import Template
    except ImportError:
        return _simple_render(
            template,
            chapter_goal=chapter_goal,
            genre_profile=genre_profile,
            mode_profile=mode_profile,
            characters=characters,
            previous_summary=previous_summary,
        )

    jinja_template = Template(template)
    return jinja_template.render(
        mode_id=mode_profile.id,
        genre_name=genre_profile.name,
        mode_name=mode_profile.name,
        protagonist_name=_get_protagonist_name(characters),
        core_hook=genre_profile.name,  # 简化：用题材名代替
        tone=genre_profile.name,
        genre_satisfaction_types=", ".join(genre_profile.satisfaction_types)
        if genre_profile.satisfaction_types
        else "无",
        genre_pacing_rule=genre_profile.pacing_rule or "无特殊规则",
        genre_taboos=", ".join(genre_profile.taboos)
        if genre_profile.taboos
        else "无",
        chapter_goal_json=chapter_goal.model_dump_json(indent=2),
        recent_summaries=previous_summary or "（本章为开篇章节，无前置剧情）",
        character_states=_format_characters(characters),
        mode_constraints=_format_mode_constraints(mode_profile),
    )


def _simple_render(
    template: str,
    *,
    chapter_goal: ChapterGoal,
    genre_profile: GenreProfile,
    mode_profile: CreativeModeProfile,
    characters: list[Character],
    previous_summary: str,
) -> str:
    """无 Jinja2 时的降级字符串替换."""
    variables = {
        "mode_id": mode_profile.id,
        "genre_name": genre_profile.name,
        "mode_name": mode_profile.name,
        "protagonist_name": _get_protagonist_name(characters),
        "core_hook": genre_profile.name,
        "tone": genre_profile.name,
        "genre_satisfaction_types": ", ".join(genre_profile.satisfaction_types)
        if genre_profile.satisfaction_types
        else "无",
        "genre_pacing_rule": genre_profile.pacing_rule or "无特殊规则",
        "genre_taboos": ", ".join(genre_profile.taboos)
        if genre_profile.taboos
        else "无",
        "chapter_goal_json": chapter_goal.model_dump_json(indent=2),
        "recent_summaries": previous_summary or "（本章为开篇章节，无前置剧情）",
        "character_states": _format_characters(characters),
        "mode_constraints": _format_mode_constraints(mode_profile),
    }
    result = template
    for key, value in variables.items():
        result = result.replace(f"{{{{ {key} }}}}", value)
        result = result.replace(f"{{{{{key}}}}}", value)
    return result


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
        lines.append(
            f"- {char.name}（{char.role_type}）: {char.background or '背景未设定'}"
        )
        if char.personality_traits:
            lines.append(f"  性格: {', '.join(char.personality_traits)}")
        if char.goals:
            lines.append(f"  目标: {', '.join(char.goals)}")
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
        lines.append(
            f"- 审查维度: {', '.join(mode_profile.active_audit_dimensions)}"
        )
    return "\n".join(lines)


def _extract_json(text: str) -> str:
    """从 LLM 响应中提取 JSON 字符串."""
    import re

    code_block_match = re.search(
        r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL
    )
    if code_block_match:
        return code_block_match.group(1).strip()

    json_match = re.search(r"(\{.*\})", text, re.DOTALL)
    if json_match:
        return json_match.group(1).strip()

    return text.strip()


def _parse_llm_response(text: str) -> dict[str, Any]:
    """解析 LLM 响应为字典."""
    json_text = _extract_json(text)
    try:
        return json.loads(json_text)
    except json.JSONDecodeError as e:
        msg = f"LLM 返回内容无法解析为 JSON: {e}"
        raise LLMResponseParseError(msg, raw_response=text) from e


def _validate_tension(tension_data: dict[str, Any]) -> Tension | None:
    """验证并构建 Tension 对象，无效时返回 None."""
    tension_type = tension_data.get("tension_type", "")
    if tension_type not in VALID_TENSION_TYPES:
        logger.warning(
            "creative_director.invalid_tension_type",
            received=tension_type,
            valid=list(VALID_TENSION_TYPES),
        )
        return None

    intensity = tension_data.get("intensity", 0.5)
    try:
        intensity = float(intensity)
        intensity = max(0.0, min(1.0, intensity))
    except (ValueError, TypeError):
        intensity = 0.5

    characters_involved = tension_data.get("characters_involved", [])
    if not isinstance(characters_involved, list):
        characters_involved = []

    return Tension(
        tension_id=tension_data.get("tension_id", "")
        or f"tension_{uuid.uuid4().hex[:6]}",
        description=(
            tension_data.get("description", "")
            if isinstance(tension_data.get("description"), str)
            else ""
        ),
        tension_type=tension_type,
        characters_involved=[str(c) for c in characters_involved],
        resolution=(
            tension_data.get("resolution", "")
            if isinstance(tension_data.get("resolution"), str)
            else ""
        ),
        intensity=intensity,
    )


def _ensure_forbidden_patterns(patterns: list[Any]) -> list[str]:
    """确保 forbidden_patterns 至少 MIN_FORBIDDEN_PATTERNS 个具体条目."""
    valid = [str(p) for p in patterns if isinstance(p, str) and p.strip()]
    if len(valid) < MIN_FORBIDDEN_PATTERNS:
        needed = MIN_FORBIDDEN_PATTERNS - len(valid)
        valid.extend(DEFAULT_FORBIDDEN_PATTERNS[:needed])
        logger.warning(
            "creative_director.patterns_filled",
            original_count=len(valid) - needed,
            filled_count=needed,
        )
    return valid


def _build_creative_brief(
    data: dict[str, Any],
    mode_id: str,
    chapter_goal: ChapterGoal,
) -> CreativeBrief:
    """从解析后的字典构建 CreativeBrief，处理缺失字段和越界值."""
    # 解析 required_tensions
    tensions: list[Tension] = []
    raw_tensions = data.get("required_tensions", [])
    if isinstance(raw_tensions, list):
        for item in raw_tensions:
            if isinstance(item, dict):
                tension = _validate_tension(item)
                if tension is not None:
                    tensions.append(tension)

    # 解析 forbidden_patterns
    raw_patterns = data.get("forbidden_patterns", [])
    if isinstance(raw_patterns, list):
        forbidden_patterns = _ensure_forbidden_patterns(raw_patterns)
    else:
        forbidden_patterns = DEFAULT_FORBIDDEN_PATTERNS.copy()

    # 解析其他列表字段
    def _to_str_list(value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(v) for v in value if isinstance(v, (str, int, float))]
        return []

    return CreativeBrief(
        mode_id=data.get("mode_id", mode_id),
        chapter_goal=chapter_goal,
        creative_intent=(
            data.get("creative_intent", "")
            if isinstance(data.get("creative_intent"), str)
            else ""
        ),
        required_tensions=tensions,
        forbidden_patterns=forbidden_patterns,
        allowed_fissures=_to_str_list(data.get("allowed_fissures")),
        style_constraints=_to_str_list(data.get("style_constraints")),
        reader_contract=(
            data.get("reader_contract", "")
            if isinstance(data.get("reader_contract"), str)
            else ""
        ),
        polyphony_notes=_to_str_list(data.get("polyphony_notes")),
    )


async def generate_creative_brief(
    db: CreativeBriefRepository,
    project_id: str,
    chapter_goal: ChapterGoal,
    genre_profile: GenreProfile,
    mode_profile: CreativeModeProfile,
    characters: list[Character],
    previous_summary: str = "",
) -> CreativeBrief:
    """生成本章创作导演简报.

    1. 加载并渲染 Prompt 模板
    2. 调用 LLM（temperature=0.7）
    3. 解析 JSON 输出为 CreativeBrief
    4. 通过 Repository 保存
    5. 返回 CreativeBrief

    Args:
        db: CreativeBrief 数据访问层
        project_id: 项目唯一标识
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
    template = _load_prompt_template()
    prompt = _render_prompt(
        template,
        chapter_goal=chapter_goal,
        genre_profile=genre_profile,
        mode_profile=mode_profile,
        characters=characters,
        previous_summary=previous_summary,
    )

    # 调用 LLM
    try:
        response_text = await call_llm(prompt, temperature=0.7, max_retries=3)
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

    # 保存到数据库
    brief_id = f"brief_{uuid.uuid4().hex[:12]}"
    await db.create(
        brief,
        brief_id,
        project_id,
        chapter_goal.chapter_number,
    )

    logger.info(
        "creative_director.complete",
        chapter_number=chapter_goal.chapter_number,
        brief_id=brief_id,
        tension_count=len(brief.required_tensions),
        forbidden_count=len(brief.forbidden_patterns),
    )

    return brief
