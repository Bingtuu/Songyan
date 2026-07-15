"""Task 172a.6: per-genre character focal decay via profile.focal_gaps."""

from __future__ import annotations

from songyan.agents.context_manager._assemblers import _resolve_profile_level
from songyan.db.genre_runtime_profile_repo import load_profile_from_registry


def test_default_gaps_match_legacy_thresholds() -> None:
    # focal_gaps=None -> 原 3/10/30 阈值不变
    laf = {"c": 100}
    assert _resolve_profile_level("c", False, False, 103, laf) == "full"  # gap 3
    assert _resolve_profile_level("c", False, False, 108, laf) == "compact"  # gap 8
    assert _resolve_profile_level("c", False, False, 120, laf) == "symbol"  # gap 20
    assert _resolve_profile_level("c", False, False, 140, laf) == "skip"  # gap 40


def test_xuanhuan_wider_gaps_keep_character_longer() -> None:
    xuanhuan = load_profile_from_registry("xuanhuan")
    gaps = xuanhuan.character_decay.focal_gaps  # full=6, compact=16, symbol=48
    laf = {"c": 100}
    # gap 48: 默认阈值 symbol_gap=30 -> skip；xuanhuan symbol_gap=48 -> 仍 symbol
    assert _resolve_profile_level("c", False, False, 148, laf) == "skip"
    assert _resolve_profile_level("c", False, False, 148, laf, gaps) == "symbol"
    # 旧 floor=40 仍保持 symbol，证明后段角色声纹保留更宽。
    assert _resolve_profile_level("c", False, False, 140, laf) == "skip"
    assert _resolve_profile_level("c", False, False, 140, laf, gaps) == "symbol"
    # gap 16: 默认 compact_gap=10 -> symbol；xuanhuan compact_gap=16 -> compact
    assert _resolve_profile_level("c", False, False, 116, laf) == "symbol"
    assert _resolve_profile_level("c", False, False, 116, laf, gaps) == "compact"
    # 旧 compact=12 仍保持 compact。
    assert _resolve_profile_level("c", False, False, 112, laf) == "symbol"
    assert _resolve_profile_level("c", False, False, 112, laf, gaps) == "compact"


def test_protagonist_never_decays_regardless_of_gaps() -> None:
    xuanhuan = load_profile_from_registry("xuanhuan")
    gaps = xuanhuan.character_decay.focal_gaps
    assert _resolve_profile_level("hero", True, False, 999, {"hero": 1}, gaps) == "full"
