"""CLI 入口（Click 框架）."""

from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path
from typing import Any, Literal, cast

import click

from songyan.cli.commands.index import register_index_commands
from songyan.cli.outline_import import load_outline_file
from songyan.config import settings
from songyan.creative_modes.registry import (
    list_creative_mode_profiles,
    load_creative_mode_profile,
)
from songyan.db.continuity_repo import ContinuityReportRepository
from songyan.db.human_mark_repo import HumanMarkRepository
from songyan.db.llm_call_usage_repo import LlmCallUsageRepository
from songyan.db.migrations import init_schema
from songyan.db.narrative_repo import NarrativeRepository
from songyan.db.repository import ProjectRepository
from songyan.evals.cost_report import render_cost_section
from songyan.evals.streaming_report import generate_report, read_run_logs, write_report
from songyan.exceptions import SongyanError
from songyan.genres.loader import list_genre_profiles, load_genre_profile
from songyan.models.gate_config import GateConfig
from songyan.models.human_mark import HumanMark
from songyan.models.project import ProjectSetting, derive_arc_boundaries
from songyan.project_templates import ProjectInitializer, ProjectTemplateLoader
from songyan.services.backup_service import backup_project, restore_backup
from songyan.services.doctor_service import DoctorReport, run_doctor, run_run_preflight
from songyan.services.export_service import (
    ExportFormat,
    ExportResult,
    GroupBy,
    export_project,
    parse_chapter_range,
)
from songyan.services.profile_service import (
    get_profile_view,
    load_override_json,
    merge_override_inputs,
    parse_set_expression,
    render_profile_view,
    upsert_profile_overrides,
)
from songyan.services.recovery_service import (
    advice_for_backup_error,
    advice_for_doctor_checks,
    advice_for_export_error,
    advice_for_restore_error,
    missing_artifact_advice,
    preflight_failed_advice,
    render_recovery_advice,
    run_failed_advice,
)
from songyan.services.run_bundle_service import bundle_run
from songyan.utils.logging_setup import configure_logging
from songyan.utils.process_exit import force_exit_after_run_if_requested
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
    configure_logging(settings.log_level, file_level=settings.log_file_level)


def _select_mode() -> str:
    """交互式选择创作模式，返回 mode_id."""
    modes = list_creative_mode_profiles()
    click.echo("\n选择创作模式:")
    for idx, mode_id in enumerate(modes, start=1):
        profile = load_creative_mode_profile(mode_id)
        click.echo(f"  {idx}. {mode_id} — {profile.name}")

    while True:
        choice: int = click.prompt("请输入序号", type=int)
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
        choice: int = click.prompt("请输入序号", type=int)
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
        choice: int = click.prompt("请输入序号", default=4, type=int)
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

    choice: int = click.prompt("请输入序号", default=0, type=int)
    if 1 <= choice <= len(profile.sub_genres):
        return profile.sub_genres[choice - 1].sub_genre_id
    return None


def _render_doctor_report(report: DoctorReport) -> str:
    """Render doctor report as human-readable text."""
    lines = ["Songyan doctor", ""]
    for check in report.checks:
        lines.append(f"[{check.status.upper()}] {check.id}: {check.message}")
        if check.hint:
            lines.append(f"  hint: {check.hint}")
    summary = report.summary
    lines.append("")
    lines.append(
        f"Summary: {summary['pass']} PASS, {summary['warn']} WARN, {summary['fail']} FAIL"
    )
    if report.status == "fail":
        recovery = render_recovery_advice(advice_for_doctor_checks(report.checks))
        if recovery:
            lines.append(recovery)
    return "\n".join(lines)


def _render_preflight_report(report: DoctorReport) -> str:
    """Render run preflight failures as human-readable text."""
    lines = ["Songyan run preflight", ""]
    for check in report.checks:
        if check.status == "pass":
            continue
        lines.append(f"[{check.status.upper()}] {check.id}: {check.message}")
        if check.hint:
            lines.append(f"  hint: {check.hint}")
    summary = report.summary
    lines.append("")
    lines.append(
        f"Summary: {summary['pass']} PASS, {summary['warn']} WARN, {summary['fail']} FAIL"
    )
    recovery_advices = advice_for_doctor_checks(report.checks)
    if recovery_advices:
        lines.append(
            render_recovery_advice([preflight_failed_advice(), *recovery_advices])
        )
    return "\n".join(lines)


