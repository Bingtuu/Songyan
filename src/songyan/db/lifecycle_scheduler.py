"""数据生命周期调度器 — V4.0 Task 083.

提供通用框架：状态机、异步触发、异常处理、手动触发接口。
具体表的清理策略由 Task 084/085 实现 LifecycleCleaner 后注入。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Literal, Protocol
from uuid import uuid4

import structlog
from pydantic import BaseModel, Field

from songyan.db.connection import get_db

if TYPE_CHECKING:
    import aiosqlite

logger = structlog.get_logger(__name__)

LifecycleStatus = Literal["active", "dormant", "archived"]

_LIFECYCLE_TABLES: list[str] = [
    "setting_snapshots",
    "foreshadowings",
    "human_marks",
    "character_states",
    "chapter_chunks",
]


class TransitionLog(BaseModel):
    """单条状态转换日志."""

    table: str
    entity_id: str
    from_status: LifecycleStatus
    to_status: LifecycleStatus
    reason: str
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)  # noqa: UP017
    )


class LifecycleCleanupResult(BaseModel):
    """生命周期清理结果."""

    project_id: str
    current_chapter: int
    transitions: list[TransitionLog] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class LifecycleCleaner(Protocol):
    """生命周期清理器协议 — 由 Task 084/085 实现."""

    @property
    def table_name(self) -> str:
        """目标表名."""
        ...

    async def cleanup(
        self,
        conn: aiosqlite.Connection,
        project_id: str,
        current_chapter: int,
    ) -> list[TransitionLog]:
        """执行清理，返回状态转换日志列表."""
        ...


class LifecycleScheduler:
    """生命周期调度器 — 通用框架.

    Usage::
        scheduler = LifecycleScheduler()
        # 注册具体清理器（Task 084/085）
        scheduler.register_cleaner(MyCleaner())
        # 手动触发
        result = await scheduler.run_cleanup("proj-1", 50)
    """

    def __init__(self) -> None:
        self._cleaners: list[LifecycleCleaner] = []
        self._log = logger.bind(component="lifecycle_scheduler")

    def register_cleaner(self, cleaner: LifecycleCleaner) -> None:
        """注册生命周期清理器."""
        self._cleaners.append(cleaner)
        self._log.info("cleaner_registered", table=cleaner.table_name)

    async def transition(
        self,
        conn: aiosqlite.Connection,
        table: str,
        entity_id: str,
        from_status: LifecycleStatus,
        to_status: LifecycleStatus,
        reason: str,
    ) -> TransitionLog | None:
        """单条记录状态转换，带校验和日志.

        Returns:
            TransitionLog if successful, None if validation failed.
        """
        # 校验当前状态
        pk_col = _primary_key_column(table)
        cursor = await conn.execute(
            f"SELECT lifecycle_status FROM {table} WHERE {pk_col} = ?",  # noqa: S608
            (entity_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            self._log.warning(
                "transition_entity_not_found", table=table, entity_id=entity_id
            )
            return None

        current_status: LifecycleStatus = row[0]
        if current_status != from_status:
            self._log.warning(
                "transition_status_mismatch",
                table=table,
                entity_id=entity_id,
                expected=from_status,
                actual=current_status,
            )
            return None

        # 执行转换
        await conn.execute(
            f"UPDATE {table} SET lifecycle_status = ? WHERE {pk_col} = ?",  # noqa: S608
            (to_status, entity_id),
        )

        log = TransitionLog(
            table=table,
            entity_id=entity_id,
            from_status=from_status,
            to_status=to_status,
            reason=reason,
        )
        self._log.info(
            "transition_completed",
            table=table,
            entity_id=entity_id,
            from_status=from_status,
            to_status=to_status,
        )
        return log

    async def run_cleanup(
        self,
        project_id: str,
        current_chapter: int,
        conn: aiosqlite.Connection | None = None,
    ) -> LifecycleCleanupResult:
        """运行全表生命周期清理.

         SettlementExtractor 后调用。单表失败不阻塞其他表。
        """
        result = LifecycleCleanupResult(
            project_id=project_id, current_chapter=current_chapter
        )

        async def _do(c: aiosqlite.Connection) -> None:
            for cleaner in self._cleaners:
                try:
                    logs = await cleaner.cleanup(c, project_id, current_chapter)
                    result.transitions.extend(logs)
                    self._log.info(
                        "cleanup_table_completed",
                        table=cleaner.table_name,
                        transitions=len(logs),
                    )
                except (RuntimeError, OSError, ConnectionError, ValueError, TypeError) as exc:
                    error_msg = f"{cleaner.table_name}: {exc}"
                    result.errors.append(error_msg)
                    self._log.error(
                        "cleanup_table_failed",
                        table=cleaner.table_name,
                        error=str(exc),
                    )
                    # 记录到 lifecycle_errors 表
                    await self._log_error(
                        c, project_id, cleaner.table_name, "", "cleanup", str(exc)
                    )

        if conn is None:
            async with get_db() as c:
                await _do(c)
                await c.commit()
        else:
            await _do(conn)

        return result

    async def _log_error(
        self,
        conn: aiosqlite.Connection,
        project_id: str,
        table_name: str,
        entity_id: str,
        operation: str,
        error_message: str,
    ) -> None:
        """记录生命周期错误到 lifecycle_errors 表."""
        await conn.execute(
            """INSERT INTO lifecycle_errors
                (error_id, project_id, table_name, entity_id, operation, error_message)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (str(uuid4()), project_id, table_name, entity_id, operation, error_message),
        )


def _primary_key_column(table: str) -> str:
    """返回表的主键列名（简化映射）."""
    mapping: dict[str, str] = {
        "setting_snapshots": "setting_id",
        "foreshadowings": "foreshadowing_id",
        "human_marks": "mark_id",
        "character_states": "state_id",
        "chapter_chunks": "chunk_id",
    }
    return mapping.get(table, "id")
