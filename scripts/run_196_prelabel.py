"""Task 196: LLM 批量预标（纯离线，不进生成链路）."""

from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from songyan.evals.excellence_sampling import AnnotationRecord, load_chapter_content
from songyan.llm.client import call_llm
from songyan.llm.parsing import parse_llm_response
from songyan.prompts.loader import get_prompt_loader

SAMPLE_SET = Path("tasks/196-excellence-sample-set.json")
ANNOTATIONS = Path("tasks/196-excellence-annotations.json")
RAW_DIR = Path(".tmp/196_prelabel_raw")


def _connect_readonly(db_path: str) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{Path(db_path).as_posix()}?mode=ro", uri=True)


def _save_annotations(annotations: dict) -> None:
    ANNOTATIONS.write_text(
        json.dumps(annotations, ensure_ascii=False, indent=2), encoding="utf-8"
    )


async def _prelabel_one(sample: dict, content: str) -> tuple[AnnotationRecord, dict]:
    loader = get_prompt_loader()
    card = loader.load_card("excellence_prelabel")
    rendered = loader.render_card(
        card, {"genre": sample["genre"], "chapter_content": content}
    )
    raw_text = await call_llm(
        rendered.system_prompt, temperature=0.3, max_tokens=1024, timeout=120
    )
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


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit", type=int, default=None, help="最多预标多少章（smoke 调试用）"
    )
    args = parser.parse_args()
    sample_set = json.loads(SAMPLE_SET.read_text(encoding="utf-8"))
    annotations = json.loads(ANNOTATIONS.read_text(encoding="utf-8"))

    dbs = {s["genre"]: s["db"] for s in sample_set["sources"]}
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    done = failed = 0
    for sample in sample_set["samples"]:
        # 幂等：已存在任何 layer 的同 version_id 记录一律跳过，重跑不产生重复
        if any(
            a["version_id"] == sample["version_id"] for a in annotations["annotations"]
        ):
            continue
        if args.limit is not None and done + failed >= args.limit:
            break
        conn = _connect_readonly(dbs[sample["genre"]])
        content = load_chapter_content(conn, sample["version_id"])
        conn.close()
        try:
            rec, raw = await _prelabel_one(sample, content)
        except Exception as exc:  # noqa: BLE001 — 失败章记 disagreement，不中断批量
            annotations["annotations"].append(
                AnnotationRecord(
                    genre=sample["genre"], chapter=sample["chapter"],
                    version_id=sample["version_id"], sample_layer="prelabel",
                    scores={"homogeneity": 3, "tension": 3, "ai_tone": 3, "overall": 3},
                    annotator="llm-prelabel",
                    disagreement=f"prelabel_parse_failed: {exc}",
                ).model_dump()
            )
            failed += 1
            _save_annotations(annotations)
            continue
        (RAW_DIR / f"{sample['genre']}-ch{sample['chapter']:03d}.json").write_text(
            json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        annotations["annotations"].append(rec.model_dump())
        _save_annotations(annotations)
        done += 1
        print(f"prelabeled {sample['genre']} ch{sample['chapter']}")
    print(f"done={done} failed={failed}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
