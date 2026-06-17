"""Task 105b: Ch51-Ch100 验证重启.

基于 Task 106~110 + MEMO-001 修复后的代码，重新实跑 Ch51-Ch100，
统一收集 JSONL 过程日志并生成 DG-1 报告.

特点:
- 逐章运行: 每章独立超时，避免单章死循环拖垮整批
- 断点续跑: 自动检测 project_runs，从上次暂停处继续
- 死循环防护: 单章 10min 超时、全局 8h 超时、连续 3 章失败/熔断暂停
- 完整日志: 每章 accept 后自动写入 logs/chapter_runs/<run_id>.jsonl
- 自动报告: 运行结束后生成 logs/reports/report-<run_id>.md

用法:
    python scripts/run_task_105b_ch51_ch100.py --project-id proj-e74ef1e4 --start 51 --end 100
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path
from typing import Any

import structlog

from songyan.config import settings
from songyan.db.project_run_repo import ProjectRunRepository
from songyan.evals.streaming_report import generate_report
from songyan.exceptions import AutoHaltException
from songyan.workflows.phase1_graph import reset_checkpointer
from songyan.workflows.phase2_graph import run_project_pipeline

logger = structlog.get_logger(__name__)

_LOGS_DIR = Path("logs/chapter_runs")
_REPORTS_DIR = Path("logs/reports")

# 死循环/熔断参数
_CHAPTER_TIMEOUT_SEC = 600  # 单章最多 10 分钟
_GLOBAL_TIMEOUT_SEC = 8 * 3600  # 全局最多 8 小时
_MAX_CONSECUTIVE_FAILURES = 3  # 连续失败 3 章暂停（与 run_project_pipeline 内部熔断对齐）


async def _run_single_chapter_with_timeout(
    project_id: str,
    chapter_number: int,
    max_revision_rounds: int,
) -> dict[str, Any]:
    """单章运行，带超时保护."""
    start_at = time.monotonic()
    try:
        result = await asyncio.wait_for(
            run_project_pipeline(
                project_id=project_id,
                chapter_range=(chapter_number, chapter_number),
                mode_id="webnovel",
                auto_confirm=True,
                max_revision_rounds=max_revision_rounds,
                on_failure="retry",
                continuity_health_threshold=7.0,
            ),
            timeout=_CHAPTER_TIMEOUT_SEC,
        )
        return {
            "result": result,
            "elapsed_sec": time.monotonic() - start_at,
            "error": None,
        }
    except TimeoutError:
        return {
            "result": None,
            "error": f"单章超时 (> {_CHAPTER_TIMEOUT_SEC}s)",
            "elapsed_sec": time.monotonic() - start_at,
        }
    except AutoHaltException as exc:
        return {
            "result": None,
            "error": f"自动熔断: {exc.message}",
            "elapsed_sec": time.monotonic() - start_at,
            "auto_halt": exc,
        }


async def _find_resume_point(project_id: str, start: int, end: int) -> int:
    """查找可续跑的起始章节.

    检查 project_runs 表中最近一次的 completed_chapters，返回下一章.
    如果没有运行记录，返回用户指定的 start.
    """
    repo = ProjectRunRepository()
    runs = await repo.list_by_project(project_id, limit=5)
    if not runs:
        return start

    for run in runs:
        if run.chapter_range_start == start and run.chapter_range_end == end:
            if run.status == "paused" and run.completed_chapters:
                return max(run.completed_chapters) + 1
            if run.status == "completed":
                return end + 1
    return start


async def _generate_report(
    run_ids: list[str],
    project_id: str,
    start: int,
    end: int,
    primary_run_id: str | None = None,
) -> Path:
    """读取本次运行的 JSONL 日志并生成 markdown 报告.

    由于逐章运行会为每章创建独立的 run_id，需要汇总所有 run_id 的日志。
    """
    from songyan.models.run_log import ChapterRunLog

    logs: list[ChapterRunLog] = []
    seen_chapters: set[int] = set()
    for run_id in run_ids:
        log_path = _LOGS_DIR / f"{run_id}.jsonl"
        if not log_path.exists():
            continue
        with log_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = ChapterRunLog.model_validate_json(line)
                    if (
                        data.project_id == project_id
                        and start <= data.chapter_number <= end
                        and data.chapter_number not in seen_chapters
                    ):
                        logs.append(data)
                        seen_chapters.add(data.chapter_number)
                except Exception:
                    continue

    logs.sort(key=lambda x: x.chapter_number)
    report_md = generate_report(logs, chapter_range=(start, end))

    _REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_name = f"report-{primary_run_id or run_ids[-1] if run_ids else 'unknown'}.md"
    report_path = _REPORTS_DIR / report_name
    report_path.write_text(report_md, encoding="utf-8")
    return report_path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python scripts/run_task_105b_ch51_ch100.py",
        description="Task 105b: Ch51-Ch100 验证重启",
    )
    parser.add_argument(
        "--project-id",
        default="proj-e74ef1e4",
        help="项目 ID（默认 proj-e74ef1e4）",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=51,
        help="起始章节（默认 51）",
    )
    parser.add_argument(
        "--end",
        type=int,
        default=100,
        help="结束章节（默认 100）",
    )
    parser.add_argument(
        "--max-revision-rounds",
        type=int,
        default=2,
        help="单章最大 revision 轮数（默认 2）",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="不续跑，强制从 --start 开始",
    )
    return parser


async def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if not settings.llm_api_key:
        print("LLM_API_KEY 未配置，请在 .env 中设置")
        return 1

    start = args.start
    end = args.end
    project_id = args.project_id
    original_start = start

    if not args.no_resume:
        resume_start = await _find_resume_point(project_id, start, end)
        if resume_start > end:
            print(f"项目 {project_id} 的 Ch{start}-Ch{end} 已经标记为完成，无需重跑")
            return 0
        if resume_start != start:
            print(f"从 Ch{resume_start} 续跑（已完成的章节跳过）")
            start = resume_start

    print(f"\n{'='*60}")
    print(f"Task 105b: Ch{start}-Ch{end} 验证重启")
    print(f"   项目 ID: {project_id}")
    print(f"   单章超时: {_CHAPTER_TIMEOUT_SEC}s")
    print(f"   全局超时: {_GLOBAL_TIMEOUT_SEC / 3600:.1f}h")
    print(f"   连续失败熔断: {_MAX_CONSECUTIVE_FAILURES} 章")
    print(f"{'='*60}\n")

    await reset_checkpointer()

    run_id: str | None = None
    run_ids: list[str] = []
    completed: list[int] = []
    failed: list[int] = []
    consecutive_failures = 0
    global_start = time.monotonic()

    for chapter_number in range(start, end + 1):
        if time.monotonic() - global_start > _GLOBAL_TIMEOUT_SEC:
            print(f"\n全局超时 (> {_GLOBAL_TIMEOUT_SEC / 3600:.1f}h)，暂停运行")
            print("可重新运行脚本以续跑")
            break

        print(f"\n[Ch{chapter_number}] 开始...")
        outcome = await _run_single_chapter_with_timeout(
            project_id=project_id,
            chapter_number=chapter_number,
            max_revision_rounds=args.max_revision_rounds,
        )

        if outcome.get("auto_halt"):
            exc = outcome["auto_halt"]
            print(f"自动熔断：{exc.message}")
            print(f"   最后章节: Ch{exc.last_chapter}")
            print(f"   原因: {exc.reason}")
            print("可重新运行脚本以续跑")
            break

        if outcome.get("error"):
            print(f"失败: {outcome['error']}")
            failed.append(chapter_number)
            consecutive_failures += 1
        else:
            result = outcome["result"]
            if result:
                run_id = result.run_id
                run_ids.append(run_id)
            if result and chapter_number not in result.chapters_failed:
                completed.append(chapter_number)
                consecutive_failures = 0
                print(f"成功 | {outcome['elapsed_sec']:.1f}s")
            else:
                failed.append(chapter_number)
                consecutive_failures += 1
                print(f"失败 | {outcome['elapsed_sec']:.1f}s")

        if consecutive_failures >= _MAX_CONSECUTIVE_FAILURES:
            print(f"\n连续 {consecutive_failures} 章失败，暂停运行")
            print("可重新运行脚本以续跑")
            break

    total_elapsed = time.monotonic() - global_start

    print(f"\n{'='*60}")
    print("运行结束")
    print(f"   完成: {completed}")
    print(f"   失败: {failed}")
    print(f"   总耗时: {total_elapsed / 60:.1f} 分钟")

    if run_ids:
        primary_run_id = run_ids[-1]
        report_path = await _generate_report(
            run_ids, project_id, original_start, end, primary_run_id=primary_run_id
        )
        print(f"   报告: {report_path}")
    else:
        print("   没有生成 run_id，无法生成报告")

    return 0 if not failed else 1


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        print("\n\n用户中断，已完成的章节会保留在 project_runs 中")
        sys.exit(130)
