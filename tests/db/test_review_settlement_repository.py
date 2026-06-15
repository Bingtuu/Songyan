"""Review and settlement repository tests."""

from __future__ import annotations

from pathlib import Path

import aiosqlite
import pytest

from songyan.db import (
    ChapterVersionRepository,
    CharacterRepository,
    CreativeBriefRepository,
    ForeshadowingRepository,
    LiteraryObservationRepository,
    NumericalLedgerRepository,
    ProjectRepository,
    ReviewReportRepository,
    SettingSnapshotRepository,
)
from songyan.db.migrations import init_schema
from songyan.models import (
    ChapterGoal,
    ChapterVersion,
    Character,
    CreativeBrief,
    ForeshadowingItem,
    Increment,
    LiteraryAuditResult,
    LiteraryObservation,
    LLMAuditResult,
    MergedReviewReport,
    NewSetting,
    NumericalUpdate,
    ProjectSetting,
    ReviewCategory,
    ReviewIssue,
    RuleAuditResult,
    Tension,
)

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def repo_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    import songyan.db.connection as conn_mod

    db_path = tmp_path / "repo.db"
    monkeypatch.setattr(
        conn_mod,
        "settings",
        type("S", (), {"database_url": f"sqlite:///{db_path}"})(),
    )
    await init_schema(db_path)
    return db_path


async def _seed_project(project_id: str = "p1") -> None:
    await ProjectRepository().create(
        ProjectSetting(genre_id="xuanhuan", protagonist_name="Lin Feng"),
        project_id,
    )


async def _seed_character(character_id: str = "c1", project_id: str = "p1") -> None:
    await CharacterRepository().create(
        Character(character_id=character_id, project_id=project_id, name="Lin Feng")
    )


async def _seed_version(version_id: str = "v1", project_id: str = "p1") -> None:
    await ChapterVersionRepository().create(
        ChapterVersion(version_id=version_id, project_id=project_id, chapter_number=1)
    )


class TestReviewRepositories:
    async def test_creative_brief_create_and_get(self, repo_db: Path) -> None:
        await _seed_project()
        goal = ChapterGoal(chapter_number=1, target_events=["enter trial"])
        brief = CreativeBrief(
            mode_id="webnovel",
            chapter_goal=goal,
            creative_intent="pressure through scarcity",
            required_tensions=[
                Tension(
                    tension_id="t1",
                    description="mentor withholds truth",
                    tension_type="information_asymmetry",
                )
            ],
            forbidden_patterns=["easy win"],
        )

        await CreativeBriefRepository().create(brief, "b1", "p1", 1)
        saved = await CreativeBriefRepository().get("b1")

        assert saved is not None
        assert saved.chapter_goal.target_events == ["enter trial"]
        assert saved.required_tensions[0].tension_id == "t1"
        assert saved.forbidden_patterns == ["easy win"]

    async def test_creative_brief_get_missing_returns_none(self, repo_db: Path) -> None:
        assert await CreativeBriefRepository().get("missing") is None

    async def test_review_report_create_and_get_by_version(self, repo_db: Path) -> None:
        await _seed_project()
        await _seed_version()
        issue = ReviewIssue(
            issue_id="i1",
            category=ReviewCategory.NARRATIVE_HOOK,
            severity="major",
            evidence_quote="opening is static",
            evidence_location="p1",
            issue_description="No action in opening.",
        )
        report = MergedReviewReport(
            chapter_version_id="v1",
            rule_audit=RuleAuditResult(ai_tell_count=2, has_opening_hook=False),
            llm_audit=LLMAuditResult(issues=[issue], dimension_scores={"hook": 3.0}),
            issues=[issue],
            overall_score=6.5,
            ai_tell_count=2,
            dimension_scores={"hook": 3.0},
            summary="needs stronger hook",
        )

        await ReviewReportRepository().create(report, "r1")
        saved = await ReviewReportRepository().get_by_version("v1")

        assert saved is not None
        assert saved.rule_audit is not None
        assert saved.rule_audit.ai_tell_count == 2
        assert saved.llm_audit is not None
        assert saved.issues[0].category == ReviewCategory.NARRATIVE_HOOK
        assert saved.dimension_scores == {"hook": 3.0}

    async def test_review_report_get_missing_returns_none(self, repo_db: Path) -> None:
        assert await ReviewReportRepository().get_by_version("missing") is None

    async def test_literary_observation_create_and_get_by_version(self, repo_db: Path) -> None:
        await _seed_project()
        await _seed_version()
        result = LiteraryAuditResult(
            observations=[
                LiteraryObservation(
                    observation_id="o1",
                    observation_type="valuable_fissure",
                    description="productive ambiguity",
                    evidence_quote="he smiled without answering",
                    preserve=True,
                )
            ],
            literary_quality_score=7.5,
            summary="keep the ambiguity",
        )

        await LiteraryObservationRepository().create(result, "o-report-1", "v1")
        saved = await LiteraryObservationRepository().get_by_version("v1")

        assert saved is not None
        assert saved.literary_quality_score == 7.5
        assert saved.observations[0].preserve is True


