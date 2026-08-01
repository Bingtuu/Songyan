"""Task 199 style extraction -> style card runner.

Runs offline report-only style extraction over Task 196 samples and Task
197/198 signal output.  The generated style cards are not prompt cards and are
not injected into any runtime path.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from songyan.evals.style_card_extraction import (  # noqa: E402
    StyleCardError,
    StyleScopeMode,
    build_style_card_report,
    load_style_card_inputs,
    render_style_card_report,
)

DEFAULT_SAMPLE_SET = Path("archive/v10/artifacts/196-excellence-sample-set.json")
DEFAULT_ANNOTATIONS = Path("archive/v10/artifacts/196-excellence-annotations.json")
DEFAULT_EXCELLENCE_REPORT = Path("archive/v10/artifacts/197-198-excellence-signals-report.json")
DEFAULT_JSON = Path("archive/v10/artifacts/199-style-card-report.json")
DEFAULT_MD = Path("archive/v10/reports/199-style-card-report.md")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-set", type=Path, default=DEFAULT_SAMPLE_SET)
    parser.add_argument("--annotations", type=Path, default=DEFAULT_ANNOTATIONS)
    parser.add_argument(
        "--excellence-report",
        type=Path,
        default=DEFAULT_EXCELLENCE_REPORT,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_MD)
    parser.add_argument(
        "--scope",
        choices=["all", "by-genre", "both"],
        default="both",
        help="style card scope: overall, per-genre, or both",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        chapters, annotations, excellence_report = load_style_card_inputs(
            args.sample_set,
            args.annotations,
            args.excellence_report,
        )
        report = build_style_card_report(
            chapters,
            annotations,
            excellence_report,
            sample_set_path=args.sample_set,
            annotations_path=args.annotations,
            excellence_report_path=args.excellence_report,
            scope_mode=cast(StyleScopeMode, args.scope),
        )
    except StyleCardError as exc:
        print(f"run_199_style_card_extraction error: {exc}", file=sys.stderr)
        return 2

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_style_card_report(report), encoding="utf-8")
    print(
        "style card report written: "
        f"{args.output_json.as_posix()} and {args.output_md.as_posix()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
