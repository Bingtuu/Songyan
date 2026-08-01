"""Task 206 Storyline Tree spike runner.

Consumes Task 204/205 artifacts and emits a standalone report-only Storyline
Tree spike report. It does not wire into ``songyan report``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from songyan.evals.storyline_tree_spike import (  # noqa: E402
    StorylineTreeSpikeError,
    build_storyline_tree_report,
    load_storyline_tree_inputs,
    render_storyline_tree_report,
)

DEFAULT_MANIFEST = Path("archive/v10/artifacts/204-kg-diff-sample-manifest.json")
DEFAULT_KG_REPORT = Path("archive/v10/artifacts/204-kg-diff-spike-report.json")
DEFAULT_FACTTRACK_REPORT = Path("archive/v10/artifacts/205-facttrack-validity-interval-report.json")
DEFAULT_JSON = Path("archive/v10/artifacts/206-storyline-tree-spike-report.json")
DEFAULT_MD = Path("archive/v10/reports/206-storyline-tree-spike-report.md")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--kg-diff-report", type=Path, default=DEFAULT_KG_REPORT)
    parser.add_argument("--facttrack-report", type=Path, default=DEFAULT_FACTTRACK_REPORT)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_MD)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        inputs = load_storyline_tree_inputs(
            manifest_path=args.manifest,
            kg_diff_report_path=args.kg_diff_report,
            facttrack_report_path=args.facttrack_report,
        )
        report = build_storyline_tree_report(
            inputs,
            manifest_path=args.manifest,
            kg_diff_report_path=args.kg_diff_report,
            facttrack_report_path=args.facttrack_report,
            root_dir=Path.cwd(),
        )
    except StorylineTreeSpikeError as exc:
        print(f"run_206_storyline_tree_spike error: {exc}", file=sys.stderr)
        return 2

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_storyline_tree_report(report), encoding="utf-8")
    print(
        "Storyline Tree spike report written: "
        f"{args.output_json.as_posix()} and {args.output_md.as_posix()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
