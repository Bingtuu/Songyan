"""Read-only plan gate on the chapter review path.

The gate reads approved cards for one project and calls the three existing
checkers. It does not write plan canon or the settlement tables.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from songyan.db.connection import get_db
from songyan.db.plan_fact_loader import (
    XIAFEI_PROJECT_ID,
    bundled_xiafei_fixture,
    load_plan_fact_fixture,
)
from songyan.db.plan_fact_repo import PlanFactRepository
from songyan.db.repository import ProjectRepository
from songyan.models.chapter import ChapterVersion
from songyan.models.plan_facts import (
    PlanAttribute,
    PlanClaim,
    PlanClue,
    PlanEntity,
    PlanEvent,
)
from songyan.models.project import ProjectSetting
from songyan.plan_checks.claim_check import ClaimAnchor
from songyan.plan_checks.gate import run_plan_fact_gate
from songyan.plan_checks.typed_attributes import AttributeExtract
from songyan.workflows._nodes import rule_auditor_node

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "xiafei_jiuan"
_CHAPTER = "横杆刮痕走向自内向外。"
_COUNT_TABLES = (
    "plan_entities",
    "plan_attributes",
    "plan_events",
    "plan_time_anchors",
    "plan_clues",
    "character_states",
    "setting_snapshots",
)


@pytest.fixture
async def gate_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point get_db() at a temporary schema."""
    import songyan.db.connection as conn_mod
    from songyan.db.migrations import init_schema

    db_path = tmp_path / "gate.db"
    monkeypatch.setattr(
        conn_mod,
        "settings",
        type("S", (), {"database_url": f"sqlite:///{db_path}"})(),
    )
    await init_schema(db_path)


async def _counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    async with get_db() as conn:
        for table in _COUNT_TABLES:
            cursor = await conn.execute(f"SELECT COUNT(*) FROM {table}")
            row = await cursor.fetchone()
            assert row is not None
            counts[table] = int(row[0])
    return counts


async def _seed_mixed_cards() -> None:
    """Approved and pending cards in two projects."""
    projects = ProjectRepository()
    setting = ProjectSetting(genre_id="scifi", protagonist_name="陈照")
    await projects.create(setting, "p1")
    await projects.create(setting, "p2")
    repo = PlanFactRepository()
    await repo.write_entity(
        PlanEntity(
            entity_id="ent-scratch",
            project_id="p1",
            entity_type="object",
            aliases=["刮痕"],
        )
    )
    await repo.write_attribute(
        PlanAttribute(
            attribute_id="attr-dir",
            project_id="p1",
            entity_id="ent-scratch",
            key="direction",
            value="右向左",
            valid_from_ch=1,
            valid_to_ch=3,
            source="human",
            approval_status="approved",
        )
    )
    await repo.write_attribute(
        PlanAttribute(
            attribute_id="attr-dir-pending",
            project_id="p1",
            entity_id="ent-scratch",
            key="direction",
            value="自内向外",
            valid_from_ch=1,
            valid_to_ch=3,
            source="human",
            approval_status="pending",
        )
    )
    await repo.write_event(
        PlanEvent(
            event_id="evt-ok",
            project_id="p1",
            ch=2,
            claims=[PlanClaim(claim_id="claim-scratch", text="刮痕方向为右向左")],
            approval_status="approved",
        )
    )
    await repo.write_event(
        PlanEvent(
            event_id="evt-pending",
            project_id="p1",
            ch=2,
            claims=[PlanClaim(claim_id="claim-pending", text="待审主张不该出现")],
            approval_status="pending",
        )
    )
    await repo.write_clue(
        PlanClue(
            clue_id="clue-ok",
            project_id="p1",
            planted_ch=1,
            must_mention_in=[2],
            label="刮痕",
            mention_terms=["右向左"],
            approval_status="approved",
        )
    )
    await repo.write_clue(
        PlanClue(
            clue_id="clue-pending",
            project_id="p1",
            planted_ch=1,
            must_mention_in=[2],
            label="待审",
            mention_terms=["待审用语"],
            approval_status="pending",
        )
    )
    await repo.write_clue(
        PlanClue(
            clue_id="clue-other",
            project_id="p2",
            planted_ch=1,
            must_mention_in=[2],
            label="别的项目",
            mention_terms=["别的项目"],
            approval_status="approved",
        )
    )


def _extracts() -> list[AttributeExtract]:
    return [
        AttributeExtract(
            entity_id="ent-scratch",
            key="direction",
            value="自内向外",
            chapter=1,
        ),
        AttributeExtract(
            entity_id="ent-scratch",
            key="direction",
            value="自内向外",
            chapter=2,
        ),
        AttributeExtract(
            entity_id="ent-new",
            key="direction",
            value="北",
            chapter=2,
        ),
    ]


def _anchors() -> list[ClaimAnchor]:
    return [
        ClaimAnchor(
            claim_id="claim-scratch",
            contradict_terms=["自内向外"],
            support_terms=["右向左"],
        )
    ]