@cli.command(name="doctor")
@click.option("--json", "json_output", is_flag=True, help="输出机器可读 JSON")
@click.option("--check-llm", is_flag=True, help="显式执行 LLM 客户端初始化探针")
@click.option("--init-db", is_flag=True, help="初始化/迁移当前 DATABASE_URL 指向的 SQLite DB")
def doctor(json_output: bool, check_llm: bool, init_db: bool) -> None:
    """检查 Songyan 本地运行环境."""
    report = asyncio.run(run_doctor(check_llm=check_llm, init_db=init_db))
    if json_output:
        click.echo(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        click.echo(_render_doctor_report(report))
    if report.status == "fail":
        raise click.exceptions.Exit(1)


@cli.group(name="profile")
def profile_cli() -> None:
    """GenreRuntimeProfile 调参工具."""
    pass


@profile_cli.command(name="show")
@click.option("--genre", required=True, help="体裁 ID")
@click.option("--json", "json_output", is_flag=True, help="输出机器可读 JSON")
def profile_show(genre: str, json_output: bool) -> None:
    """展示 registry / DB override / effective 三列 Profile."""
    try:
        view = asyncio.run(get_profile_view(genre))
    except click.Abort:
        raise
    except SongyanError as exc:
        raise click.ClickException(str(exc)) from exc
    except _CLI_CATCHABLE as exc:
        raise click.ClickException(str(exc)) from exc

    if json_output:
        click.echo(json.dumps(view.to_dict(), ensure_ascii=False, indent=2))
    else:
        click.echo(render_profile_view(view))


@profile_cli.command(name="diff")
@click.option("--genre", required=True, help="体裁 ID")
@click.option("--json", "json_output", is_flag=True, help="输出机器可读 JSON")
def profile_diff(genre: str, json_output: bool) -> None:
    """展示 DB override 对 effective Profile 造成的差异."""
    try:
        view = asyncio.run(get_profile_view(genre))
    except click.Abort:
        raise
    except SongyanError as exc:
        raise click.ClickException(str(exc)) from exc
    except _CLI_CATCHABLE as exc:
        raise click.ClickException(str(exc)) from exc

    if json_output:
        click.echo(json.dumps(view.to_dict(diff_only=True), ensure_ascii=False, indent=2))
    else:
        click.echo(render_profile_view(view, diff_only=True))


@profile_cli.command(name="upsert")
@click.option("--genre", required=True, help="体裁 ID（必须是注册表已知体裁）")
@click.option(
    "--set",
    "set_values",
    multiple=True,
    help="覆盖字段，格式 key=value；支持 dot path，如 continuity.health_overdue_weight=0.2",
)
@click.option(
    "--from-json",
    "json_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="覆盖意图 JSON 文件（不是 effective profile 全量 JSON）",
)
@click.option("--reset", is_flag=True, help="清空 DB override 意图，effective 回到 registry")
@click.option("--json", "json_output", is_flag=True, help="输出机器可读 JSON")
def profile_upsert(
    genre: str,
    set_values: tuple[str, ...],
    json_path: Path | None,
    reset: bool,
    json_output: bool,
) -> None:
    """写入 GenreRuntimeProfile DB override."""
    try:
        if reset and (set_values or json_path):
            raise click.ClickException("--reset 不能与 --set / --from-json 同时使用")
        json_overrides = load_override_json(json_path) if json_path else None
        set_items = [parse_set_expression(item) for item in set_values]
        overrides = merge_override_inputs(json_overrides, set_items)
        asyncio.run(init_schema())
        view = asyncio.run(
            upsert_profile_overrides(
                genre,
                overrides,
                reset=reset,
            )
        )
    except click.Abort:
        raise
    except SongyanError as exc:
        raise click.ClickException(str(exc)) from exc
    except _CLI_CATCHABLE as exc:
        raise click.ClickException(str(exc)) from exc

    if json_output:
        click.echo(json.dumps(view.to_dict(diff_only=True), ensure_ascii=False, indent=2))
    else:
        click.echo(f"profile override updated: {genre}")
        click.echo(render_profile_view(view, diff_only=True))


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
        story_structure=cast(Literal["three_act", "five_act", "serial", "free"], story_structure),
        sub_genre_id=sub_genre_id,
        arc_boundaries=arc_boundaries,
        arc_boundaries_auto=arc_boundaries_auto,
    )

    project_id = uuid.uuid4().hex
    repo = ProjectRepository()
    await repo.create(project, project_id)

    # Task 170e: 建项目时即补建 protagonist Character，让 DialogueStyleCard 声纹机制有落点
    from songyan.workflows._helpers import ensure_protagonist_character

    await ensure_protagonist_character(project_id, project)

    # Task 142: 可选大纲导入（缺省不执行，保持旧行为逐字节等价）
    if outline_file:
        outline, arcs, threads = load_outline_file(outline_file, project_id)
        await NarrativeRepository().import_outline(project_id, outline, arcs, threads)
        click.echo(
            f"  已导入大纲: {len(arcs)} 个弧规划, {len(threads)} 条线索"
        )

    return project_id, project


