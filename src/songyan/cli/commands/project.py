"""task 256：``songyan project list``（PRD :559 之一；B7 只做 list 不做别名）。"""

from __future__ import annotations

import asyncio
import json

import click

from songyan.db.connection import get_db_path
from songyan.db.repository import ProjectRepository


async def _list_payload() -> dict[str, object]:
    db_path = get_db_path()
    if not db_path.is_file():
        raise click.ClickException(f"找不到数据库文件: {db_path}")
    rows = await ProjectRepository().list_projects()
    projects = []
    for row in rows:
        project = dict(row["project"])  # type: ignore[arg-type]
        projects.append(
            {
                "project_id": project.get("project_id"),
                "title": project.get("title"),
                "genre_id": project.get("genre_id"),
                "mode_id": project.get("mode_id"),
                "lifecycle_status": project.get("lifecycle_status"),
                "estimated_chapters": project.get("estimated_chapters"),
                "words_per_chapter": project.get("words_per_chapter"),
                "heads": int(row["heads"]),  # type: ignore[arg-type]
            }
        )
    return {"projects": projects}


@click.group(name="project")
def project_group() -> None:
    """项目级只读面（list；new/init 别名不在本期——B7）。"""


@project_group.command(name="list")
@click.option("--json", "as_json", is_flag=True, help="JSON 输出")
def project_list(as_json: bool) -> None:
    """列出全部项目（id/title/体裁/生命周期/章头数）；空库 exit 0。"""
    payload = asyncio.run(_list_payload())
    projects = payload["projects"]
    assert isinstance(projects, list)
    if as_json:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    if not projects:
        click.echo("（无项目）")
        return
    for row in projects:
        click.echo(
            f"- {row['project_id']} title={row['title'] or '-'} "
            f"genre={row['genre_id']} lifecycle={row['lifecycle_status']} "
            f"heads={row['heads']}"
        )


def register_project_commands(cli: click.Group) -> None:
    """Mount the ``project`` group (list)。"""
    cli.add_command(project_group)