class TestPlanFactGate:
    async def test_only_approved_cards_for_this_chapter_are_checked(
        self, gate_db: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def _refuse_model(*_args: object, **_kwargs: object) -> str:
            raise AssertionError("the default gate must not call a model")

        monkeypatch.setattr("songyan.llm.client.call_llm", _refuse_model)
        await _seed_mixed_cards()

        chapter_two = await run_plan_fact_gate(
            "p1",
            2,
            _CHAPTER,
            extracts=_extracts(),
            anchors=_anchors(),
        )
        chapter_one = await run_plan_fact_gate(
            "p1",
            1,
            _CHAPTER,
            extracts=_extracts(),
            anchors=_anchors(),
        )

        assert chapter_two.passed is False
        missing = [
            (row.point_id, tuple(row.missing_terms)) for row in chapter_two.missing_mentions
        ]
        assert missing == [("clue-ok", ("右向左",))]
        assert [row.claim_id for row in chapter_two.claim_verdicts] == ["claim-scratch"]
        assert chapter_two.claim_verdicts[0].status == "contradicted"
        assert "自内向外" in chapter_two.claim_verdicts[0].citation
        assert [
            (row.attribute_id, row.chapter, row.approved_value, row.extract_value)
            for row in chapter_two.attribute_mismatches
        ] == [("attr-dir", 2, "右向左", "自内向外")]

        assert [row.point_id for row in chapter_one.missing_mentions] == []
        assert chapter_one.claim_verdicts == []
        assert [
            (row.attribute_id, row.chapter) for row in chapter_one.attribute_mismatches
        ] == [("attr-dir", 1)]

    async def test_other_project_cards_stay_out(self, gate_db: None) -> None:
        await _seed_mixed_cards()

        report = await run_plan_fact_gate("p2", 2, _CHAPTER, extracts=_extracts())

        assert [row.point_id for row in report.missing_mentions] == ["clue-other"]
        assert report.claim_verdicts == []
        assert report.attribute_mismatches == []
        assert report.passed is False

    async def test_gate_does_not_write_canon_or_settlement(self, gate_db: None) -> None:
        await _seed_mixed_cards()
        before = await _counts()

        await run_plan_fact_gate(
            "p1",
            2,
            _CHAPTER,
            extracts=_extracts(),
            anchors=_anchors(),
        )

        assert await _counts() == before
        pending = await PlanFactRepository().list_pending_attributes("p1")
        assert [row.attribute_id for row in pending] == ["attr-dir-pending"]

    async def test_no_approved_cards_passes(self, gate_db: None) -> None:
        report = await run_plan_fact_gate("p-empty", 1, _CHAPTER)

        assert report.passed is True
        assert report.missing_mentions == []
        assert report.claim_verdicts == []
        assert report.attribute_mismatches == []

    async def test_v4_fixture_classes_still_flag(self, gate_db: None) -> None:
        await load_plan_fact_fixture(bundled_xiafei_fixture())
        extracts = _v4_extracts()
        anchors = _v4_anchors()
        missing: dict[int, set[tuple[str, tuple[str, ...]]]] = {}
        mismatches: set[tuple[int | None, str, str, str]] = set()
        by_claim: dict[str, str] = {}
        for chapter in (1, 2, 3):
            report = await run_plan_fact_gate(
                XIAFEI_PROJECT_ID,
                chapter,
                (_FIXTURE / f"ch0{chapter}.md").read_text(encoding="utf-8"),
                extracts=extracts,
                anchors=anchors,
            )
            missing[chapter] = {
                (row.point_id, tuple(row.missing_terms)) for row in report.missing_mentions
            }
            mismatches.update(
                (row.chapter, row.entity_id, row.key, row.extract_value)
                for row in report.attribute_mismatches
            )
            by_claim.update({row.claim_id: row.status for row in report.claim_verdicts})

        assert ("clue-scratch", ("右向左",)) in missing[2]
        assert (2, "xiafei-scratch", "direction", "自内向外") in mismatches
        assert (2, "xiafei-scratch", "count", "2") in mismatches
        assert by_claim["claim-ch2-scratch"] == "contradicted"

        assert ("clue-blunt", ("钝器伤",)) in missing[2]
        assert by_claim["claim-ch2-blunt"] == "unmentioned"

        assert ("clue-mechanism", ("往外拉",)) in missing[3]
        assert (3, "xiafei-mechanism", "direction", "从外往内拉") in mismatches
        assert by_claim["claim-ch3-pull"] == "contradicted"

        assert (3, "xiafei-hook", "ownership", "横杆拓片") in mismatches
        assert by_claim["claim-ch3-hook"] == "contradicted"

        assert ("clue-era", ("九一八",)) in missing[1]
        assert (1, "xiafei-era", "time_anchor", "1931年末·日军进逼锦州") in mismatches
        assert by_claim["claim-ch1-era"] == "contradicted"
        assert (3, "xiafei-case-time", "time_anchor", "1931-03") not in mismatches


class TestChapterReviewInvokesGate:
    async def test_rule_auditor_reads_approved_cards_only(self, gate_db: None) -> None:
        await _seed_mixed_cards()
        before = await _counts()
        version = ChapterVersion(
            version_id="v1",
            project_id="p1",
            chapter_number=2,
            content=_CHAPTER,
            word_count=12,
        )
        state = {
            "project_id": "p1",
            "chapter_number": 2,
            "current_version_id": "v1",
            "chapter_goal_id": "",
            "context_package": SimpleNamespace(mandatory_references=None),
            "_plan_attribute_extracts": [
                {
                    "entity_id": "ent-scratch",
                    "key": "direction",
                    "value": "自内向外",
                    "chapter": 2,
                },
                {
                    "entity_id": "ent-new",
                    "key": "direction",
                    "value": "北",
                    "chapter": 2,
                },
            ],
            "_plan_claim_anchors": [
                {"claim_id": "claim-scratch", "contradict_terms": ["自内向外"]},
            ],
        }

        with (
            patch(
                "songyan.workflows._nodes.load_version",
                new_callable=AsyncMock,
                return_value=version,
            ),
            patch("songyan.workflows._nodes.save_rule_audit", new_callable=AsyncMock) as save_audit,
        ):
            result = await rule_auditor_node(state)

        report = result["_plan_fact_gate"]
        assert result["status"] == "llm_auditing"
        assert "settlement_id" not in result
        assert report["passed"] is False
        assert [row["point_id"] for row in report["missing_mentions"]] == ["clue-ok"]
        assert [row["claim_id"] for row in report["claim_verdicts"]] == ["claim-scratch"]
        assert report["claim_verdicts"][0]["status"] == "contradicted"
        assert [row["attribute_id"] for row in report["attribute_mismatches"]] == ["attr-dir"]
        assert await _counts() == before
        save_audit.assert_awaited()

    async def test_missing_version_skips_the_gate(self) -> None:
        with patch(
            "songyan.workflows._nodes.load_version",
            new_callable=AsyncMock,
            return_value=None,
        ) as load_version:
            result = await rule_auditor_node({"current_version_id": "missing"})

        load_version.assert_awaited()
        assert result["status"] == "rule_auditor"
        assert result["error"] == "Version not found"
        assert "_plan_fact_gate" not in result

    async def test_live_state_does_not_score_typed_hook_drift(self, gate_db: None) -> None:
        """The review path leaves extracts and anchors unset.

        v4 chapter 3 puts the hook mark on the bar rubbing. Must-mention
        still runs. Typed ownership and the contradicted hook claim do
        not, until the caller supplies those inputs.
        """
        await load_plan_fact_fixture(bundled_xiafei_fixture())
        text = (_FIXTURE / "ch03.md").read_text(encoding="utf-8")
        version = ChapterVersion(
            version_id="v-ch3",
            project_id=XIAFEI_PROJECT_ID,
            chapter_number=3,
            content=text,
            word_count=len(text),
        )
        state = {
            "project_id": XIAFEI_PROJECT_ID,
            "chapter_number": 3,
            "current_version_id": "v-ch3",
            "chapter_goal_id": "",
            "context_package": SimpleNamespace(mandatory_references=None),
        }

        with (
            patch(
                "songyan.workflows._nodes.load_version",
                new_callable=AsyncMock,
                return_value=version,
            ),
            patch("songyan.workflows._nodes.save_rule_audit", new_callable=AsyncMock),
        ):
            result = await rule_auditor_node(state)

        report = result["_plan_fact_gate"]
        assert report["attribute_mismatches"] == []
        hook = next(row for row in report["claim_verdicts"] if row["claim_id"] == "claim-ch3-hook")
        assert hook["status"] == "unmentioned"
        assert any(row["point_id"] == "clue-mechanism" for row in report["missing_mentions"])

        supplied = await run_plan_fact_gate(
            XIAFEI_PROJECT_ID,
            3,
            text,
            extracts=_v4_extracts(),
            anchors=_v4_anchors(),
        )
        assert any(
            row.entity_id == "xiafei-hook" and row.key == "ownership"
            for row in supplied.attribute_mismatches
        )
        assert any(
            row.claim_id == "claim-ch3-hook" and row.status == "contradicted"
            for row in supplied.claim_verdicts
        )


def _v4_extracts() -> list[AttributeExtract]:
    payload = json.loads((_FIXTURE / "v4_extracts.json").read_text(encoding="utf-8"))
    rows: list[AttributeExtract] = []
    for chapter_rows in payload["chapters"].values():
        rows.extend(AttributeExtract.model_validate(row) for row in chapter_rows)
    return rows


def _v4_anchors() -> list[ClaimAnchor]:
    payload = json.loads((_FIXTURE / "claim_anchors.json").read_text(encoding="utf-8"))
    return [ClaimAnchor.model_validate(row) for row in payload]
