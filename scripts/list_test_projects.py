import sqlite3

conn = sqlite3.connect('songyan.db')
c = conn.cursor()

c.execute("SELECT project_id, title, created_at FROM projects")
projects = c.fetchall()
print(f"Total projects: {len(projects)}")
for p in projects:
    print(f"  {p[0]} | {p[1]} | {p[2]}")

# Count versions per project
c.execute("SELECT project_id, COUNT(*) FROM chapter_versions GROUP BY project_id")
version_counts = dict(c.fetchall())
print("\nVersions per project:")
for pid, count in version_counts.items():
    print(f"  {pid}: {count} versions")

conn.close()
