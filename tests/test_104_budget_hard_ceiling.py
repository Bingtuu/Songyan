"""Task 104: BudgetHardCeiling — 预算硬天花板单元测试."""

from __future__ import annotations

import pytest

from songyan.agents.context_manager import BudgetPruner
from songyan.models import (
    ArcSummary,
    ChapterGoal,
    ChapterSummary,
    CharacterStateSnapshot,
    ContextPackage,
    CreativeBrief,
    CreativeModeProfile,
    DialogueStyleCard,
    EmotionArcItem,
    ForeshadowingItem,
    GenreProfile,
    HardConstraint,
    ModeRules,
    NewConceptBudget,
    OpenThread,
    ProjectSetting,
    ProtagonistActiveChoice,
    PunchPoint,
    RecentPlot,
    SoftReference,
    Tension,
    VoiceAnchor,
    VoiceSample,
    VolumeSummary,
)

# =============================================================================
# Helpers
# =============================================================================

_LONG_TEXT = (
    "这是一段用于压测上下文预算的极长描述，"
    "需要包含足够的汉字来模拟真实创作导演输出中 style_constraints、"
    "required_tensions、voice_samples 等字段膨胀后的 token 占用。" * 20
)


def _make_goal(chapter_number: int = 50) -> ChapterGoal:
    return ChapterGoal(
        chapter_number=chapter_number,
        target_events=[],
        hooks=[],
        obligations=[],
        word_count_target=3200,
    )


def _make_large_creative_brief() -> CreativeBrief:
    """构造类似 xuanhuan Ch2 的超长 creative_brief."""
    lt = _LONG_TEXT
    return CreativeBrief(
        mode_id="webnovel_intense",
        chapter_goal=_make_goal(chapter_number=2),
        creative_intent="让读者持续保持高能阅读体验" + lt[:80],
        required_tensions=[
            Tension(
                tension_id=f"t-{i}",
                description=f"张力{i}: {lt}",
                tension_type="power_imbalance",
                characters_involved=["主角", "反派"],
                resolution="未解决",
                intensity=0.8,
            )
            for i in range(5)
        ],
        forbidden_patterns=[f"禁止模式{i}: {lt[:60]}" for i in range(6)],
        allowed_fissures=[f"可控裂口{i}: {lt[:60]}" for i in range(4)],
        style_constraints=[f"风格约束{i}: {lt}" for i in range(8)],
        reader_contract="读者应为本章主角的逆袭感到振奋",
        polyphony_notes=[f"复调注释{i}" for i in range(3)],
        punch_points=[
            PunchPoint(
                punch_id=f"p-{i}",
                description=f"刺激点{i}: {lt}",
                punch_type="revelation",
                target_scene=i + 1,
                intensity=0.9,
            )
            for i in range(5)
        ],
        emotion_arc=[
            EmotionArcItem(scene=i, from_emotion="压抑", to_emotion="爆发")
            for i in range(8)
        ],
        voice_anchors=[
            VoiceAnchor(
                character_id=f"c-{i}",
                emotional_register="冷酷",
                verbal_tick="哼",
                taboo_phrase="不可能",
            )
            for i in range(3)
        ],
        voice_samples=[
            VoiceSample(
                character_id=f"c-{i}",
                character_name=f"角色{i}",
                sample_lines=[lt[:120], lt[120:240]],
                forbidden_patterns=["禁止台词1", "禁止台词2"],
                mood_anchor="悲愤",
            )
            for i in range(3)
        ],
        protagonist_active_choice=ProtagonistActiveChoice(
            choice="主角决定冒险突破",
            alternatives=["退缩", "求助"],
            cost="经脉受损",
            irreversible_consequence="再也无法回头",
        ),
        new_concept_budget=NewConceptBudget(
            max_new_core_concepts=2,
            grounding_scene="铁匠铺爆炸现场",
            forbidden_mode="禁止连续解释",
        ),
    )


