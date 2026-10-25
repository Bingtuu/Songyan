"""Load an ADR-0001 plan-fact fixture into the configured SQLite database.

Example::

    DATABASE_URL=sqlite:///songyan.db python scripts/load_plan_facts.py

With no path, loads the shipped 霞飞路《旧案》 ch1–3 cards.
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from songyan.db.plan_fact_loader import bundled_xiafei_fixture, load_plan_fact_fixture


def main(argv: list[str] | None = None) -> None:
    """Parse args and load one fixture."""
    parser = argparse.ArgumentParser(description="Load plan-fact cards into SQLite")
    parser.add_argument(
        "fixture",
        nargs="?",
        type=Path,
        default=bundled_xiafei_fixture(),
        help="fixture JSON (default: 霞飞路《旧案》 ch1–3)",
    )
    parser.add_argument(
        "--project-id",
        default=None,
        help="write the cards onto this project id (default: the id in the fixture)",
    )
    args = parser.parse_args(argv)
    bundle = asyncio.run(load_plan_fact_fixture(args.fixture, project_id=args.project_id))
    print(
        f"loaded project {bundle.project_id}: "
        f"{len(bundle.entities)} entities, "
        f"{len(bundle.attributes)} attributes, "
        f"{len(bundle.events)} events, "
        f"{len(bundle.time_anchors)} time anchors, "
        f"{len(bundle.clues)} clues"
    )


if __name__ == "__main__":
    main()
