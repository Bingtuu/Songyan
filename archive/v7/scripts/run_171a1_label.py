"""Task 171a-1: apply agent-provisional blind labels to candidate ground truth.

Labeling policy (documented for auditability; agent-provisional, not human-final):
- accept  : matched span is a genuine prose problem of the stated carrier_type.
- reject  : false positive — e.g. matched_text is narration spanning across two
            quotes (the cross-paragraph quote-spanning artifact), or the span is
            action beat rather than info-delivery.
- aggregate 'repeated_revelation_beat' rows (matched_text '... 出现 N 次') are kept
  as accept when N reflects a real repeated pattern (>=3), else reject.
"""

from __future__ import annotations

import json
from pathlib import Path

GT_DIR = Path(".tmp/ground_truth")

# Explicit verdicts keyed by (genre, chapter, carrier_type, matched_text prefix).
# Rationale recorded inline.
VERDICTS: dict[tuple[str, int, str, str], str] = {
    # --- scifi: info_delivery are genuine setting-dumps in dialogue ---
    ("scifi", 1, "info_delivery_dialogue", "“冥王星轨道外"): "accept",
    ("scifi", 1, "info_delivery_dialogue", "“木卫二石板上"): "accept",
    ("scifi", 5, "info_delivery_dialogue", "“他来找我"): "accept",
    ("scifi", 5, "info_delivery_dialogue", "“我是曙光号"): "accept",
    ("scifi", 2, "human_voice_homogeneity", "场景9"): "accept",
    # aggregate beats: faq/info repeated >=3 -> genuine fatigue signal
    ("scifi", 1, "repeated_revelation_beat", "faq_dialogue 出现 4"): "accept",
    ("scifi", 1, "repeated_revelation_beat", "info_delivery_dialogue 出现 2"): "reject",
    ("scifi", 2, "repeated_revelation_beat", "faq_dialogue 出现 6"): "accept",
    ("scifi", 3, "repeated_revelation_beat", "faq_dialogue 出现 3"): "accept",
    ("scifi", 5, "repeated_revelation_beat", "faq_dialogue 出现 6"): "accept",
    ("scifi", 5, "repeated_revelation_beat", "info_delivery_dialogue 出现 2"): "reject",
    # --- wuxia ---
    ("wuxia", 1, "repeated_revelation_beat", "faq_dialogue 出现 6"): "accept",
    ("wuxia", 3, "repeated_revelation_beat", "faq_dialogue 出现 15"): "accept",
    ("wuxia", 3, "repeated_revelation_beat", "info_delivery_dialogue 出现 3"): "accept",
    # FP: matched_text is narration spanning two quotes (布片/信笺描写), not info-dialogue
    ("wuxia", 3, "info_delivery_dialogue", "”女人从袖中取出"): "reject",
    ("wuxia", 3, "info_delivery_dialogue", "”字迹很工整"): "reject",
    # FP: action beat (掷茶碗碎片), not non-character revelation monologue
    ("wuxia", 3, "direct_revelation_monologue", "”沈砚放下茶碗"): "reject",
    ("wuxia", 3, "human_voice_homogeneity", "场景10"): "accept",
    ("wuxia", 4, "repeated_revelation_beat", "faq_dialogue 出现 4"): "accept",
    ("wuxia", 4, "repeated_revelation_beat", "protagonist_summary_tell 出现 2"): "accept",
    # protagonist summary-tell: genuine "他发现了...被灭口" telling
    ("wuxia", 4, "protagonist_summary_tell", "。他发现了柳孤鸣"): "accept",
    ("wuxia", 4, "protagonist_summary_tell", "。现在他发现"): "accept",
}


def _match_verdict(genre: str, rec: dict) -> str | None:
    ct = rec["carrier_type"]
    mt = rec.get("matched_text", "")
    for (g, ch, c, prefix), verdict in VERDICTS.items():
        if g == genre and ch == rec["chapter"] and c == ct and mt.startswith(prefix):
            return verdict
    return None


def main() -> None:
    for genre in ("scifi", "wuxia"):
        path = GT_DIR / f"task171a1_{genre}_ground_truth.jsonl"
        if not path.exists():
            print(f"skip {genre}: no file")
            continue
        out = []
        labeled = 0
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            v = _match_verdict(genre, rec)
            if v is not None:
                rec["human_verdict"] = v
                rec["labeler"] = "agent-provisional"
                labeled += 1
            out.append(rec)
        with path.open("w", encoding="utf-8") as f:
            for rec in out:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"{genre}: labeled {labeled}/{len(out)}")


if __name__ == "__main__":
    main()
