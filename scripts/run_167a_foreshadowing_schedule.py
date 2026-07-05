"""Task 167a: offline active foreshadowing schedule generation."""

from __future__ import annotations

import argparse
import asyncio
import sys

from songyan.db.foreshadowing_schedule_repo import ForeshadowingScheduleRepository
from songyan.db.migrations import init_schema
from songyan.evals.foreshadowing_schedule import generate_foreshadowing_schedule_plan


async def _run(args: argparse.Namespace) -> int:
    await init_schema()
    plan = await generate_foreshadowing_schedule_plan(
        args.project_id,
        target_chapter=args.target_chapter,
        horizon_chapters=args.horizon,
        max_items=args.max_items,
        duplicate_window=args.duplicate_window,
    )
    if not args.no_persist:
        await ForeshadowingScheduleRepository().create(plan)
    sys.stdout.write(plan.model_dump_json(indent=2))
    sys.stdout.write("\n")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a draft foreshadowing schedule plan from SQLite facts."
    )
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--target-chapter", required=True, type=int)
    parser.add_argument("--horizon", default=5, type=int)
    parser.add_argument("--max-items", default=3, type=int)
    parser.add_argument("--duplicate-window", default=3, type=int)
    parser.add_argument(
        "--no-persist",
        action="store_true",
        help="只预览 schedule plan，不写入 foreshadowing_schedule_* 表",
    )
    return parser


async def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    return await _run(args)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
