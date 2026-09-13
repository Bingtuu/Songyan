"""V15 Task 236: import_replay_marks 读写 — 导入回放幂等标记."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from songyan.db.connection import get_db
from songyan.exceptions import ImportReplayError
from songyan.models.import_replay import ReplayMark

if TYPE_CHECKING:
    import aiosqlite

logger = structlog.get_logger(__name__)


class ImportReplayRepository:
    """import_replay_marks 的读写；所有方法支持外部 conn（同事务写入）."""

    async def get_mark(
        self,
        project_id: str,
        chapter_number: int,
        conn: aiosqlite.Connection | None = None,
    ) -> ReplayMark | None:
        """按 (project_id, chapter_number) 查询幂等标记；无记录返回 None."""

        async def _do(c: aiosqlite.Connection) -> ReplayMark | None:
            cursor = await c.execute(
                """SELECT project_id, run_id, chapter_number, draft_version_id,
                          accepted_version_id, summary_id, source_fingerprint
                   FROM import_replay_marks
                   WHERE project_id = ? AND chapter_number = ?""",
                (project_id, chapter_number),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return ReplayMark(
                project_id=row[0],
                run_id=row[1],
                chapter_number=row[2],
                draft_version_id=row[3],
                accepted_version_id=row[4],
                summary_id=row[5],
                source_fingerprint=row[6],
            )

        if conn is not None:
            return await _do(conn)
        async with get_db() as c:
            return await _do(c)

    async def insert_mark(
        self,
        mark: ReplayMark,
        conn: aiosqlite.Connection | None = None,
    ) -> None:
        """幂等插入：已存在同 (project_id, chapter_number) 行时——
        指纹一致则忽略，不一致抛 ImportReplayError.
        """

        async def _do(c: aiosqlite.Connection) -> None:
            cursor = await c.execute(
                "SELECT source_fingerprint FROM import_replay_marks "
                "WHERE project_id = ? AND chapter_number = ?",
                (mark.project_id, mark.chapter_number),
            )
            row = await cursor.fetchone()
            if row is not None:
                if row[0] == mark.source_fingerprint:
                    return
                msg = (
                    "replay mark fingerprint mismatch for "
                    f"project={mark.project_id} chapter={mark.chapter_number}: "
                    f"existing={row[0]} new={mark.source_fingerprint}"
                )
                raise ImportReplayError(msg)
            await c.execute(
                """INSERT INTO import_replay_marks (
                    project_id, run_id, chapter_number, draft_version_id,
                    accepted_version_id, summary_id, source_fingerprint
                ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    mark.project_id,
                    mark.run_id,
                    mark.chapter_number,
                    mark.draft_version_id,
                    mark.accepted_version_id,
                    mark.summary_id,
                    mark.source_fingerprint,
                ),
            )

        if conn is not None:
            await _do(conn)
        else:
            async with get_db() as c:
                await _do(c)
                await c.commit()
        logger.info(
            "repository.write",
            table="import_replay_marks",
            operation="insert_mark",
            project_id=mark.project_id,
            chapter_number=mark.chapter_number,
        )
