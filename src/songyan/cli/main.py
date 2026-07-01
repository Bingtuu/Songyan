"""CLI 入口（Click 框架）."""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

import click

from songyan.cli.commands.index import register_index_commands
from songyan.cli.outline_import import load_outline_file
from songyan.creative_modes.registry import (
    list_creative_mode_profiles,
    load_creative_mode_profile,
)
from songyan.db.continuity_repo import ContinuityReportRepository
from songyan.db.human_mark_repo import HumanMarkRepository
from songyan.db.migrations import init_schema
from songyan.db.narrative_repo import NarrativeRepository
from songyan.db.repository import ProjectRepository
from songyan.evals.streaming_report import generate_report, read_run_logs, write_report
from songyan.exceptions import SongyanError
from songyan.genres.loader import list_genre_profiles, load_genre_profile
from songyan.models.gate_config import GateConfig
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


async def _create_project_async(outline_file: str | None = None) -> tuple[str, ProjectSetting]:
    """异步执行项目创建逻辑.

    Args:
        outline_file: 可选的全书大纲 JSON 文件路径。缺省（None）时项目创建行为
            与现状完全一致，不写任何叙事骨架表。
    """
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

    # Task 142: 可选大纲导入（缺省不执行，保持旧行为逐字节等价）
    if outline_file:
        outline, arcs, threads = load_outline_file(outline_file, project_id)
        await NarrativeRepository().import_outline(project_id, outline, arcs, threads)
        click.echo(
            f"  已导入大纲: {len(arcs)} 个弧规划, {len(threads)} 条线索"
        )

    return project_id, project


@cli.command()
@click.option(
    "--outline-file",
    type=click.Path(exists=True),
    default=None,
    help="可选：全书大纲 JSON 文件，导入 StoryOutline/ArcPlan/PlotThread",
)
def create_project(outline_file: str | None) -> None:
    """交互式创建小说项目（可选 --outline-file 导入全书大纲）."""
    try:
        project_id, project = asyncio.run(_create_project_async(outline_file))
    except click.Abort:
        raise
    except SongyanError as exc:
        raise click.ClickException(str(exc)) from exc
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
@click.option(
    "--gate-mode",
    default="enforce",
    type=click.Choice(["observe", "enforce"]),
    help="候选硬门禁模式：enforce 触发即暂停 run（默认），observe 只记录不暂停",
)
def run(
    project_id: str,
    chapters: str,
    mode_id: str,
    human_gates: str,
    auto_confirm: bool,
    rag_mode: str | None,
    skip_rag: bool,
    gate_mode: str,
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

        gate_config = GateConfig.for_mode(gate_mode)
        click.echo(f"门禁模式: {gate_mode}")

        result = asyncio.run(
            run_project_pipeline(
                project_id=project_id,
                chapter_range=chapter_range,
                mode_id=mode_id,
                auto_confirm=auto_confirm,
                gate_config=gate_config,
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
# Task 119: Streaming report command
# ---------------------------------------------------------------------------


@cli.command(name="report")
@click.option(
    "--run-id",
    required=True,
    help="运行 ID（从 logs/chapter_runs/<run_id>.jsonl 读取）",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="输出 markdown 路径（默认 logs/reports/report-<run_id>.md）",
)
@click.option(
    "--start",
    type=int,
    default=None,
    help="章节范围起始（默认从 JSONL 自动推断）",
)
@click.option(
    "--end",
    type=int,
    default=None,
    help="章节范围结束（默认从 JSONL 自动推断）",
)
def report_cmd(
    run_id: str,
    output: Path | None,
    start: int | None,
    end: int | None,
) -> None:
    """从 JSONL 运行日志生成流式验证 markdown 报告。

    示例:
        songyan report --run-id run-8e14bcf1
        songyan report --run-id run-8e14bcf1 -o logs/reports/my-report.md
    """
    try:
        logs = read_run_logs(run_id)
        if not logs:
            click.echo("警告: 未从 JSONL 中读取到任何日志记录")
            return

        # 确定章节范围
        chapter_range: tuple[int, int] | None = None
        if start is not None and end is not None:
            chapter_range = (start, end)
        else:
            chapter_range = (
                min(getattr(log_, "chapter_number", 0) for log_ in logs),
                max(getattr(log_, "chapter_number", 0) for log_ in logs),
            )

        report_md = generate_report(logs, chapter_range=chapter_range)

        # 一致性检查警告
        missing_budget = [
            getattr(log_, "chapter_number", "?")
            for log_ in logs
            if getattr(log_, "success", False) and getattr(log_, "budget_used", None) is None
        ]
        if missing_budget:
            click.echo(f"警告: 以下成功章节缺少 budget_used: {missing_budget}")

        emergency_chapters = [
            getattr(log_, "chapter_number", "?")
            for log_ in logs
            if getattr(log_, "context_emergency", False)
        ]
        if emergency_chapters:
            click.echo(f"警告: 以下章节触发了 ContextEmergency: {emergency_chapters}")

        # 写入文件
        if output:
            output_path = write_report(report_md, run_id, output.parent)
        else:
            output_path = write_report(report_md, run_id, Path("logs/reports"))

        click.echo(f"报告已生成: {output_path}")

    except click.Abort:
        raise
    except _CLI_CATCHABLE as exc:
        raise click.ClickException(str(exc)) from exc


@cli.command(name="metrics")
@click.option("--project-id", required=True, help="项目 ID（从 SQLite 事实源读逐章度量）")
@click.option("--chapters", required=True, help="章节范围，如 1-150")
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="输出 markdown 路径（默认 logs/reports/metrics-<project_id>.md）",
)
def metrics_cmd(project_id: str, chapters: str, output: Path | None) -> None:
    """从 SQLite 事实源生成 V6 阶段 A 长期度量报告（DB 支撑，可复算历史 DB）。

    示例:
        songyan metrics --project-id mynovel --chapters 1-150
        # 复算历史库：先用 DATABASE_URL 覆盖指向 .tmp/task138n_ch1_ch30_rerun.db
    """
    from songyan.evals.db_metrics import render_stage_a_metrics

    try:
        if "-" in chapters:
            start_s, end_s = chapters.split("-", 1)
            start, end = int(start_s), int(end_s)
        else:
            start = end = int(chapters)

        report_md = asyncio.run(render_stage_a_metrics(project_id, start, end))

        out_dir = output.parent if output else Path("logs/reports")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = output if output else out_dir / f"metrics-{project_id}.md"
        out_path.write_text(report_md, encoding="utf-8")
        click.echo(f"度量报告已生成: {out_path}")

    except click.Abort:
        raise
    except _CLI_CATCHABLE as exc:
        raise click.ClickException(str(exc)) from exc


# ---------------------------------------------------------------------------
# Phase 8b: RAG index commands
# ---------------------------------------------------------------------------
register_index_commands(cli)
