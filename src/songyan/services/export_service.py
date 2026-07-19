"""Task 177: accepted manuscript export service."""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeAlias

import structlog

from songyan.db.layered_context_repo import ArcSummaryRepository, VolumeSummaryRepository
from songyan.db.repository import (
    ChapterHeadRepository,
    ChapterVersionRepository,
    ProjectRepository,
)
from songyan.exceptions import SongyanError
from songyan.models import ArcSummary, VolumeSummary

logger = structlog.get_logger(__name__)

ExportFormat: TypeAlias = Literal["md", "txt"]
GroupBy: TypeAlias = Literal["flat", "arc", "volume"]

_WINDOWS_ILLEGAL_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{idx}" for idx in range(1, 10)),
    *(f"LPT{idx}" for idx in range(1, 10)),
}


class ExportServiceError(SongyanError):
    """Export cannot be completed with the requested parameters or DB state."""


@dataclass(frozen=True)
class ChapterExport:
    """Accepted chapter payload used by the renderer."""

    chapter_number: int
    content: str
    word_count: int = 0
    version_id: str | None = None


@dataclass(frozen=True)
class ExportGroup:
    """Arc/volume grouping range for export rendering."""

    title: str
    start_chapter: int
    end_chapter: int


@dataclass(frozen=True)
class RenderedExportFile:
    """Rendered manuscript file content plus its chapter membership."""

    filename: str
    content: str
    chapters: tuple[int, ...]


@dataclass(frozen=True)
class ExportedFile:
    """File written by ``export_project``."""

    path: Path
    chapter_count: int


@dataclass(frozen=True)
class ExportResult:
    """Result returned by ``export_project``."""

    files: tuple[ExportedFile, ...]
    skipped_count: int = 0


@dataclass(frozen=True)
class _ChapterCollection:
    chapters: tuple[ChapterExport, ...]
    skipped_count: int = 0


def parse_chapter_range(value: str | None) -> tuple[int, int] | None:
    """Parse CLI chapter range syntax.

    Accepted forms are ``N`` and ``A-B``. The returned tuple is inclusive.
    """
    if value is None or not value.strip():
        return None

    raw = value.strip()
    if "-" in raw:
        start_s, end_s = raw.split("-", 1)
    else:
        start_s = end_s = raw

    if not start_s.isdigit() or not end_s.isdigit():
        msg = "章节范围必须是正整数或 a-b 格式"
        raise ExportServiceError(msg)

    start = int(start_s)
    end = int(end_s)
    if start < 1 or end < 1:
        msg = "章节范围必须从 1 或更大的正整数开始"
        raise ExportServiceError(msg)
    if start > end:
        msg = "章节范围起始章不能大于结束章"
        raise ExportServiceError(msg)
    return (start, end)


def sanitize_filename_component(value: str | None, *, fallback: str = "untitled") -> str:
    """Return a Windows-safe filename component."""
    raw = (value or "").strip()
    sanitized = _WINDOWS_ILLEGAL_RE.sub("_", raw)
    sanitized = re.sub(r"\s+", " ", sanitized).strip(" .")
    if not sanitized:
        sanitized = fallback
    if sanitized.upper().split(".", 1)[0] in _WINDOWS_RESERVED_NAMES:
        sanitized = f"_{sanitized}"
    return sanitized


async def collect_accepted_chapters(
    project_id: str,
    chapters: tuple[int, int] | None = None,
) -> list[ChapterExport]:
    """Load accepted head chapter content from SQLite, sorted by chapter number."""
    collection = await _collect_accepted_chapters_with_stats(project_id, chapters)
    return list(collection.chapters)


