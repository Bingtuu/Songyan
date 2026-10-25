"""Score the five 霞飞路 roadmap classes. This does not write canon.

Recall for one class is interception by the read-only gate, or
non-occurrence in the new chapters. A missing chapter or a missing
occurrence judgment leaves that class unscored. Phrase absence is not
treated as non-occurrence.

On the live review path the gate receives no attribute extracts and no
claim anchors. Contradiction and typed mismatches therefore stay empty
unless this scorer is given those inputs. An unmentioned claim counts
toward T2 only when anchors were supplied. Without anchors, unmentioned
is the default for every claim whose text is not copied verbatim.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel, Field

from songyan.plan_checks.claim_check import ClaimAnchor
from songyan.plan_checks.gate import PlanFactGateReport, run_plan_fact_gate
from songyan.plan_checks.typed_attributes import AttributeExtract

Verdict = Literal["recalled", "miss", "unscored"]
BoardStatus = Literal["scored", "unscored", "blocked"]

_REQUIRED_CHAPTERS = (1, 2, 3)


class RoadmapClass(BaseModel):
    """One denominator class from the plan-first roadmap."""

    class_id: str
    label: str
    live_path_signal: str


ROADMAP_CLASSES: tuple[RoadmapClass, ...] = (
    RoadmapClass(
        class_id="T1",
        label="证物属性漂移",
        live_path_signal=(
            "第 2 章必须提及可以标出缺「右向左」。"
            "没有摘录时，方向和数量的类型化比较不会标出。"
        ),
    ),
    RoadmapClass(
        class_id="T5",
        label="证物归属漂移",
        live_path_signal=(
            "活路径标不出。归属不符要类型化摘录，"
            "主张矛盾要「横杆拓片」这类锚；两者都不在审查 state 里。"
        ),
    ),
    RoadmapClass(
        class_id="T4",
        label="机制方向",
        live_path_signal=(
            "第 3 章必须提及可以标出缺「往外拉」。"
            "没有摘录时，类型化方向不会标出。"
        ),
    ),
    RoadmapClass(
        class_id="T2",
        label="证据遗漏",
        live_path_signal=(
            "第 2 章必须提及可以标出缺「钝器伤」。"
            "没有主张锚时，主张「未提及」是缺省值，不算这一类的拦截。"
        ),
    ),
    RoadmapClass(
        class_id="T6",
        label="时代时间线",
        live_path_signal=(
            "第 1 章必须提及可以标出缺「九一八」。"
            "没有摘录时，时局时间锚的类型化比较不会标出。"
        ),
    ),
)


class ClassScore(BaseModel):
    """One class. ``recall`` stays null until both sides of the rule exist."""

    class_id: str
    label: str
    occurred: bool | None = None
    intercepted: bool | None = None
    recall: bool | None = None
    verdict: Verdict
    basis: str
    signals: list[str] = Field(default_factory=list)
    live_path_signal: str = ""


class RecallScoreboard(BaseModel):
    """Five class rows. ``recalled`` is null unless every row is scored."""

    status: BoardStatus
    recalled: int | None = None
    denominator: int = 5
    classes: list[ClassScore]
    anchors_supplied: bool = False
    extracts_supplied: bool = False
    reason: str = ""


def blocked_rerun_scoreboard(*, reason: str) -> RecallScoreboard:
    """Five unscored rows. Used when no new chapters were written."""
    return RecallScoreboard(
        status="blocked",
        recalled=None,
        classes=[
            ClassScore(
                class_id=spec.class_id,
                label=spec.label,
                verdict="unscored",
                basis="没有新章正文，不能判断这一类是拦截还是未发生。",
                live_path_signal=spec.live_path_signal,
            )
            for spec in ROADMAP_CLASSES
        ],
        reason=reason,
    )


def score_reports(
    reports: Mapping[int, PlanFactGateReport],
    occurred: Mapping[str, bool] | None,
    *,
    anchors_supplied: bool,
    extracts_supplied: bool,
) -> RecallScoreboard:
    """Apply the roadmap recall rule to gate reports and occurrence flags.

    ``occurred`` is a reader's judgment of the new prose. This function
    does not infer it from contradict phrases.
    """
    complete = all(chapter in reports for chapter in _REQUIRED_CHAPTERS)
    classes: list[ClassScore] = []
    for spec in ROADMAP_CLASSES:
        signals = _signals(spec.class_id, reports, anchors_supplied=anchors_supplied)
        intercepted = bool(signals) if complete else None
        occurrence = None if occurred is None else occurred.get(spec.class_id)
        verdict, recall, basis = _verdict(occurrence, intercepted, signals)
        classes.append(
            ClassScore(
                class_id=spec.class_id,
                label=spec.label,
                occurred=occurrence,
                intercepted=intercepted,
                recall=recall,
                verdict=verdict,
                basis=basis,
                signals=signals,
                live_path_signal=spec.live_path_signal,
            )
        )
    scored = all(row.verdict != "unscored" for row in classes)
    recalled = sum(1 for row in classes if row.recall) if scored else None
    if not complete:
        reason = "门报告缺第 1–3 章中的一章，召回不算。"
        status: BoardStatus = "unscored"
    elif occurred is None or any(row.occurred is None for row in classes):
        reason = "发生与否还没有人读正文填写。短语没出现不算未发生。"
        status = "unscored"
    else:
        reason = ""
        status = "scored"
    return RecallScoreboard(
        status=status,
        recalled=recalled,
        classes=classes,
        anchors_supplied=anchors_supplied,
        extracts_supplied=extracts_supplied,
        reason=reason,
    )


async def score_chapters(
    chapters: Mapping[int, str],
    *,
    project_id: str,
    extracts: list[AttributeExtract] | None = None,
    anchors: list[ClaimAnchor] | None = None,
    occurred: Mapping[str, bool] | None = None,
) -> RecallScoreboard:
    """Run the read-only gate on each chapter, then score the five classes.

    The caller loads approved cards first. This function does not write them.
    """
    reports: dict[int, PlanFactGateReport] = {}
    for chapter in sorted(chapters):
        reports[chapter] = await run_plan_fact_gate(
            project_id,
            chapter,
            chapters[chapter],
            extracts=extracts,
            anchors=anchors,
        )
    return score_reports(
        reports,
        occurred,
        anchors_supplied=anchors is not None,
        extracts_supplied=extracts is not None,
    )


def _verdict(
    occurred: bool | None,
    intercepted: bool | None,
    signals: list[str],
) -> tuple[Verdict, bool | None, str]:
    if occurred is None or intercepted is None:
        return "unscored", None, "这一类还不能记召回。"
    listed = "、".join(signals) if signals else ""
    if not occurred:
        if intercepted:
            return (
                "recalled",
                True,
                f"未发生，记为召回。门另有标记：{listed}。",
            )
        return "recalled", True, "未发生，记为召回。门没有标出这一类。"
    if intercepted:
        return "recalled", True, f"发生了，门标出：{listed}。"
    return "miss", False, "发生了，门没有标出。"


def _signals(
    class_id: str,
    reports: Mapping[int, PlanFactGateReport],
    *,
    anchors_supplied: bool,
) -> list[str]:
    if class_id == "T1":
        return _collect(
            _mention(reports, 2, "clue-scratch", "右向左"),
            _mismatch(reports, "xiafei-scratch", "direction"),
            _mismatch(reports, "xiafei-scratch", "count"),
            _contradicted(reports, "claim-ch2-scratch"),
        )
    if class_id == "T5":
        return _collect(
            _mismatch(reports, "xiafei-hook", "ownership"),
            _contradicted(reports, "claim-ch3-hook"),
        )
    if class_id == "T4":
        return _collect(
            _mention(reports, 3, "clue-mechanism", "往外拉"),
            _mismatch(reports, "xiafei-mechanism", "direction"),
            _contradicted(reports, "claim-ch3-pull"),
        )
    if class_id == "T2":
        signals = _collect(_mention(reports, 2, "clue-blunt", "钝器伤"))
        if anchors_supplied and _claim_status(reports, "claim-ch2-blunt") == "unmentioned":
            signals.append("主张 claim-ch2-blunt 为未提及")
        return signals
    if class_id == "T6":
        return _collect(
            _mention(reports, 1, "clue-era", "九一八"),
            _mismatch(reports, "xiafei-era", "time_anchor"),
            _contradicted(reports, "claim-ch1-era"),
        )
    raise ValueError(f"unknown roadmap class: {class_id}")


def _collect(*parts: str) -> list[str]:
    return [part for part in parts if part]


def _mention(
    reports: Mapping[int, PlanFactGateReport],
    chapter: int,
    point_id: str,
    term: str,
) -> str:
    report = reports.get(chapter)
    if report is None:
        return ""
    for row in report.missing_mentions:
        if row.point_id == point_id and term in row.missing_terms:
            return f"第 {chapter} 章必须提及缺「{term}」"
    return ""


def _mismatch(
    reports: Mapping[int, PlanFactGateReport],
    entity_id: str,
    key: str,
) -> str:
    for report in reports.values():
        for row in report.attribute_mismatches:
            if row.entity_id == entity_id and row.key == key:
                chapter = row.chapter if row.chapter is not None else report.chapter
                return (
                    f"第 {chapter} 章类型化 {entity_id}.{key} "
                    f"为「{row.extract_value}」，批准值是「{row.approved_value}」"
                )
    return ""


def _contradicted(reports: Mapping[int, PlanFactGateReport], claim_id: str) -> str:
    if _claim_status(reports, claim_id) == "contradicted":
        return f"主张 {claim_id} 为矛盾"
    return ""


def _claim_status(
    reports: Mapping[int, PlanFactGateReport],
    claim_id: str,
) -> str | None:
    for report in reports.values():
        for row in report.claim_verdicts:
            if row.claim_id == claim_id:
                return row.status
    return None
