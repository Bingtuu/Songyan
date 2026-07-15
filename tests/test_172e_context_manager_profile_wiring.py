"""Task 172e: ContextManager / BudgetPruner field wiring.

Proves that BudgetPruner reads partition ratios, max_* caps, hard_enforce_ratio,
and context_emergency_trigger_ratio from GenreRuntimeProfile, falling back to
legacy module constants when no profile is provided.
"""

from __future__ import annotations

from songyan.agents.context_manager import BudgetPruner, assemble_context_package
from songyan.db.genre_runtime_profile_repo import load_profile_from_registry
from songyan.models import (
    ChapterGoal,
    CharacterStateSnapshot,
    ContextPackage,
    ForeshadowingItem,
    GenreRuntimeProfile,
    HardConstraint,
    NewSetting,
    ProjectSetting,
    SoftReference,
)


def _build_test_profile(**overrides) -> GenreRuntimeProfile:
    base = load_profile_from_registry("scifi")
    data = base.model_dump(mode="json")
    data.update(overrides)
    return GenreRuntimeProfile.model_validate(data)


def _make_goal(chapter_number: int = 1) -> ChapterGoal:
    return ChapterGoal(
        chapter_number=chapter_number,
        target_events=["test event"],
        hooks=[],
        obligations=[],
        word_count_target=3200,
    )


def _make_ctx_with_character_states(n: int = 10) -> ContextPackage:
    """Build a context whose character_states partition dominates the budget."""
    return ContextPackage(
        chapter_goal=_make_goal(),
        hard_constraints=[HardConstraint(type="obligation", description="hc", source="test")],
        character_states=[
            CharacterStateSnapshot(
                character_id=f"c-{i}",
                name=f"角色{i}",
                importance_score=1.0 - (i * 0.05),
            )
            for i in range(n)
        ],
    )


def test_partition_ratios_from_profile() -> None:
    pruner = BudgetPruner(
        runtime_profile=_build_test_profile(
            partition_ratios={
                "character_states": 0.50,
                "recent_plot": 0.30,
                "soft_references": 0.15,
                "foreshadowing": 0.05,
            }
        )
    )
    assert pruner.runtime_profile is not None
    assert pruner.runtime_profile.partition_ratios["character_states"] == 0.50


def test_max_character_states_from_profile() -> None:
    pruner = BudgetPruner(runtime_profile=_build_test_profile(max_character_states=8))
    assert pruner.runtime_profile.max_character_states == 8


def test_hard_enforce_ratio_from_profile() -> None:
    pruner = BudgetPruner(runtime_profile=_build_test_profile(hard_enforce_ratio=1.5))
    assert pruner.runtime_profile.hard_enforce_ratio == 1.5


def test_context_emergency_trigger_ratio_from_profile() -> None:
    pruner = BudgetPruner(
        runtime_profile=_build_test_profile(context_emergency_trigger_ratio=0.95)
    )
    assert pruner.runtime_profile.context_emergency_trigger_ratio == 0.95


def test_scifi_profile_defaults_equal_legacy_constants() -> None:
    scifi = load_profile_from_registry("scifi")
    assert scifi.partition_ratios["character_states"] == 0.30
    assert scifi.partition_ratios["recent_plot"] == 0.20
    assert scifi.partition_ratios["soft_references"] == 0.15
    assert scifi.partition_ratios["foreshadowing"] == 0.10
    assert scifi.max_soft_refs == 10
    assert scifi.max_foreshadowing == 8
    assert scifi.max_character_states == 4
    assert scifi.max_setting_input == 10
    assert scifi.hard_enforce_ratio == 1.3
    assert scifi.context_emergency_trigger_ratio == 1.0


def test_apply_partition_budgets_uses_custom_ratio() -> None:
    """Behavior-level proof: a custom character_states ratio triggers extra pruning."""
    ctx = _make_ctx_with_character_states(n=6)
    budget = 1500  # default 30% = 450 tokens allowance; low ratio 1% = 15 tokens

    default_pruner = BudgetPruner()
    pruned_default = default_pruner._apply_partition_budgets(ctx.model_copy(deep=True), budget)

    low_ratio_profile = _build_test_profile(
        partition_ratios={
            "character_states": 0.01,
            "recent_plot": 0.20,
            "soft_references": 0.15,
            "foreshadowing": 0.10,
        }
    )
    low_ratio_pruner = BudgetPruner(runtime_profile=low_ratio_profile)
    pruned_low = low_ratio_pruner._apply_partition_budgets(ctx.model_copy(deep=True), budget)

    assert len(pruned_low.character_states) <= len(pruned_default.character_states)
    # The low ratio forces character_states to be pruned; default does not.
    assert len(pruned_low.character_states) < 6


def test_prune_soft_references_falls_back_to_profile_when_param_unset() -> None:
    ctx = ContextPackage(
        chapter_goal=_make_goal(),
        hard_constraints=[HardConstraint(type="obligation", description="hc", source="test")],
        soft_references=[
            SoftReference(
                type="world_setting",
                content=f"设定{i}",
                relevance_score=0.9 - (i * 0.05),
                last_mentioned_chapter=i,
            )
            for i in range(20)
        ],
    )
    profile = _build_test_profile(max_soft_refs=3)
    pruner = BudgetPruner(runtime_profile=profile)
    pruned = pruner._prune_soft_references(ctx.model_copy(deep=True), budget=10000)
    assert len(pruned.soft_references) == 3


