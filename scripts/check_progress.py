import sqlite3
import json
from datetime import datetime

db_path = "c:/Vibe Project/Songyan/songyan.db"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Check all chapter heads 1-150
cursor.execute("""
    SELECT chapter_number, accepted_version_id, status
    FROM chapter_heads
    WHERE chapter_number BETWEEN 1 AND 150
    ORDER BY chapter_number
""")
rows = cursor.fetchall()

accepted = [r['chapter_number'] for r in rows if r['status'] == 'accepted']
under_review = [r['chapter_number'] for r in rows if r['status'] == 'under_review']
draft = [r['chapter_number'] for r in rows if r['status'] == 'draft']
other = [r['chapter_number'] for r in rows if r['status'] not in ('accepted', 'under_review', 'draft')]

print(f"=== Overall Progress ===")
print(f"  Accepted: {len(accepted)} chapters")
print(f"  Under review: {len(under_review)} chapters -> {under_review}")
print(f"  Draft: {len(draft)} chapters -> {draft}")
print(f"  Other: {len(other)} chapters -> {other}")

if accepted:
    print(f"  Accepted range: Ch{min(accepted)} - Ch{max(accepted)}")
    # Find gaps in accepted
    gaps = [i for i in range(min(accepted), max(accepted)+1) if i not in accepted]
    if gaps:
        print(f"  Gaps in accepted: {gaps}")
    else:
        print(f"  No gaps in accepted range")

# Check project_runs
cursor.execute("SELECT run_id, status, current_chapter, completed_chapters, failed_chapters, updated_at FROM project_runs ORDER BY run_id DESC LIMIT 5")
runs = cursor.fetchall()
print(f"\n=== project_runs ===")
for r in runs:
    print(f"  {r['run_id']}: status={r['status']}, current={r['current_chapter']}, failed={r['failed_chapters']}, updated={r['updated_at']}")

# Check Ch127 latest version
cursor.execute("""
    SELECT v.version_id, v.version_type, v.word_count, v.score_card, v.created_at
    FROM chapter_versions v
    WHERE v.chapter_number = 127
    ORDER BY v.version_id DESC
    LIMIT 3
""")
versions = cursor.fetchall()
print(f"\n=== Ch127 latest versions ===")
for v in versions:
    sc = json.loads(v["score_card"]) if v["score_card"] else {}
    overall = sc.get("overall", "N/A")
    print(f"  {v['version_id']}: type={v['version_type']}, wc={v['word_count']}, overall={overall}, created={v['created_at']}")

# Check for any errors in last hour
cursor.execute("""
    SELECT error_message, created_at
    FROM lifecycle_errors
    ORDER BY created_at DESC
    LIMIT 3
""")
errors = cursor.fetchall()
print(f"\n=== Latest errors ===")
if errors:
    for e in errors:
        print(f"  {e['created_at']}: {e['error_message'][:100] if e['error_message'] else ''}")
else:
    print("  No errors")

conn.close()
