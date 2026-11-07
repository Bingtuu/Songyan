"""M3 variant CLI — step 1 ``list``; step 2 ``generate``; step 3 ``diff`` (no stubs)."""

from __future__ import annotations

import asyncio
import json

import click

from songyan.db.connection import get_db_path
from songyan.db.repository import ProjectRepository
from songyan.services.variant_diff import (
    MissingVariantSlotError,
    diff_variant_slots,
    list_variant_rows,
)
from songyan.services.variant_generate import generate_chapter_variants


class VariantSlotMissing(click.ClickException):
    """Missing variant slot — process exit 2 (tech-m3 §4.1 business reject)."""

    exit_code = 2


async def _ensure_project_readable(project_id: str) -> None:
    db_path = get_db_path()
    if not db_path.is_file():
        raise click.ClickException(f"找不到数据库文件: {db_path}")
    project = await ProjectRepository().get(project_id)
    if project is None:
        raise click.ClickException(f"项目不存在: {project_id}")


async def _list_variants(project_id: str, chapter: int) -> list[dict[str, object]]:
    await _ensure_project_readable(project_id)
    return await list_variant_rows(project_id, chapter)


async def _generate_variants(
    project_id: str,
    chapter: int,
    n: int,
    budget_cny: float | None,
) -> dict[str, object]:
    await _ensure_project_readable(project_id)
    result = await generate_chapter_variants(
        project_id,
        chapter,
        n=n,
        budget_cny=budget_cny,
    )
    return {
        "n": result.n_requested,
        "fingerprint": result.fingerprint,
        "budget_exhausted": result.budget_exhausted,
        "variants": [row.model_dump(mode="json") for row in result.variants],
    }


async def _diff_variants(
    project_id: str,
    chapter: int,
    slot_a: int,
    slot_b: int,
) -> dict[str, object]:
    await _ensure_project_readable(project_id)
    try:
        result = await diff_variant_slots(project_id, chapter, slot_a, slot_b)
    except MissingVariantSlotError as exc:
        raise VariantSlotMissing(str(exc)) from exc
    return {
        "chapter": result.chapter,
        "a": result.a,
        "b": result.b,
        "content_ref_a": result.content_ref_a,
        "content_ref_b": result.content_ref_b,
        "diff": result.diff,
    }


@click.group(name="variant")
def variant_group() -> None:
    """章内 Variant（抽卡）。子命令随 tech-m3 小步落地，无空桩。"""


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
            f"fp={row['fingerprint']} "
            f"ref={row['content_ref']} stale={row['stale_vs_canon']} "
            f"cost={row['cost_cny_estimate']}"
        )


@variant_group.command(name="generate")
@click.option("--project-id", required=True, help="项目 ID")
@click.option("--chapter", required=True, type=int, help="章号")
@click.option("--n", default=2, show_default=True, type=int, help="生成槽数（默认 2）")
@click.option(
    "--budget-cny",
    default=None,
    type=float,
    help="本命令费用预算（¥）；耗尽则保留已写槽并以退出码 3 结束",
)
@click.option("--json", "as_json", is_flag=True, help="JSON 输出")
@click.pass_context
def variant_generate(
    ctx: click.Context,
    project_id: str,
    chapter: int,
    n: int,
    budget_cny: float | None,
    as_json: bool,
) -> None:
    """生成 N 个章内草稿槽（默认 N=2）；只读 Canon；不自动 pick。"""
    if chapter < 1:
        raise click.ClickException("chapter 必须 >= 1")
    if n < 1:
        raise click.ClickException("n 必须 >= 1")
    if budget_cny is not None and budget_cny < 0:
        raise click.ClickException("budget-cny 必须 >= 0")

    payload = asyncio.run(
        _generate_variants(project_id, chapter, n=n, budget_cny=budget_cny)
    )
    variants = payload["variants"]
    assert isinstance(variants, list)

    if as_json:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        click.echo(
            f"generated={len(variants)}/{payload['n']} "
            f"fingerprint={str(payload['fingerprint'])[:12]}… "
            f"budget_exhausted={payload['budget_exhausted']}"
        )
        for row in variants:
            assert isinstance(row, dict)
            click.echo(
                f"- slot={row['slot_index']} status={row['status']} "
                f"ref={row['content_ref']} cost={row['cost_cny_estimate']}"
            )

    if payload["budget_exhausted"]:
        if not as_json:
            click.echo(
                f"预算耗尽：已写入 {len(variants)}/{payload['n']} 槽",
                err=True,
            )
        ctx.exit(3)


@variant_group.command(name="diff")
@click.option("--project-id", required=True, help="项目 ID")
@click.option("--chapter", required=True, type=int, help="章号")
@click.option("--a", "slot_a", required=True, type=int, help="槽 A（slot_index）")
@click.option("--b", "slot_b", required=True, type=int, help="槽 B（slot_index）")
@click.option("--json", "as_json", is_flag=True, help="JSON 输出")
def variant_diff(
    project_id: str,
    chapter: int,
    slot_a: int,
    slot_b: int,
    as_json: bool,
) -> None:
    """两槽正文 unified diff（只读）；缺槽退出码 2。"""
    if chapter < 1:
        raise click.ClickException("chapter 必须 >= 1")
    if slot_a < 1 or slot_b < 1:
        raise click.ClickException("slot --a/--b 必须 >= 1")

    payload = asyncio.run(_diff_variants(project_id, chapter, slot_a, slot_b))
    if as_json:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    click.echo(payload["diff"], nl=False)
    if not str(payload["diff"]).endswith("\n"):
        click.echo("")


def register_variant_commands(cli: click.Group) -> None:
    """Mount the ``variant`` group (only implemented subcommands)."""
    cli.add_command(variant_group)
