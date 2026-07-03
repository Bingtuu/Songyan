"""Task 159 Layer 2 冒烟测试：复现脚本 + N/D/S/R/V 汇总渲染 + 基线对比 + T5 复核.

不调用真实 LLM；只验证脚本常量隔离、纯逻辑函数（基线对比 / N/D/S/R/V 汇总 / T5 复核）
与报告拼装不出错。真正的验收由 Layer 3 的 150 章实跑背书。
"""

from __future__ import annotations

import scripts.run_159_ch1_ch150 as r159
from songyan.evals.v6_acceptance import ThresholdResult, V6AcceptanceResult


def _tr(key: str, passed: bool | None, measured: object = 0) -> ThresholdResult:
    return ThresholdResult(
        key=key,
        passed=passed,
        measured=measured,
        threshold="-",
        sufficient=passed is not None,
        detail=f"{key} synthetic",
    )


def _result(states: dict[str, bool | None]) -> V6AcceptanceResult:
    results = [_tr(k, v) for k, v in states.items()]
    sufficient = [r for r in results if r.sufficient]
    return V6AcceptanceResult(
        project_id="proj-159",
        chapter_start=1,
        chapter_end=150,
        results=results,
        all_passed=all(r.passed is True for r in sufficient),
        undecided=[r.key for r in results if r.passed is None],
    )


def _all_pass_states() -> dict[str, bool | None]:
    return {
        "T1": True,
        "T2": True,
        "T6a": True,
        "T6b": True,
        "T6c": True,
        "T3/T8": True,
        "T4": True,
        "T5": True,
    }


class TestConstantsIsolation:
    def test_default_range_is_1_to_150(self) -> None:
        assert r159.START_CHAPTER == 1
        assert r159.END_CHAPTER == 150

    def test_paths_use_task159_prefix(self) -> None:
        assert "task159_ch1_ch150" in str(r159.DB_PATH)
        assert "task159_ch1_ch150" in str(r159.METRICS_PATH)
        assert "task159_project" in str(r159.PROJECT_FILE)
        assert "task-159" in str(r159.REPORT_PATH)

    def test_does_not_touch_157_158_artifacts(self) -> None:
        for path in (r159.DB_PATH, r159.METRICS_PATH, r159.PROJECT_FILE, r159.REPORT_PATH):
            s = str(path)
            assert "task157" not in s
            assert "task158" not in s
            assert "task-157" not in s
            assert "task-158" not in s

    def test_reuses_harness_not_fork(self) -> None:
        # 判据必须来自 songyan.evals.v6_acceptance，不 fork
        assert r159.evaluate_v6_acceptance.__module__ == "songyan.evals.v6_acceptance"
        assert (
            r159.render_v6_acceptance_section.__module__
            == "songyan.evals.v6_acceptance"
        )

    def test_reuses_158_builders(self) -> None:
        assert r159.base._project_setting is not None
        assert r159.base._build_outline is not None

    def test_gate_and_failure_defaults_match_158(self) -> None:
        # 与 158 同口径：enforce + isolate
        assert r159.GATE_MODE == "enforce"
        assert r159.ON_FAILURE == "isolate"

    def test_r_evidence_references_158r(self) -> None:
        assert r159.R_EVIDENCE_RUN_ID == "run-82bd2e07"
        assert "task-158r" in r159.R_EVIDENCE_REPORT


class TestMetricsJsonlAppend:
    def test_append_metric_creates_jsonl(self, tmp_path, monkeypatch) -> None:
        import json

        metrics_path = tmp_path / "m.jsonl"
        monkeypatch.setattr(r159, "METRICS_PATH", metrics_path)
        r159._append_metric({"chapter": 1, "accepted": True})
        r159._append_metric({"chapter": 2, "accepted": False})
        lines = metrics_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["chapter"] == 1
        assert json.loads(lines[1])["accepted"] is False


