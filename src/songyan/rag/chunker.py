"""章节文本切分器 — 场景感知、句子边界保护、重叠缓冲."""

from __future__ import annotations

import re
from typing import Literal

from songyan.models.rag import ChunkMetadata, TextChunk

SCENE_MARKER_PATTERN = re.compile(r"^#{3,4}\s+Scene\s+\d+", re.IGNORECASE)
FRONTMATTER_PATTERN = re.compile(r"^---\s*\n.*?\n---\s*\n", re.DOTALL)
CHAPTER_TITLE_PATTERN = re.compile(r"^#\s+.*", re.MULTILINE)
DIALOGUE_PATTERN = re.compile(r"^[\s]*[\"\"" '"' '].*["""' "']")
# 常见中文对话标记
DIALOGUE_MARKERS = re.compile(
    r"^[\s]*[（(]?[\"" '"' ']|[「『【〔〈《〝（]|[）)]?[""' "'']$|[」』】〕〉》〞）]$"
)


def _extract_body(content: str) -> str:
    """去掉 markdown frontmatter 和章节标题，保留正文."""
    content = FRONTMATTER_PATTERN.sub("", content)
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

    if len(segments) <= 1:
        return [p.strip() for p in content.split("\n\n") if p.strip()]
    return [s for s in segments if s]


def _find_sentence_boundary(text: str, target_pos: int) -> int:
    """在 target_pos 附近找句子边界，返回最佳切分位置."""
    if target_pos >= len(text):
        return len(text)

    for i in range(target_pos, min(len(text), target_pos + 50)):
        if text[i] in "。？！\n":
            return i + 1

    for i in range(target_pos, max(0, target_pos - 50), -1):
        if text[i] in "。？！\n":
            return i + 1

    for i in range(target_pos, max(0, target_pos - 30), -1):
        if text[i] == " ":
            return i

    return target_pos


def _classify_chunk(text: str) -> Literal["narrative", "dialogue", "description", "action"]:
    """基于文本特征简单分类 chunk 类型."""
    lines = text.splitlines()
    if not lines:
        return "narrative"

    dialogue_lines = 0
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(('"', '"""', "'", "''", "「", "『", "【", "（")):
            dialogue_lines += 1
        elif stripped.startswith("（") and stripped.endswith("）"):
            dialogue_lines += 1
        elif '"' in stripped and stripped.count('"') >= 2:
            dialogue_lines += 1

    if dialogue_lines > len(lines) * 0.5:
        return "dialogue"

    # 简化：其余归为 narrative（后续可扩展 description/action 检测）
    return "narrative"


def _extract_mentions(text: str, known_items: list[str] | None) -> list[str]:
    """从文本中提取已知项的提及."""
    if not known_items:
        return []
    return [item for item in known_items if item in text]


class Chunker:
    """章节文本切分器 — 生产版本."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 100) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_chapter(
        self,
        content: str,
        project_id: str,
        chapter_number: int,
        version_id: str,
        known_characters: list[str] | None = None,
        known_settings: list[str] | None = None,
    ) -> list[TextChunk]:
        """将章节正文切分为带重叠的 chunks.

        Args:
            content: 章节原始 markdown 内容
            project_id: 项目 ID
            chapter_number: 章节号
            version_id: 版本 ID
            known_characters: 已知角色名列表（用于 metadata 提取）
            known_settings: 已知设定 key 列表（用于 metadata 提取）

        Returns:
            TextChunk 列表
        """
        body = _extract_body(content)
        if not body:
            return []

        paragraphs = _split_by_scenes(body)
        chunks: list[TextChunk] = []
        current_text = ""
        current_index = 0
        start_char = 0

        def _flush(text: str, s_char: int) -> int:
            nonlocal current_index, current_text, start_char
            if not text.strip():
                return s_char
            chunk_type = _classify_chunk(text)
            meta = ChunkMetadata(
                characters_mentioned=_extract_mentions(text, known_characters),
                setting_keys_mentioned=_extract_mentions(text, known_settings),
                chunk_type=chunk_type,
                start_char=s_char,
                end_char=s_char + len(text),
            )
            chunks.append(
                TextChunk(
                    chunk_id=f"{project_id}_{chapter_number}_{current_index}",
                    project_id=project_id,
                    chapter_number=chapter_number,
                    version_id=version_id,
                    chunk_index=current_index,
                    text=text.strip(),
                    metadata=meta,
                )
            )
            current_index += 1
            overlap_start = max(0, len(text) - self.chunk_overlap)
            current_text = text[overlap_start:]
            start_char = s_char + len(text) - len(current_text)
            return start_char

        for para in paragraphs:
            if (
                current_text
                and len(current_text) + len(para) > self.chunk_size
                and len(current_text) >= self.chunk_size * 0.5
            ):
                start_char = _flush(current_text, start_char)

            if len(para) > self.chunk_size:
                if current_text.strip():
                    start_char = _flush(current_text, start_char)

                p_start = 0
                while p_start < len(para):
                    end = min(p_start + self.chunk_size, len(para))
                    if end < len(para):
                        end = _find_sentence_boundary(para, end)
                    piece = para[p_start:end]
                    start_char = _flush(piece, start_char)
                    p_start = end - self.chunk_overlap if end < len(para) else end
                continue

            current_text += "\n" + para if current_text else para

        if current_text.strip():
            _flush(current_text, start_char)

        return chunks
