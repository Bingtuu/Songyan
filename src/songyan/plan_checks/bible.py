"""Thin wrapper: approved plan cards are the chapter bible.

The writing and revision prompts read that bible. Body extracts are not
inserted into plan canon, and a pending row is not promoted here. A human
approves a card by writing it; this module only reads ``approved`` rows.
"""

from __future__ import annotations

import aiosqlite
import structlog
from pydantic import BaseModel, Field

from songyan.db.plan_fact_repo import PlanFactRepository
from songyan.models.plan_facts import (
    PlanAttribute,
    PlanClue,
    PlanEntity,
    PlanEvent,
    PlanTimeAnchor,
)

logger = structlog.get_logger(__name__)

BIBLE_HEADING = "本章事实圣经（已批准计划卡）"


class ChapterPlanBible(BaseModel):
    """Approved cards that apply to one chapter, plus the prompt text."""

    project_id: str
    chapter: int
    text: str = ""
    entity_ids: list[str] = Field(default_factory=list)
    attribute_ids: list[str] = Field(default_factory=list)
    event_ids: list[str] = Field(default_factory=list)
    clue_ids: list[str] = Field(default_factory=list)
    time_anchor_ids: list[str] = Field(default_factory=list)


def wrap_writing_prompt(prompt: str, bible_text: str) -> str:
    """Put the approved bible ahead of an existing writing or revision prompt.

    An empty bible leaves the prompt unchanged, so projects without plan
    cards keep the previous writer text.
    """
    text = bible_text.strip()
    if not text:
        return prompt
    block = (
        f"## {BIBLE_HEADING}\n"
        "这些是人维护的已批准计划卡，是本章权威事实。写作和修订必须遵守。\n"
        "正文里新出现、卡上没有的事实不是已成立事实，不能写进事实圣经。\n"
        f"{text}"
    )
    return f"{block}\n\n{prompt}"


def plan_fact_gate_failure_lines(report: object) -> list[str]:
    """Human-readable lines for a failed plan-fact gate.

    A passed report, a missing report, and a supported claim produce no
    lines. This does not decide review routing.
    """
    data = _report_dict(report)
    if data is None or data.get("passed") is True:
        return []
    lines: list[str] = []
    for row in _rows(data.get("missing_mentions")):
        terms = "、".join(str(term) for term in row.get("missing_terms") or [])
        label = str(row.get("label") or "").strip()
        point_id = str(row.get("point_id") or "").strip()
        head = " ".join(part for part in (point_id, label) if part)
        lines.append(f"必须提及未出现：{head} 缺 {terms}".strip())
    for row in _rows(data.get("claim_verdicts")):
        status = row.get("status")
        if status == "contradicted":
            kind = "主张矛盾"
        elif status == "unmentioned":
            kind = "主张未提及"
        else:
            continue
        lines.append(f"{kind}：{row.get('claim_id')} {row.get('text')}".strip())
    for row in _rows(data.get("attribute_mismatches")):
        lines.append(
            "属性不符："
            f"{row.get('entity_id')}.{row.get('key')} "
            f"圣经「{row.get('approved_value')}」正文「{row.get('extract_value')}」"
        )
    return lines


async def load_chapter_plan_bible(project_id: str, chapter: int) -> ChapterPlanBible:
    """Read the approved bible for one chapter.

    Pending rows, other projects, other chapters, and attributes outside
    the chapter window are not included. A missing database file yields an
    empty bible and is not created here.
    """
    if not isinstance(project_id, str) or not project_id.strip():
        raise ValueError("project_id must be non-empty")
    if not isinstance(chapter, int) or isinstance(chapter, bool) or chapter < 1:
        raise ValueError("chapter must be >= 1")
    empty = ChapterPlanBible(project_id=project_id, chapter=chapter)
    if not _database_file_exists():
        return empty
    repo = PlanFactRepository()
    try:
        entities = await repo.list_canon_entities(project_id)
        attributes = await repo.list_canon_attributes(project_id)
        events = await repo.list_canon_events(project_id)
        clues = await repo.list_canon_clues(project_id)
        anchors = await repo.list_canon_time_anchors(project_id)
    except aiosqlite.OperationalError as exc:
        if "no such table" in str(exc):
            logger.warning(
                "plan_bible.tables_missing",
                project_id=project_id,
                chapter=chapter,
            )
            return empty
        raise
    return _select_bible(
        project_id=project_id,
        chapter=chapter,
        entities=entities,
        attributes=attributes,
        events=events,
        clues=clues,
        time_anchors=anchors,
    )


