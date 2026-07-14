"""Task 172a.3: runtime_profile injection into context assembly.

Proves:
- scifi profile / None profile produce byte-identical budget to the old
  _dynamic_budget formula (no behavior regression).
- xuanhuan profile raises the budget (the real lever for un-prunable overflow).
"""

from __future__ import annotations

from songyan.agents.context_manager._assemblers import (
    BUDGET_INCREMENT_PER_CHAPTER,
    DEFAULT_BASE_BUDGET,
    _dynamic_budget,
)
from songyan.db.genre_runtime_profile_repo import load_profile_from_registry


def test_scifi_profile_budget_equals_legacy_formula() -> None:
    scifi = load_profile_from_registry("scifi")
    for ch in (1, 8, 50, 100, 200):
        legacy = _dynamic_budget(ch, DEFAULT_BASE_BUDGET)
        assert scifi.dynamic_budget(ch) == legacy, f"scifi budget diverged at Ch{ch}"


def test_scifi_profile_uses_default_constants() -> None:
    scifi = load_profile_from_registry("scifi")
    assert scifi.base_budget == DEFAULT_BASE_BUDGET
    assert scifi.ramp_per_chapter == BUDGET_INCREMENT_PER_CHAPTER


def test_xuanhuan_profile_budget_is_higher_at_ch8() -> None:
    scifi = load_profile_from_registry("scifi")
    xuanhuan = load_profile_from_registry("xuanhuan")
    # Ch8 is where xuanhuan halted; higher base budget must give more headroom
    assert xuanhuan.dynamic_budget(8) > scifi.dynamic_budget(8)
    # scifi Ch8 = 8000 + 8*250 = 10000; xuanhuan base 12000 -> 14000
    assert scifi.dynamic_budget(8) == 10000
    assert xuanhuan.dynamic_budget(8) == 14000