async def _create_project_from_template(
    template_id: str, outline_file: str | None
) -> tuple[str, ProjectSetting]:
    await init_schema()
    template = ProjectTemplateLoader().load(template_id)

    if outline_file:
        outline, arcs, threads = load_outline_file(outline_file, "dummy")
        template.set_outline(outline, arcs, threads)

    project_id, project = await ProjectInitializer.from_template(template)
    return project_id, project


@cli.command()
@click.option(
    "--outline-file",
    type=click.Path(exists=True),
    default=None,
    help="可选：全书大纲 JSON 文件，导入 StoryOutline/ArcPlan/PlotThread",
)
@click.option(
    "--template",
    "template_id",
    default=None,
    help="使用项目模板 ID 一键创建",
)
def create_project(outline_file: str | None, template_id: str | None) -> None:
    """交互式创建小说项目，或 --template 使用模板."""
    try:
        if template_id:
            project_id, project = asyncio.run(
                _create_project_from_template(template_id, outline_file)
            )
        else:
            project_id, project = asyncio.run(_create_project_async(outline_file))
    except click.Abort:
        raise
    except SongyanError as exc:
        raise click.ClickException(str(exc)) from exc
    except _CLI_CATCHABLE as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"\n[OK] 项目已创建: {project_id}")
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
            mark_type=cast(
                Literal["setting", "character", "foreshadowing", "item", "custom"], mark_type
            ),
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


async def _list_projects_async() -> list[dict[str, Any]]:
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


async def _run_export_project(
    project_id: str,
    *,
    output_dir: Path,
    fmt: ExportFormat,
    by: GroupBy,
    chapters: tuple[int, int] | None,
) -> ExportResult:
    return await export_project(
        project_id,
        output_dir=output_dir,
        fmt=fmt,
        by=by,
        chapters=chapters,
    )


@cli.command(name="export")
@click.option("--project-id", required=True, help="项目 ID")
@click.option(
    "--format",
    "fmt",
    default="md",
    show_default=True,
    type=click.Choice(["md", "txt"]),
    help="导出格式",
)
@click.option(
    "--by",
    "group_by",
    default="flat",
    show_default=True,
    type=click.Choice(["flat", "arc", "volume"]),
    help="导出分组方式",
)
@click.option("--chapters", default=None, help="章节范围，如 1-100；留空导出全部 accepted 章")
@click.option(
    "--output",
    "output_dir",
    default=Path("exports"),
    show_default=True,
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    help="输出目录",
)
def export_cmd(
    project_id: str,
    fmt: str,
    group_by: str,
    chapters: str | None,
    output_dir: Path,
) -> None:
    """导出 accepted head 正文为纯净书稿."""
    try:
        chapter_range = parse_chapter_range(chapters)
        exported = asyncio.run(
            _run_export_project(
                project_id,
                output_dir=output_dir,
                fmt=cast(ExportFormat, fmt),
                by=cast(GroupBy, group_by),
                chapters=chapter_range,
            )
        )
    except click.Abort:
        raise
    except SongyanError as exc:
        recovery = render_recovery_advice(
            advice_for_export_error(str(exc), project_id)
        )
        message = str(exc) + (recovery if recovery else "")
        raise click.ClickException(message) from exc
    except _CLI_CATCHABLE as exc:
        raise click.ClickException(str(exc)) from exc

    total_chapters = sum(item.chapter_count for item in exported.files)
    click.echo(f"已导出 {total_chapters} 章到 {len(exported.files)} 个文件:")
    if exported.skipped_count:
        click.echo(
            f"已跳过 {exported.skipped_count} 章（accepted head 指向的版本缺失或不匹配）"
        )
    for item in exported.files:
        click.echo(f"  {item.path} ({item.chapter_count} 章)")


