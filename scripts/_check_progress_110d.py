import json
from pathlib import Path
from collections import defaultdict

LOG_DIR = Path("logs/chapter_runs")

# 收集所有 JSONL 文件中 chapter_number 在 80-100 之间的记录
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

# 去重：同一章节取最新的（按 finished_at）
by_chapter = {}
for r in records:
    ch = r["chapter_number"]
    if ch not in by_chapter or r.get("finished_at", "") > by_chapter[ch].get("finished_at", ""):
        by_chapter[ch] = r

print(f"Completed chapters: {len(by_chapter)}")
for ch in sorted(by_chapter):
    r = by_chapter[ch]
    sc = r.get("score_card", {})
    print(
        f"Ch{ch:3d}: budget={r.get('budget_used', 0):.3f} "
        f"emergency={r.get('context_emergency', False)} "
        f"qg_pass={r.get('quality_gate_passed', False)} "
        f"conv_fail={r.get('convergence_failed', False)} "
        f"skip_settl={r.get('skip_settlement', False)} "
        f"overall={sc.get('overall_score', 0):.3f} "
        f"coherence={sc.get('coherence', {}).get('score', 0):.3f} "
        f"readability={sc.get('readability', {}).get('score', 0):.3f} "
        f"duration={r.get('duration_sec', 0):.0f}s "
        f"words={r.get('word_count', 0)} "
        f"revisions={r.get('revision_rounds', 0)}"
    )
