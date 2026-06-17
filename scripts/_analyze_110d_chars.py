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

print("Ch80-Ch95 角色状态与软参考加载分析")
print("=" * 90)
print(f"{'Ch':>4} | {'QG':>4} | {'chars':>5} | {'softs':>5} | {'budget':>6} | {'emerg':>5}")
print("-" * 90)

for ch in sorted(new_data.keys()):
    r = new_data[ch]
    qg = "PASS" if r.get("quality_gate_passed") else "FAIL"
    chars = r.get("character_states_loaded", 0)
    softs = r.get("soft_refs_loaded", 0)
    budget = r.get("budget_used", 0)
    emerg = "T" if r.get("context_emergency") else "F"
    print(f"{ch:>4} | {qg:>4} | {chars:>5} | {softs:>5} | {budget:>6.3f} | {emerg:>5}")

print()
# 统计 PASS vs FAIL 的平均 chars/softs
pass_chars = [r.get("character_states_loaded", 0) for r in new_data.values() if r.get("quality_gate_passed")]
fail_chars = [r.get("character_states_loaded", 0) for r in new_data.values() if not r.get("quality_gate_passed")]
pass_softs = [r.get("soft_refs_loaded", 0) for r in new_data.values() if r.get("quality_gate_passed")]
fail_softs = [r.get("soft_refs_loaded", 0) for r in new_data.values() if not r.get("quality_gate_passed")]

print("统计:")
print(f"  PASS 章节: avg_chars={sum(pass_chars)/len(pass_chars):.1f}, avg_softs={sum(pass_softs)/len(pass_softs):.1f}")
print(f"  FAIL 章节: avg_chars={sum(fail_chars)/len(fail_chars):.1f}, avg_softs={sum(fail_softs)/len(fail_softs):.1f}")
