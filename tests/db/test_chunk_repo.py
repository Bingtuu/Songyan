"""ChunkRepository 测试."""

from __future__ import annotations

import numpy as np
import pytest

from songyan.db.chunk_repo import ChunkRepository
from songyan.db.repository import ChapterVersionRepository, ProjectRepository
from songyan.models import ChapterVersion, ProjectSetting
from songyan.models.rag import ChunkMetadata, TextChunk

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def seeded_db(test_db) -> None:
    """创建项目和章节版本，满足外键约束."""
    project = ProjectSetting(
        title="Test",
        genre_id="xuanhuan",
        mode_id="webnovel",
        protagonist_name="Alice",
    )
    await ProjectRepository().create(project, "proj1")
    version = ChapterVersion(
        version_id="v1",
        project_id="proj1",
        chapter_number=1,
        version_number=1,
        version_type="accepted",
        content="test content",
    )
    await ChapterVersionRepository().create(version)


def _make_chunk(
    project_id: str = "proj1",
    chapter_number: int = 1,
    chunk_index: int = 0,
) -> TextChunk:
    return TextChunk(
        chunk_id=f"{project_id}_{chapter_number}_{chunk_index}",
        project_id=project_id,
        chapter_number=chapter_number,
        version_id=f"v{chapter_number}",
        chunk_index=chunk_index,
        text=f"test chunk {chunk_index}",
        metadata=ChunkMetadata(
            characters_mentioned=["Alice"],
            chunk_type="narrative",
        ),
    )


class TestChunkRepository:
    """ChunkRepository CRUD 测试."""

    async def test_chunk_repo_bulk_insert(self, test_db, seeded_db) -> None:
        """批量写入后读取验证."""
        repo = ChunkRepository()
        chunks = [
            _make_chunk(chunk_index=0),
            _make_chunk(chunk_index=1),
        ]
        embeddings = np.random.random((2, 768)).astype(np.float32)

        await repo.bulk_insert(chunks, embeddings)

        loaded = await repo.get_by_project("proj1")
        assert len(loaded) == 2
        assert loaded[0].chunk_id == "proj1_1_0"
        assert loaded[1].chunk_id == "proj1_1_1"
        assert loaded[0].metadata.characters_mentioned == ["Alice"]

        # 验证带 embeddings 的加载
        loaded2, embs = await repo.get_with_embeddings("proj1")
        assert len(loaded2) == 2
        assert embs is not None
        assert embs.shape == (2, 768)
        np.testing.assert_array_equal(embs, embeddings)

    async def test_chunk_repo_delete_by_chapter(self, test_db, seeded_db) -> None:
        """删除后该章节 chunks 为空."""
        # 为第 2 章创建版本
        v2 = ChapterVersion(
            version_id="v2",
            project_id="proj1",
            chapter_number=2,
            version_number=1,
            version_type="accepted",
            content="ch2",
        )
        await ChapterVersionRepository().create(v2)

        repo = ChunkRepository()
        chunks_ch1 = [_make_chunk(chapter_number=1, chunk_index=i) for i in range(2)]
        chunks_ch2 = [_make_chunk(chapter_number=2, chunk_index=i) for i in range(2)]
        emb1 = np.random.random((2, 768)).astype(np.float32)
        emb2 = np.random.random((2, 768)).astype(np.float32)

        await repo.bulk_insert(chunks_ch1, emb1)
        await repo.bulk_insert(chunks_ch2, emb2)

        # 删除第 1 章
        await repo.delete_by_chapter("proj1", 1)

        loaded, _ = await repo.get_with_embeddings("proj1")
        assert len(loaded) == 2
        assert all(c.chapter_number == 2 for c in loaded)

    async def test_chunk_repo_delete_by_project(self, test_db, seeded_db) -> None:
        """删除整个项目."""
        repo = ChunkRepository()
        chunks = [_make_chunk(chunk_index=i) for i in range(2)]
        emb = np.random.random((2, 768)).astype(np.float32)

        await repo.bulk_insert(chunks, emb)
        await repo.delete_by_project("proj1")

        loaded, _ = await repo.get_with_embeddings("proj1")
        assert loaded == []
