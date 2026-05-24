"""Numerical formula validation for xuanhuan genre."""

from __future__ import annotations

import time

from pydantic import BaseModel

from songyan.models.settlement import NumericalUpdate


class NumericalContext(BaseModel):
    """Context for numerical validation — character attributes at chapter start."""

    character_id: str
    attribute_name: str
    opening_value: float


class NumericalValidationError(BaseModel):
    """A single numerical validation error."""

    character_id: str
    attribute_name: str
    expected_closing: float
    actual_closing: float
    discrepancy: float
    message: str


def validate_numerical_update(update: NumericalUpdate) -> list[str]:
    """Validate a :class:`NumericalUpdate` for internal consistency.

    Checks that ``closing_value == opening_value + sum(increments) - sum(decrements)``.

    Returns an empty list when valid, otherwise a list of human-readable
    error messages.

    Complexity: O(k) where *k* is the number of increments + decrements.
    """
    total_increment = sum(inc.amount for inc in update.increments)
    total_decrement = sum(dec.amount for dec in update.decrements)
    expected = update.opening_value + total_increment - total_decrement

    if abs(expected - update.closing_value) < 1e-6:
        return []

    discrepancy = update.closing_value - expected
    parts: list[str] = []
    if update.increments:
        parts.append(
            "增量: "
            + ", ".join(f"{inc.amount}({inc.source})" for inc in update.increments)
        )
    if update.decrements:
        parts.append(
            "消耗: "
            + ", ".join(f"{dec.amount}({dec.usage})" for dec in update.decrements)
        )

    detail = "; ".join(parts) if parts else "无增减记录"
    return [
        f"数值公式验证失败: {update.character_id}.{update.attribute_name} "
        f"期望值 {expected:.2f} = {update.opening_value:.2f} + "
        f"{total_increment:.2f} - {total_decrement:.2f}, "
        f"实际值 {update.closing_value:.2f} "
        f"(偏差 {discrepancy:+.2f}); {detail}"
    ]


def validate_numerical_updates(updates: list[NumericalUpdate]) -> list[str]:
    """Validate multiple :class:`NumericalUpdate` objects.

    Returns a flat list of all error messages.
    """
    errors: list[str] = []
    for update in updates:
        errors.extend(validate_numerical_update(update))
    return errors


def validate_numerical_updates_with_timing(
    updates: list[NumericalUpdate],
) -> tuple[list[str], int]:
    """Run :func:`validate_numerical_updates` and return elapsed milliseconds."""
    start = time.perf_counter()
    result = validate_numerical_updates(updates)
    elapsed = int((time.perf_counter() - start) * 1000)
    return result, elapsed
