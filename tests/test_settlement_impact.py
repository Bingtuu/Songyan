"""Tests for Phase 4 settlement impact score and open thread extraction."""

from __future__ import annotations

import pytest

from songyan.agents.settlement_extractor import (
    _calculate_impact_score,
    _extract_open_threads,
)
from songyan.models import (
    CharacterUpdate,
    ForeshadowingUpdate,
    NewSetting,
    StateSettlement,
)


class TestImpactScore:
    def test_empty_settlement(self) -> None:
        settlement = StateSettlement()
        score = _calculate_impact_score(settlement)
        assert score == 0.0

    def test_world_upheaval_bonus(self) -> None:
        settlement = StateSettlement(
            new_settings=[
                NewSetting(
                    setting_name="新法则",
                    description="这个设定颠覆了世界观",
                    source_quote="",
                )
            ]
        )
        score = _calculate_impact_score(settlement)
        # 世界观颠覆 0.5 + 新设定 0.05 = 0.55
        assert score == 0.55

    def test_character_death_bonus(self) -> None:
        settlement = StateSettlement(
            character_updates=[
                CharacterUpdate(
                    character_id="char1",
                    field="status",
                    old_value="活着",
                    new_value="死亡",
                    source_quote="",
                )
            ]
        )
        score = _calculate_impact_score(settlement)
        assert score == 0.4

    def test_new_setting_bonus(self) -> None:
        settlement = StateSettlement(
            new_settings=[
                NewSetting(setting_name="A", description="普通设定", source_quote=""),
                NewSetting(setting_name="B", description="普通设定", source_quote=""),
            ]
        )
        score = _calculate_impact_score(settlement)
        # 2 * 0.05 = 0.10
        assert score == pytest.approx(0.10, abs=0.001)

    def test_foreshadowing_plant_bonus(self) -> None:
        settlement = StateSettlement(
            foreshadowing_updates=[
                ForeshadowingUpdate(
                    operation="plant", description="伏笔1", source_version_id="v1"
                ),
                ForeshadowingUpdate(
                    operation="plant", description="伏笔2", source_version_id="v1"
                ),
                ForeshadowingUpdate(
                    operation="plant", description="伏笔3", source_version_id="v1"
                ),
            ]
        )
        score = _calculate_impact_score(settlement)
        # 3 * 0.03 = 0.09
        assert score == pytest.approx(0.09, abs=0.001)

    def test_capped_at_1_0(self) -> None:
        settlement = StateSettlement(
            new_settings=[
                NewSetting(
                    setting_name=f"设定{i}",
                    description="这个设定颠覆了世界观",
                    source_quote="",
                )
                for i in range(10)
            ]
        )
        score = _calculate_impact_score(settlement)
        assert score <= 1.0

    def test_combined_score(self) -> None:
        settlement = StateSettlement(
            new_settings=[
                NewSetting(
                    setting_name="新法则",
                    description="颠覆了世界观",
                    source_quote="",
                ),
                NewSetting(setting_name="普通", description="普通", source_quote=""),
            ],
            character_updates=[
                CharacterUpdate(
                    character_id="char1",
                    field="status",
                    old_value="活着",
                    new_value="重伤濒死",
                    source_quote="",
                )
            ],
        )
        score = _calculate_impact_score(settlement)
        # 0.5 (upheaval) + 0.4 (death) + 2*0.05 (new settings) = 1.0
        assert score == pytest.approx(1.0, abs=0.001)


class TestOpenThreadExtraction:
    def test_from_foreshadowing_plant(self) -> None:
        settlement = StateSettlement(
            foreshadowing_updates=[
                ForeshadowingUpdate(
                    operation="plant", description="神秘老人身份", source_version_id="v1"
                )
            ]
        )
        threads = _extract_open_threads(settlement, chapter_number=5)
        assert len(threads) == 1
        assert "伏笔：神秘老人身份" in threads

    def test_from_mystery_setting(self) -> None:
        settlement = StateSettlement(
            new_settings=[
                NewSetting(
                    setting_name="玄天剑",
                    description="这是一把隐藏着秘密的上古神器",
                    source_quote="",
                )
            ]
        )
        threads = _extract_open_threads(settlement, chapter_number=3)
        assert len(threads) == 1
        assert "设定：玄天剑" in threads[0]

    def test_from_character_goal(self) -> None:
        settlement = StateSettlement(
            character_updates=[
                CharacterUpdate(
                    character_id="char1",
                    field="goal",
                    old_value="",
                    new_value="找到真相",
                    source_quote="",
                )
            ]
        )
        threads = _extract_open_threads(settlement, chapter_number=7)
        assert len(threads) == 1
        assert "角色目标：char1 的 找到真相" in threads[0]

    def test_multiple_sources(self) -> None:
        settlement = StateSettlement(
            foreshadowing_updates=[
                ForeshadowingUpdate(
                    operation="plant", description="伏笔A", source_version_id="v1"
                )
            ],
            new_settings=[
                NewSetting(
                    setting_name="X",
                    description="未知的秘密",
                    source_quote="",
                )
            ],
            character_updates=[
                CharacterUpdate(
                    character_id="c1",
                    field="目标",
                    old_value="",
                    new_value="复仇",
                    source_quote="",
                )
            ],
        )
        threads = _extract_open_threads(settlement, chapter_number=10)
        assert len(threads) == 3

    def test_resolve_not_extracted(self) -> None:
        settlement = StateSettlement(
            foreshadowing_updates=[
                ForeshadowingUpdate(
                    operation="resolve", description="回收伏笔", source_version_id="v1"
                )
            ]
        )
        threads = _extract_open_threads(settlement, chapter_number=5)
        assert len(threads) == 0

    def test_empty_settlement(self) -> None:
        settlement = StateSettlement()
        threads = _extract_open_threads(settlement, chapter_number=1)
        assert threads == []
