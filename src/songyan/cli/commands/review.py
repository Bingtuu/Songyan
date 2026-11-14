"""M4 步 4 ``songyan review`` — 只读共审报告（tech-m4 §4.4 / B8 / B11）。

被审正文 = ``head.current_version_id`` 工作稿（W2 共审针对未 accept 的工作稿，
与 ``check`` 的 accepted 口径显式分叉）。七源输入并集内存合并呈现，全程零写库
（不调用 ``merge_reviews`` / ``list_variant_rows``）。

tech-m4-followup 步 3：``--deep`` 追加显式 LLM 深审（B4 成本前置交互门 /
B5 零写库 / B6 三件套输入四口径）；不带 ``--deep`` 行为一字不动。

exit 码（B11）：0 = 报告输出（含发现问题）；1 = 缺库 / 缺项目 / 参数非法 /
深审 LLM 产出无法解析（基础报告照出，stderr 注明）；2 = 指定章不存在
（不在章宇宙）/ 成本门拒绝（非交互缺 ``--yes``、超 ``--budget-cny``、人取消）。
"""

from __future__ import annotations

import asyncio
import json
import sys

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


class DeepCostReject(click.ClickException):
    """深审成本门拒绝（非交互缺 --yes / 超预算 / 人取消）— exit 2。"""

    exit_code = 2


def _stdin_isatty() -> bool:
    """独立小函数便于测试 monkeypatch。"""
    return sys.stdin.isatty()


def _cost_gate(
    estimated_cny: float,
    model: str,
    *,
    yes: bool,
    budget_cny: float | None,
) -> None:
    """成本前置（B4）：预估打印 → 超预算拒绝 → --yes 跳过 → 交互 y/N → 非 TTY 拒绝。"""
    note = f"deep 深审预估：模型 {model}，费用约 ¥{estimated_cny:.4f}"
    if budget_cny is not None and estimated_cny > budget_cny:
        raise DeepCostReject(f"{note}；超过 --budget-cny={budget_cny}，拒绝执行")
    if yes:
        click.echo(f"{note}（--yes 跳过确认）", err=True)
        return
    if not _stdin_isatty():
        raise DeepCostReject(
            f"{note}；非交互环境须显式 --yes 才会执行（防脚本静默烧钱）"
        )
    click.echo(note, err=True)
    if not click.confirm("继续执行深审？", default=False):
        raise DeepCostReject("已取消深审")


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
        raise ChapterNotInUniverseError(
            f"该章还没有章节工作记录：第 {chapter} 章"
            f"（开新章走 chapter continue --chapter {chapter}）"
        )
    return await build_chapter_review(project_id, chapter)


async def _deep_inputs(
    project_id: str, chapter: int, report: ChapterReviewReport
) -> tuple[str, str, str, float, str]:
    """深审三件套装配（B6）+ 费用预估；返回 (正文, 圣经, 上一章摘要, 估价, 模型)。"""
    from songyan.db.repository import ChapterVersionRepository
    from songyan.plan_checks.bible import load_chapter_plan_bible
    from songyan.services.review_deep import (
        build_deep_review_prompt,
        estimate_deep_review_cost,
    )
    from songyan.workflows.phase2_graph import _get_previous_summary

    if report.workdraft_version_id is None:
        raise click.ClickException(
            "当前章无工作稿（head.current_version_id 为空），无可深审正文"
        )
    version = await ChapterVersionRepository().get(report.workdraft_version_id)
    if version is None:
        raise click.ClickException(f"工作稿版本缺失：{report.workdraft_version_id}")
    bible = await load_chapter_plan_bible(project_id, chapter)
    previous_summary = await _get_previous_summary(project_id, chapter)
    prompt = build_deep_review_prompt(
        content=version.content,
        bible_text=bible.text,
        previous_summary=previous_summary,
    )
    cost, model = estimate_deep_review_cost(prompt)
    return version.content, bible.text, previous_summary, cost, model


def _render_markdown(report: ChapterReviewReport) -> str:
    lines = [
        f"# 共审报告 · 第 {report.chapter} 章",
        "",
        f"项目：`{report.project_id}`",
        "",
        "## 被审工作稿",
    ]
    if report.workdraft_version_id is not None:
        lines.append(f"`{report.workdraft_version_id}`（当前工作稿）")
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
    if report.deep_count:
        lines.append(f"- LLM 深审（source=deep）：{report.deep_count} 条")
    return "\n".join(lines)


def register_review_commands(cli: click.Group) -> None:
    """Mount the ``review`` command."""
    cli.add_command(review_cmd)


@click.command(name="review")
@click.option("--project-id", required=True, help="项目 ID")
@click.option("--chapter", default=None, type=int, help="章节号（默认章宇宙最近一章）")
@click.option("--json", "json_output", is_flag=True, help="输出机器可读 JSON")
@click.option(
    "--deep",
    is_flag=True,
    help="追加显式 LLM 深审（成本前置确认；非交互须配 --yes）",
)
@click.option(
    "--yes",
    is_flag=True,
    help="跳过深审费用交互确认（脚本/CI 用）",
)
@click.option(
    "--budget-cny",
    default=None,
    type=float,
    help="深审费用硬上限（¥）；预估超过即拒绝执行",
)
def review_cmd(
    project_id: str,
    chapter: int | None,
    json_output: bool,
    deep: bool,
    yes: bool,
    budget_cny: float | None,
) -> None:
    """只读共审报告：七源输入并集按严重度分组呈现（不写库、不调 merge_reviews）。

    --deep 追加 LLM 深审分区（source=deep，与七源 findings 同形合并）。
    """
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
            "note": "还没有任何章节工作记录，无可审章（先 chapter continue --chapter 1 开书）",
        }
        if json_output:
            click.echo(json.dumps(empty_payload, ensure_ascii=False))
        else:
            click.echo(empty_payload["note"])
        return

    if deep:
        from songyan.services.review_deep import DeepReviewError, run_deep_review

        content, bible_text, previous_summary, cost, model = asyncio.run(
            _deep_inputs(project_id, report.chapter, report)
        )
        _cost_gate(cost, model, yes=yes, budget_cny=budget_cny)
        try:
            deep_findings = asyncio.run(
                run_deep_review(
                    project_id,
                    report.chapter,
                    content=content,
                    bible_text=bible_text,
                    previous_summary=previous_summary,
                )
            )
        except DeepReviewError as exc:
            # 基础报告照出（B11 口径），stderr 注明 deep 分区失败，exit 1。
            if json_output:
                click.echo(
                    json.dumps(report.model_dump(mode="json"),
                               ensure_ascii=False, indent=2)
                )
            else:
                click.echo(_render_markdown(report))
            raise click.ClickException(f"deep 深审失败：{exc}") from exc
        report.findings.extend(deep_findings)
        report.deep_count = len(deep_findings)

    if json_output:
        click.echo(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2))
    else:
        click.echo(_render_markdown(report))
