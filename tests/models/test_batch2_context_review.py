"""Batch 2: Context, review, creative_mode, literary models."""

import pytest
from pydantic import ValidationError

from songyan.models.chapter import ChapterGoal
from songyan.models.context import (
    ChapterSummary,
    CharacterStateSnapshot,
    ContextPackage,
    ForeshadowingItem,
    GenreRules,
    HardConstraint,
    ModeRules,
    RecentPlot,
    SoftReference,
)
from songyan.models.creative_mode import CreativeBrief, CreativeModeProfile, Tension
from songyan.models.literary import LiteraryAuditResult, LiteraryObservation
from songyan.models.review import (
    AiTellMatch,
    FatigueWordMatch,
    LLMAuditResult,
    MergedReviewReport,
    ReviewCategory,
    ReviewIssue,
    RuleAuditResult,
)


class TestTension:
    """Tension 测试."""

    def test_instantiation(self) -> None:
        t = Tension(
            tension_id="t-001",
            description="主角与反派的力量对比",
            tension_type="power_imbalance",
        )
        assert t.intensity == 0.5
        assert t.resolution == ""

    def test_all_types(self) -> None:
        """所有 tension_type 合法值."""
        for tt in (
            "value_conflict",
            "information_asymmetry",
            "power_imbalance",
            "emotional_contrast",
            "temporal_pressure",
        ):
            t = Tension(
                tension_id=f"t-{tt}",
                description="test",
                tension_type=tt,
            )
            assert t.tension_type == tt


class TestCreativeBrief:
    """CreativeBrief 测试."""

    def test_instantiation(self) -> None:
        goal = ChapterGoal(chapter_number=1)
        cb = CreativeBrief(
            mode_id="webnovel",
            chapter_goal=goal,
        )
        assert cb.mode_id == "webnovel"
        assert cb.creative_intent == ""

    def test_with_tensions(self) -> None:
        goal = ChapterGoal(chapter_number=1)
        cb = CreativeBrief(
            mode_id="webnovel",
            chapter_goal=goal,
            required_tensions=[
                Tension(
                    tension_id="t-001",
                    description="力量悬殊",
                    tension_type="power_imbalance",
                    intensity=0.8,
                ),
            ],
            forbidden_patterns=["打脸后立刻和解"],
        )
        assert len(cb.required_tensions) == 1
        assert cb.required_tensions[0].intensity == 0.8


class TestCreativeModeProfile:
    """CreativeModeProfile 测试."""

    def test_instantiation(self) -> None:
        cmp = CreativeModeProfile(id="webnovel", name="网文模式")
        assert cmp.revision_policy == "standard"
        assert cmp.context_pruning_strategy == "default"

    def test_from_dict(self) -> None:
        data = {
            "id": "webnovel",
            "name": "网文模式",
            "enabled_agents": {
                "pre_write": ["goal_planner", "creative_director"],
                "write": ["writer"],
            },
            "audit_weights": {"narrative_pacing": 1.2},
            "tolerance": {"max_ai_tells": 2.0},
        }
        cmp = CreativeModeProfile.from_dict(data)
        assert cmp.id == "webnovel"
        assert "goal_planner" in cmp.enabled_agents["pre_write"]
        assert cmp.tolerance["max_ai_tells"] == 2.0


class TestHardConstraint:
    """HardConstraint 测试."""

    def test_all_types(self) -> None:
        for ctype in ("character_state", "setting_fact", "timeline", "taboo", "obligation"):
            hc = HardConstraint(type=ctype, description="test", source="test")
            assert hc.type == ctype


class TestCharacterStateSnapshot:
    """CharacterStateSnapshot 测试."""

    def test_instantiation(self) -> None:
        css = CharacterStateSnapshot(
            character_id="char-001",
            name="王林",
            importance_score=1.0,
        )
        assert css.importance_score == 1.0
        assert css.current_location is None


class TestChapterSummary:
    """ChapterSummary 测试."""

    def test_instantiation(self) -> None:
        cs = ChapterSummary(chapter_number=1, summary="主角出发")
        assert cs.chapter_number == 1
        assert cs.key_events == []


class TestRecentPlot:
    """RecentPlot 测试."""

    def test_instantiation(self) -> None:
        rp = RecentPlot()
        assert rp.summaries == []
        assert rp.last_chapter_ending == ""

    def test_with_summaries(self) -> None:
        rp = RecentPlot(
            summaries=[
                ChapterSummary(chapter_number=1, summary="出发"),
                ChapterSummary(chapter_number=2, summary="遇险"),
            ],
            last_chapter_ending="他推开了那扇门……",
        )
        assert len(rp.summaries) == 2


