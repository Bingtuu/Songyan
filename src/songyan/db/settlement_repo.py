"""Async repositories for settlement outputs."""

from __future__ import annotations

import difflib
from sqlite3 import Row
from typing import TYPE_CHECKING

import structlog

from songyan.db.connection import get_db

if TYPE_CHECKING:
    import aiosqlite
from songyan.db.repository import _from_json
from songyan.models import Decrement, ForeshadowingItem, Increment, NewSetting, NumericalUpdate
from songyan.utils.json_helpers import model_json as _model_json

logger = structlog.get_logger(__name__)


class ForeshadowingRepository:
    """Repository for foreshadowing records."""

    async def create(
        self,
        item: ForeshadowingItem,
        project_id: str,
        source_version_id: str | None = None,
        conn: aiosqlite.Connection | None = None,
    ) -> None:
        async def _do(c: aiosqlite.Connection) -> None:
            await c.execute(
                """INSERT INTO foreshadowings (
                    foreshadowing_id, project_id, description, planted_in_chapter,
                    expected_resolve_chapter, status, source_version_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    item.foreshadowing_id,
                    project_id,
                    item.description,
                    item.planted_in_chapter,
                    item.expected_resolve_chapter,
                    item.status,
                    source_version_id,
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
            table="foreshadowings",
            operation="insert",
            foreshadowing_id=item.foreshadowing_id,
        )

    async def update_status(
        self, foreshadowing_id: str, status: str, conn: aiosqlite.Connection | None = None
    ) -> None:
        async def _do(c: aiosqlite.Connection) -> None:
            await c.execute(
                "UPDATE foreshadowings SET status = ? WHERE foreshadowing_id = ?",
                (status, foreshadowing_id),
            )

        if conn is None:
            async with get_db() as c:
                await _do(c)
                await c.commit()
        else:
            await _do(conn)
        logger.info(
            "repository.write",
            table="foreshadowings",
            operation="update_status",
            foreshadowing_id=foreshadowing_id,
        )

    async def list_all(self, project_id: str) -> list[ForeshadowingItem]:
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                "SELECT * FROM foreshadowings WHERE project_id = ? ORDER BY planted_in_chapter",
                (project_id,),
            )
            rows = await cursor.fetchall()
        return [
            ForeshadowingItem(
                foreshadowing_id=row["foreshadowing_id"],
                description=row["description"],
                planted_in_chapter=row["planted_in_chapter"],
                expected_resolve_chapter=row["expected_resolve_chapter"],
                status=row["status"],
                source_version_id=row["source_version_id"],
            )
            for row in rows
        ]

    async def list_active(self, project_id: str) -> list[ForeshadowingItem]:
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                """SELECT * FROM foreshadowings
                WHERE project_id = ?
                  AND lifecycle_status = 'active'
                  AND status IN ('planted', 'due')
                ORDER BY planted_in_chapter, foreshadowing_id""",
                (project_id,),
            )
            rows = await cursor.fetchall()
        return [
            ForeshadowingItem(
                foreshadowing_id=row["foreshadowing_id"],
                description=row["description"],
                planted_in_chapter=row["planted_in_chapter"],
                expected_resolve_chapter=row["expected_resolve_chapter"],
                status=row["status"],
                source_version_id=row["source_version_id"],
            )
            for row in rows
        ]

    async def archive_overdue(
        self, project_id: str, current_chapter: int, window: int = 5,
        conn: aiosqlite.Connection | None = None,
    ) -> int:
        """将 overdue > window 章的 foreshadowings 标记为 dormant.

        条件: current_chapter - expected_resolve_chapter > window
              AND lifecycle_status = 'active'
        返回: 影响的记录数
        """
        async def _do(c: aiosqlite.Connection) -> int:
            cursor = await c.execute(
                """UPDATE foreshadowings
                SET lifecycle_status = 'dormant'
                WHERE project_id = ?
                  AND lifecycle_status = 'active'
                  AND status IN ('planted', 'due', 'overdue')
                  AND expected_resolve_chapter IS NOT NULL
                  AND ? - expected_resolve_chapter > ?""",
                (project_id, current_chapter, window),
            )
            return cursor.rowcount

        if conn is None:
            async with get_db() as c:
                archived = await _do(c)
                await c.commit()
        else:
            archived = await _do(conn)
        if archived > 0:
            logger.info(
                "repository.write",
                table="foreshadowings",
                operation="archive_overdue",
                project_id=project_id,
                current_chapter=current_chapter,
                window=window,
                archived_count=archived,
            )
        return archived

    async def archive_very_overdue(
        self, project_id: str, current_chapter: int, window: int = 15,
        conn: aiosqlite.Connection | None = None,
    ) -> int:
        """将 overdue > window 章的 dormant foreshadowings 标记为 archived.

        条件: current_chapter - expected_resolve_chapter > window
              AND lifecycle_status = 'dormant'
        返回: 影响的记录数
        """
        async def _do(c: aiosqlite.Connection) -> int:
            cursor = await c.execute(
                """UPDATE foreshadowings
                SET lifecycle_status = 'archived'
                WHERE project_id = ?
                  AND lifecycle_status = 'dormant'
                  AND status IN ('planted', 'due', 'overdue')
                  AND expected_resolve_chapter IS NOT NULL
                  AND ? - expected_resolve_chapter > ?""",
                (project_id, current_chapter, window),
            )
            return cursor.rowcount

        if conn is None:
            async with get_db() as c:
                archived = await _do(c)
                await c.commit()
        else:
            archived = await _do(conn)
        if archived > 0:
            logger.info(
                "repository.write",
                table="foreshadowings",
                operation="archive_very_overdue",
                project_id=project_id,
                current_chapter=current_chapter,
                window=window,
                archived_count=archived,
            )
        return archived

    async def archive_resolved(
        self, project_id: str, conn: aiosqlite.Connection | None = None,
    ) -> int:
        """将 status='resolved' 的 foreshadowings 标记为 archived.

        返回: 影响的记录数
        """
        async def _do(c: aiosqlite.Connection) -> int:
            cursor = await c.execute(
                """UPDATE foreshadowings
                SET lifecycle_status = 'archived'
                WHERE project_id = ?
                  AND status = 'resolved'
                  AND lifecycle_status IN ('active', 'dormant')""",
                (project_id,),
            )
            return cursor.rowcount

        if conn is None:
            async with get_db() as c:
                archived = await _do(c)
                await c.commit()
        else:
            archived = await _do(conn)
        if archived > 0:
            logger.info(
                "repository.write",
                table="foreshadowings",
                operation="archive_resolved",
                project_id=project_id,
                archived_count=archived,
            )
        return archived

    async def mark_overdue(
        self,
        project_id: str,
        current_chapter: int,
        conn: aiosqlite.Connection | None = None,
    ) -> int:
        """将 expected_resolve_chapter < current_chapter 的 planted/due 伏笔标记为 overdue."""
        async def _do(c: aiosqlite.Connection) -> int:
            cursor = await c.execute(
                """UPDATE foreshadowings
                SET status = 'overdue'
                WHERE project_id = ?
                  AND status IN ('planted', 'due')
                  AND expected_resolve_chapter IS NOT NULL
                  AND expected_resolve_chapter < ?""",
                (project_id, current_chapter),
            )
            return cursor.rowcount

        if conn is None:
            async with get_db() as c:
                updated = await _do(c)
                await c.commit()
        else:
            updated = await _do(conn)
        if updated > 0:
            logger.info(
                "repository.write",
                table="foreshadowings",
                operation="mark_overdue",
                project_id=project_id,
                current_chapter=current_chapter,
                updated_count=updated,
            )
        return updated

    async def get_unresolved_ratio(
        self,
        project_id: str,
        current_chapter: int,
        conn: aiosqlite.Connection | None = None,
    ) -> float:
        """计算未解决伏笔比例 = (planted + due) / current_chapter."""
        async def _do(c: aiosqlite.Connection) -> float:
            cursor = await c.execute(
                """SELECT COUNT(*) FROM foreshadowings
                WHERE project_id = ?
                  AND status IN ('planted', 'due')""",
                (project_id,),
            )
            row = await cursor.fetchone()
            unresolved = row[0] if row else 0
            return unresolved / current_chapter if current_chapter > 0 else 0.0

        if conn is None:
            async with get_db() as c:
                return await _do(c)
        return await _do(conn)


    async def list_with_lifecycle(self, project_id: str) -> list[dict]:
        """返回伏笔（含 lifecycle_status），用于真兑现 vs 逾期归档区分（V6 Task 148）."""
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                """SELECT foreshadowing_id, description, planted_in_chapter,
                          expected_resolve_chapter, status, lifecycle_status
                   FROM foreshadowings WHERE project_id = ?
                   ORDER BY planted_in_chapter, foreshadowing_id""",
                (project_id,),
            )
            rows = await cursor.fetchall()
        return [dict(row) for row in rows]


class SettingSnapshotRepository:
    """Repository for setting snapshots."""

    async def create(
        self,
        setting: NewSetting,
        project_id: str,
        setting_id: str,
        conn: aiosqlite.Connection | None = None,
    ) -> None:
        async def _do(c: aiosqlite.Connection) -> None:
            await c.execute(
                """INSERT INTO setting_snapshots (
                    setting_id, project_id, setting_name, description,
                    source_quote, setting_key
                ) VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    setting_id,
                    project_id,
                    setting.setting_name,
                    setting.description,
                    setting.source_quote,
                    setting.setting_key,
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
            table="setting_snapshots",
            operation="insert",
            setting_id=setting_id,
        )

    async def list_by_project(self, project_id: str) -> list[NewSetting]:
        """只返回 lifecycle_status='active' 的 setting_snapshots."""
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                """SELECT * FROM setting_snapshots
                WHERE project_id = ?
                  AND lifecycle_status = 'active'
                ORDER BY created_at, setting_id""",
                (project_id,),
            )
            rows = await cursor.fetchall()
        result: list[NewSetting] = []
        for i, row in enumerate(rows):
            result.append(
                NewSetting(
                    setting_name=row["setting_name"],
                    description=row["description"],
                    source_quote=row["source_quote"],
                    setting_key=row["setting_key"],
                    chapter_number=i + 1,  # 1-indexed ordinal
                )
            )
        return result

    async def archive_stale(
        self,
        project_id: str,
        current_chapter: int,
        window: int = 10,
        conn: aiosqlite.Connection | None = None,
    ) -> int:
        """将 N 章未提及的 setting_snapshots 标记为 dormant.

        通过 JOIN setting_tracking 判断 last_mentioned_chapter。
        is_critical（human_marks priority>=8）除外。
        同步将 setting_tracking.status 标记为 dormant，避免 orphan 统计失真。
        返回: 影响的记录数
        """
        async def _do(c: aiosqlite.Connection) -> int:
            cursor = await c.execute(
                """UPDATE setting_snapshots
                SET lifecycle_status = 'dormant'
                WHERE project_id = ?
                  AND lifecycle_status = 'active'
                  AND setting_key IN (
                      SELECT st.setting_key FROM setting_tracking st
                      WHERE st.project_id = ?
                        AND st.last_mentioned_chapter < ?
                  )
                  AND setting_key NOT IN (
                      SELECT target_key FROM human_marks
                      WHERE project_id = ?
                        AND priority >= 8
                        AND mark_type = 'setting'
                        AND lifecycle_status = 'active'
                  )""",
                (
                    project_id,
                    project_id,
                    current_chapter - window,
                    project_id,
                ),
            )
            # 同步 tracking 表状态
            await c.execute(
                """UPDATE setting_tracking
                SET status = 'dormant'
                WHERE project_id = ?
                  AND status = 'active'
                  AND last_mentioned_chapter < ?
                  AND setting_key NOT IN (
                      SELECT target_key FROM human_marks
                      WHERE project_id = ?
                        AND priority >= 8
                        AND mark_type = 'setting'
                        AND lifecycle_status = 'active'
                  )""",
                (project_id, current_chapter - window, project_id),
            )
            return cursor.rowcount

        if conn is None:
            async with get_db() as c:
                archived = await _do(c)
                await c.commit()
        else:
            archived = await _do(conn)
        if archived > 0:
            logger.info(
                "repository.write",
                table="setting_snapshots",
                operation="archive_stale",
                project_id=project_id,
                current_chapter=current_chapter,
                window=window,
                archived_count=archived,
            )
        return archived

    async def list_active_with_tracking(
        self, project_id: str
    ) -> list[dict]:
        """返回 active 设定及其 tracking 信息（用于 resolve_confidence 计算）.

        V5.0 Task 103: JOIN setting_tracking 获取 last_mentioned_chapter 和 category。
        """
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                """SELECT
                    ss.setting_id,
                    ss.setting_name,
                    ss.description,
                    ss.source_quote,
                    ss.setting_key,
                    ss.lifecycle_status,
                    ss.created_at,
                    st.last_mentioned_chapter,
                    st.introduced_in_chapter,
                    st.category
                FROM setting_snapshots ss
                LEFT JOIN setting_tracking st
                    ON ss.setting_key = st.setting_key
                    AND ss.project_id = st.project_id
                WHERE ss.project_id = ?
                  AND ss.lifecycle_status = 'active'
                ORDER BY ss.created_at""",
                (project_id,),
            )
            rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def archive_by_confidence(
        self,
        project_id: str,
        low_confidence_keys: list[str],
        conn: aiosqlite.Connection | None = None,
    ) -> int:
        """将低 confidence 的 setting_snapshots 标记为 archived.

        V5.0 Task 103: 由 SettingEvaporator 调用，纯规则蒸发。
        同步将 setting_tracking.status 标记为 archived，保持生命周期一致。
        """
        if not low_confidence_keys:
            return 0

        placeholders = ",".join("?" * len(low_confidence_keys))
        sql = f"""UPDATE setting_snapshots
            SET lifecycle_status = 'archived'
            WHERE project_id = ?
              AND lifecycle_status = 'active'
              AND setting_key IN ({placeholders})"""
        params = [project_id] + low_confidence_keys

        async def _do(c: aiosqlite.Connection) -> int:
            cursor = await c.execute(sql, params)
            await c.execute(
                f"""UPDATE setting_tracking
                SET status = 'archived'
                WHERE project_id = ?
                  AND status IN ('active', 'dormant')
                  AND setting_key IN ({placeholders})""",
                params,
            )
            return cursor.rowcount

        if conn is None:
            async with get_db() as c:
                archived = await _do(c)
                await c.commit()
        else:
            archived = await _do(conn)
        if archived > 0:
            logger.info(
                "repository.write",
                table="setting_snapshots",
                operation="archive_by_confidence",
                project_id=project_id,
                archived_count=archived,
                keys=low_confidence_keys,
            )
        return archived

    async def archive_very_stale(
        self,
        project_id: str,
        current_chapter: int,
        window: int = 20,
        conn: aiosqlite.Connection | None = None,
    ) -> int:
        """将 M 章未提及的 dormant setting_snapshots 标记为 archived.

        返回: 影响的记录数
        """
        async def _do(c: aiosqlite.Connection) -> int:
            cursor = await c.execute(
                """UPDATE setting_snapshots
                SET lifecycle_status = 'archived'
                WHERE project_id = ?
                  AND lifecycle_status = 'dormant'
                  AND setting_key IN (
                      SELECT st.setting_key FROM setting_tracking st
                      WHERE st.project_id = ?
                        AND st.last_mentioned_chapter < ?
                  )""",
                (
                    project_id,
                    project_id,
                    current_chapter - window,
                ),
            )
            return cursor.rowcount

        if conn is None:
            async with get_db() as c:
                archived = await _do(c)
                await c.commit()
        else:
            archived = await _do(conn)
        if archived > 0:
            logger.info(
                "repository.write",
                table="setting_snapshots",
                operation="archive_very_stale",
                project_id=project_id,
                current_chapter=current_chapter,
                window=window,
                archived_count=archived,
            )
        return archived

    async def archive_by_key(
        self,
        project_id: str,
        setting_key: str,
        conn: aiosqlite.Connection | None = None,
    ) -> int:
        """将指定 setting_key 的 active snapshots 标记为 archived.

        Task 110b: 同一 setting_key 更新时，旧版本自动归档，保留最新版本。
        返回: 影响的记录数。
        """
        async def _do(c: aiosqlite.Connection) -> int:
            cursor = await c.execute(
                """UPDATE setting_snapshots
                SET lifecycle_status = 'archived'
                WHERE project_id = ?
                  AND setting_key = ?
                  AND lifecycle_status = 'active'""",
                (project_id, setting_key),
            )
            return cursor.rowcount

        if conn is None:
            async with get_db() as c:
                archived = await _do(c)
                await c.commit()
        else:
            archived = await _do(conn)
        if archived > 0:
            logger.info(
                "repository.write",
                table="setting_snapshots",
                operation="archive_by_key",
                project_id=project_id,
                setting_key=setting_key,
                archived_count=archived,
            )
        return archived


