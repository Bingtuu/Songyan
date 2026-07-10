"""Task 170m: Export Ch30-Ch32 candidates for exposition-carrier ground truth.

用法:
    python scripts/run_170m_ground_truth_export.py

输出:
    - .tmp/ground_truth/task170m_ch30_ch32_ground_truth.jsonl
    - .tmp/ground_truth/task170m_ch30_ch32_ground_truth.md（供人工终审的表格视图）
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from songyan.agents.rule_auditor import detect_exposition_carriers
from songyan.config import settings
from songyan.db import LiteraryKeywordRepository
from songyan.db.repository import ChapterHeadRepository, ChapterVersionRepository
from songyan.utils._helpers import split_paragraphs

settings.database_url = os.getenv(
    "DATABASE_URL", "sqlite:///.tmp/task170l_few_shot_voice_anchor.db"
)

PROJECT_FILE = Path(".tmp/task170l_few_shot_voice_anchor_project.json")
GROUND_TRUTH_DIR = Path(".tmp/ground_truth")
JSONL_PATH = GROUND_TRUTH_DIR / "task170m_ch30_ch32_ground_truth.jsonl"
MD_PATH = GROUND_TRUTH_DIR / "task170m_ch30_ch32_ground_truth.md"

ASSESS_START = int(os.getenv("ASSESS_START", "30"))
ASSESS_END = int(os.getenv("ASSESS_END", "32"))


def _resolve_project_id(cli_pid: str | None) -> str | None:
    if cli_pid:
        return cli_pid
    pid = os.getenv("PROJECT_ID")
    if pid:
        return pid
    if PROJECT_FILE.exists():
        try:
            return json.loads(PROJECT_FILE.read_text(encoding="utf-8")).get("project_id")
        except (json.JSONDecodeError, OSError):
            return None
    return None


def _paragraph_index_for_offset(text: str, offset: int | None) -> int:
    if offset is None:
        return -1
    paragraphs = split_paragraphs(text)
    cursor = 0
    for idx, para in enumerate(paragraphs, 1):
        start = text.find(para, cursor)
        if start == -1:
            continue
        end = start + len(para)
        if start <= offset < end:
            return idx
        cursor = end
    return -1


async def _load_accepted_content(project_id: str) -> dict[int, dict[str, Any]]:
    head_repo = ChapterHeadRepository()
    version_repo = ChapterVersionRepository()
    heads = await head_repo.list_by_project(project_id)
    result: dict[int, dict[str, Any]] = {}
    for head in heads:
        ch = head.chapter_number
        if ch < ASSESS_START or ch > ASSESS_END:
            continue
        if head.status != "accepted" or not head.accepted_version_id:
            continue
        version = await version_repo.get(head.accepted_version_id)
        if version is None:
            continue
        result[ch] = {
            "version_id": version.version_id,
            "content": version.content,
            "word_count": version.word_count,
        }
    return result


async def _amain(project_id: str) -> int:
    print(f"[preflight] project={project_id}, window=Ch{ASSESS_START}-Ch{ASSESS_END}")

    chapters = await _load_accepted_content(project_id)
    if not chapters:
        print("[error] 窗口内没有 accepted 章节。")
        return 1
    print(f"[load] accepted chapters: {sorted(chapters.keys())}")

    keyword_repo = LiteraryKeywordRepository()
    keywords = await keyword_repo.load_exposition_keywords(project_id)
    print(
        f"[keywords] characters={len(keywords['character_names'])}, "
        f"settings={len(keywords['setting_keywords'])}, "
        f"non_char={len(keywords['non_character_keywords'])}"
    )

    GROUND_TRUTH_DIR.mkdir(parents=True, exist_ok=True)
    jsonl_fp = JSONL_PATH.open("w", encoding="utf-8")
    md_lines: list[str] = [
        f"# Task 170m Ground Truth 候选（Ch{ASSESS_START}-Ch{ASSESS_END}）",
        "",
        "> 机器预标结果。请对每一行做终审：",
        "> - `human_verdict`: `accept` / `reject` / `retype:<new_carrier_type>` / `add-missing`",
        "> - 如需补充未检出的 exposition 段落，在文件末尾追加一行，设置 `annotator` 为 `human`。",
        "",
        "| Ch | 段 | carrier_type | severity | 位置 | 原文摘录 | 建议操作 | 备注 |",
        "|---:|---:|:---|:---|:---|:---|:---|:---|",
    ]

    total = 0
    for ch in sorted(chapters.keys()):
        content = chapters[ch]["content"]
        carriers = detect_exposition_carriers(
            content,
            character_names=keywords["character_names"],
            non_character_keywords=keywords["non_character_keywords"],
            info_delivery_keywords=keywords["setting_keywords"],
        )
        print(f"[detect] Ch{ch}: {len(carriers)} candidates")
        total += len(carriers)
        for c in carriers:
            para_idx = _paragraph_index_for_offset(content, c.start)
            para_text = ""
            if para_idx > 0:
                paras = split_paragraphs(content)
                if para_idx <= len(paras):
                    para_text = paras[para_idx - 1]
            record = {
                "chapter": ch,
                "paragraph_index": para_idx,
                "paragraph_text": para_text,
                "carrier_type": c.carrier_type,
                "start": c.start,
                "end": c.end,
                "matched_text": c.matched_text,
                "annotator": "machine_pre",
                "note": f"{c.severity}: {c.message}",
                "human_verdict": None,
            }
            jsonl_fp.write(json.dumps(record, ensure_ascii=False) + "\n")
            excerpt = (c.matched_text or "").replace("|", "\\|").replace("\n", " ")[:80]
            md_lines.append(
                f"| {ch} | {para_idx} | {c.carrier_type} | {c.severity} | {c.location} | "
                f"{excerpt} |  |  |"
            )

    jsonl_fp.close()
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")
    md_lines.append(f"**合计**: {total} 个机器预标候选。")
    MD_PATH.write_text("\n".join(md_lines), encoding="utf-8")

    print(f"[export] {JSONL_PATH}")
    print(f"[export] {MD_PATH}")
    print(f"[summary] total candidates: {total}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Task 170m ground truth candidate export")
    parser.add_argument("--project-id", default=None)
    args = parser.parse_args()
    project_id = _resolve_project_id(args.project_id)
    if not project_id:
        parser.error("无法确定 project_id；用 --project-id 或 PROJECT_ID 环境变量")
    return asyncio.run(_amain(project_id))


if __name__ == "__main__":
    raise SystemExit(main())
