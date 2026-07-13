"""Foreshadowing schedule lifecycle services (V7 Task 167b)."""

from __future__ import annotations

from collections.abc import Iterable

import structlog

from songyan.db.connection import get_db
from songyan.db.foreshadowing_schedule_repo import ForeshadowingScheduleRepository
from songyan.exceptions import SongyanError
from songyan.models import ForeshadowingScheduleItem, StateSettlement

logger = structlog.get_logger(__name__)


class ForeshadowingScheduleServiceError(SongyanError):
    """Foreshadowing schedule lifecycle error."""


async def activate_foreshadowing_schedule_plan(
    plan_id: str,
    *,
    repo: ForeshadowingScheduleRepository | None = None,
) -> None:
    """Transition a draft schedule plan and its draft items to active."""
    repo = repo or ForeshadowingScheduleRepository()
    plan = await repo.get(plan_id)
    if plan is None:
        msg = f"foreshadowing schedule plan not found: {plan_id}"
        raise ForeshadowingScheduleServiceError(msg)
    if plan.status != "draft":
        msg = f"only draft schedule plans can be activated: {plan_id}"
        raise ForeshadowingScheduleServiceError(msg)
    async with get_db() as conn:
        try:
            await repo.update_plan_status(plan_id, "active", conn=conn)
            draft_ids = [item.item_id for item in plan.items if item.status == "draft"]
            await repo.update_items_status(draft_ids, "active", conn=conn)
            await conn.commit()
        except Exception as exc:  # noqa: BLE001 - rollback and wrap lifecycle errors
            await conn.rollback()
            if isinstance(exc, ForeshadowingScheduleServiceError):
                raise
            msg = f"failed to activate foreshadowing schedule plan: {plan_id}"
            raise ForeshadowingScheduleServiceError(msg) from exc
    logger.info("foreshadowing_schedule.activate", plan_id=plan_id, items=len(plan.items))


async def mark_schedule_items_injected(
    item_ids: Iterable[str],
    *,
    repo: ForeshadowingScheduleRepository | None = None,
) -> None:
    """Transition active schedule items to injected after planning-side use."""
    ids = list(dict.fromkeys(item_ids))
    if not ids:
        return
    repo = repo or ForeshadowingScheduleRepository()
    await repo.update_items_status(ids, "injected")
    logger.info("foreshadowing_schedule.injected", count=len(ids), item_ids=ids)


def _settlement_text(settlement: StateSettlement) -> str:
    parts: list[str] = []
    parts.extend(settlement.planted_hooks)
    parts.extend(settlement.resolved_hooks)
    parts.extend(settlement.open_threads)
    for update in settlement.foreshadowing_updates:
        parts.append(update.description or "")
    for setting in settlement.new_settings:
        parts.append(setting.setting_name or "")
        parts.append(setting.description or "")
    for char_update in settlement.character_updates:
        parts.append(char_update.new_value or "")
    return "\n".join(part for part in parts if part)


def _item_referenced(item: ForeshadowingScheduleItem, text: str) -> bool:
    if not text:
        return False
    keys = {
        item.source_id,
        item.title,
        item.description,
    }
    evidence = item.evidence or {}
    thread = evidence.get("thread")
    if isinstance(thread, dict):
        keys.add(str(thread.get("thread_id") or ""))
        keys.add(str(thread.get("title") or ""))
        keys.add(str(thread.get("description") or ""))
    foreshadowing = evidence.get("foreshadowing")
    if isinstance(foreshadowing, dict):
        keys.add(str(foreshadowing.get("foreshadowing_id") or ""))
        keys.add(str(foreshadowing.get("description") or ""))
    return any(key and key in text for key in keys)


async def update_schedule_after_accept(
    *,
    project_id: str,
    chapter_number: int,
    settlement: StateSettlement,
    repo: ForeshadowingScheduleRepository | None = None,
) -> dict[str, list[str]]:
    """Advance injected schedule items after a chapter is accepted.

    Referenced injected items are marked ``satisfied``. Injected items targeting
    the accepted chapter or earlier and not referenced are marked ``missed``.
    """
    repo = repo or ForeshadowingScheduleRepository()
    items = await repo.list_recent_items(
        project_id,
        start_chapter=1,
        end_chapter=chapter_number,
        statuses=("injected",),
    )
    text = _settlement_text(settlement)
    satisfied: list[str] = []
    missed: list[str] = []
    for item in items:
        if _item_referenced(item, text):
            satisfied.append(item.item_id)
        elif item.target_chapter <= chapter_number:
            missed.append(item.item_id)
    async with get_db() as conn:
        try:
            await repo.update_items_status(satisfied, "satisfied", conn=conn)
            await repo.update_items_status(missed, "missed", conn=conn)
            await conn.commit()
        except Exception as exc:  # noqa: BLE001 - rollback and wrap lifecycle errors
            await conn.rollback()
            msg = "failed to update foreshadowing schedule lifecycle after accept"
            raise ForeshadowingScheduleServiceError(msg) from exc
    if satisfied or missed:
        logger.info(
            "foreshadowing_schedule.after_accept",
            project_id=project_id,
            chapter_number=chapter_number,
            satisfied=satisfied,
            missed=missed,
        )
    return {"satisfied": satisfied, "missed": missed}