class SettingDeduplicationService:
    """设定语义去重服务 — Task 110.

    基于文本相似度检测并合并语义重复的 active setting 记录。
    """

    def __init__(self) -> None:
        self._log = logger.bind(component="setting_deduplication")

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        """计算两段文本的相似度，返回 0.0 ~ 1.0."""
        return difflib.SequenceMatcher(None, a, b).ratio()

    async def deduplicate(
        self,
        project_id: str,
        threshold: float = 0.85,
        conn: aiosqlite.Connection | None = None,
    ) -> int:
        """对 setting_tracking 中 active 记录进行语义去重.

        保留 introduced_in_chapter 最早的主记录，archive 较新的重复记录，
        同时同步更新 setting_snapshots 的 lifecycle_status。
        返回: 被 archive 的记录数。
        """
        async def _do(c: aiosqlite.Connection) -> int:
            cursor = await c.execute(
                """SELECT tracking_id, setting_key, setting_name, description,
                           introduced_in_chapter, last_mentioned_chapter
                    FROM setting_tracking
                    WHERE project_id = ? AND status = 'active'
                    ORDER BY introduced_in_chapter, tracking_id""",
                (project_id,),
            )
            rows = await cursor.fetchall()
            if len(rows) < 2:
                return 0

            archived_count = 0
            # 已处理（被 archive）的 tracking_id 集合，避免重复处理
            archived_ids: set[str] = set()

            for i in range(len(rows)):
                master = rows[i]
                master_id = master[0]
                if master_id in archived_ids:
                    continue
                master_text = f"{master[2]} {master[3]}"
                master_last = master[5]

                for j in range(i + 1, len(rows)):
                    dup = rows[j]
                    dup_id = dup[0]
                    if dup_id in archived_ids:
                        continue
                    dup_text = f"{dup[2]} {dup[3]}"

                    sim = self._similarity(master_text, dup_text)
                    if sim >= threshold:
                        # archive 重复记录
                        await c.execute(
                            """UPDATE setting_tracking
                            SET status = 'archived'
                            WHERE tracking_id = ?""",
                            (dup_id,),
                        )
                        # 同步 archive setting_snapshots
                        await c.execute(
                            """UPDATE setting_snapshots
                            SET lifecycle_status = 'archived'
                            WHERE project_id = ? AND setting_key = ?""",
                            (project_id, dup[1]),
                        )
                        archived_ids.add(dup_id)
                        archived_count += 1
                        # 更新主记录的 last_mentioned_chapter
                        if dup[5] > master_last:
                            master_last = dup[5]
                            await c.execute(
                                """UPDATE setting_tracking
                                SET last_mentioned_chapter = ?
                                WHERE tracking_id = ?""",
                                (master_last, master_id),
                            )

            return archived_count

        if conn is None:
            async with get_db() as c:
                count = await _do(c)
                await c.commit()
        else:
            count = await _do(conn)
        if count > 0:
            self._log.info(
                "setting_deduplication.completed",
                project_id=project_id,
                threshold=threshold,
                archived_count=count,
            )
        return count


