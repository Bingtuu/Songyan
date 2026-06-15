"""Task 106: Unified Scoring System tests."""

from __future__ import annotations

from songyan.evals.score_aggregator import ScoreAggregator
from songyan.models import (
    AiTellMatch,
    ChapterScoreCard,
    DimensionScore,
    FatigueWordMatch,
    LLMAuditResult,
    PunchCheck,
    ReviewCategory,
    ReviewIssue,
    RuleAuditResult,
    ScoreFlags,
)

# =============================================================================
# Model tests
# =============================================================================


class TestChapterScoreCard:
    def test_dimension_scores_excludes_unavailable(self):
        card = ChapterScoreCard(
            length=DimensionScore(score=0.8),
            budget=DimensionScore(score=0.9),
            coherence=DimensionScore(score=0.7),
            momentum=DimensionScore(score=-1.0),
            readability=DimensionScore(score=0.6),
        )
        dims = card.dimension_scores
        assert "length" in dims
        assert "budget" in dims
        assert "coherence" in dims
        assert "momentum" not in dims
        assert "readability" in dims

    def test_score_flags_blocking(self):
        flags = ScoreFlags(coherence_critical=True, budget_ok=True)
        assert flags.has_blocking_issue is True

        flags2 = ScoreFlags(coherence_critical=False, budget_ok=False)
        assert flags2.has_blocking_issue is True

        flags3 = ScoreFlags(coherence_critical=False, budget_ok=True)
        assert flags3.has_blocking_issue is False

    def test_score_flags_needs_revision(self):
        flags = ScoreFlags(coherence_critical=True)
        assert flags.needs_revision is True

        flags2 = ScoreFlags(coherence_major=True)
        assert flags2.needs_revision is True

        flags3 = ScoreFlags()
        assert flags3.needs_revision is False


# =============================================================================
# ScoreAggregator tests
# =============================================================================


def _make_rule_result(
    *,
    word_count: int = 3000,
    word_count_target: int = 3000,
    ai_tell_count: int = 0,
    fatigue_word_count: int = 0,
    has_opening_hook: bool = True,
    has_ending_hook: bool = True,
    paragraph_rhythm_score: float = 7.0,
    scene_count: int = 3,
    punch_check: PunchCheck | None = None,
) -> RuleAuditResult:
    return RuleAuditResult(
        word_count=word_count,
        word_count_target=word_count_target,
        word_count_ratio=word_count / word_count_target if word_count_target > 0 else 1.0,
        ai_tell_count=ai_tell_count,
        ai_tell_matches=[AiTellMatch(pattern="p", matched_text="t", location="l")] * ai_tell_count,
        fatigue_word_count=fatigue_word_count,
        fatigue_word_matches=[
            FatigueWordMatch(word="w", count=1, locations=["l"])
        ] * fatigue_word_count,
        has_opening_hook=has_opening_hook,
        has_ending_hook=has_ending_hook,
        paragraph_rhythm_score=paragraph_rhythm_score,
        scene_count=scene_count,
        punch_check=punch_check or PunchCheck(expected_punch_count=0),
    )


def _make_llm_result(*, issues: list[ReviewIssue] | None = None) -> LLMAuditResult:
    return LLMAuditResult(issues=issues or [])


class TestScoreLength:
    def test_perfect_length(self):
        rule = _make_rule_result(word_count=3000, word_count_target=3000)
        card = ScoreAggregator.aggregate("v1", rule, _make_llm_result())
        assert card.length.score == 1.0
        assert card.flags.length_ok is True

    def test_slightly_long(self):
        rule = _make_rule_result(word_count=3150, word_count_target=3000)
        card = ScoreAggregator.aggregate("v1", rule, _make_llm_result())
        assert card.length.score == 1.0
        assert card.flags.length_ok is True

    def test_moderately_long(self):
        rule = _make_rule_result(word_count=3450, word_count_target=3000)
        card = ScoreAggregator.aggregate("v1", rule, _make_llm_result())
        assert 0.0 < card.length.score < 1.0
        assert card.flags.length_ok is True

    def test_way_too_long(self):
        rule = _make_rule_result(word_count=5000, word_count_target=3000)
        card = ScoreAggregator.aggregate("v1", rule, _make_llm_result())
        assert card.length.score == 0.0
        assert card.flags.length_ok is False