@cli.command(name="backup")
@click.option("--project-id", required=True, help="要备份的项目 ID")
@click.option(
    "--output",
    "output_path",
    default=Path("backups"),
    show_default=True,
    type=click.Path(path_type=Path),
    help="输出目录或 .zip 文件路径",
)
def backup_cmd(project_id: str, output_path: Path) -> None:
    """备份项目资产为 zip 包（DB 快照 + manifest + 运行摘要 + 日志索引）."""
    try:
        result = asyncio.run(backup_project(project_id, output=output_path))
    except click.Abort:
        raise
    except SongyanError as exc:
        recovery = render_recovery_advice(advice_for_backup_error(str(exc)))
        message = str(exc) + (recovery if recovery else "")
        raise click.ClickException(message) from exc
    except _CLI_CATCHABLE as exc:
        raise click.ClickException(str(exc)) from exc

    manifest = result.manifest
    project = manifest["project"]
    schema = manifest["schema"]
    click.echo(f"备份已生成: {result.backup_path}")
    click.echo(f"  project_id: {project['project_id']}")
    click.echo(f"  标题: {project.get('title') or '(未命名)'}")
    click.echo(f"  schema: {schema['status']} (version={schema['schema_version']})")
    click.echo(f"  runs: {manifest['runs']['count']}")
    click.echo("  sensitive: .env/api_key/log_content not included")


@cli.command(name="restore")
@click.option(
    "--backup",
    "backup_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="由 songyan backup 生成的 zip 文件",
)
@click.option(
    "--database-url",
    required=True,
    help="恢复目标 SQLite URL，例如 sqlite:///restored.db",
)
@click.option("--force", is_flag=True, help="允许覆盖已存在的目标 DB")
def restore_cmd(backup_path: Path, database_url: str, force: bool) -> None:
    """从备份资产包恢复 SQLite DB，并执行 schema 校验."""
    try:
        result = asyncio.run(
            restore_backup(backup_path, database_url=database_url, force=force)
        )
    except click.Abort:
        raise
    except SongyanError as exc:
        recovery = render_recovery_advice(advice_for_restore_error(str(exc)))
        message = str(exc) + (recovery if recovery else "")
        raise click.ClickException(message) from exc
    except _CLI_CATCHABLE as exc:
        raise click.ClickException(str(exc)) from exc

    project = result.manifest["project"]
    schema = result.schema
    click.echo(f"恢复完成: {result.database_path}")
    click.echo(f"  project_id: {project['project_id']}")
    click.echo(f"  标题: {project.get('title') or '(未命名)'}")
    click.echo(f"  schema: {schema['status']} (version={schema['schema_version']})")
    click.echo("")
    click.echo("下一步:")
    click.echo(f"  $env:DATABASE_URL = \"{database_url}\"")
    click.echo("  songyan doctor --json")
    click.echo("  songyan list-projects")


@cli.command(name="bundle-run")
@click.option("--run-id", required=True, help="要打包诊断信息的 run_id")
@click.option("--project-id", default=None, help="可选：校验 run 所属 project_id")
@click.option(
    "--output",
    "output_path",
    default=Path("bundles"),
    show_default=True,
    type=click.Path(path_type=Path),
    help="输出目录或 .zip 文件路径",
)
def bundle_run_cmd(run_id: str, project_id: str | None, output_path: Path) -> None:
    """生成可分享的 run 诊断包（JSON + Markdown + 日志索引）."""
    try:
        result = asyncio.run(
            bundle_run(run_id, project_id=project_id, output=output_path)
        )
    except click.Abort:
        raise
    except SongyanError as exc:
        message = str(exc)
        if "run log not found" in message:
            recovery = render_recovery_advice([missing_artifact_advice(run_id)])
            message += recovery if recovery else ""
        raise click.ClickException(message) from exc
    except _CLI_CATCHABLE as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"诊断包已生成: {result.bundle_path}")
    click.echo(f"  run_id: {result.bundle['run']['run_id']}")
    click.echo(f"  project_id: {result.bundle['run']['project_id']}")
    click.echo(f"  files: {', '.join(['bundle.json', 'bundle.md', 'logs/index.json'])}")
    click.echo("  sensitive: api_key/env/log_content/manuscript_content not included")


async def _resolve_run_mode_id(project_id: str, explicit_mode_id: str | None) -> str:
    """Resolve the effective mode for ``songyan run``.

    CLI input has priority.  When omitted, the project setting stored in
    SQLite is authoritative.
    """
    if explicit_mode_id:
        return explicit_mode_id

    project = await ProjectRepository().get(project_id)
    if project is None or not project.mode_id:
        raise click.ClickException(
            f"无法读取项目 mode_id：project_id={project_id}；"
            "请检查项目 ID，或显式传入 --mode-id。"
        )
    return project.mode_id


