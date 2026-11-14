"""M1 steps 2–3 + M2 steps 2–3: canon write + promise settle + hard/stale."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Coroutine
from typing import Any

import click

from songyan.cli.commands.workbench import _ensure_project_readable
from songyan.db.connection import get_db
from songyan.db.plan_fact_repo import PlanFactError, PlanFactRepository
from songyan.db.repository import ChapterHeadRepository
from songyan.db.settlement_repo import ForeshadowingRepository
from songyan.models.plan_facts import PlanAttribute, PlanEntity

_NOT_YET = "尚未入典；需 canon confirm 后才进入 Canon / 圣经。"
_CONFIRMED = "已入典"
_ACCEPT_HINT = (
    "尚未入典；accept 不写库。请使用 canon confirm 入典。"
)
_SETTLED = "已销账"
_OPEN_PROMISE_STATUSES = frozenset({"planted", "due", "overdue"})


class UncomputableStaleRangeError(click.ClickException):
    """Wanted stale mark but chapter range cannot be computed — exit 2."""

    exit_code = 2


def compute_stale_chapter_set(
    *,
    valid_from_ch: int | None = None,
    valid_to_ch: int | None = None,
    explicit_from_ch: int | None = None,
    explicit_to_ch: int | None = None,
) -> set[int] | None:
    """Closed-interval scope for W4 stale marks (tech-m2 §3.1 / B1 / §4.2).

    Returns a chapter set, or ``None`` when uncomputable. Only closed
    intervals count (explicit ``from``+``to``, else ``valid_from``+
    ``valid_to``). A one-sided explicit window fails loud instead of
    silently falling back to the valid window (task 226 切片 5).
    A one-sided valid window does not guess an unbounded set.
    Both ends empty → ``None``.
    """
    if (explicit_from_ch is None) != (explicit_to_ch is None):
        return None

    chapters: set[int] = set()

    if explicit_from_ch is not None and explicit_to_ch is not None:
        if explicit_from_ch < 1 or explicit_to_ch < 1 or explicit_to_ch < explicit_from_ch:
            return None
        chapters.update(range(explicit_from_ch, explicit_to_ch + 1))
    elif valid_from_ch is not None and valid_to_ch is not None:
        if valid_from_ch < 1 or valid_to_ch < 1 or valid_to_ch < valid_from_ch:
            return None
        chapters.update(range(valid_from_ch, valid_to_ch + 1))

    if not chapters:
        return None
    return chapters




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


async def _confirm_entity(
    *,
    project_id: str,
    entity_id: str,
    hard: bool = False,
    mark_stale: bool = False,
    from_ch: int | None = None,
    to_ch: int | None = None,
) -> str:
    row = await _load_entity_for_project(project_id, entity_id)
    if row.approval_status == "rejected":
        raise ConfirmRejectedError(
            f"entity {row.entity_id} 已 rejected，不能直接 confirm 转正；"
            "如需恢复请 canon edit 重新进 pending 队列（task 226 切片 5）"
        )
    want_stale = hard or mark_stale
    chapters: set[int] | None = None
    if want_stale:
        chapters = compute_stale_chapter_set(
            explicit_from_ch=from_ch,
            explicit_to_ch=to_ch,
        )
        if chapters is None:
            raise UncomputableStaleRangeError(
                "要标脏但范围不可算：entity 无 valid 窗口时 --hard / --mark-stale "
                "须同时提供 --from-ch 与 --to-ch（tech-m2 §4.2）"
            )

    updated = row.model_copy(update={"approval_status": "approved"})
    async with get_db() as conn:
        await PlanFactRepository().write_entity(updated, conn=conn)
        if want_stale and chapters is not None:
            await ChapterHeadRepository().mark_content_stale(
                project_id, sorted(chapters), conn=conn
            )
        await conn.commit()

    msg = f"{_CONFIRMED} entity {updated.entity_id}（approval_status=approved）"
    if want_stale and chapters is not None:
        span = ",".join(str(c) for c in sorted(chapters))
        msg += f"；已标脏章 {span}"
    return msg


async def _confirm_attribute(
    *,
    project_id: str,
    attribute_id: str,
    hard: bool = False,
    mark_stale: bool = False,
    from_ch: int | None = None,
    to_ch: int | None = None,
) -> str:
    row = await _load_attribute_for_project(project_id, attribute_id)
    if row.approval_status == "rejected":
        raise ConfirmRejectedError(
            f"attribute {row.attribute_id} 已 rejected，不能直接 confirm 转正；"
            "如需恢复请 canon edit 重新进 pending 队列（task 226 切片 5）"
        )
    want_stale = hard or mark_stale
    chapters: set[int] | None = None
    if want_stale:
        chapters = compute_stale_chapter_set(
            valid_from_ch=row.valid_from_ch,
            valid_to_ch=row.valid_to_ch,
            explicit_from_ch=from_ch,
            explicit_to_ch=to_ch,
        )
        if chapters is None:
            raise UncomputableStaleRangeError(
                "要标脏但范围不可算：两端 valid 皆空且无证据章号时不猜成脏；"
                "整命令失败（不入典也不标脏）（tech-m2 §4.2）"
            )

    updated = row.model_copy(update={"approval_status": "approved"})
    try:
        async with get_db() as conn:
            await PlanFactRepository().write_attribute(updated, conn=conn)
            if want_stale and chapters is not None:
                await ChapterHeadRepository().mark_content_stale(
                    project_id, sorted(chapters), conn=conn
                )
            await conn.commit()
    except PlanFactError as exc:
        raise click.ClickException(str(exc)) from exc

    msg = (
        f"{_CONFIRMED} attribute {updated.attribute_id} "
        f"（approval_status=approved, source={updated.source}）"
    )
    if want_stale and chapters is not None:
        span = ",".join(str(c) for c in sorted(chapters))
        msg += f"；已标脏章 {span}"
    return msg


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


class MissingAcceptedVersionError(click.ClickException):
    """Chapter has no accepted_version_id — process exit 2."""

    exit_code = 2


class ConfirmRejectedError(click.ClickException):
    """Row already rejected; revive via canon edit, not confirm — exit 2."""

    exit_code = 2


async def _load_open_foreshadowing(
    *, project_id: str, foreshadowing_id: str
) -> dict[str, Any]:
    await _ensure_project_readable(project_id)
    fid = foreshadowing_id.strip()
    if not fid:
        raise click.ClickException("foreshadowing-id 不能为空")
    row = await ForeshadowingRepository().get_row(fid)
    if row is None or row.get("project_id") != project_id:
        raise click.ClickException(f"foreshadowing 不存在: {fid}")
    return row


async def _confirm_promise(
    *,
    project_id: str,
    foreshadowing_id: str,
    chapter: int,
    evidence: str,
) -> str:
    """Human settle of an open foreshadowing (W5 / tech-m2 §4.1 / B3)."""
    evidence_text = evidence.strip()
    if not evidence_text:
        raise click.ClickException("evidence 不能为空")
    if chapter < 1:
        raise click.ClickException("chapter 须为正整数")

    row = await _load_open_foreshadowing(
        project_id=project_id, foreshadowing_id=foreshadowing_id
    )
    status = str(row["status"])
    lifecycle = str(row.get("lifecycle_status") or "active")
    if lifecycle != "active" or status not in _OPEN_PROMISE_STATUSES:
        raise click.ClickException(
            f"foreshadowing 不在开放承诺集: {row['foreshadowing_id']} "
            f"(status={status}, lifecycle_status={lifecycle})"
        )

    head = await ChapterHeadRepository().get(project_id, chapter)
    if head is None or not head.accepted_version_id:
        raise MissingAcceptedVersionError(
            f"第 {chapter} 章没有 accepted_version_id，无法回填 resolved_version_id"
        )

    # task 228：守卫与写入同一事务（原子 UPDATE 自带开放集条件），evidence 落库。
    async with get_db() as conn:
        settled = await ForeshadowingRepository().settle_resolved(
            row["foreshadowing_id"],
            resolved_chapter=chapter,
            resolved_version_id=head.accepted_version_id,
            evidence=evidence_text,
            open_statuses=tuple(sorted(_OPEN_PROMISE_STATUSES)),
            conn=conn,
        )
        if not settled:
            cursor = await conn.execute(
                "SELECT status, lifecycle_status FROM foreshadowings "
                "WHERE foreshadowing_id = ?",
                (row["foreshadowing_id"],),
            )
            current = await cursor.fetchone()
            cur_status = current[0] if current else "?"
            cur_lifecycle = current[1] if current else "?"
            raise click.ClickException(
                f"foreshadowing 不在开放承诺集（并发或状态已变）: "
                f"{row['foreshadowing_id']} "
                f"(当前 status={cur_status}, lifecycle_status={cur_lifecycle})"
            )
        await conn.commit()
    return (
        f"{_SETTLED} promise {row['foreshadowing_id']} "
        f"（status=resolved, resolved_chapter={chapter}, "
        f"resolved_version_id={head.accepted_version_id}；"
        f"evidence={evidence_text}）"
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
    """将计划行入典为 approved，或确认销账开放承诺。"""


@canon_confirm_group.command(name="entity")
@click.option("--project-id", required=True, help="项目 ID")
@click.option("--entity-id", required=True, help="实体稳定 id")
@click.option("--hard", is_flag=True, default=False, help="硬变更：入典并按范围标脏")
@click.option(
    "--mark-stale",
    is_flag=True,
    default=False,
    help="显式标脏（软注记也可用；范围算法同 --hard）",
)
@click.option("--from-ch", type=int, default=None, help="显式标脏起始章（含）")
@click.option("--to-ch", type=int, default=None, help="显式标脏结束章（含）")
def confirm_entity(
    project_id: str,
    entity_id: str,
    hard: bool,
    mark_stale: bool,
    from_ch: int | None,
    to_ch: int | None,
) -> None:
    """将 entity 设为 approved（入典）；可选 --hard / --mark-stale 标脏。"""
    click.echo(
        _run(
            _confirm_entity(
                project_id=project_id,
                entity_id=entity_id,
                hard=hard,
                mark_stale=mark_stale,
                from_ch=from_ch,
                to_ch=to_ch,
            )
        )
    )


@canon_confirm_group.command(name="attribute")
@click.option("--project-id", required=True, help="项目 ID")
@click.option("--attribute-id", required=True, help="属性稳定 id")
@click.option("--hard", is_flag=True, default=False, help="硬变更：入典并按范围标脏")
@click.option(
    "--mark-stale",
    is_flag=True,
    default=False,
    help="显式标脏（软注记也可用；范围算法同 --hard）",
)
@click.option("--from-ch", type=int, default=None, help="显式标脏起始章（含；覆盖 valid）")
@click.option("--to-ch", type=int, default=None, help="显式标脏结束章（含；覆盖 valid）")
def confirm_attribute(
    project_id: str,
    attribute_id: str,
    hard: bool,
    mark_stale: bool,
    from_ch: int | None,
    to_ch: int | None,
) -> None:
    """将 attribute 设为 approved（入典）；可选 --hard / --mark-stale 标脏。"""
    click.echo(
        _run(
            _confirm_attribute(
                project_id=project_id,
                attribute_id=attribute_id,
                hard=hard,
                mark_stale=mark_stale,
                from_ch=from_ch,
                to_ch=to_ch,
            )
        )
    )


def _stdin_isatty() -> bool:
    """独立小函数便于测试 monkeypatch（task 259）。"""
    import sys

    return sys.stdin.isatty()


class BatchConfirmReject(click.ClickException):
    """批量确认拒绝（人取消 / 非交互缺 --yes）— exit 2。"""

    exit_code = 2


@canon_confirm_group.command(name="batch")
@click.option("--project-id", required=True, help="项目 ID")
@click.option("--yes", is_flag=True, help="跳过交互确认（脚本/CI 用）")
@click.option("--json", "as_json", is_flag=True, help="JSON 输出")
def confirm_batch(project_id: str, yes: bool, as_json: bool) -> None:
    """批量确认全部 pending 提案（entity/attribute；软确认不带标脏）。

    人确认语义不稀释：摘要 y/N 或 --yes；非 TTY 须显式 --yes（exit 2）。
    批量前请先 `canon pending` 过目。task 259。
    """
    from songyan.cli.commands.workbench import _ensure_project_readable as _ensure
    from songyan.cli.commands.workbench import _load_pending

    _run(_ensure(project_id))
    entities, attributes = _run(_load_pending(project_id))
    if not entities and not attributes:
        click.echo("无 pending 提案")
        return
    note = (
        f"batch confirm：entity={len(entities)} attribute={len(attributes)}"
        f"（软确认不带 --hard/--mark-stale）"
    )
    if not yes:
        if not _stdin_isatty():
            raise BatchConfirmReject(
                f"{note}；非交互环境须显式 --yes 才会执行（防脚本静默入典）"
            )
        click.echo(note, err=True)
        if not click.confirm("确认全部入典？", default=False):
            raise BatchConfirmReject("已取消批量确认")
    else:
        click.echo(f"{note}（--yes 跳过确认）", err=True)

    ok = 0
    failed: list[str] = []
    for row in entities:
        try:
            _run(_confirm_entity(project_id=project_id, entity_id=row.entity_id))
            ok += 1
        except Exception as exc:  # noqa: BLE001 - 逐条隔离，保住已确认
            failed.append(f"entity {row.entity_id}: {exc}")
    for row in attributes:
        try:
            _run(_confirm_attribute(project_id=project_id, attribute_id=row.attribute_id))
            ok += 1
        except Exception as exc:  # noqa: BLE001
            failed.append(f"attribute {row.attribute_id}: {exc}")

    payload = {
        "confirmed": ok,
        "failed": len(failed),
        "entity": len(entities),
        "attribute": len(attributes),
    }
    if as_json:
        click.echo(json.dumps(payload, ensure_ascii=False))
    else:
        click.echo(f"confirmed={ok} failed={len(failed)}")
    for item in failed:
        click.echo(f"失败：{item}", err=True)
    if failed:
        raise click.ClickException(
            f"批量确认部分失败（{len(failed)} 条）；已确认的保留"
        ) from None


@canon_confirm_group.command(name="promise")
@click.option("--project-id", required=True, help="项目 ID")
@click.option("--foreshadowing-id", required=True, help="伏笔 / 承诺稳定 id")
@click.option("--chapter", required=True, type=int, help="兑现章号")
@click.option("--evidence", required=True, help="人给的短证据串")
def confirm_promise(
    project_id: str, foreshadowing_id: str, chapter: int, evidence: str
) -> None:
    """人确认销账开放承诺：status=resolved 并回填 resolved_*。"""
    click.echo(
        _run(
            _confirm_promise(
                project_id=project_id,
                foreshadowing_id=foreshadowing_id,
                chapter=chapter,
                evidence=evidence,
            )
        )
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
