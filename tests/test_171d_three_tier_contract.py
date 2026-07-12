"""Tests for Task 171d three-tier contract (A1 render + A3 spot-read observe-only)."""

from __future__ import annotations

from songyan.evals.db_metrics import (
    LiteraryScorePoint,
    detect_literary_spot_read,
    render_three_tier_contract_summary,
)


def _points(values: list[float]) -> list[LiteraryScorePoint]:
    """Build points where all four dims equal the given per-chapter value."""
    return [
        LiteraryScorePoint(
            chapter=i + 1,
            literary_quality_score=v,
            character_autonomy_score=v,
            conceptual_grounding_score=v,
            fissure_preservation_score=v,
        )
        for i, v in enumerate(values)
    ]


class TestDetectLiterarySpotRead:
    def test_insufficient_baseline_no_trigger(self) -> None:
        res = detect_literary_spot_read(_points([4.0] * 6))
        assert res.baseline_available is False
        assert res.spot_read_recommended is False

    def test_stable_scores_no_trigger(self) -> None:
        # 15 chapters all ~4.0: window mean never drops below base*0.85 (=3.4)
        res = detect_literary_spot_read(_points([4.0] * 15))
        assert res.baseline_available is True
        assert res.spot_read_recommended is False
        assert res.triggered_dimensions == []

    def test_relative_floor_breach_triggers(self) -> None:
        # baseline (first 10) = 4.0 -> relative floor 3.4; later window drops to 3.0
        values = [4.0] * 10 + [3.0] * 5
        res = detect_literary_spot_read(_points(values))
        assert res.spot_read_recommended is True
        assert "literary_quality_score" in res.triggered_dimensions
        # first trigger window should be recorded
        assert res.first_trigger_window["literary_quality_score"] is not None

    def test_absolute_floor_protects_low_baseline(self) -> None:
        # baseline 3.2 -> relative floor 2.72, but absolute floor 3.0 dominates;
        # window drops to 2.8 < 3.0 -> trigger (rubric 1–10 scale, floor=3.0)
        values = [3.2] * 10 + [2.8] * 5
        res = detect_literary_spot_read(_points(values))
        assert res.spot_read_recommended is True

    def test_result_is_observe_only_shape(self) -> None:
        """A3: 结果只含建议标志/维度，无任何 halt/block/gate 字段."""
        res = detect_literary_spot_read(_points([4.0] * 15))
        fields = set(res.model_dump().keys())
        assert not (
            fields & {"halt", "blocked", "gate_triggered", "auto_halt", "reject"}
        )
        assert "spot_read_recommended" in fields


class TestRenderThreeTierContractSummary:
    def test_tiers_present_and_labeled(self) -> None:
        res = detect_literary_spot_read(_points([4.0] * 15))
        md = render_three_tier_contract_summary(res, tier1_hard_defect_total=0)
        assert "Tier 1" in md
        assert "Tier 2" in md
        assert "Tier 3" in md
        # 阻塞性标注互不混淆
        assert "阻塞" in md
        assert "observe" in md.lower()

    def test_tier1_hard_defect_shown(self) -> None:
        res = detect_literary_spot_read(_points([4.0] * 15))
        md = render_three_tier_contract_summary(
            res, tier1_hard_defect_total=3, tier1_detail="meta 2 + 重复 1"
        )
        assert "3 处硬缺陷" in md

    def test_tier2_spot_read_recommendation_rendered(self) -> None:
        values = [4.0] * 10 + [3.0] * 5
        res = detect_literary_spot_read(_points(values))
        md = render_three_tier_contract_summary(res, tier1_hard_defect_total=0)
        assert "建议人工抽读" in md

    def test_tier2_never_says_blocked(self) -> None:
        """A3 铁律：Tier 2 行必须标 observe/不阻塞，绝不出现自动阻塞语义."""
        values = [4.0] * 10 + [3.0] * 5
        res = detect_literary_spot_read(_points(values))
        md = render_three_tier_contract_summary(res, tier1_hard_defect_total=0)
        # Tier 2 行含"不阻塞"
        tier2_line = next(line for line in md.splitlines() if "Tier 2" in line)
        assert "不阻塞" in tier2_line
