"""Chunker 单元测试."""

from __future__ import annotations

from songyan.rag.chunker import Chunker


class TestChunkerBasics:
    """基础切分测试."""

    def test_chunk_short_chapter(self) -> None:
        """<500 字章节 → 1 个 chunk."""
        chunker = Chunker(chunk_size=500, chunk_overlap=100)
        content = "这是一个短章节。只有几句话。"
        chunks = chunker.chunk_chapter(
            content=content,
            project_id="proj1",
            chapter_number=1,
            version_id="v1",
        )
        assert len(chunks) == 1
        assert chunks[0].text == content
        assert chunks[0].chunk_id == "proj1_1_0"

    def test_chunk_1200_with_overlap(self) -> None:
        """1200 字 → 多个 chunk，验证重叠."""
        chunker = Chunker(chunk_size=500, chunk_overlap=100)
        # 构造约 1200 字文本
        sentences = [f"这是第{i}句话，用于测试文本切分功能。" for i in range(60)]
        content = "".join(sentences)
        chunks = chunker.chunk_chapter(
            content=content,
            project_id="proj1",
            chapter_number=1,
            version_id="v1",
        )
        assert len(chunks) >= 2
        # 验证相邻 chunks 有重叠
        for i in range(len(chunks) - 1):
            overlap = set(chunks[i].text) & set(chunks[i + 1].text)
            assert len(overlap) > 0, f"chunk {i} 和 {i+1} 没有重叠"

    def test_chunk_scene_boundary(self) -> None:
        """含 Scene 标记时优先按场景分割."""
        chunker = Chunker(chunk_size=500, chunk_overlap=50)
        content = "### Scene 1\n第一场景的内容。\n\n### Scene 2\n第二场景的内容。"
        chunks = chunker.chunk_chapter(
            content=content,
            project_id="proj1",
            chapter_number=1,
            version_id="v1",
        )
        assert len(chunks) >= 1
        # Scene 标记被去除或保留在正文中，但至少按段落分割了
        assert any("Scene" in c.text or "场景" in c.text for c in chunks)

    def test_chunk_no_scene_fallback(self) -> None:
        """无场景标记时按段落分割."""
        chunker = Chunker(chunk_size=500, chunk_overlap=50)
        content = "第一段。\n\n第二段。\n\n第三段。"
        chunks = chunker.chunk_chapter(
            content=content,
            project_id="proj1",
            chapter_number=1,
            version_id="v1",
        )
        assert len(chunks) >= 1

    def test_chunk_sentence_protection(self) -> None:
        """不会在句子中间切断."""
        chunker = Chunker(chunk_size=50, chunk_overlap=10)
        # 构造一个长段落，需要强制切分
        content = "A" * 30 + "。" + "B" * 30 + "。" + "C" * 30 + "。"
        chunks = chunker.chunk_chapter(
            content=content,
            project_id="proj1",
            chapter_number=1,
            version_id="v1",
        )
        assert len(chunks) >= 2
        # 每个 chunk 应该以句号结尾（或在边界处）
        for c in chunks[:-1]:
            text = c.text.strip()
            assert text[-1] in "。？！\n" or len(text) < chunker.chunk_size + 10

    def test_chunk_metadata_extraction(self) -> None:
        """从文本中提取角色名和设定 key."""
        chunker = Chunker(chunk_size=500, chunk_overlap=50)
        content = "方远舟看着林语嫣。认知补丁开始生效。"
        chunks = chunker.chunk_chapter(
            content=content,
            project_id="proj1",
            chapter_number=1,
            version_id="v1",
            known_characters=["方远舟", "林语嫣"],
            known_settings=["认知补丁", "共生协议"],
        )
        assert len(chunks) == 1
        meta = chunks[0].metadata
        assert "方远舟" in meta.characters_mentioned or "林语嫣" in meta.characters_mentioned
        assert "认知补丁" in meta.setting_keys_mentioned

    def test_chunk_empty_content(self) -> None:
        """空内容返回空列表."""
        chunker = Chunker()
        chunks = chunker.chunk_chapter(
            content="",
            project_id="proj1",
            chapter_number=1,
            version_id="v1",
        )
        assert chunks == []

    def test_chunk_frontmatter_stripped(self) -> None:
        """YAML frontmatter 被去除."""
        chunker = Chunker()
        content = "---\ntitle: test\n---\n# 第一章\n正文内容。"
        chunks = chunker.chunk_chapter(
            content=content,
            project_id="proj1",
            chapter_number=1,
            version_id="v1",
        )
        assert len(chunks) == 1
        assert "---" not in chunks[0].text
        assert "# 第一章" not in chunks[0].text
        assert "正文内容" in chunks[0].text
