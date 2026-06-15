"""Shared helpers for quality detection utils."""

from __future__ import annotations

import re


def split_paragraphs(text: str) -> list[str]:
    """Split text into paragraphs by blank lines."""
    paragraphs: list[str] = []
    for block in text.split("\n"):
        stripped = block.strip()
        if stripped:
            paragraphs.append(stripped)
    return paragraphs


def split_sentences(text: str) -> list[str]:
    """Split Chinese text into sentences by punctuation.

    Preserves punctuation at the end of each sentence.
    """
    # Split on Chinese sentence-ending punctuation
    raw = re.split(r"([。！？…]+)", text)
    sentences: list[str] = []
    i = 0
    while i < len(raw):
        part = raw[i]
        if i + 1 < len(raw) and re.match(r"[。！？…]+$", raw[i + 1]):
            sentences.append(part + raw[i + 1])
            i += 2
        else:
            if part.strip():
                sentences.append(part)
            i += 1
    return sentences


def locate_position(text: str, match_start: int) -> str:
    """Return human-readable location like '第3段第2句'.

    Args:
        text: Full text.
        match_start: Character index where the match begins.

    Returns:
        Location string in Chinese.
    """
    paragraphs = split_paragraphs(text)
    cursor = 0
    for p_idx, para in enumerate(paragraphs):
        p_start = text.find(para, cursor)
        if p_start == -1:
            continue
        p_end = p_start + len(para)
        if p_start <= match_start < p_end:
            sentences = split_sentences(para)
            s_cursor = p_start
            for s_idx, sent in enumerate(sentences):
                s_start = text.find(sent, s_cursor)
                if s_start == -1:
                    continue
                s_end = s_start + len(sent)
                if s_start <= match_start < s_end:
                    return f"第{p_idx + 1}段第{s_idx + 1}句"
                s_cursor = s_end
            return f"第{p_idx + 1}段"
        cursor = p_end
    return "未知位置"