class TestForeshadowingItem:
    """ForeshadowingItem 测试."""

    def test_all_statuses(self) -> None:
        for status in ("planted", "due", "overdue", "resolved"):
            fi = ForeshadowingItem(
                foreshadowing_id="f-001",
                description="神秘玉简",
                planted_in_chapter=1,
                status=status,
            )
            assert fi.status == status


class TestSoftReference:
    """SoftReference 测试."""

    def test_all_types(self) -> None:
        for stype in ("world_setting", "character_backstory", "style_sample"):
            sr = SoftReference(type=stype, content="test")
            assert sr.type == stype


class TestGenreRules:
    """GenreRules 测试."""

    def test_instantiation(self) -> None:
        gr = GenreRules(genre_id="xuanhuan")
        assert gr.writer_rules == []
        assert gr.fatigue_words == []


class TestModeRules:
    """ModeRules 测试."""

    def test_defaults(self) -> None:
        mr = ModeRules(mode_id="webnovel")
        assert mr.tolerance_max_ai_tells == 2.0
        assert mr.tolerance_max_fatigue_words == 3.0


class TestContextPackage:
    """ContextPackage 测试."""

    def test_minimal_instantiation(self) -> None:
        goal = ChapterGoal(chapter_number=1)
        cp = ContextPackage(chapter_goal=goal)
        assert cp.estimated_tokens == 0
        assert cp.creative_brief is None

    def test_with_creative_brief(self) -> None:
        goal = ChapterGoal(chapter_number=1)
        brief = CreativeBrief(mode_id="webnovel", chapter_goal=goal)
        cp = ContextPackage(
            chapter_goal=goal,
            creative_brief=brief,
            hard_constraints=[
                HardConstraint(type="taboo", description="不能暴露身份", source="设定"),
            ],
            character_states=[
                CharacterStateSnapshot(
                    character_id="char-001",
                    name="王林",
                    importance_score=1.0,
                ),
            ],
            recent_plot=RecentPlot(
                summaries=[ChapterSummary(chapter_number=1, summary="出发")],
            ),
            genre_rules=GenreRules(
                genre_id="xuanhuan",
                writer_rules=["设定不可吃书"],
            ),
            mode_rules=ModeRules(mode_id="webnovel"),
        )
        assert cp.creative_brief is not None
        assert len(cp.hard_constraints) == 1
        assert cp.genre_rules is not None

    def test_budget_tracking(self) -> None:
        goal = ChapterGoal(chapter_number=1)
        cp = ContextPackage(chapter_goal=goal, estimated_tokens=15000, budget_used=0.5)
        assert cp.budget_used == 0.5


class TestReviewCategory:
    """ReviewCategory 枚举测试."""

    def test_all_14_dimensions(self) -> None:
        expected = {
            "world_consistency",
            "character_behavior",
            "timeline",
            "new_setting_unregistered",
            "narrative_pacing",
            "narrative_hook",
            "info_dump",
            "dialogue_distinctness",
            "dialogue_subtext",
            "description_sensory",
            "show_dont_tell",
            "genre_numerical",
            "voice",
            "exposition",
        }
        actual = {m.value for m in ReviewCategory}
        assert actual == expected


class TestReviewIssue:
    """ReviewIssue 测试."""

    def test_instantiation(self) -> None:
        ri = ReviewIssue(
            issue_id="i-001",
            category=ReviewCategory.WORLD_CONSISTENCY,
            severity="critical",
            evidence_quote="他昨天还是筑基期",
            evidence_location="第3段",
            issue_description="境界突变无解释",
        )
        assert ri.severity == "critical"
        assert ri.fix_type == "patch"
        assert ri.confidence == 1.0

    def test_invalid_severity_raises(self) -> None:
        """非法 severity 抛 ValidationError."""
        with pytest.raises(ValidationError):
            ReviewIssue(
                issue_id="i-001",
                category=ReviewCategory.WORLD_CONSISTENCY,
                severity="invalid",  # 非法值
                evidence_quote="test",
                evidence_location="test",
                issue_description="test",
            )


