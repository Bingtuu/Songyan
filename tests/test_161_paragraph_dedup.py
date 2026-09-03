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


# ---------------------------------------------------------------------------
# Task 225: 句子级逐字重复检测
# 语料来源：.tmp/225_ch2_new.txt（rev-2-12 被误 accept 脏版）、
# .tmp/225_old_ch3_accepted.txt（旧 Ch3 accepted 的逐字重复句）。
# 背景：段落级相似度检测漏掉「两段共享一个逐字长句但整体相似度 < 0.95」的情况。
# ---------------------------------------------------------------------------
_CH2_NEW_DUP_SENTENCE = "对话框关闭后，8.0kg的缺口没有扩大，反而被固定成一个可复测的间隔。"
_CH2_NEW_TRIPLE_SENTENCE = "沈砚的视线扫过它，没有停留。"
_OLD_CH3_DUP_SENTENCE = (
    "他撤销了手动关联请求，在比对规则里把“合并同源对象”改为“保留独立对象并生成会话内临时标签”。"
)


class TestDuplicateSentenceDetection:
    def test_detects_verbatim_sentence_across_dissimilar_paragraphs(self) -> None:
        """ch2_new 真实形态：两段共享逐字长句但段落整体不重复（相似度 ~0.79）."""
        para_a = f"然后他移动光标，选择了“否”。系统没有再次询问。{_CH2_NEW_DUP_SENTENCE}"
        para_b = (
            f"系统没有再次询问。{_CH2_NEW_DUP_SENTENCE}"
            "本地终端在间隔两侧添加了测量基准点，使这段缺口可以被未来的任何复核操作精确复现。"
        )
        text = f"前文铺垫段落，内容完全不同。\n\n{para_a}\n\n{para_b}"

        matches = detect_duplicate_paragraphs(text)

        assert len(matches) == 1
        assert matches[0].matched_text == _CH2_NEW_DUP_SENTENCE
        assert matches[0].paragraph_index == 3
        assert matches[0].duplicate_of_index == 2
        assert matches[0].similarity == 1.0
        assert matches[0].location.startswith("第3段")
        assert matches[0].original_location.startswith("第2段")

    def test_old_ch3_style_verbatim_sentence_hit(self) -> None:
        """old_ch3_accepted 的逐字重复句（47 字）必须命中."""
        para_a = f"他盯着比对结果看了很久。{_OLD_CH3_DUP_SENTENCE}"
        para_b = f"{_OLD_CH3_DUP_SENTENCE}标签生成后，会话日志里多了一条可回溯的记录。"

        matches = detect_duplicate_paragraphs(f"{para_a}\n\n{para_b}")

        assert len(matches) == 1
        assert matches[0].matched_text == _OLD_CH3_DUP_SENTENCE
        assert matches[0].similarity == 1.0

    def test_triple_occurrence_reports_each_repeat(self) -> None:
        """ch2_new 中 ×3 的 14 字句：第二次、第三次出现各报一条."""
        para_a = f"关闭选项在屏幕上闪烁。{_CH2_NEW_TRIPLE_SENTENCE}他转而看向接收选项。"
        para_b = f"审计会话的关闭选项再次亮起。{_CH2_NEW_TRIPLE_SENTENCE}他没有触碰关闭选项。"
        para_c = f"拒绝选项同样在屏幕上。{_CH2_NEW_TRIPLE_SENTENCE}拒绝会让责任质量悬置。"
        text = f"{para_a}\n\n{para_b}\n\n{para_c}"

        matches = detect_duplicate_paragraphs(text)

        assert len(matches) == 2
        assert {m.paragraph_index for m in matches} == {2, 3}
        assert all(m.duplicate_of_index == 1 for m in matches)
        assert all(m.matched_text == _CH2_NEW_TRIPLE_SENTENCE for m in matches)

    def test_short_sentence_below_min_chars_ignored(self) -> None:
        """归一化后 < 12 字的句子重复不报（防误伤短 refrain）."""
        text = "他沉默了。系统没有再次询问。\n\n她签字前停顿了一秒。系统没有再次询问。"

        assert detect_duplicate_paragraphs(text) == []

    def test_ch1_style_numeric_readings_no_false_positive(self) -> None:
        """Ch1 accepted 风格：27.00kg 等数值多次出现但句子整体不同，不命中."""
        text = (
            "责任质量差值那一栏从0.00kg跳到27.00kg，又跳回0.00kg。\n\n"
            "差值停在27.00kg的整数上，没有再变动。\n\n"
            "沈砚把扫描结果和磁锁回执并排放在屏幕上，两个数据之间的差值精确地等于27.00kg。\n\n"
            "协议文本被存进离线记录，差值静止在27.00kg，没有继续增长。"
        )

        assert detect_duplicate_paragraphs(text) == []

    def test_sentence_match_deduped_against_paragraph_match(self) -> None:
        """段落级已命中的后现段落，其内部句子级命中须去重，不重复计数."""
        para = _long_para()
        text = f"{para}\n\n过渡段。\n\n{para}"

        matches = detect_duplicate_paragraphs(text)

        assert len(matches) == 1
        assert matches[0].matched_text == para
        assert matches[0].paragraph_index == 3

    def test_clean_text_zero_hits(self) -> None:
        """干净重写版（ch2_v13 形态）：零重复，必须零命中."""
        text = (
            "沈砚把完整链路重新走了一遍，每一步都留下独立的时间戳。\n\n"
            "复核终端亮起绿色的状态灯，缺口数值保持稳定，没有任何漂移。\n\n"
            "他合上记录本，确认这次会话可以归档，然后起身离开了值班席。"
        )

        assert detect_duplicate_paragraphs(text) == []
