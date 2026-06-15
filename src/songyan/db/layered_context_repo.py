"""Async repositories for layered context (Phase 4)."""

from __future__ import annotations

import json as _json
from datetime import datetime
from sqlite3 import Row

import aiosqlite
import structlog

from songyan.db.connection import get_db
from songyan.models import ArcSummary, PermanentScene, VolumeSummary

logger = structlog.get_logger(__name__)


def _parse_datetime(value: str | None) -> datetime:
    """Parse SQLite datetime string to Python datetime."""
    if not value:
        return datetime.now()
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return datetime.now()


class ArcSummaryRepository:
    """Repository for Arc summaries."""

    async def create(self, arc: ArcSummary, project_id: str) -> None:
        async with get_db() as conn:
            await conn.execute(
                """INSERT INTO arc_summaries (
                    arc_id, project_id, start_chapter, end_chapter,
                    arc_title, arc_summary, key_events, resolved_threads,
                    new_threads, character_arcs
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    arc.arc_id,
                    project_id,
                    arc.start_chapter,
                    arc.end_chapter,
                    arc.arc_title,
                    arc.arc_summary,
                    _json.dumps(arc.key_events, ensure_ascii=False),
                    _json.dumps(arc.resolved_threads, ensure_ascii=False),
                    _json.dumps(arc.new_threads, ensure_ascii=False),
                    _json.dumps(arc.character_arcs, ensure_ascii=False),
                ),
            )
            await conn.commit()
        logger.info(
            "repository.write",
            table="arc_summaries",
            operation="insert",
            arc_id=arc.arc_id,
        )

    async def get_by_arc_id(self, arc_id: str) -> ArcSummary | None:
        """按 arc_id 获取 Arc 摘要."""
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                "SELECT * FROM arc_summaries WHERE arc_id = ?",
                (arc_id,),
            )
            row = await cursor.fetchone()
        if row is None:
            return None
        return ArcSummary(
            arc_id=row["arc_id"],
            project_id=row["project_id"] or "",
            start_chapter=row["start_chapter"],
            end_chapter=row["end_chapter"],
            arc_title=row["arc_title"] or "",
            arc_summary=row["arc_summary"] or "",
            key_events=_json.loads(row["key_events"] or "[]"),
            resolved_threads=_json.loads(row["resolved_threads"] or "[]"),
            new_threads=_json.loads(row["new_threads"] or "[]"),
            character_arcs=_json.loads(row["character_arcs"] or "{}"),
            generated_at=_parse_datetime(row["created_at"]),
        )

    async def get_current_arc(
        self, project_id: str, chapter_number: int
    ) -> ArcSummary | None:
        """获取包含指定章节的 Arc."""
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                """SELECT * FROM arc_summaries
                WHERE project_id = ? AND start_chapter <= ? AND end_chapter >= ?
                ORDER BY start_chapter DESC LIMIT 1""",
                (project_id, chapter_number, chapter_number),
            )
            row = await cursor.fetchone()
        if row is None:
            return None
        return ArcSummary(
            arc_id=row["arc_id"],
            project_id=row["project_id"] or "",
            start_chapter=row["start_chapter"],
            end_chapter=row["end_chapter"],
            arc_title=row["arc_title"] or "",
            arc_summary=row["arc_summary"] or "",
            key_events=_json.loads(row["key_events"] or "[]"),
            resolved_threads=_json.loads(row["resolved_threads"] or "[]"),
            new_threads=_json.loads(row["new_threads"] or "[]"),
            character_arcs=_json.loads(row["character_arcs"] or "{}"),
            generated_at=_parse_datetime(row["created_at"]),
        )

    async def list_by_project(self, project_id: str) -> list[ArcSummary]:
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                "SELECT * FROM arc_summaries WHERE project_id = ? ORDER BY start_chapter",
                (project_id,),
            )
            rows = await cursor.fetchall()
        return [
            ArcSummary(
                arc_id=row["arc_id"],
                project_id=row["project_id"] or "",
                start_chapter=row["start_chapter"],
                end_chapter=row["end_chapter"],
                arc_title=row["arc_title"] or "",
                arc_summary=row["arc_summary"] or "",
                key_events=_json.loads(row["key_events"] or "[]"),
                resolved_threads=_json.loads(row["resolved_threads"] or "[]"),
                new_threads=_json.loads(row["new_threads"] or "[]"),
                character_arcs=_json.loads(row["character_arcs"] or "{}"),
                generated_at=_parse_datetime(row["created_at"]),
            )
            for row in rows
        ]

    async def update(self, arc: ArcSummary, project_id: str) -> None:
        """更新 Arc 摘要记录."""
        async with get_db() as conn:
            await conn.execute(
                """UPDATE arc_summaries SET
                    start_chapter = ?, end_chapter = ?,
                    arc_title = ?, arc_summary = ?,
                    key_events = ?, resolved_threads = ?,
                    new_threads = ?, character_arcs = ?
                WHERE arc_id = ? AND project_id = ?""",
                (
                    arc.start_chapter,
                    arc.end_chapter,
                    arc.arc_title,
                    arc.arc_summary,
                    _json.dumps(arc.key_events, ensure_ascii=False),
                    _json.dumps(arc.resolved_threads, ensure_ascii=False),
                    _json.dumps(arc.new_threads, ensure_ascii=False),
                    _json.dumps(arc.character_arcs, ensure_ascii=False),
                    arc.arc_id,
                    project_id,
                ),
            )
            await conn.commit()
        logger.info(
            "repository.write",
            table="arc_summaries",
            operation="update",
            arc_id=arc.arc_id,
        )

    async def delete_by_project(self, project_id: str) -> int:
        """删除项目下的所有 Arc 摘要，返回删除数量."""
        async with get_db() as conn:
            cursor = await conn.execute(
                "DELETE FROM arc_summaries WHERE project_id = ?",
                (project_id,),
            )
            await conn.commit()
            deleted = cursor.rowcount or 0
        logger.info(
            "repository.write",
            table="arc_summaries",
            operation="delete_by_project",
            project_id=project_id,
            deleted=deleted,
        )
        return deleted


class VolumeSummaryRepository:
    """Repository for Volume summaries."""

    async def create(self, volume: VolumeSummary, project_id: str) -> None:
        async with get_db() as conn:
            await conn.execute(
                """INSERT INTO volume_summaries (
                    volume_id, project_id, start_chapter, end_chapter,
                    volume_title, volume_summary, major_revelations, world_state
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    volume.volume_id,
                    project_id,
                    volume.start_chapter,
                    volume.end_chapter,
                    volume.volume_title,
                    volume.volume_summary,
                    _json.dumps(volume.major_revelations, ensure_ascii=False),
                    volume.world_state,
                ),
            )
            await conn.commit()
        logger.info(
            "repository.write",
            table="volume_summaries",
            operation="insert",
            volume_id=volume.volume_id,
        )

    async def get_by_volume_id(self, volume_id: str) -> VolumeSummary | None:
        """按 volume_id 获取 Volume 摘要."""
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                "SELECT * FROM volume_summaries WHERE volume_id = ?",
                (volume_id,),
            )
            row = await cursor.fetchone()
        if row is None:
            return None
        return VolumeSummary(
            volume_id=row["volume_id"],
            project_id=row["project_id"] or "",
            start_chapter=row["start_chapter"],
            end_chapter=row["end_chapter"],
            volume_title=row["volume_title"] or "",
            volume_summary=row["volume_summary"] or "",
            major_revelations=_json.loads(row["major_revelations"] or "[]"),
            world_state=row["world_state"] or "",
            generated_at=_parse_datetime(row["created_at"]),
        )

    async def get_current_volume(
        self, project_id: str, chapter_number: int
    ) -> VolumeSummary | None:
        """获取包含指定章节的 Volume."""
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                """SELECT * FROM volume_summaries
                WHERE project_id = ? AND start_chapter <= ? AND end_chapter >= ?
                ORDER BY start_chapter DESC LIMIT 1""",
                (project_id, chapter_number, chapter_number),
            )
            row = await cursor.fetchone()
        if row is None:
            return None
        return VolumeSummary(
            volume_id=row["volume_id"],
            project_id=row["project_id"] or "",
            start_chapter=row["start_chapter"],
            end_chapter=row["end_chapter"],
            volume_title=row["volume_title"] or "",
            volume_summary=row["volume_summary"] or "",
            major_revelations=_json.loads(row["major_revelations"] or "[]"),
            world_state=row["world_state"] or "",
            generated_at=_parse_datetime(row["created_at"]),
        )

    async def get_previous_volume(
        self, project_id: str, chapter_number: int
    ) -> VolumeSummary | None:
        """获取在指定章节之前结束的最近一个 Volume.

        用于 TemporalCompressor 金字塔分层：只加载历史卷，
        当前卷的信息由最近逐章摘要和当前弧摘要覆盖。
        """
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                """SELECT * FROM volume_summaries
                WHERE project_id = ? AND end_chapter < ?
                ORDER BY end_chapter DESC LIMIT 1""",
                (project_id, chapter_number),
            )
            row = await cursor.fetchone()
        if row is None:
            return None
        return VolumeSummary(
            volume_id=row["volume_id"],
            project_id=row["project_id"] or "",
            start_chapter=row["start_chapter"],
            end_chapter=row["end_chapter"],
            volume_title=row["volume_title"] or "",
            volume_summary=row["volume_summary"] or "",
            major_revelations=_json.loads(row["major_revelations"] or "[]"),
            world_state=row["world_state"] or "",
            generated_at=_parse_datetime(row["created_at"]),
        )

    async def list_by_project(self, project_id: str) -> list[VolumeSummary]:
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                "SELECT * FROM volume_summaries WHERE project_id = ? ORDER BY start_chapter",
                (project_id,),
            )
            rows = await cursor.fetchall()
        return [
            VolumeSummary(
                volume_id=row["volume_id"],
                project_id=row["project_id"] or "",
                start_chapter=row["start_chapter"],
                end_chapter=row["end_chapter"],
                volume_title=row["volume_title"] or "",
                volume_summary=row["volume_summary"] or "",
                major_revelations=_json.loads(row["major_revelations"] or "[]"),
                world_state=row["world_state"] or "",
                generated_at=_parse_datetime(row["created_at"]),
            )
            for row in rows
        ]

    async def update(self, volume: VolumeSummary, project_id: str) -> None:
        """更新 Volume 摘要记录."""
        async with get_db() as conn:
            await conn.execute(
                """UPDATE volume_summaries SET
                    start_chapter = ?, end_chapter = ?,
                    volume_title = ?, volume_summary = ?,
                    major_revelations = ?, world_state = ?
                WHERE volume_id = ? AND project_id = ?""",
                (
                    volume.start_chapter,
                    volume.end_chapter,
                    volume.volume_title,
                    volume.volume_summary,
                    _json.dumps(volume.major_revelations, ensure_ascii=False),
                    volume.world_state,
                    volume.volume_id,
                    project_id,
                ),
            )
            await conn.commit()
        logger.info(
            "repository.write",
            table="volume_summaries",
            operation="update",
            volume_id=volume.volume_id,
        )

    async def delete_by_project(self, project_id: str) -> int:
        """删除项目下的所有 Volume 摘要，返回删除数量."""
        async with get_db() as conn:
            cursor = await conn.execute(
                "DELETE FROM volume_summaries WHERE project_id = ?",
                (project_id,),
            )
            await conn.commit()
            deleted = cursor.rowcount or 0
        logger.info(
            "repository.write",
            table="volume_summaries",
            operation="delete_by_project",
            project_id=project_id,
            deleted=deleted,
        )
        return deleted


