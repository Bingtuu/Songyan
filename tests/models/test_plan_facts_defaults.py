"""Plan fact card models default to approval_status=pending.

Task 232 (P0-3): a card constructed without an explicit status must land
in the pending queue, not silently become canon. Callers that mean
"already approved" (fixtures, tests) pass the status explicitly.
"""

from songyan.models.plan_facts import (
    PlanAttribute,
    PlanClue,
    PlanEntity,
    PlanEvent,
    PlanTimeAnchor,
)


def _entity(**overrides: object) -> PlanEntity:
    fields: dict[str, object] = {
        "entity_id": "e-1",
        "project_id": "p-1",
        "entity_type": "person",
    }
    fields.update(overrides)
    return PlanEntity(**fields)  # type: ignore[arg-type]


def _attribute(**overrides: object) -> PlanAttribute:
    fields: dict[str, object] = {
        "attribute_id": "a-1",
        "project_id": "p-1",
        "entity_id": "e-1",
        "key": "occupation",
        "value": "法医",
        "source": "plan",
    }
    fields.update(overrides)
    return PlanAttribute(**fields)  # type: ignore[arg-type]


def _time_anchor(**overrides: object) -> PlanTimeAnchor:
    fields: dict[str, object] = {
        "anchor_id": "t-1",
        "project_id": "p-1",
        "date": "1931-09-18",
        "kind": "story",
    }
    fields.update(overrides)
    return PlanTimeAnchor(**fields)  # type: ignore[arg-type]


def _event(**overrides: object) -> PlanEvent:
    fields: dict[str, object] = {
        "event_id": "v-1",
        "project_id": "p-1",
        "ch": 1,
    }
    fields.update(overrides)
    return PlanEvent(**fields)  # type: ignore[arg-type]


def _clue(**overrides: object) -> PlanClue:
    fields: dict[str, object] = {
        "clue_id": "c-1",
        "project_id": "p-1",
        "planted_ch": 1,
    }
    fields.update(overrides)
    return PlanClue(**fields)  # type: ignore[arg-type]


def test_models_default_to_pending() -> None:
    assert _entity().approval_status == "pending"
    assert _attribute().approval_status == "pending"
    assert _time_anchor().approval_status == "pending"
    assert _event().approval_status == "pending"
    assert _clue().approval_status == "pending"


def test_explicit_status_still_honored() -> None:
    assert _entity(approval_status="approved").approval_status == "approved"
    assert _attribute(approval_status="rejected").approval_status == "rejected"
    assert _time_anchor(approval_status="approved").approval_status == "approved"
    assert _event(approval_status="rejected").approval_status == "rejected"
    assert _clue(approval_status="approved").approval_status == "approved"
