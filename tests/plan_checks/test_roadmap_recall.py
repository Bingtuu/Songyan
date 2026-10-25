"""Roadmap recall rule for the five 霞飞路 classes.

The v4 chapters calibrate the scorer. They are not a re-run score.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from songyan.db.plan_fact_loader import (
    XIAFEI_PROJECT_ID,
    bundled_xiafei_fixture,
    load_plan_fact_fixture,
)
from songyan.plan_checks.claim_check import ClaimAnchor, ClaimVerdict
from songyan.plan_checks.gate import PlanFactGateReport
from songyan.plan_checks.roadmap_recall import (
    ROADMAP_CLASSES,
    blocked_rerun_scoreboard,
    score_chapters,
    score_reports,
)
from songyan.plan_checks.typed_attributes import AttributeExtract

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "xiafei_jiuan"
_CLASS_IDS = tuple(spec.class_id for spec in ROADMAP_CLASSES)


@pytest.fixture
async def xiafei_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Load the approved cards into a temporary database."""
    import songyan.db.connection as conn_mod
    from songyan.db.migrations import init_schema

    db_path = tmp_path / "xiafei.db"
    monkeypatch.setattr(
        conn_mod,
        "settings",
        type("S", (), {"database_url": f"sqlite:///{db_path}"})(),
    )
    await init_schema(db_path)
    await load_plan_fact_fixture(bundled_xiafei_fixture())


def _chapters() -> dict[int, str]:
    return {
        number: (_FIXTURE / f"ch0{number}.md").read_text(encoding="utf-8")
        for number in (1, 2, 3)
    }


def _extracts() -> list[AttributeExtract]:
    payload = json.loads((_FIXTURE / "v4_extracts.json").read_text(encoding="utf-8"))
    rows: list[AttributeExtract] = []
    for chapter_rows in payload["chapters"].values():
        rows.extend(AttributeExtract.model_validate(row) for row in chapter_rows)
    return rows


def _anchors() -> list[ClaimAnchor]:
    payload = json.loads((_FIXTURE / "claim_anchors.json").read_text(encoding="utf-8"))
    return [ClaimAnchor.model_validate(row) for row in payload]


def _empty_reports() -> dict[int, PlanFactGateReport]:
    return {
        chapter: PlanFactGateReport(project_id=XIAFEI_PROJECT_ID, chapter=chapter)
        for chapter in (1, 2, 3)
    }


def _occurred(**flags: bool) -> dict[str, bool]:
    base = dict.fromkeys(_CLASS_IDS, False)
    base.update(flags)
    return base


class TestRoadmapRecallRule:
    def test_blocked_board_has_five_unscored_rows(self) -> None:
        board = blocked_rerun_scoreboard(reason="no key")

        assert board.status == "blocked"
        assert board.recalled is None
        assert board.denominator == 5
        assert [row.class_id for row in board.classes] == list(_CLASS_IDS)
        assert {row.verdict for row in board.classes} == {"unscored"}
        assert all(row.recall is None and row.occurred is None for row in board.classes)

    def test_non_occurrence_recalls_without_a_gate_flag(self) -> None:
        board = score_reports(
            _empty_reports(),
            _occurred(),
            anchors_supplied=False,
            extracts_supplied=False,
        )

        assert board.status == "scored"
        assert board.recalled == 5
        assert [row.verdict for row in board.classes] == ["recalled"] * 5
        assert all(row.intercepted is False for row in board.classes)

    def test_occurrence_without_a_signal_is_a_miss(self) -> None:
        board = score_reports(
            _empty_reports(),
            _occurred(T5=True),
            anchors_supplied=True,
            extracts_supplied=True,
        )
        by_id = {row.class_id: row for row in board.classes}

        assert board.recalled == 4
        assert by_id["T5"].verdict == "miss"
        assert by_id["T5"].recall is False
        assert by_id["T1"].verdict == "recalled"

    def test_unmentioned_claim_is_not_t2_without_anchors(self) -> None:
        reports = _empty_reports()
        reports[2] = reports[2].model_copy(
            update={
                "claim_verdicts": [
                    ClaimVerdict(
                        claim_id="claim-ch2-blunt",
                        text="正式验尸报告写有死者后脑钝器伤",
                        status="unmentioned",
                    )
                ]
            }
        )
        board = score_reports(
            reports,
            _occurred(T2=True),
            anchors_supplied=False,
            extracts_supplied=False,
        )
        blunt = next(row for row in board.classes if row.class_id == "T2")

        assert blunt.intercepted is False
        assert blunt.verdict == "miss"

    def test_unmentioned_claim_counts_for_t2_when_anchors_were_supplied(self) -> None:
        reports = _empty_reports()
        reports[2] = reports[2].model_copy(
            update={
                "claim_verdicts": [
                    ClaimVerdict(
                        claim_id="claim-ch2-blunt",
                        text="正式验尸报告写有死者后脑钝器伤",
                        status="unmentioned",
                    )
                ]
            }
        )
        board = score_reports(
            reports,
            _occurred(T2=True),
            anchors_supplied=True,
            extracts_supplied=False,
        )
        blunt = next(row for row in board.classes if row.class_id == "T2")

        assert blunt.intercepted is True
        assert blunt.verdict == "recalled"
        assert "未提及" in blunt.basis

    def test_missing_chapter_does_not_invent_a_total(self) -> None:
        reports = {1: _empty_reports()[1]}
        board = score_reports(
            reports,
            _occurred(),
            anchors_supplied=False,
            extracts_supplied=False,
        )

        assert board.status == "unscored"
        assert board.recalled is None
        assert {row.verdict for row in board.classes} == {"unscored"}

    async def test_v4_fixture_calibration_is_five_of_five(self, xiafei_db: None) -> None:
        """Known v4 drift, with the fixture extracts and anchors, is all intercepted."""
        board = await score_chapters(
            _chapters(),
            project_id=XIAFEI_PROJECT_ID,
            extracts=_extracts(),
            anchors=_anchors(),
            occurred=_occurred(T1=True, T5=True, T4=True, T2=True, T6=True),
        )
        by_id = {row.class_id: row for row in board.classes}

        assert board.status == "scored"
        assert board.recalled == 5
        assert by_id["T1"].intercepted is True
        assert by_id["T5"].intercepted is True
        assert by_id["T4"].intercepted is True
        assert by_id["T2"].intercepted is True
        assert by_id["T6"].intercepted is True
        assert all(row.verdict == "recalled" for row in board.classes)

    async def test_v4_live_inputs_do_not_intercept_hook_ownership(
        self, xiafei_db: None
    ) -> None:
        board = await score_chapters(
            _chapters(),
            project_id=XIAFEI_PROJECT_ID,
            occurred=_occurred(T1=True, T5=True, T4=True, T2=True, T6=True),
        )
        by_id = {row.class_id: row for row in board.classes}

        assert board.extracts_supplied is False
        assert board.anchors_supplied is False
        assert by_id["T5"].intercepted is False
        assert by_id["T5"].verdict == "miss"
        assert by_id["T1"].intercepted is True
        assert by_id["T2"].intercepted is True
        assert by_id["T4"].intercepted is True
        assert by_id["T6"].intercepted is True
        assert board.recalled == 4