class NumericalLedgerRepository:
    """Repository for numerical ledgers."""

    async def create(
        self,
        update: NumericalUpdate,
        project_id: str,
        chapter_number: int,
        ledger_id: str,
        conn: aiosqlite.Connection | None = None,
    ) -> None:
        async def _do(c: aiosqlite.Connection) -> None:
            await c.execute(
                """INSERT INTO numerical_ledgers (
                    ledger_id, project_id, character_id, attribute_name,
                    chapter_number, opening_value, increments, decrements,
                    closing_value
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    ledger_id,
                    project_id,
                    update.character_id,
                    update.attribute_name,
                    chapter_number,
                    update.opening_value,
                    _model_json(update.increments),
                    _model_json(update.decrements),
                    update.closing_value,
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
            table="numerical_ledgers",
            operation="insert",
            ledger_id=ledger_id,
        )

    async def get_latest(self, character_id: str, attribute_name: str) -> NumericalUpdate | None:
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                """SELECT * FROM numerical_ledgers
                WHERE character_id = ? AND attribute_name = ?
                ORDER BY chapter_number DESC, created_at DESC, ledger_id DESC
                LIMIT 1""",
                (character_id, attribute_name),
            )
            row = await cursor.fetchone()
        if row is None:
            return None
        return NumericalUpdate(
            character_id=row["character_id"],
            attribute_name=row["attribute_name"],
            opening_value=row["opening_value"],
            increments=[
                Increment.model_validate(item) for item in _from_json(row["increments"], [])
            ],
            decrements=[
                Decrement.model_validate(item) for item in _from_json(row["decrements"], [])
            ],
            closing_value=row["closing_value"],
        )
