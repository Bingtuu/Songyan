"""Formal segment-boundary audit tool for Ch100 climbs."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from songyan.evals.five_gate_acceptance import FiveGateToolError  # noqa: E402
from songyan.evals.segment_audit import (  # noqa: E402
    collect_segment_audit,
    render_segment_audit,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path, help="target SQLite DB path")
    parser.add_argument("--project-id", required=True, help="target project_id")
    parser.add_argument("--up-to", type=int, default=None, help="chapter boundary to audit")
    parser.add_argument(
        "--genre",
        default=None,
        help="genre id; orphan thresholds follow GenreRuntimeProfile when set",
    )
    parser.add_argument("--top", type=int, default=8, help="number of hotspot chapters")
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
        report = collect_segment_audit(
            args.db,
            project_id=args.project_id,
            up_to=args.up_to,
            top=args.top,
            genre=args.genre,
        )
    except FiveGateToolError as exc:
        print(f"segment_audit error: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(render_segment_audit(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
