"""Task 171c: offline literary-lever A/B measurement harness (框架 §8 R2 / §6.2 支柱4).

Provides the *measurement instrument* every lever arm shares: score a set of
accepted chapters on the 171a-validated detectors, restricted to 171b's
dialogue-carrying layer (so voice is only counted where it's measurable). This
lets us compare any two "arms" (baseline vs post-processed vs temperature vs
model-swap) apples-to-apples, with an explicit marginal-gain / exit judgment.

This module does NOT change any detector and does NOT call an LLM. It only reads
accepted prose and runs the existing detectors + stratifier.

Usage:
    # score a DB's accepted chapters into an arm summary JSON
    python scripts/run_171c_ab.py score --db .tmp/task170p_validation.db --arm baseline_scifi
    # compare two scored arms and emit marginal-gain + exit verdict
    python scripts/run_171c_ab.py compare --base baseline_scifi --arm postproc_scifi
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from songyan.agents.rule_auditor import (  # noqa: E402
    _VOICE_QUOTE_RE,
    detect_exposition_carriers,
    detect_human_voice_homogeneity,
)
from songyan.utils.literary_postproc import split_long_expository_quotes  # noqa: E402
from songyan.utils.sampling import classify_dialogue_layer, is_voice_applicable  # noqa: E402

ARM_DIR = Path(".tmp/task171c")
# 边际增益判定：exposition 命中数每章下降 >= 该比例才算"提升"（框架退出判据）。
MARGINAL_GAIN_MIN = 0.10  # 10% 相对降幅


def _load_registry(db_path: str) -> set[str]:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    row = con.execute("SELECT project_id FROM characters LIMIT 1").fetchone()
    if row is None:
        con.close()
        return set()
    pid = row["project_id"]
    names = {
        r["name"]
        for r in con.execute("SELECT name FROM characters WHERE project_id=?", (pid,))
        if r["name"]
    }
    con.close()
    return names


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


def score_db(db_path: str, arm: str, *, postproc: bool = False) -> dict[str, Any]:
    """Score a DB's dialogue-carrying accepted chapters; write + return arm summary.

    If ``postproc`` is set, apply the deterministic content-preserving
    exposition-quote split (171c 杠杆) to each chapter *before* scoring, so the
    arm measures "baseline + deterministic post-processing".
    """
    registry = _load_registry(db_path)
    per_chapter: list[dict[str, Any]] = []
    total_splits = 0
    for ch, content in _load_accepted(db_path):
        if postproc:
            content, splits = split_long_expository_quotes(content)
            total_splits += splits
        quotes = len(_VOICE_QUOTE_RE.findall(content))
        layer, _density = classify_dialogue_layer(len(content), quotes)
        if not is_voice_applicable(layer):
            continue  # 稀疏章不纳入文学提质 A/B（对治样本错配）
        expo = detect_exposition_carriers(content, character_names=registry)
        voice = detect_human_voice_homogeneity(content, character_names=registry)
        # exposition 单条命中（排除 aggregate 计数，避免双计干扰边际判定）
        expo_single = [m for m in expo if m.carrier_type != "repeated_revelation_beat"]
        per_chapter.append(
            {
                "chapter": ch,
                "layer": layer,
                "exposition_count": len(expo_single),
                "voice_homogeneity_count": len(voice),
            }
        )
    n = len(per_chapter)
    expo_total = sum(r["exposition_count"] for r in per_chapter)
    voice_total = sum(r["voice_homogeneity_count"] for r in per_chapter)
    summary = {
        "arm": arm,
        "db": db_path,
        "postproc": postproc,
        "quotes_split": total_splits,
        "registry": sorted(registry),
        "chapters_scored": n,
        "exposition_total": expo_total,
        "voice_homogeneity_total": voice_total,
        "exposition_per_chapter": round(expo_total / n, 3) if n else 0.0,
        "voice_per_chapter": round(voice_total / n, 3) if n else 0.0,
        "per_chapter": per_chapter,
    }
    ARM_DIR.mkdir(parents=True, exist_ok=True)
    path = ARM_DIR / f"arm_{arm}.json"
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"[score] arm={arm} chapters={n} splits={total_splits} "
        f"expo/ch={summary['exposition_per_chapter']} "
        f"voice/ch={summary['voice_per_chapter']} -> {path}"
    )
    return summary


def _load_arm(arm: str) -> dict[str, Any]:
    path = ARM_DIR / f"arm_{arm}.json"
    if not path.exists():
        raise SystemExit(f"arm not scored yet: {path} (run `score` first)")
    return json.loads(path.read_text(encoding="utf-8"))


def compare(base_arm: str, test_arm: str) -> dict[str, Any]:
    """Compare test arm vs base; marginal gain = relative drop in exposition/ch."""
    base = _load_arm(base_arm)
    test = _load_arm(test_arm)
    b_expo = base["exposition_per_chapter"]
    t_expo = test["exposition_per_chapter"]
    rel_drop = (b_expo - t_expo) / b_expo if b_expo else 0.0
    improved = rel_drop >= MARGINAL_GAIN_MIN
    verdict = {
        "base_arm": base_arm,
        "test_arm": test_arm,
        "base_exposition_per_chapter": b_expo,
        "test_exposition_per_chapter": t_expo,
        "relative_drop": round(rel_drop, 3),
        "marginal_gain_threshold": MARGINAL_GAIN_MIN,
        "improved": improved,
        "conclusion": (
            "提升（边际增益达标，可继续该杠杆）"
            if improved
            else "非提升（边际增益不达标 → 按退出判据停该杠杆、换下一根）"
        ),
    }
    ARM_DIR.mkdir(parents=True, exist_ok=True)
    path = ARM_DIR / f"compare_{base_arm}__vs__{test_arm}.json"
    path.write_text(json.dumps(verdict, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(verdict, ensure_ascii=False, indent=2))
    print(f"[compare] -> {path}")
    return verdict


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    ps = sub.add_parser("score", help="score a DB's dialogue-carrying chapters")
    ps.add_argument("--db", required=True)
    ps.add_argument("--arm", required=True)
    ps.add_argument(
        "--postproc",
        action="store_true",
        help="apply deterministic exposition-quote split before scoring",
    )
    pc = sub.add_parser("compare", help="compare test arm vs base arm")
    pc.add_argument("--base", required=True)
    pc.add_argument("--arm", required=True)
    args = parser.parse_args()
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if args.cmd == "score":
        score_db(args.db, args.arm, postproc=args.postproc)
    elif args.cmd == "compare":
        compare(args.base, args.arm)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
