"""M1 steps 2–3: human ``canon edit`` / ``confirm`` / ``dismiss`` (+ non-persist accept)."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any

import click

from songyan.cli.commands.workbench import _ensure_project_readable
from songyan.db.plan_fact_repo import PlanFactError, PlanFactRepository
from songyan.models.plan_facts import PlanAttribute, PlanEntity

_NOT_YET = "尚未入典；需 canon confirm 后才进入 Canon / 圣经。"
_CONFIRMED = "已入典"
_ACCEPT_HINT = (
    "尚未入典；accept 不写库。请使用 canon confirm 入典。"
)


async def _edit_entity(
    *,
    project_id: str,
    entity_id: str,
    entity_type: str,
    aliases: tuple[str, ...],
) -> str:
    await _ensure_project_readable(project_id)
    if not entity_id.strip():
        raise click.ClickException("entity-id 不能为空")
    if not entity_type.strip():
        raise click.ClickException("type 不能为空")
    entity = PlanEntity(
        entity_id=entity_id.strip(),
        project_id=project_id,
        entity_type=entity_type.strip(),
        aliases=[a for a in aliases if a.strip()],
        approval_status="pending",
    )
    await PlanFactRepository().write_entity(entity)
    return (
        f"已写入 pending entity {entity.entity_id}（{_NOT_YET}）"
    )


async def _edit_attribute(
    *,
    project_id: str,
    attribute_id: str,
    entity_id: str,
    key: str,
    value: str,
    valid_from_ch: int | None,
    valid_to_ch: int | None,
) -> str:
    await _ensure_project_readable(project_id)
    if not attribute_id.strip():
        raise click.ClickException("attribute-id 不能为空")
    if not entity_id.strip():
        raise click.ClickException("entity-id 不能为空")
    if not key.strip():
        raise click.ClickException("key 不能为空")
    attribute = PlanAttribute(
        attribute_id=attribute_id.strip(),
        project_id=project_id,
        entity_id=entity_id.strip(),
        key=key.strip(),
        value=value,
        valid_from_ch=valid_from_ch,
        valid_to_ch=valid_to_ch,
        source="human",
        approval_status="pending",
    )
    try:
        await PlanFactRepository().write_attribute(attribute)
    except PlanFactError as exc:
        raise click.ClickException(str(exc)) from exc
    return (
        f"已写入 pending attribute {attribute.attribute_id} "
        f"source=human（{_NOT_YET}）"
    )


async def _load_entity_for_project(project_id: str, entity_id: str) -> PlanEntity:
    await _ensure_project_readable(project_id)
    if not entity_id.strip():
        raise click.ClickException("entity-id 不能为空")
    row = await PlanFactRepository().read_entity(entity_id.strip())
    if row is None or row.project_id != project_id:
        raise click.ClickException(f"entity 不存在: {entity_id.strip()}")
    return row


async def _load_attribute_for_project(
    project_id: str, attribute_id: str
) -> PlanAttribute:
    await _ensure_project_readable(project_id)
    if not attribute_id.strip():
        raise click.ClickException("attribute-id 不能为空")
    row = await PlanFactRepository().read_attribute(attribute_id.strip())
    if row is None or row.project_id != project_id:
        raise click.ClickException(f"attribute 不存在: {attribute_id.strip()}")
    return row


async def _confirm_entity(*, project_id: str, entity_id: str) -> str:
    row = await _load_entity_for_project(project_id, entity_id)
    updated = row.model_copy(update={"approval_status": "approved"})
    await PlanFactRepository().write_entity(updated)
    return f"{_CONFIRMED} entity {updated.entity_id}（approval_status=approved）"


async def _confirm_attribute(*, project_id: str, attribute_id: str) -> str:
    row = await _load_attribute_for_project(project_id, attribute_id)
    updated = row.model_copy(update={"approval_status": "approved"})
    try:
        await PlanFactRepository().write_attribute(updated)
    except PlanFactError as exc:
        raise click.ClickException(str(exc)) from exc
    return (
        f"{_CONFIRMED} attribute {updated.attribute_id} "
        f"（approval_status=approved, source={updated.source}）"
    )


async def _dismiss_entity(*, project_id: str, entity_id: str) -> str:
    row = await _load_entity_for_project(project_id, entity_id)
    updated = row.model_copy(update={"approval_status": "rejected"})
    await PlanFactRepository().write_entity(updated)
    return (
        f"已驳回 entity {updated.entity_id}（approval_status=rejected；"
        "不进 Canon / Pending / 圣经）"
    )


async def _dismiss_attribute(*, project_id: str, attribute_id: str) -> str:
    row = await _load_attribute_for_project(project_id, attribute_id)
    updated = row.model_copy(update={"approval_status": "rejected"})
    try:
        await PlanFactRepository().write_attribute(updated)
    except PlanFactError as exc:
        raise click.ClickException(str(exc)) from exc
    return (
        f"已驳回 attribute {updated.attribute_id}（approval_status=rejected；"
        "不进 Canon / Pending / 圣经）"
    )


async def _accept_entity(*, project_id: str, entity_id: str) -> str:
    row = await _load_entity_for_project(project_id, entity_id)
    return (
        f"entity {row.entity_id} 仍为 {row.approval_status}；{_ACCEPT_HINT}"
    )


async def _accept_attribute(*, project_id: str, attribute_id: str) -> str:
    row = await _load_attribute_for_project(project_id, attribute_id)
    return (
        f"attribute {row.attribute_id} 仍为 {row.approval_status}；{_ACCEPT_HINT}"
    )


def _run(coro: Coroutine[Any, Any, str]) -> str:
    try:
        return asyncio.run(coro)
    except click.ClickException:
        raise
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


@click.group(name="edit")
def canon_edit_group() -> None:
    """写入/改写计划行。默认 pending；人写 attribute 强制 source=human。"""


@canon_edit_group.command(name="entity")
@click.option("--project-id", required=True, help="项目 ID")
@click.option("--entity-id", required=True, help="实体稳定 id")
@click.option("--type", "entity_type", required=True, help="实体类型")
@click.option("--alias", "aliases", multiple=True, help="别名，可重复")
def edit_entity(
    project_id: str,
    entity_id: str,
    entity_type: str,
    aliases: tuple[str, ...],
) -> None:
    """写入或覆盖一条 entity，approval_status=pending。"""
    click.echo(
        _run(
            _edit_entity(
                project_id=project_id,
                entity_id=entity_id,
                entity_type=entity_type,
                aliases=aliases,
            )
        )
    )


@canon_edit_group.command(name="attribute")
@click.option("--project-id", required=True, help="项目 ID")
@click.option("--attribute-id", required=True, help="属性稳定 id")
@click.option("--entity-id", required=True, help="所属实体 id")
@click.option("--key", required=True, help="属性键")
@click.option("--value", required=True, help="属性值")
@click.option("--valid-from-ch", type=int, default=None, help="生效起始章（含）")
@click.option("--valid-to-ch", type=int, default=None, help="生效结束章（含）")
def edit_attribute(
    project_id: str,
    attribute_id: str,
    entity_id: str,
    key: str,
    value: str,
    valid_from_ch: int | None,
    valid_to_ch: int | None,
) -> None:
    """写入或覆盖一条 attribute；强制 source=human、pending。"""
    click.echo(
        _run(
            _edit_attribute(
                project_id=project_id,
                attribute_id=attribute_id,
                entity_id=entity_id,
                key=key,
                value=value,
                valid_from_ch=valid_from_ch,
                valid_to_ch=valid_to_ch,
            )
        )
    )


@click.group(name="confirm")
def canon_confirm_group() -> None:
    """将计划行入典为 approved。输出写明已入典。"""


@canon_confirm_group.command(name="entity")
@click.option("--project-id", required=True, help="项目 ID")
@click.option("--entity-id", required=True, help="实体稳定 id")
def confirm_entity(project_id: str, entity_id: str) -> None:
    """将 entity 设为 approved（入典）。"""
    click.echo(_run(_confirm_entity(project_id=project_id, entity_id=entity_id)))


@canon_confirm_group.command(name="attribute")
@click.option("--project-id", required=True, help="项目 ID")
@click.option("--attribute-id", required=True, help="属性稳定 id")
def confirm_attribute(project_id: str, attribute_id: str) -> None:
    """将 attribute 设为 approved（入典）。"""
    click.echo(
        _run(_confirm_attribute(project_id=project_id, attribute_id=attribute_id))
    )


@click.group(name="dismiss")
def canon_dismiss_group() -> None:
    """驳回计划行：approval_status=rejected（保留行，不进 Canon）。"""


@canon_dismiss_group.command(name="entity")
@click.option("--project-id", required=True, help="项目 ID")
@click.option("--entity-id", required=True, help="实体稳定 id")
def dismiss_entity(project_id: str, entity_id: str) -> None:
    """将 entity 设为 rejected。"""
    click.echo(_run(_dismiss_entity(project_id=project_id, entity_id=entity_id)))


@canon_dismiss_group.command(name="attribute")
@click.option("--project-id", required=True, help="项目 ID")
@click.option("--attribute-id", required=True, help="属性稳定 id")
def dismiss_attribute(project_id: str, attribute_id: str) -> None:
    """将 attribute 设为 rejected。"""
    click.echo(
        _run(_dismiss_attribute(project_id=project_id, attribute_id=attribute_id))
    )


@click.group(name="accept")
def canon_accept_group() -> None:
    """非持久 UX：不写库，仅提醒去 confirm。"""


@canon_accept_group.command(name="entity")
@click.option("--project-id", required=True, help="项目 ID")
@click.option("--entity-id", required=True, help="实体稳定 id")
def accept_entity(project_id: str, entity_id: str) -> None:
    """不改变 approval_status；提醒尚未入典。"""
    click.echo(_run(_accept_entity(project_id=project_id, entity_id=entity_id)))


@canon_accept_group.command(name="attribute")
@click.option("--project-id", required=True, help="项目 ID")
@click.option("--attribute-id", required=True, help="属性稳定 id")
def accept_attribute(project_id: str, attribute_id: str) -> None:
    """不改变 approval_status；提醒尚未入典。"""
    click.echo(
        _run(_accept_attribute(project_id=project_id, attribute_id=attribute_id))
    )


def register_canon_write_commands(cli: click.Group) -> None:
    """Attach ``canon edit|confirm|dismiss|accept`` under the existing ``canon`` group."""
    canon = cli.commands.get("canon")
    if not isinstance(canon, click.Group):
        raise RuntimeError("canon group must be registered before canon write commands")
    canon.add_command(canon_edit_group)
    canon.add_command(canon_confirm_group)
    canon.add_command(canon_dismiss_group)
    canon.add_command(canon_accept_group)
