import asyncio
import sqlite3
from pathlib import Path

# 添加 src 到路径
import sys
sys.path.insert(0, str(Path("src").resolve()))

from songyan.agents.context_manager import assemble_context_package, BudgetPruner
from songyan.utils.token_estimator import TokenEstimator
from songyan.db.connection import get_db
from songyan.db.repository import (
    CharacterRepository, ProjectRepository,
)
from songyan.db.context_repo import (
    CharacterStateRepository, SummaryRepository,
)
from songyan.db.settlement_repo import (
    ForeshadowingRepository, SettingSnapshotRepository,
)
from songyan.db.layered_context_repo import (
    ArcSummaryRepository, VolumeSummaryRepository, PermanentSceneRepository,
)
from songyan.db.human_mark_repo import HumanMarkRepository
from songyan.workflows._helpers import (
    load_layered_summaries, load_characters,
    load_character_states, load_active_foreshadowings,
    load_setting_snapshots, load_open_threads,
    load_permanent_scenes, load_arc_context,
    load_volume_context,
)
from songyan.models import ChapterGoal, GenreProfile, CreativeModeProfile, ProjectSetting

async def main():
    project_id = "proj-e74ef1e4"
    chapter_number = 92
    db = get_db()

    # 加载项目
    project_repo = ProjectRepository()
    project = await project_repo.get(project_id)
    assert project

    # 加载角色
    char_repo = CharacterRepository()
    characters = await char_repo.list_by_project(project_id)
    print(f"Characters: {len(characters)}")
    for c in characters:
        print(f"  {c.name} ({c.role_type}) id={c.character_id}")

    # 加载角色状态
    state_repo = CharacterStateRepository()
    character_states = await state_repo.list_latest_by_project(project_id)
    print(f"Character states: {len(character_states)}")
    for s in character_states:
        print(f"  char_id={s.character_id} field={s.field}")

    # 加载摘要
    summaries = await load_layered_summaries(project_id, chapter_number)
    print(f"Summaries: {len(summaries)}")
    for s in summaries:
        print(f"  Ch{s.chapter_number} type={s.source_type} chars={len(s.summary)} chars_appeared={s.characters_appeared}")

    # 加载其他数据
    foreshadowings = await load_active_foreshadowings(project_id)
    settings = await load_setting_snapshots(project_id)
    open_threads = await load_open_threads(project_id, chapter_number)
    permanent_scenes = await load_permanent_scenes(project_id)
    arc_context = await load_arc_context(project_id, chapter_number)
    volume_context = await load_volume_context(project_id, chapter_number)

    # 构建 chapter goal (简化)
    chapter_goal = ChapterGoal(
        chapter_number=chapter_number,
        target_events=["test"],
        mood="tense",
        pacing="fast",
    )

    genre_profile = GenreProfile(id="scifi", name="scifi", rules=[])
    mode_profile = CreativeModeProfile(
        id="webnovel",
        name="webnovel",
        mode_rules=[],
        human_memory={"chapter_window": 10, "priority_threshold": 5, "max_marks_in_context": 20},
    )

    # 调用 assemble_context_package
    ctx = assemble_context_package(
        chapter_goal=chapter_goal,
        creative_brief=None,
        genre_profile=genre_profile,
        mode_profile=mode_profile,
        project=project,
        characters=characters,
        character_states=character_states,
        recent_summaries=summaries,
        active_foreshadowings=foreshadowings,
        setting_snapshots=settings,
        budget_tokens=15360,
        open_threads=open_threads,
        permanent_scenes=permanent_scenes,
        arc_context=arc_context,
        volume_context=volume_context,
    )

    print("\n" + "="*60)
    print("Budget Breakdown for Ch92")
    print("="*60)

    est = TokenEstimator()
    total = est.estimate_model(ctx)
    print(f"Total tokens: {total}")
    print(f"Budget: {ctx.budget_used * 15360 if ctx.budget_used else 15360}")
    print(f"Budget used: {ctx.budget_used:.3f}")

    def estimate(data):
        return est.estimate_model(data) if data else 0

    print(f"\ncharacter_states: {estimate(ctx.character_states)} ({len(ctx.character_states)} chars)")
    for s in (ctx.character_states or []):
        print(f"  {s.name}: {estimate(s)} tokens (score={s.importance_score})")

    print(f"\nrecent_plot: {estimate(ctx.recent_plot)}")
    if ctx.recent_plot:
        for s in ctx.recent_plot.summaries:
            print(f"  Ch{s.chapter_number}: {len(s.summary)} chars")

    print(f"\nsoft_references: {estimate(ctx.soft_references)} ({len(ctx.soft_references)} refs)")
    print(f"foreshadowing: {estimate(ctx.foreshadowing)} ({len(ctx.foreshadowing)} items)")
    print(f"hard_constraints: {estimate(ctx.hard_constraints)}")
    print(f"arc_context: {estimate(ctx.arc_context)}")
    print(f"volume_context: {estimate(ctx.volume_context)}")
    print(f"permanent_scenes: {estimate(ctx.permanent_scenes)} ({len(ctx.permanent_scenes)} scenes)")
    print(f"open_threads: {estimate(ctx.open_threads)} ({len(ctx.open_threads)} threads)")
    print(f"human_marks: {estimate(ctx.human_marks)} ({len(ctx.human_marks)} marks)")

if __name__ == "__main__":
    asyncio.run(main())
