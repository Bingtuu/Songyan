"""Repository for ``chapter_variants`` (tech-m3 B1 / step 1)."""

from __future__ import annotations

from datetime import UTC, datetime
from sqlite3 import IntegrityError, Row

import structlog

from songyan.db.connection import get_db
from songyan.exceptions import DuplicatePickedVariantError
from songyan.models.variant import ChapterVariant, VariantStatus

logger = structlog.get_logger(__name__)

def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _row_to_variant(row: Row) -> ChapterVariant:
    return ChapterVariant(
        variant_id=row["variant_id"],
        project_id=row["project_id"],
        chapter_number=int(row["chapter_number"]),
        slot_index=int(row["slot_index"]),
        status=row["status"],
        parent_canon_fingerprint=row["parent_canon_fingerprint"],
        content_ref=row["content_ref"],
        stale_vs_canon=int(row["stale_vs_canon"] or 0),
        score_card_json=row["score_card_json"],
        cost_cny_estimate=float(row["cost_cny_estimate"] or 0.0),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class ChapterVariantRepository:
    """Insert / list chapter variants; enforce one ``picked`` per chapter."""

    async def insert(self, variant: ChapterVariant) -> None:
        """Insert one variant row.

        Raises ``DuplicatePickedVariantError`` when status is ``picked`` and the
        chapter already has a picked row (application guard + unique index).
        """
        now = variant.created_at or _utc_now()
        updated = variant.updated_at or now
        status: VariantStatus = variant.status
        async with get_db() as conn:
            if status == "picked":
                cursor = await conn.execute(
                    """
                    SELECT variant_id FROM chapter_variants
                    WHERE project_id = ? AND chapter_number = ? AND status = 'picked'
                    LIMIT 1
                    """,
                    (variant.project_id, variant.chapter_number),
                )
                existing = await cursor.fetchone()
                if existing is not None:
                    raise DuplicatePickedVariantError(
                        f"chapter {variant.chapter_number} already has picked "
                        f"variant {existing[0]}"
                    )
            try:
                await conn.execute(
                    """
                    INSERT INTO chapter_variants (
                        variant_id, project_id, chapter_number, slot_index,
                        status, parent_canon_fingerprint, content_ref,
                        stale_vs_canon, score_card_json, cost_cny_estimate,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        variant.variant_id,
                        variant.project_id,
                        variant.chapter_number,
                        variant.slot_index,
                        status,
                        variant.parent_canon_fingerprint,
                        variant.content_ref,
                        int(variant.stale_vs_canon),
                        variant.score_card_json,
                        float(variant.cost_cny_estimate),
                        now,
                        updated,
                    ),
                )
                await conn.commit()
            except IntegrityError as exc:
                msg = str(exc).lower()
                if status == "picked" or "picked" in msg or "single_picked" in msg:
                    raise DuplicatePickedVariantError(
                        f"chapter {variant.chapter_number} already has a picked variant"
                    ) from exc
                raise
        logger.info(
            "chapter_variants.insert",
            variant_id=variant.variant_id,
            project_id=variant.project_id,
            chapter_number=variant.chapter_number,
            slot_index=variant.slot_index,
            status=status,
        )

    async def list_for_chapter(
        self, project_id: str, chapter_number: int
    ) -> list[ChapterVariant]:
        """List all variants for one chapter (any status), ordered by slot_index."""
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                """
                SELECT * FROM chapter_variants
                WHERE project_id = ? AND chapter_number = ?
                ORDER BY slot_index ASC, created_at ASC
                """,
                (project_id, chapter_number),
            )
            rows = await cursor.fetchall()
        return [_row_to_variant(row) for row in rows]

    async def get_by_slot(
        self, project_id: str, chapter_number: int, slot_index: int
    ) -> ChapterVariant | None:
        """Return the variant for one slot_index, if any."""
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                """
                SELECT * FROM chapter_variants
                WHERE project_id = ? AND chapter_number = ? AND slot_index = ?
                LIMIT 1
                """,
                (project_id, chapter_number, slot_index),
            )
            row = await cursor.fetchone()
        return _row_to_variant(row) if row is not None else None

    async def get_picked(
        self, project_id: str, chapter_number: int
    ) -> ChapterVariant | None:
        """Return the picked variant for a chapter, if any."""
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                """
                SELECT * FROM chapter_variants
                WHERE project_id = ? AND chapter_number = ? AND status = 'picked'
                LIMIT 1
                """,
                (project_id, chapter_number),
            )
            row = await cursor.fetchone()
        return _row_to_variant(row) if row is not None else None
