"""Task 167b: schedule injection and lifecycle tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

from songyan.agents.creative_director import _render_prompt as _render_cd_prompt
from songyan.agents.goal_planner import _render_prompt as _render_goal_prompt
from songyan.creative_modes.registry import load_creative_mode_profile
from songyan.db.foreshadowing_schedule_repo import ForeshadowingScheduleRepository
from songyan.db.narrative_repo import NarrativeRepository
from songyan.db.repository import ProjectRepository
from songyan.genres.loader import load_genre_profile
from songyan.models import (
    ArcPlan,
    ChapterGoal,
    Character,
    ForeshadowingScheduleItem,
    ForeshadowingSchedulePlan,
    ProjectSetting,
    StateSettlement,
)
from songyan.services.foreshadowing_schedule import (
    activate_foreshadowing_schedule_plan,
    update_schedule_after_accept,
)
from songyan.workflows._narrative_context import (
    NarrativeGoalContext,
    load_narrative_goal_context,
)
from songyan.workflows._nodes import goal_planner_node

PID = "proj-167b"


async def _seed_project(project_id: str = PID) -> str:
    await ProjectRepository().create(
        ProjectSetting(title=project_id, genre_id="scifi", protagonist_name="林渊"),
        project_id=project_id,
    )
    return project_id


async def _seed_arc(project_id: str = PID) -> None:
    await NarrativeRepository().add_arc_plan(
        ArcPlan(
            arc_id=f"{project_id}-arc0",
            project_id=project_id,
            arc_index=0,
            start_chapter=1,
            end_chapter=10,
            arc_goal="推进灰塔主线",
            is_mainline=True,
        )
    )


def _schedule_item(
    plan_id: str,
    item_id: str,
    *,
    project_id: str = PID,
    source_id: str,
    description: str,
    priority: float = 10.0,
    status: str = "draft",
    target_chapter: int = 3,
) -> ForeshadowingScheduleItem:
    return ForeshadowingScheduleItem(
        item_id=item_id,
        plan_id=plan_id,
        project_id=project_id,
        item_order=0,
        target_chapter=target_chapter,
        source_type="foreshadowing",
        source_id=source_id,
        title=description,
        description=description,
        priority_score=priority,
        reason_codes=["foreshadowing_due"],
        rationale="伏笔临近兑现",
        status=status,  # type: ignore[arg-type]
        evidence={"foreshadowing": {"description": description}},
    )


async def _create_plan_with_items(
    plan_id: str,
    items: list[ForeshadowingScheduleItem],
    *,
    project_id: str = PID,
    target_chapter: int = 3,
) -> ForeshadowingSchedulePlan:
    for index, item in enumerate(items):
        item.item_order = index
    plan = ForeshadowingSchedulePlan(
        plan_id=plan_id,
        project_id=project_id,
        target_chapter=target_chapter,
        current_arc_index=0,
        items=items,
    )
    await ForeshadowingScheduleRepository().create(plan)
    return plan


class TestScheduleInjection:
    async def test_active_schedule_item_enters_narrative_context(
        self, test_db: Path
    ) -> None:
        await _seed_project()
        await _seed_arc()
        await _create_plan_with_items(
            "fsp-active",
            [
                _schedule_item(
                    "fsp-active",
                    "fsi-active",
                    source_id="fs-gray",
                    description="灰塔信号必须推进",
                )
            ],
        )
        await activate_foreshadowing_schedule_plan("fsp-active")

        ctx = await load_narrative_goal_context(PID, 3)

        assert ctx.scheduled_items
        assert ctx.scheduled_items[0]["source_id"] == "fs-gray"
        assert ctx.scheduled_items[0]["rationale"] == "伏笔临近兑现"

    async def test_no_active_schedule_keeps_old_context_empty(
        self, test_db: Path
    ) -> None:
        await _seed_project()
        await _seed_arc()

        ctx = await load_narrative_goal_context(PID, 3)

        assert ctx.has_skeleton is True
        assert ctx.scheduled_items == []

    async def test_goal_prompt_contains_schedule_source_and_reason(self) -> None:
        genre = load_genre_profile("scifi")
        mode = load_creative_mode_profile("webnovel")
        project = ProjectSetting(genre_id="scifi", protagonist_name="林渊")
        ctx = NarrativeGoalContext(
            has_skeleton=True,
            arc_goal="推进灰塔主线",
            arc_index=0,
            scheduled_items=[
                {
                    "item_id": "fsi-1",
                    "source_id": "fs-gray",
                    "description": "灰塔信号必须推进",
                    "target_chapter": 3,
                    "rationale": "伏笔临近兑现",
                    "status": "active",
                }
            ],
        )

        prompt = _render_goal_prompt(
            chapter_number=3,
            project=project,
            genre_profile=genre,
            mode_profile=mode,
            recent_summaries="",
            narrative_ctx=ctx,
        )

        assert "fs-gray" in prompt
        assert "灰塔信号必须推进" in prompt
        assert "伏笔临近兑现" in prompt

    async def test_creative_director_prompt_contains_schedule_item(
        self, test_db: Path
    ) -> None:
        await _seed_project()
        genre = load_genre_profile("scifi")
        mode = load_creative_mode_profile("webnovel")
        project = ProjectSetting(genre_id="scifi", protagonist_name="林渊")
        ctx = NarrativeGoalContext(
            has_skeleton=True,
            arc_goal="推进灰塔主线",
            arc_index=0,
            scheduled_items=[
                {
                    "item_id": "fsi-1",
                    "source_type": "foreshadowing",
                    "source_id": "fs-gray",
                    "description": "灰塔信号必须推进",
                    "rationale": "伏笔临近兑现",
                    "status": "active",
                }
            ],
        )

        prompt = await _render_cd_prompt(
            project_id=PID,
            project=project,
            chapter_goal=ChapterGoal(chapter_number=3),
            genre_profile=genre,
            mode_profile=mode,
            characters=[
                Character(
                    character_id="c-protagonist",
                    project_id=PID,
                    name="林渊",
                    role_type="protagonist",
                )
            ],
            previous_summary="",
            seed_settings=[],
            narrative_ctx=ctx,
        )

        assert "主动调度项" in prompt
        assert "fs-gray" in prompt
        assert "灰塔信号必须推进" in prompt

    async def test_schedule_injection_marks_active_items_injected(
        self, test_db: Path
    ) -> None:
        await _seed_project()
        await _seed_arc()
        await _create_plan_with_items(
            "fsp-node",
            [
                _schedule_item(
                    "fsp-node",
                    "fsi-node",
                    source_id="fs-node",
                    description="节点注入伏笔",
                )
            ],
        )
        await activate_foreshadowing_schedule_plan("fsp-node")
        fake_goal_json = (
            '{"target_events": ["推进调度项"], "emotional_arc": "紧张", '
            '"hooks": [], "obligations": [], "word_count_target": 3000, '
            '"chapter_type": ""}'
        )

        with patch(
            "songyan.agents.goal_planner.call_llm",
            new=AsyncMock(return_value=fake_goal_json),
        ):
            result = await goal_planner_node(
                {
                    "project_id": PID,
                    "chapter_number": 3,
                    "previous_summary": "",
                }
            )

        assert result["status"] == "creative_direction"
        plan = await ForeshadowingScheduleRepository().get("fsp-node")
        assert plan is not None
        assert plan.items[0].status == "injected"

    async def test_schedule_limit_caps_injected_context_items(
        self, test_db: Path
    ) -> None:
        await _seed_project()
        await _seed_arc()
        items = [
            _schedule_item(
                "fsp-limit",
                f"fsi-{idx}",
                source_id=f"fs-{idx}",
                description=f"调度项 {idx}",
                priority=float(idx),
            )
            for idx in range(5)
        ]
        await _create_plan_with_items("fsp-limit", items)
        await activate_foreshadowing_schedule_plan("fsp-limit")

        ctx = await load_narrative_goal_context(PID, 3, schedule_limit=2)

        assert len(ctx.scheduled_items) == 2
        assert [item["source_id"] for item in ctx.scheduled_items] == ["fs-4", "fs-3"]


class TestScheduleLifecycle:
    async def test_accept_marks_referenced_item_satisfied(self, test_db: Path) -> None:
        await _seed_project()
        await _create_plan_with_items(
            "fsp-satisfied",
            [
                _schedule_item(
                    "fsp-satisfied",
                    "fsi-satisfied",
                    source_id="fs-gray",
                    description="灰塔信号",
                    status="injected",
                )
            ],
        )

        result = await update_schedule_after_accept(
            project_id=PID,
            chapter_number=3,
            settlement=StateSettlement(planted_hooks=["灰塔信号出现新含义"]),
        )

        plan = await ForeshadowingScheduleRepository().get("fsp-satisfied")
        assert result["satisfied"] == ["fsi-satisfied"]
        assert plan is not None
        assert plan.items[0].status == "satisfied"

    async def test_accept_marks_unreferenced_due_item_missed(
        self, test_db: Path
    ) -> None:
        await _seed_project()
        await _create_plan_with_items(
            "fsp-missed",
            [
                _schedule_item(
                    "fsp-missed",
                    "fsi-missed",
                    source_id="fs-missed",
                    description="没有出现的伏笔",
                    status="injected",
                )
            ],
        )

        result = await update_schedule_after_accept(
            project_id=PID,
            chapter_number=3,
            settlement=StateSettlement(planted_hooks=["无关内容"]),
        )

        plan = await ForeshadowingScheduleRepository().get("fsp-missed")
        assert result["missed"] == ["fsi-missed"]
        assert plan is not None
        assert plan.items[0].status == "missed"
