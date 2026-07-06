"""Task 170c 误报体检：对隔离 DB 全窗口跑分级去重，人工核验新命中是否真重复.

只读。逐章打印命中的段落对（截断展示），供人工判断是否误伤正常复现修辞。
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from songyan.config import settings

settings.database_url = os.getenv("DATABASE_URL", "sqlite:///.tmp/task170b_ch1_ch40.db")

from songyan.agents.rule_auditor import detect_duplicate_paragraphs  # noqa: E402
from songyan.db.repository import ChapterHeadRepository, ChapterVersionRepository  # noqa: E402

PROJECT_FILE = Path(".tmp/task170b_project.json")
START = int(os.getenv("SWEEP_START", "1"))
END = int(os.getenv("SWEEP_END", "40"))


async def _amain() -> int:
    project_id = json.loads(PROJECT_FILE.read_text(encoding="utf-8"))["project_id"]
    head_repo = ChapterHeadRepository()
    version_repo = ChapterVersionRepository()
    total = 0
    for ch in range(START, END + 1):
        head = await head_repo.get(project_id, ch)
        if head is None or head.status != "accepted" or not head.accepted_version_id:
            continue
        version = await version_repo.get(head.accepted_version_id)
        if version is None:
            continue
        matches = detect_duplicate_paragraphs(version.content)
        if not matches:
            continue
        total += len(matches)
        print(f"\n=== Ch{ch}: {len(matches)} 命中 ===")
        for m in matches:
            print(
                f"  段{m.paragraph_index} ≈ 段{m.duplicate_of_index}  sim={m.similarity}"
            )
            print(f"    A[{m.duplicate_of_index}]: {m.original_text[:60]}")
            print(f"    B[{m.paragraph_index}]: {m.matched_text[:60]}")
    print(f"\n[summary] 窗口 Ch{START}-Ch{END} 总命中 = {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_amain()))
