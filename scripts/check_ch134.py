import sqlite3
import json

db_path = "c:/Vibe Project/Songyan/songyan.db"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Ch134 status
cursor.execute("SELECT chapter_number, accepted_version_id, status FROM chapter_heads WHERE chapter_number = 134")
row = cursor.fetchone()
print(f"Ch134 head: {dict(row) if row else 'None'}")

# Ch134 versions
cursor.execute("""
    SELECT version_id, version_type, word_count, score_card, created_at
    FROM chapter_versions
    WHERE chapter_number = 134
    ORDER BY version_id DESC
""")
versions = cursor.fetchall()
print(f"\nCh134 versions ({len(versions)}):")
for v in versions:
    sc = json.loads(v["score_card"]) if v["score_card"] else {}
    overall = sc.get("overall", "N/A")
    print(f"  {v['version_id']}: type={v['version_type']}, wc={v['word_count']}, overall={overall}, created={v['created_at']}")

conn.close()
