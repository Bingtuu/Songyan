"""CLI 入口（Click 框架）."""

from __future__ import annotations

import asyncio
import uuid

import click

from songyan.creative_modes.registry import (
    list_creative_mode_profiles,
    load_creative_mode_profile,
)
from songyan.db.migrations import init_schema
from songyan.db.repository import ProjectRepository
from songyan.genres.loader import list_genre_profiles, load_genre_profile
from songyan.models.project import ProjectSetting


@click.group()
def cli() -> None:
    """Songyan（松烟）— 多 Agent 中文小说写作系统."""
    pass


def _select_mode() -> str:
    """交互式选择创作模式，返回 mode_id."""
    modes = list_creative_mode_profiles()
    click.echo("\n选择创作模式:")
    for idx, mode_id in enumerate(modes, start=1):
        profile = load_creative_mode_profile(mode_id)
        click.echo(f"  {idx}. {mode_id} — {profile.name}")

    while True:
        choice = click.prompt("请输入序号", type=int)
        if 1 <= choice <= len(modes):
            return modes[choice - 1]
        click.echo(f"无效输入，请输入 1-{len(modes)} 之间的数字")


def _select_genre() -> str:
    """交互式选择题材，返回 genre_id."""
    genres = list_genre_profiles()
    click.echo("\n选择题材:")
    for idx, genre_id in enumerate(genres, start=1):
        profile = load_genre_profile(genre_id)
        click.echo(f"  {idx}. {genre_id} — {profile.name}")

    while True:
        choice = click.prompt("请输入序号", type=int)
        if 1 <= choice <= len(genres):
            return genres[choice - 1]
        click.echo(f"无效输入，请输入 1-{len(genres)} 之间的数字")


async def _create_project_async() -> tuple[str, ProjectSetting]:
    """异步执行项目创建逻辑."""
    await init_schema()

    mode_id = _select_mode()
    genre_id = _select_genre()
    title = click.prompt("项目标题", default="", show_default=False)
    protagonist_name = click.prompt("主角姓名")
    protagonist_background = click.prompt(
        "主角背景（可选）", default="", show_default=False
    )
    core_hook = click.prompt("核心钩子（可选）", default="", show_default=False)
    target_reader_expectation = click.prompt(
        "目标读者预期（可选）", default="", show_default=False
    )
    target_word_count = click.prompt("目标字数", default=100_000, type=int)
    tone = click.prompt("基调", default="热血")

    project = ProjectSetting(
        title=title,
        genre_id=genre_id,
        mode_id=mode_id,
        protagonist_name=protagonist_name,
        protagonist_background=protagonist_background,
        core_hook=core_hook,
        target_reader_expectation=target_reader_expectation,
        target_word_count=target_word_count,
        tone=tone,
    )

    project_id = uuid.uuid4().hex
    repo = ProjectRepository()
    await repo.create(project, project_id)

    return project_id, project


@cli.command()
def create_project() -> None:
    """交互式创建小说项目."""
    try:
        project_id, project = asyncio.run(_create_project_async())
    except click.Abort:
        raise
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"\n✓ 项目已创建: {project_id}")
    click.echo(f"  模式: {project.mode_id}")
    click.echo(f"  题材: {project.genre_id}")
    click.echo(f"  标题: {project.title or '(未命名)'}")


async def _list_projects_async() -> list[dict]:
    """异步查询所有项目，返回原始行数据列表."""
    await init_schema()

    from sqlite3 import Row

    from songyan.db.connection import get_db

    async with get_db() as conn:
        conn.row_factory = Row
        cursor = await conn.execute(
            """
            SELECT project_id, title, genre_id, mode_id,
                   protagonist_name, created_at
            FROM projects
            ORDER BY created_at DESC
            """
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


@cli.command()
def list_projects() -> None:
    """列出所有小说项目."""
    try:
        projects = asyncio.run(_list_projects_async())
    except click.Abort:
        raise
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc

    if not projects:
        click.echo("暂无项目。使用 `songyan create-project` 创建一个。")
        return

    click.echo(
        f"\n{'项目 ID':<24} {'标题':<14} {'题材':<10} "
        f"{'模式':<10} {'主角':<10} {'创建时间'}"
    )
    click.echo("-" * 84)
    for row in projects:
        title = row["title"] or "(未命名)"
        click.echo(
            f"{row['project_id']:<24} {title:<14} "
            f"{row['genre_id']:<10} {row['mode_id']:<10} "
            f"{row['protagonist_name']:<10} {row['created_at']}"
        )
