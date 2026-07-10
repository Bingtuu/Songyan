"""Task 170m: Recalibrated exposition-carrier evaluation with ground truth.

用法:
    # 先完成人工终审（修改 .tmp/ground_truth/task170m_ch30_ch32_ground_truth.jsonl
    # 中每个 candidate 的 human_verdict 字段）
    python scripts/run_170m_reeval.py

输出:
    docs/reports/task-170m-exposition-carrier-recalibration-report.md
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from songyan.agents.rule_auditor import detect_exposition_carriers
from songyan.config import settings
from songyan.db import LiteraryKeywordRepository
from songyan.db.repository import ChapterHeadRepository, ChapterVersionRepository

settings.database_url = os.getenv(
    "DATABASE_URL", "sqlite:///.tmp/task170l_few_shot_voice_anchor.db"
)

PROJECT_FILE = Path(".tmp/task170l_few_shot_voice_anchor_project.json")
GROUND_TRUTH_PATH = Path(".tmp/ground_truth/task170m_ch30_ch32_ground_truth.jsonl")
REPORT_PATH = Path("docs/reports/task-170m-exposition-carrier-recalibration-report.md")

ASSESS_START = int(os.getenv("ASSESS_START", "30"))
ASSESS_END = int(os.getenv("ASSESS_END", "32"))

# 与 170l 静态检测报告的窗口合计数对比（来源：task-170l-few-shot-voice-anchor-reeval-report.md）
BASELINE_STATIC_COUNT = 72


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


def _load_ground_truth(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            verdict = rec.get("human_verdict")
            if verdict == "reject":
                continue
            if verdict is None:
                # 尚未终审，不计入 ground truth
                continue
            if isinstance(verdict, str) and verdict.startswith("retype:"):
                rec["carrier_type"] = verdict.split(":", 1)[1].strip()
            records.append(rec)
    return records


def _overlap(a_start: int | None, a_end: int | None, b_start: int | None, b_end: int | None) -> bool:
    """判断两个标注是否重叠；任一方无偏移时退化为同章同类型匹配。"""
    if a_start is None or a_end is None or b_start is None or b_end is None:
        return True
    return min(a_end, b_end) > max(a_start, b_start)


def _evaluate(
    ground_truth: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
) -> dict[str, Any]:
    """按 carrier_type 拆分计算 P/R/F1。"""
    types = sorted({r["carrier_type"] for r in ground_truth} | {r["carrier_type"] for r in predictions})
    per_type: dict[str, dict[str, Any]] = {}
    total_tp = total_fp = total_fn = 0

    for ctype in types:
        gt_list = [r for r in ground_truth if r["carrier_type"] == ctype]
        pred_list = [r for r in predictions if r["carrier_type"] == ctype]
        matched_pred: set[int] = set()
        matched_gt: set[int] = set()

        for gi, g in enumerate(gt_list):
            for pi, p in enumerate(pred_list):
                if pi in matched_pred:
                    continue
                if g["chapter"] != p["chapter"]:
                    continue
                if not _overlap(g.get("start"), g.get("end"), p.get("start"), p.get("end")):
                    continue
                matched_gt.add(gi)
                matched_pred.add(pi)
                break

        tp = len(matched_gt)
        fp = len(pred_list) - len(matched_pred)
        fn = len(gt_list) - len(matched_gt)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )
        per_type[ctype] = {
            "gt_count": len(gt_list),
            "pred_count": len(pred_list),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(f1, 3),
        }
        total_tp += tp
        total_fp += fp
        total_fn += fn

    total_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) else 0.0
    total_recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) else 0.0
    total_f1 = (
        2 * total_precision * total_recall / (total_precision + total_recall)
        if (total_precision + total_recall) > 0
        else 0.0
    )

    return {
        "per_type": per_type,
        "overall": {
            "tp": total_tp,
            "fp": total_fp,
            "fn": total_fn,
            "precision": round(total_precision, 3),
            "recall": round(total_recall, 3),
            "f1": round(total_f1, 3),
        },
    }


def _fmt(v: float) -> str:
    return f"{v:.3f}"


async def _amain(project_id: str) -> int:
    print(f"[preflight] project={project_id}, window=Ch{ASSESS_START}-Ch{ASSESS_END}")

    chapters = await _load_accepted_content(project_id)
    if not chapters:
        print("[error] 窗口内没有 accepted 章节。")
        return 1

    keyword_repo = LiteraryKeywordRepository()
    keywords = await keyword_repo.load_exposition_keywords(project_id)

    ground_truth = _load_ground_truth(GROUND_TRUTH_PATH)
    print(f"[ground_truth] {len(ground_truth)} accepted labels")

    predictions: list[dict[str, Any]] = []
    pred_by_ch: dict[int, int] = defaultdict(int)
    for ch in sorted(chapters.keys()):
        content = chapters[ch]["content"]
        carriers = detect_exposition_carriers(
            content,
            character_names=keywords["character_names"],
            non_character_keywords=keywords["non_character_keywords"],
            info_delivery_keywords=keywords["setting_keywords"],
        )
        pred_by_ch[ch] = len(carriers)
        for c in carriers:
            predictions.append(
                {
                    "chapter": ch,
                    "carrier_type": c.carrier_type,
                    "start": c.start,
                    "end": c.end,
                    "matched_text": c.matched_text,
                }
            )

    eval_result = _evaluate(ground_truth, predictions)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines: list[str] = [
        "# Task 170m: exposition carrier 量具二次校准报告",
        "",
        f"> 生成时间: {ts}",
        f"> 项目: `{project_id}` 窗口: Ch{ASSESS_START}-Ch{ASSESS_END}",
        "> 本报告基于 **动态关键词 + 人工/半人工 ground truth** 重新计算 exposition carrier 检测器的 P/R/F1。",
        "",
        "## 1. 动态关键词抽取",
        "",
        f"- 角色名: {len(keywords['character_names'])} 个 ({', '.join(sorted(keywords['character_names']))})",
        f"- 设定关键词: {len(keywords['setting_keywords'])} 个",
        f"- 非人实体候选: {len(keywords['non_character_keywords'])} 个 ({', '.join(sorted(keywords['non_character_keywords']))})",
        "",
        "## 2. 检测计数对比",
        "",
        "| 来源 | Ch30 | Ch31 | Ch32 | 合计 |",
        "|---:|---:|---:|---:|---:|",
    ]
    lines.append(
        f"| 170l 静态硬编码检测 | - | - | - | {BASELINE_STATIC_COUNT} |"
    )
    lines.append(
        f"| 170m 动态关键词检测 | {pred_by_ch.get(30, 0)} | {pred_by_ch.get(31, 0)} | "
        f"{pred_by_ch.get(32, 0)} | {sum(pred_by_ch.values())} |"
    )
    lines.append("")
    lines.append(
        "> 说明：静态计数来自 170l 复评报告（硬编码科幻关键词）；动态计数使用从 `setting_snapshots` / "
        "`characters` 抽取的项目实际关键词。"
    )
    lines.append("")

    lines.append("## 3. Ground truth 终审状态")
    lines.append("")
    lines.append(f"- ground truth 文件: `{GROUND_TRUTH_PATH}`")
    lines.append(f"- 已接受标签数: {len(ground_truth)}")
    if not ground_truth:
        lines.append(
            "- ⚠️ 尚未有人工终审标签；请在 ground truth 文件中填写 `human_verdict` 后重跑本脚本。"
        )
    lines.append("")

    lines.append("## 4. 按 carrier_type 的 P/R/F1")
    lines.append("")
    lines.append(
        "| carrier_type | GT | Pred | TP | FP | FN | Precision | Recall | F1 |"
    )
    lines.append("|:---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for ctype, vals in eval_result["per_type"].items():
        lines.append(
            f"| {ctype} | {vals['gt_count']} | {vals['pred_count']} | {vals['tp']} | "
            f"{vals['fp']} | {vals['fn']} | {_fmt(vals['precision'])} | {_fmt(vals['recall'])} | {_fmt(vals['f1'])} |"
        )
    ov = eval_result["overall"]
    lines.append(
        f"| **Overall** | **{ov['tp'] + ov['fn']}** | **{ov['tp'] + ov['fp']}** | "
        f"**{ov['tp']}** | **{ov['fp']}** | **{ov['fn']}** | "
        f"**{_fmt(ov['precision'])}** | **{_fmt(ov['recall'])}** | **{_fmt(ov['f1'])}** |"
    )
    lines.append("")

    lines.append("## 5. 漏报 / 误报样例")
    lines.append("")
    # Compute false positives / false negatives for display
    fp_samples: list[str] = []
    fn_samples: list[str] = []
    for ctype, vals in eval_result["per_type"].items():
        gt_list = [r for r in ground_truth if r["carrier_type"] == ctype]
        pred_list = [r for r in predictions if r["carrier_type"] == ctype]
        matched_gt, matched_pred = set(), set()
        for gi, g in enumerate(gt_list):
            for pi, p in enumerate(pred_list):
                if pi in matched_pred:
                    continue
                if g["chapter"] != p["chapter"]:
                    continue
                if not _overlap(g.get("start"), g.get("end"), p.get("start"), p.get("end")):
                    continue
                matched_gt.add(gi)
                matched_pred.add(pi)
                break
        for pi, p in enumerate(pred_list):
            if pi not in matched_pred:
                excerpt = (p.get("matched_text") or "")[:80].replace("\n", " ")
                fp_samples.append(f"- **Ch{p['chapter']}** [{ctype}]: {excerpt}")
        for gi, g in enumerate(gt_list):
            if gi not in matched_gt:
                excerpt = (g.get("matched_text") or g.get("paragraph_text", ""))[:80].replace("\n", " ")
                fn_samples.append(f"- **Ch{g['chapter']}** [{ctype}]: {excerpt}")

    if fp_samples:
        lines.append("### 5.1 误报（机器标出但 ground truth 未接受）")
        lines.extend(fp_samples[:10])
        lines.append("")
    else:
        lines.append("### 5.1 误报")
        lines.append("无。")
        lines.append("")

    if fn_samples:
        lines.append("### 5.2 漏报（ground truth 接受但机器未标出）")
        lines.extend(fn_samples[:10])
        lines.append("")
    else:
        lines.append("### 5.2 漏报")
        lines.append("无。")
        lines.append("")

    lines.append("## 6. 校准结论与建议")
    lines.append("")
    if not ground_truth:
        lines.append(
            "- ⚠️ 缺少人工终审 ground truth，本节的 P/R/F1 均为 0。"
            "请先完成 `.tmp/ground_truth/task170m_ch30_ch32_ground_truth.jsonl` 的终审。"
        )
    else:
        if ov["precision"] >= 0.8 and ov["recall"] >= 0.8:
            lines.append(
                f"- 整体 P={_fmt(ov['precision'])} / R={_fmt(ov['recall'])} / F1={_fmt(ov['f1'])}，"
                "量具可信，可将动态检测接入日常 reeval。"
            )
        elif ov["recall"] < 0.6:
            lines.append(
                f"- 召回率仅 {_fmt(ov['recall'])}，说明机器预标严重漏报；"
                "建议放宽引语长度阈值或扩展 info_delivery 关键词。"
            )
        elif ov["precision"] < 0.6:
            lines.append(
                f"- 精确率仅 {_fmt(ov['precision'])}，说明机器预标误报较多；"
                "建议收紧阈值、过滤高频噪音词或增加冲突/代价前置检查。"
            )
        else:
            lines.append(
                f"- 整体 P={_fmt(ov['precision'])} / R={_fmt(ov['recall'])} / F1={_fmt(ov['f1'])}，"
                "量具有效但仍有优化空间，建议按第 5 节样例定向调整阈值。"
            )
        lines.append(
            f"- 与 170l 静态计数 {BASELINE_STATIC_COUNT} 相比，动态检测总数为 {sum(pred_by_ch.values())}，"
            "差异主要来自硬编码科幻关键词被替换为项目实际关键词。"
        )
    lines.append("")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"[report] {REPORT_PATH}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Task 170m recalibrated exposition carrier evaluation")
    parser.add_argument("--project-id", default=None)
    args = parser.parse_args()
    project_id = _resolve_project_id(args.project_id)
    if not project_id:
        parser.error("无法确定 project_id；用 --project-id 或 PROJECT_ID 环境变量")
    return asyncio.run(_amain(project_id))


if __name__ == "__main__":
    raise SystemExit(main())
