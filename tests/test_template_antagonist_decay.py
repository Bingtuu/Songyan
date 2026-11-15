"""task 267：未出场模板反派不再永不衰减。

口径（唯一、稳定）：antagonist 已出场（last>0）或有 character_states → 仍受
核心角色保护（full / 0.8）；从未出场且无 states → 只给符号档案
（importance 0.2），不占硬顶、不保送 0.8，可被已出场/有状态角色挤掉。
protagonist 永不衰减不变。
"""

from __future__ import annotations

from songyan.agents.context_manager._assemblers import (
    _build_character_snapshots,
    _resolve_profile_level,
)
from songyan.models import Character, CharacterState


class TestResolveProfileLevelTemplateAntagonist:
    def test_never_appeared_stateless_antagonist_gets_symbol(self) -> None:
        """0 states、从未出场的模板反派：不再保送 full。"""
        assert (
            _resolve_profile_level(
                "c-ant", False, True, 5, {"c-ant": 0}, has_character_states=False
            )
            == "symbol"
        )
        # last_appeared_chapters 缺失（测试场景）同样收窄
        assert (
            _resolve_profile_level(
                "c-ant", False, True, 5, None, has_character_states=False
            )
            == "symbol"
        )

    def test_appeared_antagonist_keeps_protection(self) -> None:
        """已出场 antagonist 无 states 仍受保护（出场即已建立存在感）。"""
        assert (
            _resolve_profile_level(
                "c-ant", False, True, 20, {"c-ant": 3}, has_character_states=False
            )
            == "full"
        )

    def test_stateful_antagonist_keeps_protection(self) -> None:
        """有 character_states 的 antagonist 仍受保护。"""
        assert (
            _resolve_profile_level(
                "c-ant", False, True, 20, {"c-ant": 0}, has_character_states=True
            )
            == "full"
        )

    def test_protagonist_never_decays_regardless(self) -> None:
        """主角永不衰减（含从未出场且无 states）。"""
        assert (
            _resolve_profile_level(
                "c-pro", True, False, 50, {"c-pro": 0}, has_character_states=False
            )
            == "full"
        )

    def test_default_has_states_true_backward_compatible(self) -> None:
        """缺省 has_character_states=True 保持旧调用行为（antagonist full）。"""
        assert _resolve_profile_level("c-ant", False, True, 5, {"c-ant": 0}) == "full"


class TestHardTopEviction:
    """模拟 urban 硬顶=4：模板反派符号档案被有状态配角挤出 top-4。"""

    def _char(self, cid: str, name: str, role: str) -> Character:
        return Character(
            character_id=cid,
            project_id="p1",
            name=name,
            role_type=role,  # type: ignore[arg-type]
        )

    def _state(self, cid: str, field: str, value: str) -> CharacterState:
        return CharacterState(character_id=cid, field=field, value=value)

    def test_template_antagonist_dropped_from_top4(self) -> None:
        characters = [
            self._char("c-pro", "陈屿", "protagonist"),
            self._char("c-ant", "周牧野", "antagonist"),  # 模板反派：0 states 未出场
            self._char("c-s1", "周德顺", "supporting"),
            self._char("c-s2", "林知遥", "supporting"),
            self._char("c-s3", "老张", "supporting"),
        ]
        states = [
            self._state("c-s1", "location", "钟表店"),
            self._state("c-s2", "location", "网吧"),
            self._state("c-s3", "emotional_state", "焦虑"),
        ]
        last_appeared = {"c-s1": 2, "c-s2": 3, "c-s3": 4}

        snapshots = _build_character_snapshots(
            characters,
            states,
            current_chapter=5,
            last_appeared_chapters=last_appeared,
        )
        by_id = {s.character_id: s for s in snapshots}

        # 模板反派只剩符号档案（0.2），有状态配角为 full（0.8），主角 1.0
        assert by_id["c-ant"].importance_score == 0.2
        assert by_id["c-s1"].importance_score == 0.8

        # 硬顶=4（同分保先登记顺序）：top-4 不含模板反派
        hard_top = 4
        ranked = sorted(
            snapshots, key=lambda s: s.importance_score, reverse=True
        )[:hard_top]
        assert "c-ant" not in {s.character_id for s in ranked}
        assert "c-pro" in {s.character_id for s in ranked}
        for cid in ("c-s1", "c-s2", "c-s3"):
            assert cid in {s.character_id for s in ranked}