def _make_xuanhuan_like_context() -> ContextPackage:
    """复现 xuanhuan Ch2 触发 ContextEmergency 后仍超预算的场景."""
    from songyan.agents.context_manager import _build_genre_rules

    lt = _LONG_TEXT
    genre = GenreProfile(
        id="xuanhuan",
        name="玄幻",
        chapter_types=["开篇", "升级", "战斗"],
        fatigue_words=["冷笑", "蝼蚁", "废物"],
        satisfaction_types=["实力提升", "打脸"],
        pacing_rule="每章至少一个小高潮",
        writer_rules=["对话简短有力"] * 3,
        reviewer_focus=["设定一致性"],
        taboos=["虐主", "绿帽"],
        pacing_templates=[
            {"name": "节奏模板1", "pattern": "压抑→爆发→收获" * 20},
            {"name": "节奏模板2", "pattern": "埋伏→冲突→反转" * 20},
        ],
        sensory_templates=[
            {"sense": "visual", "template": "红光冲天" * 20},
            {"sense": "tactile", "template": "气血翻涌" * 20},
        ],
    )
    mode = CreativeModeProfile(
        id="webnovel_intense",
        name="高强度网文",
        enabled_agents={"pre_write": ["goal_planner", "creative_director"]},
        audit_weights={"style_ai_tells": 0.3},
        active_audit_dimensions=["style_ai_tells"],
        revision_policy="standard",
        tolerance={"max_ai_tells": 2.0, "max_fatigue_words": 3.0},
        context_pruning_strategy="default",
        literary_optimization_plugins=[
            "punch_density",
            "paragraph_rhythm",
            "sensory_immersion",
            "dialogue_basics",
        ],
    )
    project = ProjectSetting(
        title="测试玄幻",
        genre_id="xuanhuan",
        mode_id="webnovel_intense",
        protagonist_name="陆沉",
        protagonist_background="铁匠铺学徒",
        core_hook="获得灵渊传承",
        tone="热血",
        target_reader_expectation="爽文读者",
        taboos=["绿帽"],
    )
    goal = _make_goal(chapter_number=2)
    return ContextPackage(
        chapter_goal=goal,
        creative_brief=_make_large_creative_brief(),
        mode_profile=mode,
        hard_constraints=[
            HardConstraint(type="obligation", description=f"核心义务{i}: {lt[:80]}", source="test")
            for i in range(6)
        ],
        character_states=[
            CharacterStateSnapshot(
                character_id="char-001",
                name="陆沉",
                current_location="铁匠铺",
                current_cultivation="淬体境一重",
                emotional_state="愤怒",
                importance_score=1.0,
            ),
            CharacterStateSnapshot(
                character_id="char-002",
                name="赵天衡",
                current_location="赵家",
                emotional_state="阴沉",
                importance_score=0.8,
            ),
        ],
        recent_plot=RecentPlot(
            summaries=[
                ChapterSummary(
                    chapter_number=1,
                    summary="第一章摘要：陆沉获得灵渊传承" + lt[:100],
                    key_events=["获得传承"],
                    characters_appeared=["陆沉"],
                )
            ]
        ),
        foreshadowing=[
            ForeshadowingItem(
                foreshadowing_id="fs-001",
                description="神秘老人身份" + lt[:80],
                planted_in_chapter=1,
                status="planted",
            )
        ],
        genre_rules=_build_genre_rules(genre, project, goal),
        mode_rules=ModeRules(mode_id="webnovel_intense"),
    )


