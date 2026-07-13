"""Task 167a: active foreshadowing schedule generation tests."""

from __future__ import annotations

from pathlib import Path

from songyan.db.foreshadowing_schedule_repo import ForeshadowingScheduleRepository
from songyan.db.migrations import _EXPECTED_TABLES
from songyan.db.narrative_repo import NarrativeRepository
from songyan.db.replan_repo import ReplanProposalRepository
from songyan.db.repository import ProjectRepository
from songyan.db.settlement_repo import ForeshadowingRepository
from songyan.evals.foreshadowing_schedule import generate_foreshadowing_schedule_plan
from songyan.models import (
    ArcPlan,
    ForeshadowingItem,
    ForeshadowingScheduleItem,
    ForeshadowingSchedulePlan,
    PlanningConstraint,
    PlotThread,
    ProjectSetting,
    ReplanAction,
    ReplanProposal,
)

PID = "proj-167a"


async def _seed_project(project_id: str = PID) -> str:
    await ProjectRepository().create(
        ProjectSetting(title=project_id, genre_id="scifi", protagonist_name="林渊"),
        project_id=project_id,
    )
    return project_id


async def _seed_version(
    project_id: str = PID, version_id: str = "v1", chapter_number: int = 1
) -> None:
    from songyan.db.connection import get_db

    async with get_db() as conn:
        await conn.execute(
            """INSERT OR IGNORE INTO chapter_versions (
                version_id, project_id, chapter_number, version_number, version_type
            ) VALUES (?, ?, ?, ?, ?)""",
            (version_id, project_id, chapter_number, 1, "accepted"),
        )
        await conn.commit()


async def _seed_arc(
    arc_id: str,
    *,
    project_id: str = PID,
    arc_index: int,
    start: int,
    end: int,
    threads_to_open: list[str] | None = None,
    threads_to_resolve: list[str] | None = None,
) -> ArcPlan:
    arc = ArcPlan(
        arc_id=arc_id,
        project_id=project_id,
        arc_index=arc_index,
        start_chapter=start,
        end_chapter=end,
        arc_goal=f"Arc {arc_index}",
        threads_to_open=threads_to_open or [],
        threads_to_resolve=threads_to_resolve or [],
        is_mainline=True,
    )
    await NarrativeRepository().add_arc_plan(arc)
    return arc


async def _seed_thread(
    thread_id: str,
    *,
    project_id: str = PID,
    title: str | None = None,
    is_mainline: bool = False,
    expected_resolve_arc: int | None = None,
    status: str = "opened",
) -> PlotThread:
    thread = PlotThread(
        thread_id=thread_id,
        project_id=project_id,
        title=title or thread_id,
        description=f"{thread_id} description",
        is_mainline=is_mainline,
        opened_chapter=1 if status != "planned" else None,
        expected_resolve_arc=expected_resolve_arc,
        status=status,  # type: ignore[arg-type]
        last_status_chapter=1 if status != "planned" else None,
        last_status_version_id="v-open" if status != "planned" else None,
    )
    await NarrativeRepository().add_thread(thread)
    return thread


async def _seed_foreshadowing(
    foreshadowing_id: str,
    *,
    project_id: str = PID,
    description: str,
    planted: int,
    expected: int | None,
    status: str = "planted",
    source_version_id: str = "v1",
) -> None:
    await _seed_version(project_id, source_version_id, planted)
    await ForeshadowingRepository().create(
        ForeshadowingItem(
            foreshadowing_id=foreshadowing_id,
            description=description,
            planted_in_chapter=planted,
            expected_resolve_chapter=expected,
            status=status,  # type: ignore[arg-type]
        ),
        project_id,
        source_version_id,
    )


async def _seed_constraint(
    constraint_id: str,
    *,
    project_id: str = PID,
    content: str,
    target_id: str = "",
) -> None:
    proposal = ReplanProposal(
        proposal_id=f"rp-{constraint_id}",
        project_id=project_id,
        actions=[
            ReplanAction(
                action_id=f"ra-{constraint_id}",
                proposal_id=f"rp-{constraint_id}",
                action_order=0,
                target_type="style_constraint",
                target_id=target_id,
                field="planning_constraints",
                old_value=None,
                new_value=content,
                reason="测试规划约束",
            )
        ],
    )
    repo = ReplanProposalRepository()
    await repo.create(proposal)
    await repo.create_planning_constraint(
        PlanningConstraint(
            constraint_id=constraint_id,
            project_id=project_id,
            source_proposal_id=proposal.proposal_id,
            source_action_id=proposal.actions[0].action_id,
            target_id=target_id,
            constraint_type="planning_constraint",
            content=content,
            reason="测试规划约束",
        )
    )


class TestForeshadowingScheduleSchema:
    async def test_tables_registered(self, test_db: Path) -> None:
        assert "foreshadowing_schedule_plans" in _EXPECTED_TABLES
        assert "foreshadowing_schedule_items" in _EXPECTED_TABLES


