"""Text cleanliness metrics and T9 support (V7 Task 164)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from songyan.agents.rule_auditor import (
    detect_duplicate_paragraphs,
    detect_markdown_scene_titles,
    detect_meta_tag_leaks,
)
from songyan.db.repository import ChapterHeadRepository, ChapterVersionRepository
from songyan.db.text_cleanliness_repo import (
    TextCleanlinessMetricRepository,
    TextCleanlinessMetricRow,
)
from songyan.evals.timeline_consistency import (
    TimelineConflict,
    detect_timeline_conflicts,
    extract_time_signals,
)


def _model_dump_list(items: list[Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in items:
        if hasattr(item, "model_dump"):
            result.append(item.model_dump(mode="json"))
        elif isinstance(item, dict):
            result.append(item)
    return result


def _timeline_conflicts_by_current_chapter(
    conflicts: list[TimelineConflict],
) -> dict[int, list[TimelineConflict]]:
    grouped: dict[int, list[TimelineConflict]] = defaultdict(list)
    for conflict in conflicts:
        grouped[conflict.current_chapter].append(conflict)
    return grouped


async def collect_text_cleanliness_metrics(
    project_id: str,
    start: int,
    end: int,
    *,
    persist: bool = True,
    head_repo: ChapterHeadRepository | None = None,
    version_repo: ChapterVersionRepository | None = None,
    metric_repo: TextCleanlinessMetricRepository | None = None,
) -> list[TextCleanlinessMetricRow]:
    """Derive text cleanliness metrics from accepted chapter text.

    When ``persist=True`` the derived metrics are upserted into
    ``text_cleanliness_metrics`` and then returned.
    """
    head_repo = head_repo or ChapterHeadRepository()
    version_repo = version_repo or ChapterVersionRepository()
    metric_repo = metric_repo or TextCleanlinessMetricRepository()

    heads = await head_repo.list_by_project(project_id)
    accepted: dict[int, tuple[str, str]] = {}
    for head in heads:
        if not (start <= head.chapter_number <= end):
            continue
        if head.status != "accepted" or not head.accepted_version_id:
            continue
        version = await version_repo.get(head.accepted_version_id)
        if version is None:
            continue
        accepted[head.chapter_number] = (version.version_id, version.content)

    signals_by_chapter = {
        chapter: extract_time_signals(chapter, content)
        for chapter, (_, content) in accepted.items()
    }
    timeline_conflicts = detect_timeline_conflicts(signals_by_chapter)
    conflicts_by_chapter = _timeline_conflicts_by_current_chapter(timeline_conflicts)

    rows: list[TextCleanlinessMetricRow] = []
    for chapter in sorted(accepted):
        version_id, content = accepted[chapter]
        meta_matches = detect_meta_tag_leaks(content)
        scene_title_matches = detect_markdown_scene_titles(content)
        duplicate_matches = detect_duplicate_paragraphs(content)
        chapter_conflicts = conflicts_by_chapter.get(chapter, [])
        row = TextCleanlinessMetricRow(
            project_id=project_id,
            chapter_number=chapter,
            version_id=version_id,
            meta_tag_leak_count=len(meta_matches) + len(scene_title_matches),
            duplicate_paragraph_count=len(duplicate_matches),
            timeline_conflict_count=len(chapter_conflicts),
            details={
                "meta_tag_matches": _model_dump_list(meta_matches),
                "markdown_scene_title_matches": _model_dump_list(scene_title_matches),
                "duplicate_paragraph_matches": _model_dump_list(duplicate_matches),
                "timeline_conflicts": _model_dump_list(chapter_conflicts),
            },
        )
        if persist:
            await metric_repo.upsert(row)
        rows.append(row)

    return rows


async def load_text_cleanliness_metrics(
    project_id: str,
    start: int,
    end: int,
    *,
    repo: TextCleanlinessMetricRepository | None = None,
) -> list[TextCleanlinessMetricRow]:
    """Read persisted text cleanliness metrics."""
    repo = repo or TextCleanlinessMetricRepository()
    return await repo.list_by_project(project_id, start, end)


async def refresh_text_cleanliness_metrics(
    project_id: str,
    start: int,
    end: int,
) -> list[TextCleanlinessMetricRow]:
    """Derive and persist text cleanliness metrics for a chapter range."""
    return await collect_text_cleanliness_metrics(project_id, start, end, persist=True)


def render_text_cleanliness_section(rows: list[TextCleanlinessMetricRow]) -> str:
    """Render text cleanliness metric section."""
    lines = ["## 文本洁净度（T9 harness 数据源）", ""]
    if not rows:
        lines.append("（无 text_cleanliness_metrics 数据；请先刷新或确认存在 accepted 正文）")
        return "\n".join(lines)

    total_meta = sum(row.meta_tag_leak_count for row in rows)
    total_dup = sum(row.duplicate_paragraph_count for row in rows)
    total_timeline = sum(row.timeline_conflict_count for row in rows)
    meta_chapters = [row.chapter_number for row in rows if row.meta_tag_leak_count > 0]
    dup_chapters = [row.chapter_number for row in rows if row.duplicate_paragraph_count > 0]
    timeline_chapters = [row.chapter_number for row in rows if row.timeline_conflict_count > 0]

    lines.append(
        f"- 汇总：元标记 **{total_meta}**，重复长段落 **{total_dup}**，"
        f"时间线矛盾 **{total_timeline}**。"
    )
    lines.append("")
    lines.append("| 章 | version | 元标记 | 重复长段落 | 时间线矛盾 |")
    lines.append("|----|---------|--------|------------|------------|")
    for row in rows:
        lines.append(
            f"| {row.chapter_number} | {row.version_id} | "
            f"{row.meta_tag_leak_count} | {row.duplicate_paragraph_count} "
            f"| {row.timeline_conflict_count} |"
        )

    lines.append("")
    lines.append(f"- 元标记违规章：{meta_chapters or '无'}")
    lines.append(f"- 重复长段落违规章：{dup_chapters or '无'}")
    lines.append(f"- 时间线矛盾诊断章：{timeline_chapters or '无'}")
    return "\n".join(lines)
