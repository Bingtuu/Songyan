"""172a.1 audit helper: measure REAL token cost of genre_rules per genre.

Loads each genres/*.json, builds a GenreRules-equivalent payload, and reports
tiktoken token counts. Used to replace the plan's char-count-based "38%" claim
with a real token measurement, and to size base_budget per genre.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from songyan.models.genre import GenreProfile  # noqa: E402
from songyan.utils.token_estimator import TokenEstimator  # noqa: E402

GENRE_DIR = ROOT / "genres"
TARGET_GENRES = ["scifi", "xuanhuan", "wuxia", "urban"]


def _genre_rules_payload(gp: GenreProfile) -> dict:
    """Approximate the fields _build_genre_rules injects into context (content-only)."""
    return {
        "genre_id": gp.id,
        "writer_rules": gp.writer_rules,
        "writer_rules_by_type": gp.writer_rules_by_type,
        "fatigue_words": gp.fatigue_words,
        "satisfaction_types": gp.satisfaction_types,
        "pacing_rule": gp.pacing_rule,
        "taboos": gp.taboos,
        "style_baseline": gp.style_baseline.model_dump() if gp.style_baseline else None,
        "reviewer_focus": gp.reviewer_focus,
        "pacing_templates": [pt.model_dump() for pt in gp.pacing_templates],
        "sensory_templates": [st.model_dump() for st in gp.sensory_templates],
    }


def main() -> None:
    est = TokenEstimator()
    rows: list[dict] = []
    scifi_tokens = None
    for genre in TARGET_GENRES:
        path = GENRE_DIR / f"{genre}.json"
        if not path.exists():
            print(f"MISSING: {path}")
            continue
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        gp = GenreProfile.from_dict(data)
        payload = _genre_rules_payload(gp)
        raw_chars = len(json.dumps(payload, ensure_ascii=False))
        tokens = est.estimate_model(payload)
        writer_rule_tokens = est.estimate_model(gp.writer_rules)
        rows.append(
            {
                "genre": genre,
                "genre_rules_tokens": tokens,
                "genre_rules_chars": raw_chars,
                "writer_rules_count": len(gp.writer_rules),
                "writer_rules_tokens": writer_rule_tokens,
                "taboos_count": len(gp.taboos),
            }
        )
        if genre == "scifi":
            scifi_tokens = tokens

    print(f"{'genre':<10}{'gr_tokens':>10}{'gr_chars':>10}{'wr_rules':>9}{'wr_tokens':>10}{'vs_scifi':>10}")
    for r in rows:
        vs = ""
        if scifi_tokens:
            vs = f"{(r['genre_rules_tokens'] / scifi_tokens - 1) * 100:+.1f}%"
        print(
            f"{r['genre']:<10}{r['genre_rules_tokens']:>10}{r['genre_rules_chars']:>10}"
            f"{r['writer_rules_count']:>9}{r['writer_rules_tokens']:>10}{vs:>10}"
        )

    out = ROOT / ".tmp" / "172a1_genre_rules_tokens.json"
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWROTE: {out}")


if __name__ == "__main__":
    main()
