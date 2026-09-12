"""V15 Task 235: 章节切分与人工确认（segment 阶段）.

只读源文件，产出可 diff 的章节边界清单；人工确认后才允许回放。
设计冻结见 docs/reports/234-v15-import-pipeline-audit.md。
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from songyan.exceptions import ImportSegmentError, ImportSourceError
from songyan.models.import_manifest import (
    ChapterBoundary,
    SegmentManifest,
    manifest_to_json,
)
from songyan.utils.token_estimator import TokenEstimator
from songyan.utils.word_count import count_chinese_words

#: 解码尝试顺序：utf-8-sig 覆盖 BOM 与普通 utf-8；gb18030 是 GBK 超集（标准库自带）。
_DECODE_ORDER = ("utf-8-sig", "gb18030")

#: 章节标题行：口径合并自 agents/writer.py 与 services/text_cleanliness_cleaner.py。
#: 行首额外容忍全角空格（U+3000），覆盖中文网文/出版文本的全角缩进标题行。
_CHAPTER_HEADER_RE = re.compile(
    r"^[ \t　]*#{0,6}[ \t]*"
    r"(?:第[ \t]*[一二三四五六七八九十百千万零〇两\d]+[ \t]*(?:章|章节|回)"
    r"|Chapter[ \t]+\d+)"
    r"[^\n]*$",
    re.MULTILINE | re.IGNORECASE,
)


def decode_source(data: bytes) -> tuple[str, str]:
    """按固定顺序解码源文件字节；全部失败时显式报错，不猜测.

    已知盲区：gb18030 几乎能对任意字节序列解码"成功"，因此无 BOM 的
    UTF-16 源文件会被静默解码成乱码而非抛错。双编码顺序是冻结设计，
    不在此处猜测或嗅探编码；用户需按报错提示自行转存 UTF-8。
    """
    for encoding in _DECODE_ORDER:
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    msg = (
        "源文件编码无法识别（已尝试 utf-8-sig / gb18030）。"
        "请先用文本编辑器将源文件另存为 UTF-8 后重试。"
    )
    raise ImportSourceError(msg)


def normalize_line_endings(text: str) -> tuple[str, bool]:
    """CRLF/CR 归一化为 LF；返回 (文本, 是否发生过归一)."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return normalized, normalized != text


def detect_boundaries(
    text: str,
    *,
    token_budget: int,
    estimator: TokenEstimator | None = None,
) -> tuple[list[ChapterBoundary], str, list[str]]:
    """规则切分章节；返回 (边界列表, 前言文本, 逐章正文列表).

    偏移基于传入文本（调用方需先 normalize_line_endings）。
    正文为标题行之后到下一章标题前的内容，标题行剥离（与 Writer 入库口径一致）。
    识别不到任何章节标题时显式报错，不自动硬切。
    已知盲区：以「第N章…」开头的正文引用行会被识别为标题（规则切分固有盲区，
    由人工确认闸门兜底）。
    """
    estimator = estimator or TokenEstimator()
    matches = list(_CHAPTER_HEADER_RE.finditer(text))
    if not matches:
        msg = (
            "未识别到任何章节标题（支持 第N章/第N章节/第N回/Chapter N，可带 # 前缀）。"
            "请先人工为源文件补充章节标题，或拆分文件后重试。"
        )
        raise ImportSegmentError(msg)

    prologue = text[: matches[0].start()].strip()
    boundaries: list[ChapterBoundary] = []
    bodies: list[str] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        title = match.group(0).strip().lstrip("#").strip()
        body = text[match.end() : end].strip()
        est_tokens = estimator.estimate(body)
        boundaries.append(
            ChapterBoundary(
                chapter_number=index + 1,
                title=title,
                start_offset=start,
                end_offset=end,
                char_count=len(body),
                word_count=count_chinese_words(body),
                est_tokens=est_tokens,
                over_token_budget=est_tokens > token_budget,
                body_sha256=hashlib.sha256(body.encode("utf-8")).hexdigest(),
            )
        )
        bodies.append(body)
    return boundaries, prologue, bodies


def build_manifest(
    source_path: Path,
    *,
    token_budget: int,
    now: datetime | None = None,
) -> tuple[SegmentManifest, str, list[str]]:
    """读取源文件并构建切分清单；返回 (清单, 规范化文本, 逐章正文).

    只读源文件，不修改。``now`` 可注入以保证产物可复现（默认当前 UTC 时间）。
    """
    raw = source_path.read_bytes()
    text, encoding = decode_source(raw)
    normalized, endings_changed = normalize_line_endings(text)
    boundaries, prologue, bodies = detect_boundaries(normalized, token_budget=token_budget)
    manifest = SegmentManifest(
        source_path=str(source_path),
        source_sha256=hashlib.sha256(raw).hexdigest(),
        normalized_sha256=hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
        encoding=encoding,
        line_endings_normalized=endings_changed,
        token_budget=token_budget,
        chapter_count=len(boundaries),
        has_prologue=bool(prologue),
        prologue_chars=len(prologue),
        boundaries=boundaries,
        status="pending_confirmation",
        created_at=now or datetime.now(UTC),
    )
    return manifest, normalized, bodies


def write_segment_artifacts(
    output_dir: Path,
    manifest: SegmentManifest,
    normalized_text: str,
    bodies: list[str],
) -> Path:
    """落盘切分产物；返回 manifest 路径."""
    output_dir.mkdir(parents=True, exist_ok=True)
    chapters_dir = output_dir / "chapters"
    chapters_dir.mkdir(exist_ok=True)
    (output_dir / "source.normalized.txt").write_text(normalized_text, encoding="utf-8")
    for boundary, body in zip(manifest.boundaries, bodies, strict=True):
        chapter_file = chapters_dir / f"ch{boundary.chapter_number:03d}.md"
        chapter_file.write_text(body + "\n", encoding="utf-8")
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(manifest_to_json(manifest), encoding="utf-8")
    return manifest_path


def load_manifest(manifest_path: Path) -> SegmentManifest:
    """加载并校验清单；文件损坏时显式报错."""
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        return SegmentManifest.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        msg = f"切分清单无法读取或校验失败: {manifest_path}（{exc}）"
        raise ImportSegmentError(msg) from exc
