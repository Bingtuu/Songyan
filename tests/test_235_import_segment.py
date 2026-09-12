"""Task 235: V15 章节切分与人工确认 — 服务层单测."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from songyan.exceptions import ImportSegmentError, ImportSourceError
from songyan.models.import_manifest import (
    ChapterBoundary,
    SegmentManifest,
    manifest_to_json,
)
from songyan.services.import_segment_service import (
    decode_source,
    detect_boundaries,
    normalize_line_endings,
)
from songyan.utils.hashing import sha256_file

SAMPLE = (
    "引子\n\n这是一段题外话。\n\n"
    "第一章 风起\n\n松烟初入城。\n他抬头看天。\n\n"
    "第二章\n\n雨下了一夜。\n\n"
    "第三十五章 雪\n\n城破了。\n"
)


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


def test_normalize_line_endings() -> None:
    text, changed = normalize_line_endings("a\r\nb\rc")
    assert text == "a\nb\nc"
    assert changed is True
    assert normalize_line_endings("a\nb") == ("a\nb", False)


def test_detect_boundaries_chinese_and_arabic() -> None:
    boundaries, prologue, _bodies = detect_boundaries(SAMPLE, token_budget=6000)
    assert prologue == "引子\n\n这是一段题外话。"
    assert [b.chapter_number for b in boundaries] == [1, 2, 3]
    assert boundaries[0].title == "第一章 风起"
    assert boundaries[1].title == "第二章"
    assert boundaries[2].title == "第三十五章 雪"


def test_detect_boundaries_offsets_roundtrip() -> None:
    text, _ = normalize_line_endings(SAMPLE)
    boundaries, _, _bodies = detect_boundaries(text, token_budget=6000)
    for boundary in boundaries:
        segment = text[boundary.start_offset : boundary.end_offset]
        assert segment.startswith(boundary.title)
    assert boundaries[0].start_offset == text.index("第一章")
    assert boundaries[-1].end_offset == len(text)


def test_detect_boundaries_english_and_hui_unit() -> None:
    text = "Chapter 1 Awakening\n\nBody one.\n\n第五回 试剑\n\nBody two.\n"
    boundaries, prologue, _ = detect_boundaries(text, token_budget=6000)
    assert len(boundaries) == 2
    assert prologue == ""


def test_detect_boundaries_strips_title_from_body() -> None:
    boundaries, _, bodies = detect_boundaries(SAMPLE, token_budget=6000)
    expected = hashlib.sha256("松烟初入城。\n他抬头看天。".encode()).hexdigest()
    assert bodies[0] == "松烟初入城。\n他抬头看天。"
    assert boundaries[0].body_sha256 == expected


def test_detect_boundaries_flags_over_budget() -> None:
    boundaries, _, _ = detect_boundaries(SAMPLE, token_budget=5)
    assert all(b.over_token_budget for b in boundaries)


def test_detect_boundaries_within_budget() -> None:
    boundaries, _, _ = detect_boundaries(SAMPLE, token_budget=6000)
    assert all(b.over_token_budget is False for b in boundaries)


def test_detect_boundaries_full_width_indent_header() -> None:
    text = "　第一章 风起\n\n松烟初入城。\n\n第二章\n\n雨下了一夜。\n"
    boundaries, prologue, _ = detect_boundaries(text, token_budget=6000)
    assert prologue == ""
    assert [b.title for b in boundaries] == ["第一章 风起", "第二章"]


def test_detect_boundaries_prefixed_header_offsets_and_title() -> None:
    text = "　## 第三章 标题\n\n正文内容。\n"
    boundaries, prologue, bodies = detect_boundaries(text, token_budget=6000)
    assert prologue == ""
    assert len(boundaries) == 1
    boundary = boundaries[0]
    assert boundary.title == "第三章 标题"
    # start_offset 指向原始标题行行首（含全角缩进与 # 前缀），是有意语义。
    assert boundary.start_offset == 0
    assert text[boundary.start_offset : boundary.end_offset] == text
    assert bodies[0] == "正文内容。"
    assert boundary.body_sha256 == hashlib.sha256("正文内容。".encode()).hexdigest()


def test_detect_boundaries_eof_empty_body_chapter() -> None:
    text = "第一章 A\n\n正文。\n\n第二章 B\n"
    boundaries, _, bodies = detect_boundaries(text, token_budget=6000)
    assert len(boundaries) == 2
    assert bodies[1] == ""
    assert boundaries[1].char_count == 0
    assert boundaries[1].body_sha256 == hashlib.sha256(b"").hexdigest()


def test_detect_boundaries_no_header_raises() -> None:
    with pytest.raises(ImportSegmentError, match="章节标题"):
        detect_boundaries("没有标题的一大段正文。" * 100, token_budget=6000)


def _write_source(tmp_path: Path, content: str = SAMPLE) -> Path:
    src = tmp_path / "book.txt"
    src.write_text(content, encoding="utf-8")
    return src


def test_build_manifest_binds_fingerprints(tmp_path: Path) -> None:
    from songyan.services.import_segment_service import build_manifest

    src = _write_source(tmp_path)
    manifest, normalized, bodies = build_manifest(src, token_budget=6000)
    assert manifest.source_sha256 == sha256_file(src)
    assert manifest.normalized_sha256 == hashlib.sha256(normalized.encode()).hexdigest()
    assert manifest.encoding == "utf-8-sig"
    assert manifest.chapter_count == 3
    assert manifest.has_prologue is True
    assert manifest.status == "pending_confirmation"
    assert len(bodies) == 3
    assert bodies[0] == "松烟初入城。\n他抬头看天。"


def test_write_artifacts_layout_and_no_title_in_bodies(tmp_path: Path) -> None:
    from songyan.services.import_segment_service import build_manifest, write_segment_artifacts

    src = _write_source(tmp_path)
    manifest, normalized, bodies = build_manifest(src, token_budget=6000)
    out = tmp_path / "out"
    write_segment_artifacts(out, manifest, normalized, bodies)

    assert (out / "manifest.json").exists()
    assert (out / "source.normalized.txt").read_text(encoding="utf-8") == normalized
    ch1 = (out / "chapters" / "ch001.md").read_text(encoding="utf-8")
    assert "第一章" not in ch1
    assert ch1.startswith("松烟初入城。")


def test_load_manifest_roundtrip(tmp_path: Path) -> None:
    from songyan.services.import_segment_service import (
        build_manifest,
        load_manifest,
        write_segment_artifacts,
    )

    src = _write_source(tmp_path)
    manifest, normalized, bodies = build_manifest(src, token_budget=6000)
    out = tmp_path / "out"
    write_segment_artifacts(out, manifest, normalized, bodies)
    loaded = load_manifest(out / "manifest.json")
    assert loaded == manifest


def test_load_manifest_invalid_json_raises(tmp_path: Path) -> None:
    from songyan.services.import_segment_service import load_manifest

    bad = tmp_path / "manifest.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(ImportSegmentError):
        load_manifest(bad)


def test_gate_rejects_pending_manifest(tmp_path: Path) -> None:
    from songyan.services.import_segment_service import (
        assert_replay_allowed,
        build_manifest,
        write_segment_artifacts,
    )

    src = _write_source(tmp_path)
    manifest, normalized, bodies = build_manifest(src, token_budget=6000)
    path, _ = write_segment_artifacts(tmp_path / "out", manifest, normalized, bodies)
    with pytest.raises(ImportSegmentError, match="确认"):
        assert_replay_allowed(path)


def test_confirm_flips_status_and_gate_passes(tmp_path: Path) -> None:
    from songyan.services.import_segment_service import (
        assert_replay_allowed,
        build_manifest,
        confirm_manifest,
        write_segment_artifacts,
    )

    src = _write_source(tmp_path)
    manifest, normalized, bodies = build_manifest(src, token_budget=6000)
    path, _ = write_segment_artifacts(tmp_path / "out", manifest, normalized, bodies)
    confirmed = confirm_manifest(path)
    assert confirmed.status == "confirmed"
    assert confirmed.confirmed_at is not None
    assert assert_replay_allowed(path).status == "confirmed"


def test_confirm_rejects_tampered_source(tmp_path: Path) -> None:
    from songyan.services.import_segment_service import (
        build_manifest,
        confirm_manifest,
        write_segment_artifacts,
    )

    src = _write_source(tmp_path)
    manifest, normalized, bodies = build_manifest(src, token_budget=6000)
    path, _ = write_segment_artifacts(tmp_path / "out", manifest, normalized, bodies)
    src.write_text("被改过的源文件", encoding="utf-8")
    with pytest.raises(ImportSegmentError, match="指纹"):
        confirm_manifest(path)


def test_confirm_revalidates_edited_boundaries(tmp_path: Path) -> None:
    import json as _json

    from songyan.services.import_segment_service import (
        build_manifest,
        confirm_manifest,
        write_segment_artifacts,
    )

    src = _write_source(tmp_path)
    manifest, normalized, bodies = build_manifest(src, token_budget=6000)
    path, _ = write_segment_artifacts(tmp_path / "out", manifest, normalized, bodies)
    payload = _json.loads(path.read_text(encoding="utf-8"))
    payload["boundaries"][1]["start_offset"] = len(normalized) + 100
    payload["boundaries"][1]["end_offset"] = len(normalized) + 200
    path.write_text(_json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ImportSegmentError):
        confirm_manifest(path)


def test_confirm_regenerates_chapters_after_manual_split(tmp_path: Path) -> None:
    import json as _json

    from songyan.services.import_segment_service import (
        build_manifest,
        confirm_manifest,
        write_segment_artifacts,
    )

    src = _write_source(tmp_path)
    manifest, normalized, bodies = build_manifest(src, token_budget=6000)
    path, _ = write_segment_artifacts(tmp_path / "out", manifest, normalized, bodies)
    payload = _json.loads(path.read_text(encoding="utf-8"))
    second = payload["boundaries"][1]
    mid = second["start_offset"] + (second["end_offset"] - second["start_offset"]) // 2
    first_half = dict(second, end_offset=mid)
    second_half = dict(second, start_offset=mid, chapter_number=3)
    payload["boundaries"][2]["chapter_number"] = 4
    payload["boundaries"][1:2] = [first_half, second_half]
    payload["chapter_count"] = 4
    path.write_text(_json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    confirmed = confirm_manifest(path)
    assert confirmed.chapter_count == 4
    chapters_dir = path.parent / "chapters"
    assert sorted(p.name for p in chapters_dir.iterdir()) == [
        "ch001.md",
        "ch002.md",
        "ch003.md",
        "ch004.md",
    ]
    for boundary in confirmed.boundaries:
        content = (chapters_dir / f"ch{boundary.chapter_number:03d}.md").read_text(
            encoding="utf-8"
        )
        assert content.endswith("\n")
        current = hashlib.sha256(content[:-1].encode("utf-8")).hexdigest()
        assert current == boundary.body_sha256


def test_slice_chapter_body_matches_detect_bodies() -> None:
    from songyan.services.import_segment_service import slice_chapter_body

    text, _ = normalize_line_endings(SAMPLE)
    boundaries, _, bodies = detect_boundaries(text, token_budget=6000)
    for boundary, body in zip(boundaries, bodies, strict=True):
        title, sliced_body = slice_chapter_body(text, boundary)
        assert title == boundary.title
        assert sliced_body == body
        assert hashlib.sha256(sliced_body.encode("utf-8")).hexdigest() == boundary.body_sha256


def test_confirm_body_sha256_matches_detect(tmp_path: Path) -> None:
    """detect 与 confirm 对同一未编辑样本产出相同 body_sha256（共享切片口径）."""
    from songyan.services.import_segment_service import (
        build_manifest,
        confirm_manifest,
        write_segment_artifacts,
    )

    src = _write_source(tmp_path)
    manifest, normalized, bodies = build_manifest(src, token_budget=6000)
    path, _ = write_segment_artifacts(tmp_path / "out", manifest, normalized, bodies)
    confirmed = confirm_manifest(path)
    for original, refreshed in zip(manifest.boundaries, confirmed.boundaries, strict=True):
        assert refreshed.body_sha256 == original.body_sha256
        assert refreshed.title == original.title


def test_resegment_removes_stale_chapter_files(tmp_path: Path) -> None:
    """重新切分章数减少后，chapters/ 不残留旧章."""
    from songyan.services.import_segment_service import (
        build_manifest,
        slice_chapter_body,
        write_segment_artifacts,
    )

    src = _write_source(tmp_path)
    manifest, normalized, bodies = build_manifest(src, token_budget=6000)
    out = tmp_path / "out"
    write_segment_artifacts(out, manifest, normalized, bodies)
    assert (out / "chapters" / "ch003.md").exists()

    merged = manifest.boundaries[1].model_copy(
        update={"end_offset": manifest.boundaries[2].end_offset}
    )
    new_boundaries = [manifest.boundaries[0], merged]
    new_manifest = manifest.model_copy(
        update={"boundaries": new_boundaries, "chapter_count": 2}
    )
    new_bodies = [slice_chapter_body(normalized, b)[1] for b in new_boundaries]
    write_segment_artifacts(out, new_manifest, normalized, new_bodies)
    assert sorted(p.name for p in (out / "chapters").iterdir()) == ["ch001.md", "ch002.md"]


def test_cleanup_preserves_non_chapter_notes(tmp_path: Path) -> None:
    """清理只针对 ch + 恰好 3 位数字 + .md，不误删人工笔记."""
    from songyan.services.import_segment_service import (
        build_manifest,
        confirm_manifest,
        write_segment_artifacts,
    )

    src = _write_source(tmp_path)
    manifest, normalized, bodies = build_manifest(src, token_budget=6000)
    out = tmp_path / "out"
    path, _ = write_segment_artifacts(out, manifest, normalized, bodies)
    notes = out / "chapters" / "ch_notes.md"
    notes.write_text("人工审查笔记", encoding="utf-8")
    confirm_manifest(path)
    assert notes.read_text(encoding="utf-8") == "人工审查笔记"
    write_segment_artifacts(out, manifest, normalized, bodies)
    assert notes.read_text(encoding="utf-8") == "人工审查笔记"


def test_write_artifacts_flags_overwrite_of_confirmed(tmp_path: Path) -> None:
    from songyan.services.import_segment_service import (
        build_manifest,
        confirm_manifest,
        write_segment_artifacts,
    )

    src = _write_source(tmp_path)
    manifest, normalized, bodies = build_manifest(src, token_budget=6000)
    out = tmp_path / "out"
    path, overwritten = write_segment_artifacts(out, manifest, normalized, bodies)
    assert overwritten is False
    confirm_manifest(path)
    _, overwritten = write_segment_artifacts(out, manifest, normalized, bodies)
    assert overwritten is True
