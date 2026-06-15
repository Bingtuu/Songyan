"""Settlement → RAG indexing 集成测试."""

from __future__ import annotations

import pytest

from songyan.db.chunk_repo import ChunkRepository
from songyan.db.repository import ChapterVersionRepository, ProjectRepository
from songyan.models import ChapterVersion, ProjectSetting
from songyan.models.rag import RAGConfig
from songyan.rag.embedder import Embedder
from songyan.workflows._helpers import _index_accepted_chapter

pytestmark = pytest.mark.asyncio


class TestSettlementIndexing:
    """Settlement 后 RAG 索引测试."""

    @pytest.fixture(autouse=True)
    def clear_embedder_cache(self) -> None:
        """清理 embedder 缓存."""
        Embedder.clear_cache()

    async def test_index_accepted_chapter(self, test_db) -> None:
        """Mock Embedder，验证 indexing 后 chunk 入库."""
        # 创建项目
        project = ProjectSetting(
            title="Test",
            genre_id="xuanhuan",
            mode_id="webnovel",
            protagonist_name="Alice",
        )
        project_id = "test_proj_1"
        await ProjectRepository().create(project, project_id)

        # 创建章节版本
        version = ChapterVersion(
            version_id="v1",
            project_id=project_id,
            chapter_number=1,
            version_number=1,
            version_type="accepted",
            content="方远舟看着林语嫣。这是第一章的内容。",
        )
        await ChapterVersionRepository().create(version)

        rag_config = RAGConfig(
            enabled="always",
            embedding_model="mock",
            chunk_size=500,
            chunk_overlap=100,
        )

        await _index_accepted_chapter(
            project_id=project_id,
            chapter_number=1,
            version_id=version.version_id,
            content=version.content,
            rag_config=rag_config,
        )

        # 验证入库
        repo = ChunkRepository()
        chunks, embeddings = await repo.get_with_embeddings(project_id)
        assert len(chunks) >= 1
        assert embeddings is not None
        assert embeddings.shape[1] == 768
        assert chunks[0].version_id == "v1"

    async def test_index_never_skips(self, test_db) -> None:
        """enabled=never 时跳过索引."""
        rag_config = RAGConfig(enabled="never")

        await _index_accepted_chapter(
            project_id="proj1",
            chapter_number=1,
            version_id="v1",
            content="some content",
            rag_config=rag_config,
        )

        repo = ChunkRepository()
        chunks, _ = await repo.get_with_embeddings("proj1")
        assert chunks == []
