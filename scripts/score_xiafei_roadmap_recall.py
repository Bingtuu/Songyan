"""Score 霞飞路 ch1–3 against the five roadmap classes.

The occurrence file is required before a recall total is written. Missing
phrases are not treated as "the error did not happen".

Example::

    python scripts/score_xiafei_roadmap_recall.py \\
        --chapters-dir docs/archive/experiments/xiafei-plan-gate-rerun-2026-10-25/chapters \\
        --occurred docs/archive/experiments/xiafei-plan-gate-rerun-2026-10-25/occurred.json \\
        --extracts docs/archive/experiments/xiafei-plan-gate-rerun-2026-10-25/extracts.json

``--live-path`` omits claim anchors and attribute extracts, which is what
``rule_auditor_node`` does when the review state leaves those keys unset.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import tempfile
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    """Load approved cards, run the gate, and write a scoreboard."""
    parser = argparse.ArgumentParser(description="Score the five 霞飞路 roadmap classes")
    parser.add_argument("--chapters-dir", type=Path, required=True)
    parser.add_argument("--occurred", type=Path, default=None)
    parser.add_argument("--extracts", type=Path, default=None)
    parser.add_argument("--anchors", type=Path, default=None)
    parser.add_argument(
        "--live-path",
        action="store_true",
        help="do not pass anchors or extracts (matches the unset review state)",
    )
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    chapters = {
        number: (args.chapters_dir / f"ch0{number}.md").read_text(encoding="utf-8")
        for number in (1, 2, 3)
    }
    occurred = None if args.occurred is None else _occurred(args.occurred)
    anchor_payload = None
    extract_payload = None
    if not args.live_path:
        anchor_path = args.anchors or _default_anchors()
        anchor_payload = json.loads(anchor_path.read_text(encoding="utf-8"))
        if args.extracts is not None:
            extract_payload = json.loads(args.extracts.read_text(encoding="utf-8"))

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/score.db"
        board = asyncio.run(
            _score(chapters, extract_payload, anchor_payload, occurred)
        )

    payload = board.model_dump()
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output is None:
        print(text, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        print(
            f"status={board.status} recalled={board.recalled}/5"
            if board.recalled is not None
            else f"status={board.status} recalled=unscored"
        )
    return 0 if board.status != "blocked" else 2


def _default_anchors() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "tests"
        / "fixtures"
        / "xiafei_jiuan"
        / "claim_anchors.json"
    )


def _occurred(path: Path) -> dict[str, bool]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("occurred file must be an object")
    flags: dict[str, bool] = {}
    for key, value in payload.items():
        if value is None:
            continue
        if not isinstance(value, bool):
            raise SystemExit(f"occurred.{key} must be true, false, or null")
        flags[str(key)] = value
    return flags


async def _score(
    chapters: dict[int, str],
    extract_payload: object,
    anchor_payload: object,
    occurred: dict[str, bool] | None,
) -> object:
    from songyan.db.migrations import init_schema
    from songyan.db.plan_fact_loader import (
        XIAFEI_PROJECT_ID,
        bundled_xiafei_fixture,
        load_plan_fact_fixture,
    )
    from songyan.plan_checks.claim_check import ClaimAnchor
    from songyan.plan_checks.roadmap_recall import score_chapters
    from songyan.plan_checks.typed_attributes import AttributeExtract

    extracts = None
    if extract_payload is not None:
        extracts = [
            AttributeExtract.model_validate(row) for row in _extract_rows(extract_payload)
        ]
    anchors = None
    if anchor_payload is not None:
        if not isinstance(anchor_payload, list):
            raise SystemExit("anchors file must be a list")
        anchors = [ClaimAnchor.model_validate(row) for row in anchor_payload]

    await init_schema()
    await load_plan_fact_fixture(bundled_xiafei_fixture())
    return await score_chapters(
        chapters,
        project_id=XIAFEI_PROJECT_ID,
        extracts=extracts,
        anchors=anchors,
        occurred=occurred,
    )


def _extract_rows(payload: object) -> list[object]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("chapters"), dict):
        rows: list[object] = []
        for chapter_rows in payload["chapters"].values():
            if not isinstance(chapter_rows, list):
                raise SystemExit("extract chapters must be lists")
            rows.extend(chapter_rows)
        return rows
    raise SystemExit("extracts file must be a list or {chapters: {...}}")


if __name__ == "__main__":
    raise SystemExit(main())
