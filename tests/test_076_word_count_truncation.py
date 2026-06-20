"""Task 076: Writer 强制字数截断 — 单元测试."""

from __future__ import annotations

from songyan.agents.writer import _enforce_word_count, _parse_scenes


def _make_content(scene_texts: list[str]) -> str:
    """Generate test content with scene headers."""
    parts: list[str] = []
    for i, text in enumerate(scene_texts, 1):
        parts.append(f"### Scene {i}")
        parts.append(text)
    return "\n\n".join(parts)


class TestNoTruncationNeeded:
    def test_under_threshold(self) -> None:
        content = _make_content(["这是第一段正文。", "这是第二段正文。"])
        scenes = _parse_scenes(content)
        wc = 100
        result = _enforce_word_count(content, scenes, 100, wc)
        assert result[3] is False
        assert result[0] == content

    def test_at_threshold_exact(self) -> None:
        content = _make_content(["字" * 65, "字" * 65])
        scenes = _parse_scenes(content)
        wc = 130
        result = _enforce_word_count(content, scenes, 100, wc)
        assert result[3] is False


class TestTruncationMultiScene:
    def test_truncates_last_scene(self) -> None:
        # Task 095: min_scenes=2，截断后须保留至少 2 个 scene
        # 4 个 scene，截断到 scene3 前保留 2 个 scene（300 字，在 [240, 360] 内）
        content = _make_content(["一" * 150, "二" * 150, "三" * 200, "四" * 300])
        scenes = _parse_scenes(content)
        target = 300
        wc = 800
        result = _enforce_word_count(content, scenes, target, wc)
        assert result[3] is True
        assert result[2] <= int(target * 1.20)
        assert len(result[1]) < len(scenes)
        assert len(result[1]) >= 2  # Task 095: 至少保留 2 个 scene
        assert "三" not in result[0]
        assert "四" not in result[0]

    def test_truncation_reason_contains_scene_number(self) -> None:
        # Task 095: 4 个 scene，截断到 scene3 前保留 2 个 scene（160 字，在 [160, 300] 内）
        content = _make_content(["一" * 80, "二" * 80, "三" * 150, "四" * 150])
        scenes = _parse_scenes(content)
        wc = 460
        result = _enforce_word_count(content, scenes, 200, wc)
        assert result[3] is True
        assert "truncated_before_scene_" in result[4]

    def test_scene_count_reduced_but_nonzero(self) -> None:
        # Task 095: 4 个 scene，截断到 scene3 前保留 2 个 scene（360 字，刚好在 upper 内）
        content = _make_content(
            ["短正文。" * 40, "中等长度。" * 40, "较长内容。" * 50, "很长内容。" * 50]
        )
        scenes = _parse_scenes(content)
        target = 300
        wc = 860
        result = _enforce_word_count(content, scenes, target, wc)
        assert result[3] is True
        assert len(result[1]) >= 2  # Task 095: 至少保留 2 个 scene
        assert result[2] <= int(target * 1.20)
        for s in result[1]:
            assert s["content"].strip(), f"Scene {s['scene_number']} should not be empty"


class TestSingleSceneDisallowed:
    def test_single_scene_marks_disallowed(self) -> None:
        content = _make_content(["单一段落很长很长" * 100])
        scenes = _parse_scenes(content)
        wc = 200
        result = _enforce_word_count(content, scenes, 100, wc)
        assert result[3] is False  # 077c: 保护放行 ≠ 物理截断
        assert result[4] == "truncation_would_destroy_structure"
        assert result[0] == content

    def test_single_scene_content_preserved(self) -> None:
        content = _make_content(["保持原文不动的测试。"])
        scenes = _parse_scenes(content)
        wc = 500
        result = _enforce_word_count(content, scenes, 100, wc)
        assert result[0] == content
        assert result[4] == "truncation_would_destroy_structure"


class TestEdgeCases:
    def test_empty_content(self) -> None:
        result = _enforce_word_count("", [], 100, 0)
        assert result[3] is False

    def test_no_scene_headers(self) -> None:
        content = "没有 scene 标题的纯文本段落。" * 50
        scenes: list[dict] = [{"scene_number": 1, "content": content}]
        wc = 150
        result = _enforce_word_count(content, scenes, 100, wc)
        assert result[3] is False  # 077c: 无 scene 标题时不截断

    def test_many_scenes(self) -> None:
        texts = [f"Scene {i} 正文内容填充到足够长度。" * 15 for i in range(1, 11)]
        content = _make_content(texts)
        scenes = _parse_scenes(content)
        wc = 2000
        target = 500
        result = _enforce_word_count(content, scenes, target, wc)
        assert result[3] is True
        assert result[2] <= int(target * 1.20)
        for s in result[1]:
            assert s["content"].strip(), f"Scene {s['scene_number']} 不应为空"


class TestSceneReParse:
    def test_truncated_scene_numbers_contiguous(self) -> None:
        # Task 095: 3 个 scene，截断到 scene3 前保留 2 个 scene（300 字）
        content = _make_content(["正" * 150, "文" * 150, "长" * 300])
        scenes = _parse_scenes(content)
        wc = 600
        result = _enforce_word_count(content, scenes, 300, wc)
        assert result[3] is True
        for i, s in enumerate(result[1], 1):
            assert s["scene_number"] == i

    def test_truncated_content_scene_boundary_aligned(self) -> None:
        # Task 095: 4 个 scene，截断到 scene4 前保留 3 个 scene（330 字）
        content = _make_content(
            [
                "正文内容填充足够长度。" * 10,
                "正文内容填充足够长度。" * 10,
                "正文内容填充足够长度。" * 10,
                "正文内容填充足够长度。" * 50,
            ]
        )
        scenes = _parse_scenes(content)
        wc = 888
        result = _enforce_word_count(content, scenes, 300, wc)
        assert result[3] is True
        last_scene = result[1][-1]
        assert "### Scene" not in last_scene["content"]
