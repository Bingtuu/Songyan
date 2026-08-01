"""Task 197/198 offline excellence signals runner.

Runs report-only signals over the Task 196 sample set.  It does not write to
SQLite and does not affect generation, CED, five-gate, segment audit, or T9.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from songyan.evals.excellence_signals import (  # noqa: E402
    ExcellenceSignalError,
    build_excellence_signal_report,
    load_task196_inputs,
    render_excellence_signal_report,
)

DEFAULT_SAMPLE_SET = Path("archive/v10/artifacts/196-excellence-sample-set.json")
DEFAULT_ANNOTATIONS = Path("archive/v10/artifacts/196-excellence-annotations.json")
DEFAULT_JSON = Path("archive/v10/artifacts/197-198-excellence-signals-report.json")
DEFAULT_MD = Path("archive/v10/reports/197-198-excellence-signals-report.md")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-set", type=Path, default=DEFAULT_SAMPLE_SET)
    parser.add_argument("--annotations", type=Path, default=DEFAULT_ANNOTATIONS)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_MD)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        chapters, annotations = load_task196_inputs(args.sample_set, args.annotations)
        report = build_excellence_signal_report(
            chapters,
            annotations,
            sample_set_path=args.sample_set,
            annotations_path=args.annotations,
        )
    except ExcellenceSignalError as exc:
        print(f"run_197_198_excellence_signals error: {exc}", file=sys.stderr)
        return 2

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_excellence_signal_report(report), encoding="utf-8")
    print(
        "excellence signals written: "
        f"{args.output_json.as_posix()} and {args.output_md.as_posix()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