class TestBaselineComparison:
    def test_all_good_not_worse(self) -> None:
        cmp = r159.compare_to_baseline(
            completed_count=150,
            target_count=150,
            orphan_slope=2.0,
            p1_breach_chapters=[],
            t3_passed=True,
            t4_passed=True,
            t5_passed=True,
        )
        assert cmp.not_worse_than_baseline is True
        assert cmp.orphan_slope_ok is True
        assert cmp.p1_critical_zero is True

    def test_orphan_slope_above_baseline_is_worse(self) -> None:
        cmp = r159.compare_to_baseline(
            completed_count=150,
            target_count=150,
            orphan_slope=3.5,  # > 3.14 阈值
            p1_breach_chapters=[],
            t3_passed=True,
            t4_passed=True,
            t5_passed=True,
        )
        assert cmp.orphan_slope_ok is False
        assert cmp.not_worse_than_baseline is False

    def test_orphan_slope_just_below_threshold_ok(self) -> None:
        cmp = r159.compare_to_baseline(
            completed_count=150,
            target_count=150,
            orphan_slope=3.14,
            p1_breach_chapters=[],
            t3_passed=True,
            t4_passed=True,
            t5_passed=True,
        )
        assert cmp.orphan_slope_ok is True
        assert cmp.not_worse_than_baseline is True

    def test_p1_breach_is_worse(self) -> None:
        cmp = r159.compare_to_baseline(
            completed_count=150,
            target_count=150,
            orphan_slope=2.0,
            p1_breach_chapters=[42],
            t3_passed=True,
            t4_passed=True,
            t5_passed=True,
        )
        assert cmp.p1_critical_zero is False
        assert cmp.not_worse_than_baseline is False

    def test_incomplete_is_worse(self) -> None:
        cmp = r159.compare_to_baseline(
            completed_count=148,
            target_count=150,
            orphan_slope=2.0,
            p1_breach_chapters=[],
            t3_passed=True,
            t4_passed=True,
            t5_passed=True,
        )
        assert cmp.completion_ok is False
        assert cmp.not_worse_than_baseline is False

    def test_t3_fail_is_worse(self) -> None:
        cmp = r159.compare_to_baseline(
            completed_count=150,
            target_count=150,
            orphan_slope=2.0,
            p1_breach_chapters=[],
            t3_passed=False,
            t4_passed=True,
            t5_passed=True,
        )
        assert cmp.t3_not_red is False
        assert cmp.not_worse_than_baseline is False

    def test_none_states_do_not_block(self) -> None:
        # 待判定（None）不算劣于基线，但也不误判为红
        cmp = r159.compare_to_baseline(
            completed_count=150,
            target_count=150,
            orphan_slope=None,
            p1_breach_chapters=[],
            t3_passed=None,
            t4_passed=None,
            t5_passed=None,
        )
        assert cmp.not_worse_than_baseline is True
        assert cmp.orphan_slope_ok is None
        assert cmp.t3_not_red is None


