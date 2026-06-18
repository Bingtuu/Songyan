import json
from pathlib import Path
from datetime import datetime

LOG_DIR = Path("logs/chapter_runs")

# 找到今天 22:14 之后生成的日志（第二轮验证）
target_time = "2026-06-17T22:14"
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
                finished = data.get("finished_at", "")
                if ch and 91 <= ch <= 93 and finished >= target_time:
                    records.append(data)
            except Exception:
                continue

print("=" * 70)
print("Task 110d Fix Round 2 验证结果 (Ch91-Ch93)")
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

    # 对比修复前后
    print("\n对比 (修复前 -> 修复后):")
    old = {
        91: {"qg": False, "chars": 1},
        92: {"qg": True, "chars": 1},
        93: {"qg": False, "chars": 1},
    }
    for ch in [91, 92, 93]:
        r = next((x for x in records if x["chapter_number"] == ch), None)
        if r:
            o = old[ch]
            n_qg = "PASS" if r.get("quality_gate_passed") else "FAIL"
            o_qg = "PASS" if o["qg"] else "FAIL"
            n_chars = r.get("character_states_loaded", 0)
            print(f"  Ch{ch}: QG {o_qg} -> {n_qg} | chars {o['chars']} -> {n_chars}")
