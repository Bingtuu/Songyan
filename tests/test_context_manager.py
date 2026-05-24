"""Tests for ContextManager Agent."""

from __future__ import annotations

from songyan.agents.context_manager import (
    BudgetPruner,
    TokenEstimator,
    _build_character_snapshots,
    _build_genre_rules,
    _build_hard_constraints,
    _build_mode_rules,
    _build_recent_plot,
    _build_soft_references,
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
        ChapterSummary(chapter_number=1, summary="第一章摘要", key_events=["事件A"]),
        ChapterSummary(chapter_number=2, summary="第二章摘要", key_events=["事件B"]),
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
        # 只保留 importance_score >= 0.8 的
        for s in result.character_states:
            assert s.importance_score >= 0.8

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
        project = ProjectSetting(
            genre_id="g", protagonist_name="主角", taboos=["绿帽"]
        )
        constraints = _build_hard_constraints(goal, genre, project)
        taboos = [c for c in constraints if c.type == "taboo"]
        assert any(c.description == "绿帽" for c in taboos)

    def test_empty_obligations(self) -> None:
        goal = ChapterGoal(chapter_number=1, obligations=[])
        genre = GenreProfile(id="g", name="测试")
        project = ProjectSetting(genre_id="g", protagonist_name="主角")
        constraints = _build_hard_constraints(goal, genre, project)
        assert len(constraints) == 0


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
        rules = _build_genre_rules(genre)
        assert rules.genre_id == "xuanhuan"
        assert rules.pacing_rule == "每章至少一个小高潮"
        assert "冷笑" in rules.fatigue_words


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
        ctx = await assemble_context_package(
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
        ctx = await assemble_context_package(
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
        ctx = await assemble_context_package(
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
        ctx = await assemble_context_package(
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
        ctx = await assemble_context_package(
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
            open_threads=["剑灵身份", "反派阴谋"],
        )
        assert ctx.recent_plot.last_chapter_ending == "主角拔出玄天剑"
        assert ctx.recent_plot.open_threads == ["剑灵身份", "反派阴谋"]
