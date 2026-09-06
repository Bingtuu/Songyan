"""V12 Task 225 终判修复：Ch3 accepted 正文两处编辑（不触发 settlement）.

修复内容（reading review 软备注 1 + T9 slash_splice_artifact）：
1. 「操作流程与第二章相同」→「操作流程与上一次相同」（第N章元引用，Ch2 brief 已禁同类）
2. backtick UI 行内「（影像帧序列） / 空白」→「（影像帧序列）；空白」（T9 slash splice）

做法：append-only 新建 version_type="edited" 版本（parent=v-e19d12bc），
同事务切换 chapter_heads accepted/current 指向新版本；不改写历史版本，
不重跑 pipeline，不触发 settlement（两处改动不改变任何事实）。
"""

from __future__ import annotations

import asyncio
import sys

import aiosqlite

from songyan.agents.rule_auditor import (
    detect_markdown_scene_titles,
    detect_meta_tag_leaks,
    detect_text_cleanliness_artifacts,
)
from songyan.utils.word_count import count_chinese_words
from songyan.workflows._helpers import new_id

DB_PATH = "projects/hard-sf-new-weird/runtime/songyan.db"
PROJECT_ID = "hard-sf-new-weird-v12-224f-144113"
CHAPTER = 3
OLD_VERSION_ID = "v-e19d12bc"

REPLACEMENTS: list[tuple[str, str]] = [
    ("操作流程与第二章相同", "操作流程与上一次相同"),
    ("（影像帧序列） / 空白值班席07", "（影像帧序列）；空白值班席07"),
]

FORBIDDEN_PATTERNS = ("第一章", "第二章", "第三章", "本章")


async def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM chapter_versions WHERE version_id = ?", (OLD_VERSION_ID,)
        )
        old = dict(await cur.fetchone())
        assert old["project_id"] == PROJECT_ID and old["chapter_number"] == CHAPTER

        # 幂等守卫：已存在 edit 产物时直接退出，防止重复建版本
        cur = await db.execute(
            "SELECT version_id FROM chapter_versions WHERE parent_version_id = ?",
            (OLD_VERSION_ID,),
        )
        existing = [r[0] for r in await cur.fetchall()]
        if existing:
            print(f"已存在 edited 版本 {existing}，本次不重复创建；退出。")
            return

        content = old["content"]
        for old_s, new_s in REPLACEMENTS:
            count = content.count(old_s)
            assert count == 1, f"替换目标出现 {count} 次（应为 1）: {old_s!r}"
            content = content.replace(old_s, new_s, 1)

        # 修复后验证：T9 三类检测全零 + 元引用禁令扫描零命中
        meta = detect_meta_tag_leaks(content)
        scene = detect_markdown_scene_titles(content)
        artifacts = detect_text_cleanliness_artifacts(content)
        assert not (meta or scene or artifacts), (
            f"修复后仍有 T9 命中: meta={len(meta)} scene={len(scene)} artifact={len(artifacts)}"
        )
        for pat in FORBIDDEN_PATTERNS:
            assert pat not in content, f"元引用残留: {pat}"

        word_count = count_chinese_words(content)
        new_version_id = new_id("v")

        cur = await db.execute(
            "SELECT COALESCE(MAX(version_number), 0) + 1 FROM chapter_versions "
            "WHERE project_id = ? AND chapter_number = ?",
            (PROJECT_ID, CHAPTER),
        )
        next_version_number = (await cur.fetchone())[0]

        await db.execute("BEGIN IMMEDIATE")
        try:
            await db.execute(
                """INSERT INTO chapter_versions (
                    version_id, project_id, chapter_number, version_number,
                    version_type, content, word_count, parent_version_id, created_at
                ) VALUES (?, ?, ?, ?, 'edited', ?, ?, ?, datetime('now'))""",
                (
                    new_version_id,
                    PROJECT_ID,
                    CHAPTER,
                    next_version_number,
                    content,
                    word_count,
                    OLD_VERSION_ID,
                ),
            )
            await db.execute(
                """UPDATE chapter_heads
                   SET accepted_version_id = ?, current_version_id = ?, status = 'accepted'
                   WHERE project_id = ? AND chapter_number = ?""",
                (new_version_id, new_version_id, PROJECT_ID, CHAPTER),
            )
            await db.execute("COMMIT")
        except Exception:
            await db.execute("ROLLBACK")
            raise

    print(f"OK: new edited version {new_version_id} (parent={OLD_VERSION_ID})")
    print(f"word_count: {old['word_count']} -> {word_count}, chars: {len(content)}")
    print("T9 三类检测 0 命中；第N章/本章元引用扫描 0 命中")


if __name__ == "__main__":
    asyncio.run(main())
