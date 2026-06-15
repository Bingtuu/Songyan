"""Tests for numerical formula validation."""

from __future__ import annotations

from songyan.models.settlement import Decrement, Increment, NumericalUpdate
from songyan.utils.numerical_validator import (
    validate_numerical_update,
    validate_numerical_updates,
    validate_numerical_updates_with_timing,
)


class TestValidateNumericalUpdate:
    """Tests for validate_numerical_update."""

    def test_valid_no_changes(self) -> None:
        update = NumericalUpdate(
            character_id="char_001",
            attribute_name="cultivation_level",
            opening_value=100.0,
            closing_value=100.0,
        )
        errors = validate_numerical_update(update)
        assert errors == []

    def test_valid_with_increment(self) -> None:
        update = NumericalUpdate(
            character_id="char_001",
            attribute_name="cultivation_level",
            opening_value=100.0,
            increments=[Increment(amount=10.0, source="breakthrough", source_quote="突破了一层")],
            closing_value=110.0,
        )
        errors = validate_numerical_update(update)
        assert errors == []

    def test_valid_with_decrement(self) -> None:
        update = NumericalUpdate(
            character_id="char_001",
            attribute_name="spirit_stones",
            opening_value=100.0,
            decrements=[Decrement(amount=20.0, usage="purchase", source_quote="买了一瓶丹药")],
            closing_value=80.0,
        )
        errors = validate_numerical_update(update)
        assert errors == []

    def test_valid_with_both(self) -> None:
        update = NumericalUpdate(
            character_id="char_001",
            attribute_name="health",
            opening_value=100.0,
            increments=[Increment(amount=30.0, source="healing", source_quote="服用丹药")],
            decrements=[Decrement(amount=50.0, usage="combat", source_quote="战斗中受伤")],
            closing_value=80.0,
        )
        errors = validate_numerical_update(update)
        assert errors == []

    def test_invalid_closing_value(self) -> None:
        update = NumericalUpdate(
            character_id="char_001",
            attribute_name="cultivation_level",
            opening_value=100.0,
            increments=[Increment(amount=10.0, source="breakthrough", source_quote="突破")],
            closing_value=120.0,  # Should be 110.0
        )
        errors = validate_numerical_update(update)
        assert len(errors) == 1
        assert "验证失败" in errors[0]
        assert "120.0" in errors[0]
        assert "110.0" in errors[0]

    def test_invalid_negative_result(self) -> None:
        update = NumericalUpdate(
            character_id="char_001",
            attribute_name="spirit_stones",
            opening_value=10.0,
            decrements=[Decrement(amount=20.0, usage="spend", source_quote="花费")],
            closing_value=10.0,  # Should be -10.0
        )
        errors = validate_numerical_update(update)
        assert len(errors) == 1
        assert "验证失败" in errors[0]

    def test_multiple_increments(self) -> None:
        update = NumericalUpdate(
            character_id="char_001",
            attribute_name="exp",
            opening_value=0.0,
            increments=[
                Increment(amount=10.0, source="battle", source_quote="战斗"),
                Increment(amount=20.0, source="quest", source_quote="任务"),
            ],
            closing_value=30.0,
        )
        errors = validate_numerical_update(update)
        assert errors == []

    def test_multiple_decrements(self) -> None:
        update = NumericalUpdate(
            character_id="char_001",
            attribute_name="mana",
            opening_value=100.0,
            decrements=[
                Decrement(amount=10.0, usage="spell1", source_quote="施法1"),
                Decrement(amount=15.0, usage="spell2", source_quote="施法2"),
            ],
            closing_value=75.0,
        )
        errors = validate_numerical_update(update)
        assert errors == []

    def test_error_message_contains_detail(self) -> None:
        update = NumericalUpdate(
            character_id="char_001",
            attribute_name="cultivation_level",
            opening_value=100.0,
            increments=[Increment(amount=10.0, source="breakthrough", source_quote="突破")],
            closing_value=120.0,
        )
        errors = validate_numerical_update(update)
        assert len(errors) == 1
        assert "char_001" in errors[0]
        assert "cultivation_level" in errors[0]
        assert "增量" in errors[0]


class TestValidateNumericalUpdates:
    """Tests for batch validation."""

    def test_empty_list(self) -> None:
        errors = validate_numerical_updates([])
        assert errors == []

    def test_multiple_updates(self) -> None:
        updates = [
            NumericalUpdate(
                character_id="char_001",
                attribute_name="health",
                opening_value=100.0,
                closing_value=100.0,
            ),
            NumericalUpdate(
                character_id="char_002",
                attribute_name="mana",
                opening_value=50.0,
                increments=[Increment(amount=10.0, source="rest", source_quote="休息")],
                closing_value=60.0,
            ),
        ]
        errors = validate_numerical_updates(updates)
        assert errors == []

    def test_mixed_valid_and_invalid(self) -> None:
        updates = [
            NumericalUpdate(
                character_id="char_001",
                attribute_name="health",
                opening_value=100.0,
                closing_value=100.0,
            ),
            NumericalUpdate(
                character_id="char_002",
                attribute_name="mana",
                opening_value=50.0,
                closing_value=60.0,  # Should be 50.0
            ),
        ]
        errors = validate_numerical_updates(updates)
        assert len(errors) == 1
        assert "char_002" in errors[0]


class TestNumericalValidatorPerformance:
    """Performance tests."""

    def test_performance_under_10ms(self) -> None:
        updates = [
            NumericalUpdate(
                character_id=f"char_{i:03d}",
                attribute_name="cultivation_level",
                opening_value=100.0 + i,
                increments=[
                    Increment(amount=10.0, source="battle", source_quote="战斗"),
                    Increment(amount=5.0, source="meditation", source_quote="修炼"),
                ],
                decrements=[
                    Decrement(amount=3.0, usage="injury", source_quote="受伤"),
                ],
                closing_value=112.0 + i,
            )
            for i in range(100)
        ]
        result, elapsed = validate_numerical_updates_with_timing(updates)
        assert elapsed < 10, f"Numerical validation took {elapsed}ms, expected < 10ms"