async def _collect_accepted_chapters_with_stats(
    project_id: str,
    chapters: tuple[int, int] | None = None,
) -> _ChapterCollection:
    if chapters is not None:
        _validate_chapter_range(chapters)

    head_repo = ChapterHeadRepository()
    version_repo = ChapterVersionRepository()
    try:
        heads = await head_repo.list_by_project(project_id)
    except sqlite3.Error as exc:
        raise _to_export_db_error(exc) from exc

    results: list[ChapterExport] = []
    skipped_count = 0
    for head in heads:
        if head.status != "accepted" or not head.accepted_version_id:
            continue
        if chapters is not None and not (chapters[0] <= head.chapter_number <= chapters[1]):
            continue

        try:
            version = await version_repo.get(head.accepted_version_id)
        except sqlite3.Error as exc:
            raise _to_export_db_error(exc) from exc
        if version is None:
            skipped_count += 1
            logger.warning(
                "export.chapter_version_missing",
                project_id=project_id,
                chapter_number=head.chapter_number,
                version_id=head.accepted_version_id,
            )
            continue
        if version.project_id != project_id or version.chapter_number != head.chapter_number:
            skipped_count += 1
            logger.warning(
                "export.chapter_version_mismatch",
                project_id=project_id,
                chapter_number=head.chapter_number,
                version_id=version.version_id,
                version_project_id=version.project_id,
                version_chapter_number=version.chapter_number,
            )
            continue

        results.append(
            ChapterExport(
                chapter_number=head.chapter_number,
                content=version.content,
                word_count=version.word_count,
                version_id=version.version_id,
            )
        )

    if not results:
        range_text = "" if chapters is None else f"（范围 {chapters[0]}-{chapters[1]}）"
        msg = f"项目 {project_id} 没有可导出的 accepted 章节{range_text}"
        raise ExportServiceError(msg)
    return _ChapterCollection(chapters=tuple(results), skipped_count=skipped_count)


def render_book(
    project_title: str | None,
    chapters: Sequence[ChapterExport],
    fmt: ExportFormat = "md",
    by: GroupBy = "flat",
    groups: Sequence[ExportGroup] = (),
    *,
    project_id: str | None = None,
) -> dict[str, str]:
    """Render files as ``filename -> content`` for pure-render consumers.

    ``render_book_files`` is the primary render API for export because it keeps
    per-file chapter membership. This wrapper intentionally drops that metadata.
    """
    return {
        rendered.filename: rendered.content
        for rendered in render_book_files(
            project_title,
            chapters,
            fmt=fmt,
            by=by,
            groups=groups,
            project_id=project_id,
        )
    }


def render_book_files(
    project_title: str | None,
    chapters: Sequence[ChapterExport],
    *,
    fmt: ExportFormat = "md",
    by: GroupBy = "flat",
    groups: Sequence[ExportGroup] = (),
    project_id: str | None = None,
) -> list[RenderedExportFile]:
    """Render manuscript files and preserve per-file chapter membership."""
    _validate_export_format(fmt)
    _validate_group_by(by)

    ordered_chapters = tuple(sorted(chapters, key=lambda item: item.chapter_number))
    if not ordered_chapters:
        msg = "没有可渲染的章节"
        raise ExportServiceError(msg)

    if by == "flat":
        return [
            _render_flat_file(
                project_title,
                project_id,
                ordered_chapters,
                fmt,
            )
        ]

    if not groups:
        logger.warning("export.groups_missing", group_by=by)
        return [
            _render_flat_file(
                project_title,
                project_id,
                ordered_chapters,
                fmt,
            )
        ]

    return _render_grouped_files(ordered_chapters, groups, fmt, by)


