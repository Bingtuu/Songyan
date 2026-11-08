"""M4 步 4 切片 3: 复读启发式（tech-m4 §4.4 / B8）。

三腿各自命中 + 干净正文不误报；阈值原样（evals/excellence_signals.py:30,636-671
口径：句 ≥12 归一化字符且 ≥3 次；段落 ≥40 归一化字符且 ≥2 次；跨章句 ≥14）。
跨章腿语义 = 与上一章 accepted 正文比对（evals 原「跨样本语料索引」不适配单项目
逐章审，任务文档评审 M1 修入）；无上一章正文 → 跳过此腿。
"""

from __future__ import annotations

from songyan.plan_checks.repetition_check import (
    MIN_CROSS_CHAPTER_SENTENCE_LEN,
    MIN_REPEAT_PARAGRAPH_LEN,
    MIN_REPEAT_SENTENCE_LEN,
    check_repetition,
)

_REPEAT_SENT = "末班车在午夜十二点准时进站了。"  # 归一化 14 字符 ≥ 12
_PARAGRAPH = (
    "雨下了整整一夜，站台上积着薄薄的水，灯光落在水面上碎成一片。"
    "他把那枚末班铜牌攥在掌心里，掌心已经被边缘硌出了红痕。"
)  # 归一化长度 ≥ 40


def test_constants_locked() -> None:
    """阈值原样锁死：句 12 / 段落 40 / 跨章句 14。"""
    assert MIN_REPEAT_SENTENCE_LEN == 12
    assert MIN_REPEAT_PARAGRAPH_LEN == 40
    assert MIN_CROSS_CHAPTER_SENTENCE_LEN == 14


def test_sentence_repeat_hit() -> None:
    """同一句子逐字出现 3 次 → 句子腿命中，count=3。"""
    text = f"夜雨未停。\n\n{_REPEAT_SENT}\n\n{_REPEAT_SENT}\n\n{_REPEAT_SENT}\n\n铜镜微凉。"
    hits = check_repetition(text, chapter=2)
    sentence_hits = [h for h in hits if h.kind == "sentence"]
    assert len(sentence_hits) == 1
    hit = sentence_hits[0]
    assert hit.count == 3
    assert hit.quote == _REPEAT_SENT
    assert hit.location != ""


def test_sentence_repeat_twice_no_hit() -> None:
    """只出现 2 次（< 3）不命中。"""
    text = f"{_REPEAT_SENT}\n\n{_REPEAT_SENT}"
    assert [h for h in check_repetition(text, chapter=2) if h.kind == "sentence"] == []


def test_short_sentence_no_hit() -> None:
    """归一化 < 12 字符的短句即使 ≥3 次也不命中。"""
    text = "末班车走了。\n末班车走了。\n末班车走了。\n末班车走了。"
    assert check_repetition(text, chapter=2) == []


def test_paragraph_repeat_hit() -> None:
    """同一长段落（归一化 ≥40）出现 2 次 → 段落腿命中。"""
    text = f"{_PARAGRAPH}\n\n{_PARAGRAPH}"
    hits = [h for h in check_repetition(text, chapter=2) if h.kind == "paragraph"]
    assert len(hits) == 1
    assert hits[0].count == 2


def test_cross_chapter_hit() -> None:
    """当前章句子与上一章 accepted 正文逐字重复 → 跨章腿命中。"""
    current = "站台尽头钟声响起。他把那枚末班铜牌紧紧攥在掌心里。夜雨未停。"
    previous = "上一章的旧稿。他把那枚末班铜牌紧紧攥在掌心里。别的句子。"
    hits = check_repetition(
        current, chapter=2, previous_accepted_text=previous
    )
    cross = [h for h in hits if h.kind == "cross_chapter"]
    assert len(cross) == 1
    assert cross[0].quote == "他把那枚末班铜牌紧紧攥在掌心里。"
    assert cross[0].count >= 1


def test_cross_chapter_skipped_without_previous() -> None:
    """无上一章正文 → 跨章腿跳过，不炸不命中。"""
    current = "他把那枚末班铜牌紧紧攥在掌心里。夜雨未停。"
    assert check_repetition(current, chapter=1, previous_accepted_text=None) == []


def test_cross_chapter_short_sentence_no_hit() -> None:
    """跨章比对句归一化 < 14 字符 → 不命中。"""
    short = "末班车走了。"
    current = f"{short}别的内容再写一点。"
    previous = f"上一章。{short}别的。"
    hits = check_repetition(current, chapter=2, previous_accepted_text=previous)
    assert [h for h in hits if h.kind == "cross_chapter"] == []


def test_clean_text_no_hits() -> None:
    """干净正文：无逐字复读 → 零命中。"""
    text = (
        "夜雨落在南站站台。\n\n陈照收起铜镜，转身走进雨里。\n\n"
        "末班车进站了，车灯切开雨幕。\n\n他踏上台阶，没有再回头。"
    )
    assert check_repetition(text, chapter=2) == []
