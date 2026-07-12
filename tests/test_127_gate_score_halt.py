"""Task 127: health_low_score_halt 复合条件单元测试.

复合条件：当前 overall_health_score 低于项目历史最低分，且同章 P1 计数
超过近期审计点 P1 计数中位数的指定倍数时才触发。
"""

from __future__ import annotations

from songyan.models import ContinuityReport, GateConfig, OrphanedSetting
from songyan.workflows._gates import check_health_low_single_gate, evaluate_all_gates


def _critical_orphans(count: int) -> list[OrphanedSetting]:
    # Task 171p2: 硬 P1 来源改用 critical orphaned setting（state_mismatch 已降为观测）。
    return [
        OrphanedSetting(
            tracking_id=f"t{i}",
            setting_key=f"k{i}",
            setting_name=f"设定{i}",
            introduced_in_chapter=1,
            last_mentioned_chapter=1,
            chapters_since_mention=5,
            category="critical",
        )
        for i in range(count)
    ]


def _report(
    chapter: int,
    health_score: float = 10.0,
    p1_count: int = 0,
) -> ContinuityReport:
    return ContinuityReport(
        report_id=f"rpt-{chapter}",
        project_id="proj",
        checked_up_to_chapter=chapter,
        overall_health_score=health_score,
        orphaned_settings=_critical_orphans(p1_count),
    )


def _score_halt_config(enabled: bool = True) -> GateConfig:
    return GateConfig(
        health_low_gate_enabled=True,
        health_low_score_halt_enabled=enabled,
        health_low_score_halt_window=3,
        health_low_score_halt_min_p1=20,
        health_low_score_halt_anomaly_factor=1.8,
    )


# ---------------------------------------------------------------------------
# Case 1: 开局期 score 从 10.0 回落至 5.2，P1 正常 -> 不触发
# ---------------------------------------------------------------------------


def test_score_halt_not_triggered_in_opening_with_normal_p1() -> None:
    current = _report(chapter=6, health_score=5.2, p1_count=5)
    cfg = _score_halt_config()
    triggered, reasons, updated_min = check_health_low_single_gate(
        current,
        cfg,
        previous_p1_counts=[5, 5, 5],
        min_health_score_so_far=10.0,
    )
    assert not triggered
    assert reasons == []
    assert updated_min == 5.2


# ---------------------------------------------------------------------------
# Case 2: score 创新低，但 P1 正常 -> 不触发
# ---------------------------------------------------------------------------


def test_score_halt_not_triggered_when_p1_normal() -> None:
    current = _report(chapter=9, health_score=4.0, p1_count=10)
    cfg = _score_halt_config()
    triggered, reasons, updated_min = check_health_low_single_gate(
        current,
        cfg,
        previous_p1_counts=[5, 5, 5],
        min_health_score_so_far=5.2,
    )
    assert not triggered
    assert reasons == []
    assert updated_min == 4.0


# ---------------------------------------------------------------------------
# Case 3: score 未创新低，但 P1 激增 -> 不触发（由 health_low_p1_halt 处理）
# ---------------------------------------------------------------------------


def test_score_halt_not_triggered_when_score_not_new_low() -> None:
    current = _report(chapter=9, health_score=6.0, p1_count=60)
    cfg = _score_halt_config()
    triggered, reasons, updated_min = check_health_low_single_gate(
        current,
        cfg,
        previous_p1_counts=[10, 10, 10],
        min_health_score_so_far=5.2,
    )
    assert not triggered
    assert reasons == []
    assert updated_min == 5.2


# ---------------------------------------------------------------------------
# Case 4: score 创新低且 P1 激增 -> 触发
# ---------------------------------------------------------------------------


def test_score_halt_triggered_on_new_low_and_p1_spike() -> None:
    current = _report(chapter=9, health_score=4.0, p1_count=60)
    cfg = _score_halt_config()
    triggered, reasons, updated_min = check_health_low_single_gate(
        current,
        cfg,
        previous_p1_counts=[10, 10, 10],
        min_health_score_so_far=5.2,
    )
    assert triggered
    assert len(reasons) == 1
    assert "health_low_score_halt" in reasons[0]
    assert "score=4.0" in reasons[0]
    assert "min_so_far=5.2" in reasons[0]
    assert "P1_count=60" in reasons[0]
    assert updated_min == 4.0


# ---------------------------------------------------------------------------
# Case 5: score_halt_enabled=False 时，Case 4 也不触发
# ---------------------------------------------------------------------------


def test_score_halt_disabled_does_not_trigger() -> None:
    current = _report(chapter=9, health_score=4.0, p1_count=60)
    cfg = _score_halt_config(enabled=False)
    triggered, reasons, updated_min = check_health_low_single_gate(
        current,
        cfg,
        previous_p1_counts=[10, 10, 10],
        min_health_score_so_far=5.2,
    )
    assert not triggered
    assert reasons == []
    assert updated_min == 4.0


# ---------------------------------------------------------------------------
# Case 6: 历史最低分在运行过程中正确更新
# ---------------------------------------------------------------------------


def test_min_health_score_updates_across_calls() -> None:
    cfg = _score_halt_config()

    # 第一章审计点：min 未知，current=10.0 -> 不触发，updated_min=10.0
    r1 = _report(chapter=3, health_score=10.0, p1_count=0)
    triggered1, _, min1 = check_health_low_single_gate(
        r1,
        cfg,
        previous_p1_counts=[],
        min_health_score_so_far=None,
    )
    assert not triggered1
    assert min1 == 10.0

    # 第二章审计点：score 正常回落至 5.2，P1 正常 -> 不触发，updated_min=5.2
    r2 = _report(chapter=6, health_score=5.2, p1_count=5)
    triggered2, _, min2 = check_health_low_single_gate(
        r2,
        cfg,
        previous_p1_counts=[0],
        min_health_score_so_far=min1,
    )
    assert not triggered2
    assert min2 == 5.2

    # 第三章审计点：score 创新低 4.0 且 P1 激增 -> 触发，updated_min=4.0
    r3 = _report(chapter=9, health_score=4.0, p1_count=60)
    triggered3, _, min3 = check_health_low_single_gate(
        r3,
        cfg,
        previous_p1_counts=[0, 5],
        min_health_score_so_far=min2,
    )
    assert triggered3
    assert min3 == 4.0


# ---------------------------------------------------------------------------
# 边界：previous_p1_counts 不足窗口时使用全部可用数据
# ---------------------------------------------------------------------------


def test_score_halt_uses_available_p1_counts_when_window_not_full() -> None:
    current = _report(chapter=6, health_score=4.0, p1_count=60)
    cfg = _score_halt_config()
    triggered, reasons, _ = check_health_low_single_gate(
        current,
        cfg,
        previous_p1_counts=[10],
        min_health_score_so_far=5.2,
    )
    assert triggered
    assert "health_low_score_halt" in reasons[0]


# ---------------------------------------------------------------------------
# evaluate_all_gates 透传 min_health_score_so_far
# ---------------------------------------------------------------------------


def test_evaluate_all_gates_returns_updated_min_score() -> None:
    report = _report(chapter=6, health_score=5.2, p1_count=5)
    cfg = _score_halt_config()
    triggered, reasons, updated_min = evaluate_all_gates(
        health_low_report=report,
        context_metrics={"context_emergency": False},
        chapter_result={"success": True},
        recent_results=[],
        config=cfg,
        previous_p1_counts=[5, 5, 5],
        min_health_score_so_far=10.0,
    )
    assert not triggered
    assert reasons == []
    assert updated_min == 5.2
