"""Repository for ``chapter_variants`` (tech-m3 B1; pick/abandon; stale step 5)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from sqlite3 import IntegrityError, Row
from typing import TYPE_CHECKING

import structlog

from songyan.db.connection import get_db
from songyan.exceptions import DuplicatePickedVariantError
from songyan.models.variant import ChapterVariant, VariantStatus

if TYPE_CHECKING:
    import aiosqlite

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


@dataclass(frozen=True)
class PickSlotOutcome:
    """Result of transactional pick: new picked row + optional archived prior."""

    picked: ChapterVariant
    archived_variant_id: str | None


class ChapterVariantRepository:
    """Insert / list / pick / abandon chapter variants; one ``picked`` per chapter."""

    async def insert(
        self, variant: ChapterVariant, conn: aiosqlite.Connection | None = None
    ) -> None:
        """Insert one variant row.

        Raises ``DuplicatePickedVariantError`` when status is ``picked`` and the
        chapter already has a picked row (application guard + unique index).
        When ``conn`` is given, writes on it without committing (caller owns
        the transaction).
        """
        now = variant.created_at or _utc_now()
        updated = variant.updated_at or now
        status: VariantStatus = variant.status

        async def _do(c: aiosqlite.Connection) -> None:
            if status == "picked":
                cursor = await c.execute(
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
                await c.execute(
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
            except IntegrityError as exc:
                msg = str(exc).lower()
                if status == "picked" or "picked" in msg or "single_picked" in msg:
                    raise DuplicatePickedVariantError(
                        f"chapter {variant.chapter_number} already has a picked variant"
                    ) from exc
                raise

        if conn is None:
            async with get_db() as own:
                await _do(own)
                await own.commit()
        else:
            await _do(conn)
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

    async def list_by_project(self, project_id: str) -> list[ChapterVariant]:
        """该项目全部 variant 行（任意状态，含 abandoned/archived），章号+槽号升序。

        只读；章进度视图需要全量状态做六态推导（活动槽判定在视图层）。
        """
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                """
                SELECT * FROM chapter_variants
                WHERE project_id = ?
                ORDER BY chapter_number ASC, slot_index ASC, created_at ASC
                """,
                (project_id,),
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
                ORDER BY created_at ASC
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

    async def pick_slot(
        self, project_id: str, chapter_number: int, slot_index: int
    ) -> PickSlotOutcome:
        """Archive prior picked (if any) then mark ``slot_index`` as picked.

        Runs in one transaction so the single-picked unique index never sees
        two ``picked`` rows. Does not touch ``plan_*`` or chapter_versions.
        """
        now = _utc_now()
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                """
                SELECT * FROM chapter_variants
                WHERE project_id = ? AND chapter_number = ? AND slot_index = ?
                ORDER BY created_at ASC
                LIMIT 1
                """,
                (project_id, chapter_number, slot_index),
            )
            target_row = await cursor.fetchone()
            if target_row is None:
                raise LookupError(
                    f"variant slot missing: chapter={chapter_number} slot={slot_index}"
                )
            target = _row_to_variant(target_row)

            archived_id: str | None = None
            cursor = await conn.execute(
                """
                SELECT variant_id FROM chapter_variants
                WHERE project_id = ? AND chapter_number = ? AND status = 'picked'
                  AND slot_index != ?
                """,
                (project_id, chapter_number, slot_index),
            )
            prior_rows = await cursor.fetchall()
            for prior in prior_rows:
                await conn.execute(
                    """
                    UPDATE chapter_variants
                    SET status = 'archived', updated_at = ?
                    WHERE variant_id = ?
                    """,
                    (now, prior["variant_id"]),
                )
                archived_id = prior["variant_id"]

            if target.status != "picked":
                try:
                    await conn.execute(
                        """
                        UPDATE chapter_variants
                        SET status = 'picked', updated_at = ?
                        WHERE variant_id = ?
                        """,
                        (now, target.variant_id),
                    )
                except IntegrityError as exc:
                    raise DuplicatePickedVariantError(
                        f"chapter {chapter_number} already has a picked variant"
                    ) from exc

            await conn.commit()

            cursor = await conn.execute(
                "SELECT * FROM chapter_variants WHERE variant_id = ?",
                (target.variant_id,),
            )
            fresh = await cursor.fetchone()
            assert fresh is not None
            picked = _row_to_variant(fresh)

        logger.info(
            "chapter_variants.pick_slot",
            project_id=project_id,
            chapter_number=chapter_number,
            slot_index=slot_index,
            variant_id=picked.variant_id,
            archived_variant_id=archived_id,
        )
        return PickSlotOutcome(picked=picked, archived_variant_id=archived_id)

    async def set_status(
        self,
        project_id: str,
        chapter_number: int,
        slot_index: int,
        *,
        status: VariantStatus,
    ) -> ChapterVariant:
        """Set status for one slot; returns the updated row."""
        now = _utc_now()
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                """
                SELECT * FROM chapter_variants
                WHERE project_id = ? AND chapter_number = ? AND slot_index = ?
                ORDER BY created_at ASC
                LIMIT 1
                """,
                (project_id, chapter_number, slot_index),
            )
            row = await cursor.fetchone()
            if row is None:
                raise LookupError(
                    f"variant slot missing: chapter={chapter_number} slot={slot_index}"
                )
            variant_id = row["variant_id"]
            await conn.execute(
                """
                UPDATE chapter_variants
                SET status = ?, updated_at = ?
                WHERE variant_id = ?
                """,
                (status, now, variant_id),
            )
            await conn.commit()
            cursor = await conn.execute(
                "SELECT * FROM chapter_variants WHERE variant_id = ?",
                (variant_id,),
            )
            fresh = await cursor.fetchone()
            assert fresh is not None
            updated = _row_to_variant(fresh)
        logger.info(
            "chapter_variants.set_status",
            project_id=project_id,
            chapter_number=chapter_number,
            slot_index=slot_index,
            status=status,
            variant_id=updated.variant_id,
        )
        return updated

    async def set_stale_flags(self, updates: list[tuple[str, int]]) -> None:
        """Set ``stale_vs_canon`` for ``(variant_id, flag)`` pairs in one transaction.

        Does not touch status, content_ref, or ``chapter_heads.content_stale``.
        """
        if not updates:
            return
        now = _utc_now()
        async with get_db() as conn:
            for variant_id, flag in updates:
                await conn.execute(
                    """
                    UPDATE chapter_variants
                    SET stale_vs_canon = ?, updated_at = ?
                    WHERE variant_id = ?
                    """,
                    (int(flag), now, variant_id),
                )
            await conn.commit()
        logger.info(
            "chapter_variants.set_stale_flags",
            count=len(updates),
        )