class TestForeshadowingScheduleGeneration:
    async def test_no_skeleton_returns_noop(self, test_db: Path) -> None:
        await _seed_project()

        plan = await generate_foreshadowing_schedule_plan(
            PID,
            target_chapter=5,
            plan_id="fsp-noop",
        )

        assert plan.items == []
        assert "no matching ArcPlan" in plan.summary

    async def test_mainline_thread_prioritized(self, test_db: Path) -> None:
        await _seed_project()
        await _seed_arc("arc-0", arc_index=0, start=1, end=5)
        await _seed_thread("side", is_mainline=False)
        await _seed_thread("main", is_mainline=True)

        plan = await generate_foreshadowing_schedule_plan(
            PID,
            target_chapter=3,
            max_items=2,
            plan_id="fsp-mainline",
        )

        assert [item.source_id for item in plan.items][:2] == ["main", "side"]
        assert "mainline_thread" in plan.items[0].reason_codes

    async def test_expected_resolve_arc_due_generates_due_item(
        self, test_db: Path
    ) -> None:
        await _seed_project()
        await _seed_arc("arc-0", arc_index=0, start=1, end=5)
        await _seed_arc("arc-1", arc_index=1, start=6, end=10)
        await _seed_thread("thread-due", expected_resolve_arc=1)

        plan = await generate_foreshadowing_schedule_plan(
            PID,
            target_chapter=6,
            max_items=1,
            plan_id="fsp-thread-due",
        )

        assert plan.current_arc_index == 1
        assert plan.items[0].source_id == "thread-due"
        assert "resolve_arc_due" in plan.items[0].reason_codes

    async def test_overdue_foreshadowing_high_priority(self, test_db: Path) -> None:
        await _seed_project()
        await _seed_arc("arc-0", arc_index=0, start=1, end=10)
        await _seed_foreshadowing(
            "f-overdue",
            description="旧港倒计时必须兑现",
            planted=1,
            expected=3,
        )

        plan = await generate_foreshadowing_schedule_plan(
            PID,
            target_chapter=8,
            max_items=1,
            plan_id="fsp-overdue",
        )

        assert plan.items[0].source_type == "foreshadowing"
        assert plan.items[0].source_id == "f-overdue"
        assert "foreshadowing_overdue" in plan.items[0].reason_codes

    async def test_planning_constraint_boosts_related_candidate(
        self, test_db: Path
    ) -> None:
        await _seed_project()
        await _seed_arc("arc-0", arc_index=0, start=1, end=5)
        await _seed_thread("plain", title="普通线索")
        await _seed_thread("boosted", title="灰塔信号")
        await _seed_constraint(
            "pc-boost",
            target_id="boosted",
            content="下一阶段必须推进 boosted / 灰塔信号。",
        )

        plan = await generate_foreshadowing_schedule_plan(
            PID,
            target_chapter=3,
            max_items=1,
            plan_id="fsp-boost",
        )

        assert plan.items[0].source_id == "boosted"
        assert "replan_backed" in plan.items[0].reason_codes

    async def test_duplicate_window_suppresses_recent_schedule(
        self, test_db: Path
    ) -> None:
        await _seed_project()
        await _seed_arc("arc-0", arc_index=0, start=1, end=20)
        await _seed_foreshadowing(
            "f-dup",
            description="重复调度伏笔",
            planted=1,
            expected=9,
            status="due",
        )
        await _seed_foreshadowing(
            "f-new",
            description="新的调度伏笔",
            planted=1,
            expected=10,
            status="due",
        )
        repo = ForeshadowingScheduleRepository()
        await repo.create(
            ForeshadowingSchedulePlan(
                plan_id="fsp-old",
                project_id=PID,
                target_chapter=9,
                items=[
                    ForeshadowingScheduleItem(
                        item_id="fsi-old",
                        plan_id="fsp-old",
                        project_id=PID,
                        item_order=0,
                        target_chapter=9,
                        source_type="foreshadowing",
                        source_id="f-dup",
                    )
                ],
            )
        )

        plan = await generate_foreshadowing_schedule_plan(
            PID,
            target_chapter=10,
            max_items=2,
            duplicate_window=3,
            plan_id="fsp-dedupe",
        )

        assert "f-dup" not in {item.source_id for item in plan.items}
        assert "f-new" in {item.source_id for item in plan.items}

    async def test_schedule_plan_persists_and_reads_back(self, test_db: Path) -> None:
        await _seed_project()
        await _seed_arc("arc-0", arc_index=0, start=1, end=5)
        await _seed_thread("main", is_mainline=True)

        plan = await generate_foreshadowing_schedule_plan(
            PID,
            target_chapter=3,
            max_items=1,
            plan_id="fsp-persist",
        )
        repo = ForeshadowingScheduleRepository()
        await repo.create(plan)
        got = await repo.get("fsp-persist")
        recent = await repo.list_recent_items(PID, start_chapter=1, end_chapter=5)

        assert got is not None
        assert got.items[0].source_id == "main"
        assert recent[0].source_id == "main"
