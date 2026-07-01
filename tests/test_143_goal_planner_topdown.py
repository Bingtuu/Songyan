"""Tests for Task 143 — GoalPlanner 自顶向下派生.

覆盖：143a ``load_narrative_goal_context`` 加载/回退；143b prompt 注入、
``derived_from_arc`` 派生与持久化、无骨架回退等价性。
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

from songyan.agents.goal_planner import _render_prompt, define_chapter_goal
from songyan.creative_modes.registry import load_creative_mode_profile
from songyan.db.narrative_repo import NarrativeRepository
from songyan.db.repository import ChapterGoalRepository, ProjectRepository
from songyan.db.settlement_repo import ForeshadowingRepository
from songyan.genres.loader import load_genre_profile
from songyan.models import (
    ArcPlan,
    ChapterGoal,
    ForeshadowingItem,
    PlotThread,
    ProjectSetting,
)
from songyan.workflows._narrative_context import (
    NarrativeGoalContext,
    load_narrative_goal_context,
)

_FAKE_GOAL_JSON = (
    '{"target_events": ["主角夺剑"], "emotional_arc": "紧张", '
    '"hooks": ["剑灵开口"], "obligations": [], '
    '"word_count_target": 3000, "chapter_type": ""}'
)


async def _seed_project(project_id: str = "proj-143") -> str:
    await ProjectRepository().create(
        ProjectSetting(genre_id="xuanhuan", protagonist_name="英雄"),
        project_id,
    )
    return project_id


def _profiles():
    return load_genre_profile("xuanhuan"), load_creative_mode_profile("webnovel")


# --------------------------------------------------------------------------- #
# 143a: load_narrative_goal_context
# --------------------------------------------------------------------------- #
class TestNarrativeContextLoader:
    async def test_with_skeleton(self, test_db: Path) -> None:
        pid = await _seed_project()
        repo = NarrativeRepository()
        await repo.add_arc_plan(
            ArcPlan(
                arc_id="a0", project_id=pid, arc_index=0,
                start_chapter=1, end_chapter=20, arc_goal="开局立威",
                threads_to_resolve=["t1"], is_mainline=True,
            )
        )
        await repo.add_thread(
            PlotThread(thread_id="t1", project_id=pid, title="身世", is_mainline=True)
        )
        await repo.advance_thread_status("t1", "opened", 1, "v1")

        ctx = await load_narrative_goal_context(pid, 5)
        assert ctx.has_skeleton is True
        assert ctx.arc_goal == "开局立威"
        assert ctx.arc_index == 0
        assert ctx.is_mainline_arc is True
        assert any(t["thread_id"] == "t1" for t in ctx.open_threads)
        assert any(t["thread_id"] == "t1" for t in ctx.threads_to_resolve)

    async def test_no_skeleton_fallback(self, test_db: Path) -> None:
        pid = await _seed_project()
        ctx = await load_narrative_goal_context(pid, 5)
        assert ctx.has_skeleton is False
        assert ctx.open_threads == []
        assert ctx.threads_to_resolve == []
        assert ctx.due_foreshadowings == []

    async def test_chapter_beyond_all_arcs(self, test_db: Path) -> None:
        pid = await _seed_project()
        await NarrativeRepository().add_arc_plan(
            ArcPlan(arc_id="a0", project_id=pid, arc_index=0, start_chapter=1, end_chapter=20)
        )
        ctx = await load_narrative_goal_context(pid, 99)
        assert ctx.has_skeleton is False

    async def test_due_foreshadowings(self, test_db: Path) -> None:
        pid = await _seed_project()
        await NarrativeRepository().add_arc_plan(
            ArcPlan(arc_id="a0", project_id=pid, arc_index=0, start_chapter=1, end_chapter=20)
        )
        await ForeshadowingRepository().create(
            ForeshadowingItem(
                foreshadowing_id="f1", description="神秘信物",
                planted_in_chapter=1, expected_resolve_chapter=7, status="planted",
            ),
            pid,
        )
        ctx = await load_narrative_goal_context(pid, 5, due_window=5)
        assert any(f["foreshadowing_id"] == "f1" for f in ctx.due_foreshadowings)
        # 窗口外不纳入
        ctx2 = await load_narrative_goal_context(pid, 1, due_window=2)
        assert ctx2.due_foreshadowings == []


# --------------------------------------------------------------------------- #
# 143b: derived_from_arc 持久化
# --------------------------------------------------------------------------- #
class TestDerivedFromArcPersistence:
    async def test_roundtrip(self, test_db: Path) -> None:
        pid = await _seed_project()
        repo = ChapterGoalRepository()
        await repo.create(ChapterGoal(chapter_number=1, derived_from_arc=2), "g1", pid)
        got = await repo.get("g1")
        assert got is not None and got.derived_from_arc == 2

        await repo.create(ChapterGoal(chapter_number=2), "g2", pid)
        got2 = await repo.get_by_chapter(pid, 2)
        assert got2 is not None and got2.derived_from_arc is None


# --------------------------------------------------------------------------- #
# 143b: prompt 注入 + 回退等价性（无需 DB / LLM）
# --------------------------------------------------------------------------- #
class TestRenderPrompt:
    def test_fallback_zero_diff(self) -> None:
        genre, mode = _profiles()
        project = ProjectSetting(genre_id="xuanhuan", protagonist_name="英雄")
        p_none = _render_prompt(
            chapter_number=1, project=project, genre_profile=genre,
            mode_profile=mode, recent_summaries="", narrative_ctx=None,
        )
        p_empty = _render_prompt(
            chapter_number=1, project=project, genre_profile=genre,
            mode_profile=mode, recent_summaries="",
            narrative_ctx=NarrativeGoalContext(has_skeleton=False),
        )
        assert p_none == p_empty
        assert "叙事骨架" not in p_none
        assert "目标规划师" in p_none  # 仍是 1.0.0 正文

    def test_skeleton_injects_arc_and_threads(self) -> None:
        genre, mode = _profiles()
        project = ProjectSetting(genre_id="xuanhuan", protagonist_name="英雄")
        ctx = NarrativeGoalContext(
            has_skeleton=True, arc_goal="开局立威", arc_index=0, is_mainline_arc=True,
            open_threads=[
                {"thread_id": "t1", "title": "身世", "status": "opened", "is_mainline": True}
            ],
        )
        p = _render_prompt(
            chapter_number=1, project=project, genre_profile=genre,
            mode_profile=mode, recent_summaries="", narrative_ctx=ctx,
        )
        assert "叙事骨架" in p
        assert "开局立威" in p
        assert "t1" in p

        p_none = _render_prompt(
            chapter_number=1, project=project, genre_profile=genre,
            mode_profile=mode, recent_summaries="", narrative_ctx=None,
        )
        assert p != p_none


# --------------------------------------------------------------------------- #
# 143b: define_chapter_goal 派生 + 回退（Mock LLM）
# --------------------------------------------------------------------------- #
class TestDefineChapterGoal:
    async def test_derivation_sets_arc(self) -> None:
        genre, mode = _profiles()
        project = ProjectSetting(genre_id="xuanhuan", protagonist_name="英雄")
        ctx = NarrativeGoalContext(has_skeleton=True, arc_goal="开局立威", arc_index=3)
        with patch(
            "songyan.agents.goal_planner.call_llm",
            new=AsyncMock(return_value=_FAKE_GOAL_JSON),
        ) as m:
            goal = await define_chapter_goal(
                project_id="p", project=project, genre_profile=genre,
                mode_profile=mode, chapter_number=1,
                previous_summary="", narrative_ctx=ctx,
            )
        assert goal.derived_from_arc == 3
        assert "开局立威" in m.await_args[0][0]

    async def test_fallback_no_arc(self) -> None:
        genre, mode = _profiles()
        project = ProjectSetting(genre_id="xuanhuan", protagonist_name="英雄")
        with patch(
            "songyan.agents.goal_planner.call_llm",
            new=AsyncMock(return_value=_FAKE_GOAL_JSON),
        ) as m:
            goal = await define_chapter_goal(
                project_id="p", project=project, genre_profile=genre,
                mode_profile=mode, chapter_number=1,
                previous_summary="", narrative_ctx=None,
            )
        assert goal.derived_from_arc is None
        assert "叙事骨架" not in m.await_args[0][0]
