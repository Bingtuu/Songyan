"""Task 161: 段落级去重与重复长段落检测."""

from __future__ import annotations

from songyan.agents.revision_handler._segmented_revision import (
    _dedup_long_paragraphs,
    _reassemble_content,
)
from songyan.agents.rule_auditor import detect_duplicate_paragraphs, run_rule_audit


def _long_para(marker: str = "A") -> str:
    return (
        f"林渊把第{marker}段观测记录压在掌心，沿着裂开的甲板向前。"
        "雾面屏上残留的光像被潮汐拖长的伤口，逐行显示旧港区的压力曲线。"
        "他没有立刻下结论，只把每一次金属回声、每一次管线震颤、"
        "每一处温度异常都写进临时日志，等待它们在下一次共振里互相印证。"
    )


class TestDedupLongParagraphs:
    def test_exact_duplicate_long_paragraph_removed(self) -> None:
        para = _long_para()
        paragraphs = ["开头短段。", para, "中间过渡。", para, "结尾短段。"]

        result = _dedup_long_paragraphs(paragraphs)

        assert result == ["开头短段。", para, "中间过渡。", "结尾短段。"]

    def test_high_similarity_duplicate_removed(self) -> None:
        para = _long_para()
        variant = para.replace("沿着裂开的甲板向前", "沿着裂开的甲板继续向前", 1)

        result = _dedup_long_paragraphs([para, "过渡。", variant])

        assert result == [para, "过渡。"]

    def test_short_repetition_is_preserved(self) -> None:
        paragraphs = ["不。", "不。", "不。", "警报还在响。", "警报还在响。"]

        result = _dedup_long_paragraphs(paragraphs)

        assert result == paragraphs


class TestDuplicateParagraphDetection:
    def test_detects_duplicate_long_paragraph_with_location(self) -> None:
        para = _long_para()
        text = f"{para}\n\n过渡段。\n\n{para}"

        matches = detect_duplicate_paragraphs(text)

        assert len(matches) == 1
        assert matches[0].paragraph_index == 3
        assert matches[0].duplicate_of_index == 1
        assert matches[0].similarity == 1.0
        assert matches[0].location.startswith("第3段")
        assert matches[0].original_location.startswith("第1段")

    def test_detects_high_similarity_duplicate(self) -> None:
        para = _long_para()
        variant = para.replace("压力曲线", "潮汐压力曲线", 1)
        text = f"{para}\n\n{variant}"

        matches = detect_duplicate_paragraphs(text)

        assert len(matches) == 1
        assert matches[0].similarity >= 0.9

    def test_no_false_positive_for_short_repetition(self) -> None:
        text = "不。\n\n不。\n\n警报还在响。\n\n警报还在响。"

        assert detect_duplicate_paragraphs(text) == []

    def test_run_rule_audit_records_duplicate_count(self) -> None:
        para = _long_para()
        result = run_rule_audit(f"{para}\n\n{para}", word_count_target=100)

        assert result.duplicate_paragraph_count == 1
        assert result.duplicate_paragraph_matches[0].matched_text == para


class TestReassembleContentDedup:
    def test_reassemble_dedups_duplicate_revised_scene_paragraph(self) -> None:
        para = _long_para()
        scenes = [
            {"scene_number": 1, "content": "旧一", "header": "### Scene 1"},
            {"scene_number": 2, "content": "旧二", "header": "### Scene 2"},
        ]
        revised = [para, f"独有段落。\n\n{para}"]

        result = _reassemble_content(scenes, revised)

        assert result.count(para) == 1
        assert "### Scene 1" not in result
        assert "### Scene 2" not in result
        assert "独有段落。" in result

    def test_reassemble_preserves_short_repeated_paragraphs(self) -> None:
        scenes = [
            {"scene_number": 1, "content": "旧一", "header": "### Scene 1"},
            {"scene_number": 2, "content": "旧二", "header": "### Scene 2"},
        ]
        revised = ["不。", "不。"]

        result = _reassemble_content(scenes, revised)

        assert result.count("不。") == 2

    def test_reassemble_strips_scene_markers_from_revised_scene(self) -> None:
        scenes = [
            {"scene_number": 1, "content": "旧一", "header": ""},
            {"scene_number": 2, "content": "旧二", "header": ""},
        ]
        revised = ["### Scene 1\n\n第一段正文。", "Scene 2: 控制室\n\n第二段正文。"]

        result = _reassemble_content(scenes, revised)

        assert "Scene 1" not in result
        assert "Scene 2" not in result
        assert "第一段正文。" in result
        assert "第二段正文。" in result
