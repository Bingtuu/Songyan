"""Outline import (Task 142) — 解析全书大纲 JSON，构建叙事骨架对象.

MVP 只做"能录入、能存、能读回"：解析 + 结构/引用校验，不做智能生成或
与已生成章节的一致性校验。写入由 ``NarrativeRepository.import_outline`` 原子完成。
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from songyan.exceptions import SongyanError
from songyan.models import ArcPlan, PlotThread, StoryOutline


class OutlineImportError(SongyanError):
    """大纲导入文件格式错误 / 校验失败."""


def load_outline_file(
    path: str, project_id: str
) -> tuple[StoryOutline, list[ArcPlan], list[PlotThread]]:
    """解析大纲 JSON 文件，返回 (StoryOutline, arc_plans, plot_threads).

    校验：JSON 合法、顶层为对象、``arc_plans``/``plot_threads`` 为数组、
    ``thread_id`` 存在且唯一、``arc_plans`` 引用的 thread_id 不悬空、
    必填字段（arc_index/start_chapter/end_chapter）齐全。

    Raises:
        OutlineImportError: 任一校验失败。
    """
    p = Path(path)
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        msg = f"大纲文件不存在: {path}"
        raise OutlineImportError(msg) from exc
    except json.JSONDecodeError as exc:
        msg = f"大纲文件不是合法 JSON: {exc}"
        raise OutlineImportError(msg) from exc

    if not isinstance(raw, dict):
        msg = "大纲文件顶层必须是 JSON 对象"
        raise OutlineImportError(msg)

    outline_data = raw.get("outline", {})
    if not isinstance(outline_data, dict):
        msg = "`outline` 字段必须是对象"
        raise OutlineImportError(msg)

    arc_data = raw.get("arc_plans", [])
    thread_data = raw.get("plot_threads", [])
    if not isinstance(arc_data, list) or not isinstance(thread_data, list):
        msg = "`arc_plans` 与 `plot_threads` 必须是数组"
        raise OutlineImportError(msg)

    try:
        outline = StoryOutline(
            project_id=project_id,
            **{k: v for k, v in outline_data.items() if k != "project_id"},
        )
        threads, thread_ids = _build_threads(thread_data, project_id)
        arcs = _build_arcs(arc_data, project_id)
    except ValidationError as exc:
        msg = f"大纲字段校验失败: {exc}"
        raise OutlineImportError(msg) from exc

    _check_thread_refs(arcs, thread_ids)
    return outline, arcs, threads


def _build_threads(
    thread_data: list[object], project_id: str
) -> tuple[list[PlotThread], set[str]]:
    threads: list[PlotThread] = []
    thread_ids: set[str] = set()
    for item in thread_data:
        if not isinstance(item, dict):
            msg = "plot_threads 每项必须是对象"
            raise OutlineImportError(msg)
        tid = item.get("thread_id")
        if not tid:
            msg = "plot_threads 缺少 thread_id"
            raise OutlineImportError(msg)
        if tid in thread_ids:
            msg = f"plot_threads thread_id 重复: {tid}"
            raise OutlineImportError(msg)
        thread_ids.add(tid)
        threads.append(
            PlotThread(
                project_id=project_id,
                **{k: v for k, v in item.items() if k != "project_id"},
            )
        )
    return threads, thread_ids


def _build_arcs(arc_data: list[object], project_id: str) -> list[ArcPlan]:
    arcs: list[ArcPlan] = []
    for idx, item in enumerate(arc_data):
        if not isinstance(item, dict):
            msg = "arc_plans 每项必须是对象"
            raise OutlineImportError(msg)
        rest = {k: v for k, v in item.items() if k not in ("project_id", "arc_id")}
        arc_id = item.get("arc_id") or f"{project_id}-arc{item.get('arc_index', idx)}"
        arcs.append(ArcPlan(arc_id=arc_id, project_id=project_id, **rest))
    return arcs


def _check_thread_refs(arcs: list[ArcPlan], thread_ids: set[str]) -> None:
    for arc in arcs:
        for tid in [*arc.threads_to_open, *arc.threads_to_resolve]:
            if tid not in thread_ids:
                msg = (
                    f"arc(arc_index={arc.arc_index}) 引用了不存在的 thread_id: {tid}"
                )
                raise OutlineImportError(msg)
