"""V15 导入已有小说续写管线 CLI（Task 235 起）.

ingest   → 创建导入项目（projects + 主角 characters，指纹登记）
segment  → 规则切分源文件，产出可审查的章节边界清单
confirm  → 人工确认清单（回放闸门）
status   → 查看清单状态与回放闸门判定（退出码 0=可回放, 1=不可）
replay   → 逐章回放 settlement（幂等断点续跑，存在失败章时退出码 1）
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

import click

from songyan.agents.settlement_extractor import MAX_CONTENT_TOKENS
from songyan.db.migrations import init_schema
from songyan.db.repository import ProjectRepository
from songyan.exceptions import SongyanError
from songyan.genres.loader import list_genre_profiles
from songyan.models import ProjectSetting
from songyan.services.import_segment_service import (
    assert_replay_allowed,
    build_manifest,
    confirm_manifest,
    decode_source,
    load_manifest,
    write_segment_artifacts,
)
from songyan.utils.hashing import sha256_file


@click.group(name="import")
def import_group() -> None:
    """V15 导入已有小说续写管线."""


@import_group.command(name="ingest")
@click.option(
    "--source",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="源小说文件（txt/md）",
)
@click.option(
    "--title",
    default=None,
    help="项目标题（缺省取源文件名）",
)
@click.option(
    "--genre",
    "genre_id",
    required=True,
    help="体裁 ID（显式选择，不做自动猜测）",
)
@click.option(
    "--protagonist-name",
    required=True,
    help="主角名（建档时刻即入库，供 settlement 登记）",
)
@click.option(
    "--protagonist-background",
    default="",
    show_default=True,
    help="主角背景",
)
@click.option(
    "--mode",
    "mode_id",
    default="webnovel",
    show_default=True,
    help="创作模式 ID",
)
@click.option(
    "--words-per-chapter",
    default=3000,
    show_default=True,
    type=click.IntRange(min=1),
    help="每章目标字数",
)
def import_ingest_cmd(
    source: Path,
    title: str | None,
    genre_id: str,
    protagonist_name: str,
    protagonist_background: str,
    mode_id: str,
    words_per_chapter: int,
) -> None:
    """创建导入项目并登记源文件指纹（F1 主角建档前置，F8 显式选择体裁）."""
    try:
        decode_source(source.read_bytes())
    except SongyanError as exc:
        raise click.ClickException(str(exc)) from exc

    digest = sha256_file(source)

    available_genres = list_genre_profiles()
    if genre_id not in available_genres:
        raise click.ClickException(
            f"未知体裁: {genre_id}。可用体裁: {', '.join(available_genres)}"
        )

    project = ProjectSetting(
        title=title or source.stem,
        genre_id=genre_id,
        mode_id=mode_id,
        protagonist_name=protagonist_name,
        protagonist_background=protagonist_background,
        words_per_chapter=words_per_chapter,
        lifecycle_status="importing",
    )
    project_id = uuid.uuid4().hex

    async def _create() -> None:
        from songyan.workflows._helpers import ensure_protagonist_character

        await init_schema()
        await ProjectRepository().create(project, project_id)
        await ensure_protagonist_character(project_id, project)

    try:
        asyncio.run(_create())
    except SongyanError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"项目 ID   : {project_id}")
    click.echo(f"标题      : {project.title}")
    click.echo(f"体裁      : {genre_id}")
    click.echo(f"主角      : {protagonist_name}")
    click.echo(f"指纹      : {digest}")
    click.echo(f"生命周期  : {project.lifecycle_status}")
    click.echo(
        "下一步: songyan import segment --source <源文件> --output <目录>，"
        "人工审查并 confirm 后执行 "
        f"songyan import replay --project {project_id} --manifest <清单路径>"
    )


@import_group.command(name="segment")
@click.option(
    "--source",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="源小说文件（txt/md）",
)
@click.option(
    "--output",
    type=click.Path(file_okay=False, path_type=Path),
    required=True,
    help="切分产物输出目录",
)
@click.option(
    "--token-budget",
    default=MAX_CONTENT_TOKENS,
    show_default=True,
    type=click.IntRange(min=1),
    help="单章 token 预算（超出则在结果中列出）",
)
def import_segment_cmd(source: Path, output: Path, token_budget: int) -> None:
    """规则切分源文件，产出章节边界清单（需人工确认后才可回放）."""
    try:
        manifest, normalized, bodies = build_manifest(source.resolve(), token_budget=token_budget)
        manifest_path, overwrote_confirmed = write_segment_artifacts(
            output, manifest, normalized, bodies
        )
    except SongyanError as exc:
        raise click.ClickException(str(exc)) from exc
    if overwrote_confirmed:
        click.echo("注意：已覆盖先前已确认的清单，需重新人工确认")
    click.echo(f"源文件    : {source}（{manifest.encoding}）")
    click.echo(f"章节数    : {manifest.chapter_count}")
    if manifest.has_prologue:
        click.echo(f"前言      : {manifest.prologue_chars} 字（不会进入回放，请人工确认归属）")
    over = [b for b in manifest.boundaries if b.over_token_budget]
    if over:
        click.echo("超 token 预算章节（回放时尾部事实可能丢失，建议人工拆分）:")
        for b in over:
            click.echo(
                f"  第 {b.chapter_number} 章 {b.title}："
                f"约 {b.est_tokens} token > {manifest.token_budget}"
            )
    click.echo(f"清单      : {manifest_path}")
    click.echo("下一步: 人工审查 manifest.json 与 chapters/ 后执行 songyan import confirm")


@import_group.command(name="confirm")
@click.option(
    "--manifest",
    "manifest_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="manifest.json 路径",
)
def import_confirm_cmd(manifest_path: Path) -> None:
    """人工确认切分清单（确认后回放闸门放行）."""
    try:
        confirmed = confirm_manifest(manifest_path)
    except SongyanError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"已确认: {confirmed.chapter_count} 章，回放闸门已放行")


@import_group.command(name="status")
@click.option(
    "--manifest",
    "manifest_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="manifest.json 路径",
)
def import_status_cmd(manifest_path: Path) -> None:
    """查看清单状态与回放闸门判定.退出码 0=可回放, 1=不可."""
    try:
        manifest = load_manifest(manifest_path)
    except SongyanError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"状态      : {manifest.status}")
    click.echo(f"章节数    : {manifest.chapter_count}")
    click.echo(f"源文件    : {manifest.source_path}")
    try:
        assert_replay_allowed(manifest_path)
    except SongyanError as exc:
        click.echo(f"回放闸门  : 拒绝（{exc}）")
        raise SystemExit(1) from None
    click.echo("回放闸门  : 放行")


@import_group.command(name="replay")
@click.option(
    "--project",
    "project_id",
    required=True,
    help="项目 ID（ingest 回执中的项目 ID）",
)
@click.option(
    "--manifest",
    "manifest_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="manifest.json 路径（须已 confirm 放行）",
)
@click.option(
    "--chapters",
    default=None,
    help="只回放指定章节，逗号分隔章节号（如 1,2,3）；缺省回放全部",
)
@click.option(
    "--run-id",
    default=None,
    help="复用既有回放 run_id（断点续跑归并到同一 run）",
)
def import_replay_cmd(
    project_id: str,
    manifest_path: Path,
    chapters: str | None,
    run_id: str | None,
) -> None:
    """对已确认清单逐章回放 settlement.存在失败章时退出码 1."""
    from songyan.services.import_replay_service import replay_import

    chapter_set: set[int] | None = None
    if chapters is not None:
        try:
            chapter_set = {int(part) for part in chapters.split(",")}
        except ValueError:
            raise click.ClickException(
                f"无法解析 --chapters: {chapters!r}。"
                "正确格式为逗号分隔的章节号，例如: 1,2,3"
            ) from None

    try:
        report = asyncio.run(
            replay_import(
                project_id, manifest_path, chapters=chapter_set, run_id=run_id
            )
        )
    except SongyanError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(report.render_text())
    if report.by_status("failed"):
        raise SystemExit(1)


def register_import_commands(cli: click.Group) -> None:
    """注册 V15 导入管线命令."""
    cli.add_command(import_group)
