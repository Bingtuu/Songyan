"""RAG indexing end-to-end tests — Task 071 root cause fix verification."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from songyan.db.chunk_repo import ChunkRepository
from songyan.db.repository import ChapterVersionRepository, ProjectRepository
from songyan.models import ChapterVersion, ProjectSetting
from songyan.models.rag import RAGConfig
from songyan.rag.embedder import Embedder
from songyan.rag.retriever import RAGRetriever
from songyan.rag.vector_store import VectorStore
from songyan.workflows._helpers import _index_accepted_chapter

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def proj_with_version(test_db) -> tuple[str, str]:
    """创建项目和已接受章节版本，返回 (project_id, version_id)."""
    project = ProjectSetting(
        title="RAG Test",
        genre_id="xuanhuan",
        mode_id="webnovel",
        protagonist_name="Test",
    )
    await ProjectRepository().create(project, "rag-proj")
    version = ChapterVersion(
        version_id="v-rag-1",
        project_id="rag-proj",
        chapter_number=1,
        version_number=1,
        version_type="draft",
        content="方远舟站在空间站观察窗前。\n\n\"认知补丁已经生效，\"他说。\n\n窗外是永恒的黑暗。",
    )
    await ChapterVersionRepository().create(version)
    return "rag-proj", "v-rag-1"


class TestAcceptVersion:
    """ChapterVersionRepository.accept_version — Task 071 fix."""

    async def test_accept_version_creates_accepted_copy(self, test_db, proj_with_version) -> None:
        """accept_version 保留原版本，创建新的 accepted 版本并返回其 ID."""
        project_id, version_id = proj_with_version
        repo = ChapterVersionRepository()

        before = await repo.get(version_id)
        assert before is not None
        assert before.version_type == "draft"

        accepted_version_id = await repo.accept_version(version_id)

        # 原版本保持 draft 不变
        original = await repo.get(version_id)
        assert original is not None
        assert original.version_type == "draft"

        # 新版本为 accepted
        accepted = await repo.get(accepted_version_id)
        assert accepted is not None
        assert accepted.version_type == "accepted"
        assert accepted.parent_version_id == version_id
        assert accepted.content == original.content


class TestIndexAcceptedChapter:
    """_index_accepted_chapter 完整流程 — 写入 → 加载 → 检索."""

    async def test_index_and_retrieve(self, test_db, proj_with_version) -> None:
        """索引章节后，VectorStore 能加载并检索到结果."""
        project_id, version_id = proj_with_version
        content = (
            "方远舟站在空间站观察窗前。认知补丁已经生效。\n\n"
            "窗外是永恒的黑暗。远处有微弱的星光闪烁。\n\n"
            "\"我们必须找到出路，\"方远舟说。\n\n"
            "控制台发出红色的警报声。系统正在崩溃。"
        )
        rag_config = RAGConfig(
            enabled="always",
            chunk_size=100,
            chunk_overlap=20,
            embedding_model="mock",
        )

        with (
            patch(
                "songyan.workflows._helpers.CharacterRepository.list_by_project",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "songyan.db.continuity_repo.SettingTrackingRepository.list_by_project",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            await _index_accepted_chapter(
                project_id=project_id,
                chapter_number=1,
                version_id=version_id,
                content=content,
                rag_config=rag_config,
            )

        # 验证：新建 VectorStore 从 DB 加载后能检索
        store = VectorStore(project_id, ChunkRepository())
        await store.load()
        assert store.total_chunks > 0, "VectorStore 应加载到非零 chunks"

        embedder = Embedder("mock")
        query_emb = embedder.embed(["认知补丁"])[0]
        results = await store.search(query_emb, top_k=3, min_similarity=0.0)
        assert len(results) > 0, "检索应返回非空结果"
        assert results[0].chapter_number == 1

    async def test_index_persists_embedding_shape(self, test_db, proj_with_version) -> None:
        """写入的 embedding shape 与加载后一致."""
        project_id, version_id = proj_with_version
        content = "方远舟发现了秘密。空间站的真相令人震惊。"
        rag_config = RAGConfig(
            enabled="always",
            chunk_size=50,
            chunk_overlap=10,
            embedding_model="mock",
        )

        with (
            patch(
                "songyan.workflows._helpers.CharacterRepository.list_by_project",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "songyan.db.continuity_repo.SettingTrackingRepository.list_by_project",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            await _index_accepted_chapter(
                project_id=project_id,
                chapter_number=1,
                version_id=version_id,
                content=content,
                rag_config=rag_config,
            )

        store = VectorStore(project_id, ChunkRepository())
        await store.load()
        assert store._embeddings is not None
        assert store._embeddings.shape[0] == store.total_chunks
        assert store._embeddings.shape[1] == 768  # mock embedder dimension

    async def test_index_empty_content(self, test_db, proj_with_version) -> None:
        """空内容不应抛异常，也不写入数据."""
        project_id, version_id = proj_with_version
        rag_config = RAGConfig(enabled="always", embedding_model="mock")

        with (
            patch(
                "songyan.workflows._helpers.CharacterRepository.list_by_project",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "songyan.db.continuity_repo.SettingTrackingRepository.list_by_project",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            await _index_accepted_chapter(
                project_id=project_id,
                chapter_number=1,
                version_id=version_id,
                content="",
                rag_config=rag_config,
            )

        store = VectorStore(project_id, ChunkRepository())
        await store.load()
        assert store.total_chunks == 0


class TestRetrieverWithIndexedData:
    """RAGRetriever 在真实索引数据上的检索."""

    async def test_retrieve_for_chapter_after_index(self, test_db, proj_with_version) -> None:
        """索引后，retrieve_for_chapter 返回非空结果."""
        project_id, version_id = proj_with_version
        from songyan.models.chapter import ChapterGoal

        content = (
            "方远舟发现了认知补丁的秘密。空间站的系统正在崩溃。\n\n"
            "\"我们必须逃离这里，\"他对自己说。"
        )
        rag_config = RAGConfig(
            enabled="always",
            chunk_size=80,
            chunk_overlap=15,
            embedding_model="mock",
            max_results=5,
            min_similarity=0.0,
        )

        with (
            patch(
                "songyan.workflows._helpers.CharacterRepository.list_by_project",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "songyan.db.continuity_repo.SettingTrackingRepository.list_by_project",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            await _index_accepted_chapter(
                project_id=project_id,
                chapter_number=1,
                version_id=version_id,
                content=content,
                rag_config=rag_config,
            )

        embedder = Embedder("mock")
        store = VectorStore(project_id, ChunkRepository())
        retriever = RAGRetriever(
            embedder=embedder,
            vector_store=store,
            rag_config=rag_config,
        )

        goal = ChapterGoal(
            chapter_number=2,
            target_events=["认知补丁", "空间站"],
            obligations=[],
        )
        results = await retriever.retrieve_for_chapter(
            project_id=project_id,
            chapter_number=2,
            chapter_goal=goal,
            recent_plot=None,
        )
        assert len(results) > 0, "retrieve_for_chapter 应返回非空结果"
