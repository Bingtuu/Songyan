"""文本切分模块 — 将章节正文切分为带重叠的语义 chunks."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


SCENE_MARKER_PATTERN = re.compile(r"^#{3,4}\s+Scene\s+\d+", re.IGNORECASE)
FRONTMATTER_PATTERN = re.compile(r"^---\s*\n.*?\n---\s*\n", re.DOTALL)
CHAPTER_TITLE_PATTERN = re.compile(r"^#\s+.*", re.MULTILINE)


@dataclass
class ChapterChunk:
    """章节文本切片."""

    chunk_id: str
    chapter_num: int
    chunk_index: int
    text: str
    is_chapter_boundary: bool = False


@dataclass
class ChunkerConfig:
    """切分配置."""

    chunk_size: int = 500
    chunk_overlap: int = 100


def _extract_body(content: str) -> str:
    """去掉 markdown frontmatter 和章节标题，保留正文."""
    # 去掉 frontmatter
    content = FRONTMATTER_PATTERN.sub("", content)
    # 去掉 # 第N章 标题行
    content = CHAPTER_TITLE_PATTERN.sub("", content)
    return content.strip()


def _split_by_scenes(content: str) -> list[str]:
    """按场景标记分割文本，无标记时退化为按空行分段落."""
    lines = content.splitlines()
    segments: list[str] = []
    current_segment: list[str] = []

    for line in lines:
        if SCENE_MARKER_PATTERN.match(line.strip()):
            if current_segment:
                segments.append("\n".join(current_segment).strip())
                current_segment = []
        current_segment.append(line)

    if current_segment:
        segments.append("\n".join(current_segment).strip())

    # 无场景标记时退化为按空行分段
    if len(segments) <= 1:
        return [p.strip() for p in content.split("\n\n") if p.strip()]
    return [s for s in segments if s]


def _find_sentence_boundary(text: str, target_pos: int) -> int:
    """在 target_pos 附近找句子边界（句号/问号/感叹号/换行），返回最佳切分位置."""
    if target_pos >= len(text):
        return len(text)

    # 先向后找
    for i in range(target_pos, min(len(text), target_pos + 50)):
        if text[i] in "。？！\n":
            return i + 1

    # 再向前找
    for i in range(target_pos, max(0, target_pos - 50), -1):
        if text[i] in "。？！\n":
            return i + 1

    # fallback：回退到空格
    for i in range(target_pos, max(0, target_pos - 30), -1):
        if text[i] == " ":
            return i

    return target_pos


class Chunker:
    """章节文本切分器."""

    def __init__(self, config: ChunkerConfig | None = None) -> None:
        self.config = config or ChunkerConfig()

    def chunk_chapter(
        self,
        content: str,
        chapter_num: int,
        project_id: str = "",
    ) -> list[ChapterChunk]:
        """将章节正文切分为带重叠的 chunks."""
        body = _extract_body(content)
        if not body:
            return []

        paragraphs = _split_by_scenes(body)
        chunks: list[ChapterChunk] = []
        current_text = ""
        current_index = 0

        def _flush(text: str) -> None:
            nonlocal current_index, current_text
            if not text.strip():
                return
            chunks.append(
                ChapterChunk(
                    chunk_id=f"{project_id}_{chapter_num}_{current_index}",
                    chapter_num=chapter_num,
                    chunk_index=current_index,
                    text=text.strip(),
                    is_chapter_boundary=False,
                )
            )
            current_index += 1
            # 保留 overlap 作为下一块的开头
            overlap_start = max(0, len(text) - self.config.chunk_overlap)
            current_text = text[overlap_start:]

        for para in paragraphs:
            # 如果当前非空且加上这一段会超 chunk_size，先落盘
            if (
                current_text
                and len(current_text) + len(para) > self.config.chunk_size
                and len(current_text) >= self.config.chunk_size * 0.5
            ):
                _flush(current_text)

            # 如果段落本身超过 chunk_size，需要强制切分
            if len(para) > self.config.chunk_size:
                # 先落盘当前 buffer
                if current_text.strip():
                    _flush(current_text)

                start = 0
                while start < len(para):
                    end = min(start + self.config.chunk_size, len(para))
                    # 找句子边界
                    if end < len(para):
                        end = _find_sentence_boundary(para, end)
                    piece = para[start:end]
                    _flush(piece)
                    start = end - self.config.chunk_overlap if end < len(para) else end
                continue

            current_text += "\n" + para if current_text else para

        # 落盘最后一个 chunk
        if current_text.strip():
            _flush(current_text)

        return chunks

    def chunk_project_chapters(
        self,
        chapters_dir: str | Path,
        project_id: str = "",
    ) -> list[ChapterChunk]:
        """从项目章节目录加载所有章节并切分."""
        chapters_path = Path(chapters_dir)
        all_chunks: list[ChapterChunk] = []

        for chapter_file in sorted(chapters_path.glob("chapter_*.md")):
            # 从文件名提取章节号
            match = re.search(r"chapter_(\d+)", chapter_file.name)
            if not match:
                continue
            chapter_num = int(match.group(1))

            content = chapter_file.read_text(encoding="utf-8")
            chunks = self.chunk_chapter(content, chapter_num, project_id)
            all_chunks.extend(chunks)

        return all_chunks
