import json
from pathlib import Path

LOG_DIR = Path("logs/chapter_runs")

records = []
for jsonl_path in LOG_DIR.glob("*.jsonl"):
    with jsonl_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                ch = data.get("chapter_number")
                if ch and 80 <= ch <= 100:
                    records.append(data)
            except Exception:
                continue

by_chapter = {}
for r in records:
    ch = r["chapter_number"]
    if ch not in by_chapter or r.get("finished_at", "") > by_chapter[ch].get("finished_at", ""):
        by_chapter[ch] = r

new_data = {ch: r for ch, r in by_chapter.items() if r.get("finished_at", "").startswith("2026-06-17")}

print("Ch80-Ch93 连贯性与 settlement 分析")
print("=" * 90)
print(f"{'Ch':>4} | {'QG':>4} | {'conv':>6} | {'skip_set':>8} | {'cont_health':>11} | {'budget':>6} | {'settle':>6} | {'rev':>3}")
print("-" * 90)

for ch in sorted(new_data.keys()):
    r = new_data[ch]
    qg = "PASS" if r.get("quality_gate_passed") else "FAIL"
    conv = "T" if r.get("convergence_failed") else "F"
    skip = "T" if r.get("skip_settlement") else "F"
    health = r.get("continuity_health_score")
    health_str = f"{health:>11.1f}" if health is not None else "          -"
    budget = r.get("budget_used", 0)
    settle = "T" if r.get("settlement_success") else "F"
    rev = r.get("revision_rounds", 0)
    print(f"{ch:>4} | {qg:>4} | {conv:>6} | {skip:>8} | {health_str} | {budget:>6.3f} | {settle:>6} | {rev:>3}")

print()
print("连锁反应分析:")
print("-" * 40)
for ch in sorted(new_data.keys()):
    r = new_data[ch]
    if r.get("skip_settlement"):
        print(f"  Ch{ch}: settlement 被跳过 (conv_failed={r.get('convergence_failed')})")
