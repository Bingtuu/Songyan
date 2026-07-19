"""Tests for V9 Task 177 — manuscript export service and CLI wiring."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import aiosqlite
import pytest
from click.testing import CliRunner
from structlog.testing import capture_logs

from songyan.cli import main as cli_main
from songyan.db.layered_context_repo import ArcSummaryRepository, VolumeSummaryRepository
from songyan.db.repository import ChapterHeadRepository, ChapterVersionRepository, ProjectRepository
from songyan.models import ArcSummary, ChapterHead, ChapterVersion, ProjectSetting, VolumeSummary
from songyan.services.export_service import (
    ChapterExport,
    ExportedFile,
    ExportGroup,
    ExportServiceError,
    collect_accepted_chapters,
    export_project,
    render_book,
    render_book_files,
    sanitize_filename_component,
)

PID = "proj-177"


async def _seed_project(project_id: str = PID, title: str = "测试书") -> None:
    await ProjectRepository().create(
        ProjectSetting(title=title, genre_id="xuanhuan", protagonist_name="林渊"),
        project_id,
    )


async def _seed_chapter(
    chapter_number: int,
    content: str,
    *,
    project_id: str = PID,
    accepted: bool = True,
) -> str:
    version_id = f"v-{project_id}-{chapter_number}"
    await ChapterVersionRepository().create(
        ChapterVersion(
            version_id=version_id,
            project_id=project_id,
            chapter_number=chapter_number,
            version_number=1,
            version_type="accepted" if accepted else "draft",
            content=content,
            word_count=len(content),
        )
    )
    await ChapterHeadRepository().update(
        ChapterHead(
            project_id=project_id,
            chapter_number=chapter_number,
            current_version_id=version_id,
            accepted_version_id=version_id if accepted else None,
            status="accepted" if accepted else "draft",
        )
    )
    return version_id


async def _seed_missing_accepted_head(
    db_path: Path,
    chapter_number: int,
    *,
    project_id: str = PID,
) -> None:
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(
            """INSERT INTO chapter_heads (
                project_id, chapter_number, current_version_id,
                accepted_version_id, status
            ) VALUES (?, ?, ?, ?, ?)""",
            (
                project_id,
                chapter_number,
                f"missing-{chapter_number}",
                f"missing-{chapter_number}",
                "accepted",
            ),
        )
        await conn.commit()


async def test_collect_accepted_chapters_sorts_filters_and_warns(
    test_db: Path,
) -> None:
    await _seed_project()
    await _seed_chapter(2, "第二章正文")
    await _seed_chapter(1, "第一章正文")
    await _seed_chapter(4, "第四章草稿", accepted=False)
    await _seed_missing_accepted_head(test_db, 3)

    with capture_logs() as logs:
        chapters = await collect_accepted_chapters(PID, (1, 3))

    assert [chapter.chapter_number for chapter in chapters] == [1, 2]
    assert [chapter.content for chapter in chapters] == ["第一章正文", "第二章正文"]
    assert any(entry.get("event") == "export.chapter_version_missing" for entry in logs)


async def test_collect_accepted_chapters_rejects_empty_range(test_db: Path) -> None:
    await _seed_project()
    await _seed_chapter(1, "第一章正文")

    with pytest.raises(ExportServiceError, match="没有可导出"):
        await collect_accepted_chapters(PID, (2, 3))


def test_render_flat_markdown_is_clean_and_ordered() -> None:
    rendered = render_book(
        "灵渊纪",
        [
            ChapterExport(2, "第二章正文"),
            ChapterExport(1, "第一章正文"),
        ],
    )

    assert list(rendered) == ["灵渊纪-flat.md"]
    content = rendered["灵渊纪-flat.md"]
    assert content.startswith("# 灵渊纪\n\n## 第 1 章\n\n第一章正文")
    assert content.index("## 第 1 章") < content.index("## 第 2 章")
    assert "version_id" not in content
    assert "字）" not in content
    assert "---" not in content
    assert content.endswith("\n")


def test_render_txt_has_no_markdown_symbols() -> None:
    rendered = render_book(
        "断刀行",
        [ChapterExport(1, "刀光落下。"), ChapterExport(2, "雪夜无声。")],
        fmt="txt",
    )

    content = rendered["断刀行-flat.txt"]
    assert "#" not in content
    assert "第 1 章\n\n刀光落下。" in content
    assert "第 2 章\n\n雪夜无声。" in content


def test_render_by_arc_splits_files_and_keeps_ungrouped_chapters() -> None:
    rendered = render_book(
        "测试书",
        [
            ChapterExport(1, "一"),
            ChapterExport(2, "二"),
            ChapterExport(3, "三"),
            ChapterExport(4, "四"),
            ChapterExport(5, "五"),
        ],
        by="arc",
        groups=[
            ExportGroup("起势", 1, 2),
            ExportGroup("收束", 4, 4),
        ],
    )

    assert set(rendered) == {
        "arc-00-未分弧.md",
        "arc-01-起势.md",
        "arc-02-收束.md",
    }
    assert "## 第 1 章\n\n一" in rendered["arc-01-起势.md"]
    assert "## 第 2 章\n\n二" in rendered["arc-01-起势.md"]
    assert "<!-- chapters 1-2 -->" in rendered["arc-01-起势.md"]
    assert "## 第 3 章\n\n三" in rendered["arc-00-未分弧.md"]
    assert "## 第 5 章\n\n五" in rendered["arc-00-未分弧.md"]
    assert "## 第 4 章\n\n四" in rendered["arc-02-收束.md"]


def test_render_by_arc_falls_back_to_flat_when_no_group_records() -> None:
    with capture_logs() as logs:
        rendered = render_book(
            "测试书",
            [ChapterExport(1, "正文")],
            by="arc",
            groups=[],
        )

    assert list(rendered) == ["测试书-flat.md"]
    assert any(entry.get("event") == "export.groups_missing" for entry in logs)


def test_render_grouped_invalid_overlap_and_empty_groups_warn() -> None:
    with capture_logs() as logs:
        rendered = render_book_files(
            "测试书",
            [ChapterExport(1, "一"), ChapterExport(2, "二"), ChapterExport(3, "三")],
            by="arc",
            groups=[
                ExportGroup("占位", 0, 0),
                ExportGroup("A", 1, 2),
                ExportGroup("B", 2, 3),
                ExportGroup("空弧", 10, 12),
            ],
        )

    by_name = {item.filename: item for item in rendered}
    assert by_name["arc-01-A.md"].chapters == (1, 2)
    assert by_name["arc-02-B.md"].chapters == (3,)
    assert "arc-03-空弧.md" not in by_name
    assert any(entry.get("event") == "export.group_invalid" for entry in logs)
    assert any(entry.get("event") == "export.group_overlap" for entry in logs)
    assert any(entry.get("event") == "export.group_empty" for entry in logs)


def test_render_by_volume_ignores_invalid_placeholder() -> None:
    rendered = render_book(
        "测试书",
        [ChapterExport(1, "一"), ChapterExport(2, "二")],
        by="volume",
        groups=[
            ExportGroup("（暂无卷数据）", 0, 0),
            ExportGroup("第一卷", 1, 2),
        ],
    )

    assert set(rendered) == {"volume-01-第一卷.md"}
    assert "## 第 1 章\n\n一" in rendered["volume-01-第一卷.md"]


def test_filename_sanitizer_is_windows_safe() -> None:
    safe = sanitize_filename_component('  A<>:"/\\|?* .  ')

    assert safe == "A_________"
    for char in '<>:"/\\|?*':
        assert char not in safe
    assert not safe.endswith((" ", "."))
    assert sanitize_filename_component(" ", fallback="untitled") == "untitled"
    assert sanitize_filename_component("CON") == "_CON"


async def test_export_project_writes_current_files_without_cleaning_old_output(
    test_db: Path,
    tmp_path: Path,
) -> None:
    await _seed_project(title="净书")
    await _seed_chapter(1, "第一章正文")
    await _seed_chapter(2, "第二章正文")

    output_dir = tmp_path / "export"
    output_dir.mkdir()
    stale_file = output_dir / "stale.md"
    stale_file.write_text("old", encoding="utf-8")

    written = await export_project(PID, output_dir=output_dir)

    assert written == [ExportedFile(path=output_dir / "净书-flat.md", chapter_count=2)]
    assert stale_file.exists()
    content = (output_dir / "净书-flat.md").read_text(encoding="utf-8")
    assert "第一章正文" in content
    assert "第二章正文" in content


async def test_export_project_uses_arc_metadata(test_db: Path, tmp_path: Path) -> None:
    await _seed_project(title="弧书")
    await _seed_chapter(1, "第一章正文")
    await _seed_chapter(2, "第二章正文")
    await ArcSummaryRepository().create(
        ArcSummary(arc_id="arc-1", start_chapter=1, end_chapter=2, arc_title="第一弧"),
        project_id=PID,
    )
    await VolumeSummaryRepository().create(
        VolumeSummary(volume_id="vol-0", start_chapter=0, end_chapter=0, volume_title="占位"),
        project_id=PID,
    )

    written = await export_project(PID, output_dir=tmp_path, by="arc")

    assert written == [ExportedFile(path=tmp_path / "arc-01-第一弧.md", chapter_count=2)]
    assert (tmp_path / "arc-01-第一弧.md").exists()


def test_export_cli_transmits_parameters(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[dict[str, Any]] = []

    async def fake_run_export_project(
        project_id: str,
        *,
        output_dir: Path,
        fmt: str,
        by: str,
        chapters: tuple[int, int] | None,
    ) -> list[ExportedFile]:
        calls.append(
            {
                "project_id": project_id,
                "output_dir": output_dir,
                "fmt": fmt,
                "by": by,
                "chapters": chapters,
            }
        )
        return [ExportedFile(path=output_dir / "book.txt", chapter_count=2)]

    monkeypatch.setattr(cli_main, "_run_export_project", fake_run_export_project)

    result = CliRunner().invoke(
        cli_main.cli,
        [
            "export",
            "--project-id",
            "p1",
            "--format",
            "txt",
            "--by",
            "arc",
            "--chapters",
            "1-2",
            "--output",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert calls == [
        {
            "project_id": "p1",
            "output_dir": tmp_path,
            "fmt": "txt",
            "by": "arc",
            "chapters": (1, 2),
        }
    ]
    assert "已导出 2 章到 1 个文件" in result.output
    assert "book.txt (2 章)" in result.output


def test_export_cli_rejects_invalid_chapter_range() -> None:
    result = CliRunner().invoke(
        cli_main.cli,
        ["export", "--project-id", "p1", "--chapters", "3-1"],
    )

    assert result.exit_code != 0
    assert "章节范围起始章不能大于结束章" in result.output
