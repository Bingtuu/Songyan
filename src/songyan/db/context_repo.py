"""Async repositories for context package assembly."""

from __future__ import annotations

from sqlite3 import Row

import structlog

from songyan.db.connection import get_db
from songyan.models import ChapterSummary, CharacterState
from songyan.utils.json_helpers import from_json as _from_json

logger = structlog.get_logger(__name__)


class SummaryRepository:
    """Repository for chapter summaries."""

    async def create(
        self,
        summary: ChapterSummary,
        project_id: str,
        summary_id: str,
    ) -> None:
        """创建章节摘要记录."""
        import json as _json

        async with get_db() as conn:
            await conn.execute(
                """INSERT INTO summaries (
                    summary_id, project_id, chapter_number,
                    plot_summary, key_events, characters_appeared, emotional_tone, impact_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    summary_id,
                    project_id,
                    summary.chapter_number,
                    summary.summary,
                    _json.dumps(summary.key_events, ensure_ascii=False),
                    _json.dumps(summary.characters_appeared, ensure_ascii=False),
                    summary.emotional_tone,
                    summary.impact_score,
                ),
            )
            await conn.commit()
        logger.info(
            "repository.write",
            table="summaries",
            operation="create",
            project_id=project_id,
            chapter_number=summary.chapter_number,
        )

    async def list_recent(
        self,
        project_id: str,
        before_chapter: int,
        limit: int = 3,
    ) -> list[ChapterSummary]:
        """获取最近 N 章的摘要（before_chapter 之前的章节）."""
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                """SELECT chapter_number, plot_summary, key_events,
                          characters_appeared, impact_score
                   FROM summaries
                   WHERE project_id = ? AND chapter_number < ?
                   ORDER BY chapter_number DESC
                   LIMIT ?""",
                (project_id, before_chapter, limit),
            )
            rows = await cursor.fetchall()
        # 按 chapter_number 升序返回（从旧到新）
        summaries = [
            ChapterSummary(
                chapter_number=row["chapter_number"],
                summary=row["plot_summary"] or "",
                key_events=_from_json(row["key_events"], []),
                characters_appeared=_from_json(row["characters_appeared"], []),
                impact_score=row["impact_score"] or 0.0,
            )
            for row in reversed(rows)
        ]
        logger.info(
            "repository.read",
            table="summaries",
            operation="list_recent",
            project_id=project_id,
            count=len(summaries),
        )
        return summaries

    async def list_by_chapter_range(
        self,
        project_id: str,
        start_chapter: int,
        end_chapter: int,
    ) -> list[ChapterSummary]:
        """获取指定章节范围内的所有摘要."""
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                """SELECT chapter_number, plot_summary, key_events,
                          characters_appeared, impact_score
                   FROM summaries
                   WHERE project_id = ? AND chapter_number >= ? AND chapter_number <= ?
                   ORDER BY chapter_number""",
                (project_id, start_chapter, end_chapter),
            )
            rows = await cursor.fetchall()
        summaries = [
            ChapterSummary(
                chapter_number=row["chapter_number"],
                summary=row["plot_summary"] or "",
                key_events=_from_json(row["key_events"], []),
                characters_appeared=_from_json(row["characters_appeared"], []),
                impact_score=row["impact_score"] or 0.0,
            )
            for row in rows
        ]
        logger.info(
            "repository.read",
            table="summaries",
            operation="list_by_chapter_range",
            project_id=project_id,
            range=f"{start_chapter}-{end_chapter}",
            count=len(summaries),
        )
        return summaries

    async def get_max_chapter_number(self, project_id: str) -> int:
        """获取项目下已有摘要的最大章节号."""
        async with get_db() as conn:
            cursor = await conn.execute(
                "SELECT MAX(chapter_number) FROM summaries WHERE project_id = ?",
                (project_id,),
            )
            row = await cursor.fetchone()
        return row[0] if row and row[0] else 0


class CharacterStateRepository:
    """Repository for querying character state snapshots."""

    async def list_recent_by_project(
        self,
        project_id: str,
        limit_per_character: int = 5,
    ) -> list[CharacterState]:
        """获取项目下每个角色的最新状态记录.

        使用窗口函数一次性查询，避免 N+1。
        V4.0: 只返回 lifecycle_status='active' 的记录；protagonist 始终包含。
        """
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                """SELECT cs.character_id, cs.field, cs.value, cs.source_version_id,
                          cs.created_at, c.role_type
                FROM (
                    SELECT *,
                        ROW_NUMBER() OVER (
                            PARTITION BY character_id
                            ORDER BY created_at DESC, state_id DESC
                        ) as rn
                    FROM character_states
                    WHERE lifecycle_status = 'active'
                      OR character_id IN (
                          SELECT character_id FROM characters
                          WHERE project_id = ? AND role_type = 'protagonist'
                      )
                ) cs
                JOIN characters c ON cs.character_id = c.character_id
                WHERE c.project_id = ?
                  AND cs.rn <= ?""",
                (project_id, project_id, limit_per_character),
            )
            rows = await cursor.fetchall()
        states = [
            CharacterState(
                character_id=row["character_id"],
                field=row["field"],
                value=row["value"],
                source_version_id=row["source_version_id"],
                lifecycle_status=row["lifecycle_status"] if "lifecycle_status" in row.keys() else "active",
                created_at=row["created_at"],
            )
            for row in rows
        ]
        logger.info(
            "repository.read",
            table="character_states",
            operation="list_recent_by_project",
            project_id=project_id,
            count=len(states),
        )
        return states

    async def archive_stale(
        self,
        project_id: str,
        current_chapter: int,
        window: int = 30,
        conn: aiosqlite.Connection | None = None,
    ) -> int:
        """将 30 章未出场的非核心角色标记为 dormant.

        返回: 影响的记录数
        """
        async def _do(c: aiosqlite.Connection) -> int:
            threshold = current_chapter - window
            # 获取每个非 protagonist 角色的最新 state_id
            cursor = await c.execute(
                """SELECT cs.state_id
                FROM character_states cs
                JOIN (
                    SELECT character_id, MAX(state_id) as max_state_id
                    FROM character_states
                    WHERE lifecycle_status = 'active'
                    GROUP BY character_id
                ) latest ON cs.character_id = latest.character_id
                    AND cs.state_id = latest.max_state_id
                JOIN characters ch ON cs.character_id = ch.character_id
                JOIN chapter_versions cv ON cs.source_version_id = cv.version_id
                WHERE ch.project_id = ?
                  AND ch.role_type NOT IN ('protagonist', 'antagonist')
                  AND cs.lifecycle_status = 'active'
                  AND cv.chapter_number < ?""",
                (project_id, threshold),
            )
            rows = await cursor.fetchall()
            state_ids = [row[0] for row in rows]
            if not state_ids:
                return 0
            placeholders = ",".join("?" * len(state_ids))
            update_cursor = await c.execute(
                f"""UPDATE character_states
                SET lifecycle_status = 'dormant'
                WHERE state_id IN ({placeholders})""",
                state_ids,
            )
            return update_cursor.rowcount

        if conn is None:
            async with get_db() as c:
                archived = await _do(c)
                await c.commit()
        else:
            archived = await _do(conn)
        if archived > 0:
            logger.info(
                "repository.write",
                table="character_states",
                operation="archive_stale",
                project_id=project_id,
                current_chapter=current_chapter,
                window=window,
                archived_count=archived,
            )
        return archived

    async def archive_very_stale(
        self,
        project_id: str,
        current_chapter: int,
        window: int = 60,
        conn: aiosqlite.Connection | None = None,
    ) -> int:
        """将 60 章未出场的 dormant 角色标记为 archived.

        返回: 影响的记录数
        """
        async def _do(c: aiosqlite.Connection) -> int:
            threshold = current_chapter - window
            cursor = await c.execute(
                """SELECT cs.state_id
                FROM character_states cs
                JOIN (
                    SELECT character_id, MAX(state_id) as max_state_id
                    FROM character_states
                    WHERE lifecycle_status = 'dormant'
                    GROUP BY character_id
                ) latest ON cs.character_id = latest.character_id
                    AND cs.state_id = latest.max_state_id
                JOIN characters ch ON cs.character_id = ch.character_id
                JOIN chapter_versions cv ON cs.source_version_id = cv.version_id
                WHERE ch.project_id = ?
                  AND ch.role_type NOT IN ('protagonist', 'antagonist')
                  AND cs.lifecycle_status = 'dormant'
                  AND cv.chapter_number < ?""",
                (project_id, threshold),
            )
            rows = await cursor.fetchall()
            state_ids = [row[0] for row in rows]
            if not state_ids:
                return 0
            placeholders = ",".join("?" * len(state_ids))
            update_cursor = await c.execute(
                f"""UPDATE character_states
                SET lifecycle_status = 'archived'
                WHERE state_id IN ({placeholders})""",
                state_ids,
            )
            return update_cursor.rowcount

        if conn is None:
            async with get_db() as c:
                archived = await _do(c)
                await c.commit()
        else:
            archived = await _do(conn)
        if archived > 0:
            logger.info(
                "repository.write",
                table="character_states",
                operation="archive_very_stale",
                project_id=project_id,
                current_chapter=current_chapter,
                window=window,
                archived_count=archived,
            )
        return archived

    async def _compute_dynamic_cap(
        self,
        project_id: str,
        current_chapter: int,
        conn: aiosqlite.Connection,
    ) -> int:
        """基于情节需求与上下文压强计算动态 cap.

        demand = 最近 10 章出场角色数 + 2
        pressure = (最近 5 章新增设定 + 伏笔) // 3
        cap = min(25, max(12, demand - pressure))
        """
        # 1. 最近 10 章出场角色数
        cursor = await conn.execute(
            """SELECT COUNT(DISTINCT cs.character_id)
            FROM character_states cs
            JOIN chapter_versions cv ON cs.source_version_id = cv.version_id
            WHERE cv.project_id = ? AND cv.chapter_number > ?
              AND cv.chapter_number <= ?""",
            (project_id, current_chapter - 10, current_chapter),
        )
        row = await cursor.fetchone()
        recent_chars = row[0] if row else 0

        # 2. 最近 5 章新增设定数 (created_at 近似)
        cursor = await conn.execute(
            """SELECT created_at FROM chapter_versions
            WHERE project_id = ? AND chapter_number > ?
            ORDER BY created_at ASC LIMIT 1""",
            (project_id, current_chapter - 5),
        )
        row = await cursor.fetchone()
        anchor = row[0] if row else "1970-01-01"
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM setting_snapshots WHERE project_id = ? AND created_at >= ?",
            (project_id, anchor),
        )
        row = await cursor.fetchone()
        new_settings = row[0] if row else 0

        # 3. 最近 5 章新增伏笔数
        cursor = await conn.execute(
            """SELECT COUNT(*) FROM foreshadowings
            WHERE project_id = ? AND planted_in_chapter > ?
              AND planted_in_chapter <= ?""",
            (project_id, current_chapter - 5, current_chapter),
        )
        row = await cursor.fetchone()
        new_foreshadowings = row[0] if row else 0

        demand = recent_chars + 2
        pressure = (new_settings + new_foreshadowings) // 3
        cap = min(25, max(12, demand - pressure))
        return cap

    async def archive_stale_functional(
        self,
        project_id: str,
        current_chapter: int,
        window: int = 8,
        conn: aiosqlite.Connection | None = None,
    ) -> int:
        """将 8 章未出场的功能性角色（无 goals/relationships）标记为 dormant."""
        async def _do(c: aiosqlite.Connection) -> int:
            threshold = current_chapter - window
            cursor = await c.execute(
                """SELECT latest.max_state_id
                FROM character_states cs
                JOIN (
                    SELECT character_id, MAX(state_id) as max_state_id
                    FROM character_states
                    WHERE lifecycle_status = 'active'
                    GROUP BY character_id
                ) latest ON cs.character_id = latest.character_id
                    AND cs.state_id = latest.max_state_id
                JOIN characters ch ON cs.character_id = ch.character_id
                JOIN chapter_versions cv ON cs.source_version_id = cv.version_id
                WHERE ch.project_id = ?
                  AND ch.role_type NOT IN ('protagonist', 'antagonist')
                  AND ch.goals = '[]'
                  AND ch.relationships = '{}'
                  AND cs.lifecycle_status = 'active'
                  AND cv.chapter_number < ?""",
                (project_id, threshold),
            )
            rows = await cursor.fetchall()
            state_ids = [row[0] for row in rows]
            if not state_ids:
                return 0
            placeholders = ",".join("?" * len(state_ids))
            update_cursor = await c.execute(
                f"""UPDATE character_states
                SET lifecycle_status = 'dormant'
                WHERE state_id IN ({placeholders})""",
                state_ids,
            )
            return update_cursor.rowcount

        if conn is None:
            async with get_db() as c:
                archived = await _do(c)
                await c.commit()
        else:
            archived = await _do(conn)
        if archived > 0:
            logger.info(
                "repository.write",
                table="character_states",
                operation="archive_stale_functional",
                project_id=project_id,
                current_chapter=current_chapter,
                window=window,
                archived_count=archived,
            )
        return archived

    async def archive_overflow(
        self,
        project_id: str,
        current_chapter: int,
        cap: int | None = None,
        conn: aiosqlite.Connection | None = None,
    ) -> int:
        """当活跃角色数超过 cap 时，淘汰 least-recently-appeared 非核心角色.

        保护 protagonist / antagonist，功能性角色优先被淘汰。
        cap 为 None 时启用动态计算（基于情节密度与上下文压强）。
        返回: 影响的记录数
        """
        async def _do(c: aiosqlite.Connection) -> int:
            effective_cap = cap
            if effective_cap is None:
                effective_cap = await self._compute_dynamic_cap(
                    project_id, current_chapter, c
                )

            # 1. 统计总活跃角色数
            cursor = await c.execute(
                """SELECT COUNT(DISTINCT cs.character_id)
                FROM character_states cs
                JOIN characters ch ON cs.character_id = ch.character_id
                WHERE ch.project_id = ? AND cs.lifecycle_status = 'active'""",
                (project_id,),
            )
            row = await cursor.fetchone()
            total_active = row[0] if row else 0
            excess = total_active - effective_cap
            if excess <= 0:
                return 0

            # 2. 找出 excess 个角色：功能性优先，其次 least-recently-appeared
            cursor = await c.execute(
                """SELECT latest.max_state_id
                FROM character_states cs
                JOIN (
                    SELECT character_id, MAX(state_id) as max_state_id
                    FROM character_states
                    WHERE lifecycle_status = 'active'
                    GROUP BY character_id
                ) latest ON cs.character_id = latest.character_id
                    AND cs.state_id = latest.max_state_id
                JOIN characters ch ON cs.character_id = ch.character_id
                JOIN chapter_versions cv ON cs.source_version_id = cv.version_id
                WHERE ch.project_id = ?
                  AND ch.role_type NOT IN ('protagonist', 'antagonist')
                  AND cs.lifecycle_status = 'active'
                ORDER BY
                    CASE WHEN ch.goals = '[]' AND ch.relationships = '{}' THEN 0 ELSE 1 END ASC,
                    cv.chapter_number ASC
                LIMIT ?""",
                (project_id, excess),
            )
            rows = await cursor.fetchall()
            state_ids = [row[0] for row in rows]
            if not state_ids:
                return 0
            placeholders = ",".join("?" * len(state_ids))
            update_cursor = await c.execute(
                f"""UPDATE character_states
                SET lifecycle_status = 'dormant'
                WHERE state_id IN ({placeholders})""",
                state_ids,
            )
            return update_cursor.rowcount

        if conn is None:
            async with get_db() as c:
                archived = await _do(c)
                await c.commit()
        else:
            archived = await _do(conn)
        if archived > 0:
            logger.info(
                "repository.write",
                table="character_states",
                operation="archive_overflow",
                project_id=project_id,
                current_chapter=current_chapter,
                cap=cap,
                archived_count=archived,
            )
        return archived

    async def get_last_appeared_chapters(
        self,
        project_id: str,
    ) -> dict[str, int]:
        """获取每个角色最后出场的章节号.

        V5.0 Task 102: 通过 character_states.source_version_id JOIN
        chapter_versions 推导 last_appeared_chapter，不修改 DB schema。
        若角色无状态记录，则不在返回结果中（调用方视为未出场）。
        """
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                """SELECT
                    cs.character_id,
                    MAX(cv.chapter_number) as last_chapter
                FROM character_states cs
                JOIN chapter_versions cv ON cs.source_version_id = cv.version_id
                JOIN characters ch ON cs.character_id = ch.character_id
                WHERE ch.project_id = ?
                GROUP BY cs.character_id""",
                (project_id,),
            )
            rows = await cursor.fetchall()
        result = {row["character_id"]: row["last_chapter"] for row in rows}
        logger.info(
            "repository.read",
            table="character_states",
            operation="get_last_appeared_chapters",
            project_id=project_id,
            count=len(result),
        )
        return result

    async def list_latest_by_project(
        self,
        project_id: str,
    ) -> list[CharacterState]:
        """获取项目下每个角色的最新一条状态记录（每个 field 取最新）.

        使用窗口函数替代关联子查询，提升性能。
        """
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                """SELECT character_id, field, value, source_version_id, created_at
                FROM (
                    SELECT cs.*,
                        ROW_NUMBER() OVER (
                            PARTITION BY cs.character_id, cs.field
                            ORDER BY cs.created_at DESC, cs.state_id DESC
                        ) as rn
                    FROM character_states cs
                    INNER JOIN characters c ON cs.character_id = c.character_id
                    WHERE c.project_id = ?
                )
                WHERE rn = 1
                ORDER BY character_id, field""",
                (project_id,),
            )
            rows = await cursor.fetchall()
        states = [
            CharacterState(
                character_id=row["character_id"],
                field=row["field"],
                value=row["value"],
                source_version_id=row["source_version_id"],
                lifecycle_status=row["lifecycle_status"] if "lifecycle_status" in row.keys() else "active",
                created_at=row["created_at"],
            )
            for row in rows
        ]
        logger.info(
            "repository.read",
            table="character_states",
            operation="list_latest_by_project",
            project_id=project_id,
            count=len(states),
        )
        return states

    async def list_state_history_by_project(
        self,
        project_id: str,
        up_to_chapter: int,
    ) -> list[dict]:
        """获取项目下所有角色的状态历史（含关联的 chapter_number）.

        通过 source_version_id JOIN chapter_versions 获取章节号。
        """
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                """SELECT
                    cs.character_id,
                    cs.field,
                    cs.value,
                    cv.chapter_number,
                    cs.source_version_id
                FROM character_states cs
                JOIN chapter_versions cv ON cs.source_version_id = cv.version_id
                JOIN characters ch ON cs.character_id = ch.character_id
                WHERE ch.project_id = ? AND cv.chapter_number <= ?
                ORDER BY cs.character_id, cs.field, cv.chapter_number""",
                (project_id, up_to_chapter),
            )
            rows = await cursor.fetchall()
        result = [
            {
                "character_id": row["character_id"],
                "field": row["field"],
                "value": row["value"],
                "chapter_number": row["chapter_number"],
                "source_version_id": row["source_version_id"],
            }
            for row in rows
        ]
        logger.info(
            "repository.read",
            table="character_states",
            operation="list_state_history_by_project",
            project_id=project_id,
            count=len(result),
        )
        return result
