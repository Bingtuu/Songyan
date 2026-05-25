"""SummaryWriter — 基于 accepted version + settlement 生成结构化摘要."""

from __future__ import annotations

import uuid

import structlog

from songyan.db.context_repo import SummaryRepository
from songyan.llm.client import call_llm
from songyan.llm.parsing import parse_llm_response
from songyan.models import ChapterSummary, StateSettlement
from songyan.prompts import get_prompt_loader

logger = structlog.get_logger(__name__)


def _build_prompt(content: str, settlement: StateSettlement) -> str:
    """构建 SummaryWriter Prompt."""
    loader = get_prompt_loader()
    card = loader.load_card("summary_writer")
    system_prompt = card.system_prompt

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

    return (
        f"{system_prompt}\n\n{settlement_text}\n\n"
        f"## 章节正文（节选）\n\n{content_preview}\n\n"
        "请输出 JSON 格式的摘要。"
    )


def _extract_characters_from_settlement(settlement: StateSettlement) -> list[str]:
    """从 settlement 中提取出场角色列表."""
    chars: set[str] = set()
    for cu in settlement.character_updates:
        chars.add(cu.character_id)
    for nu in settlement.numerical_updates:
        chars.add(nu.character_id)
    return sorted(chars)


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
) -> ChapterSummary:
    """基于 accepted version + settlement 生成结构化摘要.

    优先从 settlement 中提取结构化信息，plot_summary 调用轻量 LLM。

    Args:
        content: 章节正文（accepted version）
        settlement: 状态结算结果
        project_id: 项目 ID
        chapter_number: 章节号
        db: SummaryRepository

    Returns:
        ChapterSummary
    """
    prompt = _build_prompt(content, settlement)

    # 调用 LLM 生成 plot_summary 和 emotional_tone
    llm_raw = await call_llm(
        prompt=prompt,
        temperature=0.3,
        max_tokens=800,
        expect_json=True,
    )
    parsed = parse_llm_response(llm_raw, expect_json=True)
    data = parsed.data if parsed.data else {}

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
    )

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
    )
    return summary


async def _save_summary(
    db: SummaryRepository,
    summary_id: str,
    project_id: str,
    chapter_number: int,
    summary: ChapterSummary,
) -> None:
    """保存摘要到 summaries 表.

    SummaryRepository 目前只有 list_recent，这里直接操作底层 DB。
    """
    from songyan.db.connection import get_db
    from songyan.db.repository import _to_json

    async with get_db() as conn:
        await conn.execute(
            """INSERT INTO summaries (
                summary_id, project_id, chapter_number,
                plot_summary, key_events, characters_appeared, emotional_tone
            ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                summary_id,
                project_id,
                chapter_number,
                summary.summary,
                _to_json(summary.key_events),
                _to_json(summary.characters_appeared),
                summary.emotional_tone,
            ),
        )
        await conn.commit()
    logger.info(
        "repository.write",
        table="summaries",
        operation="insert",
        summary_id=summary_id,
    )
