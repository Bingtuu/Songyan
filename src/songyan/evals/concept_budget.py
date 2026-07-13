"""Concept budget constraints for planning (Task 163).

MVP scope:
- derive a lightweight concept ledger from setting_tracking;
- detect conceptual_grounding decline from literary observations;
- build a planning-side constraint string for CreativeDirector;
- render diagnostics for metrics.

This module does not modify content, does not create workflow nodes, and does
not gate chapter acceptance.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from songyan.db.continuity_repo import SettingTrackingRepository
from songyan.db.review_repo import LiteraryObservationRepository

_TERMINAL_GROUNDED_STATUSES = {"resolved"}
_IGNORED_STATUSES = {"archived", "abandoned"}


class ConceptLedgerEntry(BaseModel):
    """MVP concept ledger entry."""

    concept_key: str
    concept_name: str
    introduced_chapter: int
    grounded: bool
    last_referenced_chapter: int | None = None
    status: str = "active"
    category: str = "background"


class ConceptualGroundingPoint(BaseModel):
    chapter: int
    conceptual_grounding_score: float


class ConceptBudgetReport(BaseModel):
    current_chapter: int
    max_new_concepts: int
    tighten: bool
    total_concepts: int
    ungrounded_count: int
    ungrounded_entries: list[ConceptLedgerEntry]
    grounding_points: list[ConceptualGroundingPoint]
    constraint_text: str = ""


def build_concept_ledger_from_rows(
    rows: list[dict[str, Any]],
    *,
    current_chapter: int | None = None,
) -> list[ConceptLedgerEntry]:
    """Build concept ledger entries from setting_tracking rows."""
    entries: list[ConceptLedgerEntry] = []
    for row in rows:
        status = str(row.get("status") or "active")
        if status in _IGNORED_STATUSES:
            continue
        introduced = int(row.get("introduced_in_chapter") or 0)
        if current_chapter is not None and introduced > current_chapter:
            continue
        key = str(row.get("setting_key") or "").strip()
        if not key:
            continue
        last = row.get("last_mentioned_chapter")
        last_chapter = int(last) if last is not None else None
        grounded = status in _TERMINAL_GROUNDED_STATUSES or (
            last_chapter is not None and last_chapter > introduced
        )
        entries.append(
            ConceptLedgerEntry(
                concept_key=key,
                concept_name=str(row.get("setting_name") or key),
                introduced_chapter=introduced,
                grounded=grounded,
                last_referenced_chapter=last_chapter,
                status=status,
                category=str(row.get("category") or "background"),
            )
        )
    entries.sort(
        key=lambda item: (
            item.grounded,
            item.last_referenced_chapter or item.introduced_chapter,
            item.introduced_chapter,
            item.concept_key,
        )
    )
    return entries


async def collect_concept_ledger(
    project_id: str,
    current_chapter: int,
    repo: SettingTrackingRepository | None = None,
) -> list[ConceptLedgerEntry]:
    """Collect concept ledger from setting_tracking up to current_chapter."""
    repo = repo or SettingTrackingRepository()
    rows = await repo.list_by_project(project_id)
    return build_concept_ledger_from_rows(rows, current_chapter=current_chapter)


async def collect_conceptual_grounding_points(
    project_id: str,
    start: int,
    end: int,
    repo: LiteraryObservationRepository | None = None,
) -> list[ConceptualGroundingPoint]:
    """Collect conceptual_grounding scores by chapter."""
    if end < start:
        return []
    repo = repo or LiteraryObservationRepository()
    rows = await repo.list_scores_by_chapter_range(project_id, start, end)
    points = [
        ConceptualGroundingPoint(
            chapter=int(row["chapter"]),
            conceptual_grounding_score=float(row["conceptual_grounding_score"] or 0.0),
        )
        for row in rows
    ]
    points.sort(key=lambda item: item.chapter)
    return points


def detect_conceptual_grounding_tighten(
    points: list[ConceptualGroundingPoint],
    *,
    baseline_n: int = 10,
    window: int = 5,
    drop: float = 0.20,
) -> bool:
    """Return True when conceptual_grounding has dropped enough to tighten budget."""
    ordered = sorted(points, key=lambda item: item.chapter)
    if len(ordered) < baseline_n:
        return False
    series = [point.conceptual_grounding_score for point in ordered]
    baseline = sum(series[:baseline_n]) / baseline_n
    threshold = baseline * (1 - drop)
    if len(series) < window:
        return False
    for idx in range(len(series) - window + 1):
        window_mean = sum(series[idx: idx + window]) / window
        if window_mean <= threshold:
            return True
    return False


def _effective_max_new_concepts(max_new_concepts: int, tighten: bool) -> int:
    if tighten:
        return max(0, min(max_new_concepts, 1))
    return max(0, max_new_concepts)


def build_concept_budget_constraint_from_ledger(
    entries: list[ConceptLedgerEntry],
    *,
    max_new_concepts: int = 2,
    tighten: bool = False,
    ungrounded_limit: int = 5,
) -> str:
    """Build planning-side concept budget constraint text from a ledger."""
    effective_max = _effective_max_new_concepts(max_new_concepts, tighten)
    ungrounded = [entry for entry in entries if not entry.grounded]
    if not entries and not tighten:
        return ""

    lines = [
        "## 概念预算约束（Task 163）",
        f"- 本章新概念/新机构/新术语引入上限：{effective_max} 个。",
        "- 优先落地、复用、剧情化已引入概念；非必要不造新概念。",
        "- 如确需引入新概念，必须用【设定推导】说明它从哪个既有设定自然推出。",
    ]
    if tighten:
        lines.append(
            "- conceptual_grounding 滑窗下滑已触发收紧：本章优先让旧概念通过行动/冲突落地。"
        )
    if ungrounded:
        lines.append("- 本章优先落地以下未落地概念：")
        for entry in ungrounded[:ungrounded_limit]:
            last = entry.last_referenced_chapter or entry.introduced_chapter
            lines.append(
                f"  - {entry.concept_name}（{entry.concept_key}，"
                f"引入 Ch{entry.introduced_chapter}，最近 Ch{last}）"
            )
    return "\n".join(lines)


async def build_concept_budget_constraint(
    project_id: str,
    chapter_no: int,
    *,
    max_new_concepts: int = 2,
) -> str:
    """Generate planning-side concept budget constraint for CreativeDirector."""
    current_chapter = max(0, chapter_no - 1)
    entries = await collect_concept_ledger(project_id, current_chapter)
    points = await collect_conceptual_grounding_points(project_id, 1, current_chapter)
    tighten = detect_conceptual_grounding_tighten(points)
    return build_concept_budget_constraint_from_ledger(
        entries,
        max_new_concepts=max_new_concepts,
        tighten=tighten,
    )


async def collect_concept_budget_report(
    project_id: str,
    current_chapter: int,
    *,
    max_new_concepts: int = 2,
) -> ConceptBudgetReport:
    """Collect concept budget diagnostic report."""
    entries = await collect_concept_ledger(project_id, current_chapter)
    points = await collect_conceptual_grounding_points(project_id, 1, current_chapter)
    tighten = detect_conceptual_grounding_tighten(points)
    ungrounded = [entry for entry in entries if not entry.grounded]
    constraint = build_concept_budget_constraint_from_ledger(
        entries,
        max_new_concepts=max_new_concepts,
        tighten=tighten,
    )
    return ConceptBudgetReport(
        current_chapter=current_chapter,
        max_new_concepts=_effective_max_new_concepts(max_new_concepts, tighten),
        tighten=tighten,
        total_concepts=len(entries),
        ungrounded_count=len(ungrounded),
        ungrounded_entries=ungrounded,
        grounding_points=points,
        constraint_text=constraint,
    )


def render_concept_budget_section(report: ConceptBudgetReport | None) -> str:
    """Render concept budget diagnostics for metrics/report output."""
    lines = ["## 概念预算诊断（Task 163，规划侧约束；不自动改写）", ""]
    if report is None or report.total_concepts == 0:
        lines.append("（无概念台账：尚无 setting_tracking 记录，规划侧回退旧行为）")
        return "\n".join(lines)

    tighten = "是" if report.tighten else "否"
    lines.append(
        f"- 概念总数 **{report.total_concepts}**；未落地 **{report.ungrounded_count}**；"
        f"本章新概念预算 **{report.max_new_concepts}**；触发收紧：**{tighten}**。"
    )
    if not report.ungrounded_entries:
        lines.append("- ✓ 当前无未落地概念。")
        return "\n".join(lines)

    lines.append("")
    lines.append("| 概念 | key | 引入章 | 最近提及 | 状态 | 类别 |")
    lines.append("|------|-----|--------|----------|------|------|")
    for entry in report.ungrounded_entries[:20]:
        last = entry.last_referenced_chapter if entry.last_referenced_chapter is not None else "-"
        lines.append(
            f"| {entry.concept_name} | {entry.concept_key} | "
            f"{entry.introduced_chapter} | {last} | {entry.status} | {entry.category} |"
        )
    return "\n".join(lines)
