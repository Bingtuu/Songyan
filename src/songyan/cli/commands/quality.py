"""质量口径复现 CLI 命令（只读）：five-gate 与 t9.

V13 Task 229：外部技术用户用这两条命令在自己的 run 上复现
CED / T9 / 五门数值。两条命令均为只读：

- ``five-gate`` 通过 SQLite ``mode=ro`` URI 打开 DB（复用
  ``five_gate_acceptance.open_readonly_db``），不存在时显式报错；
- ``t9`` 走 ``collect_text_cleanliness_metrics(persist=False)`` 纯内存路径，
  不写 ``text_cleanliness_metrics`` 表。

口径定义见 ``docs/quality-gates.md``。

退出码约定（两条命令一致）：0 = PASS，1 = FAIL，2 = 工具错误或样本不足。
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import click

from songyan.db.connection import get_db_path
from songyan.evals.five_gate_acceptance import (
    DEFAULT_ALLOWED_GAP,
    FiveGateToolError,
    evaluate_project,
    open_readonly_db,
    render_text_report,
)

# 工具错误/样本不足退出码（PASS=0、FAIL=1 之外）
_TOOL_ERROR_EXIT = 2


def _resolve_db_path(db: Path | None) -> Path:
    """解析目标 DB 路径：显式 --db 优先，缺省用 DATABASE_URL."""
    if db is not None:
        return db
    return get_db_path()


def _genre_from_db(db_path: Path, project_id: str) -> str:
    """从目标 DB 的 projects 表读取体裁标签（只读）."""
    with open_readonly_db(db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT genre_id FROM projects WHERE project_id = ? LIMIT 1",
            (project_id,),
        )
        row = cur.fetchone()
    if row is None:
        msg = f"project not found in {db_path}: {project_id}"
        raise FiveGateToolError(msg)
    return str(row["genre_id"])


@click.command(name="five-gate")
@click.option("--project-id", required=True, help="目标 project_id")
@click.option("--up-to", required=True, type=int, help="评估章节边界（含），如 100")
@click.option(
    "--genre",
    default=None,
    help="体裁标签（仅作报告标签）；缺省从目标 DB 的 projects 表读取",
)
@click.option(
    "--db",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="目标 SQLite DB 路径；缺省用 DATABASE_URL 指向的库",
)
@click.option(
    "--baseline",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="可选 sci-fi baseline JSON 路径；缺省用包内资源",
)
@click.option(
    "--allow-gap",
    type=int,
    default=DEFAULT_ALLOWED_GAP,
    help="completeness 门容忍的 accepted 缺口",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="输出格式；json 含 metrics.ced 段，可直接取 CED 数值",
)
def five_gate_cmd(
    project_id: str,
    up_to: int,
    genre: str | None,
    db: Path | None,
    baseline: Path | None,
    allow_gap: int,
    output_format: str,
) -> None:
    """对目标项目跑五门验收（只读；退出码 0=PASS / 1=FAIL / 2=工具错误）.

    CED 数值混在五门报告中；``--format json`` 输出的 ``metrics.ced``
    段（issue_count / word_count / ced_per_1k_words）即 CED 独立取数来源。
    """
    try:
        db_path = _resolve_db_path(db)
        resolved_genre = genre or _genre_from_db(db_path, project_id)
        report = evaluate_project(
            db_path,
            project_id=project_id,
            genre=resolved_genre,
            up_to=up_to,
            baseline_path=baseline,
            allow_gap=allow_gap,
        )
    except (FiveGateToolError, OSError, ValueError) as exc:
        click.echo(f"five-gate error: {exc}", err=True)
        raise SystemExit(_TOOL_ERROR_EXIT) from exc

    if output_format == "json":
        click.echo(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        click.echo(render_text_report(report))
    if report.verdict != "PASS":
        raise SystemExit(1)


def _parse_chapter_range(chapters: str) -> tuple[int, int]:
    """解析章节范围参数，如 ``1-200`` 或单章 ``3``."""
    if "-" in chapters:
        start_s, end_s = chapters.split("-", 1)
        start, end = int(start_s), int(end_s)
    else:
        start = end = int(chapters)
    if start < 1 or end < start:
        msg = f"invalid chapter range: {chapters}"
        raise ValueError(msg)
    return start, end


@click.command(name="t9")
@click.option("--project-id", required=True, help="目标 project_id")
@click.option("--chapters", required=True, help="章节范围，如 1-200")
@click.option(
    "--include-timeline",
    is_flag=True,
    help="将时间线矛盾计入红线（冻结口径默认 report-only，不计入）",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="输出格式",
)
def t9_cmd(project_id: str, chapters: str, include_timeline: bool, output_format: str) -> None:
    """重算 T9 文本洁净度（只读，persist=False 不写派生表）.

    红线口径：元标记泄漏=0、重复长段落=0；时间线矛盾默认 report-only。
    退出码 0=PASS / 1=FAIL / 2=样本不足或工具错误。
    """
    from songyan.evals.text_cleanliness import collect_text_cleanliness_metrics
    from songyan.evals.v6_acceptance import check_t9

    try:
        start, end = _parse_chapter_range(chapters)
        verdict = asyncio.run(
            check_t9(project_id, start, end, include_timeline_in_redline=include_timeline)
        )
        rows = asyncio.run(
            collect_text_cleanliness_metrics(project_id, start, end, persist=False)
        )
    except (OSError, ValueError, RuntimeError) as exc:
        click.echo(f"t9 error: {exc}", err=True)
        raise SystemExit(_TOOL_ERROR_EXIT) from exc

    if output_format == "json":
        payload = {
            "project_id": project_id,
            "chapters": f"{start}-{end}",
            "passed": verdict.passed,
            "sufficient": verdict.sufficient,
            "measured": verdict.measured,
            "threshold": verdict.threshold,
            "detail": verdict.detail,
            "per_chapter": [
                {
                    "chapter_number": row.chapter_number,
                    "meta_tag_leak_count": row.meta_tag_leak_count,
                    "duplicate_paragraph_count": row.duplicate_paragraph_count,
                    "timeline_conflict_count": row.timeline_conflict_count,
                }
                for row in rows
            ],
        }
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        label = {True: "PASS", False: "FAIL", None: "INSUFFICIENT"}[verdict.passed]
        click.echo(f"=== T9 文本洁净度 @ {project_id} Ch{start}-{end} ===")
        click.echo(f"  verdict   : {label}（阈值 {verdict.threshold}）")
        click.echo(f"  measured  : {verdict.measured}")
        click.echo(f"  detail    : {verdict.detail}")
        if rows:
            click.echo("  per-chapter:")
            for row in rows:
                click.echo(
                    f"    Ch{row.chapter_number}: meta={row.meta_tag_leak_count} "
                    f"duplicate={row.duplicate_paragraph_count} "
                    f"timeline={row.timeline_conflict_count}"
                )

    if verdict.passed is not True:
        # FAIL 与样本不足（INSUFFICIENT）都不允许以 0 退出
        raise SystemExit(1 if verdict.passed is False else _TOOL_ERROR_EXIT)


def register_quality_commands(cli: click.Group) -> None:
    """注册质量口径复现命令."""
    cli.add_command(five_gate_cmd)
    cli.add_command(t9_cmd)
