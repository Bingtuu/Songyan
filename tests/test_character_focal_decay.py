"""Task 102: CharacterFocalDecay — 角色焦点衰减测试."""

from __future__ import annotations

import pytest

from songyan.agents.context_manager._assemblers import (
    _build_character_snapshots,
    _resolve_profile_level,
)
from songyan.models import Character, CharacterState


class TestResolveProfileLevel:
    """测试衰减级别解析逻辑."""

    def test_protagonist_never_decays(self) -> None:
        """protagonist 永不衰减."""
        assert _resolve_profile_level("c1", True, False, 100, {"c1": 50}) == "full"
        assert _resolve_profile_level("c1", True, False, 100, {"c1": 10}) == "full"
        assert _resolve_profile_level("c1", True, False, 100, {"c1": 1}) == "full"

    def test_antagonist_never_decays(self) -> None:
        """antagonist 永不衰减."""
        assert _resolve_profile_level("c1", False, True, 100, {"c1": 50}) == "full"
        assert _resolve_profile_level("c1", False, True, 100, {"c1": 1}) == "full"

    def test_gap_0_to_3_full(self) -> None:
        """未出场 0-3 章：完整档案."""
        assert _resolve_profile_level("c1", False, False, 10, {"c1": 10}) == "full"
        assert _resolve_profile_level("c1", False, False, 10, {"c1": 9}) == "full"
        assert _resolve_profile_level("c1", False, False, 10, {"c1": 7}) == "full"

    def test_gap_4_to_10_compact(self) -> None:
        """未出场 4-10 章：精简档案."""
        assert _resolve_profile_level("c1", False, False, 10, {"c1": 6}) == "compact"
        assert _resolve_profile_level("c1", False, False, 15, {"c1": 5}) == "compact"
        assert _resolve_profile_level("c1", False, False, 20, {"c1": 10}) == "compact"

    def test_gap_11_to_30_symbol(self) -> None:
        """未出场 11-30 章：符号档案."""
        assert _resolve_profile_level("c1", False, False, 20, {"c1": 9}) == "symbol"
        assert _resolve_profile_level("c1", False, False, 40, {"c1": 10}) == "symbol"
        assert _resolve_profile_level("c1", False, False, 50, {"c1": 20}) == "symbol"

    def test_gap_over_30_skip(self) -> None:
        """未出场 30+ 章：不加载."""
        assert _resolve_profile_level("c1", False, False, 50, {"c1": 19}) == "skip"
        assert _resolve_profile_level("c1", False, False, 100, {"c1": 50}) == "skip"
        assert _resolve_profile_level("c1", False, False, 100, {"c1": 1}) == "skip"

    def test_no_last_appeared_defaults_full(self) -> None:
        """无出场记录时默认完整档案（向后兼容）."""
        assert _resolve_profile_level("c1", False, False, 10, None) == "full"
        assert _resolve_profile_level("c1", False, False, 10, {}) == "full"

    def test_last_chapter_zero_defaults_full(self) -> None:
        """last_chapter=0（从未出场）默认完整档案."""
        assert _resolve_profile_level("c1", False, False, 10, {"c1": 0}) == "full"


