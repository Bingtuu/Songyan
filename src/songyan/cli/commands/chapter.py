"""M4 步 2/3: chapter accept / continue CLI（tech-m4 §5 步 2/3 / B2/B11）。

accept exit 码表（B11）：0 = 已确认；1 = 缺库 / 缺项目 / 参数非法（含文件错误）；
2 = 无可确认稿 / 重复 accept（幂等提示）。

continue exit 码表（B11）：0 = 生成待确认 / 停闸 / 全部完成；1 = 缺库 / 缺项目 /
参数非法 / LLM 失败与 settlement 阶段 LLM 失败（写 pause_reason 后）；
2 = B1 两前置 / --require-plan 拒绝；3 = 预算耗尽（已写保留）。
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import click

from songyan.db.connection import get_db_path
from songyan.db.repository import ProjectRepository
from songyan.services.chapter_accept import (
    AlreadyAcceptedError,
    ChapterFileError,
    NothingToAcceptError,
    accept_chapter,
)
from songyan.services.chapter_continue import (
    ContinueBudgetExceeded,
    ContinueGateError,
    ContinueLLMError,
    ContinueSettlementError,
    continue_chapters,
)


class ChapterBusinessReject(click.ClickException):
    """Business reject — process exit 2（tech-m4 B11）。"""

    exit_code = 2


class ChapterBudgetRejected(click.ClickException):
    """预算耗尽 — process exit 3（已写保留，沿用 variant 语义）。"""

    exit_code = 3


async def _accept_chapter(
    project_id: str,
    chapter: int,
    from_file: Path | None,
) -> dict[str, object]:
    db_path = get_db_path()
    if not db_path.is_file():
        raise click.ClickException(f"找不到数据库文件: {db_path}")
    project = await ProjectRepository().get(project_id)
    if project is None:
        raise click.ClickException(f"项目不存在: {project_id}")
    try:
        outcome = await accept_chapter(project_id, chapter, from_file=from_file)
    except (NothingToAcceptError, AlreadyAcceptedError) as exc:
        raise ChapterBusinessReject(str(exc)) from exc
    except ChapterFileError as exc:
        raise click.ClickException(str(exc)) from exc
    return {
        "chapter": outcome.chapter_number,
        "accepted_version_id": outcome.accepted_version_id,
        "source_version_id": outcome.source_version_id,
        "edited_version_id": outcome.edited_version_id,
        "word_count": outcome.word_count,
        "edit_ratio": outcome.edit_ratio,
    }


@click.group(name="chapter")
def chapter_group() -> None:
    """章级人确认写径。子命令随 tech-m4 小步落地，无空桩。"""


@chapter_group.command(name="accept")
@click.option("--project-id", required=True, help="项目 ID")
@click.option("--chapter", required=True, type=int, help="章号")
@click.option(
    "--from-file",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="外置编辑稿路径；传入则以该稿为 accepted 副本来源（先物化 edited 行）",
)
@click.option("--json", "as_json", is_flag=True, help="JSON 输出")
def chapter_accept_cmd(
    project_id: str,
    chapter: int,
    from_file: Path | None,
    as_json: bool,
) -> None:
    """确认一章工作稿为 accepted（picked / 人改稿 → accepted）；不写结算库。"""
    if chapter < 1:
        raise click.ClickException("chapter 必须 >= 1")
    payload = asyncio.run(_accept_chapter(project_id, chapter, from_file))
    # task 253 / S5：几乎没改就标 settled 的所有权提醒（<5%，不拦，exit 0）。
    edit_warn_threshold = 0.05
    if float(payload.get("edit_ratio") or 0.0) < edit_warn_threshold:
        click.echo(
            f"人改率 {float(payload['edit_ratio']):.1%}：本章几乎未改动工作稿即确认"
            f"——所有权提醒（S5），不影响确认",
            err=True,
        )
    if as_json:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    click.echo(
        f"已确认 chapter={payload['chapter']} "
        f"accepted_version_id={payload['accepted_version_id']} "
        f"word_count={payload['word_count']}"
    )


async def _continue_chapters(
    project_id: str,
    count: int,
    variants: int | None,
    require_plan: bool,
) -> dict[str, Any] | None:
    db_path = get_db_path()
    if not db_path.is_file():
        raise click.ClickException(f"找不到数据库文件: {db_path}")
    project = await ProjectRepository().get(project_id)
    if project is None:
        raise click.ClickException(f"项目不存在: {project_id}")
    try:
        outcome = await continue_chapters(
            project_id,
            count=count,
            variants=variants,
            require_plan=require_plan,
            notice=lambda m: click.echo(m, err=True),
        )
    except ContinueGateError as exc:
        raise ChapterBusinessReject(str(exc)) from exc
    except (ContinueSettlementError, ContinueLLMError) as exc:
        raise click.ClickException(str(exc)) from exc
    except ContinueBudgetExceeded as exc:
        raise ChapterBudgetRejected(str(exc)) from exc
    if outcome is None:
        return None
    return {
        "chapter": outcome.chapter_number,
        "version_id": outcome.version_id,
        "word_count": outcome.word_count,
        "cost_cny": outcome.cost_cny,
        "next_hint": outcome.next_hint,
    }


@chapter_group.command(name="continue")
@click.option("--project-id", required=True, help="项目 ID")
@click.option("--count", default=1, type=int, help="批命令次数 1..3（逐章停闸，非跳过确认）")
@click.option("--variants", type=int, default=None, help="转调 M3 抽卡生成 N 槽（不 auto-pick）")
@click.option("--require-plan", is_flag=True, help="本章计划缺失时拒绝执行（默认仅警告）")
@click.option("--json", "as_json", is_flag=True, help="JSON 输出")
def chapter_continue_cmd(
    project_id: str,
    count: int,
    variants: int | None,
    require_plan: bool,
    as_json: bool,
) -> None:
    """推进下一章：准备（settlement）→ 组装 → 生成草稿或抽卡转调；每章生成即停闸。"""
    if count < 1 or count > 3:
        raise click.ClickException(f"--count 必须在 1..3 之间（收到 {count}）")
    if variants is not None and variants < 1:
        raise click.ClickException(f"--variants 必须 >= 1（收到 {variants}）")
    payload = asyncio.run(_continue_chapters(project_id, count, variants, require_plan))
    if payload is None:
        # 区分「空项目（章宇宙为空）」与「全部 accepted」——前者并非已确认完成
        # （task 244 / 冒烟发现 2）。
        from songyan.services.chapter_progress import load_chapter_progress

        progress = asyncio.run(load_chapter_progress(project_id))
        if not progress.chapters:
            click.echo(
                "项目尚无章节工作稿；开章走 run --chapters N 或 "
                "variant generate --chapter N"
            )
        else:
            click.echo("全部章已 accepted")
        return
    if as_json:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    progress = f"（--count {count} 逐章停闸：1/{count}）" if count > 1 else ""
    if payload["version_id"] is not None:
        click.echo(
            f"已生成 章 {payload['chapter']} 草稿 version_id={payload['version_id']} "
            f"word_count={payload['word_count']} cost=¥{payload['cost_cny']:.4f}{progress}"
        )
    else:
        click.echo(f"已生成 章 {payload['chapter']} 抽卡槽（见 variant list）{progress}")
    click.echo(payload["next_hint"])


async def _chapter_status_payload(
    project_id: str, chapter: int
) -> dict[str, object] | None:
    """None = 章不在章宇宙（调用方按 exit 2 处理）。"""
    db_path = get_db_path()
    if not db_path.is_file():
        raise click.ClickException(f"找不到数据库文件: {db_path}")
    project = await ProjectRepository().get(project_id)
    if project is None:
        raise click.ClickException(f"项目不存在: {project_id}")
    from songyan.services.chapter_status import load_chapter_status

    report = await load_chapter_status(project_id, chapter)
    if report is None:
        return None
    return report.model_dump(mode="json")


@chapter_group.command(name="status")
@click.option("--project-id", required=True, help="项目 ID")
@click.option("--chapter", required=True, type=int, help="章号")
@click.option("--json", "as_json", is_flag=True, help="JSON 输出")
def chapter_status_cmd(project_id: str, chapter: int, as_json: bool) -> None:
    """只读章进度面：章态 / head 指针 / variant 槽 / 费用 / 共审计数。

    不承载 ContextEmergency（tech-m4 B10 分工句）；零写库。
    """
    if chapter < 1:
        raise click.ClickException("chapter 必须 >= 1")
    payload = asyncio.run(_chapter_status_payload(project_id, chapter))
    if payload is None:
        raise ChapterBusinessReject(
            f"指定章不存在（不在章宇宙）：第 {chapter} 章"
        )
    if as_json:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    counts = payload["review_findings"]
    click.echo(
        f"chapter: {payload['chapter']}  state: {payload['state']}"
    )
    click.echo(
        f"head: current={payload['current_version_id'] or '-'} "
        f"accepted={payload['accepted_version_id'] or '-'} "
        f"content_stale={payload['content_stale']}"
    )
    variants = payload["variants"]
    if variants:
        click.echo("variants:")
        for row in variants:
            flag = f" flag={row['quality_flag']}" if row["quality_flag"] else ""
            click.echo(
                f"- slot={row['slot_index']} status={row['status']}"
                f"{flag} stale_vs_canon={row['stale_vs_canon']}"
                f" slStale={row['stale_vs_storyline']}"
                f" cost={row['cost_cny_estimate']}"
            )
    else:
        click.echo("variants: （无槽）")
    click.echo(
        f"cost: slots=¥{payload['slot_cost_sum']:.4f} "
        f"llm=¥{payload['llm_cost_sum']:.4f}"
    )
    click.echo(
        f"review: hard={counts.get('hard', 0)} "
        f"warning={counts.get('warning', 0)} info={counts.get('info', 0)}"
    )


def register_chapter_commands(cli: click.Group) -> None:
    """Mount the ``chapter`` group (only implemented subcommands)."""
    cli.add_command(chapter_group)
