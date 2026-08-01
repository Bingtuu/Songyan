"""Task 196: 规则信号试点——ai_tells + fatigue_words 跑样本集并对照标注."""

from __future__ import annotations

import json
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from songyan.evals.excellence_sampling import load_chapter_content
from songyan.utils.ai_tells import detect_ai_tells
from songyan.utils.fatigue_words import detect_fatigue_words

SAMPLE_SET = Path("archive/v10/artifacts/196-excellence-sample-set.json")
ANNOTATIONS = Path("archive/v10/artifacts/196-excellence-annotations.json")
GENRE_DATA = Path("src/songyan/genres/data")
OUTPUT = Path(".tmp/196_rule_pilot.json")


def _connect_readonly(db_path: str) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{Path(db_path).as_posix()}?mode=ro", uri=True)


def main() -> int:
    sample_set = json.loads(SAMPLE_SET.read_text(encoding="utf-8"))
    annotations = json.loads(ANNOTATIONS.read_text(encoding="utf-8"))
    ann_by_vid = {
        a["version_id"]: a
        for a in annotations["annotations"]
        if a["sample_layer"] in ("anchor", "prelabel") and a["disagreement"] is None
    }
    dbs = {s["genre"]: s["db"] for s in sample_set["sources"]}

    results = []
    for sample in sample_set["samples"]:
        genre = sample["genre"]
        fatigue_words = json.loads(
            (GENRE_DATA / f"{genre}.json").read_text(encoding="utf-8")
        ).get("fatigue_words", [])
        with closing(_connect_readonly(dbs[genre])) as conn:
            content = load_chapter_content(conn, sample["version_id"])
        tells = detect_ai_tells(content)
        fatigue = detect_fatigue_words(content, fatigue_words)
        ann = ann_by_vid.get(sample["version_id"])
        results.append({
            "genre": genre,
            "chapter": sample["chapter"],
            "version_id": sample["version_id"],
            "ai_tell_count": len(tells),
            "ai_tell_categories": sorted({t.pattern.split(":")[0] for t in tells}),
            "fatigue_word_total": sum(f.count for f in fatigue),
            "annotator": ann["annotator"] if ann else None,
            "sample_layer": ann["sample_layer"] if ann else None,
            "ai_tone_score": ann["scores"]["ai_tone"] if ann else None,
            "homogeneity_score": ann["scores"]["homogeneity"] if ann else None,
        })
    OUTPUT.write_text(
        json.dumps({"results": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"pilot done: {len(results)} chapters -> {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
