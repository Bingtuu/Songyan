"""M1 step 2: human ``canon edit`` write path (pending; attribute source=human)."""

from __future__ import annotations

import asyncio

import click

from songyan.cli.commands.workbench import _ensure_project_readable
from songyan.db.plan_fact_repo import PlanFactError, PlanFactRepository
from songyan.models.plan_facts import PlanAttribute, PlanEntity

_NOT_YET = "尚未入典；需 canon confirm 后才进入 Canon / 圣经。"


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
    try:
        message = asyncio.run(
            _edit_entity(
                project_id=project_id,
                entity_id=entity_id,
                entity_type=entity_type,
                aliases=aliases,
            )
        )
    except click.ClickException:
        raise
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(message)


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
    try:
        message = asyncio.run(
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
    except click.ClickException:
        raise
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(message)


def register_canon_write_commands(cli: click.Group) -> None:
    """Attach ``canon edit`` under the existing ``canon`` group (M0 show)."""
    canon = cli.commands.get("canon")
    if not isinstance(canon, click.Group):
        raise RuntimeError("canon group must be registered before canon write commands")
    canon.add_command(canon_edit_group)
