"""SummaryWriter — 基于 accepted version + settlement 生成结构化摘要."""

from __future__ import annotations

import uuid

import structlog
from structlog.contextvars import bind_contextvars

from songyan.db.context_repo import SummaryRepository
from songyan.llm.client import call_llm
from songyan.llm.parsing import parse_llm_response
from songyan.models import ChapterSummary, StateSettlement

logger = structlog.get_logger(__name__)

# Task 110b: summary 长度上限
_MAX_PLOT_SUMMARY_LENGTH = 200  # 模板化后关键事件部分上限
_MAX_EMOTIONAL_TONE_LENGTH = 20
_MAX_TEMPLATE_TOTAL_LENGTH = 500

# 模板各部分上限
_MAX_KEY_EVENTS_LENGTH = 200
_MAX_CHAR_CHANGES_LENGTH = 80
_MAX_SETTING_FORESHADOWING_LENGTH = 80
_MAX_EMOTION_TURN_LENGTH = 40
_MAX_HOOK_LENGTH = 60

#  protagonist 决策变化关键词（用于关键事实验证）
_PROTAGONIST_DECISION_KEYWORDS = [
    "决定", "选择", "意识到", "明白", "决心", "立志", "发誓", "承诺",
    "accept", "decide", "realize", "choose", "determine", "resolve",
]


def _build_prompt(content: str, settlement: StateSettlement) -> str:
    """构建 SummaryWriter Prompt."""
    from songyan.prompts import render_agent_prompt

    # 构建 settlement 摘要文本
    settlement_text = "## StateSettlement\n"
    if settlement.character_updates:
        settlement_text += "\n### 角色变更\n"
        for cu in settlement.character_updates:
            settlement_text += f"- {cu.character_id}: {cu.field} {cu.old_value} → {cu.new_value}\n"
    if settlement.new_settings:
        settlement_text += "\n### 新设定\n"
        for ns in settlement.new_settings:
            settlement_text += f"- {ns.setting_name}: {ns.description}\n"
    if settlement.foreshadowing_updates:
        settlement_text += "\n### 伏笔操作\n"
        for fu in settlement.foreshadowing_updates:
            settlement_text += f"- {fu.operation}: {fu.description}\n"
    if settlement.numerical_updates:
        settlement_text += "\n### 数值变更\n"
        for nu in settlement.numerical_updates:
            settlement_text += (
                f"- {nu.character_id}.{nu.attribute_name}: "
                f"{nu.opening_value} → {nu.closing_value}\n"
            )

    # 截取正文前 2000 字和后 1000 字（摘要不需要全文）
    content_preview = content[:2000]
    if len(content) > 3000:
        content_preview += "\n\n...[中间省略]...\n\n" + content[-1000:]

    return render_agent_prompt(
        "summary_writer",
        {
            "settlement_text": settlement_text,
            "content_preview": content_preview,
        },
    )


def _extract_characters_from_settlement(settlement: StateSettlement) -> list[str]:
    """从 settlement 中提取出场角色列表."""
    chars: set[str] = set()
    for cu in settlement.character_updates:
        chars.add(cu.character_id)
    for nu in settlement.numerical_updates:
        chars.add(nu.character_id)
    return sorted(chars)


def _normalize_text_length(text: str, max_length: int) -> str:
    """截断文本到最大长度，保留完整句子边界."""
    if len(text) <= max_length:
        return text
    # 在 max_length 内找最后一个句号/换行，优先保留语义完整
    for sep in ("\n", "。", "；", "，", ".", ";"):
        idx = text.rfind(sep, 0, max_length)
        if idx > max_length * 0.7:
            return text[: idx + 1]
    # 无合适分隔符时硬截断并加省略号
    return text[: max_length - 3].rstrip() + "..."


