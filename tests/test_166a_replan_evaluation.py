"""Task 166a: arc outcome evaluation and draft ReplanProposal tests."""

from __future__ import annotations

from pathlib import Path

from songyan.db.context_repo import SummaryRepository
from songyan.db.migrations import _EXPECTED_TABLES
from songyan.db.narrative_repo import NarrativeRepository
from songyan.db.replan_repo import ReplanProposalRepository
from songyan.db.repository import ChapterVersionRepository, ProjectRepository
from songyan.db.review_repo import LiteraryObservationRepository
from songyan.db.text_cleanliness_repo import (
    TextCleanlinessMetricRepository,
    TextCleanlinessMetricRow,
)
from songyan.evals.replan_evaluation import (
    build_replan_proposal,
    evaluate_arc_outcome,
)
from songyan.models import (
    ArcPlan,
    ChapterSummary,
    ChapterVersion,
    LiteraryAuditResult,
    LiteraryObservation,
    PlotThread,
    ProjectSetting,
    ReplanProposal,
)

PID = "proj-166a"


async def _seed_project(project_id: str = PID) -> str:
    await ProjectRepository().create(
        ProjectSetting(title=project_id, genre_id="scifi", protagonist_name="林渊"),
        project_id=project_id,
    )
    return project_id


async def _seed_arc(
    project_id: str = PID,
    *,
    threads_to_open: list[str] | None = None,
    threads_to_resolve: list[str] | None = None,
) -> ArcPlan:
    arc = ArcPlan(
        arc_id=f"arc-{project_id}-0",
        project_id=project_id,
        arc_index=0,
        start_chapter=1,
        end_chapter=5,
        arc_goal="验证第一弧目标",
        threads_to_open=threads_to_open or [],
        threads_to_resolve=threads_to_resolve or [],
        is_mainline=True,
    )
    await NarrativeRepository().add_arc_plan(arc)
    return arc


async def _seed_thread(
    thread_id: str,
    project_id: str = PID,
    *,
    status: str = "planned",
    opened_chapter: int | None = None,
    expected_resolve_arc: int | None = 0,
) -> PlotThread:
    thread = PlotThread(
        thread_id=thread_id,
        project_id=project_id,
        title=thread_id,
        is_mainline=True,
        opened_chapter=opened_chapter,
        expected_resolve_arc=expected_resolve_arc,
        status=status,  # type: ignore[arg-type]
        last_status_chapter=opened_chapter,
        last_status_version_id=f"v-{thread_id}" if opened_chapter else None,
    )
    await NarrativeRepository().add_thread(thread)
    return thread


async def _seed_summary(project_id: str = PID, chapter: int = 1) -> None:
    await SummaryRepository().create(
        ChapterSummary(
            chapter_number=chapter,
            summary=f"第 {chapter} 章完成弧目标推进。",
            key_events=["推进主线"],
        ),
        project_id,
        summary_id=f"sum-{project_id}-{chapter}",
    )


async def _seed_version(project_id: str, chapter: int, *, version_number: int) -> str:
    version_id = f"v-{project_id}-{chapter}-{version_number}"
    await ChapterVersionRepository().create(
        ChapterVersion(
            version_id=version_id,
            project_id=project_id,
            chapter_number=chapter,
            version_number=version_number,
            version_type="accepted",
            content="干净正文。",
            word_count=4,
        )
    )
    return version_id


async def _seed_clean_text_metric(project_id: str, chapter: int) -> None:
    version_id = await _seed_version(project_id, chapter, version_number=chapter)
    await TextCleanlinessMetricRepository().upsert(
        TextCleanlinessMetricRow(
            project_id=project_id,
            chapter_number=chapter,
            version_id=version_id,
        )
    )


async def _seed_literary_observation(
    project_id: str,
    chapter: int,
    *,
    observation_type: str | None = None,
    description: str = "",
    conceptual_score: float = 8.0,
) -> None:
    version_id = await _seed_version(project_id, chapter, version_number=chapter + 100)
    observations: list[LiteraryObservation] = []
    if observation_type is not None:
        observations.append(
            LiteraryObservation(
                observation_id=f"lit-obs-{project_id}-{chapter}",
                observation_type=observation_type,  # type: ignore[arg-type]
                description=description,
                recommendation="转为后续规划约束。",
            )
        )
    await LiteraryObservationRepository().create(
        LiteraryAuditResult(
            observations=observations,
            literary_quality_score=8.0,
            character_autonomy_score=8.0,
            conceptual_grounding_score=conceptual_score,
            fissure_preservation_score=8.0,
            summary=description,
        ),
        observation_id=f"lit-{project_id}-{chapter}",
        version_id=version_id,
    )