class PermanentSceneRepository:
    """Repository for permanent scenes."""

    async def create(
        self, scene: PermanentScene, project_id: str, conn: aiosqlite.Connection | None = None
    ) -> None:
        async def _do(c: aiosqlite.Connection) -> None:
            await c.execute(
                """INSERT INTO permanent_scenes (
                    scene_id, project_id, chapter_number, scene_number,
                    excerpt, impact_tags, referenced_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(scene_id) DO UPDATE SET
                    project_id = excluded.project_id,
                    chapter_number = excluded.chapter_number,
                    scene_number = excluded.scene_number,
                    excerpt = excluded.excerpt,
                    impact_tags = excluded.impact_tags,
                    referenced_by = excluded.referenced_by""",
                (
                    scene.scene_id,
                    project_id,
                    scene.chapter_number,
                    scene.scene_number,
                    scene.excerpt,
                    _json.dumps(scene.impact_tags, ensure_ascii=False),
                    _json.dumps(scene.referenced_by, ensure_ascii=False),
                ),
            )

        if conn is None:
            async with get_db() as c:
                await _do(c)
                await c.commit()
        else:
            await _do(conn)
        logger.info(
            "repository.write",
            table="permanent_scenes",
            operation="insert",
            scene_id=scene.scene_id,
        )

    async def list_by_project(
        self, project_id: str, limit: int = 5
    ) -> list[PermanentScene]:
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                """SELECT * FROM permanent_scenes
                WHERE project_id = ?
                ORDER BY chapter_number DESC
                LIMIT ?""",
                (project_id, limit),
            )
            rows = await cursor.fetchall()
        return [
            PermanentScene(
                scene_id=row["scene_id"],
                chapter_number=row["chapter_number"],
                scene_number=row["scene_number"],
                excerpt=row["excerpt"] or "",
                impact_tags=_json.loads(row["impact_tags"] or "[]"),
                referenced_by=_json.loads(row["referenced_by"] or "[]"),
            )
            for row in rows
        ]

    async def add_reference(self, scene_id: str, chapter_number: int) -> None:
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                "SELECT referenced_by FROM permanent_scenes WHERE scene_id = ?",
                (scene_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                return
            refs = _json.loads(row["referenced_by"] or "[]")
            if chapter_number not in refs:
                refs.append(chapter_number)
                await conn.execute(
                    "UPDATE permanent_scenes SET referenced_by = ? WHERE scene_id = ?",
                    (_json.dumps(refs, ensure_ascii=False), scene_id),
                )
                await conn.commit()
