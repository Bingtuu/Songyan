"""Task 170d 回测：校准前后 LiteraryAuditor 的 character_autonomy 对比.

只读隔离 DB（170b 的 .tmp/task170b_ch1_ch40.db）。
- "校准前"：读 literary_observations 里已落库的分数（1.0.1 生成）。
- "校准后"：对每章 accepted 正文用当前默认工艺卡（1.0.2）重跑 run_literary_audit。
- 对照人工 voice 终评分（170b：Ch28-Ch40 多为 1-2）。

验证目标：对白同质章的 character_autonomy 从 6.5-8.5 向人工 voice(1-2) 收敛。
不写库、不改 accept、不改冻结口径。真实 LLM，需 DeepSeek key。

用法:
    python scripts/backtest_170d_auditor_calibration.py
    $env:BT_START="28"; $env:BT_END="40"; python scripts/backtest_170d_auditor_calibration.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from songyan.config import settings

settings.database_url = os.getenv("DATABASE_URL", "sqlite:///.tmp/task170b_ch1_ch40.db")

from songyan.agents.literary_auditor import run_literary_audit  # noqa: E402
from songyan.db.repository import (  # noqa: E402
    ChapterHeadRepository,
    ChapterVersionRepository,
)
from songyan.db.review_repo import LiteraryObservationRepository  # noqa: E402
from songyan.prompts import get_prompt_loader  # noqa: E402

PROJECT_FILE = Path(".tmp/task170b_project.json")
REPORT_PATH = Path("docs/reports/task-170d-auditor-calibration-backtest.md")
BT_START = int(os.getenv("BT_START", "28"))
BT_END = int(os.getenv("BT_END", "40"))

# 170b 人工 voice 终评分（Ch28-Ch40），作为收敛目标参照（1-5 制）。
HUMAN_VOICE: dict[int, int] = {
    28: 2, 29: 2, 30: 2, 31: 1, 32: 1, 33: 1, 34: 2,
    35: 2, 36: 2, 37: 2, 38: 2, 39: 2, 40: 2,
}


def _resolve_project_id() -> str:
    return json.loads(PROJECT_FILE.read_text(encoding="utf-8"))["project_id"]


async def _amain() -> int:
    project_id = _resolve_project_id()
    card = get_prompt_loader().load_card("literary_auditor")
    print(f"[preflight] DB={settings.database_url} project={project_id}")
    print(f"[preflight] 校准后工艺卡版本 = {card.metadata.version}")
    print(f"[preflight] 窗口 Ch{BT_START}-Ch{BT_END}  真实 LLM 重跑\n")

    head_repo = ChapterHeadRepository()
    version_repo = ChapterVersionRepository()
    obs_repo = LiteraryObservationRepository()

    # 校准前分数（1.0.1 已落库）
    before_rows = await obs_repo.list_scores_by_chapter_range(project_id, BT_START, BT_END)
    before_by_ch = {int(r["chapter"]): r for r in before_rows}

    rows: list[dict] = []
    for ch in range(BT_START, BT_END + 1):
        head = await head_repo.get(project_id, ch)
        if head is None or head.status != "accepted" or not head.accepted_version_id:
            continue
        version = await version_repo.get(head.accepted_version_id)
        if version is None:
            continue

        before = before_by_ch.get(ch, {})
        before_ca = before.get("character_autonomy_score")

        # 校准后：用 1.0.2 重跑（不写库）
        result = await run_literary_audit(version.content)
        after_ca = result.character_autonomy_score
        has_polyphony = any(
            o.observation_type == "polyphony_weakness" for o in result.observations
        )

        human_voice_10 = HUMAN_VOICE.get(ch, 0) * 2.0  # 1-5 → 0-10
        # 收敛：after 比 before 更接近人工 voice(×2)
        before_gap = (
            abs(before_ca - human_voice_10) if before_ca is not None else None
        )
        after_gap = abs(after_ca - human_voice_10)
        converged = before_gap is not None and after_gap < before_gap

        rows.append(
            {
                "ch": ch,
                "before_ca": before_ca,
                "after_ca": after_ca,
                "human_voice_10": human_voice_10,
                "before_gap": before_gap,
                "after_gap": after_gap,
                "converged": converged,
                "polyphony": has_polyphony,
            }
        )
        print(
            f"Ch{ch}: before_ca={before_ca} after_ca={after_ca:.1f} "
            f"人工voice×2={human_voice_10:.0f} "
            f"{'✓收敛' if converged else '✗未收敛'} "
            f"polyphony={'有' if has_polyphony else '无'}"
        )

    _write_report(project_id, card.metadata.version, rows)
    return 0


def _fmt(v: object) -> str:
    if v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:.1f}"
    return str(v)


def _write_report(project_id: str, card_version: str, rows: list[dict]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    converged = sum(1 for r in rows if r["converged"])
    with_poly = sum(1 for r in rows if r["polyphony"])
    before_vals = [r["before_ca"] for r in rows if r["before_ca"] is not None]
    after_vals = [r["after_ca"] for r in rows if r["after_ca"] is not None]
    before_mean = sum(before_vals) / len(before_vals) if before_vals else 0.0
    after_mean = sum(after_vals) / len(after_vals) if after_vals else 0.0

    lines = [
        "# Task 170d: LiteraryAuditor 校准回测报告",
        "",
        f"> 生成时间: {ts}",
        f"> 项目: `{project_id}`  窗口: Ch{BT_START}-Ch{BT_END}",
        f"> 校准前工艺卡: 1.0.1（已落库分数）  校准后: {card_version}（重跑）",
        "> 参照: 170b 人工 voice 终评分（1-5，多为 1-2），归一到 0-10 比较。",
        "",
        "## character_autonomy_score 校准前后对比",
        "",
        "| Ch | 校准前 | 校准后 | 人工voice×2 | 前偏差 | 后偏差 | 收敛? | polyphony观察 |",
        "|---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|",
    ]
    for r in rows:
        lines.append(
            f"| {r['ch']} | {_fmt(r['before_ca'])} | {_fmt(r['after_ca'])} "
            f"| {_fmt(r['human_voice_10'])} | {_fmt(r['before_gap'])} "
            f"| {_fmt(r['after_gap'])} | {'✓' if r['converged'] else '✗'} "
            f"| {'有' if r['polyphony'] else '无'} |"
        )
    lines += [
        "",
        f"- 校准前 character_autonomy 均值: {before_mean:.2f}",
        f"- 校准后 character_autonomy 均值: {after_mean:.2f}",
        f"- 收敛章数（后偏差 < 前偏差）: {converged}/{len(rows)}",
        f"- 输出 polyphony_weakness 观察的章数: {with_poly}/{len(rows)}",
        "",
        "> 结论口径：若校准后均值显著下移、多数章向人工 voice 收敛，"
        "且对白同质章能触发 polyphony_weakness，则校准生效（方案 A 足够）。",
    ]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n[report] {REPORT_PATH}")


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_amain()))
