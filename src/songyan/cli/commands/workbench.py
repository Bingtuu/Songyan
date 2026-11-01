"""Read-only workbench commands.

M0 step 1 prints approved and pending plan facts. Step 2 fills the storyline
section from ``NarrativeRepository`` and adds ``--json``. Neither step writes.
"""

from __future__ import annotations

import asyncio
import json

import click

from songyan.db.narrative_repo import NarrativeRepository
from songyan.db.plan_fact_repo import PlanFactRepository
from songyan.models.narrative import ArcPlan, PlotThread, StoryOutline
from songyan.models.plan_facts import (
    PlanAttribute,
    PlanClue,
    PlanEntity,
    PlanEvent,
    PlanTimeAnchor,
)

_CANON_HEAD = "# Canon（approved）"
_PENDING_HEAD = "# Pending（不是 Canon）"
_STORYLINE_HEAD = "# Storyline（规划骨架，不是已确认事实）"
_KINDS = ("entity", "attribute", "event", "time_anchor", "clue")

_Card = PlanEntity | PlanAttribute | PlanEvent | PlanTimeAnchor | PlanClue


def _card_id(kind: str, row: _Card) -> str:
    if kind == "entity":
        assert isinstance(row, PlanEntity)
        return row.entity_id
    if kind == "attribute":
        assert isinstance(row, PlanAttribute)
        return row.attribute_id
    if kind == "event":
        assert isinstance(row, PlanEvent)
        return row.event_id
    if kind == "time_anchor":
        assert isinstance(row, PlanTimeAnchor)
        return row.anchor_id
    assert isinstance(row, PlanClue)
    return row.clue_id


def _kind_block(kind: str, rows: list[_Card], *, pending: bool) -> list[str]:
    if not rows:
        body = ["（空）"]
    else:
        suffix = " approval_status=pending" if pending else ""
        body = [f"- {_card_id(kind, row)}{suffix}" for row in rows]
    return [f"## {kind}", *body]


def _storyline_text(
    outline: StoryOutline | None,
    arcs: list[ArcPlan],
    thread_counts: dict[str, int],
) -> str:
    if outline is None and not arcs and not thread_counts:
        return "（空）"
    lines: list[str] = []
    if outline is not None:
        lines.append(outline.core_conflict)
    lines.append(f"arcs: {len(arcs)}")
    for status, count in sorted(thread_counts.items()):
        lines.append(f"{status}={count}")
    return "\n".join(lines)


def _dump(rows: list[_Card] | list[ArcPlan] | list[PlotThread]) -> list[dict[str, object]]:
    return [row.model_dump(mode="json") for row in rows]


async def _load(project_id: str) -> dict[str, object]:
    facts = PlanFactRepository()
    narrative = NarrativeRepository()
    canon = {
        "entity": await facts.list_canon_entities(project_id),
        "attribute": await facts.list_canon_attributes(project_id),
        "event": await facts.list_canon_events(project_id),
        "time_anchor": await facts.list_canon_time_anchors(project_id),
        "clue": await facts.list_canon_clues(project_id),
    }
    pending = {
        "entity": await facts.list_pending_entities(project_id),
        "attribute": await facts.list_pending_attributes(project_id),
        "event": await facts.list_pending_events(project_id),
        "time_anchor": await facts.list_pending_time_anchors(project_id),
        "clue": await facts.list_pending_clues(project_id),
    }
    outline = await narrative.get_outline(project_id)
    arcs = await narrative.list_arc_plans(project_id)
    threads = await narrative.list_threads(project_id)
    thread_counts = await narrative.count_threads_by_status(project_id)
    return {
        "canon": canon,
        "pending": pending,
        "outline": outline,
        "arcs": arcs,
        "threads": threads,
        "thread_counts": thread_counts,
    }


def _render_text(loaded: dict[str, object]) -> str:
    canon = loaded["canon"]
    pending = loaded["pending"]
    assert isinstance(canon, dict)
    assert isinstance(pending, dict)
    lines = [_CANON_HEAD]
    for kind in _KINDS:
        lines.extend(_kind_block(kind, canon[kind], pending=False))
    lines.append(_PENDING_HEAD)
    for kind in _KINDS:
        lines.extend(_kind_block(kind, pending[kind], pending=True))
    lines.append(_STORYLINE_HEAD)
    outline = loaded["outline"]
    arcs = loaded["arcs"]
    thread_counts = loaded["thread_counts"]
    assert outline is None or isinstance(outline, StoryOutline)
    assert isinstance(arcs, list)
    assert isinstance(thread_counts, dict)
    lines.append(_storyline_text(outline, arcs, thread_counts))
    return "\n".join(lines)


def _render_json(project_id: str, loaded: dict[str, object]) -> str:
    canon = loaded["canon"]
    pending = loaded["pending"]
    outline = loaded["outline"]
    arcs = loaded["arcs"]
    threads = loaded["threads"]
    assert isinstance(canon, dict)
    assert isinstance(pending, dict)
    assert outline is None or isinstance(outline, StoryOutline)
    assert isinstance(arcs, list)
    assert isinstance(threads, list)
    payload = {
        "project_id": project_id,
        "canon": {
            "entities": _dump(canon["entity"]),
            "attributes": _dump(canon["attribute"]),
            "events": _dump(canon["event"]),
            "time_anchors": _dump(canon["time_anchor"]),
            "clues": _dump(canon["clue"]),
        },
        "pending": {
            "entities": _dump(pending["entity"]),
            "attributes": _dump(pending["attribute"]),
            "events": _dump(pending["event"]),
            "time_anchors": _dump(pending["time_anchor"]),
            "clues": _dump(pending["clue"]),
        },
        "storyline": {
            "outline": None if outline is None else outline.model_dump(mode="json"),
            "arcs": _dump(arcs),
            "threads": _dump(threads),
        },
    }
    return json.dumps(payload, ensure_ascii=False)


async def _render_canon_show(project_id: str, *, as_json: bool) -> str:
    loaded = await _load(project_id)
    if as_json:
        return _render_json(project_id, loaded)
    return _render_text(loaded)


@click.group(name="canon")
def canon_group() -> None:
    """已确认事实与未确认行。只读。"""


@canon_group.command(name="show")
@click.option("--project-id", required=True, help="项目 ID")
@click.option("--json", "as_json", is_flag=True, help="输出 JSON")
def canon_show(project_id: str, as_json: bool) -> None:
    """打印五类计划事实，以及故事线骨架。不写库。"""
    click.echo(asyncio.run(_render_canon_show(project_id, as_json=as_json)))


def register_workbench_commands(cli: click.Group) -> None:
    """Register the read-only workbench commands for this milestone."""
    cli.add_command(canon_group)
