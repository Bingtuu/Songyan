"""Arc/Volume 摘要自动生成 — LLM-driven aggregation."""

from __future__ import annotations

import uuid

import structlog

from songyan.db.context_repo import SummaryRepository
from songyan.db.layered_context_repo import ArcSummaryRepository, VolumeSummaryRepository
from songyan.llm.client import call_llm
from songyan.llm.parsing import parse_llm_response
from songyan.models import ArcSummary, ChapterSummary, VolumeSummary
from songyan.prompts import render_agent_prompt

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def _format_chapter_summaries(summaries: list[ChapterSummary]) -> str:
    """Format chapter summaries for the arc generator prompt."""
    lines: list[str] = []
    for s in summaries:
        lines.append(f"### 第{s.chapter_number}章")
        lines.append(f"摘要: {s.summary}")
        if s.key_events:
            lines.append(f"关键事件: {', '.join(s.key_events)}")
        if s.characters_appeared:
            lines.append(f"出场角色: {', '.join(s.characters_appeared)}")
        if s.impact_score:
            lines.append(f"影响力: {s.impact_score}")
        lines.append("")
    return "\n".join(lines)


def _format_arc_summaries(arcs: list[ArcSummary]) -> str:
    """Format arc summaries for the volume generator prompt."""
    lines: list[str] = []
    for a in arcs:
        lines.append(f"### {a.arc_title} (第{a.start_chapter}-{a.end_chapter}章)")
        lines.append(f"摘要: {a.arc_summary}")
        if a.key_events:
            lines.append(f"关键事件: {', '.join(a.key_events)}")
        if a.character_arcs:
            lines.append("角色变化:")
            for char, desc in a.character_arcs.items():
                lines.append(f"  - {char}: {desc}")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

class ArcSummaryGenerator:
    """Generate Arc-level summaries via LLM aggregation of chapter summaries."""

    def __init__(
        self,
        summary_repo: SummaryRepository | None = None,
        arc_repo: ArcSummaryRepository | None = None,
    ) -> None:
        self.summary_repo = summary_repo or SummaryRepository()
        self.arc_repo = arc_repo or ArcSummaryRepository()

    async def generate(
        self,
        project_id: str,
        start_chapter: int,
        end_chapter: int,
        *,
        temperature: float = 0.5,
    ) -> ArcSummary:
        """Generate an ArcSummary for chapters [start, end].

        If an arc covering this range already exists, it is updated in place.

        Args:
            project_id: Project identifier.
            start_chapter: First chapter in the arc (inclusive).
            end_chapter: Last chapter in the arc (inclusive).
            temperature: LLM sampling temperature.

        Returns:
            Generated ArcSummary (already persisted to DB).
        """
        # Check for existing arc covering this exact range
        existing = None
        arcs = await self.arc_repo.list_by_project(project_id)
        for a in arcs:
            if a.start_chapter == start_chapter and a.end_chapter == end_chapter:
                existing = a
                break

        summaries = await self.summary_repo.list_by_chapter_range(
            project_id, start_chapter, end_chapter
        )

        if not summaries:
            logger.warning(
                "arc_summary.no_data",
                project_id=project_id,
                start=start_chapter,
                end=end_chapter,
            )
            if existing:
                return existing
            arc = ArcSummary(
                arc_id=f"arc-{uuid.uuid4().hex[:8]}",
                project_id=project_id,
                start_chapter=start_chapter,
                end_chapter=end_chapter,
                arc_title=f"Arc {start_chapter}-{end_chapter}",
                arc_summary="（暂无摘要数据）",
            )
            await self.arc_repo.create(arc, project_id)
            return arc

        prompt = render_agent_prompt(
            "arc_summary_generator",
            {
                "start_chapter": start_chapter,
                "end_chapter": end_chapter,
                "chapter_summaries_text": _format_chapter_summaries(summaries),
            },
        )

        llm_raw = await call_llm(prompt, temperature=temperature, max_tokens=2048)
        data = parse_llm_response(llm_raw)

        if existing:
            # Update in place
            existing.arc_title = data.get("arc_title", existing.arc_title)
            existing.arc_summary = data.get("arc_summary", existing.arc_summary)
            existing.key_events = data.get("key_events", existing.key_events)
            existing.resolved_threads = data.get("resolved_threads", existing.resolved_threads)
            existing.new_threads = data.get("new_threads", existing.new_threads)
            existing.character_arcs = data.get("character_arcs", existing.character_arcs)
            await self.arc_repo.update(existing, project_id)
            logger.info(
                "arc_summary.updated",
                project_id=project_id,
                arc_id=existing.arc_id,
                chapters=len(summaries),
                title=existing.arc_title,
            )
            return existing

        arc = ArcSummary(
            arc_id=f"arc-{uuid.uuid4().hex[:8]}",
            project_id=project_id,
            start_chapter=start_chapter,
            end_chapter=end_chapter,
            arc_title=data.get("arc_title", f"Arc {start_chapter}-{end_chapter}"),
            arc_summary=data.get("arc_summary", ""),
            key_events=data.get("key_events", []),
            resolved_threads=data.get("resolved_threads", []),
            new_threads=data.get("new_threads", []),
            character_arcs=data.get("character_arcs", {}),
        )

        await self.arc_repo.create(arc, project_id)
        logger.info(
            "arc_summary.generated",
            project_id=project_id,
            arc_id=arc.arc_id,
            chapters=len(summaries),
            title=arc.arc_title,
        )
        return arc


