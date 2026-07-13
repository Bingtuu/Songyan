"""场景解析工具 — 按 ### Scene N 标记或空行分割场景."""

from __future__ import annotations

import re
from typing import Any

SCENE_PATTERN = re.compile(
    r"^###\s*Scene\s+(\d+)\s*[:：:]?", re.IGNORECASE | re.MULTILINE
)

# 空行分块时，小于该长度的块视为过渡/环境描写的碎块，合并到相邻场景
_MIN_SCENE_BLOCK_CHARS = 80

# Writer 1.2.0+ 强制多场景结构时的默认目标/上限
_DEFAULT_TARGET_SCENE_CHARS = 1800
_DEFAULT_MAX_SCENE_CHARS = 2400


def _merge_short_blocks(blocks: list[str]) -> list[str]:
    """合并过短的空行块到相邻场景，避免把零散段落计为独立场景.

    策略：
    - 长块（>=_MIN_SCENE_BLOCK_CHARS）开启新场景；
    - 短块（<_MIN_SCENE_BLOCK_CHARS）追加到当前场景；
    - 若开头就是短块，则暂存，直到遇到第一个长块时合并到其头部；
    - 若全文都是短块，则整体作为一个场景。
    """
    scenes: list[str] = []
    pending = ""
    for block in blocks:
        if len(block) >= _MIN_SCENE_BLOCK_CHARS:
            if pending:
                block = pending + "\n\n" + block
                pending = ""
            scenes.append(block)
        else:
            if not scenes:
                pending = block if not pending else pending + "\n\n" + block
            else:
                scenes[-1] = scenes[-1] + "\n\n" + block
    if pending and not scenes:
        scenes.append(pending)
    elif pending and scenes:
        scenes[-1] = scenes[-1] + "\n\n" + pending
    return scenes


def _group_blocks_balanced(
    blocks: list[str],
    min_scene_chars: int,
    max_scene_chars: int,
    target_scene_chars: int,
) -> list[str]:
    """将段落块均衡地组合成 2-4 个场景，满足最小/最大长度约束.

    用于 Writer 1.2.0+ 强制多场景结构：当 LLM 未用空行明确分隔场景时，
    按段落边界把正文切分为长度均衡的 2-4 个场景，避免整章被判定为单场景。
    """
    if not blocks:
        return []

    total = sum(len(b) for b in blocks)
    if total < min_scene_chars * 2:
        return ["\n\n".join(blocks)]

    desired = max(2, min(4, round(total / target_scene_chars)))
    max_by_min = total // min_scene_chars
    desired = min(desired, max_by_min)

    if desired <= 1:
        return ["\n\n".join(blocks)]

    targets = [total * k / desired for k in range(1, desired)]
    boundaries: list[int] = []
    cumulative = 0
    target_idx = 0

    for i, block in enumerate(blocks[:-1]):
        cumulative += len(block)
        if target_idx >= len(targets):
            break
        target = targets[target_idx]
        # 选择越过目标最近的块边界
        current_diff = abs(cumulative - target)
        next_diff = abs(cumulative + len(blocks[i + 1]) - target)
        if next_diff < current_diff:
            continue
        boundaries.append(i + 1)
        target_idx += 1

    if not boundaries:
        return ["\n\n".join(blocks)]

    scenes: list[str] = []
    start = 0
    for end in boundaries + [len(blocks)]:
        scenes.append("\n\n".join(blocks[start:end]))
        start = end

    # 若某个场景超过上限且还能再分，按最大长度追加一次后处理（简单折半）
    refined: list[str] = []
    for scene in scenes:
        if len(scene) > max_scene_chars:
            sub_blocks = [b.strip() for b in re.split(r"\n\s*\n", scene) if b.strip()]
            if len(sub_blocks) >= 2:
                half = len(scene) / 2
                acc = 0
                split_at = 0
                best_diff = half
                for i, b in enumerate(sub_blocks[:-1]):
                    acc += len(b)
                    diff = abs(acc - half)
                    if diff < best_diff:
                        best_diff = diff
                        split_at = i + 1
                refined.append("\n\n".join(sub_blocks[:split_at]))
                refined.append("\n\n".join(sub_blocks[split_at:]))
                continue
        refined.append(scene)
    return refined


def parse_scenes(
    content: str,
    min_scene_chars: int | None = None,
    max_scene_chars: int | None = None,
    target_scene_chars: int | None = None,
) -> list[dict[str, Any]]:
    """按 ### Scene N 标记或空行分割场景.

    优先识别 `### Scene N` 标记；若无标记：
    - 默认模式：按空行（\n\n+）分块，合并长度小于 80 字符的过渡碎块。
    - 严格模式（传入 min_scene_chars 等参数）：按段落边界均衡分组，
      确保每个场景满足最小长度，全章自然形成 2-4 个场景。

    Args:
        content: 章节正文。
        min_scene_chars: 严格模式下每个场景的最小字符数。
        max_scene_chars: 严格模式下每个场景的最大字符数。
        target_scene_chars: 严格模式下每个场景的目标字符数。

    Returns:
        [{"scene_number": int, "content": str}, ...]
    """
    if not content.strip():
        return []

    strict = min_scene_chars is not None
    if strict:
        min_chars: int = max(min_scene_chars or 1, 1)
        max_chars: int = max_scene_chars if max_scene_chars is not None else _DEFAULT_MAX_SCENE_CHARS
        if target_scene_chars is not None:
            target_chars: int = target_scene_chars
        else:
            target_chars = _DEFAULT_TARGET_SCENE_CHARS
    else:
        min_chars = _MIN_SCENE_BLOCK_CHARS
        max_chars = _DEFAULT_MAX_SCENE_CHARS
        target_chars = _DEFAULT_TARGET_SCENE_CHARS

    # 1. 优先使用显式场景标记
    matches = list(SCENE_PATTERN.finditer(content))
    if matches:
        scenes: list[dict[str, Any]] = []
        for i, match in enumerate(matches):
            scene_number = int(match.group(1))
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            scene_content = content[start:end].strip()
            scenes.append({"scene_number": scene_number, "content": scene_content})
        return scenes

    # 2. 无显式标记时按空行分块
    normalized = content.replace("\r\n", "\n")
    blocks = [block.strip() for block in re.split(r"\n\s*\n", normalized) if block.strip()]

    if not strict:
        merged = _merge_short_blocks(blocks)
        return [
            {"scene_number": idx + 1, "content": scene_content}
            for idx, scene_content in enumerate(merged)
        ]

    # 严格模式：均衡分组，避免整章被判定为单场景
    grouped = _group_blocks_balanced(blocks, min_chars, max_chars, target_chars)
    return [
        {"scene_number": idx + 1, "content": scene_content}
        for idx, scene_content in enumerate(grouped)
    ]
