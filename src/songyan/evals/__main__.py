"""流式验证报告 CLI 入口.

用法:
    python -m songyan.evals.streaming_report --run-id <run_id> [--output <path>]
    python -m songyan.evals.streaming_report --input <jsonl_path> --output <md_path>

示例:
    python -m songyan.evals.streaming_report --run-id run-8e14bcf1
    python -m songyan.evals.streaming_report --run-id run-8e14bcf1 \
        --output logs/reports/report-run-8e14bcf1.md
    python -m songyan.evals.streaming_report \
        --input logs/chapter_runs/run-8e14bcf1.jsonl --output report.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from songyan.evals.streaming_report import generate_report, read_run_logs, write_report

_LOGS_DIR = Path("logs/chapter_runs")
_DEFAULT_OUTPUT_DIR = Path("logs/reports")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m songyan.evals.streaming_report",
        description="从 JSONL 运行日志生成流式验证 markdown 报告。",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--run-id",
        dest="run_id",
        help="运行 ID（从 logs/chapter_runs/<run_id>.jsonl 读取）",
    )
    group.add_argument(
        "--input",
        dest="input_path",
        type=Path,
        help="JSONL 文件路径（与 --run-id 互斥）",
    )
    parser.add_argument(
        "--output",
        dest="output_path",
        type=Path,
        default=None,
        help="输出 markdown 路径（默认 logs/reports/report-<run_id>.md）",
    )
    parser.add_argument(
        "--start",
        dest="start_chapter",
        type=int,
        default=None,
        help="章节范围起始（默认从 JSONL 自动推断）",
    )
    parser.add_argument(
        "--end",
        dest="end_chapter",
        type=int,
        default=None,
        help="章节范围结束（默认从 JSONL 自动推断）",
    )
    return parser


def _validate_report_consistency(logs: list[object], report_md: str) -> list[str]:
    """验证报告内容与 JSONL 数据一致性，返回警告列表。"""
    warnings: list[str] = []

    if not logs:
        warnings.append("JSONL 中无日志记录")
        return warnings

    total = len(logs)

    # 检查报告是否提及了正确的章节数
    import re

    ch_range = re.findall(r"Ch(\d+)-Ch(\d+)", report_md)
    if ch_range:
        start, end = int(ch_range[0][0]), int(ch_range[0][1])
        reported_total = end - start + 1
        if reported_total != total:
            warnings.append(
                f"报告章节范围 Ch{start}-Ch{end} ({reported_total} 章) "
                f"与 JSONL 条目数 ({total}) 不符"
            )

    # 检查 budget_used 缺失
    missing_budget = [
        getattr(log, "chapter_number", "?")
        for log in logs
        if getattr(log, "success", False) and getattr(log, "budget_used", None) is None
    ]
    if missing_budget:
        warnings.append(f"以下成功章节缺少 budget_used: {missing_budget}")

    # 检查 context_emergency
    emergency_chapters = [
        getattr(log, "chapter_number", "?")
        for log in logs
        if getattr(log, "context_emergency", False)
    ]
    if emergency_chapters:
        warnings.append(f"以下章节触发了 ContextEmergency: {emergency_chapters}")

    return warnings


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    # 读取日志
    if args.run_id:
        run_id = args.run_id
        jsonl_path = _LOGS_DIR / f"{run_id}.jsonl"
        if not jsonl_path.exists():
            print(f"错误: JSONL 文件不存在: {jsonl_path}", file=sys.stderr)
            return 1
        logs = read_run_logs(run_id)
        print(f"从 {jsonl_path} 读取了 {len(logs)} 条日志")
    else:
        jsonl_path = args.input_path
        if not jsonl_path.exists():
            print(f"错误: JSONL 文件不存在: {jsonl_path}", file=sys.stderr)
            return 1
        from songyan.models.run_log import ChapterRunLog

        logs = []
        with open(jsonl_path, encoding="utf-8") as f:
            import json

            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    logs.append(ChapterRunLog.model_validate(data))
                except Exception as exc:
                    print(f"警告: 跳过无效行: {exc}", file=sys.stderr)
        run_id = jsonl_path.stem
        print(f"从 {jsonl_path} 读取了 {len(logs)} 条日志")

    if not logs:
        print("无日志记录，生成空报告。", file=sys.stderr)

    # 确定章节范围
    chapter_range: tuple[int, int] | None = None
    if args.start_chapter is not None and args.end_chapter is not None:
        chapter_range = (args.start_chapter, args.end_chapter)
    elif logs:
        chapter_range = (
            min(getattr(log_, "chapter_number", 0) for log_ in logs),
            max(getattr(log_, "chapter_number", 0) for log_ in logs),
        )

    # 生成报告
    report_md = generate_report(logs, chapter_range=chapter_range)

    # 一致性检查
    warnings = _validate_report_consistency(logs, report_md)
    for w in warnings:
        print(f"警告: {w}", file=sys.stderr)

    # 写入文件
    if args.output_path:
        output_path = args.output_path
    else:
        output_path = _DEFAULT_OUTPUT_DIR / f"report-{run_id}.md"

    output_path = write_report(report_md, run_id, output_path.parent)
    print(f"报告已生成: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
