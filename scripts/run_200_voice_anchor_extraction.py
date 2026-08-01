"""Task 200 character voice anchor report runner.

Runs offline report-only character voice extraction over Task 196 accepted
samples and Task 197/198/199 report artifacts.  It does not write to SQLite,
does not generate DialogueStyleCard, and does not inject prompt constraints.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from songyan.evals.voice_anchor_extraction import (  # noqa: E402
    VoiceAnchorError,
    VoiceScopeMode,
    build_voice_anchor_report,
    load_voice_anchor_inputs,
    render_voice_anchor_report,
)

DEFAULT_SAMPLE_SET = Path("archive/v10/artifacts/196-excellence-sample-set.json")
DEFAULT_ANNOTATIONS = Path("archive/v10/artifacts/196-excellence-annotations.json")
DEFAULT_EXCELLENCE_REPORT = Path("archive/v10/artifacts/197-198-excellence-signals-report.json")
DEFAULT_STYLE_REPORT = Path("archive/v10/artifacts/199-style-card-report.json")
DEFAULT_JSON = Path("archive/v10/artifacts/200-character-voice-anchor-report.json")
DEFAULT_MD = Path("archive/v10/reports/200-character-voice-anchor-report.md")


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
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_MD)
    parser.add_argument(
        "--scope",
        choices=["all", "by-genre", "both"],
        default="both",
        help="voice anchor scope: overall, per-genre, or both",
    )
    parser.add_argument(
        "--min-lines",
        type=int,
        default=2,
        help="minimum attributed dialogue lines required for one character anchor",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        chapters, annotations, excellence_report, style_report, registry = (
            load_voice_anchor_inputs(
                args.sample_set,
                args.annotations,
                args.excellence_report,
                args.style_card_report,
            )
        )
        report = build_voice_anchor_report(
            chapters,
            annotations,
            excellence_report,
            style_report,
            registry,
            sample_set_path=args.sample_set,
            annotations_path=args.annotations,
            excellence_report_path=args.excellence_report,
            style_card_report_path=args.style_card_report,
            scope_mode=cast(VoiceScopeMode, args.scope),
            min_lines=max(1, args.min_lines),
        )
    except VoiceAnchorError as exc:
        print(f"run_200_voice_anchor_extraction error: {exc}", file=sys.stderr)
        return 2

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_voice_anchor_report(report), encoding="utf-8")
    print(
        "voice anchor report written: "
        f"{args.output_json.as_posix()} and {args.output_md.as_posix()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
