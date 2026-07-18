"""Task 172c.p inventory repair helper.

This is a test/backfill utility for old wuxia DB rows whose inventory tracker
stored aggregate lists as one item. It expands aggregate rows, merges duplicate
items, refreshes last-used chapters from accepted text, and drops stale items
that cannot be grounded in the accepted text.
"""

from __future__ import annotations

import uuid
from typing import Any

from songyan.agents.continuity_auditor._scanners import (
    FORGOTTEN_THRESHOLD,
    _item_mentioned_in_content,
    _item_reference_terms,
)
from songyan.agents.settlement_extractor._apply import (
    _INVENTORY_CONSUMED_RE,
    _is_inventory_fragment,
    _item_base_name,
    _normalize_item_name,
    _split_inventory_items,
)
from songyan.db.connection import get_db
from songyan.db.continuity_repo import InventoryTrackerRepository


async def _accepted_contents(
    project_id: str,
    up_to_chapter: int,
) -> list[tuple[int, str]]:
    async with get_db() as conn:
        cursor = await conn.execute(
            """SELECT h.chapter_number, cv.content
               FROM chapter_heads h
               JOIN chapter_versions cv ON cv.version_id = h.accepted_version_id
               WHERE h.project_id = ?
                 AND h.status = 'accepted'
                 AND h.chapter_number <= ?
               ORDER BY h.chapter_number""",
            (project_id, up_to_chapter),
        )
        rows = await cursor.fetchall()
    return [(int(chapter), str(content or "")) for chapter, content in rows]


def _latest_mention(
    item_name: str,
    contents: list[tuple[int, str]],
) -> int | None:
    terms = _item_reference_terms(item_name)
    matched = [
        chapter
        for chapter, content in contents
        if _item_mentioned_in_content(item_name, terms, content)
    ]
    return max(matched) if matched else None


def _merge_key(row: dict[str, Any], item_name: str) -> tuple[str, str]:
    return (str(row.get("character_id") or ""), _normalize_item_name(item_name))


async def repair_inventory(project_id: str, up_to_chapter: int) -> dict[str, int]:
    """Repair legacy aggregate inventory rows for one project."""
    repo = InventoryTrackerRepository()
    rows = await repo.list_by_project(project_id)
    contents = await _accepted_contents(project_id, up_to_chapter)
    before_rows = len(rows)
    deleted = 0
    merged: dict[tuple[str, str], dict[str, Any]] = {}

    for row in rows:
        item_names = _split_inventory_items(str(row.get("item_name") or ""))
        if not item_names:
            item_names = [str(row.get("item_name") or "").strip()]
        for item_name in item_names:
            if not item_name:
                continue
            base_name = _item_base_name(item_name)
            if _is_inventory_fragment(base_name):
                deleted += 1
                continue
            consumed = bool(_INVENTORY_CONSUMED_RE.search(item_name)) or (
                row.get("status") == "consumed"
            )
            acquired = int(row.get("acquired_in_chapter") or 0)
            latest = _latest_mention(item_name, contents)
            if latest is None and not consumed and up_to_chapter - acquired >= FORGOTTEN_THRESHOLD:
                deleted += 1
                continue
            key = _merge_key(row, item_name)
            existing = merged.get(key)
            last_used = latest if latest is not None else int(row.get("last_used_chapter") or acquired)
            candidate = {
                "character_id": row.get("character_id") or "",
                "item_name": item_name,
                "item_description": row.get("item_description") or "",
                "acquired_in_chapter": acquired,
                "last_used_chapter": last_used,
                "status": "consumed" if consumed else row.get("status", "held"),
            }
            if existing is None:
                merged[key] = candidate
                continue
            if acquired < int(existing["acquired_in_chapter"]):
                existing["acquired_in_chapter"] = acquired
                existing["item_name"] = item_name
            existing["last_used_chapter"] = max(
                int(existing["last_used_chapter"]),
                last_used,
            )
            if candidate["status"] == "consumed":
                existing["status"] = "consumed"

    async with get_db() as conn:
        await conn.execute("DELETE FROM inventory_tracker WHERE project_id = ?", (project_id,))
        for item in merged.values():
            track_id = f"inv-repair-{uuid.uuid4().hex[:12]}"
            await repo.create(
                track_id=track_id,
                project_id=project_id,
                character_id=str(item["character_id"]),
                item_name=str(item["item_name"])[:50],
                item_description=str(item["item_description"]),
                acquired_in_chapter=int(item["acquired_in_chapter"]),
                status=str(item["status"]),
                conn=conn,
            )
            await repo.update_last_used(
                track_id,
                int(item["last_used_chapter"]),
                conn=conn,
            )
        await conn.commit()

    return {"before_rows": before_rows, "after_rows": len(merged), "deleted": deleted}
