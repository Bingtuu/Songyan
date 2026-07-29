"""Task 196: LLM 批量预标（纯离线，不进生成链路）."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from songyan.evals.excellence_sampling import AnnotationRecord, load_chapter_content
from songyan.llm.client import call_llm
from songyan.llm.parsing import parse_llm_response
from songyan.prompts._models import CraftCard
from songyan.prompts.loader import PromptLoader, get_prompt_loader

SAMPLE_SET = Path("tasks/196-excellence-sample-set.json")
ANNOTATIONS = Path("tasks/196-excellence-annotations.json")
RAW_DIR = Path(".tmp/196_prelabel_raw")

# 失败占位记录的 disagreement 前缀；带此前缀的记录不进入幂等跳过集，重跑时会重试
# （prelabel_parse_failed 为初版脚本的历史前缀，保留以便旧占位记录也能被重试替换）
FAILED_PREFIXES = ("prelabel_failed", "prelabel_parse_failed")


def _connect_readonly(db_path: str) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{Path(db_path).as_posix()}?mode=ro", uri=True)


def _save_annotations(annotations: dict[str, Any]) -> None:
    """原子写 canonical artifact：先写临时文件再 os.replace，崩溃不留半截 JSON."""
    tmp = ANNOTATIONS.with_name(ANNOTATIONS.name + ".tmp")
    tmp.write_text(
        json.dumps(annotations, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    os.replace(tmp, ANNOTATIONS)


def _is_failed_placeholder(record: dict[str, Any]) -> bool:
    disagreement = record.get("disagreement") or ""
    return disagreement.startswith(FAILED_PREFIXES)


async def _prelabel_one(
    loader: PromptLoader,
    card: CraftCard,
    sample: dict[str, Any],
    content: str,
    raw_out: dict[str, str],
) -> tuple[AnnotationRecord, dict[str, Any]]:
    rendered = loader.render_card(
        card, {"genre": sample["genre"], "chapter_content": content}
    )
    raw_text = await call_llm(
        rendered.system_prompt, temperature=0.3, max_tokens=1024, timeout=120
    )
    raw_out["raw_text"] = raw_text
    data = parse_llm_response(raw_text)
    rec = AnnotationRecord(
        genre=sample["genre"],
        chapter=sample["chapter"],
        version_id=sample["version_id"],
        sample_layer="prelabel",
        scores={
            "homogeneity": data["homogeneity"],
            "tension": data["tension"],
            "ai_tone": data["ai_tone"],
            "overall": data["overall"],
        },
        rationale=data.get("rationale", ""),
        evidence_quotes=data.get("evidence_quotes", []),
        annotator="llm-prelabel",
    )
    return rec, {"raw_response": raw_text, "parsed": data}


def _failure_placeholder(sample: dict[str, Any], exc: Exception) -> dict[str, Any]:
    return AnnotationRecord(
        genre=sample["genre"], chapter=sample["chapter"],
        version_id=sample["version_id"], sample_layer="prelabel",
        scores={"homogeneity": 3, "tension": 3, "ai_tone": 3, "overall": 3},
        annotator="llm-prelabel",
        disagreement=f"prelabel_failed: {exc}",
    ).model_dump()


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit", type=int, default=None, help="最多预标多少章（smoke 调试用）"
    )
    args = parser.parse_args()
    sample_set = json.loads(SAMPLE_SET.read_text(encoding="utf-8"))
    annotations: dict[str, Any] = json.loads(ANNOTATIONS.read_text(encoding="utf-8"))

    loader = get_prompt_loader()
    card = loader.load_card("excellence_prelabel")
    dbs = {s["genre"]: s["db"] for s in sample_set["sources"]}
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    # version_id → annotations 列表下标；失败占位记录可被成功重试原地替换
    index_by_vid = {
        a["version_id"]: i for i, a in enumerate(annotations["annotations"])
    }
    done = failed = 0
    for sample in sample_set["samples"]:
        existing_idx = index_by_vid.get(sample["version_id"])
        if existing_idx is not None and not _is_failed_placeholder(
            annotations["annotations"][existing_idx]
        ):
            continue  # 幂等：已成功/锚点记录一律跳过，重跑不产生重复
        if args.limit is not None and done + failed >= args.limit:
            break
        with contextlib.closing(_connect_readonly(dbs[sample["genre"]])) as conn:
            content = load_chapter_content(conn, sample["version_id"])
        raw_out: dict[str, str] = {}
        try:
            rec, raw = await _prelabel_one(loader, card, sample, content, raw_out)
        except Exception as exc:  # noqa: BLE001 — 失败章记 disagreement，不中断批量
            # 失败路径也落 raw（若有），便于排查卡的输出约束问题
            (RAW_DIR / f"{sample['genre']}-ch{sample['chapter']:03d}-failed.json"
             ).write_text(
                json.dumps(
                    {"raw_response": raw_out.get("raw_text", ""), "error": str(exc)},
                    ensure_ascii=False, indent=2,
                ),
                encoding="utf-8",
            )
            placeholder = _failure_placeholder(sample, exc)
            if existing_idx is not None:
                annotations["annotations"][existing_idx] = placeholder
            else:
                index_by_vid[sample["version_id"]] = len(annotations["annotations"])
                annotations["annotations"].append(placeholder)
            failed += 1
            _save_annotations(annotations)
            continue
        (RAW_DIR / f"{sample['genre']}-ch{sample['chapter']:03d}.json").write_text(
            json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        if existing_idx is not None:
            annotations["annotations"][existing_idx] = rec.model_dump()  # 原地替换占位
        else:
            index_by_vid[sample["version_id"]] = len(annotations["annotations"])
            annotations["annotations"].append(rec.model_dump())
        _save_annotations(annotations)
        done += 1
        print(f"prelabeled {sample['genre']} ch{sample['chapter']}")
    print(f"done={done} failed={failed}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
