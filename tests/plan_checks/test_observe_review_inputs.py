"""Deterministic extracts and anchors read from one chapter.

These rows feed the existing gate. They are not written to plan canon.
"""

from __future__ import annotations

from songyan.models.plan_facts import PlanAttribute, PlanClaim, PlanEntity, PlanEvent
from songyan.plan_checks.observe import observe_plan_review_inputs


def _direction(value: str, *, entity_id: str = "ent-mech") -> PlanAttribute:
    return PlanAttribute(
        attribute_id=f"attr-{entity_id}",
        project_id="p",
        entity_id=entity_id,
        key="direction",
        value=value,
        valid_from_ch=1,
        valid_to_ch=3,
        source="human",
        approval_status="approved",
    )


def _event(claim_id: str, text: str, *, participants: list[str] | None = None) -> PlanEvent:
    return PlanEvent(
        event_id="evt",
        project_id="p",
        ch=3,
        participants=participants or [],
        claims=[PlanClaim(claim_id=claim_id, text=text)],
        approval_status="approved",
    )


def test_negated_claim_phrase_becomes_ownership_extract_and_anchor() -> None:
    extracts, anchors = observe_plan_review_inputs(
        chapter=3,
        chapter_text="他把横杆拓片推过去。",
        attributes=[
            PlanAttribute(
                attribute_id="attr-hook",
                project_id="p",
                entity_id="ent-hook",
                key="ownership",
                value="门框暗处",
                valid_from_ch=2,
                valid_to_ch=3,
                source="human",
            )
        ],
        events=[_event("claim-hook", "钩状弧线属于门框暗处，不在横杆拓片上")],
    )

    assert any(
        row.entity_id == "ent-hook" and row.key == "ownership" and row.value == "横杆拓片"
        for row in extracts
    )
    anchor = next(row for row in anchors if row.claim_id == "claim-hook")
    assert "横杆拓片" in anchor.contradict_terms
    assert "门框暗处" in anchor.support_terms


def test_phrase_only_under_negation_is_not_a_contradiction() -> None:
    _extracts, anchors = observe_plan_review_inputs(
        chapter=3,
        chapter_text="钩痕不在横杆拓片上。",
        attributes=[
            PlanAttribute(
                attribute_id="attr-hook",
                project_id="p",
                entity_id="ent-hook",
                key="ownership",
                value="门框暗处",
                source="human",
            )
        ],
        events=[_event("claim-hook", "钩状弧线属于门框暗处，不在横杆拓片上")],
    )

    assert anchors == [] or all("横杆拓片" not in row.contradict_terms for row in anchors)


def test_governed_direction_alternative_is_visible() -> None:
    extracts, anchors = observe_plan_review_inputs(
        chapter=3,
        chapter_text="横杆受力的方向是从外往内拉。",
        attributes=[_direction("往外拉")],
        events=[_event("claim-pull", "拉闩方向仍是往外拉")],
        entities=[
            PlanEntity(
                entity_id="ent-mech",
                project_id="p",
                entity_type="mechanism",
                aliases=["拉闩"],
            )
        ],
    )

    assert any(row.value == "从外往内拉" and row.key == "direction" for row in extracts)
    anchor = next(row for row in anchors if row.claim_id == "claim-pull")
    assert "从外往内拉" in anchor.contradict_terms


def test_hedged_opposite_direction_is_not_extracted() -> None:
    extracts, _anchors = observe_plan_review_inputs(
        chapter=1,
        chapter_text="受力方向应该是从左向右。刮痕的方向反了。",
        attributes=[_direction("右向左", entity_id="ent-scratch")],
        events=[],
        entities=[
            PlanEntity(
                entity_id="ent-scratch",
                project_id="p",
                entity_type="object",
                aliases=["刮痕"],
            )
        ],
    )

    assert all(row.value != "左向右" for row in extracts)
    assert all("从左向右" not in row.value for row in extracts)


