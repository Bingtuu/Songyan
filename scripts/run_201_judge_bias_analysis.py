"""Task 201 judge bias analysis runner.

Consumes Task 196-200 report artifacts and emits a report-only judge bias
analysis.  It does not call LLMs, does not create prompt cards, and does not
touch runtime gates.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from songyan.evals.judge_bias_analysis import (  # noqa: E402
    JudgeBiasError,
    build_judge_bias_report,
    load_judge_bias_inputs,
    render_judge_bias_report,
)

DEFAULT_SAMPLE_SET = Path("archive/v10/artifacts/196-excellence-sample-set.json")
DEFAULT_ANNOTATIONS = Path("archive/v10/artifacts/196-excellence-annotations.json")
DEFAULT_EXCELLENCE_REPORT = Path("archive/v10/artifacts/197-198-excellence-signals-report.json")
DEFAULT_STYLE_REPORT = Path("archive/v10/artifacts/199-style-card-report.json")
DEFAULT_VOICE_REPORT = Path("archive/v10/artifacts/200-character-voice-anchor-report.json")
DEFAULT_JSON = Path("archive/v10/artifacts/201-judge-bias-report.json")
DEFAULT_MD = Path("archive/v10/reports/201-judge-bias-report.md")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-set", type=Path, default=DEFAULT_SAMPLE_SET)
    parser.add_argument("--annotations", type=Path, default=DEFAULT_ANNOTATIONS)
    parser.add_argument(
        "--excellence-report",
        type=Path,
        default=DEFAULT_EXCELLENCE_REPORT,
    )
    parser.add_argument("--style-card-report", type=Path, default=DEFAULT_STYLE_REPORT)
    parser.add_argument("--voice-anchor-report", type=Path, default=DEFAULT_VOICE_REPORT)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_MD)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        chapters, annotations, excellence_report, style_report, voice_report = (
            load_judge_bias_inputs(
                args.sample_set,
                args.annotations,
                args.excellence_report,
                args.style_card_report,
                args.voice_anchor_report,
            )
        )
        report = build_judge_bias_report(
            chapters,
            annotations,
            excellence_report,
            style_report,
            voice_report,
            sample_set_path=args.sample_set,
            annotations_path=args.annotations,
            excellence_report_path=args.excellence_report,
            style_card_report_path=args.style_card_report,
            voice_anchor_report_path=args.voice_anchor_report,
        )
    except JudgeBiasError as exc:
        print(f"run_201_judge_bias_analysis error: {exc}", file=sys.stderr)
        return 2

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_judge_bias_report(report), encoding="utf-8")
    print(
        "judge bias report written: "
        f"{args.output_json.as_posix()} and {args.output_md.as_posix()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
