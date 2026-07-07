"""Task 170f Stage 2: Ch29-Ch32 抽读评估（pacing/exposition 小样本验证）.

用法:
    # 在生成脚本跑完 Ch1-Ch32 后执行（复用同一隔离 DB）
    python scripts/run_170f_stage2_reeval.py

    # 可指定窗口 / 项目
    $env:ASSESS_START="29"; $env:ASSESS_END="32"
    python scripts/run_170f_stage2_reeval.py --project-id <pid>

    # 跳过 LLM 初评（只导出正文 + 机器分 + 洁净度，供纯人工实读）
    python scripts/run_170f_stage2_reeval.py --no-llm

说明:
    - 助手初筛：抽 Ch29-Ch32 accepted 正文 + LiteraryAuditor 四维机器分 + T9 洁净度
      + run_log 关键字段；按 5 维 rubric 做 LLM 初评，标出可疑段落与机器/人工偏差候选。
    - 用户复核：读 docs/reports/task-170f-... 中标出的重点，给 5 维终评分。
    - 不改生成侧任何 Agent；不改 accept 行为；不放宽任何冻结口径。
    - 正文导出到 .tmp/task170f_stage2_prose_ch29_ch32.md（供人工逐章实读）。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from songyan.config import settings
from songyan.db.repository import ChapterHeadRepository, ChapterVersionRepository
from songyan.db.review_repo import LiteraryObservationRepository
from songyan.evals.streaming_report import read_run_logs
from songyan.evals.text_cleanliness import (
    refresh_text_cleanliness_metrics,
)
from songyan.llm.client import call_llm
from songyan.llm.parsing import parse_llm_response

# 安全默认：强制指向隔离 DB（与生成脚本一致），避免误读/误写主库。
settings.database_url = os.getenv(
    "DATABASE_URL", "sqlite:///.tmp/task170f_stage2_ch1_ch32.db"
)

PROJECT_FILE = Path(".tmp/task170f_stage2_project.json")
REPORT_PATH = Path("docs/reports/task-170f-stage2-reeval-report.md")
PROSE_EXPORT_PATH = Path(".tmp/task170f_stage2_prose_ch29_ch32.md")

ASSESS_START = int(os.getenv("ASSESS_START", "29"))
ASSESS_END = int(os.getenv("ASSESS_END", "32"))

# 5 维 rubric（对齐已有机器维度）
RUBRIC_DIMENSIONS = [
    ("ai_tone", "AI 腔密度", "句式模板化/排比堆砌/万能过渡句 → 句式自然多变"),
    ("voice", "角色声纹区分度", "谁说话都一个腔 → 对白可辨身份、有个体语气"),
    ("concept", "概念空转", "科幻名词砸脸不落地 → 概念有具体质感与后果"),
    ("exposition", "说明文堆叠", "大段解说/设定清单式交代 → 信息融进动作与场景"),
    ("pacing", "场景节奏", "平铺无张力/停滞 → 有推进、有张弛呼吸"),
]

_RUBRIC_PROMPT = """你是一位严格的中文长篇小说文学编辑。下面是一部硬科幻网文的某一章正文。
请按 5 个维度各打 1-5 分（1=差，5=好），并给出**具体证据引文**和一句话理由。
评分要严格、挑剔，宁低勿高；不要被流畅度迷惑——"干净但无聊"应给低分。

5 个维度：
1. ai_tone（AI 腔密度）：句式是否模板化、排比堆砌、万能过渡句泛滥。分越高越自然多变。
2. voice（角色声纹区分度）：不同角色对白是否可辨身份、有个体语气。分越高越有区分。
3. concept（概念空转）：科幻名词是否落地、有具体质感与后果，而非砸脸空转。分越高越落地。
4. exposition（说明文堆叠）：信息是否融进动作/场景，而非大段解说、设定清单式交代。分越高越自然。
5. pacing（场景节奏）：是否有推进、有张弛呼吸，而非平铺无张力或停滞。分越高越好。

只输出 JSON，格式：
{
  "scores": {"ai_tone": <int>, "voice": <int>, "concept": <int>,
             "exposition": <int>, "pacing": <int>},
  "evidence": {"ai_tone": "引文或说明", "voice": "...", "concept": "...",
               "exposition": "...", "pacing": "..."},
  "worst_dimension": "<上面 5 个 key 之一>",
  "suspicious_excerpt": "本章最能暴露问题的一段原文摘录（50-120字）",
  "one_line_verdict": "一句话总评"
}

