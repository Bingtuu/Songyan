"""Repository for text cleanliness metrics (V7 Task 164)."""

from __future__ import annotations

import json
from sqlite3 import Row
from typing import Any

from pydantic import BaseModel, Field

from songyan.db.connection import get_db


class TextCleanlinessMetricRow(BaseModel):
    """Persisted per-chapter text cleanliness metric."""

    project_id: str
    chapter_number: int
    version_id: str
    meta_tag_leak_count: int = 0
    duplicate_paragraph_count: int = 0
    timeline_conflict_count: int = 0
    details: dict[str, Any] = Field(default_factory=dict)


class TextCleanlinessMetricRepository:
    """Read/write text_cleanliness_metrics."""

    async def upsert(self, row: TextCleanlinessMetricRow) -> None:
        async with get_db() as conn:
            await conn.execute(
                """INSERT INTO text_cleanliness_metrics (
                    project_id, chapter_number, version_id,
                    meta_tag_leak_count, duplicate_paragraph_count,
                    timeline_conflict_count, details_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(project_id, chapter_number) DO UPDATE SET
                    version_id = excluded.version_id,
                    meta_tag_leak_count = excluded.meta_tag_leak_count,
                    duplicate_paragraph_count = excluded.duplicate_paragraph_count,
                    timeline_conflict_count = excluded.timeline_conflict_count,
                    details_json = excluded.details_json,
                    updated_at = datetime('now')""",
                (
                    row.project_id,
                    row.chapter_number,
                    row.version_id,
                    row.meta_tag_leak_count,
                    row.duplicate_paragraph_count,
                    row.timeline_conflict_count,
                    json.dumps(row.details, ensure_ascii=False),
                ),
            )
            await conn.commit()

    async def list_by_project(
        self,
        project_id: str,
        start: int | None = None,
        end: int | None = None,
    ) -> list[TextCleanlinessMetricRow]:
        async with get_db() as conn:
            conn.row_factory = Row
            query = "SELECT * FROM text_cleanliness_metrics WHERE project_id = ?"
            params: list[Any] = [project_id]
            if start is not None and end is not None:
                query += " AND chapter_number BETWEEN ? AND ?"
                params.extend([start, end])
            query += " ORDER BY chapter_number"
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
        return [self._row_to_model(row) for row in rows]

    async def get(
        self,
        project_id: str,
        chapter_number: int,
    ) -> TextCleanlinessMetricRow | None:
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                """SELECT * FROM text_cleanliness_metrics
                WHERE project_id = ? AND chapter_number = ?""",
                (project_id, chapter_number),
            )
            row = await cursor.fetchone()
        return self._row_to_model(row) if row is not None else None

    @staticmethod
    def _row_to_model(row: Row) -> TextCleanlinessMetricRow:
        raw_details = row["details_json"] or "{}"
        try:
            details = json.loads(raw_details)
        except (TypeError, ValueError):
            details = {}
        return TextCleanlinessMetricRow(
            project_id=row["project_id"],
            chapter_number=int(row["chapter_number"]),
            version_id=row["version_id"],
            meta_tag_leak_count=int(row["meta_tag_leak_count"] or 0),
            duplicate_paragraph_count=int(row["duplicate_paragraph_count"] or 0),
            timeline_conflict_count=int(row["timeline_conflict_count"] or 0),
            details=details,
        )