def _normalize_summary(
    summary: ChapterSummary, settlement: StateSettlement
) -> ChapterSummary:
    """对 LLM 生成的 summary 做生产端后处理：模板化 + 截断 + 兜底.

    输出格式固定为 5 部分：
    - 关键事件（plot_summary 截断到 200 字）
    - 角色变化（settlement.character_updates 提取，最多 80 字）
    - 新设定伏笔（settlement.new_settings + foreshadowing，最多 80 字）
    - 情绪转折（emotional_tone，最多 40 字）
    - 下章钩子（plot_summary 最后一句，最多 60 字）

    总长度不超过 500 字。
    """
    parts: list[str] = []

    # 1. 关键事件 — 使用 plot_summary，截断到 200 字
    plot_text = _normalize_text_length(summary.summary, _MAX_KEY_EVENTS_LENGTH)
    parts.append(f"【关键事件】{plot_text}")

    # 2. 角色变化 — 从 settlement 提取，最多 80 字
    char_changes: list[str] = []
    for cu in settlement.character_updates[:3]:
        char_changes.append(f"{cu.character_id}的{cu.field}变化")
    if char_changes:
        changes_text = _normalize_text_length("、".join(char_changes), _MAX_CHAR_CHANGES_LENGTH)
        parts.append(f"【角色变化】{changes_text}")

    # 3. 新设定/伏笔 — 从 settlement 提取，最多 80 字
    setting_fs: list[str] = []
    for ns in settlement.new_settings[:2]:
        setting_fs.append(ns.setting_name)
    for fu in settlement.foreshadowing_updates[:2]:
        if fu.operation == "plant":
            setting_fs.append(f"伏笔:{fu.description[:10]}")
    if setting_fs:
        sf_text = _normalize_text_length("、".join(setting_fs), _MAX_SETTING_FORESHADOWING_LENGTH)
        parts.append(f"【新设定伏笔】{sf_text}")

    # 4. 情绪转折 — 最多 40 字
    emotion_text = summary.emotional_tone[:_MAX_EMOTION_TURN_LENGTH]
    parts.append(f"【情绪转折】{emotion_text}")

    # 5. 下章钩子 — 从 plot_summary 提取最后一句有意义的话，最多 60 字
    hook = ""
    for sep in ("……", "。", "！", "？", "；", ".", "!", "?"):
        if sep in summary.summary:
            idx = summary.summary.rfind(sep)
            if idx > 0:
                candidate = summary.summary[:idx].strip()
                # 找倒数第二个分隔符
                last_sep_idx = max(
                    candidate.rfind("。"),
                    candidate.rfind("！"),
                    candidate.rfind("？"),
                    candidate.rfind("."),
                    candidate.rfind("!"),
                    candidate.rfind("?"),
                )
                if last_sep_idx > 0:
                    hook = candidate[last_sep_idx + 1 :].strip()
                else:
                    hook = candidate.strip()
                if len(hook) >= 5:
                    break
    if hook:
        hook_text = _normalize_text_length(hook, _MAX_HOOK_LENGTH)
        parts.append(f"【下章钩子】{hook_text}")

    summary.summary = "\n".join(parts)

    # 总长度兜底截断到 500 字
    if len(summary.summary) > _MAX_TEMPLATE_TOTAL_LENGTH:
        summary.summary = summary.summary[: _MAX_TEMPLATE_TOTAL_LENGTH]

    # emotional_tone 截断到 20 字
    summary.emotional_tone = summary.emotional_tone[:_MAX_EMOTIONAL_TONE_LENGTH]
    return summary


def _validate_summary_facts(
    summary: ChapterSummary,
    settlement: StateSettlement,
) -> list[str]:
    """检查 summary 是否覆盖了关键事实.

    返回缺失项列表，仅用于日志，不阻塞 accept。
    """
    missing: list[str] = []

    # 1. 是否包含 protagonist 决策变化
    has_decision = any(kw in summary.summary for kw in _PROTAGONIST_DECISION_KEYWORDS)
    if not has_decision:
        missing.append("缺少主角决策/认知变化")

    # 2. 新设定是否被记录
    for setting in settlement.new_settings:
        if setting.setting_name and setting.setting_name not in summary.summary:
            missing.append(f"新设定未记录: {setting.setting_name}")

    # 3. 新伏笔是否被记录（简化：检查 description 关键词）
    for fs in settlement.foreshadowing_updates:
        if fs.operation == "plant" and fs.description:
            # 取前 6 个字符作为关键词
            keyword = fs.description[:6]
            if keyword and keyword not in summary.summary:
                missing.append(f"新伏笔未记录: {fs.description[:20]}")

    return missing


