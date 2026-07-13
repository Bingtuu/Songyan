"""Tests for Task 151 — MR 上限自适应 + 相关性排序."""

from __future__ import annotations

from pathlib import Path

import pytest

from songyan.db.continuity_repo import SettingTrackingRepository
from songyan.db.narrative_repo import NarrativeRepository
from songyan.db.repository import ChapterGoalRepository, ProjectRepository
from songyan.models import (
    ArcPlan,
    ChapterGoal,
    PlotThread,
    ProjectSetting,
)
from songyan.workflows._helpers import (
    _compute_mandatory_reference_inputs,
    _extract_mainline_thread_keys,
    _load_critical_mandatory_references,
    assemble_context_package,
)
from songyan.workflows._narrative_context import NarrativeGoalContext

pytestmark = pytest.mark.performance


async def _seed_project(project_id: str = "proj-151") -> str:
    await ProjectRepository().create(
        ProjectSetting(genre_id="xuanhuan", protagonist_name="英雄"),
        project_id,
    )
    return project_id


async def _create_tracking(
    project_id: str,
    key: str,
    *,
    chapter: int,
    category: str = "critical",
    status: str = "active",
    name: str = "",
    description: str = "",
    version_id: str = "v0",
    last_mentioned: int | None = None,
) -> None:
    await SettingTrackingRepository().create(
        tracking_id=f"track-{project_id}-{key}",
        project_id=project_id,
        setting_key=key,
        setting_name=name or key,
        description=description,
        introduced_in_chapter=chapter,
        source_version_id=version_id,
        category=category,
        status=status,
    )
    if last_mentioned is not None and last_mentioned != chapter:
        await SettingTrackingRepository().update_last_mentioned(
            f"track-{project_id}-{key}", last_mentioned
        )


async def _add_arc(pid: str, index: int, start: int, end: int) -> None:
    await NarrativeRepository().add_arc_plan(
        ArcPlan(
            arc_id=f"{pid}-arc{index}",
            project_id=pid,
            arc_index=index,
            start_chapter=start,
            end_chapter=end,
            is_mainline=True,
        )
    )


async def _add_thread(
    pid: str,
    thread_id: str,
    title: str,
    *,
    mainline: bool = False,
    status: str = "opened",
) -> None:
    await NarrativeRepository().add_thread(
        PlotThread(
            thread_id=thread_id,
            project_id=pid,
            title=title,
            is_mainline=mainline,
            status=status,
        )
    )


class TestAdaptiveCap:
    async def test_adaptive_cap_low_active_count(self, test_db: Path) -> None:
        pid = await _seed_project()
        # 2 active criticals, default scenes_count=3 → cap = min(max(2, 6, 6), 16) = 6
        for i in range(2):
            await _create_tracking(
                pid, f"crit-{i}", chapter=1, last_mentioned=1, category="critical", status="active"
            )
        result = await _load_critical_mandatory_references(pid, chapter_number=10)
        assert len(result) == 2  # only 2 qualify as orphan (silent >= 3)

    async def test_adaptive_cap_follows_active_count(self, test_db: Path) -> None:
        pid = await _seed_project()
        # 10 active criticals, default scenes_count=3 → cap = min(max(10, 6, 6), 16) = 10
        for i in range(10):
            await _create_tracking(
                pid, f"crit-{i}", chapter=1, last_mentioned=1, category="critical", status="active"
            )
        result = await _load_critical_mandatory_references(
            pid, chapter_number=10, active_critical_count=10
        )
        assert len(result) == 10

    async def test_adaptive_cap_upper_bound(self, test_db: Path) -> None:
        pid = await _seed_project()
        # 50 active criticals, scenes_count=10 → cap = min(max(50, 20, 6), 16) = 16
        for i in range(50):
            await _create_tracking(
                pid, f"crit-{i}", chapter=1, last_mentioned=1, category="critical", status="active"
            )
        result = await _load_critical_mandatory_references(
            pid, chapter_number=10, scenes_count=10
        )
        assert len(result) == 16

    async def test_explicit_max_overrides_adaptive(self, test_db: Path) -> None:
        pid = await _seed_project()
        for i in range(10):
            await _create_tracking(
                pid, f"crit-{i}", chapter=1, last_mentioned=1, category="critical", status="active"
            )
        result = await _load_critical_mandatory_references(
            pid, chapter_number=10, max_mandatory_references=5
        )
        assert len(result) == 5


