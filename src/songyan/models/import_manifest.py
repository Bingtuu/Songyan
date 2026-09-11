"""V15 Task 235: 导入章节切分清单模型.

清单是 segment 阶段的可审查产物：逐章边界 + 统计 + 源文件指纹，
人工确认（status -> confirmed）后才允许进入 replay 阶段。
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "1.0"


class ChapterBoundary(BaseModel):
    """单章边界：偏移基于规范化后文本（LF 行尾），end 为开区间."""

    model_config = ConfigDict(extra="forbid")

    chapter_number: int = Field(ge=1)
    title: str
    start_offset: int = Field(ge=0)
    end_offset: int = Field(ge=0)
    char_count: int = Field(ge=0)
    word_count: int = Field(ge=0)
    est_tokens: int = Field(ge=0)
    over_token_budget: bool
    body_sha256: str


class SegmentManifest(BaseModel):
    """切分清单：指纹绑定源文件，人工确认闸门状态."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = SCHEMA_VERSION
    source_path: str
    source_sha256: str
    normalized_sha256: str
    encoding: str
    line_endings_normalized: bool
    token_budget: int = Field(gt=0)
    chapter_count: int = Field(ge=1)
    has_prologue: bool
    prologue_chars: int = Field(ge=0)
    boundaries: list[ChapterBoundary]
    status: Literal["pending_confirmation", "confirmed"]
    created_at: datetime
    confirmed_at: datetime | None = None

    @model_validator(mode="after")
    def validate_boundaries(self) -> SegmentManifest:
        """章节号连续递增、偏移单调不重叠、chapter_count 与列表一致."""
        if self.chapter_count != len(self.boundaries):
            msg = "chapter_count must equal len(boundaries)"
            raise ValueError(msg)
        for index, boundary in enumerate(self.boundaries, start=1):
            if boundary.chapter_number != index:
                msg = (
                    "chapter_number must be sequential: "
                    f"expected {index}, got {boundary.chapter_number}"
                )
                raise ValueError(msg)
            if boundary.end_offset <= boundary.start_offset:
                msg = f"chapter {index}: end_offset must be > start_offset"
                raise ValueError(msg)
            if index > 1 and boundary.start_offset < self.boundaries[index - 2].end_offset:
                msg = f"chapter {index}: start_offset overlaps previous chapter"
                raise ValueError(msg)
        return self


def manifest_to_json(manifest: SegmentManifest) -> str:
    """序列化为可 diff 的稳定 JSON（排序键 + 固定缩进 + 末尾换行）."""
    payload = manifest.model_dump(mode="json")
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
