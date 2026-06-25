import sqlite3
import json
from datetime import datetime

db_path = "c:/Vibe Project/Songyan/songyan.db"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Ch129 status
cursor.execute("SELECT chapter_number, accepted_version_id, status FROM chapter_heads WHERE chapter_number = 129")
row = cursor.fetchone()
print(f"Ch129 head: {dict(row) if row else 'None'}")

# Ch129 versions
cursor.execute("""
    SELECT version_id, version_type, word_count, score_card, created_at
    FROM chapter_versions
    WHERE chapter_number = 129
    ORDER BY version_id DESC
""")
versions = cursor.fetchall()
print(f"\nCh129 versions ({len(versions)}):")
for v in versions:
    sc = json.loads(v["score_card"]) if v["score_card"] else {}
    overall = sc.get("overall", "N/A")
    print(f"  {v['version_id']}: type={v['version_type']}, wc={v['word_count']}, overall={overall}, created={v['created_at']}")

# Ch130+ status
cursor.execute("SELECT chapter_number, status FROM chapter_heads WHERE chapter_number BETWEEN 129 AND 135 ORDER BY chapter_number")
rows = cursor.fetchall()
print(f"\nCh129-Ch135 status:")
for r in rows:
    print(f"  Ch{r['chapter_number']}: {r['status']}")

# Check if run-a2bed648 is still updating
cursor.execute("SELECT run_id, status, current_chapter, updated_at FROM project_runs WHERE run_id = 'run-a2bed648'")
run = cursor.fetchone()
print(f"\nrun-a2bed648: {dict(run) if run else 'None'}")

conn.close()
