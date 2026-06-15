"""LifecycleCleaner adapter — 将 Repository archive 方法包装为 LifecycleCleaner Protocol.

V4.0 Task 087: 统一生命周期清理入口，在 settlement 后触发。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from songyan.db.lifecycle_scheduler import LifecycleCleaner, TransitionLog

if TYPE_CHECKING:
    import aiosqlite


class _RepositoryCleanerBase:
    """通用基类 — 通过 before/after 快照记录状态变化."""

    def __init__(self, repo, pk_column: str, table_name: str) -> None:
        self.repo = repo
        self.pk_column = pk_column
        self._table_name = table_name

    @property
    def table_name(self) -> str:
        return self._table_name

    def _snapshot_sql(self) -> tuple[str, tuple]:
        """返回 (sql, params) 用于快照查询.

        默认直接查本表 project_id；子类可覆盖（如 character_states 需 JOIN）。
        """
        sql = (
            f"SELECT {self.pk_column}, lifecycle_status FROM {self._table_name} "  # noqa: S608
            f"WHERE project_id = ?"  # noqa: S608
        )
        return sql, ()

    async def _snapshot(
        self, conn: aiosqlite.Connection, project_id: str
    ) -> dict[str, str]:
        sql, _ = self._snapshot_sql()
        cursor = await conn.execute(sql, (project_id,))
        rows = await cursor.fetchall()
        return {str(r[0]): r[1] for r in rows}

    async def _do_archive(
        self, project_id: str, current_chapter: int, conn: aiosqlite.Connection
    ) -> None:
        """子类覆盖：调用具体的 repository archive 方法."""
        raise NotImplementedError

    async def cleanup(
        self,
        conn: aiosqlite.Connection,
        project_id: str,
        current_chapter: int,
    ) -> list[TransitionLog]:
        before = await self._snapshot(conn, project_id)
        await self._do_archive(project_id, current_chapter, conn)
        after = await self._snapshot(conn, project_id)

        logs: list[TransitionLog] = []
        for entity_id, new_status in after.items():
            old_status = before.get(entity_id)
            if old_status != new_status:
                logs.append(
                    TransitionLog(
                        table=self._table_name,
                        entity_id=entity_id,
                        from_status=old_status,  # type: ignore[arg-type]
                        to_status=new_status,  # type: ignore[arg-type]
                        reason=f"chapter={current_chapter}",
                    )
                )
        return logs


class SettingSnapshotCleaner(_RepositoryCleanerBase, LifecycleCleaner):
    """setting_snapshots 生命周期清理器."""

    def __init__(self) -> None:
        from songyan.db.settlement_repo import SettingSnapshotRepository

        super().__init__(SettingSnapshotRepository(), "setting_id", "setting_snapshots")

    async def _do_archive(
        self, project_id: str, current_chapter: int, conn: aiosqlite.Connection
    ) -> None:
        await self.repo.archive_stale(project_id, current_chapter, conn=conn)
        await self.repo.archive_very_stale(project_id, current_chapter, conn=conn)


class ForeshadowingCleaner(_RepositoryCleanerBase, LifecycleCleaner):
    """foreshadowings 生命周期清理器."""

    def __init__(self) -> None:
        from songyan.db.settlement_repo import ForeshadowingRepository

        super().__init__(
            ForeshadowingRepository(), "foreshadowing_id", "foreshadowings"
        )

    async def _do_archive(
        self, project_id: str, current_chapter: int, conn: aiosqlite.Connection
    ) -> None:
        await self.repo.archive_overdue(project_id, current_chapter, conn=conn)
        await self.repo.archive_very_overdue(project_id, current_chapter, conn=conn)
        await self.repo.archive_resolved(project_id, conn=conn)


class HumanMarkCleaner(_RepositoryCleanerBase, LifecycleCleaner):
    """human_marks 生命周期清理器."""

    def __init__(self) -> None:
        from songyan.db.human_mark_repo import HumanMarkRepository

        super().__init__(HumanMarkRepository(), "mark_id", "human_marks")

    async def _do_archive(
        self, project_id: str, current_chapter: int, conn: aiosqlite.Connection
    ) -> None:
        await self.repo.archive_stale(project_id, current_chapter, conn=conn)
        await self.repo.archive_very_stale(project_id, current_chapter, conn=conn)


class CharacterStateCleaner(_RepositoryCleanerBase, LifecycleCleaner):
    """character_states 生命周期清理器."""

    def __init__(self) -> None:
        from songyan.db.context_repo import CharacterStateRepository

        super().__init__(CharacterStateRepository(), "state_id", "character_states")

    def _snapshot_sql(self) -> tuple[str, tuple]:
        """character_states 无 project_id，需 JOIN characters."""
        sql = (
            "SELECT cs.state_id, cs.lifecycle_status FROM character_states cs "
            "JOIN characters c ON cs.character_id = c.character_id "
            "WHERE c.project_id = ?"
        )
        return sql, ()

    async def _do_archive(
        self, project_id: str, current_chapter: int, conn: aiosqlite.Connection
    ) -> None:
        await self.repo.archive_stale(project_id, current_chapter, conn=conn)
        await self.repo.archive_stale_functional(
            project_id, current_chapter, conn=conn
        )
        await self.repo.archive_very_stale(project_id, current_chapter, conn=conn)
        await self.repo.archive_overflow(project_id, current_chapter, conn=conn)


class SettingDeduplicationCleaner(LifecycleCleaner):
    """setting_tracking 语义去重清理器 — Task 110.

    每 10 章触发一次 SettingDeduplicationService.deduplicate。
    """

    @property
    def table_name(self) -> str:
        return "setting_tracking"

    async def cleanup(
        self,
        conn: aiosqlite.Connection,
        project_id: str,
        current_chapter: int,
    ) -> list[TransitionLog]:
        if current_chapter % 10 != 0:
            return []
        from songyan.db.settlement_repo import SettingDeduplicationService

        service = SettingDeduplicationService()
        archived = await service.deduplicate(project_id, conn=conn)
        if archived > 0:
            return [
                TransitionLog(
                    table=self.table_name,
                    entity_id=f"dedup:{project_id}:{current_chapter}",
                    from_status="active",
                    to_status="archived",
                    reason=f"semantic_dedup:chapter={current_chapter}",
                )
            ]
        return []


def get_default_scheduler():
    """返回预注册了全部清理器的 LifecycleScheduler 实例."""
    from songyan.db.lifecycle_scheduler import LifecycleScheduler

    scheduler = LifecycleScheduler()
    scheduler.register_cleaner(SettingSnapshotCleaner())
    scheduler.register_cleaner(SettingDeduplicationCleaner())
    scheduler.register_cleaner(ForeshadowingCleaner())
    scheduler.register_cleaner(HumanMarkCleaner())
    scheduler.register_cleaner(CharacterStateCleaner())
    return scheduler
