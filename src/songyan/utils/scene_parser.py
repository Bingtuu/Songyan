"""场景解析工具 — 按 ### Scene N 标记分割场景."""

from __future__ import annotations

import re

SCENE_PATTERN = re.compile(
    r"^###\s*Scene\s+(\d+)\s*[:：]?", re.IGNORECASE | re.MULTILINE
)


def parse_scenes(content: str) -> list[dict]:
    """按 ### Scene N 标记分割场景.

    Returns:
        [{"scene_number": int, "content": str}, ...]
    """
    if not content.strip():
        return []

    matches = list(SCENE_PATTERN.finditer(content))
    if not matches:
        # 无场景标记，整章作为一个场景
        return [{"scene_number": 1, "content": content.strip()}]

    scenes: list[dict] = []
    for i, match in enumerate(matches):
        scene_number = int(match.group(1))
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        scene_content = content[start:end].strip()
        scenes.append({"scene_number": scene_number, "content": scene_content})
    return scenes
