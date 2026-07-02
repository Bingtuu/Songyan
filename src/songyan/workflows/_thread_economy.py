"""Thread economy — settlement 后处理：依据本章证据推进 PlotThread 状态（V6 Task 144）.

MVP：只做"正文进展驱动的自动状态推进"，基于 settlement 已产出的结构化证据做
可解释、可单测的规则映射；不新增 LLM 调用、不新增 Agent、不做显式作废（阶段 B/152）。
状态更新集中在 service 层，Writer/CreativeDirector 不直接写 DB。

收束防过早（2026-07-01 冒烟测试后加固）：主线核心名词（如"灰塔"）会频繁出现在局部
章末钩子/伏笔里，若仅凭关键词命中就收束会把主线线索过早判 resolved。因此收束受两道闸门：
1. **advanced 优先**：必须先 `opened→advanced`，禁止 `opened` 直接 `resolved`（保证 T1 链）；
2. **计划收束弧窗口**：只有当前章进入线索 `expected_resolve_arc` 对应弧的起始章后才允许收束；
   收束弧未定义/未到达则不自动收束（None 时退化为仅靠 advanced + 收束信号）。
"""

from __future__ import annotations

from songyan.db.connection import get_db
from songyan.db.narrative_repo import NarrativeRepository
from songyan.models import PlotThread, PlotThreadStatus
from songyan.models.settlement import StateSettlement

# 参与自动推进的"未收束"状态
_ACTIVE_STATUSES: tuple[PlotThreadStatus, ...] = ("planned", "opened", "advanced")


def _settlement_evidence_text(settlement: StateSettlement) -> str:
    """汇总本章 settlement 的全部文本证据（用于判定线索是否被推进）."""
    parts: list[str] = []
    for fu in settlement.foreshadowing_updates:
        parts.append(fu.description or "")
    for ns in settlement.new_settings:
        parts.append(ns.setting_name or "")
        parts.append(ns.description or "")
    for cu in settlement.character_updates:
        parts.append(cu.new_value or "")
    parts.extend(settlement.planted_hooks)
    parts.extend(settlement.resolved_hooks)
    parts.extend(settlement.open_threads)
    return "\n".join(p for p in parts if p)


def _settlement_resolved_text(settlement: StateSettlement) -> str:
    """汇总本章"收束"信号（伏笔 resolve + resolved_hooks），用于判定线索收束."""
    parts: list[str] = list(settlement.resolved_hooks)
    for fu in settlement.foreshadowing_updates:
        if fu.operation == "resolve":
            parts.append(fu.description or "")
    return "\n".join(p for p in parts if p)


def _thread_referenced(thread: PlotThread, text: str) -> bool:
    """线索是否被文本引用：thread_id 或非空 title 出现在证据文本中."""
    if not text:
        return False
    if thread.thread_id and thread.thread_id in text:
        return True
    return bool(thread.title) and thread.title in text


def _resolve_window_open(
    expected_resolve_arc: int | None,
    chapter_number: int,
    arc_start_by_index: dict[int, int],
) -> bool:
    """线索是否已进入其计划收束弧窗口（避免主线线索被过早收束）.

    - `expected_resolve_arc is None`：无计划收束弧，退化为仅靠 advanced + 收束信号（返回 True）。
    - 计划收束弧存在：当前章 >= 该弧起始章时窗口开启。
    - 计划收束弧未定义（大纲里没有该 arc_index）/尚未到达：窗口关闭，不自动收束。
    """
    if expected_resolve_arc is None:
        return True
    start = arc_start_by_index.get(expected_resolve_arc)
    if start is None:
        return False
    return chapter_number >= start


def _next_status(
    current: str,
    resolved: bool,
    *,
    expected_resolve_arc: int | None,
    chapter_number: int,
    arc_start_by_index: dict[int, int],
) -> PlotThreadStatus | None:
    """给定当前状态与证据，返回下一个状态；无需变更时返回 None.

    规则（MVP，加固版）：
    - planned  → opened（首次被推进）
    - opened   → advanced（继续推进；**禁止**直接 resolved，保证 opened→advanced→resolved 链）
    - advanced → resolved（有收束信号 **且** 已进入计划收束弧窗口）否则 None（保持 advanced）
    """
    if current == "planned":
        return "opened"
    if current == "opened":
        return "advanced"
    if current == "advanced":
        if resolved and _resolve_window_open(
            expected_resolve_arc, chapter_number, arc_start_by_index
        ):
            return "resolved"
        return None
    return None


async def update_plot_threads_after_settlement(
    project_id: str,
    chapter_number: int,
    version_id: str,
    settlement: StateSettlement,
    narrative_repo: NarrativeRepository | None = None,
) -> list[str]:
    """依据本章 settlement 证据推进相关 PlotThread 状态.

    Args:
        project_id: 项目 ID。
        chapter_number: 本章章节号。
        version_id: 本章 accepted 版本 ID（写入 last_status_version_id，T1 可追溯）。
        settlement: 本章结算结果。
        narrative_repo: 可选注入（默认新建）。

    Returns:
        本章发生状态变更的 thread_id 列表（无骨架/无变更时为空）。
    """
    repo = narrative_repo or NarrativeRepository()

    active: list[PlotThread] = []
    for status in _ACTIVE_STATUSES:
        active.extend(await repo.list_threads(project_id, status=status))
    if not active:
        return []

    arcs = await repo.list_arc_plans(project_id)
    arc_start_by_index = {a.arc_index: a.start_chapter for a in arcs}

    evidence = _settlement_evidence_text(settlement)
    resolved_evidence = _settlement_resolved_text(settlement)

    # 先在内存中算出所有待推进的 (thread_id, new_status)，再在单事务内批量提交，
    # 保证一章引用多条线索时的状态推进是原子的（要么全成功、要么全回滚，#3 修复）。
    pending: list[tuple[str, PlotThreadStatus]] = []
    for thread in active:
        if not _thread_referenced(thread, evidence):
            continue
        resolved = _thread_referenced(thread, resolved_evidence)
        new_status = _next_status(
            thread.status,
            resolved,
            expected_resolve_arc=thread.expected_resolve_arc,
            chapter_number=chapter_number,
            arc_start_by_index=arc_start_by_index,
        )
        if new_status is None:
            continue
        pending.append((thread.thread_id, new_status))

    if not pending:
        return []

    changed: list[str] = []
    async with get_db() as conn:
        for thread_id, new_status in pending:
            await repo.advance_thread_status(
                thread_id, new_status, chapter_number, version_id, conn=conn
            )
            changed.append(thread_id)
        await conn.commit()
    return changed
