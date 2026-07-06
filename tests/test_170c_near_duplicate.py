"""Task 170c: T9 近似/改写重复检测补强.

回归样本来自 170b Ch31 真实漏报（min_chars=100 floor 把 70-95 字重复滤掉）。
锁定：分级阈值既能抓 40-100 字近似重复，又不误伤短句 refrain 与中段不同段落。
"""

from __future__ import annotations

from songyan.agents.rule_auditor import detect_duplicate_paragraphs

# --- Ch31 真实漏报片段（归一化 70-95 字，旧 floor=100 会滤掉）---

# 段19 / 段23：近似改写重复（段23 多了前缀"愤怒来得很快，"），实测 ratio≈0.96
CH31_PAIR1_A = (
    "像一股电流从脊椎底部窜上来，穿过胸腔，在颅骨内壁炸开。"
    "林渊的右手痉挛了一下，手指在触控板上划出一道歪歪扭扭的线。"
    "他深吸一口气，强迫自己把注意力拉回到数据上。现在不是愤怒的时候。"
)
CH31_PAIR1_B = "愤怒来得很快，" + CH31_PAIR1_A

# 段24 / 段32：逐字重复，ratio=1.0，归一化 70 字
CH31_PAIR2 = (
    "林渊的指尖在触控板上划动，将七条光谱线的数据分别导出。"
    "他的动作变得更快，更急切——不是因为他想找到更多证据，"
    "而是因为他想否认自己看到的东西。"
)


def _long_para(marker: str = "A") -> str:
    """归一化 >100 字的长段落（复用 test_161 风格）."""
    return (
        f"林渊把第{marker}段观测记录压在掌心，沿着裂开的甲板向前。"
        "雾面屏上残留的光像被潮汐拖长的伤口，逐行显示旧港区的压力曲线。"
        "他没有立刻下结论，只把每一次金属回声、每一次管线震颤、"
        "每一处温度异常都写进临时日志，等待它们在下一次共振里互相印证。"
    )


class TestCh31RegressionNowDetected:
    """170c 回归：Ch31 的两处漏报现在必须检出."""

    def test_midlength_verbatim_duplicate_detected(self) -> None:
        text = f"{CH31_PAIR2}\n\n中间隔一段无关内容占位。\n\n{CH31_PAIR2}"

        matches = detect_duplicate_paragraphs(text)

        assert len(matches) == 1
        assert matches[0].similarity == 1.0
        assert matches[0].duplicate_of_index == 1

    def test_midlength_near_rewrite_duplicate_detected(self) -> None:
        text = f"{CH31_PAIR1_A}\n\n隔断段落。\n\n{CH31_PAIR1_B}"

        matches = detect_duplicate_paragraphs(text)

        assert len(matches) == 1
        assert matches[0].similarity >= 0.95


class TestBackwardCompatLongParagraph:
    """长段落（≥100 字）的既有行为不回退."""

    def test_long_exact_duplicate_still_detected(self) -> None:
        para = _long_para()
        text = f"{para}\n\n过渡段。\n\n{para}"

        matches = detect_duplicate_paragraphs(text)

        assert len(matches) == 1
        assert matches[0].similarity == 1.0

    def test_long_high_similarity_at_0_9_still_detected(self) -> None:
        para = _long_para()
        variant = para.replace("压力曲线", "潮汐压力曲线", 1)
        text = f"{para}\n\n{variant}"

        matches = detect_duplicate_paragraphs(text)

        assert len(matches) == 1
        assert matches[0].similarity >= 0.9


class TestNoFalsePositive:
    """负样本：短 refrain 与中段不同段落不得误伤."""

    def test_short_refrain_below_floor_preserved(self) -> None:
        text = "不。\n\n不。\n\n是灭口。\n\n是灭口。\n\n警报还在响。\n\n警报还在响。"

        assert detect_duplicate_paragraphs(text) == []

    def test_midlength_distinct_paragraphs_not_flagged(self) -> None:
        # 两段同题材但内容不同，相似度应远低于 0.95，不得误报。
        a = (
            "他调出信天翁号的飞行数据记录，与日志中的时间戳交叉比对，"
            "撞击发生在指令下达后的第四十七秒，足够让导航系统被远程接管。"
        )
        b = (
            "她翻开渡鸦母舰的能量分配曲线，把每一次共振峰值标注出来，"
            "峰值之间的间隔越来越短，像是某种倒计时正在逼近临界点。"
        )
        text = f"{a}\n\n{b}"

        assert detect_duplicate_paragraphs(text) == []

    def test_midlength_pair_in_090_095_band_not_flagged(self) -> None:
        # 中段（40-100 字）相似度落在 [0.90, 0.95)：低于中段严阈 0.95 不命中，
        # 但同一对若作为长段（≥100 字）则会被 0.9 命中——证明分级阈值对短段更严。
        base = (
            "林渊盯着屏幕上跳动的波形，七条光谱线在幽蓝的投影里缓慢重组，"
            "每一条都指向一个不同的时间坐标，他分辨不出主线。"
        )
        variant = base.replace("缓慢重组", "急速重组").replace(
            "分辨不出主线", "始终分辨不出主线"
        )
        # 实测归一化长度 54/56、ratio≈0.9455：介于长段阈 0.9 与中段严阈 0.95 之间。
        text = f"{base}\n\n{variant}"

        assert detect_duplicate_paragraphs(text) == []

        # 反证：同一段文本，若按长段阈值（0.9）判定则会命中——
        # 直接改 long_paragraph_chars 使这对被当作长段，隔离验证分级边界（不改文本、不改 ratio）。
        long_tier_matches = detect_duplicate_paragraphs(text, long_paragraph_chars=40)

        assert len(long_tier_matches) == 1
        assert 0.9 <= long_tier_matches[0].similarity < 0.95
