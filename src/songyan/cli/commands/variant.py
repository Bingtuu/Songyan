"""M3 variant CLI — step 1 registers ``variant list`` only (no stubs)."""

from __future__ import annotations

import asyncio
import json

import click

from songyan.db.chapter_variant_repo import ChapterVariantRepository
from songyan.db.connection import get_db_path
from songyan.db.repository import ProjectRepository


async def _ensure_project_readable(project_id: str) -> None:
    db_path = get_db_path()
    if not db_path.is_file():
        raise click.ClickException(f"找不到数据库文件: {db_path}")
    project = await ProjectRepository().get(project_id)
    if project is None:
        raise click.ClickException(f"项目不存在: {project_id}")


async def _list_variants(project_id: str, chapter: int) -> list[dict[str, object]]:
    await _ensure_project_readable(project_id)
    rows = await ChapterVariantRepository().list_for_chapter(project_id, chapter)
    return [row.model_dump(mode="json") for row in rows]


@click.group(name="variant")
def variant_group() -> None:
    """章内 Variant（抽卡）。步 1 仅 list；generate/pick 等随后续小步落地。"""


@variant_group.command(name="list")
@click.option("--project-id", required=True, help="项目 ID")
@click.option("--chapter", required=True, type=int, help="章号")
@click.option("--json", "as_json", is_flag=True, help="JSON 输出")
def variant_list(project_id: str, chapter: int, as_json: bool) -> None:
    """列出同章 variant 槽；无槽时返回空列表。"""
    if chapter < 1:
        raise click.ClickException("chapter 必须 >= 1")
    rows = asyncio.run(_list_variants(project_id, chapter))
    if as_json:
        click.echo(json.dumps({"variants": rows}, ensure_ascii=False, indent=2))
        return
    if not rows:
        click.echo("（空）")
        return
    for row in rows:
        click.echo(
            f"- slot={row['slot_index']} status={row['status']} "
            f"ref={row['content_ref']} stale={row['stale_vs_canon']} "
            f"cost={row['cost_cny_estimate']}"
        )


def register_variant_commands(cli: click.Group) -> None:
    """Mount the ``variant`` group (only implemented subcommands)."""
    cli.add_command(variant_group)
