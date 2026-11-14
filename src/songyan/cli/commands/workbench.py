"""Read-only workbench commands.

M0 steps 1–4: ``canon show`` and ``today`` for approved / pending facts,
storyline, and counts; missing DB / missing project exit 1.
M1 step 5 updates ``today`` fixed ``next`` (confirm available via canon confirm).
M1 write commands (``canon edit`` / confirm / dismiss) register beside this group.
M2 step 1: ``today`` promise counts + ``canon show --kind promise`` (read-only).
M2 step 6: ``today`` fixed ``next`` hints confirm/promise settle and hard confirm.
"""

from __future__ import annotations

import asyncio
import json

import click

from songyan.db.connection import get_db_path
from songyan.db.narrative_repo import NarrativeRepository
from songyan.db.plan_fact_repo import PlanFactRepository
from songyan.db.repository import ProjectRepository
from songyan.db.settlement_repo import ForeshadowingRepository
from songyan.models.chapter_progress import (
    STATE_PRIORITY,
    ChapterProgressSummary,
)
from songyan.models.context import ForeshadowingItem
from songyan.models.narrative import ArcPlan, PlotThread, StoryOutline
from songyan.models.plan_facts import (
    PlanAttribute,
    PlanClue,
    PlanEntity,
    PlanEvent,
    PlanTimeAnchor,
)
from songyan.services.chapter_progress import load_chapter_progress

_CANON_HEAD = "# 已确认事实（Canon / approved）"
_PENDING_HEAD = "# 待确认提案（pending，不是已确认事实）"
_STORYLINE_HEAD = "# 故事线（规划，不是已确认事实）"
_PROMISE_HEAD = "# 开放承诺（不是已确认事实）"
_NEXT = (
    "入典先 canon pending 过目提案，canon confirm 入典"
    "（batch --yes 可批量）；硬确认可用 --hard/--mark-stale；"
    "续写或开新章走 chapter continue（--chapter N 显式开章）；"
    "章内草稿可 variant generate 抽卡（默认 N=2，不自动选用）；"
    "生成后先 chapter accept 再 continue。"
)
_KINDS = ("entity", "attribute", "event", "time_anchor", "clue")
_OPEN_PROMISE_STATUSES = ("planted", "due", "overdue")

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


async def _ensure_project_readable(project_id: str) -> None:
    """Refuse before any get_db() call when the SQLite file is missing."""
    db_path = get_db_path()
    if not db_path.is_file():
        raise click.ClickException(f"找不到数据库文件: {db_path}")
    project = await ProjectRepository().get(project_id)
    if project is None:
        raise click.ClickException(f"项目不存在: {project_id}")


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



def _promise_counts(items: list[ForeshadowingItem]) -> dict[str, int]:
    counts = {status: 0 for status in _OPEN_PROMISE_STATUSES}
    for item in items:
        if item.status in counts:
            counts[item.status] += 1
    return counts


def _render_promise_text(items: list[ForeshadowingItem]) -> str:
    lines = [_PROMISE_HEAD]
    by_status: dict[str, list[ForeshadowingItem]] = {
        status: [] for status in _OPEN_PROMISE_STATUSES
    }
    for item in items:
        if item.status in by_status:
            by_status[item.status].append(item)
    for status in _OPEN_PROMISE_STATUSES:
        lines.append(f"## {status}")
        bucket = by_status[status]
        if not bucket:
            lines.append("（空）")
            continue
        for item in bucket:
            lines.append(
                f"- {item.foreshadowing_id} status={item.status} "
                f"planted_in_chapter={item.planted_in_chapter}"
            )
    return "\n".join(lines)


def _render_promise_json(project_id: str, items: list[ForeshadowingItem]) -> str:
    payload = {
        "project_id": project_id,
        "kind": "promise",
        "promises": [
            {
                "foreshadowing_id": item.foreshadowing_id,
                "description": item.description,
                "planted_in_chapter": item.planted_in_chapter,
                "expected_resolve_chapter": item.expected_resolve_chapter,
                "status": item.status,
                "source_version_id": item.source_version_id,
            }
            for item in items
        ],
    }
    return json.dumps(payload, ensure_ascii=False)


async def _load_open_promises(project_id: str) -> list[ForeshadowingItem]:
    """Open author-path set: active lifecycle + planted/due/overdue (B3)."""
    return await ForeshadowingRepository().list_schedulable(project_id)


async def _render_canon_show(
    project_id: str, *, as_json: bool, kind: str | None
) -> str:
    await _ensure_project_readable(project_id)
    if kind == "promise":
        items = await _load_open_promises(project_id)
        if as_json:
            return _render_promise_json(project_id, items)
        return _render_promise_text(items)
    loaded = await _load(project_id)
    if as_json:
        return _render_json(project_id, loaded)
    return _render_text(loaded)


@click.group(name="canon")
def canon_group() -> None:
    """已确认事实与未确认行；写入见 ``canon edit``。"""


