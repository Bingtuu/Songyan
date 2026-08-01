"""Task 203 integrated excellence report runner.

Consumes Task 196-202 offline artifacts and emits a standalone report-only
integrated excellence view.  It does not wire into ``songyan report``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from songyan.evals.excellence_report_integration import (  # noqa: E402
    ExcellenceIntegrationError,
    build_integrated_excellence_report,
    load_integration_inputs,
    render_integrated_excellence_report,
)

DEFAULT_SAMPLE_SET = Path("tasks/196-excellence-sample-set.json")
DEFAULT_ANNOTATIONS = Path("tasks/196-excellence-annotations.json")
DEFAULT_EXCELLENCE_REPORT = Path("tasks/197-198-excellence-signals-report.json")
DEFAULT_STYLE_REPORT = Path("tasks/199-style-card-report.json")
DEFAULT_VOICE_REPORT = Path("tasks/200-character-voice-anchor-report.json")
DEFAULT_JUDGE_REPORT = Path("tasks/201-judge-bias-report.json")
DEFAULT_READABILITY_REPORT = Path("tasks/202-readability-feasibility-report.json")
DEFAULT_JSON = Path("tasks/203-excellence-integrated-report.json")
DEFAULT_MD = Path("docs/reports/203-excellence-integrated-report.md")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-set", type=Path, default=DEFAULT_SAMPLE_SET)
    parser.add_argument("--annotations", type=Path, default=DEFAULT_ANNOTATIONS)
    parser.add_argument("--excellence-report", type=Path, default=DEFAULT_EXCELLENCE_REPORT)
    parser.add_argument("--style-card-report", type=Path, default=DEFAULT_STYLE_REPORT)
    parser.add_argument("--voice-anchor-report", type=Path, default=DEFAULT_VOICE_REPORT)
    parser.add_argument("--judge-bias-report", type=Path, default=DEFAULT_JUDGE_REPORT)
    parser.add_argument("--readability-report", type=Path, default=DEFAULT_READABILITY_REPORT)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_MD)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        inputs = load_integration_inputs(
            sample_set_path=args.sample_set,
            annotations_path=args.annotations,
            excellence_report_path=args.excellence_report,
            style_card_report_path=args.style_card_report,
            voice_anchor_report_path=args.voice_anchor_report,
            judge_bias_report_path=args.judge_bias_report,
            readability_report_path=args.readability_report,
        )
        report = build_integrated_excellence_report(
            inputs,
            sample_set_path=args.sample_set,
            annotations_path=args.annotations,
            excellence_report_path=args.excellence_report,
            style_card_report_path=args.style_card_report,
            voice_anchor_report_path=args.voice_anchor_report,
            judge_bias_report_path=args.judge_bias_report,
            readability_report_path=args.readability_report,
        )
    except ExcellenceIntegrationError as exc:
        print(f"run_203_excellence_report_integration error: {exc}", file=sys.stderr)
        return 2

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_integrated_excellence_report(report), encoding="utf-8")
    print(
        "integrated excellence report written: "
        f"{args.output_json.as_posix()} and {args.output_md.as_posix()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
