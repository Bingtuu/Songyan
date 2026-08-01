"""Task 205 FactTrack validity interval spike runner.

Consumes Task 204 manifest/report artifacts and emits a standalone report-only
validity interval spike report. It does not wire into ``songyan report``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from songyan.evals.facttrack_validity_interval import (  # noqa: E402
    FactTrackSpikeError,
    build_facttrack_validity_report,
    load_facttrack_inputs,
    render_facttrack_validity_report,
)

DEFAULT_MANIFEST = Path("tasks/204-kg-diff-sample-manifest.json")
DEFAULT_KG_REPORT = Path("tasks/204-kg-diff-spike-report.json")
DEFAULT_JSON = Path("tasks/205-facttrack-validity-interval-report.json")
DEFAULT_MD = Path("docs/reports/205-facttrack-validity-interval-report.md")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--kg-diff-report", type=Path, default=DEFAULT_KG_REPORT)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_MD)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        inputs = load_facttrack_inputs(
            manifest_path=args.manifest,
            kg_diff_report_path=args.kg_diff_report,
        )
        report = build_facttrack_validity_report(
            inputs,
            manifest_path=args.manifest,
            kg_diff_report_path=args.kg_diff_report,
            root_dir=Path.cwd(),
        )
    except FactTrackSpikeError as exc:
        print(f"run_205_facttrack_validity_interval error: {exc}", file=sys.stderr)
        return 2

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_facttrack_validity_report(report), encoding="utf-8")
    print(
        "FactTrack validity interval report written: "
        f"{args.output_json.as_posix()} and {args.output_md.as_posix()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
