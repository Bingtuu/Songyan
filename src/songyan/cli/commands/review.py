"""M4 步 4 ``songyan review`` — 只读共审报告（tech-m4 §4.4 / B8 / B11）。

被审正文 = ``head.current_version_id`` 工作稿（W2 共审针对未 accept 的工作稿，
与 ``check`` 的 accepted 口径显式分叉）。七源输入并集内存合并呈现，全程零写库
（不调用 ``merge_reviews`` / ``list_variant_rows``）。

exit 码（B11）：0 = 报告输出（含发现问题）；1 = 缺库 / 缺项目 / 参数非法；
2 = 指定章不存在（不在章宇宙）。
"""

from __future__ import annotations

import asyncio
import json

import click

from songyan.cli.commands.workbench import _ensure_project_readable
from songyan.services.review_report import (
    ChapterReviewReport,
    build_chapter_review,
    list_chapter_universe,
)

_SEVERITY_TITLES = {"hard": "硬伤", "warning": "警告", "info": "提示"}


class ChapterNotInUniverseError(click.ClickException):
    """``--chapter`` 指定章不在章宇宙 — process exit 2."""

    exit_code = 2


async def _run_review(project_id: str, chapter: int | None) -> ChapterReviewReport | None:
    """返回 None 表示章宇宙为空（调用方按 exit 0 空报告处理）。"""
    await _ensure_project_readable(project_id)
    if chapter is not None and chapter < 1:
        raise click.ClickException("chapter 须为 >= 1 的整数")
    universe = await list_chapter_universe(project_id)
    if chapter is None:
        if not universe:
            return None
        chapter = max(universe)
    elif chapter not in universe:
        raise ChapterNotInUniverseError(f"指定章不存在（不在章宇宙）：第 {chapter} 章")
    return await build_chapter_review(project_id, chapter)


def _render_markdown(report: ChapterReviewReport) -> str:
    lines = [
        f"# 共审报告 · 第 {report.chapter} 章",
        "",
        f"项目：`{report.project_id}`",
        "",
        "## 被审工作稿",
    ]
    if report.workdraft_version_id is not None:
        lines.append(f"`{report.workdraft_version_id}`（head.current_version_id 工作稿）")
    else:
        lines.append(report.gate_note)
    lines.append("")

    grouped: dict[str, list[str]] = {"hard": [], "warning": [], "info": []}
    for finding in report.findings:
        evidence = f"（证据：{finding.evidence}）" if finding.evidence else ""
        location = f" @{finding.location}" if finding.location else ""
        grouped[finding.severity].append(
            f"- [{finding.source}] {finding.message}{location}{evidence}"
        )
    for severity, title in _SEVERITY_TITLES.items():
        lines.append(f"## {title}")
        rows = grouped[severity]
        if rows:
            lines.extend(rows)
        else:
            lines.append("（无）")
        lines.append("")

    lines.append("## 分区明细")
    lines.append(f"- 三审（全版本最新）：{len(report.audits)} 版有审计")
    lines.append(f"- literary_observations：{len(report.literary)} 条")
    rep_note = f"（{report.repetition_note}）" if report.repetition_note else ""
    lines.append(f"- 复读命中：{len(report.repetition_hits)} 处{rep_note}")
    lines.append(f"- 未登记专名：{len(report.proper_noun_hits)} 个")
    lines.append(f"- variant 备注：{len(report.variant_notes)} 槽")
    lines.append(f"- 人的 mark：{len(report.human_marks)} 条")
    return "\n".join(lines)


def register_review_commands(cli: click.Group) -> None:
    """Mount the ``review`` command."""
    cli.add_command(review_cmd)


@click.command(name="review")
@click.option("--project-id", required=True, help="项目 ID")
@click.option("--chapter", default=None, type=int, help="章节号（默认章宇宙最近一章）")
@click.option("--json", "json_output", is_flag=True, help="输出机器可读 JSON")
def review_cmd(project_id: str, chapter: int | None, json_output: bool) -> None:
    """只读共审报告：七源输入并集按严重度分组呈现（不写库、不调 merge_reviews）。"""
    try:
        report = asyncio.run(_run_review(project_id, chapter))
    except click.ClickException:
        raise
    except click.Abort:
        raise
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    if report is None:
        empty_payload = {
            "project_id": project_id,
            "chapter": None,
            "note": "章宇宙为空：该项目无任何章头，无可审章。",
        }
        if json_output:
            click.echo(json.dumps(empty_payload, ensure_ascii=False))
        else:
            click.echo(empty_payload["note"])
        return

    if json_output:
        click.echo(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2))
    else:
        click.echo(_render_markdown(report))
