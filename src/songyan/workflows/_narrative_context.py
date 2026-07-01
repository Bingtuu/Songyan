"""Narrative goal context loader (V6 阶段 0 / Task 143a).

给 GoalPlanner 提供"自顶向下"的派生上下文：当前弧目标 + 本弧未收束线索 +
临近兑现伏笔。无骨架（无大纲或章节超出规划范围）时返回 ``has_skeleton=False``，
供 GoalPlanner 回退到旧行为。
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from songyan.db.narrative_repo import NarrativeRepository
from songyan.db.settlement_repo import ForeshadowingRepository
from songyan.models import PlotThread

# 未收束线索的状态集合
_OPEN_STATUSES = ("opened", "advanced")


class NarrativeGoalContext(BaseModel):
    """GoalPlanner 用的骨架派生上下文（无骨架时全空 + has_skeleton=False）."""

    has_skeleton: bool = False
    arc_goal: str = ""
    arc_index: int | None = None
    is_mainline_arc: bool = False
    open_threads: list[dict] = Field(default_factory=list)       # 本弧未收束线索
    threads_to_resolve: list[dict] = Field(default_factory=list)  # 本弧应收束线索
    due_foreshadowings: list[dict] = Field(default_factory=list)  # 临近兑现伏笔


def _thread_brief(thread: PlotThread) -> dict:
    return {
        "thread_id": thread.thread_id,
        "title": thread.title,
        "status": thread.status,
        "is_mainline": thread.is_mainline,
    }


async def load_narrative_goal_context(
    project_id: str,
    chapter_number: int,
    repo: NarrativeRepository | None = None,
    foreshadowing_repo: ForeshadowingRepository | None = None,
    *,
    due_window: int = 5,
) -> NarrativeGoalContext:
    """从骨架表 + 现有伏笔表组装 GoalPlanner 上下文.

    Args:
        project_id: 项目 ID。
        chapter_number: 当前章节号。
        repo: NarrativeRepository（默认新建）。
        foreshadowing_repo: 复用现有伏笔查询（默认新建）；不新增伏笔机制。
        due_window: "临近兑现" 窗口——expected_resolve_chapter 落在
            ``[chapter_number, chapter_number + due_window]`` 内视为临近。

    Returns:
        NarrativeGoalContext；当前章节无覆盖弧（无大纲/超出规划）时 has_skeleton=False。
    """
    repo = repo or NarrativeRepository()
    arc = await repo.get_arc_for_chapter(project_id, chapter_number)
    if arc is None:
        return NarrativeGoalContext(has_skeleton=False)

    # 本弧未收束线索：opened / advanced 状态的线索
    open_threads: list[dict] = []
    for status in _OPEN_STATUSES:
        threads = await repo.list_threads(project_id, status=status)  # type: ignore[arg-type]
        open_threads.extend(_thread_brief(t) for t in threads)

    # 本弧应收束线索：arc.threads_to_resolve 引用的线索详情
    threads_to_resolve: list[dict] = []
    for tid in arc.threads_to_resolve:
        thread = await repo.get_thread(tid)
        if thread is not None:
            threads_to_resolve.append(_thread_brief(thread))

    # 临近兑现伏笔：复用 ForeshadowingRepository.list_active（planted/due）
    fs_repo = foreshadowing_repo or ForeshadowingRepository()
    due_foreshadowings: list[dict] = []
    for item in await fs_repo.list_active(project_id):
        erc = item.expected_resolve_chapter
        if erc is not None and chapter_number <= erc <= chapter_number + due_window:
            due_foreshadowings.append(
                {
                    "foreshadowing_id": item.foreshadowing_id,
                    "description": item.description,
                    "expected_resolve_chapter": erc,
                }
            )

    return NarrativeGoalContext(
        has_skeleton=True,
        arc_goal=arc.arc_goal,
        arc_index=arc.arc_index,
        is_mainline_arc=arc.is_mainline,
        open_threads=open_threads,
        threads_to_resolve=threads_to_resolve,
        due_foreshadowings=due_foreshadowings,
    )
