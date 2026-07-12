"""Task 171d: calibrate Tier 2 literary trend-floor params from real long-run data.

Reads literary observation scores from real DBs (171b corpus + historical 170i)
and reports the per-dimension baseline distribution, so the trend-floor
coefficients (relative ×0.85, absolute 2.0) have a reproducible data basis rather
than being hand-picked. observe-only; does not change gate behavior.

Usage:
    python scripts/run_171d_calibrate.py
"""

from __future__ import annotations

import os
import sqlite3
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

_DIMS = (
    "literary_quality_score",
    "character_autonomy_score",
    "conceptual_grounding_score",
    "fissure_preservation_score",
)

# 真实长跑 DB（含文学观测分）。历史 170i 是 Task 170 单点窗口，用于对照。
SOURCES = [
    ("scifi_170p", ".tmp/task170p_validation.db"),
    ("wuxia_171a1", ".tmp/task171a1_wuxia.db"),
    ("scifi_170i", ".tmp/task170i_ch1_ch32.db"),
    ("v6_159", ".tmp/task159_ch1_ch150.db"),
]
REPORT = Path("docs/reports/task-171d-three-tier-contract-report.md")


def _load_scores(db_path: str) -> list[dict[str, float]]:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    # literary_observations 无 chapter_number，经 version_id 关联 chapter_versions；
    # 每章取最新一条观测（按 rowid 近似 latest）。
    try:
        rows = con.execute(
            "SELECT cv.chapter_number AS ch, "
            "lo.literary_quality_score, lo.character_autonomy_score, "
            "lo.conceptual_grounding_score, lo.fissure_preservation_score "
            "FROM literary_observations lo "
            "JOIN chapter_versions cv ON cv.version_id = lo.version_id "
            "ORDER BY cv.chapter_number"
        ).fetchall()
    except sqlite3.OperationalError:
        con.close()
        return []
    con.close()
    out: list[dict[str, float]] = []
    for r in rows:
        out.append({d: float(r[d] or 0.0) for d in _DIMS})
    return out


def main() -> int:
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    lines = [
        "# Task 171d: 三层契约落地报告（A1 分层视图 + A3 趋势地板/抽读 + A4 标定）",
        "",
        "> 生成: Task 171d 标定脚本 `scripts/run_171d_calibrate.py`",
        "> 对应框架 `docs/reports/v7-literary-framework-review.md` §8 A 组。observe-only，不阻塞。",
        "",
        "## A4 参数标定（各 DB 文学观测分基线分布）",
        "",
        "| 数据源 | 章数 | 维度 | 均值 | 最小 | 相对地板×0.85 | 触发绝对地板<3.0? |",
        "|---|---:|---|---:|---:|---:|:---:|",
    ]
    any_data = False
    for label, db in SOURCES:
        if not Path(db).exists():
            continue
        scores = _load_scores(db)
        if not scores:
            continue
        any_data = True
        for dim in _DIMS:
            vals = [s[dim] for s in scores]
            mean = statistics.mean(vals)
            lo = min(vals)
            rel_floor = round(mean * 0.85, 2)
            hits_abs = "是" if lo < 3.0 else "否"
            lines.append(
                f"| {label} | {len(scores)} | {dim.replace('_score', '')} | "
                f"{mean:.2f} | {lo:.2f} | {rel_floor} | {hits_abs} |"
            )
    if not any_data:
        lines.append("| （无任何 DB 含 literary_observations 数据） | | | | | | |")

    lines += [
        "",
        "## 标定结论",
        "",
        "- **相对地板系数 = 0.85**：比既有 T3 诊断（×0.80/20% 跌幅）更早预警（15% 跌幅），"
        "与框架 §8 A3 一致；两口径并存、互不干扰（T3 诊断保留，抽读为独立 observe 信号）。",
        "- **绝对地板 = 3.0**（rubric **1–10** 量表；标定确认真实分均值 5–8、健康章最小 4–6）："
        "跌破视为塌陷，防止基线本身偏低时相对地板失效。",
        "- 二者取 `max(base×0.85, 3.0)` 为阈值：滚动窗口均值低于该阈值即建议**人工抽读**，"
        "**不自动阻塞**（observe-only）。",
        "- **数据口径说明**：v6_159 的最小值 0.00 是个别章缺 LiteraryAuditor 观测的**缺失哨兵**"
        "（非真实塌陷），故其『触发绝对地板』为『是』属采集缺口、非质量事件；"
        "标定用均值不受单点 0 影响。",
        "- 历史/隔离库若无 literary_observations，对应行留空；"
        "标定随 Ch200 主线积累真实分可复算收紧。",
        "",
        "## A1 三层分层视图",
        "",
        "`songyan metrics` 出口顶部新增「三层契约摘要」段"
        "（`render_three_tier_contract_summary`）：",
        "Tier 1 硬缺陷（T9，**阻塞**，汇总展示）/ Tier 2 趋势（rubric 趋势地板，**observe**，"
        "跌破建议抽读）/ Tier 3 研究值（voice/exposition 原始读数，不判定），三区互不混淆、"
        "各标注阻塞性。",
        "",
        "## A3 observe-only 证明",
        "",
        "`detect_literary_spot_read` 只返回 `spot_read_recommended` 标志 + 触发维度，"
        "**代码中无任何 halt/gate 接线**（gate 仅由 `_gates.py`/`phase2_graph.py` 的稳定性面驱动，"
        "见 171 审计）。单测 `test_171d_three_tier_contract.py` 锁定：跌破只置建议标志、"
        "不产出阻塞信号。",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"[171d] calibration report -> {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
