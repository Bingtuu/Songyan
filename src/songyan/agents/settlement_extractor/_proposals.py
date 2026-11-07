"""Enqueue settlement / import extracts as plan_* pending proposals (M2 step 5).

Writes ``approval_status=pending`` with attribute ``source=extract`` only.
Never writes ``approved`` into plan tables. Settlement tables remain the
runtime observation store and stay ``untrusted_until_confirmed``.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import structlog

from songyan.db.plan_fact_repo import PlanFactRepository
from songyan.db.settlement_repo import UNTRUSTED_UNTIL_CONFIRMED
from songyan.models.plan_facts import PlanAttribute, PlanEntity
from songyan.models.settlement import StateSettlement

from ._setting_quality import _normalize_setting_key

if TYPE_CHECKING:
    import aiosqlite

logger = structlog.get_logger(__name__)

_SLUG_RE = re.compile(r"[^a-zA-Z0-9_-]+")


def _slug(raw: str, *, max_len: int = 48) -> str:
    cleaned = _SLUG_RE.sub("-", raw.strip()).strip("-")
    if not cleaned:
        cleaned = "x"
    return cleaned[:max_len]


def _attribute_id(
    *, project_id: str, entity_id: str, key: str, chapter_number: int
) -> str:
    return (
        f"ext-{_slug(project_id, max_len=24)}"
        f"-{_slug(entity_id)}-{_slug(key)}-c{chapter_number}"
    )


def _setting_entity_id(project_id: str, setting_key: str) -> str:
    return f"ext-set-{_slug(project_id, max_len=24)}-{_slug(setting_key)}"


async def enqueue_extract_proposals(
    settlement: StateSettlement,
    *,
    project_id: str,
    chapter_number: int,
    conn: aiosqlite.Connection,
    character_names: dict[str, str] | None = None,
    plan_repo: PlanFactRepository | None = None,
) -> list[str]:
    """Map settlement observations into pending plan attributes (source=extract).

    Idempotent per (project, entity, key, chapter). Skips rows already
    ``approved`` so confirm is not silently demoted. Settlement DB writes
    elsewhere stay observational (``untrusted_until_confirmed``).
    """
    repo = plan_repo or PlanFactRepository()
    names = character_names or {}
    written: list[str] = []

    for update in settlement.character_updates:
        entity_id = update.character_id
        await _ensure_pending_entity(
            repo,
            conn=conn,
            project_id=project_id,
            entity_id=entity_id,
            entity_type="character",
            aliases=[names[entity_id]] if entity_id in names else [],
        )
        attr_id = await _write_pending_extract_attribute(
            repo,
            conn=conn,
            project_id=project_id,
            entity_id=entity_id,
            key=update.field,
            value=update.new_value,
            chapter_number=chapter_number,
        )
        if attr_id is not None:
            written.append(attr_id)

    for setting in settlement.new_settings:
        raw_key = (setting.setting_key or "").strip()
        key = _normalize_setting_key(raw_key, setting.setting_name or raw_key)
        if key is None:
            continue
        entity_id = _setting_entity_id(project_id, key)
        aliases = [setting.setting_name] if setting.setting_name else [key]
        await _ensure_pending_entity(
            repo,
            conn=conn,
            project_id=project_id,
            entity_id=entity_id,
            entity_type="setting",
            aliases=aliases,
        )
        attr_id = await _write_pending_extract_attribute(
            repo,
            conn=conn,
            project_id=project_id,
            entity_id=entity_id,
            key="description",
            value=setting.description,
            chapter_number=chapter_number,
        )
        if attr_id is not None:
            written.append(attr_id)

    for num in settlement.numerical_updates:
        entity_id = num.character_id
        await _ensure_pending_entity(
            repo,
            conn=conn,
            project_id=project_id,
            entity_id=entity_id,
            entity_type="character",
            aliases=[names[entity_id]] if entity_id in names else [],
        )
        attr_id = await _write_pending_extract_attribute(
            repo,
            conn=conn,
            project_id=project_id,
            entity_id=entity_id,
            key=num.attribute_name,
            value=str(num.closing_value),
            chapter_number=chapter_number,
        )
        if attr_id is not None:
            written.append(attr_id)

    if written:
        logger.info(
            "settlement.extract_proposals_enqueued",
            project_id=project_id,
            chapter_number=chapter_number,
            count=len(written),
            attribute_ids=written,
            trust=UNTRUSTED_UNTIL_CONFIRMED,
        )
    return written


async def _ensure_pending_entity(
    repo: PlanFactRepository,
    *,
    conn: aiosqlite.Connection,
    project_id: str,
    entity_id: str,
    entity_type: str,
    aliases: list[str],
) -> None:
    existing = await repo.read_entity(entity_id)
    if existing is not None:
        return
    await repo.write_entity(
        PlanEntity(
            entity_id=entity_id,
            project_id=project_id,
            entity_type=entity_type,
            aliases=aliases,
            approval_status="pending",
        ),
        conn=conn,
    )


async def _write_pending_extract_attribute(
    repo: PlanFactRepository,
    *,
    conn: aiosqlite.Connection,
    project_id: str,
    entity_id: str,
    key: str,
    value: str,
    chapter_number: int,
) -> str | None:
    attribute_id = _attribute_id(
        project_id=project_id,
        entity_id=entity_id,
        key=key,
        chapter_number=chapter_number,
    )
    existing = await repo.read_attribute(attribute_id)
    if existing is not None and existing.approval_status in ("approved", "rejected"):
        # approved：confirm 不可被静默降级；rejected：人 dismissed 的提案不被
        # settlement 复活（task 226 切片 5，owner 拍板）。
        logger.info(
            "settlement.extract_proposal_skip_final",
            attribute_id=attribute_id,
            approval_status=existing.approval_status,
            project_id=project_id,
        )
        return None
    await repo.write_attribute(
        PlanAttribute(
            attribute_id=attribute_id,
            project_id=project_id,
            entity_id=entity_id,
            key=key,
            value=value,
            valid_from_ch=chapter_number,
            valid_to_ch=None,
            source="extract",
            approval_status="pending",
        ),
        conn=conn,
    )
    return attribute_id
