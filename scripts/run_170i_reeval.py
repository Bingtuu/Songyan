"""Task 170i: Ch29-Ch32 提质后抽读复评（文学提质专项 170i 出口判定）.

用法:
    # 在生成脚本跑完 Ch1-Ch32 后执行
    python scripts/run_170i_reeval.py

    # 可指定窗口 / 项目
    $env:ASSESS_START="28"; $env:ASSESS_END="32"
    python scripts/run_170i_reeval.py --project-id <pid>

    # 跳过 LLM 初评（只导出正文 + 机器分 + 洁净度 + exposition 载体）
    python scripts/run_170i_reeval.py --no-llm

说明:
    - 抽 Ch29-Ch32 accepted 正文 + LiteraryAuditor 四维机器分 + T9 洁净度
      + exposition 载体硬灌检测 + run_log 关键字段；按 5 维 rubric 做 LLM 初评。
    - 与 170h 基线逐维对比，判定是否达到 Ch200 入口标准。
    - 正文导出到 .tmp/task170i_prose_ch28_ch32.md。
    - 报告输出到 docs/reports/task-170i-remediation-reeval-report.md。
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

from songyan.agents.rule_auditor import detect_exposition_carriers
from songyan.config import settings
from songyan.db.repository import ChapterHeadRepository, ChapterVersionRepository
from songyan.db.review_repo import LiteraryObservationRepository
from songyan.evals.streaming_report import read_run_logs
from songyan.evals.text_cleanliness import (
    refresh_text_cleanliness_metrics,
)
from songyan.llm.client import call_llm
from songyan.llm.parsing import parse_llm_response

settings.database_url = os.getenv(
    "DATABASE_URL", "sqlite:///.tmp/task170i_ch1_ch32.db"
)

PROJECT_FILE = Path(".tmp/task170i_project.json")
REPORT_PATH = Path("docs/reports/task-170i-remediation-reeval-report.md")
PROSE_EXPORT_PATH = Path(".tmp/task170i_prose_ch28_ch32.md")

ASSESS_START = int(os.getenv("ASSESS_START", "29"))
ASSESS_END = int(os.getenv("ASSESS_END", "32"))

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
    except Exception as exc:  # noqa: BLE001
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
    if not llm_eval or not machine:
        return "-"
    rubric = _rubric_mean(llm_eval.get("scores", {}))
    lq = machine.get("literary_quality")
    if rubric is None or lq is None:
        return "-"
    rubric_10 = rubric * 2.0
    gap = abs(rubric_10 - float(lq))
    if gap >= 3.0:
        return f"⚠️ 偏差大(rubric≈{rubric_10:.1f} vs 机器{float(lq):.1f})"
    return f"一致(rubric≈{rubric_10:.1f} vs 机器{float(lq):.1f})"


def _export_prose(chapters: dict[int, dict[str, Any]]) -> None:
    PROSE_EXPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = [f"# Task 170i 抽读正文 Ch{ASSESS_START}-Ch{ASSESS_END}", ""]
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
    carrier_by_ch: dict[int, list[Any]],
    run_log_by_ch: dict[int, Any],
    llm_enabled: bool,
) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    clean_by_ch = {r.chapter_number: r for r in cleanliness_rows}
    chs = sorted(chapters.keys())

    lines: list[str] = [
        "# Task 170i: 中段窗口文学性/可读性复评报告（初筛）",
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
        "| exposition | 说明文堆叠 | authorial_intrusion / excessive_smoothing / exposition_carrier |",
        "| pacing | 场景节奏 | momentum / excessive_smoothing |",
        "",
        f"评分 1-5（1=差 5=好）。抽读正文见 `{PROSE_EXPORT_PATH}`。",
        "",
    ]

    lines.append("## 2. LLM 初评 5 维分")
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

    lines.append("## 4. T9 文本洁净度 + exposition 载体 + run_log")
    lines.append("")
    lines.append(
        "| Ch | meta_tag | duplicate_para | timeline_conflict | exposition_carrier | "
        "QG_passed | degraded | continuity_health |"
    )
    lines.append("|---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|")
    total_carriers = 0
    carrier_breakdown: dict[str, int] = {}
    for ch in chs:
        cr = clean_by_ch.get(ch)
        rl = run_log_by_ch.get(ch)
        qg = getattr(rl, "quality_gate_passed", None) if rl else None
        deg = getattr(rl, "degraded_accept", None) if rl else None
        health = getattr(rl, "continuity_health_score", None) if rl else None
        carriers = carrier_by_ch.get(ch, [])
        total_carriers += len(carriers)
        for c in carriers:
            carrier_breakdown[c.carrier_type] = carrier_breakdown.get(c.carrier_type, 0) + 1
        lines.append(
            f"| {ch} "
            f"| {cr.meta_tag_leak_count if cr else '-'} "
            f"| {cr.duplicate_paragraph_count if cr else '-'} "
            f"| {cr.timeline_conflict_count if cr else '-'} "
            f"| {len(carriers)} "
            f"| {_fmt(qg)} | {_fmt(deg)} | {_fmt(health)} |"
        )
    lines.append("")
    total_meta = sum(cr.meta_tag_leak_count for cr in clean_by_ch.values())
    total_dup = sum(cr.duplicate_paragraph_count for cr in clean_by_ch.values())
    lines.append(
        f"> T9 硬红线（窗口合计）：元标记泄漏 {total_meta}、整段落重复 {total_dup}。"
        f"（时间线矛盾为 report-only 诊断，不计硬红线。）"
    )
    lines.append(
        f"> exposition 载体硬灌（窗口合计）：{total_carriers} 处；"
        f"分布：{carrier_breakdown or '无'}。"
    )
    lines.append("")

    lines.append("## 5. 用户复核终评分（留空）")
    lines.append("")
    lines.append("> 请只读第 3 节 ⚠️ 偏差章和第 2 节最差维标出的章，逐章给 1-5 终评分。")
    lines.append("")
    lines.append("| Ch | ai_tone | voice | concept | exposition | pacing | 备注 |")
    lines.append("|---:|:---:|:---:|:---:|:---:|:---:|---|")
    for ch in chs:
        lines.append(f"| {ch} |  |  |  |  |  |  |")
    lines.append("")

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

    lines.append("## 7. exposition 载体硬灌明细（Task 170i 代码检测）")
    lines.append("")
    if total_carriers == 0:
        lines.append("窗口内未检测到明显 exposition 载体硬灌模式。")
    else:
        for ch in chs:
            carriers = carrier_by_ch.get(ch, [])
            if not carriers:
                continue
            lines.append(f"**Ch{ch}**（共 {len(carriers)} 处）：")
            for c in carriers:
                lines.append(
                    f"- [{c.carrier_type}] {c.severity} @ {c.location}："
                    f"{c.matched_text[:80]}"
                )
            lines.append("")
    lines.append("")

    lines.append("## 8. 与 170h 基线对比")
    lines.append("")
    lines.append("| 维度 | 170h 基线 | 170i 目标 | 备注 |")
    lines.append("|------|:---:|:---:|------|")
    lines.append("| voice | 1.75 | ≥3.0 | 170i 核心攻坚指标：人类角色声纹锚定 + 非人实体戏份限制 |")
    lines.append("| exposition | 2.5 | ≥3.0 | 170i 核心攻坚指标：认知冲突五节拍 + 主角总结容器限制 |")
    lines.append("| pacing | 3.75 | ≥3.0 | 保持，不回退 |")
    lines.append("| concept | 3.0 | ≥3.0 | 保持，不回退 |")
    lines.append("| ai_tone | 3.0 | ≥3.0 | 保持，不回退 |")
    lines.append("| T9 硬红线 | 0/0 | 0/0 | 不漏报 |")
    lines.append("| exposition_carrier | 0 | ≤1 | 代码检测不回升 |")
    lines.append("")
    lines.append(
        "## 9. Ch200 入口判定（助手初筛，非最终）"
    )
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
    lines.append(f"- exposition 载体硬灌: {total_carriers} 处")
    lines.append("")

    if window_mean is not None:
        if window_mean >= 3.0 and total_carriers <= 1 and total_meta == 0 and total_dup == 0:
            lines.append(
                "**初筛观察**：窗口均值、T9 硬红线、exposition 载体均达到 Ch200 入口候选线。"
                "最终是否放行需用户复核第 5 节终评分与第 6 节可疑摘录后决定。"
            )
        else:
            lines.append(
                "**初筛观察**：未同时满足 Ch200 入口标准（窗口均值≥3.0、T9 0/0、"
                f"exposition_carrier≤1），维持 blocker，继续 170i+ 迭代或升级路径。"
            )
    else:
        lines.append("**初筛观察**：LLM 初评缺失，无法给出 Ch200 入口判定。")
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

    cleanliness_rows = await refresh_text_cleanliness_metrics(
        project_id, ASSESS_START, ASSESS_END
    )

    carrier_by_ch: dict[int, list[Any]] = {}
    for ch in sorted(chapters.keys()):
        carrier_by_ch[ch] = detect_exposition_carriers(chapters[ch]["content"])

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

    llm_evals: dict[int, dict[str, Any] | None] = {}
    if llm_enabled:
        for ch in sorted(chapters.keys()):
            print(f"[llm] rubric eval Ch{ch} ...")
            llm_evals[ch] = await _llm_rubric_eval(ch, chapters[ch]["content"])
    else:
        llm_evals = {ch: None for ch in chapters}

    _write_report(
        project_id, chapters, machine, llm_evals, cleanliness_rows,
        carrier_by_ch, run_log_by_ch, llm_enabled
    )
    print("\n=== Done ===")
    print(f"Prose: {PROSE_EXPORT_PATH}")
    print(f"Report: {REPORT_PATH}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Task 170i Ch29-Ch32 提质后复评")
    parser.add_argument("--project-id", default=None)
    parser.add_argument("--no-llm", action="store_true", help="跳过 LLM 初评，只导出正文+机器分")
    args = parser.parse_args()
    project_id = _resolve_project_id(args.project_id)
    if not project_id:
        parser.error(
            "无法确定 project_id；用 --project-id 或先跑生成脚本"
            "（写 .tmp/task170i_project.json）"
        )
    return asyncio.run(_amain(project_id, not args.no_llm))


if __name__ == "__main__":
    raise SystemExit(main())