class TestRelevanceSorting:
    async def test_mainline_related_sorted_first(self, test_db: Path) -> None:
        pid = await _seed_project()
        # 2 mainline-related criticals, less silent
        await _create_tracking(
            pid,
            "bloodline.seal",
            name="血脈封印",
            chapter=1,
            last_mentioned=5,
            category="critical",
            status="active",
        )
        await _create_tracking(
            pid,
            "ancient.treaty",
            name="上古盟約",
            chapter=1,
            last_mentioned=6,
            category="critical",
            status="active",
        )
        # 2 non-mainline criticals, more silent
        await _create_tracking(
            pid,
            "side.herb",
            name="邊角藥材",
            chapter=1,
            last_mentioned=1,
            category="critical",
            status="active",
        )
        await _create_tracking(
            pid,
            "minor.token",
            name="小令牌",
            chapter=1,
            last_mentioned=2,
            category="critical",
            status="active",
        )

        mainline_keys = {"bloodline", "上古盟約"}
        result = await _load_critical_mandatory_references(
            pid,
            chapter_number=10,
            max_mandatory_references=2,
            mainline_thread_keys=mainline_keys,
        )

        assert len(result) == 2
        assert {r["setting_key"] for r in result} == {"bloodline.seal", "ancient.treaty"}

    async def test_fallback_sort_without_mainline_keys(self, test_db: Path) -> None:
        pid = await _seed_project()
        await _create_tracking(
            pid,
            "older",
            chapter=1,
            last_mentioned=1,
            category="critical",
            status="active",
        )
        await _create_tracking(
            pid,
            "newer",
            chapter=5,
            last_mentioned=5,
            category="critical",
            status="active",
        )
        await _create_tracking(
            pid,
            "same.introduced.older",
            chapter=1,
            last_mentioned=2,
            category="critical",
            status="active",
        )

        with_mainline = await _load_critical_mandatory_references(
            pid, chapter_number=10, mainline_thread_keys=set()
        )
        without_mainline = await _load_critical_mandatory_references(
            pid, chapter_number=10, mainline_thread_keys=None
        )

        with_keys = [r["setting_key"] for r in with_mainline]
        without_keys = [r["setting_key"] for r in without_mainline]
        assert with_keys == without_keys
        # 沉默最多优先；同沉默下越早引入越优先
        keys = [r["setting_key"] for r in without_mainline]
        assert keys[0] == "older"  # silent=9, introduced=1
        assert keys[1] == "same.introduced.older"  # silent=8, introduced=1
        assert keys[2] == "newer"  # silent=5, introduced=5


class TestExtractMainlineKeys:
    async def test_extracts_mainline_keys(self, test_db: Path) -> None:
        ctx = NarrativeGoalContext(
            has_skeleton=True,
            open_threads=[
                {"thread_id": "t1", "title": "身世之谜", "is_mainline": True},
                {"thread_id": "t2", "title": "支线任务", "is_mainline": False},
            ],
            threads_to_resolve=[
                {"thread_id": "t3", "title": "上古盟約", "is_mainline": True},
            ],
        )
        keys = _extract_mainline_thread_keys(ctx)
        assert keys == {"t1", "身世之谜", "t3", "上古盟約"}

    async def test_returns_empty_without_skeleton(self, test_db: Path) -> None:
        ctx = NarrativeGoalContext(has_skeleton=False)
        assert _extract_mainline_thread_keys(ctx) == set()
        assert _extract_mainline_thread_keys(None) == set()


class TestComputeMandatoryReferenceInputs:
    async def test_counts_active_critical_and_loads_mainline_keys(self, test_db: Path) -> None:
        pid = await _seed_project()
        await _add_arc(pid, 0, 1, 10)
        await _add_thread(pid, "t1", "身世之谜", mainline=True, status="opened")
        await _add_thread(pid, "t2", "支线任务", mainline=False, status="opened")
        await _create_tracking(pid, "crit-a", chapter=1, category="critical", status="active")
        await _create_tracking(pid, "crit-b", chapter=1, category="critical", status="active")
        await _create_tracking(pid, "crit-c", chapter=1, category="critical", status="candidate")
        await _create_tracking(pid, "bg", chapter=1, category="background", status="active")

        count, keys = await _compute_mandatory_reference_inputs(pid, chapter_number=5)
        assert count == 2
        assert keys == {"t1", "身世之谜"}


class TestAssemblyIntegration:
    async def test_assembly_passes_inputs(self, test_db: Path) -> None:
        pid = await _seed_project()
        await _add_arc(pid, 0, 1, 20)
        await _add_thread(pid, "main-seal", "血脈封印", mainline=True, status="opened")
        await _add_thread(pid, "side-herb", "邊角藥材", mainline=False, status="opened")

        # 8 active criticals, all orphan, plus 1 mainline-related critical
        # active_critical_count=9 → adaptive cap = min(max(9, 6, 6), 16) = 9
        for i in range(8):
            await _create_tracking(
                pid,
                f"crit-{i}",
                name=f"設定{i}",
                chapter=1,
                last_mentioned=1,
                category="critical",
                status="active",
            )
        # one mainline-related critical
        await _create_tracking(
            pid,
            "bloodline.seal",
            name="血脈封印",
            chapter=1,
            last_mentioned=2,
            category="critical",
            status="active",
        )

        goal = ChapterGoal(
            chapter_number=10,
            previous_summary="",
            target_events=["test"],
            word_count_target=3000,
            chapter_type="normal",
        )
        await ChapterGoalRepository().create(goal, "goal-151", pid)

        ctx = await assemble_context_package(pid, 10, goal, None)
        mr = ctx.mandatory_references
        assert len(mr) == 9  # capped at active_critical_count=9
        # mainline-related item should appear at the front
        assert mr[0]["setting_key"] == "bloodline.seal"


class TestMaxOrphanedUntouched:
    async def test_max_orphaned_still_twelve(self, test_db: Path) -> None:
        from songyan.agents.continuity_auditor._constraints import MAX_ORPHANED

        assert MAX_ORPHANED == 12