def test_recorded_name_in_a_naming_slot_is_an_ownership_extract() -> None:
    extracts, anchors = observe_plan_review_inputs(
        chapter=2,
        chapter_text="记名栏：沈酌。",
        attributes=[
            PlanAttribute(
                attribute_id="attr-owner",
                project_id="p",
                entity_id="ent-mark",
                key="ownership",
                value="周晚宁",
                valid_from_ch=1,
                valid_to_ch=3,
                source="human",
            )
        ],
        events=[
            PlanEvent(
                event_id="evt-name",
                project_id="p",
                ch=2,
                claims=[PlanClaim(claim_id="claim-name", text="灵印记名仍是周晚宁")],
            )
        ],
        entities=[
            PlanEntity(
                entity_id="ent-shen",
                project_id="p",
                entity_type="person",
                aliases=["沈酌"],
            )
        ],
    )

    assert any(row.entity_id == "ent-mark" and row.value == "沈酌" for row in extracts)
    anchor = next(row for row in anchors if row.claim_id == "claim-name")
    assert "沈酌" in anchor.contradict_terms


def test_count_change_beside_the_alias_is_numeric() -> None:
    extracts, _anchors = observe_plan_review_inputs(
        chapter=3,
        chapter_text="刻痕从一道变成了两道。",
        attributes=[
            PlanAttribute(
                attribute_id="attr-count",
                project_id="p",
                entity_id="ent-notch",
                key="count",
                value="1",
                source="human",
            )
        ],
        events=[],
        entities=[
            PlanEntity(
                entity_id="ent-notch",
                project_id="p",
                entity_type="object",
                aliases=["刻痕"],
            )
        ],
    )

    assert any(
        row.entity_id == "ent-notch" and row.key == "count" and row.value == "2" for row in extracts
    )


def test_pending_rows_are_not_read() -> None:
    extracts, anchors = observe_plan_review_inputs(
        chapter=2,
        chapter_text="走向自内向外。",
        attributes=[
            PlanAttribute(
                attribute_id="attr-pending",
                project_id="p",
                entity_id="ent-scratch",
                key="direction",
                value="右向左",
                source="human",
                approval_status="pending",
            )
        ],
        events=[
            PlanEvent(
                event_id="evt-pending",
                project_id="p",
                ch=2,
                claims=[PlanClaim(claim_id="claim-pending", text="方向为右向左")],
                approval_status="pending",
            )
        ],
    )

    assert extracts == []
    assert anchors == []


def test_negated_phrase_on_the_participant_time_anchor() -> None:
    extracts, anchors = observe_plan_review_inputs(
        chapter=1,
        chapter_text="头版写着日军进逼锦州。",
        attributes=[
            PlanAttribute(
                attribute_id="attr-era",
                project_id="p",
                entity_id="ent-era",
                key="time_anchor",
                value="1931-09-18前",
                source="plan",
            )
        ],
        events=[
            PlanEvent(
                event_id="evt-era",
                project_id="p",
                ch=1,
                participants=["ent-era"],
                claims=[
                    PlanClaim(
                        claim_id="claim-era",
                        text="本案当下在九一八之前，报纸报道的不是日军进逼锦州",
                    )
                ],
            )
        ],
    )

    assert any(row.entity_id == "ent-era" and row.value == "日军进逼锦州" for row in extracts)
    anchor = next(row for row in anchors if row.claim_id == "claim-era")
    assert "日军进逼锦州" in anchor.contradict_terms


def test_other_compass_facing_is_a_direction_extract() -> None:
    extracts, _anchors = observe_plan_review_inputs(
        chapter=2,
        chapter_text="她面朝西。流程仍写面朝东。",
        attributes=[_direction("面朝东", entity_id="ent-return")],
        events=[],
    )

    assert any(row.value == "面朝西" for row in extracts)
    assert any(row.value == "面朝东" for row in extracts)
