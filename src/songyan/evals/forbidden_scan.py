"""Per-chapter forbidden-term scan for accepted manuscript text."""

from __future__ import annotations

from dataclasses import dataclass

from songyan.agents.goal_planner import _extract_forbidden_terms_for_chapter
from songyan.db.repository import ChapterHeadRepository, ChapterVersionRepository
from songyan.evals.forbidden_patterns import detect_forbidden_patterns
from songyan.workflows._narrative_context import load_narrative_goal_context


@dataclass(frozen=True)
class ForbiddenTermHit:
    """One accepted-text match against explicit chapter-scoped forbiddens."""

    chapter_number: int
    term: str
    line_number: int
    evidence: str


@dataclass(frozen=True)
class ForbiddenScanResult:
    """Forbidden-term scan result."""

    scanned_chapters: list[int]
    hits: list[ForbiddenTermHit]
    warnings: list[str]


def scan_text_for_forbidden_terms(
    *,
    chapter_number: int,
    text: str,
    forbidden_terms: list[str],
) -> list[ForbiddenTermHit]:
    """Scan one chapter text for explicit forbidden terms."""
    hits: list[ForbiddenTermHit] = []
    seen_terms: set[str] = set()
    for raw_term in forbidden_terms:
        term = str(raw_term).strip()
        if not term or term in seen_terms:
            continue
        seen_terms.add(term)
        pos = text.find(term)
        if pos < 0:
            continue
        line_number = text.count("\n", 0, pos) + 1
        line_start = text.rfind("\n", 0, pos) + 1
        line_end = text.find("\n", pos)
        if line_end < 0:
            line_end = len(text)
        evidence = text[line_start:line_end].strip() or term
        hits.append(
            ForbiddenTermHit(
                chapter_number=chapter_number,
                term=term,
                line_number=line_number,
                evidence=evidence,
            )
        )
    for pattern_match in detect_forbidden_patterns(text, forbidden_terms):
        line_number = text.count("\n", 0, pattern_match.start) + 1
        line_start = text.rfind("\n", 0, pattern_match.start) + 1
        line_end = text.find("\n", pattern_match.start)
        if line_end < 0:
            line_end = len(text)
        evidence = text[line_start:line_end].strip() or pattern_match.matched_text
        hits.append(
            ForbiddenTermHit(
                chapter_number=chapter_number,
                term=f"pattern:{pattern_match.label}",
                line_number=line_number,
                evidence=evidence,
            )
        )
    return hits


async def scan_accepted_forbidden_terms(
    *,
    project_id: str,
    chapter_numbers: list[int],
) -> ForbiddenScanResult:
    """Scan accepted chapter versions using chapter-scoped terms from arc_goal."""
    scanned: list[int] = []
    hits: list[ForbiddenTermHit] = []
    warnings: list[str] = []
    head_repo = ChapterHeadRepository()
    version_repo = ChapterVersionRepository()

    for chapter_number in chapter_numbers:
        narrative_ctx = await load_narrative_goal_context(project_id, chapter_number)
        if not narrative_ctx.has_skeleton:
            warnings.append(f"Ch{chapter_number}: no narrative skeleton")
            continue
        terms = _extract_forbidden_terms_for_chapter(
            narrative_ctx.arc_goal,
            chapter_number,
        )
        if not terms:
            scanned.append(chapter_number)
            continue

        head = await head_repo.get(project_id, chapter_number)
        if head is None or not head.accepted_version_id:
            warnings.append(f"Ch{chapter_number}: no accepted version")
            continue
        version = await version_repo.get(head.accepted_version_id)
        if version is None:
            warnings.append(
                f"Ch{chapter_number}: accepted version not found "
                f"({head.accepted_version_id})"
            )
            continue

        scanned.append(chapter_number)
        hits.extend(
            scan_text_for_forbidden_terms(
                chapter_number=chapter_number,
                text=version.content,
                forbidden_terms=terms,
            )
        )

    return ForbiddenScanResult(
        scanned_chapters=scanned,
        hits=hits,
        warnings=warnings,
    )


def render_forbidden_scan_section(result: ForbiddenScanResult) -> str:
    """Render a markdown section for per-chapter forbidden-term scan results."""
    lines = [
        "",
        "## 章节禁用词扫描",
        "",
        f"- **扫描章节**: {_format_chapters(result.scanned_chapters)}",
        f"- **命中数**: {len(result.hits)}",
    ]
    if result.warnings:
        lines.append("- **扫描警告**:")
        lines.extend(f"  - {warning}" for warning in result.warnings)
    if result.hits:
        lines.extend(
            [
                "",
                "| 章节 | 禁用词 | 行号 | 证据 |",
                "|------|--------|------|------|",
            ]
        )
        for hit in result.hits:
            evidence = hit.evidence.replace("|", "\\|")
            lines.append(
                f"| Ch{hit.chapter_number} | `{hit.term}` | "
                f"{hit.line_number} | {evidence} |"
            )
    return "\n".join(lines)


def _format_chapters(chapters: list[int]) -> str:
    if not chapters:
        return "-"
    return ", ".join(f"Ch{chapter}" for chapter in chapters)
