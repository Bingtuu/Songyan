"""Typed attribute comparison is exact and windowed."""

from __future__ import annotations

from songyan.models.plan_facts import PlanAttribute
from songyan.plan_checks.typed_attributes import AttributeExtract, compare_typed_attributes


def _direction(value: str = "右向左", **updates: object) -> PlanAttribute:
    payload: dict[str, object] = {
        "attribute_id": "attr-direction",
        "project_id": "p1",
        "entity_id": "ent-scratch",
        "key": "direction",
        "value": value,
        "valid_from_ch": 1,
        "valid_to_ch": 3,
        "source": "human",
        "approval_status": "approved",
    }
    payload.update(updates)
    return PlanAttribute.model_validate(payload)


class TestTypedAttributes:
    def test_matching_direction_is_silent(self) -> None:
        mismatches = compare_typed_attributes(
            [_direction()],
            [AttributeExtract(entity_id="ent-scratch", key="direction", value="右向左", chapter=1)],
        )

        assert mismatches == []

    def test_drifted_direction_and_count_are_reported(self) -> None:
        count = PlanAttribute(
            attribute_id="attr-count",
            project_id="p1",
            entity_id="ent-scratch",
            key="count",
            value="1",
            valid_from_ch=1,
            valid_to_ch=3,
            source="human",
        )
        mismatches = compare_typed_attributes(
            [_direction(), count],
            [
                AttributeExtract(
                    entity_id="ent-scratch",
                    key="direction",
                    value="自内向外",
                    chapter=2,
                ),
                AttributeExtract(
                    entity_id="ent-scratch",
                    key="quantity",
                    value="2",
                    chapter=2,
                ),
            ],
        )

        assert [(row.key, row.approved_value, row.extract_value) for row in mismatches] == [
            ("direction", "右向左", "自内向外"),
            ("count", "1", "2"),
        ]

    def test_extract_outside_the_window_is_not_compared(self) -> None:
        hook = PlanAttribute(
            attribute_id="attr-hook",
            project_id="p1",
            entity_id="ent-hook",
            key="ownership",
            value="门框暗处",
            valid_from_ch=2,
            valid_to_ch=3,
            source="human",
        )

        mismatches = compare_typed_attributes(
            [hook],
            [AttributeExtract(entity_id="ent-hook", key="ownership", value="横杆拓片", chapter=1)],
        )

        assert mismatches == []

    def test_pending_and_untyped_keys_are_ignored(self) -> None:
        pending = _direction(approval_status="pending", value="右向左")
        note = PlanAttribute(
            attribute_id="attr-note",
            project_id="p1",
            entity_id="ent-scratch",
            key="note",
            value="直线",
            source="plan",
        )

        mismatches = compare_typed_attributes(
            [pending, note],
            [
                AttributeExtract(
                    entity_id="ent-scratch",
                    key="direction",
                    value="自内向外",
                    chapter=2,
                ),
                AttributeExtract(entity_id="ent-scratch", key="note", value="弧线", chapter=2),
            ],
        )

        assert mismatches == []

    def test_time_anchor_values_are_compared_as_text(self) -> None:
        era = PlanAttribute(
            attribute_id="attr-era",
            project_id="p1",
            entity_id="ent-era",
            key="time_anchor",
            value="1931-09-18前",
            valid_from_ch=1,
            valid_to_ch=3,
            source="plan",
        )

        mismatches = compare_typed_attributes(
            [era],
            [
                AttributeExtract(
                    entity_id="ent-era",
                    key="time_anchor",
                    value="1931年末·日军进逼锦州",
                    chapter=1,
                )
            ],
        )

        assert len(mismatches) == 1
        assert mismatches[0].approved_value == "1931-09-18前"
        assert mismatches[0].attribute_id == "attr-era"