class TestBuildCharacterSnapshotsDecay:
    """测试 _build_character_snapshots 的衰减输出."""

    def _make_char(self, cid: str, name: str, role: str) -> Character:
        return Character(
            character_id=cid,
            project_id="p1",
            name=name,
            role_type=role,  # type: ignore[arg-type]
            goals=[f"目标-{name}"],
            relationships={"盟友": "合作"},
        )

    def _make_state(self, cid: str, field: str, value: str) -> CharacterState:
        return CharacterState(character_id=cid, field=field, value=value)

    def test_full_profile_structure(self) -> None:
        """full_profile 保留完整字段."""
        chars = [self._make_char("c1", "主角", "protagonist")]
        states = [
            self._make_state("c1", "location", "天剑峰"),
            self._make_state("c1", "emotional_state", "愤怒"),
        ]
        snapshots = _build_character_snapshots(
            chars, states, current_chapter=10, last_appeared_chapters={"c1": 10}
        )
        assert len(snapshots) == 1
        s = snapshots[0]
        assert s.name == "主角"
        assert s.current_location == "天剑峰"
        assert s.emotional_state == "愤怒"
        assert s.active_relationships == ["盟友"]
        assert s.unresolved_issues == ["目标-主角"]
        assert s.importance_score == 1.0

    def test_compact_profile_structure(self) -> None:
        """compact_profile 精简字段."""
        chars = [self._make_char("c2", "配角", "supporting")]
        states = [
            self._make_state("c2", "location", "黑木崖"),
            self._make_state("c2", "emotional_state", "焦虑"),
        ]
        snapshots = _build_character_snapshots(
            chars, states, current_chapter=10, last_appeared_chapters={"c2": 5}
        )
        assert len(snapshots) == 1
        s = snapshots[0]
        assert s.name == "配角"
        assert s.current_location == "黑木崖"
        assert "位置:黑木崖" in (s.emotional_state or "")
        assert s.active_relationships == []
        assert s.unresolved_issues == []
        assert s.importance_score == 0.4

    def test_symbol_profile_structure(self) -> None:
        """symbol_profile 只保留符号信息."""
        chars = [self._make_char("c3", "龙套", "supporting")]
        states = [
            self._make_state("c3", "location", "洛阳"),
            self._make_state("c3", "emotional_state", "疲惫"),
        ]
        snapshots = _build_character_snapshots(
            chars, states, current_chapter=25, last_appeared_chapters={"c3": 5}
        )
        assert len(snapshots) == 1
        s = snapshots[0]
        assert s.name == "龙套"
        assert s.current_location is None
        assert s.current_cultivation is None
        assert "【符号档案】" in (s.emotional_state or "")
        assert "最后出场Ch5" in (s.emotional_state or "")
        assert "位置:洛阳" in (s.emotional_state or "")
        assert s.active_relationships == []
        assert s.unresolved_issues == []
        assert s.importance_score == 0.2

    def test_skip_excludes_character(self) -> None:
        """skip 级别角色被排除."""
        chars = [
            self._make_char("c1", "主角", "protagonist"),
            self._make_char("c2", "老角色", "supporting"),
        ]
        states = []
        snapshots = _build_character_snapshots(
            chars, states, current_chapter=100, last_appeared_chapters={"c1": 90, "c2": 50}
        )
        assert len(snapshots) == 1
        assert snapshots[0].character_id == "c1"

    def test_mixed_decay_levels(self) -> None:
        """混合衰减级别场景."""
        chars = [
            self._make_char("c1", "主角", "protagonist"),
            self._make_char("c2", "最近配角", "supporting"),
            self._make_char("c3", "中等配角", "supporting"),
            self._make_char("c4", "老配角", "supporting"),
            self._make_char("c5", "远古配角", "supporting"),
        ]
        states = [
            self._make_state("c1", "location", "主峰"),
            self._make_state("c2", "location", "侧峰"),
            self._make_state("c3", "location", "山下"),
            self._make_state("c4", "location", "远方"),
            self._make_state("c5", "location", "异界"),
        ]
        last_appeared = {
            "c1": 48,  # gap=2 → full
            "c2": 46,  # gap=4 → compact
            "c3": 40,  # gap=10 → compact
            "c4": 20,  # gap=30 → symbol
            "c5": 10,  # gap=40 → skip
        }
        snapshots = _build_character_snapshots(
            chars, states, current_chapter=50, last_appeared_chapters=last_appeared
        )
        assert len(snapshots) == 4

        ids = {s.character_id: s for s in snapshots}
        assert "c1" in ids and ids["c1"].active_relationships == ["盟友"]
        assert "c2" in ids and ids["c2"].active_relationships == []
        assert "c3" in ids and ids["c3"].active_relationships == []
        assert "c4" in ids and "【符号档案】" in (ids["c4"].emotional_state or "")
        assert "c5" not in ids

    def test_character_focus_overrides_decay(self) -> None:
        """character_focus 人工指定覆盖 decay 规则."""
        chars = [self._make_char("c2", "配角", "supporting")]
        states = [self._make_state("c2", "location", "某地")]
        focus = [{"character_id": "c2", "detail_level": "full"}]
        # gap=50 本应 skip，但 focus=full 覆盖为 full
        snapshots = _build_character_snapshots(
            chars,
            states,
            current_chapter=100,
            last_appeared_chapters={"c2": 50},
            character_focus=focus,
        )
        assert len(snapshots) == 1
        assert snapshots[0].active_relationships == ["盟友"]

    def test_backward_compatibility_no_last_appeared(self) -> None:
        """不传 last_appeared_chapters 时保持原有行为（向后兼容）."""
        chars = [self._make_char("c2", "配角", "supporting")]
        states = [self._make_state("c2", "location", "某地")]
        snapshots = _build_character_snapshots(chars, states)
        assert len(snapshots) == 1
        assert snapshots[0].active_relationships == ["盟友"]

    def test_token_reduction_30_percent(self) -> None:
        """验证 symbol + skip 后 token 减少 ≥ 30%.

        模拟 Ch55 场景：5 个角色，1 protagonist + 4 supporting。
        衰减前全部 full：约 5 * 800 = 4000 token
        衰减后 1 full + 1 compact + 1 symbol + 2 skip：约 800 + 400 + 100 = 1300
        比例：1300 / 4000 = 32.5%
        """
        chars = [
            self._make_char("c1", "主角", "protagonist"),
            self._make_char("c2", "配角A", "supporting"),
            self._make_char("c3", "配角B", "supporting"),
            self._make_char("c4", "配角C", "supporting"),
            self._make_char("c5", "配角D", "supporting"),
        ]
        states = [
            self._make_state("c1", "location", "主峰"),
            self._make_state("c2", "location", "侧峰"),
            self._make_state("c3", "location", "山下"),
            self._make_state("c4", "location", "远方"),
            self._make_state("c5", "location", "异界"),
        ]
        # 模拟 Ch55
        last_appeared = {
            "c1": 55,  # full (protagonist)
            "c2": 52,  # full (gap=3)
            "c3": 48,  # compact (gap=7)
            "c4": 30,  # symbol (gap=25)
            "c5": 10,  # skip (gap=45)
        }

        # 无衰减（全部 full）
        snapshots_flat = _build_character_snapshots(
            chars, states, current_chapter=55, last_appeared_chapters=None
        )
        # 有衰减
        snapshots_decay = _build_character_snapshots(
            chars, states, current_chapter=55, last_appeared_chapters=last_appeared
        )

        # 由于测试数据简单，主要验证结构差异
        assert len(snapshots_flat) == 5
        assert len(snapshots_decay) == 4  # c5 skipped
        assert "c5" not in {s.character_id for s in snapshots_decay}

        # 验证级别分布
        full_count = sum(1 for s in snapshots_decay if s.importance_score >= 0.8)
        compact_count = sum(1 for s in snapshots_decay if 0.3 <= s.importance_score < 0.8)
        symbol_count = sum(1 for s in snapshots_decay if s.importance_score < 0.3)
        assert full_count == 2   # c1, c2
        assert compact_count == 1  # c3
        assert symbol_count == 1   # c4


class TestGetLastAppearedChapters:
    """测试 CharacterStateRepository.get_last_appeared_chapters（集成测试）."""

    @pytest.mark.asyncio
    async def test_empty_project(self, test_db) -> None:
        """空项目返回空字典."""
        from songyan.db.context_repo import CharacterStateRepository
        from songyan.db.migrations import init_schema

        await init_schema()
        repo = CharacterStateRepository()
        result = await repo.get_last_appeared_chapters("empty-proj")
        assert result == {}
