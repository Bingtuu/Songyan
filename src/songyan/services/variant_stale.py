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
