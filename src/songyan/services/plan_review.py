"""V12 plan-only and deterministic plan review services."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from songyan.db.repository import ChapterGoalRepository
from songyan.db.review_repo import CreativeBriefRepository
from songyan.exceptions import SongyanError
from songyan.models import (
    ApprovedPlan,
    BeatSpec,
    ChapterGoal,
    CreativeBrief,
    PlanOnlyArtifact,
    PlanOnlyResult,
    PlanReviewFinding,
    PlanReviewResult,
    SupervisionSpec,
)
from songyan.workflows._nodes import creative_director_node, goal_planner_node

PlanNode = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


class PlanReviewError(SongyanError):
    """Plan-only or review-plan flow failed."""


_POLICY_PATTERNS: dict[str, tuple[str, re.Pattern[str]]] = {
    "past_backstory": (
        "规划包含旧事故、旧案、历史解释或回溯时间",
        re.compile(r"旧事故|旧案|历史事故|历史记录|两年前|三年前|过去\s*[一二三四五六七八九十两\d]*\s*年"),
    ),
    "cross_location_chase": (
        "规划包含跨区追踪、坐标或外部地点推进",
        re.compile(r"跨区|追踪到|前往|坐标|经纬度|D区|储物柜|\d{1,3}\.\d+,\s*\d{1,3}\.\d+"),
    ),
    "identity_secret_reveal": (
        "规划提前揭示身份秘密、账号或权限",
        re.compile(r"身份秘密|货舱身份|对象身份|自然人身份|自然人|账号|权限秘密|沈弥账号|系统底层配置"),
    ),
    "relative_time": (
        "规划包含相对时间或未来时间",
        re.compile(r"昨天|前天|明天|[一二三四五六七八九十两\d]+\s*年前|未来\s*第?\s*\d+\s*分钟"),
    ),
    "coordinates": (
        "规划包含坐标或经纬度",
        re.compile(r"坐标|经纬度|\d{1,3}\.\d+,\s*\d{1,3}\.\d+"),
    ),
}

_NEW_CHARACTER_PATTERN = re.compile(r"新角色|陌生人|陈屿|阮星河")


async def run_plan_only(
    *,
    project_id: str,
    chapters: list[int],
    mode_id: str | None = None,
    previous_summary_by_chapter: dict[int, str] | None = None,
    goal_node: PlanNode = goal_planner_node,
    director_node: PlanNode = creative_director_node,
) -> PlanOnlyResult:
    """Run only GoalPlanner and CreativeDirector for a chapter range.

    The reused workflow nodes write ``chapter_goals`` and ``creative_briefs``.
    They do not create ``chapter_versions`` and do not enter Writer.
    """
    artifacts: list[PlanOnlyArtifact] = []
    previous_summary_by_chapter = previous_summary_by_chapter or {}
    for chapter_number in chapters:
        state: dict[str, Any] = {
            "project_id": project_id,
            "chapter_number": chapter_number,
            "previous_summary": previous_summary_by_chapter.get(chapter_number, ""),
        }
        if mode_id:
            state["mode_id"] = mode_id

        planned = await goal_node(state)
        if planned.get("error"):
            msg = f"plan-only goal planner failed for Ch{chapter_number}: {planned['error']}"
            raise PlanReviewError(msg)
        goal_id = planned.get("chapter_goal_id")
        if not isinstance(goal_id, str) or not goal_id:
            msg = f"plan-only goal planner did not return chapter_goal_id for Ch{chapter_number}"
            raise PlanReviewError(msg)

        state.update(planned)
        directed = await director_node(state)
        if directed.get("error"):
            msg = (
                f"plan-only creative director failed for Ch{chapter_number}: "
                f"{directed['error']}"
            )
            raise PlanReviewError(msg)
        brief_id = directed.get("creative_brief_id")
        if not isinstance(brief_id, str) or not brief_id:
            msg = (
                "plan-only creative director did not return creative_brief_id "
                f"for Ch{chapter_number}"
            )
            raise PlanReviewError(msg)

        artifacts.append(
            PlanOnlyArtifact(
                project_id=project_id,
                chapter_number=chapter_number,
                chapter_goal_id=goal_id,
                creative_brief_id=brief_id,
            )
        )

    return PlanOnlyResult(project_id=project_id, artifacts=artifacts)


async def review_plan_only_result(
    result: PlanOnlyResult,
    spec: SupervisionSpec,
) -> PlanReviewResult:
    """Load plan artifacts from SQLite and review them against a supervision spec."""
    findings: list[PlanReviewFinding] = []
    goal_repo = ChapterGoalRepository()
    brief_repo = CreativeBriefRepository()
    for artifact in result.artifacts:
        goal = await goal_repo.get(artifact.chapter_goal_id)
        if goal is None:
            findings.append(
                PlanReviewFinding(
                    chapter_number=artifact.chapter_number,
                    code="missing_chapter_goal",
                    message="plan-only artifact references a missing ChapterGoal",
                    evidence=artifact.chapter_goal_id,
                )
            )
            continue

        brief = await brief_repo.get(artifact.creative_brief_id)
        if brief is None:
            findings.append(
                PlanReviewFinding(
                    chapter_number=artifact.chapter_number,
                    code="missing_creative_brief",
                    message="plan-only artifact references a missing CreativeBrief",
                    evidence=artifact.creative_brief_id,
                )
            )
            continue

        findings.extend(review_plan_documents(goal=goal, brief=brief, spec=spec))

    return PlanReviewResult(
        project_id=result.project_id,
        artifacts=list(result.artifacts),
        findings=findings,
    )


def review_plan_documents(
    *,
    goal: ChapterGoal,
    brief: CreativeBrief,
    spec: SupervisionSpec,
) -> list[PlanReviewFinding]:
    """Review one ChapterGoal + CreativeBrief pair without calling LLM."""
    chapter_number = goal.chapter_number
    try:
        chapter_spec = spec.chapter(chapter_number)
    except KeyError:
        return [
            PlanReviewFinding(
                chapter_number=chapter_number,
                code="missing_chapter_spec",
                message="supervision spec does not define this chapter",
                evidence=str(chapter_number),
            )
        ]

    findings: list[PlanReviewFinding] = []
    if not chapter_spec.allowed_beats:
        findings.append(
            PlanReviewFinding(
                chapter_number=chapter_number,
                code="missing_beat_sheet",
                message="supervision spec has no allowed beats for this chapter",
            )
        )

    plan_text = _plan_text(goal, brief)
    for literal in chapter_spec.forbidden_literals:
        start = 0
        while True:
            pos = plan_text.find(literal, start)
            if pos < 0:
                break
            if not _is_negated_policy_match(plan_text, pos, pos + len(literal)):
                findings.append(
                    PlanReviewFinding(
                        chapter_number=chapter_number,
                        code="forbidden_literal",
                        message=f"plan contains forbidden literal: {literal}",
                        evidence=_evidence_at(plan_text, pos, pos + len(literal)),
                    )
                )
                break
            start = pos + len(literal)

    for pattern in chapter_spec.forbidden_patterns:
        compiled = re.compile(pattern)
        for match in compiled.finditer(plan_text):
            if _is_negated_policy_match(plan_text, match.start(), match.end()):
                continue
            findings.append(
                PlanReviewFinding(
                    chapter_number=chapter_number,
                    code="forbidden_pattern",
                    message=f"plan contains forbidden pattern: {pattern}",
                    evidence=_evidence_at(plan_text, match.start(), match.end()),
                )
            )
            break

    policy = chapter_spec.stage_policy
    if not policy.allow_new_characters:
        match = _NEW_CHARACTER_PATTERN.search(plan_text)
        if match and not _is_negated_policy_match(plan_text, match.start(), match.end()):
            findings.append(
                PlanReviewFinding(
                    chapter_number=chapter_number,
                    code="new_character",
                    message="plan appears to introduce a new character",
                    evidence=_evidence(plan_text, match.group(0)),
                )
            )
    _add_policy_finding(
        findings,
        chapter_number,
        plan_text,
        enabled=not policy.allow_past_backstory,
        code="past_backstory",
    )
    _add_policy_finding(
        findings,
        chapter_number,
        plan_text,
        enabled=not policy.allow_cross_location_chase,
        code="cross_location_chase",
    )
    _add_policy_finding(
        findings,
        chapter_number,
        plan_text,
        enabled=not policy.allow_identity_secret_reveal,
        code="identity_secret_reveal",
    )
    _add_policy_finding(
        findings,
        chapter_number,
        plan_text,
        enabled=not policy.allow_relative_time,
        code="relative_time",
    )
    _add_policy_finding(
        findings,
        chapter_number,
        plan_text,
        enabled=not policy.allow_coordinates,
        code="coordinates",
    )

    return findings


def approve_plan_review(
    review: PlanReviewResult,
    *,
    approved_by: str = "deterministic-review",
) -> ApprovedPlan:
    """Create an approval marker from a passing review result."""
    if not review.passed:
        msg = "cannot approve a rejected plan review"
        raise PlanReviewError(msg)
    return ApprovedPlan(
        project_id=review.project_id,
        chapters=[artifact.chapter_number for artifact in review.artifacts],
        artifact_token=plan_artifact_token(review.artifacts),
        approved_by=approved_by,
    )


def ensure_plan_approved(result: PlanOnlyResult, approval: ApprovedPlan | None) -> None:
    """Raise if a plan-only result has no matching approval marker."""
    if approval is None:
        msg = "plan review approval is required before Writer"
        raise PlanReviewError(msg)
    if approval.project_id != result.project_id:
        msg = "plan approval project_id does not match plan-only result"
        raise PlanReviewError(msg)
    if approval.chapters != result.chapters:
        msg = "plan approval chapters do not match plan-only result"
        raise PlanReviewError(msg)
    if approval.artifact_token != plan_artifact_token(result.artifacts):
        msg = "plan approval token does not match plan-only artifacts"
        raise PlanReviewError(msg)


def approved_beat_sheet_for_writer(
    *,
    result: PlanOnlyResult,
    approval: ApprovedPlan | None,
    spec: SupervisionSpec,
    chapter_number: int,
) -> list[BeatSpec]:
    """Return Writer beats only after plan approval is verified."""
    ensure_plan_approved(result, approval)
    return spec.beat_sheet_for_chapter(chapter_number)


def save_approved_plan(path: str | Path, approval: ApprovedPlan) -> None:
    """Persist an approval marker as JSON."""
    approval_path = Path(path)
    approval_path.parent.mkdir(parents=True, exist_ok=True)
    approval_path.write_text(
        approval.model_dump_json(indent=2),
        encoding="utf-8",
    )


def load_approved_plan(path: str | Path) -> ApprovedPlan:
    """Load an approval marker from JSON."""
    approval_path = Path(path)
    try:
        data = json.loads(approval_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        msg = f"approved plan marker does not exist: {approval_path}"
        raise PlanReviewError(msg) from exc
    except json.JSONDecodeError as exc:
        msg = f"approved plan marker is not valid JSON: {exc}"
        raise PlanReviewError(msg) from exc
    if not isinstance(data, dict):
        msg = "approved plan marker must be a JSON object"
        raise PlanReviewError(msg)
    return ApprovedPlan.model_validate(data)


def plan_artifact_token(artifacts: list[PlanOnlyArtifact]) -> str:
    """Return a stable hash for an ordered list of plan artifacts."""
    payload = [
        artifact.model_dump(mode="json")
        for artifact in sorted(artifacts, key=lambda item: item.chapter_number)
    ]
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _add_policy_finding(
    findings: list[PlanReviewFinding],
    chapter_number: int,
    plan_text: str,
    *,
    enabled: bool,
    code: str,
) -> None:
    if not enabled:
        return
    message, pattern = _POLICY_PATTERNS[code]
    match = pattern.search(plan_text)
    if not match:
        return
    if _is_negated_policy_match(plan_text, match.start(), match.end()):
        return
    findings.append(
        PlanReviewFinding(
            chapter_number=chapter_number,
            code=code,
            message=message,
            evidence=_evidence(plan_text, match.group(0)),
        )
    )


def _plan_text(goal: ChapterGoal, brief: CreativeBrief) -> str:
    parts: list[str] = []

    def add(value: Any) -> None:
        if value is None:
            return
        if isinstance(value, str):
            parts.append(value)
            return
        if isinstance(value, dict):
            for item in value.values():
                add(item)
            return
        if isinstance(value, list | tuple | set):
            for item in value:
                add(item)
            return
        if hasattr(value, "model_dump"):
            add(value.model_dump(mode="json"))
            return
        parts.append(str(value))

    add(goal.model_dump(mode="json"))
    add(brief.model_dump(mode="json"))
    return "\n".join(parts)


def _evidence(text: str, needle: str) -> str:
    pos = text.find(needle)
    if pos < 0:
        return needle
    return _evidence_at(text, pos, pos + len(needle))


def _evidence_at(text: str, start_pos: int, end_pos: int) -> str:
    start = max(0, start_pos - 40)
    end = min(len(text), end_pos + 40)
    return text[start:end].replace("\n", " ").strip()


def _is_negated_policy_match(text: str, start: int, end: int) -> bool:
    """Return whether a policy keyword appears inside a negative instruction."""
    window = text[max(0, start - 16): min(len(text), end + 16)]
    negation_markers = (
        "不提前揭示",
        "不揭示",
        "不展开",
        "不使用",
        "不引入",
        "不是",
        "并非",
        "避免",
        "禁止",
        "不得",
        "无需",
    )
    return any(marker in window for marker in negation_markers)