class VolumeSummaryGenerator:
    """Generate Volume-level summaries via LLM aggregation of arc summaries."""

    def __init__(
        self,
        volume_repo: VolumeSummaryRepository | None = None,
    ) -> None:
        self.volume_repo = volume_repo or VolumeSummaryRepository()

    async def generate(
        self,
        project_id: str,
        arc_summaries: list[ArcSummary],
        *,
        temperature: float = 0.5,
    ) -> VolumeSummary:
        """Generate a VolumeSummary from a list of ArcSummaries.

        If a volume covering this range already exists, it is updated in place.

        Args:
            project_id: Project identifier.
            arc_summaries: Ordered list of ArcSummary objects.
            temperature: LLM sampling temperature.

        Returns:
            Generated VolumeSummary (already persisted to DB).
        """
        # Sort by start_chapter to ensure narrative order
        arcs = sorted(arc_summaries, key=lambda a: a.start_chapter)
        start_chapter = arcs[0].start_chapter if arcs else 0
        end_chapter = arcs[-1].end_chapter if arcs else 0

        # Check for existing volume covering this exact range
        existing = None
        volumes = await self.volume_repo.list_by_project(project_id)
        for v in volumes:
            if v.start_chapter == start_chapter and v.end_chapter == end_chapter:
                existing = v
                break

        if not arc_summaries:
            logger.warning("volume_summary.no_arcs", project_id=project_id)
            if existing:
                return existing
            volume = VolumeSummary(
                volume_id=f"vol-{uuid.uuid4().hex[:8]}",
                project_id=project_id,
                start_chapter=start_chapter,
                end_chapter=end_chapter,
                volume_title="（暂无卷数据）",
                volume_summary="",
            )
            await self.volume_repo.create(volume, project_id)
            return volume

        prompt = render_agent_prompt(
            "volume_summary_generator",
            {
                "arc_summaries_text": _format_arc_summaries(arcs),
            },
        )

        llm_raw = await call_llm(prompt, temperature=temperature, max_tokens=2048)
        data = parse_llm_response(llm_raw)

        if existing:
            existing.volume_title = data.get("volume_title", existing.volume_title)
            existing.volume_summary = data.get("volume_summary", existing.volume_summary)
            existing.major_revelations = data.get("major_revelations", existing.major_revelations)
            existing.world_state = data.get("world_state", existing.world_state)
            await self.volume_repo.update(existing, project_id)
            logger.info(
                "volume_summary.updated",
                project_id=project_id,
                volume_id=existing.volume_id,
                arcs=len(arcs),
                title=existing.volume_title,
            )
            return existing

        volume = VolumeSummary(
            volume_id=f"vol-{uuid.uuid4().hex[:8]}",
            project_id=project_id,
            start_chapter=start_chapter,
            end_chapter=end_chapter,
            volume_title=data.get("volume_title", f"第{start_chapter}-{end_chapter}章"),
            volume_summary=data.get("volume_summary", ""),
            major_revelations=data.get("major_revelations", []),
            world_state=data.get("world_state", ""),
        )

        await self.volume_repo.create(volume, project_id)
        logger.info(
            "volume_summary.generated",
            project_id=project_id,
            volume_id=volume.volume_id,
            arcs=len(arcs),
            title=volume.volume_title,
        )
        return volume


# ---------------------------------------------------------------------------
# Legacy compatibility wrappers (deprecated, use classes directly)
# ---------------------------------------------------------------------------

async def generate_arc_summary(
    project_id: str,
    start_chapter: int,
    end_chapter: int,
) -> ArcSummary:
    """Legacy wrapper — delegates to :class:`ArcSummaryGenerator`."""
    return await ArcSummaryGenerator().generate(project_id, start_chapter, end_chapter)


async def generate_volume_summary(
    project_id: str,
    start_chapter: int,
    end_chapter: int,
) -> VolumeSummary:
    """Legacy wrapper — reads arcs from DB and delegates to :class:`VolumeSummaryGenerator`."""
    arcs = await ArcSummaryRepository().list_by_project(project_id)
    # Filter arcs that overlap with the requested range
    filtered = [
        a for a in arcs
        if a.start_chapter <= end_chapter and a.end_chapter >= start_chapter
    ]
    return await VolumeSummaryGenerator().generate(project_id, filtered)


async def auto_generate_arc_summaries(
    project_id: str,
    arc_boundaries: list[int] | None = None,
) -> list[ArcSummary]:
    """Legacy wrapper — auto-generate arcs using boundaries.

    Args:
        project_id: Project ID.
        arc_boundaries: Arc boundary list. If None, uses heuristic (10-chapter arcs).
    """
    from songyan.agents.arc_boundary_resolver import ArcBoundaryResolver
    from songyan.db.repository import ProjectRepository

    boundaries = arc_boundaries
    if boundaries is None:
        project = await ProjectRepository().get(project_id)
        if project and project.arc_boundaries:
            boundaries = project.arc_boundaries

    # Determine max chapter
    summary_repo = SummaryRepository()
    max_ch = await summary_repo.get_max_chapter_number(project_id)
    if max_ch == 0:
        logger.warning("auto_generate_arc_summaries.no_summaries", project_id=project_id)
        return []

    resolver = ArcBoundaryResolver()
    arc_ranges = resolver.list_boundaries(max_ch, boundaries)

    results: list[ArcSummary] = []
    generator = ArcSummaryGenerator()
    for start, end in arc_ranges:
        arc = await generator.generate(project_id, start, end)
        results.append(arc)

    return results
