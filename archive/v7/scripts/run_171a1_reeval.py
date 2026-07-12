"""Task 171a-1: cross-genre metric validity reeval (voice + exposition P/R/F1).

Two phases:
  --export : load accepted prose from scifi (170p DB) + wuxia (171a1 DB), run the
             171a-decoupled detectors WITH injected project keywords, and write
             candidate stubs (human_verdict=null) for blind labeling.
  (default): read labeled ground truth, recompute predictions, and emit P/R/F1 to
             docs/reports/task-171a-1-metric-prf-report.md.

Usage:
    python scripts/run_171a1_reeval.py --export
    # (label .tmp/ground_truth/task171a1_*_ground_truth.jsonl human_verdict fields)
    python scripts/run_171a1_reeval.py
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from songyan.agents.rule_auditor import (
    detect_exposition_carriers,
    detect_human_voice_homogeneity,
)

# (genre_label, db_path, project_file)
SOURCES = [
    ("scifi", ".tmp/task170p_validation.db", ".tmp/task170p_validation_project.json"),
    ("wuxia", ".tmp/task171a1_wuxia.db", ".tmp/task171a1_wuxia_project.json"),
]
GT_DIR = Path(".tmp/ground_truth")
REPORT_PATH = Path("docs/reports/task-171a-1-metric-prf-report.md")


def _load_keywords(db_path: str) -> dict[str, set[str]]:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    row = con.execute("SELECT project_id FROM characters LIMIT 1").fetchone()
    if row is None:
        con.close()
        return {
            "character_names": set(),
            "setting_keywords": set(),
            "non_character_keywords": set(),
        }
    pid = row["project_id"]
    chars = {r["name"] for r in con.execute(
        "SELECT name FROM characters WHERE project_id=?", (pid,)
    ) if r["name"]}
    settings_kw = set()
    for r in con.execute(
        "SELECT setting_name FROM setting_snapshots "
        "WHERE project_id=? AND lifecycle_status='active'", (pid,)
    ):
        if r["setting_name"]:
            settings_kw.add(r["setting_name"].strip())
    con.close()
    return {
        "character_names": chars,
        "setting_keywords": settings_kw,
        "non_character_keywords": set(),
    }


def _load_accepted(db_path: str) -> list[tuple[int, str]]:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            "SELECT chapter_number, content FROM chapter_versions "
            "WHERE version_type='accepted' ORDER BY chapter_number"
        ).fetchall()
    except sqlite3.OperationalError:
        rows = []
    con.close()
    return [(r["chapter_number"], r["content"] or "") for r in rows]


def _predict(
    genre: str,
    chapters: list[tuple[int, str]],
    kw: dict[str, set[str]],
) -> list[dict[str, Any]]:
    preds: list[dict[str, Any]] = []
    for ch, content in chapters:
        expo = detect_exposition_carriers(
            content,
            character_names=kw["character_names"],
            setting_keywords=kw["setting_keywords"],
        )
        voice = detect_human_voice_homogeneity(content, character_names=kw["character_names"])
        for m in list(expo) + list(voice):
            preds.append({
                "genre": genre,
                "chapter": ch,
                "carrier_type": m.carrier_type,
                "start": getattr(m, "start", None),
                "end": getattr(m, "end", None),
                "matched_text": m.matched_text[:80],
                "human_verdict": None,
            })
    return preds


def _gt_path(genre: str) -> Path:
    return GT_DIR / f"task171a1_{genre}_ground_truth.jsonl"


def do_export() -> None:
    GT_DIR.mkdir(parents=True, exist_ok=True)
    for genre, db, _pf in SOURCES:
        if not Path(db).exists():
            print(f"[export] SKIP {genre}: db not found {db}")
            continue
        kw = _load_keywords(db)
        chapters = _load_accepted(db)
        preds = _predict(genre, chapters, kw)
        path = _gt_path(genre)
        with path.open("w", encoding="utf-8") as f:
            for p in preds:
                f.write(json.dumps(p, ensure_ascii=False) + "\n")
        print(
            f"[export] {genre}: chapters={len(chapters)} "
            f"registry={sorted(kw['character_names'])} candidates={len(preds)} -> {path}"
        )


def _load_labeled(path: Path) -> tuple[list[dict], list[dict]]:
    """Return (ground_truth_accepted, all_predictions)."""
    gt: list[dict] = []
    preds: list[dict] = []
    if not path.exists():
        return gt, preds
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        preds.append(rec)
        v = rec.get("human_verdict")
        if v == "accept":
            gt.append(rec)
        elif isinstance(v, str) and v.startswith("retype:"):
            r2 = dict(rec)
            r2["carrier_type"] = v.split(":", 1)[1].strip()
            gt.append(r2)
    return gt, preds


def _overlap(a0, a1, b0, b1) -> bool:
    if a0 is None or a1 is None or b0 is None or b1 is None:
        return True
    return min(a1, b1) > max(a0, b0)


def _prf(gt: list[dict], preds: list[dict]) -> dict[str, Any]:
    # The detector EMITTED every candidate, so every candidate is a prediction.
    # GT = candidates labeled accept (真实问题)。rejected candidates remain predictions
    # and therefore correctly count as false positives (precision penalty).
    pred_use = list(preds)
    families = {"voice": {"human_voice_homogeneity"}}
    # exposition = everything else
    def fam(ct: str) -> str:
        return "voice" if ct in families["voice"] else "exposition"

    out: dict[str, Any] = {}
    for family in ("voice", "exposition"):
        g = [r for r in gt if fam(r["carrier_type"]) == family]
        p = [r for r in pred_use if fam(r["carrier_type"]) == family]
        matched_p: set[int] = set()
        matched_g: set[int] = set()
        for gi, gg in enumerate(g):
            for pi, pp in enumerate(p):
                if pi in matched_p or gg["chapter"] != pp["chapter"]:
                    continue
                if not _overlap(gg.get("start"), gg.get("end"), pp.get("start"), pp.get("end")):
                    continue
                matched_g.add(gi)
                matched_p.add(pi)
                break
        tp = len(matched_g)
        fp = len(p) - len(matched_p)
        fn = len(g) - len(matched_g)
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        out[family] = {
            "gt": len(g), "pred": len(p), "tp": tp, "fp": fp, "fn": fn,
            "precision": round(prec, 3), "recall": round(rec, 3), "f1": round(f1, 3),
        }
    return out


def do_report() -> None:
    lines = [
        "# Task 171a-1: 跨体裁量具效度 P/R/F1 报告",
        "",
        f"> 生成时间: {datetime.now().isoformat(timespec='seconds')}",
        "> 对应框架 §8 B2/B3。voice=`human_voice_homogeneity`；exposition=其余 carrier 类型。",
        "",
    ]
    any_labeled = False
    for genre, _db, _pf in SOURCES:
        gt, preds = _load_labeled(_gt_path(genre))
        labeled = sum(1 for p in preds if p.get("human_verdict") is not None)
        lines.append(f"## {genre}")
        lines.append("")
        lines.append(f"- 候选 {len(preds)}，已标注 {labeled}")
        if labeled == 0:
            lines.append("- ⏳ 尚未盲标，无法计算 P/R/F1。")
            lines.append("")
            continue
        any_labeled = True
        prf = _prf(gt, preds)
        lines.append("")
        lines.append("| family | gt | pred | tp | fp | fn | P | R | F1 |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
        for fam_name, s in prf.items():
            lines.append(
                f"| {fam_name} | {s['gt']} | {s['pred']} | {s['tp']} | {s['fp']} | "
                f"{s['fn']} | {s['precision']} | {s['recall']} | {s['f1']} |"
            )
        lines.append("")
    if not any_labeled:
        lines.append("---")
        lines.append(
            "**当前无任何盲标，报告为候选统计骨架。** "
            "先 `--export`，人工标注 human_verdict 后重跑。"
        )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"[report] -> {REPORT_PATH}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--export", action="store_true", help="导出候选供盲标")
    args = parser.parse_args()
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if args.export:
        do_export()
    else:
        do_report()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
