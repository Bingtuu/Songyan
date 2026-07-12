"""Task 171u: deterministic D1 text-clean application service."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import structlog

from songyan.agents.rule_auditor import (
    collect_text_cleanliness_clean_issues,
    detect_duplicate_paragraphs,
)
from songyan.db.connection import get_db
from songyan.db.repository import ChapterHeadRepository, ChapterVersionRepository
from songyan.exceptions import SongyanError
from songyan.models import ChapterHead, ChapterVersion, TextCleanlinessCleanIssue
from songyan.utils._helpers import split_paragraphs
from songyan.utils.scene_parser import parse_scenes

logger = structlog.get_logger(__name__)


class TextCleanlinessCleanError(SongyanError):
    """Raised when deterministic D1 cleaning cannot safely complete."""


@dataclass(frozen=True)
class TextCleanResult:
    """Pure text-clean result."""

    original_content: str
    cleaned_content: str
    issues: list[TextCleanlinessCleanIssue]
    remaining_issues: list[TextCleanlinessCleanIssue]

    @property
    def changed(self) -> bool:
        return self.cleaned_content != self.original_content


@dataclass(frozen=True)
class ChapterCleanApplicationResult:
    """DB application result for one chapter."""

    project_id: str
    chapter_number: int
    original_version_id: str
    cleaned_version_id: str | None
    issues: list[TextCleanlinessCleanIssue]
    remaining_issues: list[TextCleanlinessCleanIssue]
    changed: bool


def _remove_matching_lines(content: str, predicates: list[re.Pattern[str]]) -> str:
    lines = content.splitlines()
    kept = [
        line
        for line in lines
        if not any(pattern.search(line) for pattern in predicates)
    ]
    return "\n".join(kept)


_LINE_REMOVAL_PATTERNS = [
    re.compile(
        r"^\s*#{1,6}\s*(?:第\s*)?[一二三四五六七八九十百千万零〇两\d]+"
        r"\s*(?:章|章节|回)\b.*$"
    ),
    re.compile(r"^\s*#{1,6}\s*Chapter\s+\d+\b.*$", re.I),
    re.compile(r"(?:保护内容|请勿修改|不要修改|不可修改)"),
    re.compile(r"每句末尾.{0,12}(?:加重|加强|强化).{0,8}语气"),
    re.compile(
        r"(?:请|务必|必须).{0,20}(?:改写|修改|替换|保留|删除)"
        r".{0,20}(?:本段|这一段|正文|内容)"
    ),
    re.compile(r"(?:patch|rewrite|diff)\s*(?:note|instruction|指令|说明)\s*[:：]", re.I),
    re.compile(r"^\s*(?:\.{3,}|．{3,}|。{3,}|…{2,}|·{3,})\s*$"),
]

_META_INLINE_PATTERNS = [
    re.compile(r"(?s)<!--.*?-->"),
    re.compile(r"(?s)<mark>.*?</mark>"),
    re.compile(r"(?s)\[\[.*?\]\]"),
]

_SCENE_TITLE_LINE_PATTERNS = [
    re.compile(r"^\s*#{1,6}\s*Scene\s+(?:\d+|[A-Z]).*$", re.I),
    re.compile(r"^\s*Scene\s+(?:\d+|[A-Z])(?:\s*[:：].*)?\s*$", re.I),
    re.compile(r"^\s*\*\*Scene\s+(?:\d+|[A-Z])\*\*.*$", re.I),
    re.compile(r"^\s*#{1,6}\s*场景\s*(?:\d+|[A-Z]|[一二三四五六七八九十]+).*$"),
    re.compile(r"^\s*场景\s*(?:\d+|[A-Z]|[一二三四五六七八九十]+)(?:\s*[:：].*)?\s*$"),
    re.compile(r"^\s*\*\*场景\s*(?:\d+|[A-Z]|[一二三四五六七八九十]+)\*\*.*$"),
    re.compile(r"^\s*meta:.*$", re.I),
]


def _remove_inline_meta(content: str) -> str:
    result = content
    for pattern in _META_INLINE_PATTERNS:
        result = pattern.sub("", result)
    return result


def _remove_ellipsis_placeholder_paragraphs(content: str) -> str:
    paragraphs = re.split(r"\n\s*\n", content.replace("\r\n", "\n"))
    kept: list[str] = []
    for paragraph in paragraphs:
        stripped = paragraph.strip()
        normalized = re.sub(r"\s+", "", stripped)
        is_placeholder = bool(re.fullmatch(r"[.．。…·]+", normalized)) and (
            normalized.count(".") + normalized.count("．") >= 3
            or normalized.count("…") >= 2
        )
        if stripped and not is_placeholder:
            kept.append(stripped)
    return "\n\n".join(kept)


def _clean_slash_splices(content: str) -> str:
    cleaned_lines: list[str] = []
    for line in content.splitlines():
        # Only clean narrative splice separators. Units, paths, URLs and ratios are left intact.
        line = re.sub(
            r"(?<=[\u4e00-\u9fff。！？；：，、”）】])\s*/\s*"
            r"(?=[“（【\u4e00-\u9fff])",
            "",
            line,
        )
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def _dedup_detected_paragraphs(content: str) -> str:
    duplicates = detect_duplicate_paragraphs(content)
    if not duplicates:
        return content
    duplicate_indexes = {match.paragraph_index for match in duplicates}
    kept = [
        paragraph
        for idx, paragraph in enumerate(split_paragraphs(content), 1)
        if idx not in duplicate_indexes
    ]
    return "\n\n".join(kept)


def _normalize_blank_lines(content: str) -> str:
    lines = [line.rstrip() for line in content.replace("\r\n", "\n").splitlines()]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_chapter_text(
    content: str,
    *,
    chapter_number: int | None = None,
    version_id: str | None = None,
) -> TextCleanResult:
    """Apply deterministic text-cleaning only for 171t hard-clean issue types."""
    issues = collect_text_cleanliness_clean_issues(
        content,
        chapter_number=chapter_number,
        version_id=version_id,
    )
    cleaned = content
    cleaned = _remove_inline_meta(cleaned)
    cleaned = _remove_matching_lines(
        cleaned,
        [*_LINE_REMOVAL_PATTERNS, *_SCENE_TITLE_LINE_PATTERNS],
    )
    cleaned = _clean_slash_splices(cleaned)
    cleaned = _remove_ellipsis_placeholder_paragraphs(cleaned)
    cleaned = _dedup_detected_paragraphs(cleaned)
    cleaned = _normalize_blank_lines(cleaned)
    remaining = collect_text_cleanliness_clean_issues(
        cleaned,
        chapter_number=chapter_number,
        version_id=version_id,
    )
    return TextCleanResult(
        original_content=content,
        cleaned_content=cleaned,
        issues=issues,
        remaining_issues=remaining,
    )


def _word_count(content: str) -> int:
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", content))
    other_words = len(re.findall(r"[a-zA-Z0-9]+", content))
    return chinese_chars + other_words


async def _next_version_number(conn: Any, project_id: str, chapter_number: int) -> int:
    cursor = await conn.execute(
        """SELECT COALESCE(MAX(version_number), 0) + 1
           FROM chapter_versions
           WHERE project_id = ? AND chapter_number = ?""",
        (project_id, chapter_number),
    )
    row = await cursor.fetchone()
    return int(row[0]) if row else 1


async def _get_head_for_update(
    conn: Any, project_id: str, chapter_number: int
) -> ChapterHead | None:
    conn.row_factory = None
    cursor = await conn.execute(
        """SELECT project_id, chapter_number, current_version_id,
                  accepted_version_id, status, updated_at
           FROM chapter_heads
           WHERE project_id = ? AND chapter_number = ?""",
        (project_id, chapter_number),
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    return ChapterHead(
        project_id=row[0],
        chapter_number=int(row[1]),
        current_version_id=row[2],
        accepted_version_id=row[3],
        status=row[4],
        updated_at=row[5],
    )


async def _get_version_for_update(conn: Any, version_id: str) -> ChapterVersion | None:
    conn.row_factory = None
    cursor = await conn.execute(
        """SELECT version_id, project_id, chapter_number, version_number,
                  version_type, is_abandoned, content, word_count, scenes,
                  generation_metadata, score_card, creative_brief_id,
                  parent_version_id, created_at
           FROM chapter_versions
           WHERE version_id = ?""",
        (version_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    import json

    return ChapterVersion(
        version_id=row[0],
        project_id=row[1],
        chapter_number=int(row[2]),
        version_number=int(row[3]),
        version_type=row[4],
        is_abandoned=bool(row[5]),
        content=row[6],
        word_count=int(row[7] or 0),
        scenes=json.loads(row[8] or "[]"),
        generation_metadata=json.loads(row[9] or "{}"),
        score_card=json.loads(row[10] or "{}"),
        creative_brief_id=row[11],
        parent_version_id=row[12],
        created_at=row[13],
    )


async def apply_chapter_text_cleaning(
    project_id: str,
    chapter_number: int,
    *,
    version_repo: ChapterVersionRepository | None = None,
    head_repo: ChapterHeadRepository | None = None,
) -> ChapterCleanApplicationResult:
    """Create an accepted cleaned version and atomically update chapter head."""
    version_repo = version_repo or ChapterVersionRepository()
    head_repo = head_repo or ChapterHeadRepository()

    async with get_db() as conn:
        try:
            head = await _get_head_for_update(conn, project_id, chapter_number)
            if head is None or head.status != "accepted" or not head.accepted_version_id:
                msg = f"accepted head not found: {project_id} Ch{chapter_number}"
                raise TextCleanlinessCleanError(msg)
            original = await _get_version_for_update(conn, head.accepted_version_id)
            if original is None:
                msg = f"accepted version not found: {head.accepted_version_id}"
                raise TextCleanlinessCleanError(msg)

            clean = clean_chapter_text(
                original.content,
                chapter_number=chapter_number,
                version_id=original.version_id,
            )
            if not clean.issues:
                return ChapterCleanApplicationResult(
                    project_id=project_id,
                    chapter_number=chapter_number,
                    original_version_id=original.version_id,
                    cleaned_version_id=None,
                    issues=[],
                    remaining_issues=[],
                    changed=False,
                )
            if clean.remaining_issues:
                msg = (
                    f"deterministic clean left {len(clean.remaining_issues)} hard issues "
                    f"for {project_id} Ch{chapter_number}"
                )
                raise TextCleanlinessCleanError(msg)
            if not clean.changed:
                msg = (
                    "clean issues detected but content unchanged: "
                    f"{project_id} Ch{chapter_number}"
                )
                raise TextCleanlinessCleanError(msg)

            version_number = await _next_version_number(conn, project_id, chapter_number)
            cleaned_version_id = f"clean-{chapter_number}-{version_number}-{uuid.uuid4().hex[:8]}"
            metadata = dict(original.generation_metadata or {})
            metadata["task"] = "171u"
            metadata["cleaned_from_version_id"] = original.version_id
            metadata["clean_issues"] = [
                issue.model_dump(mode="json") for issue in clean.issues
            ]
            metadata["cleaned_at"] = datetime.now().isoformat()

            cleaned_version = ChapterVersion(
                version_id=cleaned_version_id,
                project_id=project_id,
                chapter_number=chapter_number,
                version_number=version_number,
                version_type="accepted",
                content=clean.cleaned_content,
                word_count=_word_count(clean.cleaned_content),
                scenes=parse_scenes(clean.cleaned_content),
                generation_metadata=metadata,
                score_card=original.score_card,
                creative_brief_id=original.creative_brief_id,
                parent_version_id=original.version_id,
            )
            await version_repo.create(cleaned_version, conn=conn)
            await head_repo.update(
                ChapterHead(
                    project_id=project_id,
                    chapter_number=chapter_number,
                    current_version_id=cleaned_version_id,
                    accepted_version_id=cleaned_version_id,
                    status="accepted",
                    updated_at=datetime.now(),
                ),
                conn=conn,
            )
            await conn.commit()
        except Exception as exc:  # noqa: BLE001 - rollback and wrap service errors
            await conn.rollback()
            if isinstance(exc, TextCleanlinessCleanError):
                raise
            msg = f"failed to apply text clean for {project_id} Ch{chapter_number}"
            raise TextCleanlinessCleanError(msg) from exc

    logger.info(
        "text_cleanliness.clean_applied",
        project_id=project_id,
        chapter_number=chapter_number,
        original_version_id=original.version_id,
        cleaned_version_id=cleaned_version_id,
        issue_count=len(clean.issues),
    )
    return ChapterCleanApplicationResult(
        project_id=project_id,
        chapter_number=chapter_number,
        original_version_id=original.version_id,
        cleaned_version_id=cleaned_version_id,
        issues=clean.issues,
        remaining_issues=clean.remaining_issues,
        changed=True,
    )


async def apply_project_text_cleaning(
    project_id: str,
    start: int,
    end: int,
) -> list[ChapterCleanApplicationResult]:
    """Apply deterministic D1 cleaning for a chapter range."""
    results: list[ChapterCleanApplicationResult] = []
    for chapter_number in range(start, end + 1):
        results.append(await apply_chapter_text_cleaning(project_id, chapter_number))
    return results