class TestRuleAuditResult:
    """RuleAuditResult 测试."""

    def test_defaults(self) -> None:
        rar = RuleAuditResult()
        assert rar.auditor_id == "rule_auditor"
        assert rar.ai_tell_count == 0
        assert rar.word_count_ok is True

    def test_with_matches(self) -> None:
        rar = RuleAuditResult(
            ai_tell_matches=[
                AiTellMatch(pattern="不禁", matched_text="不禁一怔", location="第1段"),
            ],
            ai_tell_count=1,
            fatigue_word_matches=[
                FatigueWordMatch(word="冷笑", count=2, locations=["第2段", "第5段"]),
            ],
            fatigue_word_count=2,
            has_opening_hook=True,
            word_count=3200,
        )
        assert rar.ai_tell_count == 1
        assert rar.has_opening_hook is True


class TestLLMAuditResult:
    """LLMAuditResult 测试."""

    def test_defaults(self) -> None:
        lar = LLMAuditResult()
        assert lar.auditor_id == "llm_auditor"
        assert lar.cliche_risk_score == 0.0

    def test_with_issues(self) -> None:
        lar = LLMAuditResult(
            issues=[
                ReviewIssue(
                    issue_id="i-001",
                    category=ReviewCategory.NARRATIVE_PACING,
                    severity="major",
                    evidence_quote="连续3段叙述",
                    evidence_location="第10-12段",
                    issue_description="节奏拖沓",
                ),
            ],
            dimension_scores={"narrative_pacing": 4.0},
        )
        assert len(lar.issues) == 1
        assert lar.dimension_scores["narrative_pacing"] == 4.0


class TestMergedReviewReport:
    """MergedReviewReport 测试."""

    def test_defaults(self) -> None:
        mrr = MergedReviewReport(chapter_version_id="v-001")
        assert mrr.has_critical is False
        assert mrr.has_major is False
        assert mrr.patchable_issues == []

    def test_has_critical(self) -> None:
        mrr = MergedReviewReport(
            chapter_version_id="v-001",
            issues=[
                ReviewIssue(
                    issue_id="i-001",
                    category=ReviewCategory.WORLD_CONSISTENCY,
                    severity="critical",
                    evidence_quote="test",
                    evidence_location="test",
                    issue_description="test",
                ),
            ],
        )
        assert mrr.has_critical is True
        assert mrr.has_major is False

    def test_patchable_issues(self) -> None:
        mrr = MergedReviewReport(
            chapter_version_id="v-001",
            issues=[
                ReviewIssue(
                    issue_id="i-001",
                    category=ReviewCategory.WORLD_CONSISTENCY,
                    severity="critical",
                    evidence_quote="test",
                    evidence_location="test",
                    issue_description="test",
                    fix_type="patch",
                ),
                ReviewIssue(
                    issue_id="i-002",
                    category=ReviewCategory.NARRATIVE_PACING,
                    severity="major",
                    evidence_quote="test",
                    evidence_location="test",
                    issue_description="test",
                    fix_type="rewrite_scene",
                ),
                ReviewIssue(
                    issue_id="i-003",
                    category=ReviewCategory.INFO_DUMP,
                    severity="minor",
                    evidence_quote="test",
                    evidence_location="test",
                    issue_description="test",
                    fix_type="patch",
                ),
            ],
        )
        # 只有 critical/major + fix_type=patch
        patchable = mrr.patchable_issues
        assert len(patchable) == 1
        assert patchable[0].issue_id == "i-001"


class TestLiteraryObservation:
    """LiteraryObservation 测试."""

    def test_all_types(self) -> None:
        for otype in (
            "character_tooling",
            "conceptual_idling",
            "excessive_smoothing",
            "valuable_fissure",
            "cliche_risk",
            "polyphony_weakness",
            "authorial_intrusion",
        ):
            lo = LiteraryObservation(
                observation_id="o-001",
                observation_type=otype,
                description="test",
            )
            assert lo.observation_type == otype

    def test_valuable_fissure_preserve(self) -> None:
        lo = LiteraryObservation(
            observation_id="o-001",
            observation_type="valuable_fissure",
            description="此处裂隙可能有意图",
            preserve=True,
        )
        assert lo.preserve is True


class TestLiteraryAuditResult:
    """LiteraryAuditResult 测试."""

    def test_defaults(self) -> None:
        lar = LiteraryAuditResult()
        assert lar.auditor_id == "literary_auditor"
        assert lar.observations == []

    def test_with_observations(self) -> None:
        lar = LiteraryAuditResult(
            observations=[
                LiteraryObservation(
                    observation_id="o-001",
                    observation_type="valuable_fissure",
                    description="有意图的裂隙",
                    preserve=True,
                ),
            ],
            literary_quality_score=7.5,
        )
        assert lar.literary_quality_score == 7.5