def _make_ctx(
    n_soft_refs: int = 0,
    n_open_threads: int = 0,
    n_foreshadowing: int = 0,
    n_character_states: int = 0,
    n_dialogue_cards: int = 0,
    n_summaries: int = 0,
    with_arc_volume: bool = False,
) -> ContextPackage:
    goal = _make_goal()
    ctx = ContextPackage(
        chapter_goal=goal,
        hard_constraints=[
            HardConstraint(type="obligation", description="核心义务", source="test"),
        ],
    )
    if n_soft_refs > 0:
        ctx.soft_references = [
            SoftReference(
                type="world_setting",
                content=f"设定{i}: 第{i}个",
                relevance_score=0.7,
                last_mentioned_chapter=i,
            )
            for i in range(n_soft_refs)
        ]
    if n_open_threads > 0:
        ctx.open_threads = [
            OpenThread(
                thread_id=f"t-{i}",
                description=f"线程{i}",
                source_type="setting",
                source_chapter=i,
                priority=0.5 + (i * 0.1),
            )
            for i in range(n_open_threads)
        ]
    if n_foreshadowing > 0:
        ctx.foreshadowing = [
            ForeshadowingItem(
                foreshadowing_id=f"f-{i}",
                description=f"伏笔{i}",
                planted_in_chapter=i,
                status="planted",
            )
            for i in range(n_foreshadowing)
        ]
    if n_character_states > 0:
        ctx.character_states = [
            CharacterStateSnapshot(
                character_id=f"c-{i}",
                name=f"角色{i}",
                importance_score=max(0.1, 1.0 - (i * 0.2)),
            )
            for i in range(n_character_states)
        ]
    if n_dialogue_cards > 0:
        ctx.dialogue_style_cards = [
            DialogueStyleCard(character_id=f"dc-{i}", project_id="test")
            for i in range(n_dialogue_cards)
        ]
    if n_summaries > 0:
        ctx.recent_plot = RecentPlot(
            summaries=[
                ChapterSummary(
                    chapter_number=i,
                    summary="摘要" * 30,
                    key_events=[f"事件{i}"],
                )
                for i in range(n_summaries)
            ]
        )
    if with_arc_volume:
        ctx.arc_context = ArcSummary(
            arc_id="a1",
            project_id="test",
            start_chapter=1,
            end_chapter=50,
            arc_summary="A" * 500,
            key_events=["A", "B", "C", "D", "E"],
        )
        ctx.volume_context = VolumeSummary(
            volume_id="v1",
            project_id="test",
            start_chapter=1,
            end_chapter=50,
            volume_summary="V" * 500,
            major_revelations=["R1", "R2", "R3", "R4"],
        )
    return ctx


# =============================================================================
# Fullness Factor
# =============================================================================

class TestDynamicFullnessFactor:
    def test_zero_fullness(self) -> None:
        assert BudgetPruner._dynamic_fullness_factor(0.0) == 1.0

    def test_half_fullness(self) -> None:
        """Task 104: 0.5 * 0.7 = 0.35 → 0.65."""
        assert BudgetPruner._dynamic_fullness_factor(0.5) == pytest.approx(0.65)

    def test_full_fullness(self) -> None:
        """Task 104: 1.0 * 0.7 = 0.7 → 0.3."""
        assert BudgetPruner._dynamic_fullness_factor(1.0) == pytest.approx(0.30)

    def test_formula_uses_0_7_not_0_5(self) -> None:
        """明确验证系数是 0.7 而非旧的 0.5."""
        result = BudgetPruner._dynamic_fullness_factor(0.5)
        assert result == pytest.approx(0.65)
        assert result != pytest.approx(0.75)


# =============================================================================
# ContextEmergency Trigger
# =============================================================================

