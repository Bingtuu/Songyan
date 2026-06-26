import sqlite3
import json

db_path = "c:/Vibe Project/Songyan/songyan.db"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Find accepted version for chapter 124 via chapter_heads
cursor.execute("""
    SELECT h.accepted_version_id, h.current_version_id, h.status
    FROM chapter_heads h
    WHERE h.chapter_number = 124
""")
head = cursor.fetchone()
print(f"Chapter head: {dict(head) if head else 'None'}")

accepted_version_id = head["accepted_version_id"] if head else None

# Get all versions for Ch124
cursor.execute("""
    SELECT v.version_id, v.chapter_number, v.content, v.word_count, v.score_card, v.version_number, v.version_type
    FROM chapter_versions v
    WHERE v.chapter_number = 124
    ORDER BY v.version_id DESC
""")
rows = cursor.fetchall()

print(f"\n=== Ch124 versions found: {len(rows)} ===")
for r in rows:
    sc = json.loads(r["score_card"]) if r["score_card"] else {}
    overall = sc.get("overall", "N/A")
    length_score = sc.get("length", {}).get("score", "N/A")
    is_accepted = "[ACCEPTED]" if r["version_id"] == accepted_version_id else ""
    print(f"  version_id={r['version_id']}, type={r['version_type']}, word_count={r['word_count']}, overall={overall}, length_score={length_score} {is_accepted}")

# Get the accepted version content
if rows and accepted_version_id:
    target = [r for r in rows if r["version_id"] == accepted_version_id]
    target = target[0] if target else rows[0]
else:
    target = rows[0] if rows else None

if target:
    content = target["content"] or ""
    wc = target["word_count"] or len(content)
    print(f"\n=== Accepted version_id={target['version_id']} ===")
    print(f"=== Content length: {len(content)} chars, word_count={wc} ===")
    print(f"=== First 2000 chars ===")
    print(content[:2000])
    print(f"\n=== ... middle ... ===")
    mid = len(content)//2
    print(content[mid-500:mid+500])
    print(f"\n=== Last 1000 chars ===")
    print(content[-1000:])
else:
    print("No content found for Ch124")

conn.close()
