"""Chapter chunk repository — RAG 向量切片存储."""

from __future__ import annotations

from sqlite3 import Row
from typing import TYPE_CHECKING

import numpy as np
import structlog

from songyan.db.connection import get_db
from songyan.models.rag import ChunkMetadata, TextChunk
from songyan.utils.json_helpers import from_json as _from_json
from songyan.utils.json_helpers import to_json as _to_json

if TYPE_CHECKING:
    import aiosqlite

logger = structlog.get_logger(__name__)


class ChunkRepository:
    """章节 chunk 向量存储 Repository."""

    async def bulk_insert(
        self,
        chunks: list[TextChunk],
        embeddings: np.ndarray,
        conn: aiosqlite.Connection | None = None,
    ) -> None:
        """批量写入 chunks 和对应向量.

        Args:
            chunks: TextChunk 列表
            embeddings: (N, D) float32 numpy 数组
            conn: 可选外部连接（用于事务）
        """
        if len(chunks) != embeddings.shape[0]:
            raise ValueError(
                f"chunks ({len(chunks)}) != embeddings ({embeddings.shape[0]})"
            )

        async def _do(c: aiosqlite.Connection) -> None:
            rows = []
            for chunk, emb in zip(chunks, embeddings):
                rows.append(
                    (
                        chunk.chunk_id,
                        chunk.project_id,
                        chunk.chapter_number,
                        chunk.version_id,
                        chunk.chunk_index,
                        chunk.text,
                        _to_json(chunk.metadata.model_dump(mode="json")),
                        emb.tobytes(),
                    )
                )
            await c.executemany(
                """INSERT INTO chapter_chunks (
                    chunk_id, project_id, chapter_number, version_id,
                    chunk_index, text, metadata_json, embedding_blob
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                rows,
            )

        if conn is None:
            async with get_db() as c:
                await _do(c)
                await c.commit()
        else:
            await _do(conn)
        logger.info(
            "repository.write",
            table="chapter_chunks",
            operation="bulk_insert",
            count=len(chunks),
        )

    async def get_by_project(self, project_id: str) -> list[TextChunk]:
        """加载项目全部 chunks（不含向量，用于元数据加载）."""
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                """SELECT chunk_id, project_id, chapter_number, version_id,
                          chunk_index, text, metadata_json
                   FROM chapter_chunks
                   WHERE project_id = ?
                   ORDER BY chapter_number, chunk_index""",
                (project_id,),
            )
            rows = await cursor.fetchall()

        return [_row_to_chunk(row) for row in rows]

    async def get_with_embeddings(
        self, project_id: str
    ) -> tuple[list[TextChunk], np.ndarray | None]:
        """加载项目全部 chunks 及向量.

        Returns:
            (chunks 列表, (N, D) embeddings 数组 or None)
        """
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                """SELECT chunk_id, project_id, chapter_number, version_id,
                          chunk_index, text, metadata_json, embedding_blob
                   FROM chapter_chunks
                   WHERE project_id = ?
                   ORDER BY chapter_number, chunk_index""",
                (project_id,),
            )
            rows = await cursor.fetchall()

        if not rows:
            return [], None

        chunks = []
        embeddings = []
        for row in rows:
            chunks.append(_row_to_chunk(row))
            blob = row["embedding_blob"]
            if blob:
                embeddings.append(np.frombuffer(blob, dtype=np.float32))

        if embeddings:
            emb_array = np.vstack(embeddings)
            return chunks, emb_array
        return chunks, None

    async def delete_by_chapter(
        self,
        project_id: str,
        chapter_number: int,
        conn: aiosqlite.Connection | None = None,
    ) -> None:
        """删除指定章节的 chunks."""
        async def _do(c: aiosqlite.Connection) -> None:
            await c.execute(
                "DELETE FROM chapter_chunks WHERE project_id = ? AND chapter_number = ?",
                (project_id, chapter_number),
            )

        if conn is None:
            async with get_db() as c:
                await _do(c)
                await c.commit()
        else:
            await _do(conn)
        logger.info(
            "repository.delete",
            table="chapter_chunks",
            operation="delete_by_chapter",
            project_id=project_id,
            chapter_number=chapter_number,
        )

    async def delete_by_project(
        self,
        project_id: str,
        conn: aiosqlite.Connection | None = None,
    ) -> None:
        """删除整个项目的 chunks（rebuild 用）."""
        async def _do(c: aiosqlite.Connection) -> None:
            await c.execute(
                "DELETE FROM chapter_chunks WHERE project_id = ?",
                (project_id,),
            )

        if conn is None:
            async with get_db() as c:
                await _do(c)
                await c.commit()
        else:
            await _do(conn)
        logger.info(
            "repository.delete",
            table="chapter_chunks",
            operation="delete_by_project",
            project_id=project_id,
        )


def _row_to_chunk(row: Row) -> TextChunk:
    """从 DB Row 构造 TextChunk."""
    meta_raw = row["metadata_json"]
    meta = ChunkMetadata.model_validate(_from_json(meta_raw, {})) if meta_raw else ChunkMetadata()
    return TextChunk(
        chunk_id=row["chunk_id"],
        project_id=row["project_id"],
        chapter_number=row["chapter_number"],
        version_id=row["version_id"],
        chunk_index=row["chunk_index"],
        text=row["text"],
        metadata=meta,
    )
