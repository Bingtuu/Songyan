"""Must-mention checker: registered phrases, not an open search."""

from __future__ import annotations

import pytest

from songyan.models.plan_facts import PlanClue
from songyan.plan_checks.must_mention import check_must_mention


def _clue(**updates: object) -> PlanClue:
    base: dict[str, object] = {
        "clue_id": "clue-blunt",
        "project_id": "p1",
        "planted_ch": 1,
        "must_mention_in": [1, 2],
        "label": "后脑钝器伤",
        "mention_terms": ["钝器伤"],
    }
    base.update(updates)
    return PlanClue.model_validate(base)


class TestMustMention:
    def test_reports_a_missing_registered_phrase(self) -> None:
        missing = check_must_mention([_clue()], 2, "报告只写了毒物和门闩。")

        assert len(missing) == 1
        assert missing[0].point_id == "clue-blunt"
        assert missing[0].missing_terms == ["钝器伤"]
        assert missing[0].chapter == 2

    def test_present_phrase_is_not_missing(self) -> None:
        text = "死者后脑有一处钝器伤。"

        assert check_must_mention([_clue()], 1, text) == []

    def test_every_term_must_appear(self) -> None:
        clue = _clue(mention_terms=["刮痕", "右向左"])

        missing = check_must_mention([clue], 2, "横杆刮痕走向自内向外。")

        assert missing[0].missing_terms == ["右向左"]

    def test_other_chapters_and_pending_rows_are_skipped(self) -> None:
        pending = _clue(approval_status="pending")
        later = _clue(clue_id="clue-later", must_mention_in=[3], mention_terms=["往外拉"])

        assert check_must_mention([pending, later], 2, "") == []

    def test_label_is_the_phrase_when_terms_are_empty(self) -> None:
        clue = _clue(mention_terms=[], label="九一八")

        missing = check_must_mention([clue], 1, "头版是另一件事。")

        assert missing[0].missing_terms == ["九一八"]

    def test_chapter_must_be_positive(self) -> None:
        with pytest.raises(ValueError):
            check_must_mention([_clue()], 0, "钝器伤")
