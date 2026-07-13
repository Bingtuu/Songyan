"""Task 170: 自适应门禁小窗口验证 + T12 标定的自动化测试.

覆盖:
- 良性波动窗口不 halt(A/D)。
- 真实退化窗口 halt_candidate(observe)/halt(enforce)(B)。
- missing/insufficient 不计入 hard fail 分母(排除窗口)。
- T12 统计分母/分子正确。
- 报告包含过程监测/数据采集/可读性文学性抽检段。
- 脚本可重复运行(两次结果一致)。
- 不触碰 Ch200(窗口区间与断言)。
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from songyan.evals.adaptive_halt import evaluate_adaptive_halt
from songyan.models import (
    AdaptiveGateDataPlaneReport,
    AdaptiveGateSignalWindow,
    AdaptiveHaltDecision,
    AdaptiveHaltPolicy,
)

pytestmark = pytest.mark.performance

_SCRIPT_PATH = Path(__file__).parent.parent / "scripts" / "run_170_adaptive_gate_validation.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location("run_170_validation", _SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["run_170_validation"] = module
    spec.loader.exec_module(module)
    return module


mod = _load_script_module()


def _status_counts(present: bool) -> dict[str, dict[str, int]]:
    domains = ("continuity", "quality", "literary", "cleanliness", "context", "narrative")
    return {
        domain: {
            "present": 1 if present else 0,
            "missing": 0 if present else 1,
            "insufficient": 0,
            "observation": 0,
        }
        for domain in domains
    }


class TestScenarioBuilders:
    def test_all_scenarios_span_16_to_20_not_ch200(self) -> None:
        for key in ("benign", "degradation", "control", "single-signal"):
            scenario = mod.SCENARIO_BUILDERS[key]()
            chapters = [sig.chapter for sig in scenario.signals]
            assert chapters == [16, 17, 18, 19, 20]
            assert max(chapters) < 200  # 不触碰 Ch200

    def test_benign_expected_class(self) -> None:
        assert mod.SCENARIO_BUILDERS["benign"]().expected_class == "benign"
        assert mod.SCENARIO_BUILDERS["single-signal"]().expected_class == "benign"

    def test_degradation_expected_class(self) -> None:
        assert mod.SCENARIO_BUILDERS["degradation"]().expected_class == "degradation"


class TestPureDecisionOnScenarioWindows:
    """把场景信号聚合为窗口后跑纯判定引擎，验证语义(不依赖 DB)。"""

    def _window_from_scenario(self, scenario) -> AdaptiveGateSignalWindow:
        signals = scenario.signals
        healths = [s.health_score for s in signals if s.health_score is not None]
        p1s = [float(s.p1_count) for s in signals]
        orphans = [float(s.orphan_total) for s in signals]
        xs = [s.chapter for s in signals]
        slope = mod_linear_slope(xs, orphans)
        degraded = sum(1 for s in signals if s.degraded_accept)
        missed = sum(s.schedule_missed_count for s in signals)
        satisfied = sum(s.schedule_satisfied_count for s in signals)
        outcome = missed + satisfied
        emergencies = sum(1 for s in signals if s.context_emergency)
        return AdaptiveGateSignalWindow(
            start_chapter=16,
            end_chapter=20,
            sample_count=5,
            window_size=5,
            source_status_counts=_status_counts(present=True),
            health_min=min(healths) if healths else None,
            p1_median=_median(p1s),
            orphan_slope=slope,
            orphan_delta=int(orphans[-1] - orphans[0]) if len(orphans) >= 2 else None,
            degraded_ratio=degraded / len(signals) if signals else None,
            schedule_missed_rate=(missed / outcome) if outcome else None,
            context_emergency_ratio=(emergencies / len(signals)) if signals else None,
        )

    def test_benign_does_not_halt(self) -> None:
        scenario = mod.SCENARIO_BUILDERS["benign"]()
        window = self._window_from_scenario(scenario)
        report = AdaptiveGateDataPlaneReport(
            project_id="p",
            chapter_start=16,
            chapter_end=20,
            snapshot_count=5,
            source_status_counts=_status_counts(present=True),
            windows=[window],
        )
        decision = evaluate_adaptive_halt(report, AdaptiveHaltPolicy(warmup_chapters=10))
        assert decision.status in ("continue", "warn")

    def test_degradation_is_halt_candidate_observe(self) -> None:
        scenario = mod.SCENARIO_BUILDERS["degradation"]()
        window = self._window_from_scenario(scenario)
        report = AdaptiveGateDataPlaneReport(
            project_id="p",
            chapter_start=16,
            chapter_end=20,
            snapshot_count=5,
            source_status_counts=_status_counts(present=True),
            windows=[window],
        )
        observe = evaluate_adaptive_halt(
            report, AdaptiveHaltPolicy(warmup_chapters=10, mode="observe")
        )
        enforce = evaluate_adaptive_halt(
            report, AdaptiveHaltPolicy(warmup_chapters=10, mode="enforce")
        )
        assert observe.status == "halt_candidate"
        assert enforce.status == "halt"


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    from statistics import median

    return float(median(values))


def mod_linear_slope(xs: list[int], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 2:
        return None
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    denom = sum((x - mean_x) ** 2 for x in xs)
    if denom == 0:
        return None
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=False))
    return num / denom


class TestClassifyDecision:
    def _decision(self, status: str) -> AdaptiveHaltDecision:
        return AdaptiveHaltDecision(
            decision_id="d",
            project_id="p",
            chapter_start=16,
            chapter_end=20,
            evaluated_at_chapter=20,
            status=status,  # type: ignore[arg-type]
        )

    def test_benign_halt_candidate_is_false_positive(self) -> None:
        assert (
            mod._classify_decision("benign", self._decision("halt_candidate"), excluded=False)
            == "false_positive"
        )

    def test_benign_warn_is_correct_warn(self) -> None:
        assert (
            mod._classify_decision("benign", self._decision("warn"), excluded=False)
            == "correct_warn"
        )

    def test_benign_continue_is_correct_negative(self) -> None:
        assert (
            mod._classify_decision("benign", self._decision("continue"), excluded=False)
            == "correct_negative"
        )

    def test_degradation_halt_is_correct_positive(self) -> None:
        assert (
            mod._classify_decision("degradation", self._decision("halt"), excluded=False)
            == "correct_positive"
        )

    def test_degradation_continue_is_false_negative(self) -> None:
        assert (
            mod._classify_decision("degradation", self._decision("continue"), excluded=False)
            == "false_negative"
        )

    def test_excluded_short_circuits(self) -> None:
        assert (
            mod._classify_decision("degradation", self._decision("halt"), excluded=True)
            == "excluded"
        )


class TestComputeT12:
    def _result(self, expected: str, status: str, *, excluded: bool = False):
        scenario = mod.Scenario(
            scenario_id="x",
            label="x",
            expected_class=expected,  # type: ignore[arg-type]
            description="",
            signals=[],
        )
        decision = AdaptiveHaltDecision(
            decision_id="d",
            project_id="p",
            chapter_start=16,
            chapter_end=20,
            evaluated_at_chapter=20,
            status=status,  # type: ignore[arg-type]
        )
        return mod.ScenarioResult(
            scenario=scenario,
            seeded=5,
            observe_decision=decision,
            enforce_decision=decision,
            old_gate={
                "triggered_any": False,
                "trigger_chapters": [],
                "single_point_trigger": False,
                "reasons": [],
            },
            excluded=excluded,
            observe_class=mod._classify_decision(expected, decision, excluded=excluded),
            enforce_class=mod._classify_decision(expected, decision, excluded=excluded),
        )

    def test_clean_pass_freezes(self) -> None:
        results = [
            self._result("benign", "continue"),
            self._result("benign", "warn"),
            self._result("degradation", "halt_candidate"),
        ]
        stats = mod._compute_t12(results)
        assert stats.false_positive_count == 0
        assert stats.false_negative_count == 0
        assert stats.benign_window_count == 2
        assert stats.degraded_window_count == 1
        assert stats.false_positive_rate == 0.0
        assert stats.degraded_catch_rate == 1.0
        assert stats.frozen is True

    def test_false_positive_blocks_freeze(self) -> None:
        results = [
            self._result("benign", "halt_candidate"),  # 误报
            self._result("degradation", "halt"),
        ]
        stats = mod._compute_t12(results)
        assert stats.false_positive_count == 1
        assert stats.false_positive_rate == 1.0
        assert stats.frozen is False

    def test_false_negative_blocks_freeze(self) -> None:
        results = [
            self._result("benign", "continue"),
            self._result("degradation", "continue"),  # 漏拦
        ]
        stats = mod._compute_t12(results)
        assert stats.false_negative_count == 1
        assert stats.degraded_catch_rate == 0.0
        assert stats.frozen is False

    def test_excluded_not_in_denominator(self) -> None:
        results = [
            self._result("benign", "continue"),
            self._result("degradation", "halt_candidate"),
            self._result("degradation", "halt", excluded=True),  # 排除
        ]
        stats = mod._compute_t12(results)
        assert stats.excluded_window_count == 1
        assert stats.degraded_window_count == 1  # 排除项不进分母
        assert stats.frozen is True


class TestEndToEnd:
    async def test_full_run_produces_report_and_jsonl(self, tmp_path: Path) -> None:
        from songyan.config import settings

        original_url = settings.database_url
        original_mode = settings.checkpointer_mode
        try:
            db = tmp_path / "t170.db"
            jsonl = tmp_path / "metrics.jsonl"
            report = tmp_path / "report.md"

            rc = await mod._async_main("all", str(db), str(jsonl), str(report))
            assert rc == 0
            assert jsonl.exists()
            assert report.exists()

            report_text = report.read_text(encoding="utf-8")
            # 报告包含过程监测/数据采集/可读性文学性抽检段
            assert "## 4. 过程监测表" in report_text
            assert "## 5. 数据采集完整性" in report_text
            assert "## 8. 可读性 / 文学性抽检" in report_text
            assert "## 7. T12 误报 / 漏拦统计" in report_text
            # 不触碰 Ch200
            assert "是否触碰 Ch200 | 否" in report_text
        finally:
            settings.database_url = original_url
            settings.checkpointer_mode = original_mode

    async def test_repeatable(self, tmp_path: Path) -> None:
        from songyan.config import settings

        original_url = settings.database_url
        original_mode = settings.checkpointer_mode
        try:
            db = tmp_path / "t170.db"
            jsonl1 = tmp_path / "m1.jsonl"
            jsonl2 = tmp_path / "m2.jsonl"
            report = tmp_path / "r.md"

            await mod._async_main("all", str(db), str(jsonl1), str(report))
            await mod._async_main("all", str(db), str(jsonl2), str(report))

            # 逐行比较去掉 timestamp 后应一致(可重复运行)
            def _strip_ts(path: Path) -> list[str]:
                import json

                out = []
                for line in path.read_text(encoding="utf-8").splitlines():
                    obj = json.loads(line)
                    obj.pop("timestamp", None)
                    out.append(json.dumps(obj, ensure_ascii=False, sort_keys=True))
                return out

            assert _strip_ts(jsonl1) == _strip_ts(jsonl2)
        finally:
            settings.database_url = original_url
            settings.checkpointer_mode = original_mode