class TestSettlementRepositories:
    async def test_foreshadowing_create_update_status_and_list_active(self, repo_db: Path) -> None:
        await _seed_project()
        await _seed_version()
        repo = ForeshadowingRepository()
        await repo.create(
            ForeshadowingItem(
                foreshadowing_id="f1",
                description="black ring hums",
                planted_in_chapter=1,
                expected_resolve_chapter=5,
            ),
            "p1",
            source_version_id="v1",
        )

        active = await repo.list_active("p1")
        assert [item.foreshadowing_id for item in active] == ["f1"]

        await repo.update_status("f1", "resolved")
        assert await repo.list_active("p1") == []

    async def test_foreshadowing_foreign_key_violation_raises(self, repo_db: Path) -> None:
        with pytest.raises(aiosqlite.IntegrityError):
            await ForeshadowingRepository().create(
                ForeshadowingItem(
                    foreshadowing_id="bad",
                    description="bad",
                    planted_in_chapter=1,
                ),
                "missing",
            )

    async def test_setting_snapshot_create_and_list_by_project(self, repo_db: Path) -> None:
        await _seed_project()
        await SettingSnapshotRepository().create(
            NewSetting(
                setting_name="Qingxuan Sect",
                description="cloud sect",
                source_quote="Qingxuan stands in the clouds",
                setting_key="sect_qingxuan",
            ),
            "p1",
            "s1",
        )

        settings = await SettingSnapshotRepository().list_by_project("p1")

        assert settings[0].setting_key == "sect_qingxuan"
        assert settings[0].source_quote == "Qingxuan stands in the clouds"

    async def test_numerical_ledger_create_and_get_latest(self, repo_db: Path) -> None:
        await _seed_project()
        await _seed_character()
        repo = NumericalLedgerRepository()
        await repo.create(
            NumericalUpdate(
                character_id="c1",
                attribute_name="spirit_stones",
                opening_value=10,
                increments=[Increment(amount=5, source="reward", source_quote="won five stones")],
                closing_value=15,
            ),
            "p1",
            1,
            "n1",
        )
        await repo.create(
            NumericalUpdate(
                character_id="c1",
                attribute_name="spirit_stones",
                opening_value=15,
                closing_value=12,
            ),
            "p1",
            2,
            "n2",
        )

        latest = await repo.get_latest("c1", "spirit_stones")

        assert latest is not None
        assert latest.opening_value == 15
        assert latest.closing_value == 12

    async def test_numerical_ledger_get_missing_returns_none(self, repo_db: Path) -> None:
        assert await NumericalLedgerRepository().get_latest("missing", "qi") is None


class TestRepositoryIntegration:
    async def test_project_character_version_review_chain(self, repo_db: Path) -> None:
        await _seed_project()
        await _seed_character()
        await _seed_version()
        await ReviewReportRepository().create(
            MergedReviewReport(chapter_version_id="v1", overall_score=8.0),
            "r1",
        )

        project = await ProjectRepository().get("p1")
        characters = await CharacterRepository().list_by_project("p1")
        version = await ChapterVersionRepository().get("v1")
        report = await ReviewReportRepository().get_by_version("v1")

        assert project is not None
        assert [c.character_id for c in characters] == ["c1"]
        assert version is not None
        assert report is not None
        assert report.overall_score == 8.0