class TestNDSRVAssembly:
    def test_all_pass_verdict(self) -> None:
        rows = r159.derive_ndsrv(
            _result(_all_pass_states()),
            outline_present=True,
            d_metrics_present=True,
            r_passed=True,
            r_evidence="run-82bd2e07",
        )
        verdict, blockers = r159.summarize_ndsrv(rows)
        assert not blockers
        assert "V6 通过" in verdict
        assert all(r.state is True for r in rows)

    def test_fail_produces_blockers(self) -> None:
        states = _all_pass_states()
        states["T6b"] = False  # S 项破线
        rows = r159.derive_ndsrv(
            _result(states),
            outline_present=True,
            d_metrics_present=True,
            r_passed=True,
            r_evidence="run-82bd2e07",
        )
        verdict, blockers = r159.summarize_ndsrv(rows)
        assert "条件不通过" in verdict
        assert any("S" in b for b in blockers)

    def test_undecided_produces_conditional_pass(self) -> None:
        states = _all_pass_states()
        states["T5"] = None  # V 项待判定
        rows = r159.derive_ndsrv(
            _result(states),
            outline_present=True,
            d_metrics_present=True,
            r_passed=True,
            r_evidence="run-82bd2e07",
        )
        verdict, blockers = r159.summarize_ndsrv(rows)
        assert not blockers
        assert "条件通过" in verdict

    def test_missing_outline_fails_n(self) -> None:
        rows = r159.derive_ndsrv(
            _result(_all_pass_states()),
            outline_present=False,
            d_metrics_present=True,
            r_passed=True,
            r_evidence="run-82bd2e07",
        )
        n_row = next(r for r in rows if r.dim == "N")
        assert n_row.state is False

    def test_missing_d_metrics_fails_d(self) -> None:
        rows = r159.derive_ndsrv(
            _result(_all_pass_states()),
            outline_present=True,
            d_metrics_present=False,
            r_passed=True,
            r_evidence="run-82bd2e07",
        )
        d_row = next(r for r in rows if r.dim == "D")
        assert d_row.state is False

    def test_r_fail_fails_r(self) -> None:
        rows = r159.derive_ndsrv(
            _result(_all_pass_states()),
            outline_present=True,
            d_metrics_present=True,
            r_passed=False,
            r_evidence="none",
        )
        r_row = next(r for r in rows if r.dim == "R")
        assert r_row.state is False

    def test_render_section_contains_all_dims(self) -> None:
        rows = r159.derive_ndsrv(
            _result(_all_pass_states()),
            outline_present=True,
            d_metrics_present=True,
            r_passed=True,
            r_evidence="run-82bd2e07",
        )
        baseline = r159.compare_to_baseline(
            completed_count=150,
            target_count=150,
            orphan_slope=2.0,
            p1_breach_chapters=[],
            t3_passed=True,
            t4_passed=True,
            t5_passed=True,
        )
        text = r159.render_ndsrv_section(rows, baseline)
        for dim in ("N 骨架", "D 度量", "S 收敛", "R 可靠", "V 验证"):
            assert dim in text
        assert "不劣于基线" in text
        assert "V6 通过" in text


class TestT5Review:
    def _samples(self, scans: list[float], db_mb: float = 84.0) -> list[dict]:
        return [
            {
                "chapter_number": (i + 1) * 10,
                "db_size_bytes": int(db_mb * 1024 * 1024),
                "wal_size_bytes": 0,
                "page_count": 1,
                "page_size": 4096,
                "scan_latency_ms": s,
            }
            for i, s in enumerate(scans)
        ]

    def test_size_within_redline(self) -> None:
        a = r159.analyze_t5_samples(self._samples([80.0] * 15, db_mb=84.78))
        assert a.size_ok is True
        assert a.max_db_mb < 300.0

    def test_size_breach_flagged(self) -> None:
        a = r159.analyze_t5_samples(self._samples([80.0] * 15, db_mb=350.0))
        assert a.size_ok is False

    def test_robust_window_reduces_false_breach(self) -> None:
        # 158 破线场景：前 10 样本均值小，中段有抖动尖峰
        scans = [80, 82, 85, 90, 172, 88, 157, 91, 84, 86, 89, 90, 92, 88, 87]
        a = r159.analyze_t5_samples(
            self._samples([float(x) for x in scans]),
            old_factor=1.5,
            robust_factor=2.0,
        )
        # 现口径（前10均值×1.5）应捕到抖动尖峰破线
        assert a.old_breach_chapters
        # 候选稳健口径（中位数×2.0）应显著减少假破线
        assert len(a.robust_breach_chapters) < len(a.old_breach_chapters)

    def test_render_section_has_freeze_placeholder(self) -> None:
        a = r159.analyze_t5_samples(self._samples([80.0] * 15))
        text = r159.render_t5_review_section(a)
        assert "T5 阈值复核与冻结" in text
        assert "冻结决定" in text
        assert "现口径" in text
        assert "候选稳健口径" in text

    def test_median_helper(self) -> None:
        assert r159._median([]) == 0.0
        assert r159._median([5.0]) == 5.0
        assert r159._median([1.0, 3.0]) == 2.0
        assert r159._median([1.0, 2.0, 3.0]) == 2.0