章节正文：
---
{content}
---
"""


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
    """按 head 指针取 Ch29-Ch32 的 accepted 正文."""
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


def _machine_scores_by_chapter(rows: list[dict]) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for row in rows:
        ch = row.get("chapter")
        if ch is None:
            continue
        out[int(ch)] = {
            "literary_quality": row.get("literary_quality_score"),
            "character_autonomy": row.get("character_autonomy_score"),
            "conceptual_grounding": row.get("conceptual_grounding_score"),
            "fissure_preservation": row.get("fissure_preservation_score"),
        }
    return out


async def _llm_rubric_eval(chapter: int, content: str) -> dict[str, Any] | None:
    prompt = _RUBRIC_PROMPT.replace("{content}", content[:8000])
    try:
        resp = await call_llm(prompt, temperature=0.3, max_tokens=1200)
        data = parse_llm_response(resp)
    except Exception as exc:  # noqa: BLE001 - 初筛容错，失败记 None 不中断
        print(f"[warn] Ch{chapter} rubric eval failed: {exc}")
        return None
    scores = data.get("scores", {})
    if not isinstance(scores, dict):
        return None
    return data


def _rubric_mean(scores: dict[str, Any]) -> float | None:
    vals = []
    for key, _, _ in RUBRIC_DIMENSIONS:
        v = scores.get(key)
        if isinstance(v, (int, float)):
            vals.append(float(v))
    return sum(vals) / len(vals) if vals else None


def _divergence_flag(
    llm_eval: dict[str, Any] | None, machine: dict[str, Any] | None
) -> str:
    """粗判 LLM 初评均分(1-5) 与机器 literary_quality(0-10) 是否明显背离."""
    if not llm_eval or not machine:
        return "-"
    rubric = _rubric_mean(llm_eval.get("scores", {}))
    lq = machine.get("literary_quality")
    if rubric is None or lq is None:
        return "-"
    # 归一到 0-10 比较
    rubric_10 = rubric * 2.0
    gap = abs(rubric_10 - float(lq))
    if gap >= 3.0:
        return f"⚠️ 偏差大(rubric≈{rubric_10:.1f} vs 机器{float(lq):.1f})"
    return f"一致(rubric≈{rubric_10:.1f} vs 机器{float(lq):.1f})"


def _export_prose(chapters: dict[int, dict[str, Any]]) -> None:
    PROSE_EXPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = [f"# Task 170f Stage 2 抽读正文 Ch{ASSESS_START}-Ch{ASSESS_END}", ""]
    for ch in sorted(chapters.keys()):
        lines.append(f"## 第 {ch} 章（{chapters[ch]['word_count']} 字）")
        lines.append("")
        lines.append(chapters[ch]["content"])
        lines.append("")
        lines.append("---")
        lines.append("")
    PROSE_EXPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"[export] prose -> {PROSE_EXPORT_PATH}")


def _fmt(v: Any) -> str:
    if v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:.2f}"
    return str(v)


def _write_report(
    project_id: str,
    chapters: dict[int, dict[str, Any]],
    machine: dict[int, dict[str, Any]],
    llm_evals: dict[int, dict[str, Any] | None],
    cleanliness_rows: list[Any],
    run_log_by_ch: dict[int, Any],
    llm_enabled: bool,
) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    clean_by_ch = {r.chapter_number: r for r in cleanliness_rows}
    chs = sorted(chapters.keys())

    lines: list[str] = [
        "# Task 170f Stage 2: Ch29-Ch32 pacing/exposition 提质复评报告（初筛）",
        "",
        f"> 生成时间: {ts}",
        f"> 项目: `{project_id}`  窗口: Ch{ASSESS_START}-Ch{ASSESS_END}  抽到章数: {len(chs)}",
        "> 本报告为**助手初筛**：LLM 按 5 维 rubric 预评 + 机器分对照 + 标可疑点。",
        "> **最终文学判定以用户复核终评分为准**（见第 5 节留空表）。",
        "",
        "## 1. 5 维 rubric 说明",
        "",
        "| 维度 | 含义 | 对应机器信号 |",
        "|------|------|--------------|",
        "| ai_tone | AI 腔密度 | ai_rhythm_pattern / RuleAuditor |",
        "| voice | 角色声纹区分度 | polyphony_weakness / character_autonomy |",
        "| concept | 概念空转 | conceptual_idling / conceptual_grounding |",
        "| exposition | 说明文堆叠 | authorial_intrusion / excessive_smoothing |",
        "| pacing | 场景节奏 | momentum / excessive_smoothing |",
        "",
        "评分 1-5（1=差 5=好）。抽读正文见 `.tmp/task170f_stage2_prose_ch29_ch32.md`。",
        "",
    ]

    # 2. LLM 初评 5 维分
    lines.append("## 2. LLM 初评 5 维分（初筛，非最终）")
    lines.append("")
    if not llm_enabled:
        lines.append("（本次运行 --no-llm，跳过 LLM 初评；请纯人工实读打分。）")
        lines.append("")
    else:
        lines.append(
            "| Ch | ai_tone | voice | concept | exposition | pacing "
            "| 均值 | 最差维 | 一句话总评 |"
        )
        lines.append("|---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|")
        for ch in chs:
            ev = llm_evals.get(ch)
            if not ev:
                lines.append(f"| {ch} | - | - | - | - | - | - | - | (初评失败) |")
                continue
            sc = ev.get("scores", {})
            mean = _rubric_mean(sc)
            lines.append(
                f"| {ch} | {_fmt(sc.get('ai_tone'))} | {_fmt(sc.get('voice'))} "
                f"| {_fmt(sc.get('concept'))} | {_fmt(sc.get('exposition'))} "
                f"| {_fmt(sc.get('pacing'))} | {_fmt(mean)} "
                f"| {ev.get('worst_dimension', '-')} | {ev.get('one_line_verdict', '')} |"
            )
        lines.append("")

    # 3. 机器分 vs LLM 初评 偏差
    lines.append("## 3. 机器分 vs LLM 初评 偏差（诊断可信度）")
    lines.append("")
    lines.append(
        "| Ch | 机器 literary_quality | 机器 character_autonomy "
        "| 机器 conceptual_grounding | LLM rubric 均值(×2) | 偏差判定 |"
    )
    lines.append("|---:|:---:|:---:|:---:|:---:|---|")
    for ch in chs:
        m = machine.get(ch, {})
        ev = llm_evals.get(ch)
        rubric = _rubric_mean(ev.get("scores", {})) if ev else None
        rubric_10 = f"{rubric * 2:.1f}" if rubric is not None else "-"
        lines.append(
            f"| {ch} | {_fmt(m.get('literary_quality'))} "
            f"| {_fmt(m.get('character_autonomy'))} "
            f"| {_fmt(m.get('conceptual_grounding'))} "
            f"| {rubric_10} | {_divergence_flag(ev, m)} |"
        )
    lines.append("")
    lines.append("> 偏差判定：LLM rubric 均值归一到 0-10 后与机器 literary_quality 相差 ≥3 记 ⚠️。")
    lines.append("> ⚠️ 项是「机器诊断可能失真」的候选，需用户重点复核。")
    lines.append("")

    # 4. T9 洁净度 + run_log 关键字段
    lines.append("## 4. T9 文本洁净度 + run_log（硬红线与治理状态）")
    lines.append("")
    lines.append(
        "| Ch | meta_tag | duplicate_para | timeline_conflict "
        "| QG_passed | degraded | continuity_health |"
    )
    lines.append("|---:|:---:|:---:|:---:|:---:|:---:|:---:|")
    for ch in chs:
        cr = clean_by_ch.get(ch)
        rl = run_log_by_ch.get(ch)
        qg = getattr(rl, "quality_gate_passed", None) if rl else None
        deg = getattr(rl, "degraded_accept", None) if rl else None
        health = getattr(rl, "continuity_health_score", None) if rl else None
        lines.append(
            f"| {ch} "
            f"| {cr.meta_tag_leak_count if cr else '-'} "
            f"| {cr.duplicate_paragraph_count if cr else '-'} "
            f"| {cr.timeline_conflict_count if cr else '-'} "
            f"| {_fmt(qg)} | {_fmt(deg)} | {_fmt(health)} |"
        )
    lines.append("")
    total_meta = sum(cr.meta_tag_leak_count for cr in clean_by_ch.values())
    total_dup = sum(cr.duplicate_paragraph_count for cr in clean_by_ch.values())
    lines.append(
        f"> T9 硬红线（窗口合计）：元标记泄漏 {total_meta}、整段落重复 {total_dup}。"
        f"（时间线矛盾为 report-only 诊断，不计硬红线。）"
    )
    lines.append("")

    # 5. 用户复核终评分（留空）
    lines.append("## 5. 用户复核终评分（待填）")
    lines.append("")
    lines.append("> 请只读第 3 节 ⚠️ 偏差章和第 2 节最差维标出的章，逐章给 1-5 终评分。")
    lines.append("")
    lines.append("| Ch | ai_tone | voice | concept | exposition | pacing | 备注 |")
    lines.append("|---:|:---:|:---:|:---:|:---:|:---:|---|")
    for ch in chs:
        lines.append(f"| {ch} |  |  |  |  |  |  |")
    lines.append("")

    # 6. 可疑段落摘录
    lines.append("## 6. 可疑段落摘录（LLM 标出，供复核定位）")
    lines.append("")
    if llm_enabled:
        for ch in chs:
            ev = llm_evals.get(ch)
            if not ev:
                continue
            excerpt = ev.get("suspicious_excerpt", "")
            if excerpt:
                lines.append(f"**Ch{ch}**（最差维 {ev.get('worst_dimension', '-')}）：{excerpt}")
                lines.append("")
    else:
        lines.append("（--no-llm，无摘录。）")
        lines.append("")

    # 7. 初筛结论（助手观察，非最终判定）
    lines.append("## 7. 初筛观察（助手，非最终判定）")
    lines.append("")
    means = [
        _rubric_mean(llm_evals[ch].get("scores", {}))
        for ch in chs
        if llm_evals.get(ch)
    ]
    means = [m for m in means if m is not None]
    window_mean = sum(means) / len(means) if means else None
    divergent = sum(
        1 for ch in chs if "⚠️" in _divergence_flag(llm_evals.get(ch), machine.get(ch))
    )
    lines.append(f"- LLM 初评窗口 5 维均值: {_fmt(window_mean)} / 5")
    lines.append(f"- 机器/LLM 偏差大(⚠️)的章数: {divergent} / {len(chs)}")
    lines.append(f"- T9 硬红线: 元标记 {total_meta}、整段落重复 {total_dup}")
    lines.append("")
    lines.append(
        "> 这是助手初筛观察，**不是 pass/observation/blocker 判定**。"
        "最终判定需用户复核后，在 170f DONE 文档或 170g 复评中给出。"
    )
    lines.append("")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"[report] {REPORT_PATH}")


async def _amain(project_id: str, llm_enabled: bool) -> int:
    print(
        f"[preflight] project={project_id}, "
        f"window=Ch{ASSESS_START}-Ch{ASSESS_END}, llm={llm_enabled}"
    )

    chapters = await _load_accepted_content(project_id)
    if not chapters:
        print("[error] 窗口内没有 accepted 章节；请先跑生成脚本。")
        return 1
    print(f"[load] accepted chapters in window: {sorted(chapters.keys())}")

    _export_prose(chapters)

    score_rows = await LiteraryObservationRepository().list_scores_by_chapter_range(
        project_id, ASSESS_START, ASSESS_END
    )
    machine = _machine_scores_by_chapter(score_rows)

    # T9 洁净度：run 中不自动填，先复算落库再用返回值
    cleanliness_rows = await refresh_text_cleanliness_metrics(
        project_id, ASSESS_START, ASSESS_END
    )

    # run log（最近一次 run）
    run_log_by_ch: dict[int, Any] = {}
    try:
        from songyan.db import get_db

        async with get_db() as conn:
            conn.row_factory = lambda c, r: {d[0]: r[i] for i, d in enumerate(c.description)}
            cur = await conn.execute(
                "SELECT run_id FROM project_runs WHERE project_id = ? "
                "ORDER BY created_at DESC LIMIT 1",
                (project_id,),
            )
            rows = await cur.fetchall()
        run_id = rows[0]["run_id"] if rows else None
        if run_id:
            for log in read_run_logs(run_id):
                run_log_by_ch[log.chapter_number] = log
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] run_log load failed: {exc}")

    # LLM 初评
    llm_evals: dict[int, dict[str, Any] | None] = {}
    if llm_enabled:
        for ch in sorted(chapters.keys()):
            print(f"[llm] rubric eval Ch{ch} ...")
            llm_evals[ch] = await _llm_rubric_eval(ch, chapters[ch]["content"])
    else:
        llm_evals = {ch: None for ch in chapters}

    _write_report(
        project_id, chapters, machine, llm_evals, cleanliness_rows, run_log_by_ch, llm_enabled
    )
    print("\n=== Done ===")
    print(f"Prose: {PROSE_EXPORT_PATH}")
    print(f"Report: {REPORT_PATH}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Task 170f Stage 2 Ch29-Ch32 抽读评估")
    parser.add_argument("--project-id", default=None)
    parser.add_argument("--no-llm", action="store_true", help="跳过 LLM 初评，只导出正文+机器分")
    args = parser.parse_args()
    project_id = _resolve_project_id(args.project_id)
    if not project_id:
        parser.error(
            "无法确定 project_id；用 --project-id 或先跑生成脚本"
            "（写 .tmp/task170f_stage2_project.json）"
        )
    return asyncio.run(_amain(project_id, not args.no_llm))


if __name__ == "__main__":
    raise SystemExit(main())
