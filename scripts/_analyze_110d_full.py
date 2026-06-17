import json
from pathlib import Path
from datetime import datetime
from collections import Counter

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

# 取每章最新的记录（按 finished_at）
by_chapter = {}
for r in records:
    ch = r["chapter_number"]
    if ch not in by_chapter or r.get("finished_at", "") > by_chapter[ch].get("finished_at", ""):
        by_chapter[ch] = r

# 只保留 2026-06-17 的新数据
new_data = {}
for ch, r in by_chapter.items():
    finished_at = r.get("finished_at", "")
    if finished_at.startswith("2026-06-17"):
        new_data[ch] = r

chapters = sorted(new_data.keys())
print(f"新数据章节: {chapters}")
print(f"总章节数: {len(chapters)}\n")

if not chapters:
    print("无新数据")
    exit(0)

# 关键指标
qg_passed = sum(1 for r in new_data.values() if r.get("quality_gate_passed"))
emergency_count = sum(1 for r in new_data.values() if r.get("context_emergency"))
budgets = [r.get("budget_used", 0) for r in new_data.values()]
revision_rounds = [r.get("revision_rounds", 0) for r in new_data.values()]
convergence_failed = sum(1 for r in new_data.values() if r.get("convergence_failed"))

# 失败模式
failures = []
for ch, r in new_data.items():
    if not r.get("quality_gate_passed"):
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
        failures.append((ch, reasons, r.get("budget_used", 0), r.get("context_emergency")))

print("=" * 60)
print("Task 110d 指标汇总 (Ch80-Ch100 新数据)")
print("=" * 60)
print(f"章节范围: Ch{min(chapters)} - Ch{max(chapters)} (共 {len(chapters)} 章)")
print(f"QG 通过率: {qg_passed}/{len(chapters)} = {qg_passed/len(chapters)*100:.1f}%")
print(f"ContextEmergency 次数: {emergency_count}/{len(chapters)} = {emergency_count/len(chapters)*100:.1f}%")
print(f"平均 budget_used: {sum(budgets)/len(budgets):.3f} (min={min(budgets):.3f}, max={max(budgets):.3f})")
print(f"平均 revision 轮数: {sum(revision_rounds)/len(revision_rounds):.2f}")
print(f"ConvergenceFailed 次数: {convergence_failed}/{len(chapters)}")
print()

# 连续失败检测
consecutive_fails = 0
max_consecutive = 0
for ch in range(min(chapters), max(chapters)+1):
    if ch in new_data and not new_data[ch].get("quality_gate_passed"):
        consecutive_fails += 1
        max_consecutive = max(max_consecutive, consecutive_fails)
    else:
        consecutive_fails = 0
print(f"最大连续失败: {max_consecutive} 章")
print()

print("失败章节明细:")
for ch, reasons, budget, emerg in failures:
    print(f"  Ch{ch:3d}: {', '.join(reasons) if reasons else 'unknown'} | budget={budget:.3f} emergency={emerg}")

print()
print("每章 budget_used:")
for ch in chapters:
    r = new_data[ch]
    qg = "PASS" if r.get("quality_gate_passed") else "FAIL"
    print(f"  Ch{ch:3d}: budget={r.get('budget_used', 0):.3f} QG={qg} rev={r.get('revision_rounds', 0)} emerg={r.get('context_emergency')}")