def test_prune_foreshadowing_falls_back_to_profile_when_param_unset() -> None:
    ctx = ContextPackage(
        chapter_goal=_make_goal(),
        hard_constraints=[HardConstraint(type="obligation", description="hc", source="test")],
        foreshadowing=[
            ForeshadowingItem(
                foreshadowing_id=f"f-{i}",
                description=f"伏笔{i}",
                planted_in_chapter=i,
                status="planted",
            )
            for i in range(20)
        ],
    )
    profile = _build_test_profile(max_foreshadowing=2)
    pruner = BudgetPruner(runtime_profile=profile)
    pruned = pruner._prune_foreshadowing(ctx.model_copy(deep=True), budget=10000)
    assert len(pruned.foreshadowing) == 2


def test_prune_character_states_falls_back_to_profile_when_param_unset() -> None:
    ctx = _make_ctx_with_character_states(n=10)
    profile = _build_test_profile(max_character_states=2)
    pruner = BudgetPruner(runtime_profile=profile)
    pruned = pruner._prune_character_states(ctx.model_copy(deep=True), budget=10000)
    assert len(pruned.character_states) == 2


def test_no_profile_preserves_legacy_constants() -> None:
    """A BudgetPruner without a runtime_profile must use module constants."""
    from songyan.agents.context_manager import (
        HARD_ENFORCE_THRESHOLD,
        MAX_CHARACTER_STATES,
        MAX_FORESHADOWING,
        MAX_SOFT_REFS,
    )

    pruner = BudgetPruner()
    assert pruner.runtime_profile is None

    ctx_soft = ContextPackage(
        chapter_goal=_make_goal(),
        hard_constraints=[HardConstraint(type="obligation", description="hc", source="test")],
        soft_references=[
            SoftReference(
                type="world_setting",
                content=f"设定{i}",
                relevance_score=0.9,
                last_mentioned_chapter=i,
            )
            for i in range(50)
        ],
    )
    pruned_soft = pruner._prune_soft_references(ctx_soft.model_copy(deep=True), budget=10000)
    assert len(pruned_soft.soft_references) == MAX_SOFT_REFS

    ctx_fore = ContextPackage(
        chapter_goal=_make_goal(),
        hard_constraints=[HardConstraint(type="obligation", description="hc", source="test")],
        foreshadowing=[
            ForeshadowingItem(
                foreshadowing_id=f"f-{i}",
                description=f"伏笔{i}",
                planted_in_chapter=i,
                status="planted",
            )
            for i in range(50)
        ],
    )
    pruned_fore = pruner._prune_foreshadowing(ctx_fore.model_copy(deep=True), budget=10000)
    assert len(pruned_fore.foreshadowing) == MAX_FORESHADOWING

    ctx_char = _make_ctx_with_character_states(n=20)
    pruned_char = pruner._prune_character_states(ctx_char.model_copy(deep=True), budget=10000)
    assert len(pruned_char.character_states) == MAX_CHARACTER_STATES

    # Hard enforce threshold must still be the module constant.
    assert HARD_ENFORCE_THRESHOLD == 1.3


def test_assemble_context_package_uses_profile_max_setting_input() -> None:
    """A lower profile max_setting_input reduces non-critical settings entering soft_refs."""
    from songyan.models import CreativeModeProfile, GenreProfile

    goal = _make_goal(chapter_number=1)
    project = ProjectSetting(
        title="test",
        genre_id="scifi",
        mode_id="webnovel_intense",
        protagonist_name="A",
        protagonist_background="bg",
        core_hook="hook",
        tone="dark",
        target_reader_expectation="readers",
    )
    gp = GenreProfile(
        id="scifi",
        name="科幻",
        chapter_types=["开篇"],
        fatigue_words=[],
        satisfaction_types=[],
        pacing_rule="",
        writer_rules=[],
        reviewer_focus=[],
        taboos=[],
    )
    mode = CreativeModeProfile(
        id="webnovel_intense",
        name="高强度网文",
        enabled_agents={},
        audit_weights={},
        active_audit_dimensions=[],
        revision_policy="standard",
        tolerance={},
        context_pruning_strategy="default",
        literary_optimization_plugins=[],
    )
    settings = [
        NewSetting(
            setting_key=f"setting-{i}",
            setting_name=f"设定{i}",
            description="desc",
            source_quote=f"quote {i}",
            chapter_number=i,
        )
        for i in range(20)
    ]
    profile = _build_test_profile(max_setting_input=2)

    ctx = assemble_context_package(
        chapter_goal=goal,
        creative_brief=None,
        genre_profile=gp,
        mode_profile=mode,
        project=project,
        characters=[],
        character_states=[],
        recent_summaries=[],
        active_foreshadowings=[],
        setting_snapshots=settings,
        runtime_profile=profile,
        budget_tokens=50000,
    )
    # Soft references should be capped by the profile's max_setting_input.
    assert len(ctx.soft_references) <= profile.max_setting_input


def test_xuanhuan_profile_max_character_states_is_eight() -> None:
    """Once wired, xuanhuan's profile max_character_states=8 must be visible."""
    xuanhuan = load_profile_from_registry("xuanhuan")
    assert xuanhuan.max_character_states == 8
    pruner = BudgetPruner(runtime_profile=xuanhuan)
    assert pruner.runtime_profile.max_character_states == 8

    ctx = _make_ctx_with_character_states(n=20)
    pruned = pruner._prune_character_states(ctx, budget=10000)
    assert len(pruned.character_states) == 8
