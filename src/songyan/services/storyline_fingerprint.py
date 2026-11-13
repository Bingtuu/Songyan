"""task 252：故事线切片指纹（tech-m4-followup-s5 §3.2）。

与 parent_canon_fingerprint 完全独立：Canon 语义不被故事线污染
（PRD「故事线不是 Canon 的别名」红线），故事线演进单独驱动
``stale_vs_storyline``。

切片 = 全书 story_outlines 行 + 覆盖本章的 arcs + 相关 threads（三条件并集）。
字段白名单见 docs/tech-m4-followup-s5.md §3.2；时间戳/审计字段不进指纹。
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from songyan.models.narrative import ArcPlan, PlotThread, StoryOutline


def _outline_dict(row: StoryOutline) -> dict[str, Any]:
    return {
        "core_conflict": row.core_conflict,
        "intended_ending": row.intended_ending,
        "mainline_synopsis": row.mainline_synopsis,
        "project_id": row.project_id,
        "themes": sorted(row.themes),
    }


def _arc_dict(row: ArcPlan) -> dict[str, Any]:
    return {
        "arc_id": row.arc_id,
        "arc_goal": row.arc_goal,
        "end_chapter": row.end_chapter,
        "is_mainline": row.is_mainline,
        "start_chapter": row.start_chapter,
        "threads_to_open": sorted(row.threads_to_open),
        "threads_to_resolve": sorted(row.threads_to_resolve),
    }


def _thread_dict(row: PlotThread) -> dict[str, Any]:
    return {
        "description": row.description,
        "expected_resolve_arc": row.expected_resolve_arc,
        "is_mainline": row.is_mainline,
        "opened_chapter": row.opened_chapter,
        "status": row.status,
        "thread_id": row.thread_id,
        "title": row.title,
    }


def storyline_fingerprint_from_parts(
    *,
    outline: StoryOutline | None,
    arcs: list[ArcPlan],
    threads: list[PlotThread],
) -> str:
    """sha256 canonical JSON；输入顺序不影响摘要。"""
    payload = {
        "arcs": [_arc_dict(a) for a in sorted(arcs, key=lambda r: r.arc_id)],
        "outline": None if outline is None else _outline_dict(outline),
        "threads": [_thread_dict(t) for t in sorted(threads, key=lambda r: r.thread_id)],
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


async def load_storyline_slice(
    project_id: str, chapter: int
) -> tuple[StoryOutline | None, list[ArcPlan], list[PlotThread]]:
    """读本章相关切片：全书 outline + 覆盖本章的弧 + 相关线索（三条件并集）。"""
    from songyan.db.narrative_repo import NarrativeRepository

    repo = NarrativeRepository()
    outline = await repo.get_outline(project_id)
    arcs = [
        arc
        for arc in await repo.list_arc_plans(project_id)
        if arc.start_chapter <= chapter <= arc.end_chapter
    ]
    arc_indexes = {arc.arc_index for arc in arcs}

    referenced: set[str] = set()
    for arc in arcs:
        referenced.update(arc.threads_to_open)
        referenced.update(arc.threads_to_resolve)

    threads: list[PlotThread] = []
    for thread in await repo.list_threads(project_id):
        if thread.thread_id in referenced:
            threads.append(thread)
        elif thread.opened_chapter is not None and thread.opened_chapter <= chapter:
            threads.append(thread)
        elif (
            thread.expected_resolve_arc is not None
            and thread.expected_resolve_arc in arc_indexes
        ):
            threads.append(thread)
    return outline, arcs, threads


async def storyline_fingerprint(project_id: str, chapter: int) -> str:
    """load + hash 一体入口。"""
    outline, arcs, threads = await load_storyline_slice(project_id, chapter)
    return storyline_fingerprint_from_parts(
        outline=outline, arcs=arcs, threads=threads
    )
