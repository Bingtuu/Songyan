"""Task 204 KG graph diff spike runner.

Consumes a Task 204 sample manifest and emits a standalone report-only KG diff
spike report. It does not wire into ``songyan report``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from songyan.evals.kg_diff_spike import (  # noqa: E402
    KGDiffSpikeError,
    KGDiffSpikeReport,
    build_kg_diff_spike_report,
    load_kg_diff_manifest,
    render_kg_diff_spike_report,
)

DEFAULT_MANIFEST = Path("archive/v10/artifacts/204-kg-diff-sample-manifest.json")
DEFAULT_JSON = Path("archive/v10/artifacts/204-kg-diff-spike-report.json")
DEFAULT_MD = Path("archive/v10/reports/204-kg-diff-spike-report.md")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_MD)
    return parser


def _compact_json_report(report: KGDiffSpikeReport) -> dict[str, Any]:
    """Return a compact JSON payload without full graph snapshot rows."""
    data = report.model_dump(
        mode="json",
        exclude={
            "samples": {
                "__all__": {
                    "before_snapshot": True,
                    "after_snapshot": True,
                }
            }
        },
    )
    for sample_data, sample in zip(data["samples"], report.samples, strict=True):
        sample_data["before_snapshot_summary"] = _snapshot_summary(
            sample.before_snapshot
        )
        sample_data["after_snapshot_summary"] = _snapshot_summary(sample.after_snapshot)
    return data


def _snapshot_summary(snapshot: Any | None) -> dict[str, Any] | None:
    if snapshot is None:
        return None
    return {
        "label": snapshot.label,
        "source_db": snapshot.source_db,
        "project_id": snapshot.project_id,
        "up_to_chapter": snapshot.up_to_chapter,
        "version_id": snapshot.version_id,
        "node_count": len(snapshot.nodes),
        "edge_count": len(snapshot.edges),
        "counts": snapshot.counts,
        "warnings": snapshot.warnings,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        manifest = load_kg_diff_manifest(args.manifest)
        report = build_kg_diff_spike_report(
            manifest,
            manifest_path=args.manifest,
            root_dir=Path.cwd(),
        )
    except KGDiffSpikeError as exc:
        print(f"run_204_kg_diff_spike error: {exc}", file=sys.stderr)
        return 2

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(_compact_json_report(report), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_kg_diff_spike_report(report), encoding="utf-8")
    print(
        "KG diff spike report written: "
        f"{args.output_json.as_posix()} and {args.output_md.as_posix()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
