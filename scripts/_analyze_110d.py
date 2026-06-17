import json
from pathlib import Path
from datetime import datetime

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

print(f"Total records found: {len(records)}")
print(f"Unique chapters: {len(by_chapter)}")
print("\nChapter timestamps (latest per chapter):")
for ch in sorted(by_chapter):
    r = by_chapter[ch]
    print(f"  Ch{ch}: finished_at={r.get('finished_at', 'N/A')}, run_id={r.get('run_id', 'N/A')}")