class TestScoreBudget:
    def test_good_budget(self):
        rule = _make_rule_result()
        card = ScoreAggregator.aggregate("v1", rule, _make_llm_result(), budget_used=0.7)
        assert card.budget.score == 1.0
        assert card.flags.budget_ok is True

    def test_over_budget(self):
        rule = _make_rule_result()
        card = ScoreAggregator.aggregate("v1", rule, _make_llm_result(), budget_used=1.0)
        assert card.budget.score == 0.0
        assert card.flags.budget_ok is False

    def test_none_budget(self):
        rule = _make_rule_result()
        card = ScoreAggregator.aggregate("v1", rule, _make_llm_result(), budget_used=None)
        assert card.budget.score == 1.0


class TestScoreCoherence:
    def test_clean(self):
        rule = _make_rule_result()
        card = ScoreAggregator.aggregate("v1", rule, _make_llm_result())
        assert card.coherence.score == 1.0
        assert card.flags.coherence_critical is False
        assert card.flags.coherence_major is False

    def test_critical_coherence(self):
        issues = [
            ReviewIssue(
                issue_id="i1",
                category=ReviewCategory.WORLD_CONSISTENCY,
                severity="critical",
                evidence_quote="q",
                evidence_location="l",
                issue_description="d",
            )
        ]
        rule = _make_rule_result()
        card = ScoreAggregator.aggregate("v1", rule, _make_llm_result(issues=issues))
        assert card.coherence.score == 0.6
        assert card.flags.coherence_critical is True
        assert card.flags.needs_revision is True

    def test_major_coherence(self):
        issues = [
            ReviewIssue(
                issue_id="i1",
                category=ReviewCategory.CHARACTER_BEHAVIOR,
                severity="major",
                evidence_quote="q",
                evidence_location="l",
                issue_description="d",
            )
        ]
        rule = _make_rule_result()
        card = ScoreAggregator.aggregate("v1", rule, _make_llm_result(issues=issues))
        assert card.coherence.score == 0.75
        assert card.flags.coherence_major is True

    def test_non_coherence_issue_ignored(self):
        issues = [
            ReviewIssue(
                issue_id="i1",
                category=ReviewCategory.NARRATIVE_HOOK,
                severity="critical",
                evidence_quote="q",
                evidence_location="l",
                issue_description="d",
            )
        ]
        rule = _make_rule_result()
        card = ScoreAggregator.aggregate("v1", rule, _make_llm_result(issues=issues))
        assert card.coherence.score == 1.0


class TestScoreMomentum:
    def test_no_punch_points(self):
        rule = _make_rule_result(punch_check=PunchCheck(expected_punch_count=0))
        card = ScoreAggregator.aggregate("v1", rule, _make_llm_result())
        assert card.momentum.score == -1.0
        assert card.flags.momentum_present is True

    def test_full_momentum(self):
        rule = _make_rule_result(
            punch_check=PunchCheck(
                expected_punch_count=3,
                punch_density_ok=True,
                emotion_switch_ok=True,
            ),
            has_opening_hook=True,
            has_ending_hook=True,
        )
        card = ScoreAggregator.aggregate("v1", rule, _make_llm_result())
        assert card.momentum.score == 1.0
        assert card.flags.momentum_present is True

    def test_missing_hook(self):
        rule = _make_rule_result(
            punch_check=PunchCheck(
                expected_punch_count=3,
                punch_density_ok=True,
                emotion_switch_ok=True,
            ),
            has_opening_hook=False,
            has_ending_hook=True,
        )
        card = ScoreAggregator.aggregate("v1", rule, _make_llm_result())
        assert card.momentum.score == 0.8
        assert card.flags.momentum_present is True


class TestScoreReadability:
    def test_clean(self):
        rule = _make_rule_result()
        card = ScoreAggregator.aggregate("v1", rule, _make_llm_result())
        assert card.readability.score == 1.0
        assert card.flags.readability_ok is True

    def test_ai_tell_penalty(self):
        rule = _make_rule_result(ai_tell_count=2)
        card = ScoreAggregator.aggregate("v1", rule, _make_llm_result())
        assert card.readability.score == 0.7
        assert card.flags.readability_ok is True

    def test_fatigue_penalty(self):
        rule = _make_rule_result(fatigue_word_count=5)
        card = ScoreAggregator.aggregate("v1", rule, _make_llm_result())
        assert card.readability.score == 0.7

    def test_rhythm_penalty(self):
        rule = _make_rule_result(paragraph_rhythm_score=3.0)
        card = ScoreAggregator.aggregate("v1", rule, _make_llm_result())
        assert card.readability.score < 1.0


