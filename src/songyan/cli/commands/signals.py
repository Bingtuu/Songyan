"""task 257：``songyan signals`` — S 信号只读聚合面（tech-post-m4 v2 §B）。

独立薄命令（B6 修订）：today 保持一句下一步，report 保持 run 级管线报告。
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import click

from songyan.cli.commands.workbench import _ensure_project_readable

_ORDER = ("S1", "S2", "S3", "S4", "S5", "S7")


_S_LABELS = {
    "S1": "确认入典",
    "S2": "问题关闭周期",
    "S3": "开放承诺年龄",
    "S4": "抽卡采纳分布",
    "S5": "人改率",
    "S7": "单章成本",
}


def _render_text(payload: dict[str, Any]) -> str:
    lines = [f"信号（{payload['project_id']}）"]
    signals = payload["signals"]
    for key in _ORDER:
        block = signals[key]
        label = _S_LABELS.get(key, key)
        if block.get("gap"):
            lines.append(f"{key} {label}: 暂不可算——{block['note']}")
            continue
        parts = []
        for k, v in block.items():
            if k == "note":
                continue
            if isinstance(v, dict) and not v:
                continue
            parts.append(f"{k}={v}")
        line = f"{key} {label}: " + " ".join(parts)
        note = block.get("note")
        if note:
            line += f"（{note}）"
        lines.append(line)
    return "\n".join(lines)


@click.command(name="signals")
@click.option("--project-id", required=True, help="项目 ID")
@click.option("--json", "as_json", is_flag=True, help="JSON 输出")
def signals_cmd(project_id: str, as_json: bool) -> None:
    """S 信号聚合（S1/S3/S4/S5/S7 可算口径；S2 gap 明示）。只读，零写库。"""
    from songyan.services.signals_report import build_signals

    asyncio.run(_ensure_project_readable(project_id))
    payload = asyncio.run(build_signals(project_id))
    if as_json:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    click.echo(_render_text(payload))


def register_signals_commands(cli: click.Group) -> None:
    """Mount the ``signals`` command."""
    cli.add_command(signals_cmd)
