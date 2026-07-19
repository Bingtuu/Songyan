"""Formal five-gate replay tool for genre Ch100 climbs."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from songyan.evals.five_gate_acceptance import (  # noqa: E402
    DEFAULT_ALLOWED_GAP,
    FiveGateToolError,
    evaluate_project,
    render_text_report,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--genre", required=True, help="target genre id, used as report label")
    parser.add_argument("--db", required=True, type=Path, help="target SQLite DB path")
    parser.add_argument("--project-id", required=True, help="target project_id")
    parser.add_argument("--up-to", required=True, type=int, help="chapter boundary to evaluate")
    parser.add_argument(
        "--baseline",
        type=Path,
        default=None,
        help="optional sci-fi baseline JSON path; defaults to package resource",
    )
    parser.add_argument(
        "--allow-gap",
        type=int,
        default=DEFAULT_ALLOWED_GAP,
        help="accepted chapter gap tolerated before documented-isolate review",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="output format",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command."""
    args = build_parser().parse_args(argv)
    try:
        report = evaluate_project(
            args.db,
            project_id=args.project_id,
            genre=args.genre,
            up_to=args.up_to,
            baseline_path=args.baseline,
            allow_gap=args.allow_gap,
        )
    except FiveGateToolError as exc:
        print(f"five_gate_check error: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(render_text_report(report))
    return 0 if report.verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
