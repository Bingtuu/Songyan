"""canon-v4 chapters versus approved 霞飞路 cards.

The five roadmap classes are T1/T5 attribute drift, T4 mechanism direction,
T2 omission, and T6 era. Expected flags are listed in
docs/xiafei-plan-checks.md. Extracts and claim anchors are explicit
annotations of the drifted prose, not a second canon.
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
from songyan.db.plan_fact_repo import PlanFactRepository
from songyan.plan_checks.claim_check import AnchoredClaimJudge, ClaimAnchor, verify_chapter_claims
from songyan.plan_checks.must_mention import check_must_mention
from songyan.plan_checks.typed_attributes import AttributeExtract, compare_typed_attributes

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "xiafei_jiuan"


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


def _chapter(number: int) -> str:
    return (_FIXTURE / f"ch0{number}.md").read_text(encoding="utf-8")


def _extracts() -> list[AttributeExtract]:
    payload = json.loads((_FIXTURE / "v4_extracts.json").read_text(encoding="utf-8"))
    rows: list[AttributeExtract] = []
    for chapter_rows in payload["chapters"].values():
        rows.extend(AttributeExtract.model_validate(row) for row in chapter_rows)
    return rows


def _anchors() -> list[ClaimAnchor]:
    payload = json.loads((_FIXTURE / "claim_anchors.json").read_text(encoding="utf-8"))
    return [ClaimAnchor.model_validate(row) for row in payload]


class TestXiafeiV4Recall:
    async def test_five_roadmap_classes_are_flagged(self, xiafei_db: None) -> None:
        repo = PlanFactRepository()
        clues = await repo.list_canon_clues(XIAFEI_PROJECT_ID)
        attributes = await repo.list_canon_attributes(XIAFEI_PROJECT_ID)
        events = await repo.list_canon_events(XIAFEI_PROJECT_ID)
        judge = AnchoredClaimJudge(_anchors())

        missing: dict[int, set[tuple[str, tuple[str, ...]]]] = {}
        for chapter in (1, 2, 3):
            found = check_must_mention(clues, chapter, _chapter(chapter))
            missing[chapter] = {(row.point_id, tuple(row.missing_terms)) for row in found}
        mismatches = {
            (row.chapter, row.entity_id, row.key, row.extract_value)
            for row in compare_typed_attributes(attributes, _extracts())
        }
        verdicts = []
        for chapter in (1, 2, 3):
            verdicts.extend(
                await verify_chapter_claims(events, chapter, _chapter(chapter), judge=judge)
            )
        by_claim = {row.claim_id: row.status for row in verdicts}

        # T1 证物属性漂移：ch2 改了方向和数量，并丢掉登记方向。
        assert ("clue-scratch", ("右向左",)) in missing[2]
        assert (2, "xiafei-scratch", "direction", "自内向外") in mismatches
        assert (2, "xiafei-scratch", "count", "2") in mismatches
        assert by_claim["claim-ch2-scratch"] == "contradicted"
        assert ("clue-scratch", ("右向左",)) not in missing[1]
        assert by_claim["claim-ch1-scratch"] == "supported"

        # T2 证据遗漏：ch2 报告没有钝器伤。
        assert ("clue-blunt", ("钝器伤",)) in missing[2]
        assert ("clue-blunt", ("钝器伤",)) not in missing[1]
        assert by_claim["claim-ch2-blunt"] == "unmentioned"
        assert by_claim["claim-ch1-blunt"] == "supported"

        # T4 机制方向：ch3 改成从外往内拉，登记的「往外拉」不见了。
        assert ("clue-mechanism", ("往外拉",)) in missing[3]
        assert ("clue-mechanism", ("往外拉",)) not in missing[2]
        assert (3, "xiafei-mechanism", "direction", "从外往内拉") in mismatches
        assert (2, "xiafei-mechanism", "direction", "往外拉") not in mismatches
        assert by_claim["claim-ch3-pull"] == "contradicted"
        assert by_claim["claim-ch2-pull"] == "supported"

        # T5 证物归属漂移：钩状弧线仍被提到，但 ch3 把它放到横杆拓片上。
        assert ("clue-hook", ("门框暗处",)) not in missing[2]
        assert (3, "xiafei-hook", "ownership", "横杆拓片") in mismatches
        assert (2, "xiafei-hook", "ownership", "门框暗处") not in mismatches
        assert by_claim["claim-ch3-hook"] == "contradicted"
        assert by_claim["claim-ch2-hook"] == "supported"

        # T6 时代时间线：ch1 用锦州代替九一八前，ch3 的三月与计划一致。
        assert ("clue-era", ("九一八",)) in missing[1]
        assert (1, "xiafei-era", "time_anchor", "1931年末·日军进逼锦州") in mismatches
        assert (3, "xiafei-case-time", "time_anchor", "1931-03") not in mismatches
        assert by_claim["claim-ch1-era"] == "contradicted"
        assert by_claim["claim-ch3-date"] == "supported"

        # 章内机制推理（不计入路线图五类）：ch1 把右向左说成方向反了。
        assert by_claim["claim-ch1-physics"] == "contradicted"

        for verdict in verdicts:
            if verdict.citation:
                assert verdict.citation in _chapter(verdict.chapter or 0)
