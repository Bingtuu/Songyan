"""M4 步 1 ``songyan status`` — 项目级计数面（tech-m4 §4.5 / B10 / B11）。

章进度分布 + 待确认 picked 数 + ContextEmergency 触发统计；纯只读。
exit 0 = 成功 / 1 = 缺库、缺项目；usage 错误（缺 ``--project-id``）按 Click 默认 exit 2。
``chapter status`` 本里程碑不做（B10 分工：ContextEmergency 只挂项目级 status）。
"""

from __future__ import annotations

import asyncio
import json

import click

from songyan.db.connection import get_db_path
from songyan.db.repository import ProjectRepository
from songyan.models.chapter_progress import (
    STATE_PRIORITY,
    ChapterProgressSummary,
    ContextEmergencySummary,
)
from songyan.services.chapter_progress import (
    load_chapter_progress,
    load_context_emergency,
)


async def _ensure_project_readable(project_id: str) -> None:
    db_path = get_db_path()
    if not db_path.is_file():
        raise click.ClickException(f"找不到数据库文件: {db_path}")
    project = await ProjectRepository().get(project_id)
    if project is None:
        raise click.ClickException(f"项目不存在: {project_id}")


async def _load(
    project_id: str,
) -> tuple[ChapterProgressSummary, ContextEmergencySummary]:
    await _ensure_project_readable(project_id)
    summary = await load_chapter_progress(project_id)
    emergency = await load_context_emergency(project_id)
    return summary, emergency


def _progress_counts(summary: ChapterProgressSummary) -> dict[str, int]:
    return {state.value: summary.distribution.get(state, 0) for state in STATE_PRIORITY}


def _render_text(
    summary: ChapterProgressSummary, emergency: ContextEmergencySummary
) -> str:
    counts = " ".join(f"{key}={value}" for key, value in _progress_counts(summary).items())
    last_chapter = "-" if emergency.last_chapter is None else str(emergency.last_chapter)
    budget = "-" if emergency.budget_used_before is None else str(emergency.budget_used_before)
    return "\n".join(
        [
            f"progress: {counts}",
            f"pending_confirm: {summary.pending_confirm}",
            "context_emergency: "
            f"count={emergency.count} "
            f"last_chapter={last_chapter} "
            f"budget_used_before={budget}",
        ]
    )


def _render_json(
    project_id: str,
    summary: ChapterProgressSummary,
    emergency: ContextEmergencySummary,
) -> str:
    payload = {
        "project_id": project_id,
        "progress": _progress_counts(summary),
        "pending_confirm": summary.pending_confirm,
        "context_emergency": {
            "count": emergency.count,
            "last_chapter": emergency.last_chapter,
            "budget_used_before": emergency.budget_used_before,
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


@click.command(name="status")
@click.option("--project-id", required=True, help="项目 ID")
@click.option("--json", "as_json", is_flag=True, help="JSON 输出")
def status_cmd(project_id: str, as_json: bool) -> None:
    """项目级计数面：章进度分布 / 待确认 picked / ContextEmergency（只读，不写库）。"""
    summary, emergency = asyncio.run(_load(project_id))
    if as_json:
        click.echo(_render_json(project_id, summary, emergency))
        return
    click.echo(_render_text(summary, emergency))


def register_status_commands(cli: click.Group) -> None:
    """Mount the ``status`` command."""
    cli.add_command(status_cmd)
