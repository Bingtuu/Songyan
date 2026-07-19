"""V9 Task 175 阶段 C：songyan report 成本段渲染.

纯函数模块：``LlmCallUsageRepository.aggregate_for_run`` 与
``source_stats_for_run`` 的查询结果进，markdown 文本出。不做 DB 访问，
便于脱离 tests/cli 单测（tests/cli 在 Task 181 前不计入默认测试）。
展示风格对齐 ``streaming_report``（中文标题 + 摘要列表 + 明细表格）。
"""

from __future__ import annotations

from typing import Any

from songyan.utils.cost_estimator import format_cost_estimate

#: per agent 成本分布默认展示条数（其余合并为「其他」行）
DEFAULT_TOP_N = 5

#: chapter_number 为 NULL 的分组标签：run 级调用（arc/volume 摘要、规划等未绑定章节的调用）
RUN_LEVEL_LABEL = "run 级"

#: 无 usage 数据时的提示（旧 run 没有 llm_call_usage 行，属常态而非错误）
NO_DATA_TEXT = "无成本数据（该 run 无 LLM 调用用量记录，或为 usage 落库前的旧 run）"


def _float(value: Any) -> float:
    """容错读取数值字段（None / 缺失按 0 处理）."""
    return float(value) if value is not None else 0.0


def _int(value: Any) -> int:
    """容错读取整数字段."""
    return int(value) if value is not None else 0


def _format_ratio(numerator: int, denominator: int) -> str:
    """格式化占比：百分比 + （分子/分母），分母为 0 时显示 -."""
    if denominator <= 0:
        return "-"
    return f"{numerator / denominator:.1%} ({numerator}/{denominator})"


def _usage_row(label: str, row: dict[str, Any]) -> str:
    """渲染一行 usage 明细（per agent / 每章 两张表同构）."""
    return (
        f"| {label} | {_int(row.get('call_count'))} | "
        f"{_int(row.get('prompt_tokens'))} | "
        f"{_int(row.get('completion_tokens'))} | "
        f"{format_cost_estimate(_float(row.get('cost_cny')))} |"
    )


def _merge_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """合并多行分组为一行（per agent Top N 之外的「其他」行）."""
    return {
        "call_count": sum(_int(row.get("call_count")) for row in rows),
        "prompt_tokens": sum(_int(row.get("prompt_tokens")) for row in rows),
        "completion_tokens": sum(_int(row.get("completion_tokens")) for row in rows),
        "cost_cny": sum(_float(row.get("cost_cny")) for row in rows),
    }


def render_cost_section(
    aggregate: dict[str, list[dict[str, Any]]],
    source_stats: dict[str, int],
    *,
    top_n: int = DEFAULT_TOP_N,
    error: str | None = None,
) -> str:
    """渲染 report 的成本视图段（markdown）.

    Args:
        aggregate: ``aggregate_for_run`` 的返回，含 per_chapter / per_agent 两个分组列表；
            per_chapter 中 chapter_number=None 的分组为 run 级调用，渲染为「run 级」。
        source_stats: ``source_stats_for_run`` 的返回，含 total_calls（分母）与
            token_estimate_calls / cost_pricing_estimate_calls（两个占比的分子）。
        top_n: per agent 成本分布展示的条数，超出部分合并为「其他（k 个 agent）」一行。
        error: 取数失败的错误摘要。非 None 时渲染可区分的「成本数据读取失败」行，
            与「无成本数据」（良性旧 run）明确区分开。

    Returns:
        markdown 文本；无 usage 数据（total_calls == 0）时输出「无成本数据」提示。
    """
    per_chapter = aggregate.get("per_chapter", [])
    per_agent = aggregate.get("per_agent", [])
    total_calls = _int(source_stats.get("total_calls"))

    lines = ["## 成本视图", ""]
    if error is not None:
        lines.append(f"成本数据读取失败：{error}")
        lines.append("")
        return "\n".join(lines)
    if total_calls == 0:
        lines.append(NO_DATA_TEXT)
        lines.append("")
        return "\n".join(lines)

    # ---- 摘要：总额 / 章节数 / 每章均 / 两个估算占比 ----
    chapter_rows = [row for row in per_chapter if row.get("chapter_number") is not None]
    run_level_rows = [row for row in per_chapter if row.get("chapter_number") is None]
    run_level_calls = sum(_int(row.get("call_count")) for row in run_level_rows)
    total_cost = sum(_float(row.get("cost_cny")) for row in per_chapter)
    chapter_count = len(chapter_rows)

    chapter_count_text = str(chapter_count)
    if run_level_calls:
        chapter_count_text += f"（另有 {RUN_LEVEL_LABEL}调用 {run_level_calls} 次）"
    avg_cost_text = (
        format_cost_estimate(total_cost / chapter_count) if chapter_count else "-"
    )

    lines.extend(
        [
            f"- **run 总成本**: {format_cost_estimate(total_cost)}",
            f"- **章节数**: {chapter_count_text}",
            f"- **每章均成本**: {avg_cost_text}",
            "- **token_source='estimate' 占比**: "
            + _format_ratio(_int(source_stats.get("token_estimate_calls")), total_calls),
            "- **cost_source='pricing_estimate' 占比**: "
            + _format_ratio(
                _int(source_stats.get("cost_pricing_estimate_calls")), total_calls
            ),
            "",
        ]
    )

    # ---- per agent 成本分布（成本降序；agent 数 > top_n 时截断 Top N，其余合并「其他」） ----
    sorted_agents = sorted(
        per_agent,
        key=lambda row: (-_float(row.get("cost_cny")), str(row.get("agent") or "")),
    )
    top_rows = sorted_agents[:top_n]
    rest_rows = sorted_agents[top_n:]

    agent_title = "### per agent 成本分布"
    if rest_rows:
        agent_title += f"（Top {top_n}）"

    lines.extend(
        [
            agent_title,
            "",
            "| Agent | 调用次数 | prompt tokens | completion tokens | 成本 |",
            "|-------|---------:|--------------:|------------------:|-----:|",
        ]
    )
    for row in top_rows:
        lines.append(_usage_row(str(row.get("agent") or "unknown"), row))
    if rest_rows:
        lines.append(_usage_row(f"其他（{len(rest_rows)} 个 agent）", _merge_rows(rest_rows)))
    lines.append("")

    # ---- 每章成本（保持 repo 排序：run 级 NULL 分组在前，其后按章号升序） ----
    lines.extend(
        [
            "### 每章成本",
            "",
            "| 章节 | 调用次数 | prompt tokens | completion tokens | 成本 |",
            "|------|---------:|--------------:|------------------:|-----:|",
        ]
    )
    for row in per_chapter:
        chapter_number = row.get("chapter_number")
        label = RUN_LEVEL_LABEL if chapter_number is None else f"Ch{chapter_number}"
        lines.append(_usage_row(label, row))
    lines.append("")

    return "\n".join(lines)
