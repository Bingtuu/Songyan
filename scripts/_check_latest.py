import json
from pathlib import Path
from datetime import datetime

LOG_DIR = Path("logs/chapter_runs")

# 找到今天最新的 jsonl 文件
today_files = []
for p in LOG_DIR.glob("*.jsonl"):
    mtime = datetime.fromtimestamp(p.stat().st_mtime)
    if mtime.date() == datetime.today().date():
        today_files.append((mtime, p))

today_files.sort(reverse=True)

print(f"今天共有 {len(today_files)} 个日志文件")
print("最近 10 个文件:")
for mtime, p in today_files[:10]:
    # 读取文件最后一行
    try:
        with p.open(encoding="utf-8") as f:
            lines = f.readlines()
            if lines:
                last = json.loads(lines[-1])
                ch = last.get("chapter_number", "?")
                qg = "PASS" if last.get("quality_gate_passed") else "FAIL"
                finished = last.get("finished_at", "?")
                print(f"  {p.name}: Ch{ch} QG={qg} at {finished}")
            else:
                print(f"  {p.name}: (empty)")
    except Exception as e:
        print(f"  {p.name}: error {e}")

# 统计今天 Ch89+ 的新数据
records = {}
for _, p in today_files:
    with p.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                ch = data.get("chapter_number")
                if ch and ch >= 89:
                    rid = data.get("run_id", "")
                    finished = data.get("finished_at", "")
                    key = (ch, rid)
                    if key not in records or finished > records[key]["finished_at"]:
                        records[key] = data
            except Exception:
                continue

by_ch = {}
for data in records.values():
    ch = data["chapter_number"]
    if ch not in by_ch or data.get("finished_at", "") > by_ch[ch].get("finished_at", ""):
        by_ch[ch] = data

print(f"\nCh89+ 今天最新记录 ({len(by_ch)} 章):")
for ch in sorted(by_ch):
    r = by_ch[ch]
    qg = "PASS" if r.get("quality_gate_passed") else "FAIL"
    print(f"  Ch{ch:3d}: QG={qg} budget={r.get('budget_used', 0):.3f} rev={r.get('revision_rounds', 0)}")
