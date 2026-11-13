"""M3 variant CLI — list / generate / diff / pick / abandon (no stubs)."""

from __future__ import annotations

import asyncio
import json

import click

from songyan.db.connection import get_db_path
from songyan.db.repository import ProjectRepository
from songyan.exceptions import DuplicatePickedVariantError
from songyan.services.variant_diff import (
    MissingVariantSlotError,
    diff_variant_slots,
    list_variant_rows,
)
from songyan.services.variant_generate import (
    VariantGenerateLLMError,
    generate_chapter_variants,
)
from songyan.services.variant_pick import (
    AbandonPickedVariantError,
    FlaggedVariantPickError,
    PickAbandonedVariantError,
    StaleVariantPickError,
    abandon_variant_slot,
    pick_variant_slot,
)


class VariantBusinessReject(click.ClickException):
    """Business reject — process exit 2 (tech-m3 §4.1)."""

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
    try:
        result = await generate_chapter_variants(
            project_id,
            chapter,
            n=n,
            budget_cny=budget_cny,
        )
    except VariantGenerateLLMError as exc:
        # tech-m3 §4.2 #4：失败信息进退出码/stderr；已写槽已保留（exit 1）
        raise click.ClickException(
            f"模型调用失败（已保留 {exc.written_slots} 个已生成槽）：{exc}"
        ) from exc
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
        raise VariantBusinessReject(str(exc)) from exc
    return {
        "chapter": result.chapter,
        "a": result.a,
        "b": result.b,
        "content_ref_a": result.content_ref_a,
        "content_ref_b": result.content_ref_b,
        "diff": result.diff,
    }


async def _pick_variant(
    project_id: str,
    chapter: int,
    slot: int,
    *,
    allow_stale: bool,
) -> dict[str, object]:
    await _ensure_project_readable(project_id)
    try:
        result = await pick_variant_slot(
            project_id, chapter, slot, allow_stale=allow_stale
        )
    except MissingVariantSlotError as exc:
        raise VariantBusinessReject(str(exc)) from exc
    except StaleVariantPickError as exc:
        raise VariantBusinessReject(str(exc)) from exc
    except PickAbandonedVariantError as exc:
        raise VariantBusinessReject(str(exc)) from exc
    except FlaggedVariantPickError as exc:
        raise VariantBusinessReject(str(exc)) from exc
    except DuplicatePickedVariantError as exc:
        raise VariantBusinessReject(str(exc)) from exc
    row = result.variant
    return {
        "slot_index": row.slot_index,
        "status": row.status,
        "content_ref": row.content_ref,
        "current_version_id": result.current_version_id,
        "variant_id": row.variant_id,
        "stale_vs_canon": row.stale_vs_canon,
        "stale_vs_storyline": row.stale_vs_storyline,
        "archived_variant_id": result.archived_variant_id,
        "allow_stale": allow_stale,
    }


async def _abandon_variant(
    project_id: str,
    chapter: int,
    slot: int,
) -> dict[str, object]:
    await _ensure_project_readable(project_id)
    try:
        result = await abandon_variant_slot(project_id, chapter, slot)
    except MissingVariantSlotError as exc:
        raise VariantBusinessReject(str(exc)) from exc
    except AbandonPickedVariantError as exc:
        raise VariantBusinessReject(str(exc)) from exc
    row = result.variant
    return {
        "slot_index": row.slot_index,
        "status": row.status,
        "content_ref": row.content_ref,
        "variant_id": row.variant_id,
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
        flag = f" flag={row['quality_flag']}" if row.get("quality_flag") else ""
        click.echo(
            f"- slot={row['slot_index']} status={row['status']} "
            f"fp={row['fingerprint']} "
            f"ref={row['content_ref']} stale_vs_canon={row['stale_vs_canon']} "
            f"slStale={row['stale_vs_storyline']} "
            f"cost={row['cost_cny_estimate']}{flag}"
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
            flag = f" flag={row['quality_flag']}" if row.get("quality_flag") else ""
            click.echo(
                f"- slot={row['slot_index']} status={row['status']} "
                f"ref={row['content_ref']} cost={row['cost_cny_estimate']}{flag}"
            )

    # task 245：拒写/占位质量门——全槽失败 exit 2；部分失败 stderr 列出失败槽。
    failed_slots = [
        row for row in variants
        if isinstance(row, dict) and row.get("quality_flag")
    ]
    if variants and len(failed_slots) == len(variants):
        click.echo(
            f"全部 {len(failed_slots)} 槽被拒写/占位判定拒绝"
            f"（quality_flag："
            f"{', '.join(str(r['quality_flag']) for r in failed_slots)}）；"
            f"请补充事实后重抽",
            err=True,
        )
        ctx.exit(2)
    for row in failed_slots:
        click.echo(
            f"slot {row['slot_index']} 判失败：{row['quality_flag']}",
            err=True,
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


@variant_group.command(name="pick")
@click.option("--project-id", required=True, help="项目 ID")
@click.option("--chapter", required=True, type=int, help="章号")
@click.option("--slot", required=True, type=int, help="槽号（slot_index）")
@click.option(
    "--allow-stale",
    is_flag=True,
    help="允许 pick 已 stale_vs_canon=1 的槽（仍不写 Canon）",
)
@click.option("--json", "as_json", is_flag=True, help="JSON 输出")
def variant_pick(
    project_id: str,
    chapter: int,
    slot: int,
    allow_stale: bool,
    as_json: bool,
) -> None:
    """选用一槽：移动工作正文指针；不写 Canon / plan_*。"""
    if chapter < 1:
        raise click.ClickException("chapter 必须 >= 1")
    if slot < 1:
        raise click.ClickException("slot 必须 >= 1")

    payload = asyncio.run(
        _pick_variant(project_id, chapter, slot, allow_stale=allow_stale)
    )
    if as_json:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    click.echo(
        f"picked slot={payload['slot_index']} "
        f"ref={payload['content_ref']} "
        f"current_version_id={payload['current_version_id']} "
        f"stale_vs_canon={payload['stale_vs_canon']}"
    )
    if int(payload.get("stale_vs_storyline") or 0) == 1:
        click.echo(
            "提醒：该槽基于已演进的故事线草稿（stale_vs_storyline=1），请人工斟酌",
            err=True,
        )


@variant_group.command(name="abandon")
@click.option("--project-id", required=True, help="项目 ID")
@click.option("--chapter", required=True, type=int, help="章号")
@click.option("--slot", required=True, type=int, help="槽号（slot_index）")
@click.option("--json", "as_json", is_flag=True, help="JSON 输出")
def variant_abandon(
    project_id: str,
    chapter: int,
    slot: int,
    as_json: bool,
) -> None:
    """软删除一槽（status→abandoned）；不清空正文；拒 abandon 当前 picked。"""
    if chapter < 1:
        raise click.ClickException("chapter 必须 >= 1")
    if slot < 1:
        raise click.ClickException("slot 必须 >= 1")

    payload = asyncio.run(_abandon_variant(project_id, chapter, slot))
    if as_json:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    click.echo(
        f"abandoned slot={payload['slot_index']} ref={payload['content_ref']}"
    )


def register_variant_commands(cli: click.Group) -> None:
    """Mount the ``variant`` group (only implemented subcommands)."""
    cli.add_command(variant_group)
