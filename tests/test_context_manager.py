"""Tests for ContextManager Agent."""

from __future__ import annotations

import pytest

from songyan.agents.context_manager import (
    BudgetPruner,
    TokenEstimator,
    _build_character_snapshots,
    _build_genre_rules,
    _build_hard_constraints,
    _build_mode_rules,
    _build_recent_plot,
    _build_soft_references,
    _dynamic_max_for_chapter,
    _rank_foreshadowings,
    assemble_context_package,
)
from songyan.models import (
    ChapterGoal,
    ChapterSummary,
    Character,
    CharacterState,
    CharacterStateSnapshot,
    ContextPackage,
    CreativeBrief,
    CreativeModeProfile,
    ForeshadowingItem,
    GenreProfile,
    GenreRules,
    HardConstraint,
    HumanMark,
    ModeRules,
    NewSetting,
    ProjectSetting,
    RecentPlot,
    SoftReference,
    Tension,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_project() -> ProjectSetting:
    return ProjectSetting(
        title="测试项目",
        genre_id="xuanhuan",
        mode_id="webnovel",
        protagonist_name="林凡",
        protagonist_background="孤儿出身",
        core_hook="逆天改命",
        tone="热血",
        target_reader_expectation="爽文读者",
        taboos=["绿帽"],
    )


def _make_genre() -> GenreProfile:
    return GenreProfile(
        id="xuanhuan",
        name="玄幻",
        chapter_types=["开篇", "升级", "战斗"],
        fatigue_words=["冷笑"],
        satisfaction_types=["实力提升"],
        pacing_rule="每章至少一个小高潮",
        writer_rules=["对话简短有力"],
        reviewer_focus=["设定一致性"],
        active_audit_dimensions=["style_ai_tells"],
        taboos=["虐主", "绿帽"],
    )


def _make_mode() -> CreativeModeProfile:
    return CreativeModeProfile(
        id="webnovel",
        name="网文模式",
        enabled_agents={"pre_write": ["goal_planner"]},
        audit_weights={"style_ai_tells": 0.3},
        active_audit_dimensions=["style_ai_tells"],
        revision_policy="standard",
        tolerance={"max_ai_tells": 2.0, "max_fatigue_words": 3.0},
        context_pruning_strategy="default",
    )


def _make_chapter_goal() -> ChapterGoal:
    return ChapterGoal(
        chapter_number=3,
        previous_summary="上一章结尾",
        target_events=["争夺玄天剑"],
        emotional_arc="紧张→爆发",
        hooks=["剑灵开口说话"],
        obligations=["兑现母亲遗愿", "保护师妹"],
        word_count_target=3000,
        chapter_type="战斗",
    )


def _make_creative_brief() -> CreativeBrief:
    return CreativeBrief(
        mode_id="webnovel",
        chapter_goal=_make_chapter_goal(),
        creative_intent="让读者感受到主角在绝境中爆发的爽感",
        required_tensions=[
            Tension(
                tension_id="t1",
                description="主角与反派实力差距",
                tension_type="power_imbalance",
                intensity=0.8,
            )
        ],
        forbidden_patterns=["不要使用'冷笑'"],
        reader_contract="读者应该为主角的逆袭感到振奋",
    )


def _make_characters() -> list[Character]:
    return [
        Character(
            character_id="char_001",
            project_id="proj_123",
            name="林凡",
            role_type="protagonist",
            background="孤儿出身",
            personality_traits=["坚韧"],
            goals=["找到父母"],
            relationships={"师妹": "保护"},
        ),
        Character(
            character_id="char_002",
            project_id="proj_123",
            name="师妹",
            role_type="supporting",
            background="门派弟子",
        ),
    ]


def _make_character_states() -> list[CharacterState]:
    return [
        CharacterState(
            character_id="char_001",
            field="location",
            value="天剑峰",
            source_version_id="v1",
        ),
        CharacterState(
            character_id="char_001",
            field="emotional_state",
            value="愤怒",
            source_version_id="v1",
        ),
        CharacterState(
            character_id="char_002",
            field="location",
            value="天剑峰",
            source_version_id="v1",
        ),
    ]


def _make_summaries() -> list[ChapterSummary]:
    return [
        ChapterSummary(
            chapter_number=1,
            summary="第一章摘要",
            key_events=["事件A"],
            characters_appeared=["林凡", "师妹"],
        ),
        ChapterSummary(
            chapter_number=2,
            summary="第二章摘要",
            key_events=["事件B"],
            characters_appeared=["林凡"],
        ),
    ]


def _make_foreshadowings() -> list[ForeshadowingItem]:
    return [
        ForeshadowingItem(
            foreshadowing_id="fs_001",
            description="神秘老人身份",
            planted_in_chapter=1,
            status="planted",
        ),
        ForeshadowingItem(
            foreshadowing_id="fs_002",
            description="玄天剑秘密",
            planted_in_chapter=2,
            expected_resolve_chapter=5,
            status="due",
        ),
    ]


def _make_settings() -> list[NewSetting]:
    return [
        NewSetting(
            setting_name="玄天剑",
            description="上古神器",
            source_quote="剑身散发着幽蓝光芒",
            setting_key="xuantian_sword",
        ),
    ]


# ---------------------------------------------------------------------------
# TokenEstimator Tests
# ---------------------------------------------------------------------------
class TestTokenEstimator:
    def test_estimate_empty_string(self) -> None:
        est = TokenEstimator()
        assert est.estimate("") == 0

    def test_estimate_non_empty(self) -> None:
        est = TokenEstimator()
        text = "Hello world"
        tokens = est.estimate(text)
        assert tokens > 0
        # 字符数/2 是回退策略的上限
        assert tokens <= max(1, len(text) // 2) or tokens <= len(text)

    def test_estimate_chinese(self) -> None:
        est = TokenEstimator()
        text = "这是一个中文测试"
        tokens = est.estimate(text)
        assert tokens > 0

    def test_estimate_model_pydantic(self) -> None:
        est = TokenEstimator()
        obj = ChapterGoal(chapter_number=1, target_events=["事件A"])
        tokens = est.estimate_model(obj)
        assert tokens > 0

    def test_estimate_model_dict(self) -> None:
        est = TokenEstimator()
        tokens = est.estimate_model({"key": "value", "num": 123})
        assert tokens > 0

    def test_estimate_model_list(self) -> None:
        est = TokenEstimator()
        tokens = est.estimate_model(["a", "b", "c"])
        assert tokens > 0

    def test_estimate_model_none(self) -> None:
        est = TokenEstimator()
        assert est.estimate_model(None) == 0


# ---------------------------------------------------------------------------
# BudgetPruner Tests
# ---------------------------------------------------------------------------
@pytest.mark.performance
class TestBudgetPruner:
    def _make_large_context(self) -> ContextPackage:
        """构造一个超大 ContextPackage 确保会超预算."""
        return ContextPackage(
            chapter_goal=ChapterGoal(chapter_number=1),
            creative_brief=None,
            hard_constraints=[
                HardConstraint(type="taboo", description="x" * 1000, source="test")
                for _ in range(20)
            ],
            character_states=[
                CharacterStateSnapshot(
                    character_id=f"c{i}",
                    name=f"角色{i}",
                    importance_score=0.5 if i > 0 else 1.0,
                )
                for i in range(10)
            ],
            recent_plot=RecentPlot(
                summaries=[
                    ChapterSummary(
                        chapter_number=i,
                        summary="summary" * 500,
                        key_events=["event" * 100],
                    )
                    for i in range(1, 6)
                ],
            ),
            foreshadowing=[
                ForeshadowingItem(
                    foreshadowing_id=f"fs{i}",
                    description="desc" * 200,
                    planted_in_chapter=i,
                    status="planted",
                )
                for i in range(10)
            ],
            soft_references=[
                SoftReference(
                    type="world_setting",
                    content="content" * 300,
                    relevance_score=float(i) / 10,
                )
                for i in range(10)
            ],
            genre_rules=GenreRules(writer_rules=["rule" * 100]),
            mode_rules=ModeRules(),
        )

    def test_no_prune_when_under_budget(self) -> None:
        pruner = BudgetPruner()
        ctx = ContextPackage(
            chapter_goal=ChapterGoal(chapter_number=1),
            hard_constraints=[HardConstraint(type="taboo", description="x", source="test")],
        )
        result = pruner.prune(ctx, 10000)
        assert len(result.hard_constraints) == 1
        assert result.budget_used < 1.0

    def test_prune_soft_references_first(self) -> None:
        pruner = BudgetPruner()
        ctx = self._make_large_context()
        original_soft = len(ctx.soft_references)
        result = pruner.prune(ctx, 2000)
        assert len(result.soft_references) <= original_soft // 2 + 1

    def test_prune_foreshadowing_second(self) -> None:
        pruner = BudgetPruner()
        ctx = self._make_large_context()
        # 添加一个 due 状态的 foreshadowing
        ctx.foreshadowing.insert(
            0,
            ForeshadowingItem(
                foreshadowing_id="fs_due",
                description="due" * 200,
                planted_in_chapter=1,
                status="due",
            ),
        )
        # 构造足够小的预算触发多层裁剪
        result = pruner.prune(ctx, 1500)
        # due/overdue 的 foreshadowing 应优先保留
        due_items = [f for f in result.foreshadowing if f.status in ("due", "overdue")]
        assert len(due_items) > 0 or len(result.foreshadowing) == 0

    def test_prune_recent_plot_third(self) -> None:
        pruner = BudgetPruner()
        ctx = self._make_large_context()
        original_summaries = len(ctx.recent_plot.summaries)
        result = pruner.prune(ctx, 1000)
        assert len(result.recent_plot.summaries) <= max(1, original_summaries // 2)

    def test_prune_character_states_last(self) -> None:
        pruner = BudgetPruner()
        ctx = self._make_large_context()
        result = pruner.prune(ctx, 500)
        # 保留 importance_score 最高的前 N 个（不超过 MAX_CHARACTER_STATES）
        assert len(result.character_states) <= 4
        # 验证保留的是分数最高的
        original_scores = sorted([s.importance_score for s in ctx.character_states], reverse=True)
        kept_scores = sorted([s.importance_score for s in result.character_states], reverse=True)
        assert kept_scores == original_scores[: len(kept_scores)]

    def test_chapter_goal_always_preserved(self) -> None:
        pruner = BudgetPruner()
        ctx = self._make_large_context()
        result = pruner.prune(ctx, 100)
        assert result.chapter_goal.chapter_number == 1

    def test_estimated_tokens_set(self) -> None:
        pruner = BudgetPruner()
        ctx = ContextPackage(chapter_goal=ChapterGoal(chapter_number=1))
        result = pruner.prune(ctx, 10000)
        assert result.estimated_tokens >= 0
        assert result.budget_used >= 0.0

    def test_prune_empty_context(self) -> None:
        pruner = BudgetPruner()
        ctx = ContextPackage(chapter_goal=ChapterGoal(chapter_number=1))
        result = pruner.prune(ctx, 1000)
        assert result.estimated_tokens >= 0
        assert result.budget_used < 1.0

    def test_prune_no_side_effect(self) -> None:
        """prune 不应修改原始 ContextPackage 对象."""
        pruner = BudgetPruner()
        ctx = self._make_large_context()
        original_soft_refs_len = len(ctx.soft_references)
        original_foreshadowing_len = len(ctx.foreshadowing)
        original_character_states_len = len(ctx.character_states)
        original_estimated = ctx.estimated_tokens
        original_budget = ctx.budget_used

        result = pruner.prune(ctx, 1000)

        # result 被正确设置了 estimated_tokens（不强制 <= 1000，
        # 因为 hard_constraints 等核心字段始终保留，极端预算可能无法达标）
        assert result.estimated_tokens is not None
        assert result.budget_used is not None
        # 原始对象未被修改
        assert len(ctx.soft_references) == original_soft_refs_len
        assert len(ctx.foreshadowing) == original_foreshadowing_len
        assert len(ctx.character_states) == original_character_states_len
        assert ctx.estimated_tokens == original_estimated
        assert ctx.budget_used == original_budget


# ---------------------------------------------------------------------------
# Partition Builder Tests
# ---------------------------------------------------------------------------
class TestBuildHardConstraints:
    def test_from_chapter_goal_obligations(self) -> None:
        goal = ChapterGoal(chapter_number=1, obligations=["义务A", "义务B"])
        genre = GenreProfile(id="g", name="测试")
        project = ProjectSetting(genre_id="g", protagonist_name="主角")
        constraints = _build_hard_constraints(goal, genre, project)
        obligations = [c for c in constraints if c.type == "obligation"]
        assert len(obligations) == 2
        assert obligations[0].description == "义务A"

    def test_from_genre_taboos(self) -> None:
        goal = ChapterGoal(chapter_number=1)
        genre = GenreProfile(id="g", name="测试", taboos=["虐主"])
        project = ProjectSetting(genre_id="g", protagonist_name="主角")
        constraints = _build_hard_constraints(goal, genre, project)
        taboos = [c for c in constraints if c.type == "taboo"]
        assert any(c.description == "虐主" for c in taboos)

    def test_from_project_taboos(self) -> None:
        goal = ChapterGoal(chapter_number=1)
        genre = GenreProfile(id="g", name="测试")
        project = ProjectSetting(genre_id="g", protagonist_name="主角", taboos=["绿帽"])
        constraints = _build_hard_constraints(goal, genre, project)
        taboos = [c for c in constraints if c.type == "taboo"]
        assert any(c.description == "绿帽" for c in taboos)

    def test_empty_obligations(self) -> None:
        goal = ChapterGoal(chapter_number=1, obligations=[])
        genre = GenreProfile(id="g", name="测试")
        project = ProjectSetting(genre_id="g", protagonist_name="主角")
        constraints = _build_hard_constraints(goal, genre, project)
        assert len(constraints) == 0

    def test_dynamic_max_obligations_early_chapters(self) -> None:
        obligations = [f"义务{i}" for i in range(15)]
        goal = ChapterGoal(chapter_number=10, obligations=obligations)
        genre = GenreProfile(id="g", name="测试")
        project = ProjectSetting(genre_id="g", protagonist_name="主角")
        constraints = _build_hard_constraints(goal, genre, project)
        obligation_constraints = [c for c in constraints if c.type == "obligation"]
        assert len(obligation_constraints) == 10

    def test_dynamic_max_obligations_late_chapters(self) -> None:
        obligations = [f"义务{i}" for i in range(15)]
        goal = ChapterGoal(chapter_number=90, obligations=obligations)
        genre = GenreProfile(id="g", name="测试")
        project = ProjectSetting(genre_id="g", protagonist_name="主角")
        constraints = _build_hard_constraints(goal, genre, project)
        obligation_constraints = [c for c in constraints if c.type == "obligation"]
        assert len(obligation_constraints) == 6

    def test_human_marks_stay_out_of_hard_constraints(self) -> None:
        goal = ChapterGoal(chapter_number=1)
        genre = GenreProfile(id="g", name="测试")
        project = ProjectSetting(genre_id="g", protagonist_name="主角")
        marks = [
            HumanMark(
                mark_id="m1",
                project_id="p1",
                mark_type="setting",
                target_key="k1",
                note="a" * 100,
                priority=5,
            )
        ]
        constraints = _build_hard_constraints(goal, genre, project, marks)
        mark_constraints = [c for c in constraints if c.type == "human_mark"]
        assert mark_constraints == []

    def test_human_marks_preserved_in_independent_partition(self) -> None:
        goal = ChapterGoal(chapter_number=90)
        genre = GenreProfile(id="g", name="测试")
        project = ProjectSetting(genre_id="g", protagonist_name="主角")
        marks = [
            HumanMark(
                mark_id="m1",
                project_id="p1",
                mark_type="setting",
                target_key="k1",
                note="高优先级标记" * 50,
                priority=10,
            ),
            HumanMark(
                mark_id="m2",
                project_id="p1",
                mark_type="setting",
                target_key="k2",
                note="低优先级标记" * 50,
                priority=3,
            ),
        ]
        ctx = assemble_context_package(
            chapter_goal=goal,
            creative_brief=None,
            genre_profile=genre,
            mode_profile=_make_mode(),
            project=project,
            characters=[],
            character_states=[],
            recent_summaries=[],
            active_foreshadowings=[],
            setting_snapshots=[],
            human_marks=marks,
            budget_tokens=10000,
        )
        assert ctx.human_marks == [marks[0]]
        assert all(c.type != "human_mark" for c in ctx.hard_constraints)


class TestBuildCharacterSnapshots:
    def test_protagonist_importance(self) -> None:
        chars = [
            Character(
                character_id="c1",
                project_id="p1",
                name="主角",
                role_type="protagonist",
            )
        ]
        states: list[CharacterState] = []
        snapshots = _build_character_snapshots(chars, states)
        assert len(snapshots) == 1
        assert snapshots[0].importance_score == 1.0

    def test_supporting_importance(self) -> None:
        chars = [
            Character(
                character_id="c1",
                project_id="p1",
                name="配角",
                role_type="supporting",
            )
        ]
        states: list[CharacterState] = []
        snapshots = _build_character_snapshots(chars, states)
        assert snapshots[0].importance_score == 0.8

    def test_state_mapping(self) -> None:
        chars = [
            Character(
                character_id="c1",
                project_id="p1",
                name="主角",
                role_type="protagonist",
                goals=["找到父母"],
                relationships={"师妹": "保护"},
            )
        ]
        states = [
            CharacterState(
                character_id="c1",
                field="location",
                value="天剑峰",
            ),
            CharacterState(
                character_id="c1",
                field="emotional_state",
                value="愤怒",
            ),
        ]
        snapshots = _build_character_snapshots(chars, states)
        assert snapshots[0].current_location == "天剑峰"
        assert snapshots[0].emotional_state == "愤怒"
        assert "师妹" in snapshots[0].active_relationships
        assert "找到父母" in snapshots[0].unresolved_issues

    def test_multiple_characters(self) -> None:
        chars = _make_characters()
        states = _make_character_states()
        snapshots = _build_character_snapshots(chars, states)
        assert len(snapshots) == 2
        names = {s.name for s in snapshots}
        assert names == {"林凡", "师妹"}


class TestBuildRecentPlot:
    def test_basic(self) -> None:
        summaries = _make_summaries()
        plot = _build_recent_plot(summaries, "上一章结尾", ["线索1"])
        assert len(plot.summaries) == 2
        assert plot.last_chapter_ending == "上一章结尾"
        assert plot.open_threads == ["线索1"]

    def test_empty(self) -> None:
        plot = _build_recent_plot([], "", [])
        assert plot.summaries == []
        assert plot.last_chapter_ending == ""
        assert plot.open_threads == []

    def test_default_open_threads(self) -> None:
        plot = _build_recent_plot([], "")
        assert plot.open_threads == []


class TestBuildSoftReferences:
    def test_from_settings(self) -> None:
        settings = _make_settings()
        refs = _build_soft_references(settings)
        assert len(refs) == 1
        assert refs[0].type == "world_setting"
        assert "玄天剑" in refs[0].content
        assert refs[0].relevance_score == 0.7

    def test_empty(self) -> None:
        refs = _build_soft_references([])
        assert refs == []


class TestBuildGenreRules:
    def test_conversion(self) -> None:
        genre = _make_genre()
        project = ProjectSetting(genre_id="xuanhuan", protagonist_name="林凡")
        goal = _make_chapter_goal()
        rules = _build_genre_rules(genre, project, goal)
        assert rules.genre_id == "xuanhuan"
        assert rules.pacing_rule == "每章至少一个小高潮"
        assert "冷笑" in rules.fatigue_words
        assert rules.sub_genre_rules == []

    def test_sub_genre_rules_injected(self) -> None:
        from songyan.models.genre import SubGenre

        genre = _make_genre()
        genre.sub_genres = [
            SubGenre(
                sub_genre_id="cosmic_horror",
                name="宇宙恐怖",
                differentiation_rules=["强调未知的恐惧", "弱化战斗描写"],
            )
        ]
        project = ProjectSetting(
            genre_id="xuanhuan",
            protagonist_name="林凡",
            sub_genre_id="cosmic_horror",
        )
        goal = _make_chapter_goal()
        rules = _build_genre_rules(genre, project, goal)
        assert rules.sub_genre_rules == ["强调未知的恐惧", "弱化战斗描写"]

    def test_sub_genre_mismatch_ignored(self) -> None:
        from songyan.models.genre import SubGenre

        genre = _make_genre()
        genre.sub_genres = [
            SubGenre(
                sub_genre_id="space_opera",
                name="太空歌剧",
                differentiation_rules=["宏大叙事"],
            )
        ]
        project = ProjectSetting(
            genre_id="xuanhuan",
            protagonist_name="林凡",
            sub_genre_id="cosmic_horror",
        )
        goal = _make_chapter_goal()
        rules = _build_genre_rules(genre, project, goal)
        assert rules.sub_genre_rules == []

    def test_no_sub_genre_id_empty_rules(self) -> None:
        genre = _make_genre()
        project = ProjectSetting(genre_id="xuanhuan", protagonist_name="林凡")
        goal = _make_chapter_goal()
        rules = _build_genre_rules(genre, project, goal)
        assert rules.sub_genre_rules == []


class TestBuildModeRules:
    def test_conversion(self) -> None:
        mode = _make_mode()
        rules = _build_mode_rules(mode)
        assert rules.mode_id == "webnovel"
        assert rules.revision_policy == "standard"
        assert rules.tolerance_max_ai_tells == 2.0
        assert rules.tolerance_max_fatigue_words == 3.0
        assert rules.context_pruning_strategy == "default"

    def test_default_tolerance(self) -> None:
        mode = CreativeModeProfile(id="lite", name="轻量")
        rules = _build_mode_rules(mode)
        assert rules.tolerance_max_ai_tells == 2.0
        assert rules.tolerance_max_fatigue_words == 3.0
        assert rules.tolerance_max_cliche_risk == 2.0


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------
class TestAssembleContextPackage:
    async def test_full_assembly(self) -> None:
        ctx = assemble_context_package(
            chapter_goal=_make_chapter_goal(),
            creative_brief=_make_creative_brief(),
            genre_profile=_make_genre(),
            mode_profile=_make_mode(),
            project=_make_project(),
            characters=_make_characters(),
            character_states=_make_character_states(),
            recent_summaries=_make_summaries(),
            active_foreshadowings=_make_foreshadowings(),
            setting_snapshots=_make_settings(),
            budget_tokens=10000,
        )
        assert ctx.chapter_goal.chapter_number == 3
        assert ctx.creative_brief is not None
        assert len(ctx.hard_constraints) > 0
        assert len(ctx.character_states) == 2
        assert len(ctx.recent_plot.summaries) == 2
        assert len(ctx.foreshadowing) == 2
        assert len(ctx.soft_references) == 1
        assert ctx.genre_rules is not None
        assert ctx.mode_rules is not None
        assert ctx.estimated_tokens >= 0
        assert ctx.budget_used <= 1.0

    async def test_no_creative_brief(self) -> None:
        ctx = assemble_context_package(
            chapter_goal=_make_chapter_goal(),
            creative_brief=None,
            genre_profile=_make_genre(),
            mode_profile=_make_mode(),
            project=_make_project(),
            characters=_make_characters(),
            character_states=[],
            recent_summaries=[],
            active_foreshadowings=[],
            setting_snapshots=[],
            budget_tokens=10000,
        )
        assert ctx.creative_brief is None
        assert ctx.estimated_tokens >= 0

    async def test_low_budget_clamped(self) -> None:
        ctx = assemble_context_package(
            chapter_goal=_make_chapter_goal(),
            creative_brief=None,
            genre_profile=_make_genre(),
            mode_profile=_make_mode(),
            project=_make_project(),
            characters=[],
            character_states=[],
            recent_summaries=[],
            active_foreshadowings=[],
            setting_snapshots=[],
            budget_tokens=100,  # 低于 MIN_BUDGET_TOKENS
        )
        assert ctx.estimated_tokens >= 0
        # budget 被 clamp 到 MIN_BUDGET_TOKENS
        assert ctx.budget_used <= 1.0

    async def test_pruning_with_large_content(self) -> None:
        # 构造大量内容确保触发裁剪
        large_summaries = [
            ChapterSummary(
                chapter_number=i,
                summary="summary" * 500,
                key_events=["event" * 100],
            )
            for i in range(1, 11)
        ]
        large_foreshadowings = [
            ForeshadowingItem(
                foreshadowing_id=f"fs{i}",
                description="desc" * 200,
                planted_in_chapter=i,
                status="planted",
            )
            for i in range(20)
        ]
        large_settings = [
            NewSetting(
                setting_name=f"设定{i}",
                description="desc" * 300,
                source_quote="",
                setting_key=f"key{i}",
            )
            for i in range(20)
        ]
        ctx = assemble_context_package(
            chapter_goal=_make_chapter_goal(),
            creative_brief=_make_creative_brief(),
            genre_profile=_make_genre(),
            mode_profile=_make_mode(),
            project=_make_project(),
            characters=_make_characters(),
            character_states=_make_character_states(),
            recent_summaries=large_summaries,
            active_foreshadowings=large_foreshadowings,
            setting_snapshots=large_settings,
            budget_tokens=15000,
        )
        assert ctx.estimated_tokens >= 0
        # 由于内容很多，应该发生了裁剪，但最终应在预算内或接近预算
        assert ctx.budget_used <= 1.0

    async def test_last_chapter_ending_and_threads(self) -> None:
        ctx = assemble_context_package(
            chapter_goal=_make_chapter_goal(),
            creative_brief=None,
            genre_profile=_make_genre(),
            mode_profile=_make_mode(),
            project=_make_project(),
            characters=[],
            character_states=[],
            recent_summaries=[],
            active_foreshadowings=[],
            setting_snapshots=[],
            budget_tokens=10000,
            last_chapter_ending="主角拔出玄天剑",
            recent_plot_threads=["剑灵身份", "反派阴谋"],
        )
        assert ctx.recent_plot.last_chapter_ending == "主角拔出玄天剑"
        assert ctx.recent_plot.open_threads == ["剑灵身份", "反派阴谋"]
        assert ctx.recent_plot.open_threads == ["剑灵身份", "反派阴谋"]


# ---------------------------------------------------------------------------
# Phase 7: Human Mark Tests
# ---------------------------------------------------------------------------
class TestHumanMarksInContext:
    def test_high_priority_marks_enter_context(self) -> None:
        marks = [
            HumanMark(
                mark_id="m1", project_id="p1", mark_type="setting", target_key="A", priority=9
            ),
            HumanMark(
                mark_id="m2", project_id="p1", mark_type="character", target_key="B", priority=5
            ),
        ]
        ctx = assemble_context_package(
            chapter_goal=_make_chapter_goal(),
            creative_brief=None,
            genre_profile=_make_genre(),
            mode_profile=_make_mode(),
            project=_make_project(),
            characters=[],
            character_states=[],
            recent_summaries=[],
            active_foreshadowings=[],
            setting_snapshots=[],
            budget_tokens=10000,
            human_marks=marks,
        )
        # priority >= 8 (default threshold) enters context
        assert len(ctx.human_marks) == 1
        assert ctx.human_marks[0].mark_id == "m1"

    def test_marks_not_converted_to_hard_constraints(self) -> None:
        marks = [
            HumanMark(
                mark_id="m1",
                project_id="p1",
                mark_type="setting",
                target_key="核心道具",
                priority=9,
            ),
        ]
        ctx = assemble_context_package(
            chapter_goal=_make_chapter_goal(),
            creative_brief=None,
            genre_profile=_make_genre(),
            mode_profile=_make_mode(),
            project=_make_project(),
            characters=[],
            character_states=[],
            recent_summaries=[],
            active_foreshadowings=[],
            setting_snapshots=[],
            budget_tokens=10000,
            human_marks=marks,
        )
        hm_constraints = [c for c in ctx.hard_constraints if c.type == "human_mark"]
        assert hm_constraints == []
        assert len(ctx.human_marks) == 1
        assert ctx.human_marks[0].target_key == "核心道具"

    def test_marks_respect_mode_threshold(self) -> None:
        mode = CreativeModeProfile(
            id="literary",
            name="文学模式",
            human_memory={"priority_threshold": 7, "max_marks_in_context": 10},
        )
        marks = [
            HumanMark(
                mark_id="m1", project_id="p1", mark_type="setting", target_key="A", priority=6
            ),
            HumanMark(
                mark_id="m2", project_id="p1", mark_type="setting", target_key="B", priority=7
            ),
        ]
        ctx = assemble_context_package(
            chapter_goal=_make_chapter_goal(),
            creative_brief=None,
            genre_profile=_make_genre(),
            mode_profile=mode,
            project=_make_project(),
            characters=[],
            character_states=[],
            recent_summaries=[],
            active_foreshadowings=[],
            setting_snapshots=[],
            budget_tokens=10000,
            human_marks=marks,
        )
        assert len(ctx.human_marks) == 1
        assert ctx.human_marks[0].mark_id == "m2"

    def test_marks_respect_max_count(self) -> None:
        mode = CreativeModeProfile(
            id="webnovel",
            name="网文",
            human_memory={"priority_threshold": 5, "max_marks_in_context": 3},
        )
        marks = [
            HumanMark(
                mark_id=f"m{i}",
                project_id="p1",
                mark_type="setting",
                target_key=f"K{i}",
                priority=10 - i,
            )
            for i in range(1, 6)
        ]
        ctx = assemble_context_package(
            chapter_goal=_make_chapter_goal(),
            creative_brief=None,
            genre_profile=_make_genre(),
            mode_profile=mode,
            project=_make_project(),
            characters=[],
            character_states=[],
            recent_summaries=[],
            active_foreshadowings=[],
            setting_snapshots=[],
            budget_tokens=10000,
            human_marks=marks,
        )
        assert len(ctx.human_marks) <= 3

    def test_no_marks_when_none_provided(self) -> None:
        ctx = assemble_context_package(
            chapter_goal=_make_chapter_goal(),
            creative_brief=None,
            genre_profile=_make_genre(),
            mode_profile=_make_mode(),
            project=_make_project(),
            characters=[],
            character_states=[],
            recent_summaries=[],
            active_foreshadowings=[],
            setting_snapshots=[],
            budget_tokens=10000,
        )
        assert ctx.human_marks == []
        assert not any(c.type == "human_mark" for c in ctx.hard_constraints)


# ---------------------------------------------------------------------------
# Task 098: 四信号系统测试
# ---------------------------------------------------------------------------
class TestRankForeshadowings:
    def test_due_list_gets_highest_priority(self) -> None:
        items = [
            ForeshadowingItem(
                foreshadowing_id="fs1", description="a", planted_in_chapter=1, status="planted"
            ),
            ForeshadowingItem(
                foreshadowing_id="fs2", description="b", planted_in_chapter=2, status="planted"
            ),
            ForeshadowingItem(
                foreshadowing_id="fs3", description="c", planted_in_chapter=3, status="planted"
            ),
        ]
        result = _rank_foreshadowings(items, foreshadowing_due=["fs2"], current_chapter=5)
        assert result[0].foreshadowing_id == "fs2"

    def test_overdue_gets_high_priority(self) -> None:
        items = [
            ForeshadowingItem(
                foreshadowing_id="fs1", description="a", planted_in_chapter=1, status="planted"
            ),
            ForeshadowingItem(
                foreshadowing_id="fs2", description="b", planted_in_chapter=2, status="overdue"
            ),
        ]
        result = _rank_foreshadowings(items, foreshadowing_due=[], current_chapter=5)
        assert result[0].foreshadowing_id == "fs2"

    def test_due_chapter_near_gets_priority(self) -> None:
        items = [
            ForeshadowingItem(
                foreshadowing_id="fs1", description="a", planted_in_chapter=1, status="planted"
            ),
            ForeshadowingItem(
                foreshadowing_id="fs2",
                description="b",
                planted_in_chapter=2,
                status="planted",
                expected_resolve_chapter=5,
            ),
        ]
        result = _rank_foreshadowings(items, foreshadowing_due=[], current_chapter=4)
        assert result[0].foreshadowing_id == "fs2"

    def test_returns_all_items_when_no_due(self) -> None:
        items = [
            ForeshadowingItem(
                foreshadowing_id="fs1", description="a", planted_in_chapter=1, status="planted"
            ),
            ForeshadowingItem(
                foreshadowing_id="fs2", description="b", planted_in_chapter=2, status="planted"
            ),
        ]
        result = _rank_foreshadowings(items, foreshadowing_due=[], current_chapter=5)
        assert len(result) == 2


class TestBudgetPrunerFourSignals:
    def test_narrative_fullness_reduces_limits(self) -> None:
        pruner = BudgetPruner()
        ctx = ContextPackage(
            chapter_goal=ChapterGoal(chapter_number=1),
            soft_references=[
                SoftReference(
                    type="world_setting",
                    content=f"设定{i}",
                    relevance_score=0.5 + i * 0.05,
                )
                for i in range(10)
            ],
        )
        # fullness=0.0 → factor=1.0 → max_soft=10
        result_low = pruner.prune(ctx, 100000, narrative_fullness=0.0)
        assert len(result_low.soft_references) == 10

        # Task 104: fullness=1.0 → factor=0.3 → max_soft=3
        result_high = pruner.prune(ctx, 100000, narrative_fullness=1.0)
        assert len(result_high.soft_references) == 3

    def test_focal_distance_close_limits_refs(self) -> None:
        pruner = BudgetPruner()
        ctx = ContextPackage(
            chapter_goal=ChapterGoal(chapter_number=1),
            soft_references=[
                SoftReference(
                    type="world_setting",
                    content=f"设定{i}",
                    relevance_score=0.9 - i * 0.05,
                )
                for i in range(10)
            ],
        )
        result = pruner.prune(ctx, 100000, focal_distance="close")
        assert len(result.soft_references) <= 3

    def test_focal_distance_wide_compresses_chars(self) -> None:
        pruner = BudgetPruner()
        ctx = ContextPackage(
            chapter_goal=ChapterGoal(chapter_number=1),
            character_states=[
                CharacterStateSnapshot(
                    character_id="c1",
                    name="主角",
                    importance_score=1.0,
                    current_location="A",
                    current_cultivation="B",
                    emotional_state="C",
                ),
                CharacterStateSnapshot(
                    character_id="c2",
                    name="配角1",
                    importance_score=0.8,
                    current_location="A",
                    current_cultivation="B",
                    emotional_state="C",
                ),
                CharacterStateSnapshot(
                    character_id="c3",
                    name="配角2",
                    importance_score=0.7,
                    current_location="A",
                    current_cultivation="B",
                    emotional_state="C",
                ),
            ],
        )
        result = pruner.prune(ctx, 100000, focal_distance="wide")
        assert len(result.character_states) <= 2

    def test_focal_distance_disruption_truncates(self) -> None:
        pruner = BudgetPruner()
        ctx = ContextPackage(
            chapter_goal=ChapterGoal(chapter_number=1),
            soft_references=[
                SoftReference(type="world_setting", content=f"设定{i}", relevance_score=0.9)
                for i in range(6)
            ],
            foreshadowing=[
                ForeshadowingItem(foreshadowing_id=f"fs{i}", description="a", planted_in_chapter=i)
                for i in range(5)
            ],
        )
        result = pruner.prune(ctx, 100000, focal_distance="disruption")
        # disruption 会截断一半 soft_references
        assert len(result.soft_references) <= 3


class TestCharacterFocusSnapshots:
    def test_focus_full_uses_full_snapshot(self) -> None:
        chars = [
            Character(
                character_id="c1",
                name="主角",
                role_type="protagonist",
                relationships={},
                goals=[],
                project_id="p1",
            ),
            Character(
                character_id="c2",
                name="配角",
                role_type="supporting",
                relationships={},
                goals=[],
                project_id="p1",
            ),
        ]
        states = [
            CharacterState(character_id="c1", field="location", value="山门"),
            CharacterState(character_id="c2", field="location", value="城镇"),
        ]
        focus = [{"character_id": "c2", "detail_level": "full"}]
        snapshots = _build_character_snapshots(chars, states, character_focus=focus)
        snap_c2 = next((s for s in snapshots if s.character_id == "c2"), None)
        assert snap_c2 is not None
        assert snap_c2.current_location == "城镇"
        assert snap_c2.importance_score >= 0.8

    def test_focus_compressed_uses_minimal_snapshot(self) -> None:
        chars = [
            Character(
                character_id="c1",
                name="主角",
                role_type="protagonist",
                relationships={},
                goals=[],
                project_id="p1",
            ),
            Character(
                character_id="c2",
                name="配角",
                role_type="supporting",
                relationships={},
                goals=[],
                project_id="p1",
            ),
        ]
        states = [
            CharacterState(character_id="c1", field="location", value="山门"),
            CharacterState(character_id="c2", field="location", value="城镇"),
            CharacterState(character_id="c2", field="emotional_state", value="焦虑"),
        ]
        focus = [{"character_id": "c2", "detail_level": "compressed"}]
        snapshots = _build_character_snapshots(chars, states, character_focus=focus)
        snap_c2 = next((s for s in snapshots if s.character_id == "c2"), None)
        assert snap_c2 is not None
        assert snap_c2.active_relationships == []
        assert snap_c2.unresolved_issues == []
        assert "焦虑" in (snap_c2.emotional_state or "")

    def test_focus_skip_excludes_character(self) -> None:
        chars = [
            Character(
                character_id="c1",
                name="主角",
                role_type="protagonist",
                relationships={},
                goals=[],
                project_id="p1",
            ),
            Character(
                character_id="c2",
                name="配角",
                role_type="supporting",
                relationships={},
                goals=[],
                project_id="p1",
            ),
        ]
        states = [
            CharacterState(character_id="c1", field="location", value="山门"),
            CharacterState(character_id="c2", field="location", value="城镇"),
        ]
        focus = [{"character_id": "c2", "detail_level": "skip"}]
        snapshots = _build_character_snapshots(chars, states, character_focus=focus)
        assert not any(s.character_id == "c2" for s in snapshots)
        assert any(s.character_id == "c1" for s in snapshots)

    def test_no_focus_fallback_to_arc_logic(self) -> None:
        chars = [
            Character(
                character_id="c1",
                name="主角",
                role_type="protagonist",
                relationships={},
                goals=[],
                project_id="p1",
            ),
        ]
        states = [CharacterState(character_id="c1", field="location", value="山门")]
        snapshots = _build_character_snapshots(chars, states, character_focus=None)
        assert len(snapshots) == 1
        assert snapshots[0].current_location == "山门"


# ---------------------------------------------------------------------------
# Task 110c Tests
# ---------------------------------------------------------------------------
class TestDynamicMaxForChapter:
    def test_early_chapter_uses_default_caps(self) -> None:
        caps = _dynamic_max_for_chapter(50)
        assert caps["max_setting_input"] == 10
        assert caps["max_foreshadowing"] == 8
        assert caps["max_character_states"] == 4

    def test_late_chapter_tightens_caps(self) -> None:
        caps = _dynamic_max_for_chapter(90)
        assert caps["max_setting_input"] == 6
        assert caps["max_foreshadowing"] == 5
        assert caps["max_character_states"] == 3

    def test_boundary_at_chapter_80(self) -> None:
        caps = _dynamic_max_for_chapter(80)
        assert caps["max_setting_input"] == 10
        assert caps["max_foreshadowing"] == 8
        assert caps["max_character_states"] == 4


class TestContextEmergencyLevels:
    def _make_ctx(self) -> ContextPackage:
        return ContextPackage(
            chapter_goal=ChapterGoal(chapter_number=1),
            character_states=[
                CharacterStateSnapshot(
                    character_id=f"c{i}",
                    name=f"角色{i}",
                    importance_score=1.0 if i == 0 else 0.8 if i == 1 else 0.5,
                )
                for i in range(5)
            ],
            soft_references=[
                SoftReference(
                    type="world_setting",
                    content=f"设定{i}",
                    relevance_score=float(10 - i),
                    is_critical=(i == 0),
                )
                for i in range(10)
            ],
            foreshadowing=[
                ForeshadowingItem(
                    foreshadowing_id=f"fs{i}",
                    description="desc",
                    planted_in_chapter=i,
                    status="planted" if i < 3 else "due" if i < 5 else "overdue",
                )
                for i in range(8)
            ],
            open_threads=[],
            permanent_scenes=[],
        )

    def test_emergency_uses_final_hard_cut_for_level1_range(self) -> None:
        pruner = BudgetPruner()
        ctx = self._make_ctx()
        before = pruner._estimate_package(ctx)
        budget = max(1, int(before / 1.1))
        ctx = pruner._context_emergency(ctx, budget)
        assert ctx.context_emergency is True
        assert ctx.context_emergency_level == 3
        assert len(ctx.character_states) == 1
        assert ctx.soft_references == []
        assert ctx.foreshadowing == []

    def test_emergency_uses_final_hard_cut_for_level2_range(self) -> None:
        pruner = BudgetPruner()
        ctx = self._make_ctx()
        before = pruner._estimate_package(ctx)
        budget = max(1, int(before / 1.35))
        ctx = pruner._context_emergency(ctx, budget)
        assert ctx.context_emergency_level == 3
        assert len(ctx.character_states) == 1
        assert ctx.soft_references == []
        assert ctx.foreshadowing == []

    def test_level3_nuclear_mode(self) -> None:
        pruner = BudgetPruner()
        ctx = self._make_ctx()
        # 让 budget_used > 1.5 触发 Level 3
        before = pruner._estimate_package(ctx)
        budget = max(1, int(before / 2.0))
        ctx = pruner._context_emergency(ctx, budget)
        assert ctx.context_emergency_level == 3
        assert ctx.arc_context is None
        assert ctx.volume_context is None
        assert len(ctx.character_states) == 1
        assert len(ctx.soft_references) == 0
        assert len(ctx.foreshadowing) == 0
        assert ctx.recent_plot.summaries == []


class TestPartitionBudgets:
    def test_character_states_compressed_when_over_budget(self) -> None:
        pruner = BudgetPruner()
        ctx = ContextPackage(
            chapter_goal=ChapterGoal(chapter_number=1),
            character_states=[
                CharacterStateSnapshot(
                    character_id=f"c{i}",
                    name=f"角色{i}",
                    importance_score=float(10 - i),
                )
                for i in range(20)
            ],
        )
        ctx = pruner._apply_partition_budgets(ctx, 100)
        # 20 -> max(1, int(20 * 0.7)) = 14
        assert len(ctx.character_states) <= 14

    def test_recent_plot_halved_when_over_budget(self) -> None:
        pruner = BudgetPruner()
        ctx = ContextPackage(
            chapter_goal=ChapterGoal(chapter_number=1),
            recent_plot=RecentPlot(
                summaries=[
                    ChapterSummary(chapter_number=i, summary="summary" * 200) for i in range(1, 11)
                ]
            ),
        )
        ctx = pruner._apply_partition_budgets(ctx, 100)
        # 10 -> max(1, 10 // 2) = 5
        assert len(ctx.recent_plot.summaries) <= 5

    def test_soft_refs_sorted_and_trimmed(self) -> None:
        pruner = BudgetPruner()
        ctx = ContextPackage(
            chapter_goal=ChapterGoal(chapter_number=1),
            soft_references=[
                SoftReference(
                    type="world_setting",
                    content=f"设定{i}",
                    relevance_score=float(i),
                )
                for i in range(20)
            ],
        )
        ctx = pruner._apply_partition_budgets(ctx, 100)
        # 20 -> max(1, int(20 * 0.6)) = 12
        assert len(ctx.soft_references) <= 12
        # 验证按 relevance_score 降序
        scores = [r.relevance_score for r in ctx.soft_references]
        assert scores == sorted(scores, reverse=True)

    def test_foreshadowing_keeps_due_overdue_first(self) -> None:
        pruner = BudgetPruner()
        ctx = ContextPackage(
            chapter_goal=ChapterGoal(chapter_number=1),
            foreshadowing=[
                ForeshadowingItem(
                    foreshadowing_id=f"fs{i}",
                    description="desc",
                    planted_in_chapter=i,
                    status="planted" if i < 5 else "due",
                )
                for i in range(10)
            ],
        )
        ctx = pruner._apply_partition_budgets(ctx, 100)
        due_items = [f for f in ctx.foreshadowing if f.status == "due"]
        assert len(due_items) == 5  # 所有 due 都保留


class TestArcCharacterSkip:
    def test_non_arc_supporting_character_skipped(self) -> None:
        chars = [
            Character(
                character_id="c1",
                name="主角",
                role_type="protagonist",
                relationships={},
                goals=[],
                project_id="p1",
            ),
            Character(
                character_id="c2",
                name="路人甲",
                role_type="supporting",
                relationships={},
                goals=[],
                project_id="p1",
            ),
        ]
        states = [
            CharacterState(character_id="c1", field="location", value="山门"),
            CharacterState(character_id="c2", field="location", value="山下"),
        ]
        summaries = [
            ChapterSummary(
                chapter_number=1,
                summary="第一章",
                characters_appeared=["主角"],
            ),
        ]
        snapshots = _build_character_snapshots(
            chars,
            states,
            recent_summaries=summaries,
            arc_boundaries=[5, 10],
            current_chapter=2,
        )
        assert len(snapshots) == 1
        assert snapshots[0].character_id == "c1"

    def test_non_arc_antagonist_kept(self) -> None:
        chars = [
            Character(
                character_id="c1",
                name="反派",
                role_type="antagonist",
                relationships={},
                goals=[],
                project_id="p1",
            ),
        ]
        states = [CharacterState(character_id="c1", field="location", value="魔宫")]
        summaries = [
            ChapterSummary(
                chapter_number=1,
                summary="第一章",
                characters_appeared=["主角"],
            ),
        ]
        snapshots = _build_character_snapshots(
            chars,
            states,
            recent_summaries=summaries,
            arc_boundaries=[5, 10],
            current_chapter=2,
        )
        assert len(snapshots) == 1
        assert snapshots[0].character_id == "c1"

    def test_arc_character_kept(self) -> None:
        chars = [
            Character(
                character_id="c1",
                name="主角",
                role_type="protagonist",
                relationships={},
                goals=[],
                project_id="p1",
            ),
            Character(
                character_id="c2",
                name="师妹",
                role_type="supporting",
                relationships={},
                goals=[],
                project_id="p1",
            ),
        ]
        states = [
            CharacterState(character_id="c1", field="location", value="山门"),
            CharacterState(character_id="c2", field="location", value="山门"),
        ]
        summaries = [
            ChapterSummary(
                chapter_number=1,
                summary="第一章",
                characters_appeared=["主角", "师妹"],
            ),
        ]
        snapshots = _build_character_snapshots(
            chars,
            states,
            recent_summaries=summaries,
            arc_boundaries=[5, 10],
            current_chapter=2,
        )
        assert len(snapshots) == 2


class TestAssembleContextPackage110c:
    def test_soft_refs_filtered_by_keywords(self) -> None:
        goal = ChapterGoal(
            chapter_number=3,
            target_events=["争夺玄天剑"],
            hooks=["剑灵开口"],
        )
        settings = [
            NewSetting(
                setting_name="玄天剑",
                description="上古神器",
                source_quote="剑身散发着幽蓝光芒",
                setting_key="item.xuantian.sword",
            ),
            NewSetting(
                setting_name="魔道法器",
                description="邪恶法器",
                source_quote="散发着黑气",
                setting_key="item.demonic.artifact",
            ),
        ]
        pkg = assemble_context_package(
            chapter_goal=goal,
            creative_brief=None,
            genre_profile=_make_genre(),
            mode_profile=_make_mode(),
            project=_make_project(),
            characters=_make_characters(),
            character_states=_make_character_states(),
            recent_summaries=_make_summaries(),
            active_foreshadowings=_make_foreshadowings(),
            setting_snapshots=settings,
            budget_tokens=20000,
        )
        # 玄天剑应该在关键词过滤后保留（因为 setting_name 包含"玄天剑"）
        # 魔道法器应该被过滤掉（与 target_events/hooks 无关）
        names = [s.content for s in pkg.soft_references]
        assert any("玄天剑" in n for n in names)
        assert not any("魔道法器" in n for n in names)

    def test_foreshadowings_filtered_by_due_and_max(self) -> None:
        foreshadowings = [
            ForeshadowingItem(
                foreshadowing_id="fs_due",
                description="即将揭晓的秘密",
                planted_in_chapter=1,
                status="due",
            ),
            ForeshadowingItem(
                foreshadowing_id="fs_planted_1",
                description="普通伏笔1",
                planted_in_chapter=5,
                status="planted",
            ),
            ForeshadowingItem(
                foreshadowing_id="fs_planted_2",
                description="普通伏笔2",
                planted_in_chapter=6,
                status="planted",
            ),
        ]
        goal = ChapterGoal(chapter_number=10, target_events=["事件A"])
        pkg = assemble_context_package(
            chapter_goal=goal,
            creative_brief=None,
            genre_profile=_make_genre(),
            mode_profile=_make_mode(),
            project=_make_project(),
            characters=_make_characters(),
            character_states=_make_character_states(),
            recent_summaries=_make_summaries(),
            active_foreshadowings=foreshadowings,
            setting_snapshots=[],
            budget_tokens=20000,
        )
        ids = {f.foreshadowing_id for f in pkg.foreshadowing}
        assert "fs_due" in ids
        # 非 due 的最多保留到 max_foreshadowing - due_count
        # 对于 Ch10 (<=80)，max_foreshadowing=8，所以 planted 可以保留
        assert len(pkg.foreshadowing) <= 8

    def test_chapter_90_uses_tightened_caps(self) -> None:
        goal = ChapterGoal(chapter_number=90, target_events=["事件A"])
        foreshadowings = [
            ForeshadowingItem(
                foreshadowing_id=f"fs{i}",
                description="desc",
                planted_in_chapter=i,
                status="planted",
            )
            for i in range(1, 12)
        ]
        pkg = assemble_context_package(
            chapter_goal=goal,
            creative_brief=None,
            genre_profile=_make_genre(),
            mode_profile=_make_mode(),
            project=_make_project(),
            characters=_make_characters(),
            character_states=_make_character_states(),
            recent_summaries=_make_summaries(),
            active_foreshadowings=foreshadowings,
            setting_snapshots=[],
            budget_tokens=20000,
        )
        # Ch90 的 max_foreshadowing=5
        assert len(pkg.foreshadowing) <= 5
