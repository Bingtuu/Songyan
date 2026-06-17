"""Task 080: 角色出场窗口 — 只加载当前 Arc 内出场角色 — 单元测试."""

from __future__ import annotations

from songyan.agents.context_manager._assemblers import _build_character_snapshots
from songyan.models import ChapterSummary, Character, CharacterState


def _make_char(
    char_id: str,
    name: str,
    role_type: str = "supporting",
    goals: list[str] | None = None,
) -> Character:
    return Character(
        character_id=char_id,
        project_id="p1",
        name=name,
        role_type=role_type,
        goals=goals or [],
    )


def _make_summary(
    chapter_number: int,
    characters_appeared: list[str] | None = None,
) -> ChapterSummary:
    return ChapterSummary(
        chapter_number=chapter_number,
        summary="摘要",
        characters_appeared=characters_appeared or [],
    )


# =============================================================================
# Arc 边界与角色过滤
# =============================================================================

class TestArcWindowFiltering:
    def test_arc_appeared_gets_full_profile(self) -> None:
        """当前 arc 内出场的角色获得完整档案."""
        characters = [
            _make_char("c1", "主角", "protagonist"),
            _make_char("c2", "配角A", "supporting", goals=["目标A"]),
            _make_char("c3", "配角B", "supporting"),
        ]
        character_states = [
            CharacterState(character_id="c2", field="location", value="飞船"),
            CharacterState(character_id="c2", field="emotional_state", value="紧张"),
        ]
        summaries = [
            _make_summary(1, ["主角"]),
            _make_summary(2, ["配角A"]),  # arc 1-10
        ]
        snapshots = _build_character_snapshots(
            characters,
            character_states,
            recent_summaries=summaries,
            arc_boundaries=[10],
            current_chapter=5,
        )
        by_name = {s.name: s for s in snapshots}
        assert by_name["配角A"].current_location == "飞船"
        assert by_name["配角A"].emotional_state == "紧张"
        assert by_name["配角A"].importance_score == 0.8

    def test_non_arc_gets_skipped(self) -> None:
        """Task 110c: 非 arc 角色直接 skip（protagonist/antagonist 除外）."""
        characters = [
            _make_char("c1", "主角", "protagonist"),
            _make_char("c2", "配角A", "supporting"),
        ]
        summaries = [
            _make_summary(1, ["主角"]),  # arc 1-10，配角A 未出场
        ]
        snapshots = _build_character_snapshots(
            characters,
            [],
            recent_summaries=summaries,
            arc_boundaries=[10],
            current_chapter=5,
        )
        by_name = {s.name: s for s in snapshots}
        assert "配角A" not in by_name
        assert "主角" in by_name

    def test_protagonist_always_full(self) -> None:
        """主角始终获得完整档案，无论是否在 arc 内出场."""
        characters = [
            _make_char("c1", "主角", "protagonist", goals=["拯救世界"]),
        ]
        summaries = [
            _make_summary(1, []),  # 主角未在 arc 内出场
        ]
        snapshots = _build_character_snapshots(
            characters,
            [],
            recent_summaries=summaries,
            arc_boundaries=[10],
            current_chapter=5,
        )
        assert snapshots[0].name == "主角"
        assert snapshots[0].unresolved_issues == ["拯救世界"]
        assert snapshots[0].importance_score == 1.0

    def test_no_arc_boundaries_fallback(self) -> None:
        """无 arc_boundaries 时回退到最近 3 章行为."""
        characters = [
            _make_char("c1", "主角", "protagonist"),
            _make_char("c2", "配角A", "supporting"),
            _make_char("c3", "配角B", "supporting"),
        ]
        summaries = [
            _make_summary(48, ["配角A"]),
            _make_summary(49, ["配角A"]),
            _make_summary(50, ["配角B"]),
        ]
        snapshots = _build_character_snapshots(
            characters,
            [],
            recent_summaries=summaries,
            arc_boundaries=[],
            current_chapter=50,
        )
        names = {s.name for s in snapshots}
        assert "配角A" in names
        assert "配角B" in names
        assert "主角" in names

    def test_arc_boundary_correctly_resolved(self) -> None:
        """arc 边界正确确定当前章节所属 arc."""
        characters = [
            _make_char("c1", "主角", "protagonist"),
            _make_char("c2", "旧角色", "supporting"),
            _make_char("c3", "新角色", "supporting"),
        ]
        summaries = [
            _make_summary(1, ["旧角色"]),   # arc 1
            _make_summary(15, ["新角色"]),  # arc 2
        ]
        # arc_boundaries=[10] → arc1=1-10, arc2=11-20
        # current_chapter=15 → 属于 arc2
        snapshots = _build_character_snapshots(
            characters,
            [],
            recent_summaries=summaries,
            arc_boundaries=[10],
            current_chapter=15,
        )
        by_name = {s.name: s for s in snapshots}
        # 主角始终完整
        assert by_name["主角"].importance_score == 1.0
        # 新角色在 arc2 出场 → 完整
        assert by_name["新角色"].importance_score == 0.8
        # 旧角色只在 arc1 出场 → Task 110c 直接 skip
        assert "旧角色" not in by_name

    def test_character_states_total_not_in_snapshot(self) -> None:
        """character_states_total 在 ContextPackage 中，不在 snapshot 中."""
        # 此测试验证 _build_character_snapshots 返回的是过滤后的列表
        characters = [
            _make_char("c1", "主角", "protagonist"),
            _make_char("c2", "配角", "supporting"),
        ]
        snapshots = _build_character_snapshots(
            characters, [], recent_summaries=[_make_summary(1, ["主角"])]
        )
        assert len(snapshots) == 1  # 只加载主角
