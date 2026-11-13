"""task 255：storyline 编辑服务（直写 + 审计，tech-post-m4 v2 §A）。

故事线是规划面，直写不进提案队列（路线 B2）；每次 edit/remove 与目标行
**同一事务**写 ``storyline_edit_history``。规划不是 Canon（PRD :108），
本模块不触碰任何 plan_* 表。
"""

from __future__ import annotations

import json

import structlog

from songyan.db.connection import get_db
from songyan.db.narrative_repo import NarrativeRepository
from songyan.exceptions import SongyanError
from songyan.models.narrative import ArcPlan, PlotThread, StoryOutline

logger = structlog.get_logger(__name__)


def _dump(row: object | None) -> str | None:
    if row is None:
        return None
    model = getattr(row, "model_dump")
    return json.dumps(model(mode="json"), ensure_ascii=False, sort_keys=True)


async def edit_outline(
    project_id: str,
    *,
    core_conflict: str | None = None,
    mainline_synopsis: str | None = None,
    themes: list[str] | None = None,
    intended_ending: str | None = None,
) -> str:
    """读-改-写 upsert 全书大纲；审计行同事务。返回 action(create|update)。"""
    repo = NarrativeRepository()
    before = await repo.get_outline(project_id)
    after = StoryOutline(
        project_id=project_id,
        core_conflict=(
            core_conflict
            if core_conflict is not None
            else (before.core_conflict if before else "")
        ),
        mainline_synopsis=(
            mainline_synopsis
            if mainline_synopsis is not None
            else (before.mainline_synopsis if before else "")
        ),
        themes=themes if themes is not None else (before.themes if before else []),
        intended_ending=(
            intended_ending
            if intended_ending is not None
            else (before.intended_ending if before else "")
        ),
    )
    action = "update" if before is not None else "create"
    async with get_db() as conn:
        await repo.upsert_outline(after, conn=conn)
        await repo.record_history(
            project_id=project_id,
            target_type="outline",
            target_id=project_id,
            action=action,
            before_json=_dump(before),
            after_json=_dump(after),
            conn=conn,
        )
        await conn.commit()
    logger.info(
        "storyline.edit.outline",
        project_id=project_id,
        action=action,
    )
    return action


class StorylineEditError(SongyanError):
    """storyline 编辑业务拒绝（CLI 映射 exit 2）。"""

    exit_code = 2


THREAD_STATUSES = ("planned", "opened", "advanced", "resolved", "abandoned")


async def upsert_arc(
    project_id: str,
    *,
    arc_id: str,
    arc_index: int | None = None,
    start_chapter: int | None = None,
    end_chapter: int | None = None,
    arc_goal: str | None = None,
    threads_to_open: list[str] | None = None,
    threads_to_resolve: list[str] | None = None,
    is_mainline: bool | None = None,
) -> str:
    """按 arc_id upsert；校验拒绝（范围/重复 arc_index/幽灵线索引用）。"""
    repo = NarrativeRepository()
    arcs = await repo.list_arc_plans(project_id)
    before = next((a for a in arcs if a.arc_id == arc_id), None)
    merged = ArcPlan(
        arc_id=arc_id,
        project_id=project_id,
        arc_index=arc_index if arc_index is not None else (before.arc_index if before else 0),
        start_chapter=(
            start_chapter if start_chapter is not None else (before.start_chapter if before else 1)
        ),
        end_chapter=(
            end_chapter if end_chapter is not None else (before.end_chapter if before else 1)
        ),
        arc_goal=arc_goal if arc_goal is not None else (before.arc_goal if before else ""),
        threads_to_open=(
            threads_to_open
            if threads_to_open is not None
            else (before.threads_to_open if before else [])
        ),
        threads_to_resolve=(
            threads_to_resolve
            if threads_to_resolve is not None
            else (before.threads_to_resolve if before else [])
        ),
        is_mainline=(
            is_mainline
            if is_mainline is not None
            else (before.is_mainline if before else False)
        ),
    )
    if merged.start_chapter > merged.end_chapter:
        raise StorylineEditError(
            f"弧范围非法：start_chapter {merged.start_chapter} > end_chapter {merged.end_chapter}"
        )
    for other in arcs:
        if other.arc_id != arc_id and other.arc_index == merged.arc_index:
            raise StorylineEditError(
                f"arc_index {merged.arc_index} 已被弧 {other.arc_id} 占用"
            )
    refs = set(merged.threads_to_open) | set(merged.threads_to_resolve)
    if refs:
        existing = {th.thread_id for th in await repo.list_threads(project_id)}
        missing = sorted(refs - existing)
        if missing:
            raise StorylineEditError(f"弧引用了不存在的线索: {missing}")
    action = "update" if before is not None else "create"
    async with get_db() as conn:
        await repo.upsert_arc(merged, conn=conn)
        await repo.record_history(
            project_id=project_id,
            target_type="arc",
            target_id=arc_id,
            action=action,
            before_json=_dump(before),
            after_json=_dump(merged),
            conn=conn,
        )
        await conn.commit()
    logger.info("storyline.edit.arc", project_id=project_id, arc_id=arc_id, action=action)
    return action


