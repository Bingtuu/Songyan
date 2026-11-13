"""task 255：``songyan storyline`` — 故事线（规划面）人编辑写径。

直写 + 审计（services/storyline_edit）；规划不是 Canon（PRD :108），
文案与出口均不出现「入典」字样。exit 码 B11 同形：0 = 成功；2 = 业务拒绝；
1 = 缺库 / 缺项目 / 参数非法。
"""

from __future__ import annotations

import asyncio
import json

import click

from songyan.cli.commands.workbench import _ensure_project_readable
from songyan.services.storyline_edit import edit_outline as edit_outline_service


class StorylineBusinessReject(click.ClickException):
    """业务拒绝 — exit 2（B11 同形）。"""

    exit_code = 2


async def _show_payload(project_id: str) -> dict[str, object]:
    await _ensure_project_readable(project_id)
    from songyan.db.narrative_repo import NarrativeRepository

    repo = NarrativeRepository()
    outline = await repo.get_outline(project_id)
    arcs = await repo.list_arc_plans(project_id, include_archived=True)
    threads = await repo.list_threads(project_id, include_archived=True)
    return {
        "project_id": project_id,
        "outline": None if outline is None else outline.model_dump(mode="json"),
        "arcs": [a.model_dump(mode="json") for a in arcs],
        "threads": [t.model_dump(mode="json") for t in threads],
    }


@click.group(name="storyline")
def storyline_group() -> None:
    """故事线（大纲/弧/线索）人编辑写径；规划面，不是 Canon。"""


@storyline_group.command(name="show")
@click.option("--project-id", required=True, help="项目 ID")
@click.option("--json", "as_json", is_flag=True, help="JSON 输出")
def storyline_show(project_id: str, as_json: bool) -> None:
    """展示故事线三件套；文本与 today 的故事线分面同渲染口径。"""
    payload = asyncio.run(_show_payload(project_id))
    if as_json:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    from songyan.cli.commands.workbench import _storyline_text
    from songyan.db.narrative_repo import NarrativeRepository
    from songyan.models.narrative import ArcPlan, StoryOutline

    outline = (
        StoryOutline(**payload["outline"]) if payload["outline"] is not None else None
    )
    arcs = [ArcPlan(**a) for a in payload["arcs"]]

    async def _counts() -> dict[str, int]:
        return await NarrativeRepository().count_threads_by_status(project_id)

    counts = asyncio.run(_counts())
    click.echo(_storyline_text(outline, arcs, counts))
    for arc in payload["arcs"]:
        mark = " [archived]" if arc.get("archived") else ""
        click.echo(
            f"- arc={arc['arc_id']} ch{arc['start_chapter']}-{arc['end_chapter']} "
            f"goal={arc['arc_goal'] or '-'}{mark}"
        )
    for thread in payload["threads"]:
        mark = " [archived]" if thread.get("archived") else ""
        click.echo(
            f"- thread={thread['thread_id']} status={thread['status']} "
            f"title={thread['title'] or '-'}{mark}"
        )


@storyline_group.group(name="edit")
def storyline_edit_group() -> None:
    """编辑（upsert：存在即更新、不存在即建）；每次写留审计。"""


@storyline_edit_group.command(name="outline")
@click.option("--project-id", required=True, help="项目 ID")
@click.option("--core-conflict", default=None, help="全书核心冲突")
@click.option("--mainline-synopsis", default=None, help="主线梗概")
@click.option("--themes", default=None, help='JSON 数组，如 ["都市","灵异"]')
@click.option("--intended-ending", default=None, help="预期结局方向")
@click.option("--json", "as_json", is_flag=True, help="JSON 输出")
def storyline_edit_outline(
    project_id: str,
    core_conflict: str | None,
    mainline_synopsis: str | None,
    themes: str | None,
    intended_ending: str | None,
    as_json: bool,
) -> None:
    """创建/更新全书大纲行（每项目一行）；未传字段保持原值。"""
    from songyan.cli.commands.workbench import _ensure_project_readable as _ensure

    asyncio.run(_ensure(project_id))
    themes_list: list[str] | None = None
    if themes is not None:
        try:
            parsed = json.loads(themes)
        except json.JSONDecodeError as exc:
            raise click.ClickException(f"--themes 须为 JSON 数组: {exc}") from exc
        if not isinstance(parsed, list) or not all(isinstance(x, str) for x in parsed):
            raise click.ClickException("--themes 须为 JSON 字符串数组")
        themes_list = parsed
    action = asyncio.run(
        edit_outline_service(
            project_id,
            core_conflict=core_conflict,
            mainline_synopsis=mainline_synopsis,
            themes=themes_list,
            intended_ending=intended_ending,
        )
    )
    payload = {"outline": True, "action": action}
    if as_json:
        click.echo(json.dumps(payload, ensure_ascii=False))
        return
    click.echo(f"outline {action}")


