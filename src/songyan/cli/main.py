"""CLI 入口（Click 框架）."""

from __future__ import annotations

import asyncio
import uuid

import click

from songyan.cli.commands.index import register_index_commands
from songyan.creative_modes.registry import (
    list_creative_mode_profiles,
    load_creative_mode_profile,
)
from songyan.db.continuity_repo import ContinuityReportRepository
from songyan.db.human_mark_repo import HumanMarkRepository
from songyan.db.migrations import init_schema
from songyan.db.repository import ProjectRepository
from songyan.genres.loader import list_genre_profiles, load_genre_profile
from songyan.models.human_mark import HumanMark
from songyan.models.project import ProjectSetting, derive_arc_boundaries
from songyan.workflows.phase2_graph import run_project_pipeline

# CLI 层可捕获的异常类型（排除 KeyboardInterrupt / SystemExit）
_CLI_CATCHABLE = (
    RuntimeError,
    OSError,
    ConnectionError,
    ValueError,
    TypeError,
    ImportError,
    KeyError,
    AttributeError,
)


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


_STRUCTURE_OPTIONS = [
    ("three_act", "三幕式（起承转合，有明确结局，适合中短篇）"),
    ("five_act", "五幕式（更复杂的冲突升级结构）"),
    ("serial", "序列化连载（有弧但无固定终点，适合长篇连载）"),
    ("free", "自由结构（不预设结构）"),
]


def _select_story_structure() -> str:
    """交互式选择故事结构，返回 structure 值."""
    click.echo("\n故事结构:")
    for idx, (value, label) in enumerate(_STRUCTURE_OPTIONS, start=1):
        click.echo(f"  {idx}. {label}")

    while True:
        choice = click.prompt("请输入序号", default=4, type=int)
        if 1 <= choice <= len(_STRUCTURE_OPTIONS):
            return _STRUCTURE_OPTIONS[choice - 1][0]
        click.echo(f"无效输入，请输入 1-{len(_STRUCTURE_OPTIONS)} 之间的数字")


def _select_sub_genre(genre_id: str) -> str | None:
    """交互式选择题材子类型，返回 sub_genre_id 或 None."""
    profile = load_genre_profile(genre_id)
    if not profile.sub_genres:
        return None

    click.echo("\n题材子类型（可选，直接回车跳过）:")
    click.echo("  0. （不选）")
    for idx, sub in enumerate(profile.sub_genres, start=1):
        click.echo(f"  {idx}. {sub.name}")

    choice = click.prompt("请输入序号", default=0, type=int)
    if 1 <= choice <= len(profile.sub_genres):
        return profile.sub_genres[choice - 1].sub_genre_id
    return None


async def _create_project_async() -> tuple[str, ProjectSetting]:
    """异步执行项目创建逻辑."""
    await init_schema()

    mode_id = _select_mode()
    genre_id = _select_genre()
    title = click.prompt("项目标题", default="", show_default=False)
    protagonist_name = click.prompt("主角姓名")
    protagonist_background = click.prompt("主角背景（可选）", default="", show_default=False)
    core_hook = click.prompt("核心钩子（可选）", default="", show_default=False)
    target_reader_expectation = click.prompt("目标读者预期（可选）", default="", show_default=False)
    target_word_count = click.prompt("目标字数", default=100_000, type=int)
    tone = click.prompt("基调", default="热血")

    # Phase 8a: 新增种子配置
    estimated_chapters = click.prompt("预估总章数", default=30, type=int)
    words_per_chapter = click.prompt("每章目标字数", default=3000, type=int)
    story_structure = _select_story_structure()
    sub_genre_id = _select_sub_genre(genre_id)

    # 自动推导 arc_boundaries
    arc_boundaries: list[int] = []
    arc_boundaries_auto = False
    if story_structure != "free" and estimated_chapters > 0:
        arc_boundaries = derive_arc_boundaries(story_structure, estimated_chapters)
        arc_boundaries_auto = bool(arc_boundaries)

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
        estimated_chapters=estimated_chapters,
        words_per_chapter=words_per_chapter,
        story_structure=story_structure,
        sub_genre_id=sub_genre_id,
        arc_boundaries=arc_boundaries,
        arc_boundaries_auto=arc_boundaries_auto,
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
    except _CLI_CATCHABLE as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"\n✓ 项目已创建: {project_id}")
    click.echo(f"  模式: {project.mode_id}")
    click.echo(f"  题材: {project.genre_id}")
    click.echo(f"  标题: {project.title or '(未命名)'}")
    click.echo(f"  预估章数: {project.estimated_chapters}")
    click.echo(f"  每章字数: {project.words_per_chapter}")
    click.echo(f"  故事结构: {project.story_structure}")
    if project.sub_genre_id:
        click.echo(f"  子类型: {project.sub_genre_id}")
    if project.arc_boundaries:
        click.echo(f"  Arc 边界: {project.arc_boundaries} (自动推导)")


