"""Tests for Task 171c deterministic exposition post-processing transform."""

from __future__ import annotations

from songyan.utils.literary_postproc import split_long_expository_quotes


class TestSplitLongExpositoryQuotes:
    def test_no_quotes_unchanged(self) -> None:
        text = "林渊走进舱室，灯光昏暗。"
        out, n = split_long_expository_quotes(text)
        assert out == text
        assert n == 0

    def test_short_quote_not_split(self) -> None:
        text = "他说：“走吧。”"
        out, n = split_long_expository_quotes(text)
        assert out == text
        assert n == 0

    def test_long_multi_sentence_quote_split(self) -> None:
        body = "这是方舟的核心机制。" + "它由建造者文明留下。" + "钥匙藏在木卫二深处。"
        text = f"他解释道：“{body}”"
        out, n = split_long_expository_quotes(text, min_chars=10)
        assert n == 1
        # content-preserving：所有汉字都保留（只增删引号标点）
        assert body.replace("。", "") in out.replace("。", "").replace("”", "").replace("“", "")
        # 拆成了多段引号
        assert out.count("“") >= 3

    def test_content_preserving_char_set(self) -> None:
        body = "第一句很长需要凑够字数啊啊。" + "第二句也很长凑够字数哦哦。"
        text = f"“{body}”"
        out, _ = split_long_expository_quotes(text, min_chars=10)

        # 去掉引号后，字符序列不变（零内容损失）
        def _strip(s: str) -> str:
            return s.replace("“", "").replace("”", "").replace('"', "")

        assert _strip(out) == _strip(text)

    def test_single_sentence_long_quote_not_split(self) -> None:
        # 单句即使超长也不拆（无句子边界可拆）
        body = "这是一句没有句号结尾的超长说明性独白内容用来测试单句不拆分逻辑是否正确啊"
        text = f"“{body}”"
        out, n = split_long_expository_quotes(text, min_chars=10)
        assert n == 0
        assert out == text

    def test_ascii_quotes_supported(self) -> None:
        body = '第一句凑字数需要很长很长。第二句也要凑字数很长很长。'
        text = f'"{body}"'
        out, n = split_long_expository_quotes(text, min_chars=10)
        assert n == 1
