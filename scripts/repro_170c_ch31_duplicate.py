"""Task 170c 复现脚本：定位 Ch31 T9 近似重复漏报根因.

只读、不改任何数据。从隔离 DB 读 Ch31 accepted 正文，
运行当前 detect_duplicate_paragraphs（应漏报=0），
再对已知重复对逐一测量归一化字数与 SequenceMatcher ratio，
输出根因诊断（对齐 170c 假设 A/B/C/D）。

用法:
    python scripts/repro_170c_ch31_duplicate.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from songyan.config import settings

# 与 170b 一致：强制隔离 DB，绝不碰主库。
settings.database_url = os.getenv("DATABASE_URL", "sqlite:///.tmp/task170b_ch1_ch40.db")

import json  # noqa: E402

from songyan.agents.rule_auditor import (  # noqa: E402
    _normalize_paragraph_for_similarity,
    detect_duplicate_paragraphs,
)
from songyan.db.repository import ChapterHeadRepository, ChapterVersionRepository  # noqa: E402
from songyan.utils._helpers import split_paragraphs  # noqa: E402

CHAPTER = int(os.getenv("REPRO_CHAPTER", "31"))
PROJECT_FILE = Path(".tmp/task170b_project.json")


def _resolve_project_id() -> str | None:
    pid = os.getenv("PROJECT_ID")
    if pid:
        return pid
    if PROJECT_FILE.exists():
        return json.loads(PROJECT_FILE.read_text(encoding="utf-8")).get("project_id")
    return None


async def _load_chapter_content(chapter: int) -> str | None:
    project_id = _resolve_project_id()
    if not project_id:
        return None
    head = await ChapterHeadRepository().get(project_id, chapter)
    if head is None or head.status != "accepted" or not head.accepted_version_id:
        return None
    version = await ChapterVersionRepository().get(head.accepted_version_id)
    return version.content if version else None


def _measure_pair(label: str, a: str, b: str) -> None:
    na = _normalize_paragraph_for_similarity(a)
    nb = _normalize_paragraph_for_similarity(b)
    ratio = 1.0 if na == nb else SequenceMatcher(None, na, nb).ratio()
    filtered = min(len(na), len(nb)) < 100
    print(f"\n[{label}]")
    print(f"  段A 归一化字数 = {len(na)}")
    print(f"  段B 归一化字数 = {len(nb)}")
    print(f"  SequenceMatcher ratio = {ratio:.4f}")
    print(f"  旧 min_chars=100 过滤? {'是 → 两段都进不了比较循环' if filtered else '否'}")
    print(f"  threshold=0.9 达标? {'是' if ratio >= 0.9 else '否'}")


async def _amain() -> int:
    content = await _load_chapter_content(CHAPTER)
    if not content:
        print(f"[error] 未找到 Ch{CHAPTER} 的 accepted 正文（DB={settings.database_url}）")
        return 1

    print(f"[preflight] DB={settings.database_url}  Ch{CHAPTER} 正文字数={len(content)}")

    # 1. 复现漏报：当前检测器结果
    matches = detect_duplicate_paragraphs(content)
    print(f"\n[repro] 当前 detect_duplicate_paragraphs 命中 = {len(matches)}（预期漏报=0）")
    for m in matches:
        print(f"  - 段{m.paragraph_index} ≈ 段{m.duplicate_of_index}  sim={m.similarity}")

    # 2. 定位已知重复对（按 170c 文档：L633↔L641、L643↔L659）
    paragraphs = split_paragraphs(content)
    print(f"\n[info] split_paragraphs 段落数 = {len(paragraphs)}")

    pair1_candidates = [
        (i, p) for i, p in enumerate(paragraphs, 1) if "现在不是愤怒的时候" in p
    ]
    print(f"\n[locate] 含『现在不是愤怒的时候』的段落数 = {len(pair1_candidates)}")
    for i, p in pair1_candidates:
        print(f"  段{i} (归一化{len(_normalize_paragraph_for_similarity(p))}字): {p[:40]}...")

    pair2_candidates = [
        (i, p)
        for i, p in enumerate(paragraphs, 1)
        if "将七条光谱线的数据分别导出" in p
    ]
    print(f"\n[locate] 含『将七条光谱线的数据分别导出』的段落数 = {len(pair2_candidates)}")
    for i, p in pair2_candidates:
        print(f"  段{i} (归一化{len(_normalize_paragraph_for_similarity(p))}字): {p[:40]}...")

    # 3. 逐对测量
    if len(pair1_candidates) >= 2:
        _measure_pair("Pair1 L633↔L641", pair1_candidates[0][1], pair1_candidates[1][1])
    if len(pair2_candidates) >= 2:
        _measure_pair("Pair2 L643↔L659", pair2_candidates[0][1], pair2_candidates[1][1])

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_amain()))
