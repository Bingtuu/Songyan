"""Read-only workbench commands.

M0 step 1 prints approved and pending plan facts. It does not write, and it
does not read the storyline tables.
"""

from __future__ import annotations

import asyncio

import click

from songyan.db.plan_fact_repo import PlanFactRepository

_CANON_HEAD = "# Canon（approved）"
_PENDING_HEAD = "# Pending（不是 Canon）"
_STORYLINE_HEAD = "# Storyline（规划骨架，不是已确认事实）"
_KINDS = ("entity", "attribute", "event", "time_anchor", "clue")


def _kind_block(kind: str, card_ids: list[str], *, pending: bool) -> list[str]:
    if not card_ids:
        body = ["（空）"]
    else:
        suffix = " approval_status=pending" if pending else ""
        body = [f"- {card_id}{suffix}" for card_id in card_ids]
    return [f"## {kind}", *body]


async def _render_canon_show(project_id: str) -> str:
    repo = PlanFactRepository()
    canon = {
        "entity": [row.entity_id for row in await repo.list_canon_entities(project_id)],
        "attribute": [row.attribute_id for row in await repo.list_canon_attributes(project_id)],
        "event": [row.event_id for row in await repo.list_canon_events(project_id)],
        "time_anchor": [row.anchor_id for row in await repo.list_canon_time_anchors(project_id)],
        "clue": [row.clue_id for row in await repo.list_canon_clues(project_id)],
    }
    pending = {
        "entity": [row.entity_id for row in await repo.list_pending_entities(project_id)],
        "attribute": [row.attribute_id for row in await repo.list_pending_attributes(project_id)],
        "event": [row.event_id for row in await repo.list_pending_events(project_id)],
        "time_anchor": [row.anchor_id for row in await repo.list_pending_time_anchors(project_id)],
        "clue": [row.clue_id for row in await repo.list_pending_clues(project_id)],
    }
    lines = [_CANON_HEAD]
    for kind in _KINDS:
        lines.extend(_kind_block(kind, canon[kind], pending=False))
    lines.append(_PENDING_HEAD)
    for kind in _KINDS:
        lines.extend(_kind_block(kind, pending[kind], pending=True))
    lines.append(_STORYLINE_HEAD)
    lines.append("（空）")
    return "\n".join(lines)


@click.group(name="canon")
def canon_group() -> None:
    """已确认事实与未确认行。只读。"""


@canon_group.command(name="show")
@click.option("--project-id", required=True, help="项目 ID")
def canon_show(project_id: str) -> None:
    """打印五类计划事实的 Canon 与 Pending。不写库。"""
    click.echo(asyncio.run(_render_canon_show(project_id)))


def register_workbench_commands(cli: click.Group) -> None:
    """Register the read-only workbench commands for this milestone."""
    cli.add_command(canon_group)
