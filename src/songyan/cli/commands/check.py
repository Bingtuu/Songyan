"""M1 step 4: author-facing ``songyan check`` (W6) — read-only plan fact gate."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import click

from songyan.cli.commands.workbench import _ensure_project_readable
from songyan.db.repository import ChapterHeadRepository, ChapterVersionRepository
from songyan.plan_checks.claim_check import ClaimVerdict
from songyan.plan_checks.gate import PlanFactGateReport, run_plan_fact_gate
from songyan.plan_checks.must_mention import MissingMention
from songyan.plan_checks.typed_attributes import AttributeExtract, AttributeMismatch

_NO_CHAPTER = "无章可查：该章没有可用的已存版本正文。"
_PASS_LINE = "规则检查通过（只读，不写库、不入典）。"
_FAIL_LINE = "规则检查未过门（有硬伤）。"
_HINT = "若要入典，另走 canon confirm。"
_HARD = "hard"


class NoChapterError(click.ClickException):
    """No usable accepted chapter body — process exit 2."""

    exit_code = 2


def _load_extracts(path: Path | None) -> list[AttributeExtract]:
    """Load fixture/injection extracts. Production may omit; gate invents none."""
    if path is None:
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise click.ClickException("--extracts-json 须为 AttributeExtract 对象数组")
    try:
        return [AttributeExtract.model_validate(item) for item in raw]
    except Exception as exc:  # pydantic ValidationError / TypeError
        raise click.ClickException(f"--extracts-json 无效: {exc}") from exc


async def _load_chapter_text(project_id: str, chapter: int) -> str:
    """Same convention as ``cli/commands/index.py``: accepted head → version.content."""
    head = await ChapterHeadRepository().get(project_id, chapter)
    if head is None or not head.accepted_version_id:
        raise NoChapterError(_NO_CHAPTER)
    version = await ChapterVersionRepository().get(head.accepted_version_id)
    if version is None or not (version.content or "").strip():
        raise NoChapterError(_NO_CHAPTER)
    return version.content


def _report_to_dict(report: PlanFactGateReport) -> dict[str, Any]:
    """Align JSON keys with gate return; attach display severity for hard fails."""
    payload = report.model_dump(mode="json")
    for row in payload.get("attribute_mismatches", []):
        row["severity"] = _HARD
    for row in payload.get("missing_mentions", []):
        row["severity"] = _HARD
    for row in payload.get("claim_verdicts", []):
        if row.get("status") != "supported":
            row["severity"] = _HARD
    payload["hint"] = _HINT
    return payload


def _render_markdown(report: PlanFactGateReport) -> str:
    lines = [
        f"# 规则检查 · 第 {report.chapter} 章",
        "",
        f"项目：`{report.project_id}`",
        "",
        "## 结果",
        _PASS_LINE if report.passed else _FAIL_LINE,
        "",
    ]
    missing: list[MissingMention] = report.missing_mentions
    if missing:
        lines.append("## 必须提及缺失")
        for mention in missing:
            terms = (
                "、".join(mention.missing_terms)
                if mention.missing_terms
                else mention.label
            )
            lines.append(
                f"- `{mention.point_id}`（{mention.label}）缺：{terms}"
                f"（严重度：{_HARD}）"
            )
        lines.append("")
    mismatches: list[AttributeMismatch] = report.attribute_mismatches
    if mismatches:
        lines.append("## 属性不一致")
        for mismatch in mismatches:
            lines.append(
                f"- 实体 `{mismatch.entity_id}` 键 `{mismatch.key}`："
                f"圣经值「{mismatch.approved_value}」≠ 正文侧值「{mismatch.extract_value}」"
                f"（严重度：{_HARD}）"
            )
        lines.append("")
    hard_claims: list[ClaimVerdict] = [
        verdict for verdict in report.claim_verdicts if verdict.status != "supported"
    ]
    if hard_claims:
        lines.append("## 主张判定")
        for verdict in hard_claims:
            lines.append(
                f"- `{verdict.claim_id}`：{verdict.status} — {verdict.text}"
                f"（严重度：{_HARD}）"
            )
        lines.append("")
    lines.append("## 提示")
    lines.append(_HINT)
    return "\n".join(lines)


async def _run_check(
    *,
    project_id: str,
    chapter: int,
    extracts: list[AttributeExtract],
) -> PlanFactGateReport:
    await _ensure_project_readable(project_id)
    if chapter < 1:
        raise click.ClickException("chapter 须为 >= 1 的整数")
    chapter_text = await _load_chapter_text(project_id, chapter)
    return await run_plan_fact_gate(
        project_id,
        chapter,
        chapter_text,
        extracts=extracts,
    )


def register_check_commands(cli: click.Group) -> None:
    """Register ``songyan check`` on the root CLI group."""

    @cli.command(name="check")
    @click.option("--project-id", required=True, help="项目 ID")
    @click.option("--chapter", required=True, type=int, help="章节号")
    @click.option("--json", "json_output", is_flag=True, help="输出机器可读 JSON")
    @click.option(
        "--extracts-json",
        type=click.Path(exists=True, dir_okay=False, path_type=Path),
        default=None,
        help="夹具注入的 AttributeExtract JSON 数组；M1 不从正文现抽属性",
    )
    def check_cmd(
        project_id: str,
        chapter: int,
        json_output: bool,
        extracts_json: Path | None,
    ) -> None:
        """对一章正文做只读规则检查（不写库、不入典）。"""
        try:
            extracts = _load_extracts(extracts_json)
            report = asyncio.run(
                _run_check(
                    project_id=project_id,
                    chapter=chapter,
                    extracts=extracts,
                )
            )
        except click.ClickException:
            raise
        except click.Abort:
            raise
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc

        if json_output:
            click.echo(
                json.dumps(_report_to_dict(report), ensure_ascii=False, indent=2)
            )
        else:
            click.echo(_render_markdown(report))

        if not report.passed:
            raise click.exceptions.Exit(2)
