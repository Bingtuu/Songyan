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


# Task 171q: 去重助手口径与冻结 T9 检测器对齐（min_chars=40 + 分级阈值 0.95/0.9）。
# 中段（[40,100) 字）逐字重复段落 = detect_duplicate_paragraphs 所判 stutter，
# 修复前 min_chars=100 漏删；修复后默认参数即删。0.90–0.95 中段对 T9 判为"不同"，
# 助手须保留（防回退平铺 0.9 造成镜像过度删除）。
_MID_VERBATIM = (
    "林渊的手指在触控板上快速移动，他不是在断开接口，而是在逆向解析那段次声波脉冲的编码。"
)
_MID_NEAR_A = (
    "警报持续鸣响，控制舱的红光每隔三秒扫过舷窗，映在他紧绷的侧脸上，一次又一次地提醒着倒计时。"
)
_MID_NEAR_B = (
    "警报持续鸣响，控制舱的蓝光每隔五秒扫过舷窗，映在她紧绷的侧脸上，一次又一次地提醒着倒计时。"
)


class TestMidLengthDedupAlignedToT9:
    def test_mid_length_verbatim_removed_by_default(self) -> None:
        """[40,100) 字逐字重复段落经默认参数即删（回归防 min_chars 漂回 100）."""
        paragraphs = ["开头短段。", _MID_VERBATIM, "过渡段落但很短。", _MID_VERBATIM]

        result = _dedup_long_paragraphs(paragraphs)

        assert result.count(_MID_VERBATIM) == 1
        # detector（冻结 T9）在去重后应判 0 重复。
        assert detect_duplicate_paragraphs("\n\n".join(result)) == []

    def test_mid_length_verbatim_removed_via_reassemble(self) -> None:
        scenes = [
            {"scene_number": 1, "content": "旧一", "header": "### Scene 1"},
            {"scene_number": 2, "content": "旧二", "header": "### Scene 2"},
        ]
        revised = [_MID_VERBATIM, f"独有内容段。\n\n{_MID_VERBATIM}"]

        result = _reassemble_content(scenes, revised)

        assert result.count(_MID_VERBATIM) == 1
        assert "独有内容段。" in result
        assert detect_duplicate_paragraphs(result) == []

    def test_mid_length_near_pair_090_095_band_preserved(self) -> None:
        """镜像 T9：[40,100) 段 similarity∈[0.90,0.95) 判为不同，助手须双双保留."""
        paragraphs = [_MID_NEAR_A, "中间过渡短句。", _MID_NEAR_B]

        result = _dedup_long_paragraphs(paragraphs)

        assert _MID_NEAR_A in result
        assert _MID_NEAR_B in result
        # 与检测器一致：该中段对不应被判重复。
        text = f"{_MID_NEAR_A}\n\n{_MID_NEAR_B}"
        assert detect_duplicate_paragraphs(text) == []
