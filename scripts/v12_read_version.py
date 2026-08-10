"""从 SQLite 读取指定 chapter_version 的正文内容和字数等元数据。"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import aiosqlite

DB_PATH = ROOT / "projects" / "hard-sf-new-weird" / "runtime" / "songyan.db"
PROJECT_ID = "hard-sf-new-weird-v12-224b-235415"
VERSION_IDS = [
    "rev-1-6-77aba7ce",  # 224c final rolled-back version (2540 字，QG=false 前的最优版)
    "v-1-5-1608eacc",    # 224c Writer initial
    "v-1-7-d0181d98",    # 224c Rewrite Writer (2480 underflow)
]


async def main() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        for vid in VERSION_IDS:
            cur = await db.execute(
                "PRAGMA table_info(chapter_versions)"
            )
            cols = [c[1] for c in await cur.fetchall()]
            select_cols = [c for c in [
                "version_id", "chapter_number", "version_number",
                "word_count", "content", "created_at",
            ] if c in cols]
            if "version_kind" in cols:
                select_cols.append("version_kind")
            elif "status" in cols:
                select_cols.append("status")
            sql = (
                "SELECT " + ", ".join(select_cols)
                + " FROM chapter_versions WHERE project_id = ? AND version_id = ?"
            )
            cur = await db.execute(sql, (PROJECT_ID, vid))
            row = await cur.fetchone()
            if row is None:
                print(f"[NOT FOUND] {vid}")
                continue
            print("=" * 72)
            extra = ""
            if "version_kind" in row.keys():
                extra = f" | KIND: {row['version_kind']}"
            elif "status" in row.keys():
                extra = f" | STATUS: {row['status']}"
            print(f"VERSION: {row['version_id']}")
            print(f"CHAPTER: {row['chapter_number']} | VERSION_NO: {row['version_number']}")
            print(f"WORD COUNT: {row['word_count']}{extra}")
            print(f"CREATED_AT: {row['created_at']}")
            print("-" * 72)
            content = row["content"] or "(empty)"
            # 输出完整正文
            print(content)
            print()
            print(f"[End of {vid}]")
            print()


if __name__ == "__main__":
    asyncio.run(main())
