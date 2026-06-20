"""RAG 向量索引 CLI 命令."""

from __future__ import annotations

import asyncio

import click

from songyan.db.chunk_repo import ChunkRepository
from songyan.db.migrations import init_schema
from songyan.db.repository import ChapterHeadRepository, ChapterVersionRepository
from songyan.rag.chunker import Chunker
from songyan.rag.embedder import Embedder


async def _index_chapters(
    project_id: str,
    chapter_numbers: list[int] | None = None,
    rebuild: bool = False,
) -> dict:
    """为指定章节建立 RAG 向量索引.

    Args:
        project_id: 项目 ID
        chapter_numbers: 指定章节号列表，None 表示全部
        rebuild: 是否重建（先清空）

    Returns:
        统计信息 dict
    """
    await init_schema()

    repo = ChunkRepository()
    version_repo = ChapterVersionRepository()
    head_repo = ChapterHeadRepository()

    if rebuild:
        await repo.delete_by_project(project_id)

    # 确定要索引的章节列表
    if chapter_numbers is None:
        heads = await head_repo.list_by_project(project_id)
        chapter_numbers = [h.chapter_number for h in heads if h.accepted_version_id]

    total_chunks = 0
    indexed_chapters = 0
    failed_chapters = []

    embedder = Embedder()

    for ch_num in sorted(chapter_numbers):
        # 获取 accepted version
        head = await head_repo.get(project_id, ch_num)
        if head is None or not head.accepted_version_id:
            continue

        version = await version_repo.get(head.accepted_version_id)
        if version is None or not version.content:
            continue

        try:
            # 切分
            chunker = Chunker()
            chunks = chunker.chunk_chapter(
                content=version.content,
                project_id=project_id,
                chapter_number=ch_num,
                version_id=version.version_id,
            )
            if not chunks:
                continue

            # 编码
            embeddings = await embedder.aembed([c.text for c in chunks])

            # 写入
            await repo.delete_by_chapter(project_id, ch_num)
            await repo.bulk_insert(chunks, embeddings)

            total_chunks += len(chunks)
            indexed_chapters += 1
        except (RuntimeError, OSError, ConnectionError, ValueError, TypeError) as exc:
            failed_chapters.append((ch_num, str(exc)))

    return {
        "indexed_chapters": indexed_chapters,
        "total_chunks": total_chunks,
        "failed_chapters": failed_chapters,
    }


def register_index_commands(cli: click.Group) -> None:
    """注册 index 子命令到 CLI."""

    @cli.command()
    @click.option("--project-id", required=True, help="项目 ID")
    @click.option("--chapters", default=None, help="章节范围，如 1-10 或 3,5,7")
    @click.option("--rebuild", is_flag=True, help="重建整个项目的向量索引")
    def index(project_id: str, chapters: str | None, rebuild: bool) -> None:
        """为已有章节建立 RAG 向量索引."""
        try:
            chapter_numbers: list[int] | None = None
            if chapters:
                # 解析范围或列表
                nums: list[int] = []
                for part in chapters.split(","):
                    part = part.strip()
                    if "-" in part:
                        start, end = part.split("-")
                        nums.extend(range(int(start), int(end) + 1))
                    else:
                        nums.append(int(part))
                chapter_numbers = nums

            result = asyncio.run(
                _index_chapters(
                    project_id=project_id,
                    chapter_numbers=chapter_numbers,
                    rebuild=rebuild,
                )
            )

            click.echo("\n✓ 索引完成")
            click.echo(f"  索引章节数: {result['indexed_chapters']}")
            click.echo(f"  总 chunks: {result['total_chunks']}")
            if result["failed_chapters"]:
                click.echo(f"  失败章节: {len(result['failed_chapters'])}")
                for ch_num, err in result["failed_chapters"]:
                    click.echo(f"    第 {ch_num} 章: {err}")

        except click.Abort:
            raise
        except (
            RuntimeError,
            OSError,
            ConnectionError,
            ValueError,
            TypeError,
            ImportError,
            KeyError,
            AttributeError,
        ) as exc:
            raise click.ClickException(str(exc)) from exc
