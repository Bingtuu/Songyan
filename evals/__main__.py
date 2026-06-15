"""评测 CLI 入口.

用法:
    python -m evals --seed-config evals/seeds/xuanhuan_webnovel.json \
                    --seed-chapter evals/seeds/chapters/xuanhuan_ch1.md \
                    --output-dir evals/output/xuanhuan_run_01 \
                    --auto-accept
"""

from __future__ import annotations

import argparse
import asyncio
import sys

import structlog

from evals.runner import run_seed_project
from songyan.db.migrations import init_schema
from songyan.workflows.phase1_graph import reset_checkpointer

logger = structlog.get_logger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m evals",
        description="Songyan 种子项目评测 runner",
    )
    parser.add_argument("--seed-config", required=True, help="种子项目配置 JSON 路径")
    parser.add_argument("--seed-chapter", required=True, help="种子章节 Markdown 路径")
    parser.add_argument("--output-dir", required=True, help="评测结果输出目录")
    parser.add_argument(
        "--auto-accept",
        action="store_true",
        default=True,
        help="自动接受 human_confirm（默认 True）",
    )
    parser.add_argument(
        "--no-auto-accept",
        action="store_false",
        dest="auto_accept",
        help="不自动接受，流程在中断处停止",
    )
    return parser


async def _main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    # 每次运行前初始化 DB schema 并重置 checkpointer
    await init_schema()
    await reset_checkpointer()

    logger.info(
        "evals.start",
        config=args.seed_config,
        chapter=args.seed_chapter,
        output=args.output_dir,
        auto_accept=args.auto_accept,
    )

    try:
        result = await run_seed_project(
            project_config_path=args.seed_config,
            seed_chapter_path=args.seed_chapter,
            output_dir=args.output_dir,
            auto_accept=args.auto_accept,
        )
    except Exception as exc:
        logger.error("evals.failed", error=str(exc))
        raise

    print(f"\n评测完成: success={result.success}, duration={result.duration_ms}ms")
    print(f"输出目录: {result.output_dir}")
    print(f"project_id: {result.project_id}")
    if result.success:
        print(f"  chapter_version_id: {result.chapter_version_id}")
        print(f"  settlement_id: {result.settlement_id}")
        print(f"  summary_id: {result.summary_id}")
    else:
        print("  流程未到达 done 状态，请检查日志。")
        for log in result.logs:
            print(f"  log: {log}")
        return 1

    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(_main()))
    except KeyboardInterrupt:
        print("\n已取消。")
        sys.exit(130)
