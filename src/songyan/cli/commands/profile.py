"""task 266：``songyan character`` / ``songyan setting`` — 角色/设定人编辑写径。

与 ``storyline`` 同形：直写 + 审计（services/profile_edit）；软删行从默认
list 与组装出口消失，``--include-archived`` 可见。exit 码 B11 同形：
0 = 成功；2 = 业务拒绝（不存在 id / 主角 remove）；1 = 缺库 / 缺项目。
"""

from __future__ import annotations

import asyncio
import json

import click

from songyan.cli.commands.workbench import _ensure_project_readable
from songyan.services import profile_edit


class ProfileBusinessReject(click.ClickException):
    """业务拒绝 — exit 2（B11 同形）。"""

    exit_code = 2


@click.group(name="character")
def character_group() -> None:
    """角色档案人编辑写径（list / edit / remove）；remove 为软删。"""


@character_group.command(name="list")
@click.option("--project-id", required=True, help="项目 ID")
@click.option(
    "--include-archived", is_flag=True, help="列出已软删角色（默认不含）"
)
@click.option("--json", "as_json", is_flag=True, help="JSON 输出")
def character_list(project_id: str, include_archived: bool, as_json: bool) -> None:
    """列出角色档案；默认不含软删行。"""
    asyncio.run(_ensure_project_readable(project_id))
    characters = asyncio.run(profile_edit.list_characters(project_id, include_archived))
    payload = {
        "project_id": project_id,
        "characters": [c.model_dump(mode="json") for c in characters],
    }
    if as_json:
        click.echo(json.dumps(payload, ensure_ascii=False))
        return
    for c in payload["characters"]:
        mark = " [archived]" if c["archived"] else ""
        click.echo(
            f"- {c['character_id']} {c['name']} ({c['role_type']}){mark}"
        )


@character_group.command(name="edit")
@click.option("--project-id", required=True, help="项目 ID")
@click.option("--character-id", required=True, help="角色 ID")
@click.option("--name", default=None, help="角色名")
@click.option(
    "--role-type",
    type=click.Choice(["protagonist", "supporting", "antagonist"]),
    default=None,
)
@click.option("--background", default=None, help="背景")
@click.option("--traits", default=None, help='JSON 数组，如 ["沉默"]')
@click.option("--goals", default=None, help='JSON 数组，如 ["看店"]')
@click.option("--json", "as_json", is_flag=True, help="JSON 输出")
def character_edit(
    project_id: str,
    character_id: str,
    name: str | None,
    role_type: str | None,
    background: str | None,
    traits: str | None,
    goals: str | None,
    as_json: bool,
) -> None:
    """更新角色档案（未传字段保持原值）；主角改名走这里，不能 remove。"""
    asyncio.run(_ensure_project_readable(project_id))
    traits_list = _parse_json_array("--traits", traits)
    goals_list = _parse_json_array("--goals", goals)
    try:
        action = asyncio.run(
            profile_edit.edit_character(
                project_id,
                character_id,
                name=name,
                role_type=role_type,
                background=background,
                traits=traits_list,
                goals=goals_list,
            )
        )
    except profile_edit.ProfileEditError as exc:
        raise ProfileBusinessReject(str(exc)) from exc
    payload = {"character_id": character_id, "action": action}
    if as_json:
        click.echo(json.dumps(payload, ensure_ascii=False))
        return
    click.echo(f"character {character_id} {action}")


@character_group.command(name="remove")
@click.option("--project-id", required=True, help="项目 ID")
@click.option("--character-id", required=True, help="角色 ID")
@click.option("--json", "as_json", is_flag=True, help="JSON 输出")
def character_remove(project_id: str, character_id: str, as_json: bool) -> None:
    """软删角色（保留审计，从组装/名册出口消失）；主角拒绝；重复删除为 no-op。"""
    asyncio.run(_ensure_project_readable(project_id))
    try:
        action = asyncio.run(profile_edit.remove_character(project_id, character_id))
    except profile_edit.ProfileEditError as exc:
        raise ProfileBusinessReject(str(exc)) from exc
    payload = {"character_id": character_id, "action": action}
    if as_json:
        click.echo(json.dumps(payload, ensure_ascii=False))
        return
    click.echo(f"character {character_id} {action}")


@click.group(name="setting")
def setting_group() -> None:
    """设定（setting_snapshots）人编辑写径（list / edit / remove）。"""


@setting_group.command(name="list")
@click.option("--project-id", required=True, help="项目 ID")
@click.option(
    "--include-archived", is_flag=True, help="列出已软删设定（默认不含）"
)
@click.option("--json", "as_json", is_flag=True, help="JSON 输出")
def setting_list(project_id: str, include_archived: bool, as_json: bool) -> None:
    """列出设定；默认不含 archived 行（dormant 仍列出）。"""
    asyncio.run(_ensure_project_readable(project_id))
    rows = asyncio.run(profile_edit.list_settings(project_id, include_archived))
    payload = {"project_id": project_id, "settings": rows}
    if as_json:
        click.echo(json.dumps(payload, ensure_ascii=False, default=str))
        return
    for r in rows:
        mark = "" if r["lifecycle_status"] == "active" else f" [{r['lifecycle_status']}]"
        click.echo(f"- {r['setting_id']} {r['setting_name']}{mark}")


@setting_group.command(name="edit")
@click.option("--project-id", required=True, help="项目 ID")
@click.option("--setting-id", required=True, help="设定 ID")
@click.option("--name", default=None, help="设定名")
@click.option("--description", default=None, help="描述")
@click.option("--json", "as_json", is_flag=True, help="JSON 输出")
def setting_edit(
    project_id: str,
    setting_id: str,
    name: str | None,
    description: str | None,
    as_json: bool,
) -> None:
    """更新设定名/描述（未传字段保持原值）。"""
    asyncio.run(_ensure_project_readable(project_id))
    try:
        action = asyncio.run(
            profile_edit.edit_setting(project_id, setting_id, name=name, description=description)
        )
    except profile_edit.ProfileEditError as exc:
        raise ProfileBusinessReject(str(exc)) from exc
    payload = {"setting_id": setting_id, "action": action}
    if as_json:
        click.echo(json.dumps(payload, ensure_ascii=False))
        return
    click.echo(f"setting {setting_id} {action}")


@setting_group.command(name="remove")
@click.option("--project-id", required=True, help="项目 ID")
@click.option("--setting-id", required=True, help="设定 ID")
@click.option("--json", "as_json", is_flag=True, help="JSON 输出")
def setting_remove(project_id: str, setting_id: str, as_json: bool) -> None:
    """软删设定（lifecycle_status='archived'）；幂等。"""
    asyncio.run(_ensure_project_readable(project_id))
    try:
        action = asyncio.run(profile_edit.remove_setting(project_id, setting_id))
    except profile_edit.ProfileEditError as exc:
        raise ProfileBusinessReject(str(exc)) from exc
    payload = {"setting_id": setting_id, "action": action}
    if as_json:
        click.echo(json.dumps(payload, ensure_ascii=False))
        return
    click.echo(f"setting {setting_id} {action}")


def _parse_json_array(flag: str, raw: str | None) -> list[str] | None:
    if raw is None:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"{flag} 须为 JSON 数组: {exc}") from exc
    if not isinstance(parsed, list) or not all(isinstance(x, str) for x in parsed):
        raise click.ClickException(f"{flag} 须为 JSON 字符串数组")
    return parsed


def register_profile_commands(cli: click.Group) -> None:
    """Mount the ``character`` / ``setting`` groups (list / edit / remove)."""
    cli.add_command(character_group)
    cli.add_command(setting_group)
