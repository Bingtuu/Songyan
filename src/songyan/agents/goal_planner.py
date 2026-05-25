"""GoalPlanner Agent — 章节目标制定."""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any

import structlog

from songyan.db.repository import ChapterGoalRepository
from songyan.exceptions import LLMError, LLMResponseParseError
from songyan.llm.client import call_llm
from songyan.models.chapter import ChapterGoal
from songyan.models.creative_mode import CreativeModeProfile
from songyan.models.genre import GenreProfile
from songyan.models.project import ProjectSetting

logger = structlog.get_logger(__name__)

PROMPT_PATH = Path(__file__).parent.parent.parent.parent / "prompts" / "goal_planner.md"

# 默认值常量
MIN_WORD_COUNT = 2000
MAX_WORD_COUNT = 5000
DEFAULT_WORD_COUNT = 3000


def _load_prompt_template() -> str:
    """加载 GoalPlanner Prompt 模板 — 已迁移到工艺卡系统."""
    from songyan.prompts import get_prompt_loader
    return get_prompt_loader().load_card("goal_planner").system_prompt


def _render_prompt(
    template: str,
    *,
    chapter_number: int,
    project: ProjectSetting,
    genre_profile: GenreProfile,
    mode_profile: CreativeModeProfile,
    recent_summaries: str,
) -> str:
    """用 Jinja2 渲染 Prompt 模板."""
    try:
        from jinja2 import Template
    except ImportError:
        # 降级：简单字符串替换
        return _simple_render(
            template,
            chapter_number=chapter_number,
            project=project,
            genre_profile=genre_profile,
            mode_profile=mode_profile,
            recent_summaries=recent_summaries,
        )

    jinja_template = Template(template)
    return jinja_template.render(
        chapter_number=chapter_number,
        genre_name=genre_profile.name,
        mode_name=mode_profile.name,
        protagonist_name=project.protagonist_name,
        protagonist_background=project.protagonist_background or "未设定",
        core_hook=project.core_hook or "未设定",
        tone=project.tone,
        target_reader_expectation=project.target_reader_expectation or "未设定",
        taboos=", ".join(project.taboos) if project.taboos else "无",
        genre_pacing_rule=genre_profile.pacing_rule or "无特殊规则",
        genre_satisfaction_types=", ".join(genre_profile.satisfaction_types)
        if genre_profile.satisfaction_types
        else "无",
        genre_chapter_types=", ".join(genre_profile.chapter_types)
        if genre_profile.chapter_types
        else "常规",
        mode_constraints=_format_mode_constraints(mode_profile),
        recent_summaries=recent_summaries or "（本章为开篇章节，无前置剧情）",
    )


def _simple_render(
    template: str,
    *,
    chapter_number: int,
    project: ProjectSetting,
    genre_profile: GenreProfile,
    mode_profile: CreativeModeProfile,
    recent_summaries: str,
) -> str:
    """无 Jinja2 时的降级字符串替换."""
    variables = {
        "chapter_number": str(chapter_number),
        "genre_name": genre_profile.name,
        "mode_name": mode_profile.name,
        "protagonist_name": project.protagonist_name,
        "protagonist_background": project.protagonist_background or "未设定",
        "core_hook": project.core_hook or "未设定",
        "tone": project.tone,
        "target_reader_expectation": project.target_reader_expectation or "未设定",
        "taboos": ", ".join(project.taboos) if project.taboos else "无",
        "genre_pacing_rule": genre_profile.pacing_rule or "无特殊规则",
        "genre_satisfaction_types": ", ".join(genre_profile.satisfaction_types)
        if genre_profile.satisfaction_types
        else "无",
        "genre_chapter_types": ", ".join(genre_profile.chapter_types)
        if genre_profile.chapter_types
        else "常规",
        "mode_constraints": _format_mode_constraints(mode_profile),
        "recent_summaries": recent_summaries or "（本章为开篇章节，无前置剧情）",
    }
    result = template
    for key, value in variables.items():
        result = result.replace(f"{{{{ {key} }}}}", value)
        result = result.replace(f"{{{{{key}}}}}", value)
    return result


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


def _extract_json(text: str) -> str:
    """从 LLM 响应中提取 JSON 字符串.

    处理以下情况：
    - 纯 JSON
    - markdown 代码块包裹的 JSON
    - 前后有额外文本的 JSON
    """
    # 尝试提取 markdown 代码块
    code_block_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if code_block_match:
        return code_block_match.group(1).strip()

    # 尝试提取第一个 JSON 对象
    json_match = re.search(r"(\{.*\})", text, re.DOTALL)
    if json_match:
        return json_match.group(1).strip()

    return text.strip()


