"""Task 235: V15 章节切分与人工确认 — 服务层单测."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from songyan.exceptions import ImportSourceError
from songyan.utils.hashing import sha256_file


def test_sha256_file_streams_content(tmp_path: Path) -> None:
    p = tmp_path / "a.txt"
    p.write_bytes("松烟".encode() * 1000)
    assert sha256_file(p) == hashlib.sha256("松烟".encode() * 1000).hexdigest()


def test_decode_source_utf8_sig() -> None:
    from songyan.services.import_segment_service import decode_source

    text, encoding = decode_source("松烟".encode("utf-8-sig"))
    assert text == "松烟"
    assert encoding == "utf-8-sig"


def test_decode_source_gb18030_fallback() -> None:
    from songyan.services.import_segment_service import decode_source

    text, encoding = decode_source("第一章 风起".encode("gb18030"))
    assert text == "第一章 风起"
    assert encoding == "gb18030"


def test_decode_source_undecodable_raises() -> None:
    from songyan.services.import_segment_service import decode_source

    with pytest.raises(ImportSourceError, match="编码"):
        decode_source(b"\xff\xfe\x00\x01\x8f\x8e")