@canon_group.command(name="pending")
@click.option("--project-id", required=True, help="项目 ID")
@click.option("--json", "as_json", is_flag=True, help="JSON 输出")
def canon_pending(project_id: str, as_json: bool) -> None:
    """列出 pending 提案（entity/attribute 分节；attribute 带 key=值预览）。task 259。"""
    import asyncio as _asyncio
    import json as _json

    from songyan.cli.commands.workbench import _ensure_project_readable as _ensure

    _asyncio.run(_ensure(project_id))
    entities, attributes = _asyncio.run(_load_pending(project_id))
    if as_json:
        click.echo(
            _json.dumps(
                {
                    "project_id": project_id,
                    "entities": [e.model_dump(mode="json") for e in entities],
                    "attributes": [a.model_dump(mode="json") for a in attributes],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return
    if not entities and not attributes:
        click.echo("无 pending 提案")
        return
    click.echo(f"entities ({len(entities)}):")
    for row in entities:
        click.echo(f"- {row.entity_id} type={row.entity_type} alias={row.aliases}")
    click.echo(f"attributes ({len(attributes)}):")
    for row in attributes:
        click.echo(f"- {row.attribute_id} {row.key}={row.value}")


async def _load_pending(project_id: str):
    """task 259：读 pending 提案（entity/attribute 两表）。"""
    from songyan.db.plan_fact_repo import PlanFactRepository

    repo = PlanFactRepository()
    entities = await repo.list_pending_entities(project_id)
    attributes = await repo.list_pending_attributes(project_id)
    return entities, attributes


@canon_group.command(name="show")
@click.option("--project-id", required=True, help="项目 ID")
@click.option(
    "--kind",
    type=click.Choice(["promise"], case_sensitive=False),
    default=None,
    help="只打印指定类；promise = 开放承诺（不是 Canon）",
)
@click.option("--json", "as_json", is_flag=True, help="输出 JSON")
def canon_show(project_id: str, kind: str | None, as_json: bool) -> None:
    """打印五类计划事实，以及故事线骨架；``--kind promise`` 只读开放承诺。不写库。"""
    click.echo(
        asyncio.run(_render_canon_show(project_id, as_json=as_json, kind=kind))
    )



def _count_rows(bucket: dict[str, list[_Card]]) -> int:
    return sum(len(bucket[kind]) for kind in _KINDS)


def _render_today_text(
    loaded: dict[str, object],
    promise_counts: dict[str, int],
    progress: ChapterProgressSummary,
) -> str:
    canon = loaded["canon"]
    pending = loaded["pending"]
    arcs = loaded["arcs"]
    assert isinstance(canon, dict)
    assert isinstance(pending, dict)
    assert isinstance(arcs, list)
    counts = " ".join(
        f"{state.value}={progress.distribution.get(state, 0)}" for state in STATE_PRIORITY
    )
    next_chapter = "-" if progress.next_chapter is None else str(progress.next_chapter)
    next_state = "-" if progress.next_state is None else progress.next_state.value
    return "\n".join(
        [
            f"canon_rows: {_count_rows(canon)}",
            f"pending_rows: {_count_rows(pending)}",
            f"storyline_arcs: {len(arcs)}",
            f"promise_planted: {promise_counts['planted']}",
            f"promise_due: {promise_counts['due']}",
            f"promise_overdue: {promise_counts['overdue']}",
            f"chapter_progress: next_chapter={next_chapter} "
            f"next_state={next_state} pending_confirm={progress.pending_confirm} {counts}",
            _NEXT,
        ]
    )


def _render_today_json(
    project_id: str,
    loaded: dict[str, object],
    promise_counts: dict[str, int],
    progress: ChapterProgressSummary,
) -> str:
    canon = loaded["canon"]
    pending = loaded["pending"]
    outline = loaded["outline"]
    arcs = loaded["arcs"]
    thread_counts = loaded["thread_counts"]
    assert isinstance(canon, dict)
    assert isinstance(pending, dict)
    assert outline is None or isinstance(outline, StoryOutline)
    assert isinstance(arcs, list)
    assert isinstance(thread_counts, dict)
    payload = {
        "project_id": project_id,
        "canon_counts": {kind: len(canon[kind]) for kind in _KINDS},
        "pending_counts": {kind: len(pending[kind]) for kind in _KINDS},
        "promise_counts": promise_counts,
        "storyline": {
            "has_outline": outline is not None,
            "arc_count": len(arcs),
            "thread_counts": thread_counts,
        },
        "chapter_progress": {
            "next_chapter": progress.next_chapter,
            "next_state": (
                None if progress.next_state is None else progress.next_state.value
            ),
            "pending_confirm": progress.pending_confirm,
            "counts": {
                state.value: progress.distribution.get(state, 0)
                for state in STATE_PRIORITY
            },
        },
        "next": _NEXT,
    }
    return json.dumps(payload, ensure_ascii=False)


async def _render_today(project_id: str, *, as_json: bool) -> str:
    await _ensure_project_readable(project_id)
    loaded = await _load(project_id)
    promises = await _load_open_promises(project_id)
    promise_counts = _promise_counts(promises)
    progress = await load_chapter_progress(project_id)
    if as_json:
        return _render_today_json(project_id, loaded, promise_counts, progress)
    return _render_today_text(loaded, promise_counts, progress)


@click.command(name="today")
@click.option("--project-id", required=True, help="项目 ID")
@click.option("--json", "as_json", is_flag=True, help="输出 JSON")
def today(project_id: str, as_json: bool) -> None:
    """打印计数与固定下一步说明。不写库，不生成。"""
    click.echo(asyncio.run(_render_today(project_id, as_json=as_json)))


def register_workbench_commands(cli: click.Group) -> None:
    """Register the read-only workbench commands for this milestone."""
    cli.add_command(canon_group)
    cli.add_command(today)
