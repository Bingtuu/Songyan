"""Task 163: 概念预算约束测试."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

from songyan.agents.creative_director import _render_prompt, generate_creative_brief
from songyan.creative_modes.registry import load_creative_mode_profile
from songyan.db.continuity_repo import SettingTrackingRepository
from songyan.db.repository import ChapterVersionRepository, ProjectRepository
from songyan.db.review_repo import LiteraryObservationRepository
from songyan.evals.concept_budget import (
    ConceptLedgerEntry,
    ConceptualGroundingPoint,
    build_concept_budget_constraint,
    build_concept_budget_constraint_from_ledger,
    build_concept_ledger_from_rows,
    collect_concept_budget_report,
    detect_conceptual_grounding_tighten,
    render_concept_budget_section,
)
from songyan.genres.loader import load_genre_profile
from songyan.models import (
    ChapterGoal,
    ChapterVersion,
    LiteraryAuditResult,
    ProjectSetting,
)

PID = "proj-163"


async def _seed_project(project_id: str = PID) -> None:
    await ProjectRepository().create(
        ProjectSetting(
            title=f"Project {project_id}",
            genre_id="scifi",
            protagonist_name="林渊",
        ),
        project_id=project_id,
    )


async def _seed_setting(
    *,
    project_id: str = PID,
    key: str,
    name: str,
    introduced: int,
    last: int | None = None,
    status: str = "active",
    category: str = "background",
) -> None:
    await SettingTrackingRepository().create(
        tracking_id=f"st-{project_id}-{key}",
        project_id=project_id,
        setting_key=key,
        setting_name=name,
        description=f"{name}描述",
        introduced_in_chapter=introduced,
        category=category,
        status=status,
    )
    if last is not None and last != introduced:
        await SettingTrackingRepository().update_last_mentioned(
            f"st-{project_id}-{key}", last
        )


async def _seed_grounding_score(project_id: str, chapter: int, score: float) -> None:
    version_id = f"v-{project_id}-{chapter}"
    await ChapterVersionRepository().create(
        ChapterVersion(
            version_id=version_id,
            project_id=project_id,
            chapter_number=chapter,
            version_number=1,
            version_type="accepted",
            content="x",
            word_count=1,
        )
    )
    await LiteraryObservationRepository().create(
        LiteraryAuditResult(
            literary_quality_score=8.0,
            character_autonomy_score=8.0,
            conceptual_grounding_score=score,
            fissure_preservation_score=8.0,
        ),
        observation_id=f"obs-{project_id}-{chapter}",
        version_id=version_id,
    )


class TestConceptLedger:
    def test_builds_grounded_and_ungrounded_entries(self) -> None:
        rows = [
            {
                "setting_key": "concept.a",
                "setting_name": "概念A",
                "introduced_in_chapter": 1,
                "last_mentioned_chapter": 1,
                "status": "active",
                "category": "critical",
            },
            {
                "setting_key": "concept.b",
                "setting_name": "概念B",
                "introduced_in_chapter": 2,
                "last_mentioned_chapter": 5,
                "status": "active",
                "category": "background",
            },
        ]

        entries = build_concept_ledger_from_rows(rows, current_chapter=10)

        assert len(entries) == 2
        ungrounded = next(entry for entry in entries if entry.concept_key == "concept.a")
        grounded = next(entry for entry in entries if entry.concept_key == "concept.b")
        assert ungrounded.grounded is False
        assert grounded.grounded is True

    def test_ignores_future_and_archived_entries(self) -> None:
        rows = [
            {
                "setting_key": "future",
                "setting_name": "未来概念",
                "introduced_in_chapter": 99,
                "last_mentioned_chapter": 99,
                "status": "active",
            },
            {
                "setting_key": "archived",
                "setting_name": "归档概念",
                "introduced_in_chapter": 1,
                "last_mentioned_chapter": 1,
                "status": "archived",
            },
        ]

        assert build_concept_ledger_from_rows(rows, current_chapter=10) == []


class TestConstraintBuilder:
    def test_empty_ledger_returns_empty_constraint(self) -> None:
        assert build_concept_budget_constraint_from_ledger([]) == ""

    def test_normal_constraint_lists_ungrounded_concepts(self) -> None:
        entries = [
            ConceptLedgerEntry(
                concept_key="ark.first_resonator",
                concept_name="第一代共鸣器",
                introduced_chapter=3,
                last_referenced_chapter=3,
                grounded=False,
                category="critical",
            )
        ]

        text = build_concept_budget_constraint_from_ledger(entries, max_new_concepts=2)

        assert "概念预算约束" in text
        assert "新概念/新机构/新术语引入上限：2" in text
        assert "第一代共鸣器" in text
        assert "【设定推导】" in text

    def test_tighten_reduces_budget_to_one(self) -> None:
        text = build_concept_budget_constraint_from_ledger(
            [
                ConceptLedgerEntry(
                    concept_key="c",
                    concept_name="概念",
                    introduced_chapter=1,
                    grounded=True,
                )
            ],
            max_new_concepts=3,
            tighten=True,
        )

        assert "引入上限：1" in text
        assert "触发收紧" in text


class TestGroundingTrend:
    def test_detects_conceptual_grounding_drop(self) -> None:
        points = [
            ConceptualGroundingPoint(chapter=i + 1, conceptual_grounding_score=10.0)
            for i in range(10)
        ] + [
            ConceptualGroundingPoint(chapter=i + 11, conceptual_grounding_score=7.0)
            for i in range(5)
        ]

        assert detect_conceptual_grounding_tighten(points) is True

    def test_stable_grounding_does_not_tighten(self) -> None:
        points = [
            ConceptualGroundingPoint(chapter=i + 1, conceptual_grounding_score=8.0)
            for i in range(20)
        ]

        assert detect_conceptual_grounding_tighten(points) is False


class TestConceptBudgetIntegration:
    async def test_async_constraint_from_db(self, test_db: Path) -> None:
        await _seed_project()
        await _seed_setting(
            key="concept.unlanded",
            name="未落地概念",
            introduced=1,
            category="critical",
        )

        text = await build_concept_budget_constraint(PID, chapter_no=5)

        assert "概念预算约束" in text
        assert "未落地概念" in text

    async def test_grounding_drop_tightens_db_constraint(self, test_db: Path) -> None:
        project_id = "proj-163-tighten"
        await _seed_project(project_id)
        await _seed_setting(
            project_id=project_id,
            key="concept.stable",
            name="已有概念",
            introduced=1,
            last=2,
        )
        for chapter in range(1, 11):
            await _seed_grounding_score(project_id, chapter, 10.0)
        for chapter in range(11, 16):
            await _seed_grounding_score(project_id, chapter, 7.0)

        text = await build_concept_budget_constraint(project_id, chapter_no=16)

        assert "引入上限：1" in text
        assert "触发收紧" in text

    async def test_creative_director_prompt_injects_constraint(self, test_db: Path) -> None:
        await _seed_project()
        await _seed_setting(
            key="concept.prompt",
            name="提示概念",
            introduced=1,
            category="critical",
        )
        genre = load_genre_profile("scifi")
        mode = load_creative_mode_profile("webnovel")

        prompt = await _render_prompt(
            project_id=PID,
            project=ProjectSetting(genre_id="scifi", protagonist_name="林渊"),
            chapter_goal=ChapterGoal(chapter_number=5),
            genre_profile=genre,
            mode_profile=mode,
            characters=[],
            previous_summary="",
            seed_settings=[],
            narrative_ctx=None,
        )

        assert "概念预算约束" in prompt
        assert "提示概念" in prompt

    async def test_creative_brief_carries_constraint_to_writer(self, test_db: Path) -> None:
        await _seed_project()
        await _seed_setting(
            key="concept.writer",
            name="传递到 Writer 的概念",
            introduced=1,
            category="critical",
        )
        genre = load_genre_profile("scifi")
        mode = load_creative_mode_profile("webnovel")
        llm_response = """{
            "mode_id": "webnovel",
            "creative_intent": "推进冲突",
            "required_tensions": [],
            "forbidden_patterns": ["禁止空洞设定堆叠"],
            "allowed_fissures": [],
            "style_constraints": ["短句推进"],
            "reader_contract": "保持悬念"
        }"""

        with patch(
            "songyan.agents.creative_director.call_llm",
            new_callable=AsyncMock,
            return_value=llm_response,
        ):
            brief = await generate_creative_brief(
                project_id=PID,
                project=ProjectSetting(genre_id="scifi", protagonist_name="林渊"),
                chapter_goal=ChapterGoal(chapter_number=5),
                genre_profile=genre,
                mode_profile=mode,
                characters=[],
                previous_summary="",
                seed_settings=[],
                narrative_ctx=None,
            )

        assert any("概念预算约束" in item for item in brief.style_constraints)
        assert any("传递到 Writer 的概念" in item for item in brief.style_constraints)
        assert any("设定回收约束" in item for item in brief.style_constraints)

    async def test_no_ledger_prompt_falls_back_without_constraint(self, test_db: Path) -> None:
        project_id = "proj-163-empty"
        await _seed_project(project_id)
        genre = load_genre_profile("scifi")
        mode = load_creative_mode_profile("webnovel")

        prompt = await _render_prompt(
            project_id=project_id,
            project=ProjectSetting(genre_id="scifi", protagonist_name="林渊"),
            chapter_goal=ChapterGoal(chapter_number=1),
            genre_profile=genre,
            mode_profile=mode,
            characters=[],
            previous_summary="",
            seed_settings=[],
            narrative_ctx=None,
        )

        assert "概念预算约束" not in prompt

    async def test_report_counts_ungrounded_concepts(self, test_db: Path) -> None:
        await _seed_project()
        await _seed_setting(key="concept.report", name="报告概念", introduced=1)

        report = await collect_concept_budget_report(PID, current_chapter=5)
        rendered = render_concept_budget_section(report)

        assert report.ungrounded_count == 1
        assert "报告概念" in rendered
        assert "未落地 **1**" in rendered
