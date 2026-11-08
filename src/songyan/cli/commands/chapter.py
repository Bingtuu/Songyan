"""M4 步 2: chapter accept CLI — 章级人确认写径（tech-m4 §5 步 2 / B2/B11）.

exit 码表（B11）：0 = 已确认；1 = 缺库 / 缺项目 / 参数非法（含文件错误）；
2 = 无可确认稿 / 重复 accept（幂等提示）。
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import click

from songyan.db.connection import get_db_path
from songyan.db.repository import ProjectRepository
from songyan.services.chapter_accept import (
    AlreadyAcceptedError,
    ChapterFileError,
    NothingToAcceptError,
    accept_chapter,
)


class ChapterBusinessReject(click.ClickException):
    """Business reject — process exit 2（tech-m4 B11）。"""

    exit_code = 2


async def _accept_chapter(
    project_id: str,
    chapter: int,
    from_file: Path | None,
) -> dict[str, object]:
    db_path = get_db_path()
    if not db_path.is_file():
        raise click.ClickException(f"找不到数据库文件: {db_path}")
    project = await ProjectRepository().get(project_id)
    if project is None:
        raise click.ClickException(f"项目不存在: {project_id}")
    try:
        outcome = await accept_chapter(project_id, chapter, from_file=from_file)
    except (NothingToAcceptError, AlreadyAcceptedError) as exc:
        raise ChapterBusinessReject(str(exc)) from exc
    except ChapterFileError as exc:
        raise click.ClickException(str(exc)) from exc
    return {
        "chapter": outcome.chapter_number,
        "accepted_version_id": outcome.accepted_version_id,
        "source_version_id": outcome.source_version_id,
        "edited_version_id": outcome.edited_version_id,
        "word_count": outcome.word_count,
    }


@click.group(name="chapter")
def chapter_group() -> None:
    """章级人确认写径。子命令随 tech-m4 小步落地，无空桩。"""


@chapter_group.command(name="accept")
@click.option("--project-id", required=True, help="项目 ID")
@click.option("--chapter", required=True, type=int, help="章号")
@click.option(
    "--from-file",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="外置编辑稿路径；传入则以该稿为 accepted 副本来源（先物化 edited 行）",
)
@click.option("--json", "as_json", is_flag=True, help="JSON 输出")
def chapter_accept_cmd(
    project_id: str,
    chapter: int,
    from_file: Path | None,
    as_json: bool,
) -> None:
    """确认一章工作稿为 accepted（picked / 人改稿 → accepted）；不写结算库。"""
    if chapter < 1:
        raise click.ClickException("chapter 必须 >= 1")
    payload = asyncio.run(_accept_chapter(project_id, chapter, from_file))
    if as_json:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    click.echo(
        f"已确认 chapter={payload['chapter']} "
        f"accepted_version_id={payload['accepted_version_id']} "
        f"word_count={payload['word_count']}"
    )


def register_chapter_commands(cli: click.Group) -> None:
    """Mount the ``chapter`` group (only implemented subcommands)."""
    cli.add_command(chapter_group)
