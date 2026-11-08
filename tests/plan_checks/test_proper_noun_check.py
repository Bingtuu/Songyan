"""M4 步 4 切片 4: 专名启发式（tech-m4 §4.4 / B8；任务文档钉死规格）。

- 拉丁候选 = 连续 A-Za-z 且首字母大写串（≥2 字符）
- CJK 候选 = 出现 ≥3 次的 2-4 字 n-gram，减停用字表
- 已登记集合由调用方传入（三处并集在 services 层组装）；匹配精确、大小写不敏感
- 命中 = info 级「未登记专名，考虑登记」，非错误
"""

from __future__ import annotations

from songyan.plan_checks.proper_noun_check import check_proper_nouns

_REGISTERED_TEXT = "陈照收起 Kessel 铜牌，走进黑潮会馆。"


def test_latin_unregistered_hit() -> None:
    """未登记拉丁专名（首字母大写、≥2 字符）→ 命中。"""
    hits = check_proper_nouns("陈照遇见 Ashford，再无别人。", chapter=2, registered=frozenset())
    latin = [h for h in hits if h.kind == "latin"]
    assert [h.name for h in latin] == ["Ashford"]
    assert "未登记专名" in latin[0].detail


def test_latin_lowercase_or_single_char_ignored() -> None:
    """小写串或单词内部片段不算候选。"""
    hits = check_proper_nouns("他用 terminal 查到的资料。", chapter=2, registered=frozenset())
    assert [h for h in hits if h.kind == "latin"] == []


def test_cjk_unregistered_hit() -> None:
    """出现 ≥3 次的 2-4 字 n-gram → 命中（长词吸收其短子串候选）。"""
    text = "黑潮会馆亮着灯。\n他离开黑潮会馆。\n黑潮会馆在雨里。"
    hits = check_proper_nouns(text, chapter=2, registered=frozenset())
    cjk = [h for h in hits if h.kind == "cjk"]
    assert [h.name for h in cjk] == ["黑潮会馆"]
    assert cjk[0].count == 3


def test_cjk_below_count_no_hit() -> None:
    """只出现 2 次（< 3）的 n-gram 不命中。"""
    text = "灰港码头亮着灯。\n他离开灰港码头。"
    hits = check_proper_nouns(text, chapter=2, registered=frozenset())
    assert hits == []


def test_cjk_stopword_filtered() -> None:
    """含停用字的 n-gram（在/里…边界）不进候选；命中词本身不含任何停用字。"""
    text = "他在黑潮会馆的。\n她在黑潮会馆的。\n又在黑潮会馆的。"
    hits = check_proper_nouns(text, chapter=2, registered=frozenset())
    assert [h.name for h in hits if h.kind == "cjk"] == ["黑潮会馆"]
    stop_chars = set("的了吗呢吧啊哦嗯在与把被让向从和及或等")
    for hit in hits:
        assert not (set(hit.name) & stop_chars)


def test_registered_exact_no_hit() -> None:
    """已登记名（entity_id / aliases 并集由调用方给入）不命中。"""
    hits = check_proper_nouns(
        _REGISTERED_TEXT, chapter=2, registered=frozenset({"Kessel", "黑潮会馆"})
    )
    assert hits == []


def test_registered_case_insensitive() -> None:
    """匹配大小写不敏感：登记 kessel 命中正文 Kessel。"""
    hits = check_proper_nouns(
        _REGISTERED_TEXT, chapter=2, registered=frozenset({"kessel", "黑潮会馆"})
    )
    assert hits == []


def test_registered_cjk_characters_protagonist_no_hit() -> None:
    """characters protagonist 名（调用方并集）不命中；未登记专名仍命中。"""
    hits = check_proper_nouns(
        "陈照回到陈照的旧屋，遇见 Ashford。",
        chapter=2,
        registered=frozenset({"陈照"}),
    )
    assert [h.name for h in hits] == ["Ashford"]
