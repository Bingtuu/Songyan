import json
from pathlib import Path
from datetime import datetime

LOG_DIR = Path("logs/chapter_runs")

# 找到今天最新的 run-e6175edb 日志
target_run = "run-e6175edb"
records = []
for jsonl_path in LOG_DIR.glob("*.jsonl"):
    if target_run in jsonl_path.name:
        with jsonl_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    ch = data.get("chapter_number")
                    if ch and 91 <= ch <= 93:
                        records.append(data)
                except Exception:
                    continue

print("=" * 70)
print("Task 110d Fix 验证结果 (Ch91-Ch93, run-e6175edb)")
print("=" * 70)

for r in sorted(records, key=lambda x: x["chapter_number"]):
    ch = r["chapter_number"]
    qg = "PASS" if r.get("quality_gate_passed") else "FAIL"
    chars = r.get("character_states_loaded", 0)
    budget = r.get("budget_used", 0)
    rev = r.get("revision_rounds", 0)
    emerg = "T" if r.get("context_emergency") else "F"
    settle = "T" if r.get("settlement_success") else "F"
    conv = "T" if r.get("convergence_failed") else "F"
    sc = r.get("score_card", {})
    flags = sc.get("flags", {})
    reasons = []
    if flags.get("coherence_major"):
        reasons.append("coherence_major")
    if flags.get("coherence_critical"):
        reasons.append("coherence_critical")
    if not flags.get("length_ok"):
        reasons.append("length_fail")
    if not flags.get("readability_ok"):
        reasons.append("readability_fail")
    if not flags.get("momentum_present"):
        reasons.append("momentum_fail")
    print(f"Ch{ch:2d}: QG={qg} chars={chars} budget={budget:.3f} rev={rev} emerg={emerg} settle={settle} conv={conv}")
    if reasons:
        print(f"      失败原因: {', '.join(reasons)}")

if records:
    qg_passed = sum(1 for r in records if r.get("quality_gate_passed"))
    print(f"\nQG 通过率: {qg_passed}/{len(records)} = {qg_passed/len(records)*100:.1f}%")