async def export_project(
    project_id: str,
    *,
    output_dir: Path = Path("exports"),
    fmt: ExportFormat = "md",
    by: GroupBy = "flat",
    chapters: tuple[int, int] | None = None,
) -> ExportResult:
    """Export a project's accepted manuscript files to disk.

    This is a read-only DB operation. It does not call ``init_schema()`` or run
    migrations, so exporting a historical DB will not mutate its schema.
    """
    _validate_export_format(fmt)
    _validate_group_by(by)
    if chapters is not None:
        _validate_chapter_range(chapters)

    try:
        project = await ProjectRepository().get(project_id)
    except sqlite3.Error as exc:
        raise _to_export_db_error(exc) from exc
    if project is None:
        msg = f"项目不存在: {project_id}"
        raise ExportServiceError(msg)

    collection = await _collect_accepted_chapters_with_stats(project_id, chapters)
    groups = await _load_export_groups(project_id, by)
    rendered_files = render_book_files(
        project.title,
        collection.chapters,
        fmt=fmt,
        by=by,
        groups=groups,
        project_id=project_id,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[ExportedFile] = []
    for rendered in rendered_files:
        path = output_dir / rendered.filename
        path.write_text(rendered.content, encoding="utf-8")
        written.append(ExportedFile(path=path, chapter_count=len(rendered.chapters)))

    result = ExportResult(files=tuple(written), skipped_count=collection.skipped_count)
    logger.info(
        "export.project_complete",
        project_id=project_id,
        output_dir=str(output_dir),
        format=fmt,
        group_by=by,
        file_count=len(written),
        chapter_count=sum(item.chapter_count for item in written),
        skipped_count=result.skipped_count,
    )
    return result


async def _load_export_groups(project_id: str, by: GroupBy) -> list[ExportGroup]:
    try:
        if by == "flat":
            return []
        if by == "arc":
            arcs = await ArcSummaryRepository().list_by_project(project_id)
            return [_group_from_arc(arc) for arc in arcs]

        volumes = await VolumeSummaryRepository().list_by_project(project_id)
        return [_group_from_volume(volume) for volume in volumes]
    except sqlite3.Error as exc:
        raise _to_export_db_error(exc) from exc


def _group_from_arc(arc: ArcSummary) -> ExportGroup:
    return ExportGroup(
        title=arc.arc_title,
        start_chapter=arc.start_chapter,
        end_chapter=arc.end_chapter,
    )


def _group_from_volume(volume: VolumeSummary) -> ExportGroup:
    return ExportGroup(
        title=volume.volume_title,
        start_chapter=volume.start_chapter,
        end_chapter=volume.end_chapter,
    )


def _render_flat_file(
    project_title: str | None,
    project_id: str | None,
    chapters: Sequence[ChapterExport],
    fmt: ExportFormat,
) -> RenderedExportFile:
    title = _display_project_title(project_title, project_id)
    filename_title = sanitize_filename_component(
        project_title,
        fallback=f"project-{project_id[:8]}" if project_id else "untitled",
    )
    filename = f"{filename_title}-flat.{fmt}"
    return RenderedExportFile(
        filename=filename,
        content=_render_content(title, chapters, fmt),
        chapters=tuple(chapter.chapter_number for chapter in chapters),
    )


def _render_grouped_files(
    chapters: Sequence[ChapterExport],
    groups: Sequence[ExportGroup],
    fmt: ExportFormat,
    by: Literal["arc", "volume"],
) -> list[RenderedExportFile]:
    valid_groups = _valid_groups(groups, by)
    assignments, ungrouped = _assign_chapters_to_groups(chapters, valid_groups, by)
    used_filenames: set[str] = set()
    rendered: list[RenderedExportFile] = []

    ungrouped_title = "未分弧" if by == "arc" else "未分卷"
    if ungrouped:
        rendered.append(
            _with_unique_filename(
                RenderedExportFile(
                    filename=f"{by}-00-{ungrouped_title}.{fmt}",
                    content=_render_content(
                        ungrouped_title,
                        ungrouped,
                        fmt,
                        chapter_range=_chapters_range(ungrouped),
                    ),
                    chapters=tuple(chapter.chapter_number for chapter in ungrouped),
                ),
                used_filenames,
            )
        )

    for index, group in enumerate(valid_groups, start=1):
        grouped_chapters = assignments[index - 1]
        if not grouped_chapters:
            logger.warning(
                "export.group_empty",
                group_by=by,
                title=group.title,
                start_chapter=group.start_chapter,
                end_chapter=group.end_chapter,
            )
            continue

        safe_title = sanitize_filename_component(group.title, fallback="untitled")
        display_title = group.title.strip() or "untitled"
        rendered.append(
            _with_unique_filename(
                RenderedExportFile(
                    filename=f"{by}-{index:02d}-{safe_title}.{fmt}",
                    content=_render_content(
                        display_title,
                        grouped_chapters,
                        fmt,
                        chapter_range=_chapters_range(grouped_chapters),
                    ),
                    chapters=tuple(chapter.chapter_number for chapter in grouped_chapters),
                ),
                used_filenames,
            )
        )

    return rendered


def _valid_groups(groups: Sequence[ExportGroup], by: str) -> list[ExportGroup]:
    valid: list[ExportGroup] = []
    for group in groups:
        if group.start_chapter < 1 or group.end_chapter < group.start_chapter:
            logger.warning(
                "export.group_invalid",
                group_by=by,
                title=group.title,
                start_chapter=group.start_chapter,
                end_chapter=group.end_chapter,
            )
            continue
        valid.append(group)
    return sorted(valid, key=lambda item: (item.start_chapter, item.end_chapter, item.title))


def _assign_chapters_to_groups(
    chapters: Sequence[ChapterExport],
    groups: Sequence[ExportGroup],
    by: str,
) -> tuple[list[list[ChapterExport]], list[ChapterExport]]:
    assignments: list[list[ChapterExport]] = [[] for _ in groups]
    ungrouped: list[ChapterExport] = []

    for chapter in chapters:
        matches = [
            index
            for index, group in enumerate(groups)
            if group.start_chapter <= chapter.chapter_number <= group.end_chapter
        ]
        if not matches:
            ungrouped.append(chapter)
            continue
        if len(matches) > 1:
            logger.warning(
                "export.group_overlap",
                group_by=by,
                chapter_number=chapter.chapter_number,
                selected_group=matches[0] + 1,
                matched_groups=[index + 1 for index in matches],
            )
        assignments[matches[0]].append(chapter)
    return assignments, ungrouped


def _render_content(
    title: str,
    chapters: Sequence[ChapterExport],
    fmt: ExportFormat,
    *,
    chapter_range: tuple[int, int] | None = None,
) -> str:
    if fmt == "md":
        return _render_markdown(title, chapters, chapter_range=chapter_range)
    return _render_txt(title, chapters)


def _render_markdown(
    title: str,
    chapters: Sequence[ChapterExport],
    *,
    chapter_range: tuple[int, int] | None = None,
) -> str:
    sections = [f"# {title}"]
    if chapter_range is not None:
        sections.append(f"<!-- chapters {chapter_range[0]}-{chapter_range[1]} -->")
    for chapter in chapters:
        sections.append(f"## 第 {chapter.chapter_number} 章\n\n{chapter.content}")
    return _single_trailing_newline("\n\n".join(sections))


def _render_txt(title: str, chapters: Sequence[ChapterExport]) -> str:
    sections = [title]
    for chapter in chapters:
        sections.append(f"第 {chapter.chapter_number} 章\n\n{chapter.content}")
    return _single_trailing_newline("\n\n".join(sections))


def _display_project_title(project_title: str | None, project_id: str | None) -> str:
    title = (project_title or "").strip()
    if title:
        return title
    if project_id:
        return f"project-{project_id[:8]}"
    return "未命名项目"


def _with_unique_filename(
    rendered: RenderedExportFile,
    used_filenames: set[str],
) -> RenderedExportFile:
    filename = rendered.filename
    if filename not in used_filenames:
        used_filenames.add(filename)
        return rendered

    path = Path(filename)
    counter = 2
    while True:
        candidate = f"{path.stem}-{counter}{path.suffix}"
        if candidate not in used_filenames:
            used_filenames.add(candidate)
            return RenderedExportFile(
                filename=candidate,
                content=rendered.content,
                chapters=rendered.chapters,
            )
        counter += 1


def _chapters_range(chapters: Sequence[ChapterExport]) -> tuple[int, int]:
    numbers = [chapter.chapter_number for chapter in chapters]
    return (min(numbers), max(numbers))


def _single_trailing_newline(content: str) -> str:
    return content.rstrip("\n") + "\n"


def _validate_chapter_range(chapters: tuple[int, int]) -> None:
    start, end = chapters
    if start < 1 or end < 1:
        msg = "章节范围必须从 1 或更大的正整数开始"
        raise ExportServiceError(msg)
    if start > end:
        msg = "章节范围起始章不能大于结束章"
        raise ExportServiceError(msg)


def _validate_export_format(fmt: str) -> None:
    if fmt not in {"md", "txt"}:
        msg = f"不支持的导出格式: {fmt}"
        raise ExportServiceError(msg)


def _validate_group_by(by: str) -> None:
    if by not in {"flat", "arc", "volume"}:
        msg = f"不支持的导出分组: {by}"
        raise ExportServiceError(msg)


def _to_export_db_error(exc: sqlite3.Error) -> ExportServiceError:
    detail = str(exc)
    if "no such table" in detail.lower():
        return ExportServiceError(
            "导出失败：数据库 schema 不完整；export 是只读命令，不会自动迁移源库，"
            "请先初始化或迁移该 Songyan 数据库。"
        )
    return ExportServiceError(f"导出失败：读取数据库失败（{detail}）")
