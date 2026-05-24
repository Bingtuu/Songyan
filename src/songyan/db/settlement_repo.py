"""Async repositories for settlement outputs."""

from __future__ import annotations

from sqlite3 import Row

import structlog

from songyan.db.connection import get_db
from songyan.db.repository import _from_json, _model_json
from songyan.models import Decrement, ForeshadowingItem, Increment, NewSetting, NumericalUpdate

logger = structlog.get_logger(__name__)


class ForeshadowingRepository:
    """Repository for foreshadowing records."""

    async def create(
        self,
        item: ForeshadowingItem,
        project_id: str,
        source_version_id: str | None = None,
    ) -> None:
        async with get_db() as conn:
            await conn.execute(
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
            await conn.commit()
        logger.info(
            "repository.write",
            table="foreshadowings",
            operation="insert",
            foreshadowing_id=item.foreshadowing_id,
        )

    async def update_status(self, foreshadowing_id: str, status: str) -> None:
        async with get_db() as conn:
            await conn.execute(
                "UPDATE foreshadowings SET status = ? WHERE foreshadowing_id = ?",
                (status, foreshadowing_id),
            )
            await conn.commit()
        logger.info(
            "repository.write",
            table="foreshadowings",
            operation="update_status",
            foreshadowing_id=foreshadowing_id,
        )

    async def list_active(self, project_id: str) -> list[ForeshadowingItem]:
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                """SELECT * FROM foreshadowings
                WHERE project_id = ? AND status != 'resolved'
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
            )
            for row in rows
        ]


class SettingSnapshotRepository:
    """Repository for setting snapshots."""

    async def create(self, setting: NewSetting, project_id: str, setting_id: str) -> None:
        async with get_db() as conn:
            await conn.execute(
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
            await conn.commit()
        logger.info(
            "repository.write",
            table="setting_snapshots",
            operation="insert",
            setting_id=setting_id,
        )

    async def list_by_project(self, project_id: str) -> list[NewSetting]:
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                """SELECT * FROM setting_snapshots
                WHERE project_id = ?
                ORDER BY created_at, setting_id""",
                (project_id,),
            )
            rows = await cursor.fetchall()
        return [
            NewSetting(
                setting_name=row["setting_name"],
                description=row["description"],
                source_quote=row["source_quote"],
                setting_key=row["setting_key"],
            )
            for row in rows
        ]


class NumericalLedgerRepository:
    """Repository for numerical ledgers."""

    async def create(
        self,
        update: NumericalUpdate,
        project_id: str,
        chapter_number: int,
        ledger_id: str,
    ) -> None:
        async with get_db() as conn:
            await conn.execute(
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
            await conn.commit()
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
