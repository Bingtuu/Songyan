"""ContextManager RAG 集成测试."""

from __future__ import annotations

from songyan.agents.context_manager import (
    _build_rag_soft_references,
    assemble_context_package,
)
from songyan.models import (
    ChapterGoal,
    Character,
    CreativeModeProfile,
    GenreProfile,
    NewSetting,
    ProjectSetting,
)
from songyan.models.rag import ChunkMetadata, RetrievedChunk


class TestBuildRAGSoftReferences:
    """RAG soft reference 转换测试."""

    def test_conversion(self) -> None:
        """RetrievedChunk → SoftReference 转换正确."""
        chunks = [
            RetrievedChunk(
                chunk_id="c1",
                text="测试文本",
                chapter_number=3,
                similarity=0.8,
                metadata=ChunkMetadata(),
            ),
        ]
        refs = _build_rag_soft_references(chunks)
        assert len(refs) == 1
        assert refs[0].type == "rag_retrieval"
        assert refs[0].content == "测试文本"
        assert refs[0].source_chapter == 3
        assert refs[0].similarity == 0.8
        assert refs[0].relevance_score == 1.0  # min(0.8 + 0.3, 1.0)

    def test_relevance_score_capped(self) -> None:
        """relevance_score 不超过 1.0."""
        chunks = [
            RetrievedChunk(
                chunk_id="c1",
                text="test",
                chapter_number=1,
                similarity=0.95,
                metadata=ChunkMetadata(),
            ),
        ]
        refs = _build_rag_soft_references(chunks)
        assert refs[0].relevance_score == 1.0


class TestContextPackageRAGIntegration:
    """ContextPackage RAG 集成测试."""

    def _make_basic_inputs(self):
        project = ProjectSetting(
            title="测试", genre_id="xuanhuan", mode_id="webnovel",
            protagonist_name="林凡",
        )
        genre = GenreProfile(
            id="xuanhuan", name="玄幻",
            fatigue_words=[], satisfaction_types=[],
            writer_rules=[], reviewer_focus=[],
            active_audit_dimensions=["style_ai_tells"],
            taboos=["虐主"],
        )
        mode = CreativeModeProfile(
            id="webnovel", name="网文",
            enabled_agents={"pre_write": ["goal_planner"]},
            audit_weights={"style_ai_tells": 0.3},
            active_audit_dimensions=["style_ai_tells"],
            revision_policy="standard",
            tolerance={"max_ai_tells": 2.0, "max_fatigue_words": 3.0},
            context_pruning_strategy="default",
        )
        goal = ChapterGoal(chapter_number=1, target_events=["测试事件"])
        return project, genre, mode, goal

    def test_includes_rag_chunks(self) -> None:
        """rag_chunks 传入后出现在 soft_references 中."""
        project, genre, mode, goal = self._make_basic_inputs()
        rag_chunks = [
            RetrievedChunk(
                chunk_id="c1", text="历史段落", chapter_number=1,
                similarity=0.8, metadata=ChunkMetadata(),
            ),
        ]
        ctx = assemble_context_package(
            chapter_goal=goal,
            creative_brief=None,
            genre_profile=genre,
            mode_profile=mode,
            project=project,
            characters=[Character(character_id="c1", project_id="p1", name="林凡")],
            character_states=[],
            recent_summaries=[],
            active_foreshadowings=[],
            setting_snapshots=[],
            rag_chunks=rag_chunks,
        )
        rag_refs = [r for r in ctx.soft_references if r.type == "rag_retrieval"]
        assert len(rag_refs) == 1
        assert rag_refs[0].content == "历史段落"

    def test_skips_rag_when_none(self) -> None:
        """rag_chunks=None 时不添加 RAG refs."""
        project, genre, mode, goal = self._make_basic_inputs()
        ctx = assemble_context_package(
            chapter_goal=goal,
            creative_brief=None,
            genre_profile=genre,
            mode_profile=mode,
            project=project,
            characters=[Character(character_id="c1", project_id="p1", name="林凡")],
            character_states=[],
            recent_summaries=[],
            active_foreshadowings=[],
            setting_snapshots=[],
            rag_chunks=None,
        )
        rag_refs = [r for r in ctx.soft_references if r.type == "rag_retrieval"]
        assert len(rag_refs) == 0

    def test_rag_priority_over_snapshot(self) -> None:
        """RAG 结果的 relevance_score 高于普通 setting snapshot."""
        project, genre, mode, goal = self._make_basic_inputs()
        rag_chunks = [
            RetrievedChunk(
                chunk_id="c1", text="RAG内容", chapter_number=1,
                similarity=0.5, metadata=ChunkMetadata(),
            ),
        ]
        snapshots = [NewSetting(setting_name="设定A", description="desc", source_quote="")]
        ctx = assemble_context_package(
            chapter_goal=goal,
            creative_brief=None,
            genre_profile=genre,
            mode_profile=mode,
            project=project,
            characters=[Character(character_id="c1", project_id="p1", name="林凡")],
            character_states=[],
            recent_summaries=[],
            active_foreshadowings=[],
            setting_snapshots=snapshots,
            rag_chunks=rag_chunks,
        )
        scores = {r.type: r.relevance_score for r in ctx.soft_references}
        # RAG: 0.5 + 0.3 = 0.8, snapshot: ~0.7
        assert scores["rag_retrieval"] > scores.get("world_setting", 0)

    def test_sorted_by_relevance(self) -> None:
        """RAG 和 snapshot 统一按 relevance_score 降序排序."""
        project, genre, mode, goal = self._make_basic_inputs()
        rag_chunks = [
            RetrievedChunk(
                chunk_id="c1", text="低相似", chapter_number=1,
                similarity=0.4, metadata=ChunkMetadata(),
            ),
            RetrievedChunk(
                chunk_id="c2", text="高相似", chapter_number=2,
                similarity=0.9, metadata=ChunkMetadata(),
            ),
        ]
        ctx = assemble_context_package(
            chapter_goal=goal,
            creative_brief=None,
            genre_profile=genre,
            mode_profile=mode,
            project=project,
            characters=[Character(character_id="c1", project_id="p1", name="林凡")],
            character_states=[],
            recent_summaries=[],
            active_foreshadowings=[],
            setting_snapshots=[],
            rag_chunks=rag_chunks,
        )
        scores = [r.relevance_score for r in ctx.soft_references]
        assert scores == sorted(scores, reverse=True)
