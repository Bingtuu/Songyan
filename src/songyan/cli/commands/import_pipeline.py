"""V15 导入已有小说续写管线 CLI（Task 235 起）.

segment  → 规则切分源文件，产出可审查的章节边界清单
confirm  → 人工确认清单（回放闸门）
status   → 查看清单状态与回放闸门判定（退出码 0=可回放, 1=不可）
"""

from __future__ import annotations

from pathlib import Path

import click

from songyan.agents.settlement_extractor import MAX_CONTENT_TOKENS
from songyan.exceptions import SongyanError
from songyan.services.import_segment_service import (
    assert_replay_allowed,
    build_manifest,
    confirm_manifest,
    load_manifest,
    write_segment_artifacts,
)


@click.group(name="import")
def import_group() -> None:
    """V15 导入已有小说续写管线."""


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
    type=int,
    help="单章 token 预算（超出则在结果中列出）",
)
def import_segment_cmd(source: Path, output: Path, token_budget: int) -> None:
    """规则切分源文件，产出章节边界清单（需人工确认后才可回放）."""
    try:
        manifest, normalized, bodies = build_manifest(source.resolve(), token_budget=token_budget)
        manifest_path = write_segment_artifacts(output, manifest, normalized, bodies)
    except SongyanError as exc:
        raise click.ClickException(str(exc)) from exc
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


def register_import_commands(cli: click.Group) -> None:
    """注册 V15 导入管线命令."""
    cli.add_command(import_group)