# ---------------------------------------------------------------------------
# Phase 7: Human mark commands
# ---------------------------------------------------------------------------


@cli.group(name="mark")
def mark_cli() -> None:
    """人类辅助记忆标记管理."""
    pass


@mark_cli.command(name="add")
@click.option("--project-id", required=True, help="项目 ID")
@click.option(
    "--type",
    "mark_type",
    required=True,
    type=click.Choice(["setting", "character", "foreshadowing", "custom"]),
    help="标记类型",
)
@click.option("--target", required=True, help="目标标识符")
@click.option("--note", default="", help="备注说明")
@click.option("--priority", default=5, type=int, help="优先级 1~10")
@click.option("--chapter", default=None, type=int, help="关联章节号（仅记录）")
def mark_add(
    project_id: str,
    mark_type: str,
    target: str,
    note: str,
    priority: int,
    chapter: int | None,
) -> None:
    """添加一条人类标记."""
    try:
        import uuid

        asyncio.run(init_schema())
        mark = HumanMark(
            mark_id=f"hm_{uuid.uuid4().hex[:8]}",
            project_id=project_id,
            mark_type=mark_type,
            target_key=target,
            note=note,
            priority=max(1, min(10, priority)),
            created_at_chapter=chapter,
        )
        asyncio.run(HumanMarkRepository().create(mark))
        click.echo(
            f"✓ 标记已创建: {mark.mark_id} [{mark_type}] {target} (priority={mark.priority})"
        )
    except click.Abort:
        raise
    except _CLI_CATCHABLE as exc:
        raise click.ClickException(str(exc)) from exc


@mark_cli.command(name="list")
@click.option("--project-id", required=True, help="项目 ID")
@click.option(
    "--type",
    default=None,
    type=click.Choice(["setting", "character", "foreshadowing", "custom"]),
    help="按类型过滤",
)
@click.option("--min-priority", default=0, type=int, help="最低优先级")
@click.option("--suggested", is_flag=True, help="显示系统建议的标记（需 Task 043）")
def mark_list(
    project_id: str,
    type: str | None,
    min_priority: int,
    suggested: bool,
) -> None:
    """列出项目的人类标记."""
    try:
        asyncio.run(init_schema())

        if suggested:
            report = asyncio.run(ContinuityReportRepository().get_latest(project_id))
            if report is None or not report.suggested_marks:
                click.echo("暂无系统建议标记。")
                return
            click.echo(f"\n{'目标':<20} {'类型':<10} {'建议优先级':<10} {'理由'}")
            click.echo("-" * 80)
            for sm in report.suggested_marks:
                reason = sm.reason[:40] + "..." if len(sm.reason) > 40 else sm.reason
                click.echo(
                    f"{sm.target_key:<20} {sm.mark_type:<10} {sm.suggested_priority:<10} {reason}"
                )
            return

        marks = asyncio.run(
            HumanMarkRepository().list_by_project(
                project_id,
                mark_type=type,
                min_priority=min_priority,
            )
        )

        if not marks:
            click.echo("暂无标记。")
            return

        click.echo(
            f"\n{'标记 ID':<14} {'类型':<10} {'目标':<20} {'优先级':<8} {'章节':<6} {'备注'}"
        )
        click.echo("-" * 80)
        for m in marks:
            chapter = str(m.created_at_chapter or "-")
            note = m.note[:30] + "..." if len(m.note) > 30 else m.note
            click.echo(
                f"{m.mark_id:<14} {m.mark_type:<10} {m.target_key:<20} "
                f"{m.priority:<8} {chapter:<6} {note}"
            )
    except click.Abort:
        raise
    except _CLI_CATCHABLE as exc:
        raise click.ClickException(str(exc)) from exc


