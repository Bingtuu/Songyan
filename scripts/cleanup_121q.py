import sqlite3
import os

jsonl_path = 'logs/chapter_runs/run-8e59bccd.jsonl'
if os.path.exists(jsonl_path):
    os.remove(jsonl_path)
    print(f'Removed {jsonl_path}')

conn = sqlite3.connect('songyan.db')
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cursor.fetchall()]

project_id = '9819975d'

for table in tables:
    try:
        cursor.execute(f"DELETE FROM {table} WHERE project_id = ?", (project_id,))
        if cursor.rowcount > 0:
            print(f'Deleted {cursor.rowcount} rows from {table}')
    except Exception:
        pass

conn.commit()
conn.close()
print('Cleanup done')
