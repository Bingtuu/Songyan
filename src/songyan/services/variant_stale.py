"""M3 step 5: lazy ``stale_vs_canon`` refresh (tech-m3 B3).

Choice locked by tests: refresh before ``list`` / ``diff`` / ``pick`` /
``generate``. Does **not** rewrite ``chapter_heads.content_stale``.

Only marks ``stale_vs_canon=1`` when current fingerprint ≠ row parent
fingerprint. Does **not** auto-clear an already-stale row back to 0
(authoritative clear is a new generate row with matching parent fp).
"""

from __future__ import annotations

import structlog

from songyan.db.chapter_variant_repo import ChapterVariantRepository
from songyan.services.variant_fingerprint import fingerprint_chapter_parent_canon

logger = structlog.get_logger(__name__)


async def refresh_stale_vs_canon(project_id: str, chapter: int) -> int:
    """Mark rows stale when current fingerprint ≠ ``parent_canon_fingerprint``.

    Returns the number of rows newly set to ``stale_vs_canon=1``.
    Never clears an existing ``1`` back to ``0``. Never touches ``content_stale``.
    """
    if chapter < 1:
        raise ValueError("chapter must be >= 1")

    current = await fingerprint_chapter_parent_canon(project_id, chapter)
    repo = ChapterVariantRepository()
    rows = await repo.list_for_chapter(project_id, chapter)
    if not rows:
        return 0

    updates: list[tuple[str, int]] = []
    for row in rows:
        if row.parent_canon_fingerprint != current and int(row.stale_vs_canon) != 1:
            updates.append((row.variant_id, 1))

    if updates:
        await repo.set_stale_flags(updates)
        logger.info(
            "variant.stale.refresh",
            project_id=project_id,
            chapter=chapter,
            current_fingerprint=current[:12],
            marked_stale=len(updates),
        )
    return len(updates)


async def refresh_stale_vs_storyline(project_id: str, chapter: int) -> int:
    """task 252：故事线演进标脏（tech-m4-followup-s5 §3.3）。

    与 stale_vs_canon 完全独立的标记。三条规则：
    - 行指纹 NULL（旧行）→ 只补记当前指纹，不标脏（B3：升级不全书标脏）；
    - 指纹非 NULL 且 ≠ 当前值且未标脏 → 标 1；
    - 只标不消（B4：清脏 = 新 generate 行）；过期/缺失指纹一律补记当前值。
    """
    if chapter < 1:
        raise ValueError("chapter must be >= 1")

    from songyan.services.storyline_fingerprint import storyline_fingerprint

    current = await storyline_fingerprint(project_id, chapter)
    repo = ChapterVariantRepository()
    rows = await repo.list_for_chapter(project_id, chapter)
    if not rows:
        return 0

    updates: list[tuple[str, int, str]] = []
    marked = 0
    for row in rows:
        stale = int(row.stale_vs_storyline)
        if row.storyline_fingerprint is None:
            updates.append((row.variant_id, stale, current))
        elif row.storyline_fingerprint != current:
            if stale != 1:
                stale = 1
                marked += 1
            updates.append((row.variant_id, stale, current))
    if updates:
        await repo.sync_storyline_state(updates)
        logger.info(
            "variant.stale.storyline.refresh",
            project_id=project_id,
            chapter=chapter,
            current_fingerprint=current[:12],
            marked_stale=marked,
        )
    return marked