async def upsert_thread(
    project_id: str,
    *,
    thread_id: str,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
    opened_chapter: int | None = None,
    expected_resolve_arc: int | None = None,
) -> str:
    """按 thread_id upsert；status 白名单校验；expected_resolve_arc 须指向存在弧。"""
    repo = NarrativeRepository()
    threads = await repo.list_threads(project_id)
    before = next((th for th in threads if th.thread_id == thread_id), None)
    merged = PlotThread(
        thread_id=thread_id,
        project_id=project_id,
        title=title if title is not None else (before.title if before else ""),
        description=(
            description if description is not None else (before.description if before else "")
        ),
        is_mainline=before.is_mainline if before else False,
        opened_chapter=(
            opened_chapter
            if opened_chapter is not None
            else (before.opened_chapter if before else None)
        ),
        expected_resolve_arc=(
            expected_resolve_arc
            if expected_resolve_arc is not None
            else (before.expected_resolve_arc if before else None)
        ),
        status=status if status is not None else (before.status if before else "planned"),
        last_status_chapter=before.last_status_chapter if before else None,
        last_status_version_id=before.last_status_version_id if before else None,
    )
    if merged.status not in THREAD_STATUSES:
        raise StorylineEditError(
            f"status 非法：{merged.status}（允许 {list(THREAD_STATUSES)}）"
        )
    if merged.expected_resolve_arc is not None:
        arc_indexes = {a.arc_index for a in await repo.list_arc_plans(project_id)}
        if merged.expected_resolve_arc not in arc_indexes:
            raise StorylineEditError(
                f"expected_resolve_arc {merged.expected_resolve_arc} 不存在"
            )
    action = "update" if before is not None else "create"
    async with get_db() as conn:
        await repo.upsert_thread(merged, conn=conn)
        await repo.record_history(
            project_id=project_id,
            target_type="thread",
            target_id=thread_id,
            action=action,
            before_json=_dump(before),
            after_json=_dump(merged),
            conn=conn,
        )
        await conn.commit()
    logger.info("storyline.edit.thread", project_id=project_id, thread_id=thread_id, action=action)
    return action


async def remove_arc(project_id: str, *, arc_id: str) -> str:
    """软删弧（archived=1）；幂等——已软删返回 'noop' 不写审计。"""
    repo = NarrativeRepository()
    arcs = await repo.list_arc_plans(project_id, include_archived=True)
    before = next((a for a in arcs if a.arc_id == arc_id), None)
    if before is None:
        raise StorylineEditError(f"弧不存在：{arc_id}")
    if before.archived:
        return "noop"
    after = before.model_copy(update={"archived": True})
    async with get_db() as conn:
        await repo.set_arc_archived(arc_id, True, conn=conn)
        await repo.record_history(
            project_id=project_id,
            target_type="arc",
            target_id=arc_id,
            action="remove",
            before_json=_dump(before),
            after_json=_dump(after),
            conn=conn,
        )
        await conn.commit()
    logger.info("storyline.remove.arc", project_id=project_id, arc_id=arc_id)
    return "remove"


async def remove_thread(project_id: str, *, thread_id: str) -> str:
    """软删线索（archived=1）；幂等同 remove_arc。"""
    repo = NarrativeRepository()
    threads = await repo.list_threads(project_id, include_archived=True)
    before = next((th for th in threads if th.thread_id == thread_id), None)
    if before is None:
        raise StorylineEditError(f"线索不存在：{thread_id}")
    if before.archived:
        return "noop"
    after = before.model_copy(update={"archived": True})
    async with get_db() as conn:
        await repo.set_thread_archived(thread_id, True, conn=conn)
        await repo.record_history(
            project_id=project_id,
            target_type="thread",
            target_id=thread_id,
            action="remove",
            before_json=_dump(before),
            after_json=_dump(after),
            conn=conn,
        )
        await conn.commit()
    logger.info("storyline.remove.thread", project_id=project_id, thread_id=thread_id)
    return "remove"
