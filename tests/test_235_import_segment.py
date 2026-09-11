"""Task 235: V15 章节切分与人工确认 — 服务层单测."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from songyan.exceptions import ImportSourceError
from songyan.models.import_manifest import (
    ChapterBoundary,
    SegmentManifest,
    manifest_to_json,
)
from songyan.services.import_segment_service import decode_source
from songyan.utils.hashing import sha256_file


def test_sha256_file_streams_content(tmp_path: Path) -> None:
    p = tmp_path / "a.txt"
    p.write_bytes("松烟".encode() * 1000)
    assert sha256_file(p, chunk_size=7) == hashlib.sha256("松烟".encode() * 1000).hexdigest()


def test_decode_source_utf8_sig() -> None:
    text, encoding = decode_source("松烟".encode("utf-8-sig"))
    assert text == "松烟"
    assert encoding == "utf-8-sig"


def test_decode_source_gb18030_fallback() -> None:
    text, encoding = decode_source("第一章 风起".encode("gb18030"))
    assert text == "第一章 风起"
    assert encoding == "gb18030"


def test_decode_source_undecodable_raises() -> None:
    with pytest.raises(ImportSourceError, match="编码"):
        decode_source(b"\xff\xfe\x00\x01\x8f\x8e")


def _boundary(number: int, start: int, end: int) -> ChapterBoundary:
    return ChapterBoundary(
        chapter_number=number,
        title=f"第{number}章",
        start_offset=start,
        end_offset=end,
        char_count=end - start,
        word_count=end - start,
        est_tokens=10,
        over_token_budget=False,
        body_sha256="x" * 64,
    )


def _manifest(boundaries: list[ChapterBoundary]) -> SegmentManifest:
    return SegmentManifest(
        source_path="book.txt",
        source_sha256="a" * 64,
        normalized_sha256="b" * 64,
        encoding="utf-8-sig",
        line_endings_normalized=False,
        token_budget=6000,
        chapter_count=len(boundaries),
        has_prologue=False,
        prologue_chars=0,
        boundaries=boundaries,
        status="pending_confirmation",
        created_at=datetime(2026, 9, 8, tzinfo=UTC),
    )


def test_manifest_json_is_deterministic() -> None:
    first = _manifest([_boundary(1, 0, 100), _boundary(2, 100, 200)])
    second = SegmentManifest(**first.model_dump())
    assert first is not second
    first_json = manifest_to_json(first)
    assert first_json == manifest_to_json(second)
    assert first_json.endswith("\n")
    assert '"created_at": "2026-09-08T00:00:00Z"' in first_json


def test_manifest_rejects_non_sequential_chapters() -> None:
    with pytest.raises(ValueError):
        _manifest([_boundary(1, 0, 100), _boundary(3, 100, 200)])


def test_manifest_rejects_overlapping_offsets() -> None:
    with pytest.raises(ValueError):
        _manifest([_boundary(1, 0, 150), _boundary(2, 100, 200)])


def test_manifest_rejects_confirmed_without_confirmed_at() -> None:
    payload = _manifest([_boundary(1, 0, 100)]).model_dump()
    payload["status"] = "confirmed"
    with pytest.raises(ValueError, match="confirmed"):
        SegmentManifest(**payload)


def test_manifest_rejects_pending_with_confirmed_at() -> None:
    payload = _manifest([_boundary(1, 0, 100)]).model_dump()
    payload["confirmed_at"] = datetime(2026, 9, 9, tzinfo=UTC)
    with pytest.raises(ValueError, match="confirmed"):
        SegmentManifest(**payload)


def test_manifest_accepts_confirmed_with_confirmed_at() -> None:
    payload = _manifest([_boundary(1, 0, 100)]).model_dump()
    payload["status"] = "confirmed"
    payload["confirmed_at"] = datetime(2026, 9, 9, tzinfo=UTC)
    manifest = SegmentManifest(**payload)
    assert manifest.status == "confirmed"
    assert manifest.confirmed_at == datetime(2026, 9, 9, tzinfo=UTC)