def _parse_llm_response(text: str) -> dict[str, Any]:
    """解析 LLM 响应为字典.

    Args:
        text: LLM 返回的原始文本

    Returns:
        解析后的字典

    Raises:
        LLMResponseParseError: 解析失败
    """
    json_text = _extract_json(text)
    try:
        return json.loads(json_text)
    except json.JSONDecodeError as e:
        msg = f"LLM 返回内容无法解析为 JSON: {e}"
        raise LLMResponseParseError(msg, raw_response=text) from e


def _clamp_word_count(value: int) -> int:
    """将字数目标限制在合法范围内."""
    return max(MIN_WORD_COUNT, min(MAX_WORD_COUNT, value))


def _validate_chapter_type(value: str, allowed_types: list[str]) -> str:
    """验证章节类型是否在允许列表中，否则返回第一个允许值."""
    if value in allowed_types:
        return value
    if allowed_types:
        logger.warning(
            "goal_planner.invalid_chapter_type",
            received=value,
            allowed=allowed_types,
            fallback=allowed_types[0],
        )
        return allowed_types[0]
    return value


def _build_chapter_goal(
    data: dict[str, Any],
    chapter_number: int,
    genre_profile: GenreProfile,
) -> ChapterGoal:
    """从解析后的字典构建 ChapterGoal，处理缺失字段和越界值."""
    word_count = data.get("word_count_target", DEFAULT_WORD_COUNT)
    if not isinstance(word_count, int):
        try:
            word_count = int(word_count)
        except (ValueError, TypeError):
            word_count = DEFAULT_WORD_COUNT

    chapter_type = data.get("chapter_type", "")
    if isinstance(chapter_type, str):
        chapter_type = _validate_chapter_type(
            chapter_type,
            genre_profile.chapter_types,
        )
    else:
        chapter_type = genre_profile.chapter_types[0] if genre_profile.chapter_types else ""

    return ChapterGoal(
        chapter_number=chapter_number,
        previous_summary=data.get("previous_summary", ""),
        target_events=(
            data.get("target_events", [])
            if isinstance(data.get("target_events"), list)
            else []
        ),
        emotional_arc=(
            data.get("emotional_arc", "")
            if isinstance(data.get("emotional_arc"), str)
            else ""
        ),
        hooks=(
            data.get("hooks", [])
            if isinstance(data.get("hooks"), list)
            else []
        ),
        obligations=(
            data.get("obligations", [])
            if isinstance(data.get("obligations"), list)
            else []
        ),
        word_count_target=_clamp_word_count(word_count),
        chapter_type=chapter_type,
    )


async def define_chapter_goal(
    db: ChapterGoalRepository,
    project_id: str,
    project: ProjectSetting,
    genre_profile: GenreProfile,
    mode_profile: CreativeModeProfile,
    chapter_number: int,
    previous_summary: str = "",
    character_states: list[dict] | None = None,
) -> ChapterGoal:
    """制定章节目标.

    1. 加载并渲染 Prompt 模板
    2. 调用 LLM（temperature=0.7）
    3. 解析 JSON 输出为 ChapterGoal
    4. 通过 Repository 保存
    5. 返回 ChapterGoal

    Args:
        db: ChapterGoal 数据访问层
        project_id: 项目唯一标识
        project: 项目设定
        genre_profile: 题材规则
        mode_profile: 创作模式约束
        chapter_number: 章节号
        previous_summary: 最近剧情摘要
        character_states: 角色当前状态快照（可选，当前版本不注入 Prompt）

    Returns:
        生成的章节目标

    Raises:
        LLMError: LLM 调用失败
        LLMResponseParseError: 响应解析失败
    """
    logger.info(
        "goal_planner.start",
        chapter_number=chapter_number,
        project_title=project.title,
        genre=genre_profile.id,
        mode=mode_profile.id,
    )

    # 加载并渲染 Prompt
    template = _load_prompt_template()
    prompt = _render_prompt(
        template,
        chapter_number=chapter_number,
        project=project,
        genre_profile=genre_profile,
        mode_profile=mode_profile,
        recent_summaries=previous_summary,
    )

    # 调用 LLM
    try:
        response_text = await call_llm(prompt, temperature=0.7, max_retries=3)
    except LLMError:
        logger.error("goal_planner.llm_failed", chapter_number=chapter_number)
        raise

    # 解析响应
    try:
        data = _parse_llm_response(response_text)
    except LLMResponseParseError:
        logger.error(
            "goal_planner.parse_failed",
            chapter_number=chapter_number,
            raw_response=response_text[:500],
        )
        raise

    # 构建 ChapterGoal（含字段验证和修正）
    goal = _build_chapter_goal(data, chapter_number, genre_profile)

    # 保存到数据库
    goal_id = f"goal_{uuid.uuid4().hex[:12]}"
    await db.create(goal, goal_id, project_id)

    logger.info(
        "goal_planner.complete",
        chapter_number=chapter_number,
        goal_id=goal_id,
        word_count_target=goal.word_count_target,
        chapter_type=goal.chapter_type,
        event_count=len(goal.target_events),
    )

    return goal