def _extract_key_events_from_settlement(settlement: StateSettlement) -> list[str]:
    """从 settlement 中提取关键事件列表."""
    events: list[str] = []
    for cu in settlement.character_updates:
        events.append(f"{cu.character_id} 的 {cu.field} 变为 {cu.new_value}")
    for ns in settlement.new_settings:
        events.append(f"揭示新设定：{ns.setting_name}")
    for fu in settlement.foreshadowing_updates:
        if fu.operation == "plant":
            events.append(f"埋下伏笔：{fu.description}")
        elif fu.operation == "resolve":
            events.append(f"回收伏笔：{fu.description}")
    return events if events else ["章节推进"]


async def write_chapter_summary(
    content: str,
    settlement: StateSettlement,
    project_id: str,
    chapter_number: int,
    db: SummaryRepository,
    *,
    temperature: float = 0.3,
) -> tuple[str, ChapterSummary]:
    """基于 accepted version + settlement 生成结构化摘要.

    优先从 settlement 中提取结构化信息，plot_summary 调用轻量 LLM。

    Args:
        content: 章节正文（accepted version）
        settlement: 状态结算结果
        project_id: 项目 ID
        chapter_number: 章节号
        db: SummaryRepository

    Returns:
        真实落库的 summary_id 与 ChapterSummary
    """
    bind_contextvars(agent="summary_writer")
    prompt = _build_prompt(content, settlement)

    # 调用 LLM 生成 plot_summary 和 emotional_tone
    llm_raw = await call_llm(prompt, temperature=temperature)
    data = parse_llm_response(llm_raw)

    # 从 settlement 中提取结构化信息
    key_events = _extract_key_events_from_settlement(settlement)
    characters_appeared = _extract_characters_from_settlement(settlement)

    # LLM 可能提供更多 key_events 和 characters，合并去重
    if isinstance(data, dict):
        llm_events = data.get("key_events", [])
        if isinstance(llm_events, list):
            key_events = list(dict.fromkeys(key_events + llm_events))  # 去重保序
        llm_chars = data.get("characters_appeared", [])
        if isinstance(llm_chars, list):
            characters_appeared = list(dict.fromkeys(characters_appeared + llm_chars))
        plot_summary = data.get("plot_summary", "")
        emotional_tone = data.get("emotional_tone", "")
    else:
        plot_summary = ""
        emotional_tone = ""

    # fallback：如果 LLM 没生成 plot_summary，用简单的代码摘要
    if not plot_summary:
        plot_summary = "第{}章：{}。".format(chapter_number, "、".join(key_events[:3]))
    if not emotional_tone:
        emotional_tone = "中性"

    summary = ChapterSummary(
        chapter_number=chapter_number,
        summary=plot_summary,
        key_events=key_events,
        characters_appeared=characters_appeared,
        emotional_tone=emotional_tone,
        impact_score=settlement.impact_score,
    )

    # Task 110b: 关键事实验证（在模板化之前检查原始 LLM 输出，不阻塞，仅日志）
    missing_facts = _validate_summary_facts(summary, settlement)
    if missing_facts:
        logger.warning(
            "summary_writer.missing_facts",
            project_id=project_id,
            chapter_number=chapter_number,
            missing_facts=missing_facts,
        )

    # Task 110b: 生产端后处理 — 模板化 + 长度控制
    summary = _normalize_summary(summary, settlement)

    # 保存到 summaries 表
    summary_id = f"sum-{project_id}-{chapter_number}-{uuid.uuid4().hex[:8]}"
    await _save_summary(db, summary_id, project_id, chapter_number, summary)

    logger.info(
        "summary_writer.generated",
        summary_id=summary_id,
        project_id=project_id,
        chapter_number=chapter_number,
        key_event_count=len(key_events),
        character_count=len(characters_appeared),
        summary_length=len(summary.summary),
        emotional_tone_length=len(summary.emotional_tone),
    )
    return summary_id, summary


async def _save_summary(
    db: SummaryRepository,
    summary_id: str,
    project_id: str,
    chapter_number: int,
    summary: ChapterSummary,
) -> None:
    """保存摘要到 summaries 表."""
    await db.create(summary, project_id, summary_id)