@mark_cli.command(name="remove")
@click.option("--project-id", required=True, help="项目 ID")
@click.option("--mark-id", required=True, help="标记 ID")
def mark_remove(project_id: str, mark_id: str) -> None:
    """删除一条人类标记."""
    try:
        asyncio.run(init_schema())
        deleted = asyncio.run(HumanMarkRepository().remove(mark_id))
        if deleted:
            click.echo(f"✓ 标记已删除: {mark_id}")
        else:
            click.echo(f"× 未找到标记: {mark_id}")
    except click.Abort:
        raise
    except _CLI_CATCHABLE as exc:
        raise click.ClickException(str(exc)) from exc


@mark_cli.command(name="update-priority")
@click.option("--project-id", required=True, help="项目 ID")
@click.option("--mark-id", required=True, help="标记 ID")
@click.option("--priority", required=True, type=int, help="新优先级 1~10")
def mark_update_priority(project_id: str, mark_id: str, priority: int) -> None:
    """更新标记优先级."""
    try:
        asyncio.run(init_schema())
        priority = max(1, min(10, priority))
        updated = asyncio.run(HumanMarkRepository().update_priority(mark_id, priority))
        if updated:
            click.echo(f"✓ 标记优先级已更新: {mark_id} → {priority}")
        else:
            click.echo(f"× 未找到标记: {mark_id}")
    except click.Abort:
        raise
    except _CLI_CATCHABLE as exc:
        raise click.ClickException(str(exc)) from exc


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
    except _CLI_CATCHABLE as exc:
        raise click.ClickException(str(exc)) from exc

    if not projects:
        click.echo("暂无项目。使用 `songyan create-project` 创建一个。")
        return

    click.echo(
        f"\n{'项目 ID':<24} {'标题':<14} {'题材':<10} {'模式':<10} {'主角':<10} {'创建时间'}"
    )
    click.echo("-" * 84)
    for row in projects:
        title = row["title"] or "(未命名)"
        click.echo(
            f"{row['project_id']:<24} {title:<14} "
            f"{row['genre_id']:<10} {row['mode_id']:<10} "
            f"{row['protagonist_name']:<10} {row['created_at']}"
        )


@cli.command()
@click.option("--project-id", required=True, help="项目 ID")
@click.option("--chapters", required=True, help="章节范围，如 1-10")
@click.option("--mode-id", default="webnovel", help="创作模式 ID")
@click.option("--human-gates", default="", help="启用的 Human Gate，逗号分隔")
@click.option("--auto-confirm", is_flag=True, help="全自动化，跳过所有 optional gate")
@click.option(
    "--rag-mode", default=None, type=click.Choice(["auto", "always", "never"]), help="覆盖 RAG 模式"
)
@click.option("--skip-rag", is_flag=True, help="禁用 RAG 检索")
def run(
    project_id: str,
    chapters: str,
    mode_id: str,
    human_gates: str,
    auto_confirm: bool,
    rag_mode: str | None,
    skip_rag: bool,
) -> None:
    """运行多章流水线."""
    try:
        # 解析章节范围
        if "-" in chapters:
            start, end = chapters.split("-")
            chapter_range = (int(start), int(end))
        else:
            chapter_range = (int(chapters), int(chapters))

        # 解析启用的 gates
        enabled_gates = [g.strip() for g in human_gates.split(",") if g.strip()]
        if enabled_gates:
            click.echo(f"启用的 Human Gates: {', '.join(enabled_gates)}")

        # Phase 8b: RAG 模式覆盖
        if skip_rag:
            rag_mode = "never"
        if rag_mode:
            import os

            os.environ["SONGYAN_RAG_MODE"] = rag_mode
            click.echo(f"RAG 模式: {rag_mode}")

        result = asyncio.run(
            run_project_pipeline(
                project_id=project_id,
                chapter_range=chapter_range,
                mode_id=mode_id,
                auto_confirm=auto_confirm,
            )
        )

        total_chapters = len(result.chapters_completed) + len(result.chapters_failed)
        click.echo(f"\n运行完成: {len(result.chapters_completed)}/{total_chapters} 章成功")
        if result.chapters_failed:
            click.echo(f"失败: {len(result.chapters_failed)} 章")
        click.echo(f"耗时: {result.total_duration_sec:.1f} 秒")

    except click.Abort:
        raise
    except _CLI_CATCHABLE as exc:
        raise click.ClickException(str(exc)) from exc


# ---------------------------------------------------------------------------
# Phase 8b: RAG index commands
# ---------------------------------------------------------------------------
register_index_commands(cli)
