"""Task 166a: offline arc outcome evaluation and draft re-plan proposal."""

from __future__ import annotations

import argparse
import asyncio
import sys

from songyan.db.migrations import init_schema
from songyan.db.replan_repo import ReplanProposalRepository
from songyan.evals.replan_evaluation import (
    build_replan_proposal,
    evaluate_arc_outcome,
)


def _parse_chapters(value: str | None) -> tuple[int, int] | None:
    if not value:
        return None
    if "-" not in value:
        chapter = int(value)
        return chapter, chapter
    start, end = value.split("-", 1)
    return int(start), int(end)


async def _run(args: argparse.Namespace) -> int:
    await init_schema()
    evaluation = await evaluate_arc_outcome(
        args.project_id,
        arc_index=args.arc_index,
        chapter_range=_parse_chapters(args.chapters),
    )
    proposal = build_replan_proposal(evaluation)
    if not args.no_persist:
        await ReplanProposalRepository().create(proposal)
    sys.stdout.write(proposal.model_dump_json(indent=2))
    sys.stdout.write("\n")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a draft ReplanProposal from SQLite facts."
    )
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--arc-index", type=int, default=None)
    parser.add_argument("--chapters", default=None, help="章节范围，如 1-20")
    parser.add_argument(
        "--no-persist",
        action="store_true",
        help="只预览 proposal，不写入 replan_proposals/replan_actions",
    )
    return parser


async def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    return await _run(args)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
