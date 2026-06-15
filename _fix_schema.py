import asyncio, sqlite3
from pathlib import Path
import aiosqlite

async def fix():
    db_path = Path("songyan.db")
    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute(
            "SELECT name FROM pragma_table_info('chapter_versions')"
        )
        cols = {row[0] for row in await cursor.fetchall()}
        if "score_card" not in cols:
            await conn.execute(
                "ALTER TABLE chapter_versions ADD COLUMN score_card TEXT DEFAULT '{}'"
            )
            print("Added score_card column to chapter_versions")
        else:
            print("score_card column already exists")
        await conn.commit()

asyncio.run(fix())