@cli.command()
@click.option("--project-id", required=True, help="项目 ID")
@click.option("--chapters", required=True, help="章节范围，如 1-10")
@click.option(
    "--mode-id",
    default=None,
    help="创作模式 ID；不传则使用项目默认 mode_id",
)
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
@click.option(
    "--on-failure",
    default="isolate",
    type=click.Choice(["abort", "retry", "isolate"]),
    help="单章失败策略：isolate 隔离并继续（默认），abort 终止整批，retry 重试一次",
)
@click.option(
    "--resume",
    is_flag=True,
    help="复用该项目最近一次未完成的 run 进行断点续跑",
)
@click.option(
    "--run-id",
    default=None,
    help="显式指定要续跑的 run_id（优先级高于 --resume）",
)
def run(
    project_id: str,
    chapters: str,
    mode_id: str | None,
    human_gates: str,
    auto_confirm: bool,
    rag_mode: str | None,
    skip_rag: bool,
    gate_mode: str,
    on_failure: str,
    resume: bool,
    run_id: str | None,
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

        gate_config = GateConfig.for_mode(cast(Literal["observe", "enforce"], gate_mode))
        click.echo(f"门禁模式: {gate_mode}")
        preflight = asyncio.run(run_run_preflight(project_id=project_id))
        if preflight.status == "fail":
            click.echo(_render_preflight_report(preflight))
            raise click.exceptions.Exit(1)

        effective_mode_id = asyncio.run(_resolve_run_mode_id(project_id, mode_id))

        result = asyncio.run(
            run_project_pipeline(
                project_id=project_id,
                chapter_range=chapter_range,
                mode_id=effective_mode_id,
                auto_confirm=auto_confirm,
                gate_config=gate_config,
                on_failure=on_failure,
                resume=resume,
                run_id=run_id,
            )
        )

        total_chapters = len(result.chapters_completed) + len(result.chapters_failed)
        click.echo(f"\n运行完成: {len(result.chapters_completed)}/{total_chapters} 章成功")
        if result.chapters_failed:
            click.echo(f"失败: {result.chapters_failed}")  # 列出失败章号清单
        click.echo(f"耗时: {result.total_duration_sec:.1f} 秒")
        click.echo(f"run_id: {result.run_id}")
        exit_code = (
            0
            if result.final_status == "completed" and not result.chapters_failed
            else 1
        )
        if exit_code:
            click.echo(render_recovery_advice([run_failed_advice(result.run_id)]))
        force_exit_after_run_if_requested(exit_code=exit_code)
        if exit_code:
            raise click.exceptions.Exit(exit_code)

    except click.Abort:
        raise
    except click.exceptions.Exit:
        raise
    except _CLI_CATCHABLE as exc:
        raise click.ClickException(str(exc)) from exc


# ---------------------------------------------------------------------------
# Task 119: Streaming report command
# ---------------------------------------------------------------------------


def _render_cost_section(run_id: str) -> str:
    """读取 llm_call_usage 遥测并渲染 report 成本段（Task 175 阶段 C）.

    取数失败（如旧库缺 llm_call_usage 表、DB 锁死/schema 漂移）只告警并在
    报告中渲染可区分的「成本数据读取失败」行——不伪装成良性「无成本数据」
    旧 run；成本段是遥测视图，报告主流程不可断。
    """

    async def _fetch() -> tuple[dict[str, Any], dict[str, int]]:
        repo = LlmCallUsageRepository()
        aggregate = await repo.aggregate_for_run(run_id)
        source_stats = await repo.source_stats_for_run(run_id)
        return aggregate, source_stats

    try:
        aggregate, source_stats = asyncio.run(_fetch())
    except Exception as exc:  # 遥测视图降级：旧库缺表 / DB 不可用，不阻断报告
        click.echo(f"警告: 成本数据读取失败（{exc}）")
        return "\n" + render_cost_section(
            {"per_chapter": [], "per_agent": []},
            {
                "total_usage_rows": 0,
                "total_calls": 0,
                "token_estimate_calls": 0,
                "cost_pricing_estimate_calls": 0,
            },
            error=str(exc),
        )
    return "\n" + render_cost_section(aggregate, source_stats)


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
            click.echo(f"错误: 未找到运行日志 logs/chapter_runs/{run_id}.jsonl")
            click.echo(render_recovery_advice([missing_artifact_advice(run_id)]))
            raise click.exceptions.Exit(1)

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

        # Task 175 阶段 C: 追加 LLM 成本视图段（SQLite usage 遥测；取数失败降级，不阻断报告）
        report_md += _render_cost_section(run_id)

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
    except click.exceptions.Exit:
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