@storyline_edit_group.command(name="arc")
@click.option("--project-id", required=True, help="项目 ID")
@click.option("--arc-id", required=True, help="弧 ID（upsert 键）")
@click.option("--arc-index", type=int, default=None, help="弧序号（须项目内唯一）")
@click.option("--start-chapter", type=int, default=None)
@click.option("--end-chapter", type=int, default=None)
@click.option("--arc-goal", default=None)
@click.option("--open-thread", multiple=True, help="应开启的 thread_id（可多次）")
@click.option("--resolve-thread", multiple=True, help="应收束的 thread_id（可多次）")
@click.option("--is-mainline", is_flag=True, default=None, help="主线弧")
@click.option("--json", "as_json", is_flag=True, help="JSON 输出")
def storyline_edit_arc(
    project_id: str,
    arc_id: str,
    arc_index: int | None,
    start_chapter: int | None,
    end_chapter: int | None,
    arc_goal: str | None,
    open_thread: tuple[str, ...],
    resolve_thread: tuple[str, ...],
    is_mainline: bool | None,
    as_json: bool,
) -> None:
    """创建/更新一条弧；范围、arc_index 唯一性与线索引用做窄校验。"""
    from songyan.cli.commands.workbench import _ensure_project_readable as _ensure
    from songyan.services.storyline_edit import (
        StorylineEditError,
        upsert_arc,
    )

    asyncio.run(_ensure(project_id))
    try:
        action = asyncio.run(
            upsert_arc(
                project_id,
                arc_id=arc_id,
                arc_index=arc_index,
                start_chapter=start_chapter,
                end_chapter=end_chapter,
                arc_goal=arc_goal,
                threads_to_open=list(open_thread) or None,
                threads_to_resolve=list(resolve_thread) or None,
                is_mainline=is_mainline,
            )
        )
    except StorylineEditError as exc:
        raise StorylineBusinessReject(str(exc)) from exc
    payload = {"arc_id": arc_id, "action": action}
    if as_json:
        click.echo(json.dumps(payload, ensure_ascii=False))
        return
    click.echo(f"arc {arc_id} {action}")


@storyline_edit_group.command(name="thread")
@click.option("--project-id", required=True, help="项目 ID")
@click.option("--thread-id", required=True, help="线索 ID（upsert 键）")
@click.option("--title", default=None)
@click.option("--description", default=None)
@click.option(
    "--status",
    type=click.Choice(["planned", "opened", "advanced", "resolved", "abandoned"]),
    default=None,
)
@click.option("--opened-chapter", type=int, default=None)
@click.option("--expected-resolve-arc", type=int, default=None)
@click.option("--json", "as_json", is_flag=True, help="JSON 输出")
def storyline_edit_thread(
    project_id: str,
    thread_id: str,
    title: str | None,
    description: str | None,
    status: str | None,
    opened_chapter: int | None,
    expected_resolve_arc: int | None,
    as_json: bool,
) -> None:
    """创建/更新一条线索；status 白名单 + 收束弧存在性校验。"""
    from songyan.cli.commands.workbench import _ensure_project_readable as _ensure
    from songyan.services.storyline_edit import (
        StorylineEditError,
        upsert_thread,
    )

    asyncio.run(_ensure(project_id))
    try:
        action = asyncio.run(
            upsert_thread(
                project_id,
                thread_id=thread_id,
                title=title,
                description=description,
                status=status,
                opened_chapter=opened_chapter,
                expected_resolve_arc=expected_resolve_arc,
            )
        )
    except StorylineEditError as exc:
        raise StorylineBusinessReject(str(exc)) from exc
    payload = {"thread_id": thread_id, "action": action}
    if as_json:
        click.echo(json.dumps(payload, ensure_ascii=False))
        return
    click.echo(f"thread {thread_id} {action}")


@storyline_group.group(name="remove")
def storyline_remove_group() -> None:
    """软删（archived=1，可审计、不进指纹切片）；幂等。"""


@storyline_remove_group.command(name="arc")
@click.option("--project-id", required=True, help="项目 ID")
@click.option("--arc-id", required=True, help="弧 ID")
@click.option("--json", "as_json", is_flag=True, help="JSON 输出")
def storyline_remove_arc(project_id: str, arc_id: str, as_json: bool) -> None:
    """软删一条弧；重复删除为 no-op（exit 0）。"""
    from songyan.cli.commands.workbench import _ensure_project_readable as _ensure
    from songyan.services.storyline_edit import StorylineEditError, remove_arc

    asyncio.run(_ensure(project_id))
    try:
        action = asyncio.run(remove_arc(project_id, arc_id=arc_id))
    except StorylineEditError as exc:
        raise StorylineBusinessReject(str(exc)) from exc
    payload = {"arc_id": arc_id, "action": action}
    if as_json:
        click.echo(json.dumps(payload, ensure_ascii=False))
        return
    click.echo(f"arc {arc_id} {action}")


@storyline_remove_group.command(name="thread")
@click.option("--project-id", required=True, help="项目 ID")
@click.option("--thread-id", required=True, help="线索 ID")
@click.option("--json", "as_json", is_flag=True, help="JSON 输出")
def storyline_remove_thread(project_id: str, thread_id: str, as_json: bool) -> None:
    """软删一条线索；重复删除为 no-op（exit 0）。"""
    from songyan.cli.commands.workbench import _ensure_project_readable as _ensure
    from songyan.services.storyline_edit import StorylineEditError, remove_thread

    asyncio.run(_ensure(project_id))
    try:
        action = asyncio.run(remove_thread(project_id, thread_id=thread_id))
    except StorylineEditError as exc:
        raise StorylineBusinessReject(str(exc)) from exc
    payload = {"thread_id": thread_id, "action": action}
    if as_json:
        click.echo(json.dumps(payload, ensure_ascii=False))
        return
    click.echo(f"thread {thread_id} {action}")


def register_storyline_commands(cli: click.Group) -> None:
    """Mount the ``storyline`` group (show / edit / remove)。"""
    cli.add_command(storyline_group)