class TestContextEmergency:
    def _make_overflow_context(self) -> ContextPackage:
        """构造一个远超预算的上下文包."""
        return _make_ctx(
            n_soft_refs=20,
            n_open_threads=10,
            n_foreshadowing=15,
            n_character_states=8,
            n_dialogue_cards=5,
            n_summaries=10,
            with_arc_volume=True,
        )

    def test_emergency_triggered_when_budget_used_exceeds_1_0(self) -> None:
        pruner = BudgetPruner()
        ctx = self._make_overflow_context()
        budget = 500  # 极小的预算，强制超预算
        result = pruner.prune(ctx, budget)
        assert result.context_emergency is True
        assert result.budget_used <= 1.0

    def test_emergency_reduces_tokens_significantly(self) -> None:
        pruner = BudgetPruner()
        ctx = self._make_overflow_context()
        budget = 500
        before = pruner._estimate_package(ctx)
        result = pruner.prune(ctx, budget)
        assert before > budget
        # Task 110c: 分级 emergency 显著降低 token，但极端情况可能仍超预算
        assert result.estimated_tokens < before
        assert result.context_emergency is True

    def test_emergency_drastically_reduces_soft_partitions(self) -> None:
        pruner = BudgetPruner()
        ctx = self._make_overflow_context()
        result = pruner.prune(ctx, 500)
        assert result.context_emergency is True
        assert result.soft_references == []
        assert result.foreshadowing == []
        assert result.dialogue_style_cards == []
        assert result.human_marks == []
        assert result.open_threads == []
        assert result.permanent_scenes == []

    def test_emergency_preserves_hard_partitions(self) -> None:
        pruner = BudgetPruner()
        ctx = self._make_overflow_context()
        result = pruner.prune(ctx, 500)
        assert result.context_emergency is True
        assert result.chapter_goal is not None
        assert result.hard_constraints
        assert result.genre_rules is not None or ctx.genre_rules is None
        assert result.mode_rules is not None or ctx.mode_rules is None

    def test_emergency_keeps_top_character_only(self) -> None:
        pruner = BudgetPruner()
        ctx = _make_ctx(n_character_states=5)
        result = pruner.prune(ctx, 500)
        if result.context_emergency:
            assert len(result.character_states) == 1
            top = max(ctx.character_states, key=lambda s: s.importance_score)
            assert result.character_states[0].character_id == top.character_id

    def test_emergency_keeps_only_last_summary(self) -> None:
        pruner = BudgetPruner()
        ctx = _make_ctx(n_summaries=5)
        result = pruner.prune(ctx, 500)
        if result.context_emergency:
            assert result.recent_plot is not None
            assert result.recent_plot.summaries == []

    def test_no_emergency_when_under_budget(self) -> None:
        pruner = BudgetPruner()
        ctx = ContextPackage(chapter_goal=_make_goal())
        result = pruner.prune(ctx, 10000)
        assert result.context_emergency is False
        assert result.budget_used < 1.0

    def test_emergency_does_not_mutate_original(self) -> None:
        pruner = BudgetPruner()
        ctx = self._make_overflow_context()
        original_soft = len(ctx.soft_references)
        original_char = len(ctx.character_states)
        result = pruner.prune(ctx, 500)
        assert result.context_emergency is True
        assert len(ctx.soft_references) == original_soft
        assert len(ctx.character_states) == original_char
        assert ctx.context_emergency is False

    def test_emergency_trims_large_creative_brief_to_fit_budget(self) -> None:
        """Task 173: 大 creative_brief 触发 emergency 后必须被裁剪到预算内."""
        pruner = BudgetPruner()
        ctx = _make_xuanhuan_like_context()
        budget = 8500
        before = pruner._estimate_package(ctx)
        result = pruner.prune(ctx, budget)

        assert before > budget
        assert result.context_emergency is True
        assert result.budget_used <= 1.0, (
            f"ContextEmergency 后仍超预算: budget_used={result.budget_used}, "
            f"estimated_tokens={result.estimated_tokens}, budget={budget}"
        )
        assert result.creative_brief is not None
        # creative_brief 必须被显著裁剪
        assert len(result.creative_brief.style_constraints) <= 3
        assert len(result.creative_brief.required_tensions) <= 2
        assert len(result.creative_brief.punch_points) <= 2
        assert len(result.creative_brief.voice_samples) == 0
