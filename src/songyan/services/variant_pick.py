"""M3 step 4 pick/abandon; step 5 lazy stale refresh before pick (B3).

pick moves ``ChapterHead.current_version_id`` only; never writes ``plan_*``.
abandon soft-deletes (status→abandoned); never clears content.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import structlog

from songyan.db.chapter_variant_repo import ChapterVariantRepository
from songyan.db.repository import ChapterHeadRepository, ChapterVersionRepository
from songyan.exceptions import SongyanError
from songyan.models.chapter import ChapterHead
from songyan.models.variant import ChapterVariant
from songyan.services.variant_diff import MissingVariantSlotError
from songyan.services.variant_stale import refresh_stale_vs_canon

logger = structlog.get_logger(__name__)


class StaleVariantPickError(SongyanError):
    """Target slot has ``stale_vs_canon=1`` and ``--allow-stale`` was not set."""

    exit_code = 2


class AbandonPickedVariantError(SongyanError):
    """Refuse to abandon the currently picked slot (pick another first)."""

    exit_code = 2


@dataclass(frozen=True)
class PickResult:
    """Outcome of ``variant pick``."""

    variant: ChapterVariant
    current_version_id: str
    archived_variant_id: str | None


@dataclass(frozen=True)
class AbandonResult:
    """Outcome of ``variant abandon``."""

    variant: ChapterVariant


async def pick_variant_slot(
    project_id: str,
    chapter: int,
    slot: int,
    *,
    allow_stale: bool = False,
) -> PickResult:
    """Pick one slot: archive prior picked, set status, move work pointer.

    Never INSERT/UPDATE ``plan_*``. Never auto ``canon confirm``.
    Never auto-set ``content_stale``.
    """
    if chapter < 1:
        raise ValueError("chapter must be >= 1")
    if slot < 1:
        raise ValueError("slot must be >= 1")

    await refresh_stale_vs_canon(project_id, chapter)

    repo = ChapterVariantRepository()
    target = await repo.get_by_slot(project_id, chapter, slot)
    if target is None:
        raise MissingVariantSlotError(slot, chapter)
    if int(target.stale_vs_canon) == 1 and not allow_stale:
        raise StaleVariantPickError(
            f"slot {slot} 相对 Canon 已过期（stale_vs_canon=1）；"
            f"如需仍选用请加 --allow-stale"
        )

    archived_id: str | None = None
    if target.status != "picked":
        outcome = await repo.pick_slot(project_id, chapter, slot)
        target = outcome.picked
        archived_id = outcome.archived_variant_id
    # else: idempotent — already this slot; still refresh work pointer below.

    head_repo = ChapterHeadRepository()
    existing = await head_repo.get(project_id, chapter)
    if existing is None:
        head = ChapterHead(
            project_id=project_id,
            chapter_number=chapter,
            current_version_id=target.content_ref,
            accepted_version_id=None,
            status="draft",
        )
    else:
        head = existing.model_copy(
            update={
                "current_version_id": target.content_ref,
                "updated_at": datetime.now(),
            }
        )
    await head_repo.update(head)

    logger.info(
        "variant.pick",
        project_id=project_id,
        chapter=chapter,
        slot=slot,
        content_ref=target.content_ref,
        archived_variant_id=archived_id,
        allow_stale=allow_stale,
        stale_vs_canon=target.stale_vs_canon,
    )
    return PickResult(
        variant=target,
        current_version_id=target.content_ref,
        archived_variant_id=archived_id,
    )


async def abandon_variant_slot(
    project_id: str,
    chapter: int,
    slot: int,
) -> AbandonResult:
    """Soft-abandon one slot. Refuse if it is currently ``picked``."""
    if chapter < 1:
        raise ValueError("chapter must be >= 1")
    if slot < 1:
        raise ValueError("slot must be >= 1")

    repo = ChapterVariantRepository()
    target = await repo.get_by_slot(project_id, chapter, slot)
    if target is None:
        raise MissingVariantSlotError(slot, chapter)
    if target.status == "picked":
        raise AbandonPickedVariantError(
            f"slot {slot} 当前为 picked；请先 pick 其它槽再 abandon"
        )
    if target.status == "abandoned":
        return AbandonResult(variant=target)

    updated = await repo.set_status(
        project_id, chapter, slot, status="abandoned"
    )
    # Align with existing mark_abandoned path; content stays readable.
    await ChapterVersionRepository().mark_abandoned(updated.content_ref)

    logger.info(
        "variant.abandon",
        project_id=project_id,
        chapter=chapter,
        slot=slot,
        content_ref=updated.content_ref,
    )
    return AbandonResult(variant=updated)
