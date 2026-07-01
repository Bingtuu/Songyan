"""Tests for Task 144 — 线索经济约束（MVP）.

覆盖：CreativeDirector 线索约束注入（1.0.6 vs 1.0.5 回退）；
``update_plot_threads_after_settlement`` 状态机跟随更新、计数、边界，
以及收束防过早（advanced 优先 + 计划收束弧窗口）。
"""

from __future__ import annotations

from pathlib import Path

from songyan.agents.creative_director import _render_prompt
from songyan.creative_modes.registry import load_creative_mode_profile
from songyan.db.narrative_repo import NarrativeRepository
from songyan.db.repository import ProjectRepository
from songyan.genres.loader import load_genre_profile
from songyan.models import (
    ArcPlan,
    ChapterGoal,
    ForeshadowingUpdate,
    NewSetting,
    PlotThread,
    ProjectSetting,
    StateSettlement,
)
from songyan.workflows._narrative_context import NarrativeGoalContext
from songyan.workflows._thread_economy import update_plot_threads_after_settlement


async def _seed_project(project_id: str = "proj-144") -> str:
    await ProjectRepository().create(
        ProjectSetting(genre_id="xuanhuan", protagonist_name="英雄"),
        project_id,
    )
    return project_id


async def _add_thread(
    pid: str, thread_id: str, title: str, *, mainline: bool = False,
    expected_resolve_arc: int | None = None,
) -> None:
    await NarrativeRepository().add_thread(
        PlotThread(
            thread_id=thread_id, project_id=pid, title=title,
            is_mainline=mainline, expected_resolve_arc=expected_resolve_arc,
        )
    )


async def _add_arc(pid: str, index: int, start: int, end: int) -> None:
    await NarrativeRepository().add_arc_plan(
        ArcPlan(
            arc_id=f"{pid}-arc{index}", project_id=pid, arc_index=index,
            start_chapter=start, end_chapter=end, is_mainline=True,
        )
    )


def _resolve_settlement(keyword: str) -> StateSettlement:
    """构造一个含收束信号（resolved_hook）且引用 keyword 的 settlement."""
    return StateSettlement(resolved_hooks=[f"{keyword}的真相揭开"])


# --------------------------------------------------------------------------- #
# 约束注入（CreativeDirector 1.0.6 vs 1.0.5 回退）
# --------------------------------------------------------------------------- #
class TestConstraintInjection:
    async def test_injects_thread_economy(self, test_db: Path) -> None:
        genre = load_genre_profile("xuanhuan")
        mode = load_creative_mode_profile("webnovel")
        project = ProjectSetting(genre_id="xuanhuan", protagonist_name="英雄")
        goal = ChapterGoal(chapter_number=1)
        ctx = NarrativeGoalContext(
            has_skeleton=True, arc_goal="开局立威", arc_index=0,
            open_threads=[
                {"thread_id": "t1", "title": "身世之谜", "status": "opened", "is_mainline": True}
            ],
            threads_to_resolve=[
                {"thread_id": "t2", "title": "旧仇", "status": "advanced", "is_mainline": True}
            ],
        )
        prompt = await _render_prompt(
            project_id="proj-x", project=project, chapter_goal=goal,
            genre_profile=genre, mode_profile=mode, characters=[],
            previous_summary="", seed_settings=[], narrative_ctx=ctx,
        )
        assert "线索经济约束" in prompt
        assert "应推进" in prompt
        assert "应收束" in prompt
        assert "非必要不开" in prompt
        assert "身世之谜" in prompt
        assert "旧仇" in prompt

    async def test_fallback_no_skeleton(self, test_db: Path) -> None:
        genre = load_genre_profile("xuanhuan")
        mode = load_creative_mode_profile("webnovel")
        project = ProjectSetting(genre_id="xuanhuan", protagonist_name="英雄")
        goal = ChapterGoal(chapter_number=1)
        prompt = await _render_prompt(
            project_id="proj-x", project=project, chapter_goal=goal,
            genre_profile=genre, mode_profile=mode, characters=[],
            previous_summary="", seed_settings=[], narrative_ctx=None,
        )
        assert "线索经济约束" not in prompt

    async def test_fallback_skeleton_without_threads(self, test_db: Path) -> None:
        genre = load_genre_profile("xuanhuan")
        mode = load_creative_mode_profile("webnovel")
        project = ProjectSetting(genre_id="xuanhuan", protagonist_name="英雄")
        goal = ChapterGoal(chapter_number=1)
        ctx = NarrativeGoalContext(has_skeleton=True, arc_goal="开局", arc_index=0)
        prompt = await _render_prompt(
            project_id="proj-x", project=project, chapter_goal=goal,
            genre_profile=genre, mode_profile=mode, characters=[],
            previous_summary="", seed_settings=[], narrative_ctx=ctx,
        )
        assert "线索经济约束" not in prompt


