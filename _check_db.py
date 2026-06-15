import sqlite3, glob, os
os.chdir(r"c:\Vibe Project\Songyan")
dbs = glob.glob("**/*.db", recursive=True)
print("DB files:", dbs)
if not dbs:
    print("No DB files found")
    exit(1)
conn = sqlite3.connect(dbs[0])
c = conn.execute("SELECT project_id FROM projects")
for r in c.fetchall():
    print("Project:", r[0])
c = conn.execute("SELECT project_id, current_chapter, status FROM project_runs ORDER BY created_at DESC LIMIT 5")
for r in c.fetchall():
    print(f"  Run: {r[0]} Ch{r[1]} status={r[2]}")
conn.close()
