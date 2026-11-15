"""task 266：角色/设定编辑审计（profile_edit_history）。

仿 storyline_edit_history 先例：before/after 全行 JSON，与目标行同事务写。
本模块只管审计行；业务写入在 CharacterRepository / SettingSnapshotRepository。
"""

from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    import aiosqlite

logger = structlog.get_logger(__name__)


def _dump(row: Any) -> str | None:
    if row is None:
        return None
    if hasattr(row, "model_dump"):
        return json.dumps(row.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
    return json.dumps(dict(row), ensure_ascii=False, sort_keys=True, default=str)


class ProfileEditHistoryRepository:
    """profile_edit_history 写入（target_type: character | setting）。"""

    async def record_history(
        self,
        *,
        project_id: str,
        target_type: str,
        target_id: str,
        action: str,
        before: Any,
        after: Any,
        conn: aiosqlite.Connection,
    ) -> None:
        await conn.execute(
            """INSERT INTO profile_edit_history (
                history_id, project_id, target_type, target_id,
                action, before_json, after_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                f"peh-{uuid.uuid4().hex[:12]}",
                project_id,
                target_type,
                target_id,
                action,
                _dump(before),
                _dump(after),
            ),
        )
        logger.info(
            "profile_edit.history",
            project_id=project_id,
            target_type=target_type,
            target_id=target_id,
            action=action,
        )