class TestOverallScore:
    def test_all_perfect(self):
        rule = _make_rule_result(
            punch_check=PunchCheck(
                expected_punch_count=3,
                punch_density_ok=True,
                emotion_switch_ok=True,
            )
        )
        card = ScoreAggregator.aggregate("v1", rule, _make_llm_result(), budget_used=0.5)
        assert card.overall_score == 1.0

    def test_missing_momentum_normalizes(self):
        rule = _make_rule_result(punch_check=PunchCheck(expected_punch_count=0))
        card = ScoreAggregator.aggregate("v1", rule, _make_llm_result(), budget_used=0.5)
        # momentum excluded, weights renormalized
        assert card.overall_score == 1.0

    def test_realistic_score(self):
        rule = _make_rule_result(
            word_count=3300,
            word_count_target=3000,
            ai_tell_count=1,
            fatigue_word_count=2,
            has_opening_hook=True,
            has_ending_hook=True,
            paragraph_rhythm_score=6.0,
            punch_check=PunchCheck(
                expected_punch_count=3,
                punch_density_ok=True,
                emotion_switch_ok=True,
            ),
        )
        issues = [
            ReviewIssue(
                issue_id="i1",
                category=ReviewCategory.CHARACTER_BEHAVIOR,
                severity="major",
                evidence_quote="q",
                evidence_location="l",
                issue_description="d",
            )
        ]
        card = ScoreAggregator.aggregate(
            "v1", rule, _make_llm_result(issues=issues), budget_used=0.85
        )
        assert 0.0 < card.overall_score < 1.0
        assert card.flags.coherence_major is True


class TestDimensionDegradation:
    """维度级劣化检测 — Task 106-patch."""

    def test_length_degradation_detected(self):
        best = ScoreAggregator.aggregate(
            "v1", _make_rule_result(word_count=3000), _make_llm_result()
        )
        current = ScoreAggregator.aggregate(
            "v2", _make_rule_result(word_count=5000), _make_llm_result()
        )
        assert best.length.score == 1.0
        assert current.length.score == 0.0
        assert current.length.score < best.length.score - 0.3

    def test_coherence_degradation_detected(self):
        best = ScoreAggregator.aggregate(
            "v1", _make_rule_result(), _make_llm_result()
        )
        issues = [
            ReviewIssue(
                issue_id="i1",
                category=ReviewCategory.WORLD_CONSISTENCY,
                severity="critical",
                evidence_quote="q",
                evidence_location="l",
                issue_description="d",
            )
        ]
        current = ScoreAggregator.aggregate(
            "v2", _make_rule_result(), _make_llm_result(issues=issues)
        )
        assert best.coherence.score == 1.0
        assert current.coherence.score == 0.6
        # 1 个 critical 扣 0.4，0.6 < 1.0 - 0.3，触发劣化
        assert current.coherence.score < best.coherence.score - 0.3

    def test_readability_degradation_detected(self):
        best = ScoreAggregator.aggregate("v1", _make_rule_result(), _make_llm_result())
        current = ScoreAggregator.aggregate(
            "v2", _make_rule_result(ai_tell_count=5), _make_llm_result()
        )
        assert best.readability.score == 1.0
        # 5 * 0.15 = 0.75，被 cap 到 0.5，所以 score = 0.5
        assert current.readability.score == 0.5
        assert current.readability.score < best.readability.score - 0.3

    def test_unavailable_dimension_ignored(self):
        """未评估维度（score=-1.0）不参与劣化检测."""
        best = ScoreAggregator.aggregate(
            "v1",
            _make_rule_result(punch_check=PunchCheck(expected_punch_count=0)),
            _make_llm_result(),
        )
        current = ScoreAggregator.aggregate(
            "v2",
            _make_rule_result(punch_check=PunchCheck(expected_punch_count=0)),
            _make_llm_result(),
        )
        assert best.momentum.score == -1.0
        assert current.momentum.score == -1.0
        # 不会触发劣化（因为 score < 0.0 被跳过）
        assert not (current.momentum.score >= 0.0 and best.momentum.score >= 0.0)


class TestLengthThresholdCalibration:
    """长度阈值校准测试 — length_ok 阈值从 0.6 下调到 0.5."""

    def test_ratio_1_25_passes_length_ok(self):
        rule = _make_rule_result(word_count=3750, word_count_target=3000)
        card = ScoreAggregator.aggregate("v1", rule, _make_llm_result())
        assert card.length.score == 0.5
        assert card.flags.length_ok is True

    def test_ratio_1_35_fails_length_ok(self):
        rule = _make_rule_result(word_count=4050, word_count_target=3000)
        card = ScoreAggregator.aggregate("v1", rule, _make_llm_result())
        assert card.length.score == 0.3
        assert card.flags.length_ok is False