class TestReplanSchema:
    async def test_tables_registered(self, test_db: Path) -> None:
        assert "replan_proposals" in _EXPECTED_TABLES
        assert "replan_actions" in _EXPECTED_TABLES


class TestArcOutcomeEvaluation:
    async def test_no_skeleton_returns_noop_proposal(self, test_db: Path) -> None:
        await _seed_project()

        evaluation = await evaluate_arc_outcome(PID, chapter_range=(1, 5))
        proposal = build_replan_proposal(evaluation, proposal_id="rp-noop")

        assert evaluation.has_skeleton is False
        assert evaluation.risk_level == "none"
        assert proposal.status == "draft"
        assert proposal.actions == []

        await ReplanProposalRepository().create(proposal)
        got = await ReplanProposalRepository().get("rp-noop")
        assert got is not None
        assert got.actions == []

    async def test_fulfilled_arc_generates_low_risk_proposal(
        self, test_db: Path
    ) -> None:
        await _seed_project()
        await _seed_arc(threads_to_open=["t-open"], threads_to_resolve=["t-resolve"])
        await _seed_thread("t-open", status="opened", opened_chapter=2)
        await _seed_thread("t-resolve", status="resolved", opened_chapter=1)
        await _seed_summary(chapter=1)

        evaluation = await evaluate_arc_outcome(PID, arc_index=0)
        proposal = build_replan_proposal(evaluation, proposal_id="rp-low")

        assert evaluation.has_skeleton is True
        assert evaluation.risk_level == "low"
        assert evaluation.unopened_threads == []
        assert evaluation.unresolved_threads == []
        assert proposal.actions == []
        assert "No draft replan action" in proposal.summary

    async def test_unresolved_thread_generates_replan_action(
        self, test_db: Path
    ) -> None:
        await _seed_project()
        await _seed_arc(threads_to_resolve=["t-main"])
        await _seed_thread("t-main", status="advanced", opened_chapter=2)

        evaluation = await evaluate_arc_outcome(PID, arc_index=0)
        proposal = build_replan_proposal(evaluation, proposal_id="rp-unresolved")

        assert evaluation.risk_level == "high"
        assert evaluation.unresolved_threads == ["t-main"]
        assert len(proposal.actions) == 1
        action = proposal.actions[0]
        assert action.target_type == "plot_thread"
        assert action.target_id == "t-main"
        assert action.field == "expected_resolve_arc"
        assert action.new_value == 1

        before_arc = (await NarrativeRepository().list_arc_plans(PID))[0]
        before_thread = await NarrativeRepository().get_thread("t-main")
        await ReplanProposalRepository().create(proposal)
        after_arc = (await NarrativeRepository().list_arc_plans(PID))[0]
        after_thread = await NarrativeRepository().get_thread("t-main")

        assert before_arc == after_arc
        assert before_thread == after_thread
        got = await ReplanProposalRepository().get("rp-unresolved")
        assert got is not None
        assert got.actions[0].target_id == "t-main"

    async def test_style_debt_generates_style_constraint_when_metrics_pass(
        self, test_db: Path
    ) -> None:
        await _seed_project()
        await _seed_arc()
        await _seed_clean_text_metric(PID, 1)
        await _seed_clean_text_metric(PID, 2)
        await _seed_literary_observation(PID, 1, conceptual_score=8.0)
        await _seed_literary_observation(
            PID,
            2,
            observation_type="ai_rhythm_pattern",
            description="句式模型化明显，反复使用不是 A，是 B。",
            conceptual_score=8.0,
        )

        evaluation = await evaluate_arc_outcome(PID, arc_index=0)
        proposal = build_replan_proposal(evaluation, proposal_id="rp-style")

        assert "ai_rhythm_pattern" in evaluation.style_debt_signals
        assert evaluation.metric_warnings == []
        style_actions = [
            action
            for action in proposal.actions
            if action.target_type == "style_constraint"
        ]
        assert len(style_actions) == 1
        assert style_actions[0].field == "style_constraints"
        assert "模型化句式" in style_actions[0].new_value

    async def test_persisted_proposals_can_be_listed_with_actions(
        self, test_db: Path
    ) -> None:
        await _seed_project()
        await _seed_arc(threads_to_open=["t-planned"])
        await _seed_thread("t-planned", status="planned")

        proposal: ReplanProposal = build_replan_proposal(
            await evaluate_arc_outcome(PID, arc_index=0),
            proposal_id="rp-list",
        )
        await ReplanProposalRepository().create(proposal)

        listed = await ReplanProposalRepository().list_by_project(
            PID,
            status="draft",
            include_actions=True,
        )

        assert [item.proposal_id for item in listed] == ["rp-list"]
        assert listed[0].actions[0].field == "status"
        assert listed[0].actions[0].new_value == "opened"