def _select_bible(
    *,
    project_id: str,
    chapter: int,
    entities: list[PlanEntity],
    attributes: list[PlanAttribute],
    events: list[PlanEvent],
    clues: list[PlanClue],
    time_anchors: list[PlanTimeAnchor],
) -> ChapterPlanBible:
    chapter_events = sorted(
        (row for row in events if row.ch == chapter),
        key=lambda row: row.event_id,
    )
    chapter_clues = sorted(
        (row for row in clues if chapter in row.must_mention_in),
        key=lambda row: row.clue_id,
    )
    referenced: list[str] = []
    for event in chapter_events:
        for bucket in (event.participants, event.causes, event.reveals_evidence):
            for entity_id in bucket:
                if entity_id not in referenced:
                    referenced.append(entity_id)
    entity_by_id = {row.entity_id: row for row in entities}
    chosen_entities = sorted(
        (entity_by_id[entity_id] for entity_id in referenced if entity_id in entity_by_id),
        key=lambda row: row.entity_id,
    )
    referenced_ids = {row.entity_id for row in chosen_entities}
    chosen_attributes = sorted(
        (
            row
            for row in attributes
            if row.entity_id in referenced_ids and _in_window(row, chapter)
        ),
        key=lambda row: row.attribute_id,
    )
    anchor_ids: list[str] = []
    for event in chapter_events:
        if event.time_anchor_id and event.time_anchor_id not in anchor_ids:
            anchor_ids.append(event.time_anchor_id)
    anchor_by_id = {row.anchor_id: row for row in time_anchors}
    chosen_anchors = sorted(
        (anchor_by_id[anchor_id] for anchor_id in anchor_ids if anchor_id in anchor_by_id),
        key=lambda row: row.anchor_id,
    )
    text = _render(
        entities=chosen_entities,
        attributes=chosen_attributes,
        anchors=chosen_anchors,
        events=chapter_events,
        clues=chapter_clues,
    )
    return ChapterPlanBible(
        project_id=project_id,
        chapter=chapter,
        text=text,
        entity_ids=[row.entity_id for row in chosen_entities],
        attribute_ids=[row.attribute_id for row in chosen_attributes],
        event_ids=[row.event_id for row in chapter_events],
        clue_ids=[row.clue_id for row in chapter_clues],
        time_anchor_ids=[row.anchor_id for row in chosen_anchors],
    )


def _render(
    *,
    entities: list[PlanEntity],
    attributes: list[PlanAttribute],
    anchors: list[PlanTimeAnchor],
    events: list[PlanEvent],
    clues: list[PlanClue],
) -> str:
    if not events and not clues:
        return ""
    lines: list[str] = []
    for row in entities:
        aliases = "、".join(alias for alias in row.aliases if alias.strip())
        suffix = f"：{aliases}" if aliases else ""
        lines.append(f"实体 {row.entity_id}（{row.entity_type}）{suffix}")
    for row in attributes:
        lines.append(
            f"属性 {row.attribute_id}：{row.entity_id}.{row.key} = {row.value}"
            f"（{_window_label(row)}，来源 {row.source}）"
        )
    for row in anchors:
        lines.append(f"时间锚 {row.anchor_id}：{row.date}（{row.kind}）")
    for row in events:
        anchor = f"，时间锚 {row.time_anchor_id}" if row.time_anchor_id else ""
        participants = "、".join(row.participants) or "（无）"
        lines.append(f"事件 {row.event_id}（第{row.ch}章{anchor}）：参与 {participants}")
        for claim in row.claims:
            lines.append(f"主张 {claim.claim_id}：{claim.text}")
    for row in clues:
        terms = row.mention_terms or ([row.label] if row.label.strip() else [])
        shown = "、".join(terms)
        label = row.label.strip() or row.clue_id
        lines.append(f"线索 {row.clue_id}：{label}。本章必须出现：{shown}")
    return "\n".join(lines)


def _window_label(row: PlanAttribute) -> str:
    if row.valid_from_ch is None and row.valid_to_ch is None:
        return "不限章节"
    if row.valid_from_ch is not None and row.valid_to_ch is not None:
        return f"第{row.valid_from_ch}–{row.valid_to_ch}章"
    if row.valid_from_ch is not None:
        return f"第{row.valid_from_ch}章起"
    return f"至第{row.valid_to_ch}章"


def _in_window(row: PlanAttribute, chapter: int) -> bool:
    if row.valid_from_ch is not None and chapter < row.valid_from_ch:
        return False
    if row.valid_to_ch is not None and chapter > row.valid_to_ch:
        return False
    return True


def _database_file_exists() -> bool:
    from songyan.db.connection import get_db_path

    try:
        path = get_db_path()
    except ValueError:
        return False
    return path.is_file()


def _report_dict(report: object) -> dict[str, object] | None:
    if isinstance(report, dict):
        return report
    dump = getattr(report, "model_dump", None)
    if not callable(dump):
        return None
    data = dump()
    if isinstance(data, dict):
        return data
    return None


def _rows(raw: object) -> list[dict[str, object]]:
    if not isinstance(raw, list):
        return []
    return [row for row in raw if isinstance(row, dict)]
