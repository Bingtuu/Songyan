"""Task 196: 双冻结库分层抽样，落盘样本清单并可导出样本正文."""

from __future__ import annotations

import argparse
import contextlib
import json
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from songyan.evals.excellence_sampling import (
    DEFAULT_SEED,
    SAMPLES_PER_GENRE,
    SEGMENT_SIZE,
    ExcellenceSamplingError,
    load_accepted_chapters,
    load_chapter_content,
    stratified_sample,
)

SOURCES = [
    {
        "genre": "xuanhuan",
        "db": ".tmp/task_v10_xuanhuan_ch200.db",
        "project_id": "d160a55a51de4a2bb82440ebc03ec23a",
        "up_to": 200,
    },
    {
        "genre": "scifi",
        "db": ".tmp/task171_ch1_ch200.db",
        "project_id": "835afdf11a294b5eac74a5d8998bd9a2",
        "up_to": 200,  # 同库另有 Ch201-Ch220 run，对齐 Task 189 baseline 只取 Ch1-Ch200
    },
]

OUTPUT = Path("tasks/196-excellence-sample-set.json")


def _connect_readonly(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise SystemExit(f"DB not found: {db_path}")
    return sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--dump-texts", type=Path, default=None,
                        help="导出样本正文到该目录（供锚点精读/抽审阅读）")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)

    samples: list[dict[str, object]] = []
    for src in SOURCES:
        try:
            with contextlib.closing(_connect_readonly(Path(src["db"]))) as conn:
                chapters = load_accepted_chapters(conn, src["project_id"], src["genre"])
                chapters = [c for c in chapters if c.chapter_number <= src["up_to"]]
                picked = stratified_sample(chapters, per_genre=SAMPLES_PER_GENRE, seed=args.seed)
                if args.dump_texts:
                    args.dump_texts.mkdir(parents=True, exist_ok=True)
                    for c in picked:
                        content = load_chapter_content(conn, c.version_id)
                        out = args.dump_texts / f"{c.genre}-ch{c.chapter_number:03d}.txt"
                        out.write_text(
                            f"# {c.genre} Ch{c.chapter_number} ({c.version_id})\n\n{content}",
                            encoding="utf-8",
                        )
        except ExcellenceSamplingError as exc:
            print(f"build_196_sample_set error: {exc}", file=sys.stderr)
            return 2
        samples.extend(c.to_dict() for c in picked)
        print(f"{src['genre']}: {len(chapters)} accepted -> sampled {len(picked)}")

    payload = {
        "seed": args.seed,
        "segment_size": SEGMENT_SIZE,
        "samples_per_genre": SAMPLES_PER_GENRE,
        "generated_at": datetime.now(UTC).isoformat(),
        "sources": SOURCES,
        "samples": samples,
    }
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"sample set written: {args.output} ({len(samples)} samples)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