# --------------------------------------------------------------------------- #
# 状态跟随更新（update_plot_threads_after_settlement）
# --------------------------------------------------------------------------- #
class TestThreadStateFollow:
    async def test_planned_to_opened(self, test_db: Path) -> None:
        pid = await _seed_project()
        await _add_thread(pid, "t1", "身世之谜", mainline=True)
        settlement = StateSettlement(
            new_settings=[
                NewSetting(
                    setting_name="身世之谜的碎片", description="提到身世之谜", source_quote="x"
                )
            ]
        )
        changed = await update_plot_threads_after_settlement(pid, 3, "v3", settlement)
        assert changed == ["t1"]
        t = await NarrativeRepository().get_thread("t1")
        assert t is not None
        assert t.status == "opened"
        assert t.opened_chapter == 3
        assert t.last_status_chapter == 3
        assert t.last_status_version_id == "v3"

    async def test_full_lifecycle_to_resolved_no_planned_arc(self, test_db: Path) -> None:
        """无计划收束弧（expected_resolve_arc=None）：opened→advanced→resolved 链可完成."""
        pid = await _seed_project()
        repo = NarrativeRepository()
        await _add_thread(pid, "t1", "身世之谜", mainline=True)

        s1 = StateSettlement(
            foreshadowing_updates=[
                ForeshadowingUpdate(operation="plant", description="身世之谜浮现")
            ]
        )
        await update_plot_threads_after_settlement(pid, 1, "v1", s1)
        assert (await repo.get_thread("t1")).status == "opened"

        s2 = StateSettlement(
            foreshadowing_updates=[
                ForeshadowingUpdate(operation="update_status", description="身世之谜进一步推进")
            ]
        )
        await update_plot_threads_after_settlement(pid, 2, "v2", s2)
        assert (await repo.get_thread("t1")).status == "advanced"

        s3 = StateSettlement(
            foreshadowing_updates=[
                ForeshadowingUpdate(operation="resolve", description="身世之谜真相大白")
            ]
        )
        changed = await update_plot_threads_after_settlement(pid, 3, "v3", s3)
        assert changed == ["t1"]
        t = await repo.get_thread("t1")
        assert t is not None
        assert t.status == "resolved"
        assert t.last_status_chapter == 3
        assert t.last_status_version_id == "v3"

    async def test_opened_advances_not_resolves(self, test_db: Path) -> None:
        """opened 状态即便收到收束信号也只推进到 advanced（禁止 opened 直接 resolved）."""
        pid = await _seed_project()
        repo = NarrativeRepository()
        await _add_thread(pid, "t1", "惊天阴谋")
        await repo.advance_thread_status("t1", "opened", 1, "v1")
        changed = await update_plot_threads_after_settlement(
            pid, 2, "v2", _resolve_settlement("惊天阴谋")
        )
        assert changed == ["t1"]
        assert (await repo.get_thread("t1")).status == "advanced"

    async def test_advanced_to_resolved_no_planned_arc(self, test_db: Path) -> None:
        pid = await _seed_project()
        repo = NarrativeRepository()
        await _add_thread(pid, "t1", "惊天阴谋")
        await repo.advance_thread_status("t1", "opened", 1, "v1")
        await repo.advance_thread_status("t1", "advanced", 2, "v2")
        changed = await update_plot_threads_after_settlement(
            pid, 3, "v3", _resolve_settlement("惊天阴谋")
        )
        assert changed == ["t1"]
        assert (await repo.get_thread("t1")).status == "resolved"

    async def test_no_premature_resolve_before_resolve_arc(self, test_db: Path) -> None:
        """主线线索计划在 arc1（Ch11-20）收束：Ch2 收到收束信号也不 resolve，Ch11 才 resolve."""
        pid = await _seed_project()
        repo = NarrativeRepository()
        await _add_arc(pid, 0, 1, 10)
        await _add_arc(pid, 1, 11, 20)
        await _add_thread(pid, "t_blade", "断刃", mainline=True, expected_resolve_arc=1)
        await repo.advance_thread_status("t_blade", "opened", 1, "v1")
        await repo.advance_thread_status("t_blade", "advanced", 2, "v2")

        # Ch2：收束窗口未开（arc1 从 Ch11 起）→ 保持 advanced
        changed = await update_plot_threads_after_settlement(
            pid, 2, "v2b", _resolve_settlement("断刃")
        )
        assert changed == []
        assert (await repo.get_thread("t_blade")).status == "advanced"

        # Ch11：进入收束弧窗口 → resolve
        changed = await update_plot_threads_after_settlement(
            pid, 11, "v11", _resolve_settlement("断刃")
        )
        assert changed == ["t_blade"]
        assert (await repo.get_thread("t_blade")).status == "resolved"

    async def test_resolve_arc_undefined_never_auto_resolves(self, test_db: Path) -> None:
        """计划收束弧未定义（大纲没有该 arc_index）→ 不自动收束."""
        pid = await _seed_project()
        repo = NarrativeRepository()
        await _add_arc(pid, 0, 1, 10)
        await _add_arc(pid, 1, 11, 20)
        # expected_resolve_arc=2，但大纲只有 arc 0/1
        await _add_thread(pid, "t_tower", "灰塔", mainline=True, expected_resolve_arc=2)
        await repo.advance_thread_status("t_tower", "opened", 1, "v1")
        await repo.advance_thread_status("t_tower", "advanced", 2, "v2")

        changed = await update_plot_threads_after_settlement(
            pid, 15, "v15", _resolve_settlement("灰塔")
        )
        assert changed == []
        assert (await repo.get_thread("t_tower")).status == "advanced"

    async def test_no_change_when_unreferenced(self, test_db: Path) -> None:
        pid = await _seed_project()
        repo = NarrativeRepository()
        await _add_thread(pid, "t1", "身世之谜")
        settlement = StateSettlement(
            new_settings=[
                NewSetting(setting_name="无关设定", description="别的东西", source_quote="x")
            ]
        )
        changed = await update_plot_threads_after_settlement(pid, 1, "v1", settlement)
        assert changed == []
        assert (await repo.get_thread("t1")).status == "planned"

    async def test_counting_after_updates(self, test_db: Path) -> None:
        pid = await _seed_project()
        repo = NarrativeRepository()
        await _add_thread(pid, "t1", "甲线索")
        await _add_thread(pid, "t2", "乙线索")
        settlement = StateSettlement(planted_hooks=["甲线索开始推进"])
        await update_plot_threads_after_settlement(pid, 1, "v1", settlement)
        counts = await repo.count_threads_by_status(pid)
        assert counts.get("opened") == 1
        assert counts.get("planned") == 1

    async def test_no_threads_is_noop(self, test_db: Path) -> None:
        pid = await _seed_project()
        settlement = StateSettlement(planted_hooks=["随便什么"])
        assert await update_plot_threads_after_settlement(pid, 1, "v1", settlement) == []
