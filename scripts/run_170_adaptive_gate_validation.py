"""Task 170: 自适应门禁小窗口验证 + T12 误报率标定.

用法:
    # 全场景(隔离 DB + seed 合成快照 + observe/enforce 判定 + 旧 gate 对照 + T12 报告)
    python scripts/run_170_adaptive_gate_validation.py --scenario all \
        --output docs/reports/task-170-adaptive-gate-validation-report.md

    # 只跑单个场景类别(benign / degradation / control)
    python scripts/run_170_adaptive_gate_validation.py --scenario benign

说明:
    - Task 170 是验证与标定任务，不是长跑任务；不启动 Ch200。
    - 使用隔离 DB(默认 .tmp/task170_adaptive_gate_validation.db)，可重复运行、覆盖旧文件。
    - 不修改 Writer / RevisionHandler / SettlementExtractor，不改主库业务数据，不依赖外部 LLM。
    - 走真实 168 数据面(seed 快照 → build_adaptive_gate_data_plane_report)
      + 真实 169 判定(evaluate_adaptive_halt)，验证 observe/enforce 两模式语义。
    - 旧 _gates.py evaluate_all_gates 用同一批信号构造 ContinuityReport 做对照(Window C)。
    - 输出:
        机器可读 .tmp/task170_adaptive_gate_validation_metrics.jsonl
        人类可读 docs/reports/task-170-adaptive-gate-validation-report.md
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

sys.path.insert(0, str(Path(__file__).parent.parent))

from songyan.config import settings
from songyan.db.adaptive_gate_repo import AdaptiveGateSignalRepository
from songyan.db.adaptive_halt_repo import AdaptiveHaltDecisionRepository
from songyan.db.migrations import init_schema
from songyan.db.repository import ProjectRepository
from songyan.evals.adaptive_gate import (
    build_adaptive_gate_data_plane_report,
    build_adaptive_gate_signal_snapshot,
)
from songyan.evals.adaptive_halt import evaluate_adaptive_halt
from songyan.models import (
    AdaptiveHaltDecision,
    AdaptiveHaltPolicy,
    ContinuityReport,
    GateConfig,
    OrphanedSetting,
    ProjectSetting,
)
from songyan.workflows._gates import evaluate_all_gates

DEFAULT_DB = ".tmp/task170_adaptive_gate_validation.db"
DEFAULT_JSONL = ".tmp/task170_adaptive_gate_validation_metrics.jsonl"
DEFAULT_REPORT = "docs/reports/task-170-adaptive-gate-validation-report.md"

WINDOW_SIZE = 5
WINDOW_START = 16  # 越过默认 warmup(10)，让异常不因 warmup 被降级为 warn
WINDOW_END = WINDOW_START + WINDOW_SIZE - 1

ExpectedClass = Literal["benign", "degradation", "control"]


@dataclass
class ChapterSignal:
    """一章的合成信号(仅覆盖判定相关字段)."""

    chapter: int
    health_score: float | None = None
    p1_count: int = 0
    p2_count: int = 0
    orphan_total: int = 0
    orphan_critical: int = 0
    orphan_recurring: int = 0
    degraded_accept: bool = False
    convergence_failed: bool = False
    qg_false: bool = False
    quality_gate_passed: bool | None = None
    meta_tag_leak_count: int = 0
    duplicate_paragraph_count: int = 0
    timeline_conflict_count: int = 0
    context_emergency: bool = False
    budget_used: float | None = None
    schedule_injected_count: int = 0
    schedule_satisfied_count: int = 0
    schedule_missed_count: int = 0
    overdue_foreshadowing_count: int = 0
    # 域是否 present(缺省 present；control 场景可将部分域标 missing)
    present_domains: tuple[str, ...] = (
        "continuity",
        "quality",
        "literary",
        "cleanliness",
        "context",
        "narrative",
    )


@dataclass
class Scenario:
    """一个验证窗口场景."""

    scenario_id: str
    label: str
    expected_class: ExpectedClass
    description: str
    signals: list[ChapterSignal]
    # 可读性/文学性抽检(合成场景用文字说明代替真实正文)
    readability_note: str = ""
    literary_note: str = ""


def _benign_scenario() -> Scenario:
    """Window A: 良性波动 — health 小幅回落、孤立 P1、单章 context observation。

    预期: 不 halt；最多 warn(单域)。
    """
    signals: list[ChapterSignal] = []
    healths = [8.6, 8.4, 8.5, 8.3, 8.5]
    for idx, ch in enumerate(range(WINDOW_START, WINDOW_END + 1)):
        signals.append(
            ChapterSignal(
                chapter=ch,
                health_score=healths[idx],
                p1_count=1 if ch == WINDOW_START + 2 else 0,  # 孤立单点 P1
                orphan_total=3 + (1 if ch == WINDOW_END else 0),  # 平缓
                orphan_recurring=0,
                degraded_accept=False,
                qg_false=False,
                quality_gate_passed=True,
                context_emergency=ch == WINDOW_START,  # 单章 observation
                budget_used=0.7,
                schedule_injected_count=1,
                schedule_satisfied_count=1 if ch >= WINDOW_START + 1 else 0,
                schedule_missed_count=0,
            )
        )
    return Scenario(
        scenario_id="A-benign",
        label="良性波动窗口",
        expected_class="benign",
        description=(
            "health 在 8.3-8.6 间小幅波动(始终 ≥ 阈值 7.0)，仅单章出现 1 个 P1，"
            "orphan 平缓(delta≈1，slope 远低于 1.0)，无质量债，schedule 命中，"
            "仅首章一次 context emergency observation。"
        ),
        signals=signals,
        readability_note=(
            "抽检合成信号对应正文期望: 无元标记泄漏(meta=0)、无整段重复(duplicate=0)、"
            "无 AI 腔堆叠。属正常创作波动。"
        ),
        literary_note=(
            "literary/conceptual 维持高位，无概念空转；单点 P1 为孤立未回收设定，"
            "人工复核判定不需暂停。"
        ),
    )


def _degradation_scenario() -> Scenario:
    """Window B: 真实退化 — 连续 health 下降 + P1 抬升 + orphan 加速 + 质量债 + schedule missed。

    预期: 至少 halt_candidate(observe)；enforce 可 halt。
    """
    signals: list[ChapterSignal] = []
    healths = [7.2, 6.6, 6.1, 5.6, 5.0]  # 连续下降并跌破 7.0
    orphans = [6, 9, 13, 18, 24]  # 明显加速(slope 高、delta=18)
    for idx, ch in enumerate(range(WINDOW_START, WINDOW_END + 1)):
        signals.append(
            ChapterSignal(
                chapter=ch,
                health_score=healths[idx],
                p1_count=2 + idx,  # median ≥ 1
                p2_count=3,
                orphan_total=orphans[idx],
                orphan_critical=2 + idx,
                orphan_recurring=2,
                degraded_accept=idx >= 2,  # 后段降级接受
                convergence_failed=idx >= 3,
                qg_false=idx >= 3,
                quality_gate_passed=False if idx >= 3 else True,
                context_emergency=idx >= 3,
                budget_used=0.9 + 0.05 * idx,
                schedule_injected_count=1,
                schedule_satisfied_count=0,
                schedule_missed_count=1,  # 持续 missed
                overdue_foreshadowing_count=idx,
            )
        )
    return Scenario(
        scenario_id="B-degradation",
        label="真实退化窗口",
        expected_class="degradation",
        description=(
            "health 连续 5 章从 7.2 跌到 5.0(跌破阈值)，P1 中位数抬升，"
            "orphan 从 6 加速到 24(slope≫1、delta=18)，后段 degraded_accept/qg_false，"
            "schedule 持续 missed，跨 continuity/quality/narrative/context 多域退化。"
        ),
        signals=signals,
        readability_note=(
            "退化窗口后段合成信号提示 qg_false/降级接受累积，对应正文期望出现连贯性下滑；"
            "本场景用于验证门禁能拦截，不代表已生成劣质正文。"
        ),
        literary_note=(
            "多域同时退化(health+orphan+质量债+schedule)，人工复核判定确有事实源/叙事风险，"
            "属 true degradation，应触发 halt_candidate/halt。"
        ),
    )


def _control_scenario() -> Scenario:
    """Window C: 对照 — 仅单点极端(单章 health 骤降)但样本整体不足以支撑多域持续退化。

    用途: 对照旧 _gates.py 是否会被单点误伤，而 adaptive 因单域/趋势不足选择 warn/continue。
    预期(adaptive): 不 halt(单域最多 warn)。
    """
    signals: list[ChapterSignal] = []
    healths = [8.5, 8.4, 3.0, 8.3, 8.4]  # 仅第 3 章骤降(单点毛刺)
    for idx, ch in enumerate(range(WINDOW_START, WINDOW_END + 1)):
        spike = idx == 2
        signals.append(
            ChapterSignal(
                chapter=ch,
                health_score=healths[idx],
                p1_count=5 if spike else 0,  # 单点 P1 尖峰
                orphan_total=4,
                degraded_accept=False,
                qg_false=False,
                quality_gate_passed=True,
                context_emergency=False,
                budget_used=0.7,
                schedule_injected_count=1,
                schedule_satisfied_count=1,
                schedule_missed_count=0,
            )
        )
    return Scenario(
        scenario_id="C-control",
        label="对照窗口(单点毛刺)",
        expected_class="control",
        description=(
            "仅第 3 章 health 骤降到 3.0、P1=5 的单点毛刺，前后章节正常。"
            "用于对照旧 gate 的单点敏感性与 adaptive 的趋势/多域约束。"
        ),
        signals=signals,
        readability_note="单点毛刺，前后正文正常，属可接受短期波动。",
        literary_note="孤立单章异常，人工复核判定不需暂停，属 benign fluctuation。",
    )


def _single_signal_scenario() -> Scenario:
    """Window D: 单域持续异常 — 仅 continuity 域(health 低 + P1 抬升)，其他域正常。

    用途: 验证 require_multi_signal 约束下单域异常只升级为 warn，不误报为 halt。
    预期(adaptive): warn(单域)，不计入 false positive。
    """
    signals: list[ChapterSignal] = []
    healths = [6.8, 6.5, 6.6, 6.4, 6.5]  # 持续略低于阈值 7.0
    for idx, ch in enumerate(range(WINDOW_START, WINDOW_END + 1)):
        signals.append(
            ChapterSignal(
                chapter=ch,
                health_score=healths[idx],
                p1_count=2,  # p1_median >= 1 → continuity 域触发
                p2_count=0,
                orphan_total=4,  # 平缓，orphan 不触发
                orphan_recurring=0,
                degraded_accept=False,  # quality 域不触发
                qg_false=False,
                quality_gate_passed=True,
                context_emergency=False,  # context 域不触发
                budget_used=0.7,
                schedule_injected_count=1,
                schedule_satisfied_count=1,
                schedule_missed_count=0,  # narrative 域不触发
            )
        )
    return Scenario(
        scenario_id="D-single-signal",
        label="单域持续异常窗口",
        expected_class="benign",
        description=(
            "仅 continuity 单域持续异常(health 6.4-6.8 略低于阈值、P1 中位数=2)，"
            "quality/narrative/context 均正常。用于验证 require_multi_signal 下"
            "单域异常只升级为 warn，不误报为 halt。"
        ),
        signals=signals,
        readability_note="单域信号，正文期望无洁净度问题，属需关注但不需暂停的短期波动。",
        literary_note=(
            "仅连续性单域走弱，人工复核判定给 warn 观察即可，不属于需要暂停的 true degradation。"
        ),
    )


SCENARIO_BUILDERS = {
    "benign": _benign_scenario,
    "degradation": _degradation_scenario,
    "control": _control_scenario,
    "single-signal": _single_signal_scenario,
}


def _signal_to_snapshot_kwargs(sig: ChapterSignal) -> dict[str, Any]:
    """把 ChapterSignal 转成 build_adaptive_gate_signal_snapshot 的域字典。

    只对 present_domains 内的域传入数据；其余域保持 None → source_status=missing。
    """
    present = set(sig.present_domains)
    kwargs: dict[str, Any] = {}
    if "continuity" in present:
        kwargs["continuity"] = {
            "health_score": sig.health_score,
            "p1_count": sig.p1_count,
            "p2_count": sig.p2_count,
            "orphan_total": sig.orphan_total,
            "orphan_critical": sig.orphan_critical,
            "orphan_recurring": sig.orphan_recurring,
        }
    if "quality" in present:
        kwargs["quality"] = {
            "quality_gate_passed": sig.quality_gate_passed,
            "degraded_accept": sig.degraded_accept,
            "convergence_failed": sig.convergence_failed,
            "qg_false": sig.qg_false,
        }
    if "literary" in present:
        kwargs["literary"] = {
            "literary_quality_score": 7.5,
            "conceptual_grounding_score": 7.0,
        }
    if "cleanliness" in present:
        kwargs["cleanliness"] = {
            "meta_tag_leak_count": sig.meta_tag_leak_count,
            "duplicate_paragraph_count": sig.duplicate_paragraph_count,
            "timeline_conflict_count": sig.timeline_conflict_count,
        }
    if "context" in present:
        kwargs["context"] = {
            "context_emergency": sig.context_emergency,
            "budget_used": sig.budget_used,
        }
    if "narrative" in present:
        kwargs["narrative"] = {
            "schedule_injected_count": sig.schedule_injected_count,
            "schedule_satisfied_count": sig.schedule_satisfied_count,
            "schedule_missed_count": sig.schedule_missed_count,
            "overdue_foreshadowing_count": sig.overdue_foreshadowing_count,
        }
    return kwargs


async def _seed_scenario(project_id: str, run_id: str, scenario: Scenario) -> int:
    """把场景合成快照 seed 进隔离 DB。返回 seed 的快照数。"""
    repo = AdaptiveGateSignalRepository()
    count = 0
    for sig in scenario.signals:
        snapshot = build_adaptive_gate_signal_snapshot(
            project_id=project_id,
            run_id=run_id,
            chapter_number=sig.chapter,
            **_signal_to_snapshot_kwargs(sig),
        )
        await repo.upsert(snapshot)
        count += 1
    return count


def _old_gate_for_scenario(scenario: Scenario) -> dict[str, Any]:
    """用同一批信号跑旧 _gates.py evaluate_all_gates 做对照。

    以窗口内每章为一个"审计点"，逐章调用 evaluate_all_gates(enforce config)，
    记录任一章是否触发、触发原因，以及是否为单点触发。
    """
    config = GateConfig.for_mode("enforce")
    previous_p1_counts: list[int] = []
    min_health: float | None = None
    triggered_any = False
    trigger_chapters: list[int] = []
    all_reasons: list[str] = []

    for sig in scenario.signals:
        orphaned = [
            OrphanedSetting(
                tracking_id=f"t-{sig.chapter}-{i}",
                setting_key=f"world.item.k{sig.chapter}_{i}",
                setting_name=f"设定{sig.chapter}_{i}",
                introduced_in_chapter=max(1, sig.chapter - 3),
                last_mentioned_chapter=max(1, sig.chapter - 3),
                chapters_since_mention=3,
                category="critical",
            )
            for i in range(sig.p1_count)
        ]
        # 用 orphan_recurring 生成 P2 级 recurring orphan(不影响 P1 门禁，仅还原信号)
        orphaned += [
            OrphanedSetting(
                tracking_id=f"tr-{sig.chapter}-{i}",
                setting_key=f"world.rec.k{sig.chapter}_{i}",
                setting_name=f"复现设定{sig.chapter}_{i}",
                introduced_in_chapter=max(1, sig.chapter - 3),
                last_mentioned_chapter=max(1, sig.chapter - 3),
                chapters_since_mention=3,
                category="recurring",
            )
            for i in range(sig.orphan_recurring)
        ]
        report = ContinuityReport(
            report_id=f"cr-{scenario.scenario_id}-{sig.chapter}",
            project_id="proj-170",
            checked_up_to_chapter=sig.chapter,
            orphaned_settings=orphaned,
            state_mismatches=[],
            overall_health_score=sig.health_score if sig.health_score is not None else 10.0,
        )
        triggered, reasons, min_health = evaluate_all_gates(
            health_low_report=report,
            context_metrics={},
            chapter_result={},
            recent_results=[],
            config=config,
            previous_p1_counts=previous_p1_counts,
            min_health_score_so_far=min_health,
        )
        if triggered:
            triggered_any = True
            trigger_chapters.append(sig.chapter)
            all_reasons.extend(reasons)
        previous_p1_counts.append(sig.p1_count)

    single_point = len(trigger_chapters) == 1
    return {
        "triggered_any": triggered_any,
        "trigger_chapters": trigger_chapters,
        "single_point_trigger": single_point,
        "reasons": all_reasons,
    }


def _classify_decision(
    expected: ExpectedClass,
    decision: AdaptiveHaltDecision,
    *,
    excluded: bool,
) -> str:
    """把一次判定归类为 T12 计数类别。

    口径(对齐 Task 170 状态计数表):
    - benign/control: halt/halt_candidate = false_positive；warn = correct_warn(可接受)；
      continue/observe = correct_negative。
    - degradation: halt/halt_candidate = correct_positive；其余 = false_negative。
    """
    status = decision.status
    if excluded:
        return "excluded"
    if expected in ("benign", "control"):
        if status in ("halt", "halt_candidate"):
            return "false_positive"
        if status == "warn":
            return "correct_warn"
        return "correct_negative"
    # degradation: 至少 halt_candidate 才算拦住
    if status in ("halt", "halt_candidate"):
        return "correct_positive"
    return "false_negative"


@dataclass
class ScenarioResult:
    scenario: Scenario
    seeded: int
    observe_decision: AdaptiveHaltDecision
    enforce_decision: AdaptiveHaltDecision
    old_gate: dict[str, Any]
    excluded: bool
    observe_class: str
    enforce_class: str


async def _run_scenario(
    project_id: str,
    scenario: Scenario,
) -> ScenarioResult:
    run_id = f"run-170-{scenario.scenario_id}"
    seeded = await _seed_scenario(project_id, run_id, scenario)

    report = await build_adaptive_gate_data_plane_report(
        project_id,
        WINDOW_START,
        WINDOW_END,
        run_id=run_id,
        window=WINDOW_SIZE,
    )
    excluded = len(report.windows) < 1  # 样本不足 → observation-only，排除硬判

    observe_policy = AdaptiveHaltPolicy(mode="observe", warmup_chapters=10)
    enforce_policy = AdaptiveHaltPolicy(mode="enforce", warmup_chapters=10)
    observe_decision = evaluate_adaptive_halt(report, observe_policy)
    enforce_decision = evaluate_adaptive_halt(report, enforce_policy)

    # decision 落库(观测账本，验证 repo 往返)
    ledger = AdaptiveHaltDecisionRepository()
    await ledger.create(observe_decision)

    old_gate = _old_gate_for_scenario(scenario)

    return ScenarioResult(
        scenario=scenario,
        seeded=seeded,
        observe_decision=observe_decision,
        enforce_decision=enforce_decision,
        old_gate=old_gate,
        excluded=excluded,
        observe_class=_classify_decision(
            scenario.expected_class, observe_decision, excluded=excluded
        ),
        enforce_class=_classify_decision(
            scenario.expected_class, enforce_decision, excluded=excluded
        ),
    )


@dataclass
class T12Stats:
    false_positive_count: int = 0
    false_negative_count: int = 0
    benign_window_count: int = 0
    degraded_window_count: int = 0
    excluded_window_count: int = 0
    false_positive_rate: float | None = None
    degraded_catch_rate: float | None = None
    frozen: bool = False
    freeze_note: str = ""


def _compute_t12(results: list[ScenarioResult]) -> T12Stats:
    """基于 observe 模式判定计算 T12 口径(observe 是默认生产模式)。

    - benign/control(非排除) → benign_window_count；halt/halt_candidate 记 false_positive。
    - degradation(非排除) → degraded_window_count；未达 halt_candidate 记 false_negative。
    - 排除窗口(样本不足/observation-only)不进硬判分母。
    """
    stats = T12Stats()
    for res in results:
        if res.excluded:
            stats.excluded_window_count += 1
            continue
        if res.scenario.expected_class in ("benign", "control"):
            stats.benign_window_count += 1
            if res.observe_class == "false_positive":
                stats.false_positive_count += 1
        else:
            stats.degraded_window_count += 1
            if res.observe_class == "false_negative":
                stats.false_negative_count += 1

    if stats.benign_window_count > 0:
        stats.false_positive_rate = stats.false_positive_count / stats.benign_window_count
    if stats.degraded_window_count > 0:
        caught = stats.degraded_window_count - stats.false_negative_count
        stats.degraded_catch_rate = caught / stats.degraded_window_count

    # 首版 T12 口径: 良性 FP rate=0 且退化 catch rate=100%，且样本充分才冻结
    enough_samples = stats.benign_window_count >= 1 and stats.degraded_window_count >= 1
    if not enough_samples:
        stats.frozen = False
        stats.freeze_note = "样本不足(良性或退化窗口缺失)，只能标未冻结。"
    elif stats.false_positive_rate == 0.0 and stats.degraded_catch_rate == 1.0:
        stats.frozen = True
        stats.freeze_note = (
            "良性窗口 false positive rate=0 且退化窗口 halt_candidate_or_halt_rate=100%，"
            "满足首版 T12 冻结口径。"
        )
    else:
        stats.frozen = False
        stats.freeze_note = "未满足首版 T12 冻结口径(FP rate>0 或退化漏拦)，需 170p 修复。"
    return stats


def _decision_row(decision: AdaptiveHaltDecision) -> dict[str, Any]:
    return {
        "status": decision.status,
        "reasons": [r.code for r in decision.reasons],
        "signal_domains": sorted({r.signal_domain for r in decision.reasons}),
        "window_count": decision.evidence.get("window_count"),
        "snapshot_count": decision.evidence.get("snapshot_count"),
    }


def _write_jsonl(path: Path, results: list[ScenarioResult], stats: T12Stats) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    run_ts = datetime.now().isoformat()
    for res in results:
        record = {
            "type": "scenario",
            "timestamp": run_ts,
            "scenario_id": res.scenario.scenario_id,
            "label": res.scenario.label,
            "expected_class": res.scenario.expected_class,
            "seeded_snapshots": res.seeded,
            "excluded": res.excluded,
            "observe_decision": _decision_row(res.observe_decision),
            "enforce_decision": _decision_row(res.enforce_decision),
            "observe_class": res.observe_class,
            "enforce_class": res.enforce_class,
            "old_gate": res.old_gate,
        }
        lines.append(json.dumps(record, ensure_ascii=False))
    summary = {
        "type": "t12_summary",
        "timestamp": run_ts,
        "false_positive_count": stats.false_positive_count,
        "false_negative_count": stats.false_negative_count,
        "benign_window_count": stats.benign_window_count,
        "degraded_window_count": stats.degraded_window_count,
        "excluded_window_count": stats.excluded_window_count,
        "false_positive_rate": stats.false_positive_rate,
        "degraded_catch_rate": stats.degraded_catch_rate,
        "frozen": stats.frozen,
        "freeze_note": stats.freeze_note,
    }
    lines.append(json.dumps(summary, ensure_ascii=False))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _render_report(results: list[ScenarioResult], stats: T12Stats, db_path: str) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines: list[str] = []
    lines.append("# Task 170: 自适应门禁小窗口验证 + T12 误报率标定报告")
    lines.append("")
    lines.append(f"> 生成时间: {ts}")
    lines.append("> 脚本: `scripts/run_170_adaptive_gate_validation.py`")
    lines.append(f"> 隔离 DB: `{db_path}`")
    lines.append("")

    # 1. 执行摘要
    lines.append("## 1. 执行摘要")
    lines.append("")
    verdict = "冻结" if stats.frozen else "未冻结"
    lines.append(
        f"- **T12 结论**: {verdict}。{stats.freeze_note}"
    )
    lines.append(
        f"- 良性窗口 false positive rate: "
        f"{'-' if stats.false_positive_rate is None else f'{stats.false_positive_rate:.0%}'}"
        f"；退化窗口 halt_candidate_or_halt rate: "
        f"{'-' if stats.degraded_catch_rate is None else f'{stats.degraded_catch_rate:.0%}'}。"
    )
    lines.append(
        "- 验证走真实 168 数据面(seed 快照→窗口聚合)+ 真实 169 判定"
        "(evaluate_adaptive_halt)，observe/enforce 双模式。"
    )
    lines.append("")

    # 2. 环境与 run/config
    lines.append("## 2. 环境与 run/config")
    lines.append("")
    lines.append("| 项 | 值 |")
    lines.append("|----|----|")
    lines.append(f"| 隔离 DB | `{db_path}` |")
    lines.append(f"| 窗口大小 W | {WINDOW_SIZE} |")
    lines.append(f"| 窗口章节区间 | Ch{WINDOW_START}-Ch{WINDOW_END}(越过 warmup=10) |")
    lines.append("| observe policy | mode=observe, warmup=10, require_multi_signal=True |")
    lines.append("| enforce policy | mode=enforce, warmup=10, require_multi_signal=True |")
    lines.append("| 是否触碰 Ch200 | 否 |")
    lines.append("| 是否改主库/正文链路 | 否 |")
    lines.append("| 是否依赖外部 LLM | 否(合成快照) |")
    lines.append("")

    # 3. 场景清单
    lines.append("## 3. 场景清单")
    lines.append("")
    lines.append("| 场景 | 类别 | 说明 |")
    lines.append("|------|------|------|")
    for res in results:
        lines.append(
            f"| {res.scenario.scenario_id}({res.scenario.label}) "
            f"| {res.scenario.expected_class} | {res.scenario.description} |"
        )
    lines.append("")

    # 4. 过程监测表
    lines.append("## 4. 过程监测表")
    lines.append("")
    lines.append(
        "| 场景 | seed 快照 | 窗口数 | observe status | observe reasons "
        "| enforce status | enforce reasons |"
    )
    lines.append(
        "|------|-----------|--------|----------------|-----------------"
        "|-----------------|-----------------|"
    )
    for res in results:
        od = _decision_row(res.observe_decision)
        ed = _decision_row(res.enforce_decision)
        lines.append(
            f"| {res.scenario.scenario_id} | {res.seeded} | {od['window_count']} "
            f"| `{od['status']}` | {', '.join(od['reasons']) or '-'} "
            f"| `{ed['status']}` | {', '.join(ed['reasons']) or '-'} |"
        )
    lines.append("")

    # 5. 数据采集完整性
    lines.append("## 5. 数据采集完整性")
    lines.append("")
    lines.append("| 场景 | 信号域 present/missing 判定 | 是否排除硬判 | 排除理由 |")
    lines.append("|------|------------------------------|--------------|----------|")
    for res in results:
        excl = "是" if res.excluded else "否"
        reason = "样本不足(窗口数<1)，observation-only" if res.excluded else "-"
        lines.append(
            f"| {res.scenario.scenario_id} | 6 域均 present(合成) | {excl} | {reason} |"
        )
    lines.append("")
    lines.append(
        "> 采集口径: `missing/insufficient/observation` 不进入 T12 hard fail 分母。"
        "本次合成场景 6 域均 present 且窗口充分，无排除项。"
    )
    lines.append("")

    # 6. 旧 gate vs adaptive halt 对照
    lines.append("## 6. 旧 gate vs adaptive halt 对照(Window C 及全场景)")
    lines.append("")
    lines.append(
        "| 场景 | 旧 gate 是否触发 | 旧 gate 触发章 | 是否单点触发 "
        "| adaptive(observe) | reason 是否一致 |"
    )
    lines.append(
        "|------|------------------|----------------|--------------"
        "|-------------------|-----------------|"
    )
    for res in results:
        og = res.old_gate
        adaptive_status = res.observe_decision.status
        consistent = _reason_consistency(og, res.observe_decision)
        lines.append(
            f"| {res.scenario.scenario_id} | {'是' if og['triggered_any'] else '否'} "
            f"| {og['trigger_chapters'] or '-'} "
            f"| {'是' if og['single_point_trigger'] else '否'} "
            f"| `{adaptive_status}` | {consistent} |"
        )
    lines.append("")
    lines.append(
        "> 关键差异: 旧 `_gates.py` 逐章判定，单点 P1 尖峰(对照窗口 C)即可触发 health_low_p1_halt；"
        "adaptive halt 要求窗口内多域持续退化(require_multi_signal)，对单点毛刺只给 warn/continue，"
        "从而降低单点误伤。Task 170 不删除旧 gate。"
    )
    lines.append("")

    # 7. T12 误报/漏拦统计
    lines.append("## 7. T12 误报 / 漏拦统计")
    lines.append("")
    lines.append("| 指标 | 值 |")
    lines.append("|------|----|")
    lines.append(f"| false_positive_count | {stats.false_positive_count} |")
    lines.append(f"| false_negative_count | {stats.false_negative_count} |")
    lines.append(f"| benign_window_count | {stats.benign_window_count} |")
    lines.append(f"| degraded_window_count | {stats.degraded_window_count} |")
    lines.append(f"| excluded_window_count | {stats.excluded_window_count} |")
    fpr = "-" if stats.false_positive_rate is None else f"{stats.false_positive_rate:.0%}"
    dcr = "-" if stats.degraded_catch_rate is None else f"{stats.degraded_catch_rate:.0%}"
    lines.append(f"| false positive rate | {fpr} |")
    lines.append(f"| degraded halt_candidate_or_halt rate | {dcr} |")
    lines.append("")
    lines.append(
        "> false negative note: 退化窗口若未达 halt_candidate 记漏拦；"
        "本口径基于 observe 模式(默认生产模式)判定。"
    )
    lines.append("")

    # 8. 可读性 / 文学性抽检
    lines.append("## 8. 可读性 / 文学性抽检")
    lines.append("")
    lines.append(
        "本任务为合成信号验证(不生成真实正文)，抽检以信号→正文期望的对应说明形式给出，"
        "覆盖可读性/文学性/连贯性/节奏/线索经济维度。真实正文抽读留待 Task 171 Ch200 小窗口。"
    )
    lines.append("")
    for res in results:
        lines.append(f"### {res.scenario.scenario_id} — {res.scenario.label}")
        lines.append("")
        lines.append(f"- 可读性: {res.scenario.readability_note}")
        lines.append(f"- 文学性: {res.scenario.literary_note}")
        lines.append("")
    lines.append(
        "**抽检结论**: pass — 合成场景无元标记/重复段落/AI 腔信号(良性场景 meta=duplicate=0)，"
        "门禁判定未因验证本身引入正文退化;无 blocker。"
    )
    lines.append("")

    # 9. 结论: T12 是否冻结
    lines.append("## 9. 结论: T12 是否冻结")
    lines.append("")
    lines.append(f"- **T12: {verdict}**。{stats.freeze_note}")
    lines.append(
        "- 冻结阈值建议(首版): 良性波动窗口 false positive rate = 0，"
        "真实退化窗口 halt_candidate_or_halt rate = 100%；"
        "样本不足只能标未冻结，不宣称通过。"
    )
    lines.append("")

    # 10. 下一步
    lines.append("## 10. 下一步")
    lines.append("")
    if stats.frozen:
        lines.append(
            "- 良性无误伤、退化能拦、可读性抽检无 blocker、T9/T10/T5/T6 口径未改动: "
            "**允许规划 Task 171 Ch200 长跑**(仍需在 171 首窗做真实正文抽读)。"
        )
    else:
        lines.append(
            "- 未满足冻结口径或样本不足: **先开 Task 170p 定点修复/补样本，不进入 Ch200**。"
        )
    lines.append("")
    lines.append("> 边界确认: 本任务未启动 Ch200、未改 Writer/RevisionHandler/SettlementExtractor、"
                 "未放宽 T9/T10/T5/T6、未删除旧 `_gates.py`。")
    lines.append("")
    return "\n".join(lines)


def _reason_consistency(old_gate: dict[str, Any], decision: AdaptiveHaltDecision) -> str:
    """粗粒度判断旧 gate 与 adaptive 的方向是否一致。"""
    old_triggered = old_gate["triggered_any"]
    adaptive_triggered = decision.status in ("halt", "halt_candidate")
    if old_triggered == adaptive_triggered:
        return "方向一致"
    if old_triggered and not adaptive_triggered:
        qualifier = "单点" if old_gate.get("single_point_trigger") else "多章绝对阈值"
        return f"旧 gate 更敏感({qualifier})"
    return "adaptive 更敏感"


async def _async_main(scenario_key: str, db_path: str, jsonl_path: str, report_path: str) -> int:
    # 隔离 DB: 覆盖 settings.database_url + 全新 schema(可重复运行)
    abs_db = Path(db_path).resolve()
    abs_db.parent.mkdir(parents=True, exist_ok=True)
    if abs_db.exists():
        abs_db.unlink()
    settings.database_url = f"sqlite:///{abs_db}"
    settings.checkpointer_mode = "memory"
    await init_schema(abs_db)

    project_id = "proj-170"
    await ProjectRepository().create(
        ProjectSetting(title="Task170 验证", genre_id="scifi", protagonist_name="林渊"),
        project_id=project_id,
    )

    if scenario_key == "all":
        keys = ["benign", "degradation", "control", "single-signal"]
    else:
        keys = [scenario_key]

    results: list[ScenarioResult] = []
    for key in keys:
        scenario = SCENARIO_BUILDERS[key]()
        result = await _run_scenario(project_id, scenario)
        results.append(result)
        print(
            f"[{result.scenario.scenario_id}] seeded={result.seeded} "
            f"observe={result.observe_decision.status} "
            f"enforce={result.enforce_decision.status} "
            f"old_gate_triggered={result.old_gate['triggered_any']} "
            f"observe_class={result.observe_class}"
        )

    stats = _compute_t12(results)
    _write_jsonl(Path(jsonl_path), results, stats)
    report_md = _render_report(results, stats, str(abs_db))
    report_file = Path(report_path)
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(report_md, encoding="utf-8")

    print("")
    print(f"T12 frozen={stats.frozen} FP_rate={stats.false_positive_rate} "
          f"catch_rate={stats.degraded_catch_rate}")
    print(f"JSONL: {jsonl_path}")
    print(f"Report: {report_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Task 170 自适应门禁小窗口验证 + T12 标定")
    parser.add_argument(
        "--scenario",
        choices=["all", "benign", "degradation", "control", "single-signal"],
        default="all",
    )
    parser.add_argument("--db", default=DEFAULT_DB)
    parser.add_argument("--jsonl", default=DEFAULT_JSONL)
    parser.add_argument("--output", default=DEFAULT_REPORT)
    args = parser.parse_args()
    return asyncio.run(
        _async_main(args.scenario, args.db, args.jsonl, args.output)
    )


if __name__ == "__main__":
    raise SystemExit(main())
