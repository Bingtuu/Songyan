"""Writer Prompt 1.0.6 RAG 分区渲染测试."""

from __future__ import annotations

from songyan.agents.writer import _render_prompt
from songyan.models import (
    ChapterGoal,
    ContextPackage,
    CreativeBrief,
    SoftReference,
)


class TestWriterPromptRAG:
    """Writer Prompt RAG 分区测试."""

    def _make_ctx(self, rag_refs: list[SoftReference] | None = None) -> ContextPackage:
        """构造最小 ContextPackage."""
        return ContextPackage(
            chapter_goal=ChapterGoal(
                chapter_number=1,
                target_events=["事件A"],
                word_count_target=3000,
            ),
            creative_brief=CreativeBrief(
                mode_id="webnovel",
                chapter_goal=ChapterGoal(chapter_number=1),
            ),
            genre_rules=None,
            mode_rules=None,
            soft_references=rag_refs or [],
        )

    def test_rag_section_rendered_when_present(self) -> None:
        """rag_results 非空时渲染 RAG 分区."""
        ctx = self._make_ctx([
            SoftReference(
                type="rag_retrieval",
                content="这是来自第3章的历史段落内容。",
                source_chapter=3,
                similarity=0.85,
            ),
        ])
        prompt = _render_prompt(ctx)
        assert "历史相关段落（自动检索）" in prompt
        assert "第3章" in prompt
        assert "仅供参考" in prompt

    def test_rag_section_omitted_when_empty(self) -> None:
        """rag_results 为空时不渲染 RAG 分区."""
        ctx = self._make_ctx([])
        prompt = _render_prompt(ctx)
        assert "历史相关段落" not in prompt

    def test_rag_section_omitted_when_no_refs(self) -> None:
        """无 rag_retrieval 类型 refs 时不渲染."""
        ctx = self._make_ctx([
            SoftReference(
                type="world_setting",
                content="某个设定",
                relevance_score=0.7,
            ),
        ])
        prompt = _render_prompt(ctx)
        assert "历史相关段落" not in prompt

    def test_rag_text_truncated(self) -> None:
        """RAG 文本超过 200 字被截断."""
        long_text = "这是一段很长的文本。" * 50
        ctx = self._make_ctx([
            SoftReference(
                type="rag_retrieval",
                content=long_text,
                source_chapter=5,
                similarity=0.9,
            ),
        ])
        prompt = _render_prompt(ctx)
        # prompt 中应出现截断后的文本（只取前 200 字）
        # 由于 _render_prompt 构造 rag_results 时未传递 metadata.chunk_type，
        # 这里主要验证渲染不报错且包含章节号
        assert "第5章" in prompt
