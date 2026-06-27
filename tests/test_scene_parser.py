"""Tests for scene_parser blank-line fallback (Task 133)."""

from __future__ import annotations

from songyan.utils.scene_parser import parse_scenes


class TestParseScenesExplicitMarkers:
    """显式 ### Scene N 标记优先."""

    def test_two_explicit_scenes(self) -> None:
        content = "### Scene 1\n第一场景内容。\n\n### Scene 2\n第二场景内容。"
        scenes = parse_scenes(content)
        assert len(scenes) == 2
        assert scenes[0]["scene_number"] == 1
        assert "第一场景" in scenes[0]["content"]
        assert scenes[1]["scene_number"] == 2
        assert "第二场景" in scenes[1]["content"]

    def test_explicit_markers_take_precedence_over_blank_lines(self) -> None:
        content = "### Scene 1\n第一段。\n\n第二段。\n\n### Scene 2\n第三段。"
        scenes = parse_scenes(content)
        assert len(scenes) == 2
        # 第一个场景包含两个段落（因为它们在 Scene 2 之前）
        assert "第一段" in scenes[0]["content"]
        assert "第二段" in scenes[0]["content"]


class TestParseScenesBlankLines:
    """无显式标记时按空行分块."""

    def test_blank_lines_split_into_two_scenes(self) -> None:
        content = "第一段场景内容，长度足够。" * 20 + "\n\n" + "第二段场景内容，长度也足够。" * 20
        scenes = parse_scenes(content)
        assert len(scenes) == 2
        assert "第一段" in scenes[0]["content"]
        assert "第二段" in scenes[1]["content"]

    def test_short_transition_block_merged(self) -> None:
        """短过渡段（<80 字）应合并到相邻场景，而不是独立成场景."""
        long_a = "场景A的长内容。" * 30
        transition = "过渡。"
        long_b = "场景B的长内容。" * 30
        content = f"{long_a}\n\n{transition}\n\n{long_b}"
        scenes = parse_scenes(content)
        assert len(scenes) == 2
        assert "场景A" in scenes[0]["content"]
        assert "过渡" in scenes[0]["content"]
        assert "场景B" in scenes[1]["content"]

    def test_leading_short_block_merged_into_first_scene(self) -> None:
        long = "主场景内容。" * 30
        content = f"短引子。\n\n{long}"
        scenes = parse_scenes(content)
        assert len(scenes) == 1
        assert "短引子" in scenes[0]["content"]
        assert "主场景" in scenes[0]["content"]

    def test_all_short_blocks_become_one_scene(self) -> None:
        content = "短句一。\n\n短句二。\n\n短句三。"
        scenes = parse_scenes(content)
        assert len(scenes) == 1

    def test_empty_content_returns_empty(self) -> None:
        assert parse_scenes("") == []
        assert parse_scenes("   \n\n  ") == []

    def test_multiple_blank_lines_treated_as_one_separator(self) -> None:
        long_a = "场景A内容。" * 30
        long_b = "场景B内容。" * 30
        content = f"{long_a}\n\n\n\n{long_b}"
        scenes = parse_scenes(content)
        assert len(scenes) == 2

    def test_scene_numbering_starts_at_one(self) -> None:
        long_a = "场景A内容。" * 30
        long_b = "场景B内容。" * 30
        long_c = "场景C内容。" * 30
        content = f"{long_a}\n\n{long_b}\n\n{long_c}"
        scenes = parse_scenes(content)
        assert [s["scene_number"] for s in scenes] == [1, 2, 3]


class TestParseScenesContentPreservation:
    """分块后全文内容应被保留."""

    def test_all_content_present(self) -> None:
        long_a = "场景A内容。" * 30
        long_b = "场景B内容。" * 30
        content = f"{long_a}\n\n{long_b}"
        scenes = parse_scenes(content)
        reconstructed = "\n\n".join(s["content"] for s in scenes)
        assert long_a in reconstructed
        assert long_b in reconstructed
