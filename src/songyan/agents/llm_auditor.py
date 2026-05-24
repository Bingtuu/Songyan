"""LLMAuditor Agent — LLM 语义审查，覆盖 12 个维度."""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any

import structlog

from songyan.db.review_repo import ReviewReportRepository
from songyan.llm.client import call_llm
from songyan.llm.parsing import parse_llm_response
from songyan.models import (
    ContextPackage,
    LLMAuditResult,
    MergedReviewReport,
    ReviewCategory,
    ReviewIssue,
)

logger = structlog.get_logger(__name__)

MAX_CONTENT_LENGTH = 8000  # 正文长度上限，超出时截断
VALID_SEVERITIES = {"critical", "major", "minor", "info"}
VALID_FIX_TYPES = {"patch", "rewrite_scene", "confirm", "register_setting"}
DEFAULT_DIMENSIONS = [c.value for c in ReviewCategory]


def _load_prompt_template() -> str:
    """加载 LLMAuditor Prompt 模板."""
    template_path = Path(__file__).parents[3] / "prompts" / "llm_auditor.md"
    if template_path.exists():
        return template_path.read_text(encoding="utf-8")
    return (
        "审查以下章节正文，从 12 个维度评估质量。"
        "输出 JSON：issues + dimension_scores + cliche_risk_score + "
        "character_autonomy_score + conceptual_idling_score + summary"
    )


def _render_context_info(ctx: ContextPackage | None) -> str:
    """将 ContextPackage 渲染为上下文信息文本."""
    if ctx is None:
        return "（无额外上下文）"

    lines: list[str] = []

    goal = ctx.chapter_goal
    lines.append(f"**章节目标**：第{goal.chapter_number}章，类型：{goal.chapter_type}")
    if goal.target_events:
        lines.append(f"**目标事件**：{'；'.join(goal.target_events)}")
    if goal.emotional_arc:
        lines.append(f"**情感弧线**：{goal.emotional_arc}")

    if ctx.creative_brief:
        brief = ctx.creative_brief
        lines.append(f"**创作意图**：{brief.creative_intent}")
        if brief.forbidden_patterns:
            lines.append(f"**禁忌**：{'；'.join(brief.forbidden_patterns)}")

    if ctx.character_states:
        char_lines = []
        for cs in ctx.character_states:
            info = f"{cs.name}"
            if cs.emotional_state:
                info += f"（情绪：{cs.emotional_state}）"
            char_lines.append(info)
        lines.append(f"**出场角色**：{'；'.join(char_lines)}")

    if ctx.recent_plot.last_chapter_ending:
        lines.append(f"**上一章结尾**：{ctx.recent_plot.last_chapter_ending}")

    return "\n".join(lines)


def _render_prompt(content: str, context_package: ContextPackage | None) -> str:
    """渲染 LLMAuditor Prompt."""
    template = _load_prompt_template()
    context_info = _render_context_info(context_package)

    # 截断过长的正文
    if len(content) > MAX_CONTENT_LENGTH:
        content = content[:MAX_CONTENT_LENGTH] + "\n...（正文已截断）"

    prompt = template.replace("{{ context_info }}", context_info)
    prompt = prompt.replace("{{ content }}", content)
    return prompt


def _validate_category(value: str) -> str | None:
    """验证 category 是否有效，无效时返回 None."""
    try:
        ReviewCategory(value)
        return value
    except ValueError:
        logger.warning("llm_auditor.invalid_category", category=value)
        return None


def _validate_severity(value: str) -> str:
    """验证 severity，无效时回退到 'minor'."""
    if value in VALID_SEVERITIES:
        return value
    logger.warning("llm_auditor.invalid_severity", severity=value)
    return "minor"


def _validate_fix_type(value: str) -> str:
    """验证 fix_type，无效时回退到 'patch'."""
    if value in VALID_FIX_TYPES:
        return value
    logger.warning("llm_auditor.invalid_fix_type", fix_type=value)
    return "patch"


def _build_issue(data: dict[str, Any], index: int) -> ReviewIssue | None:
    """从字典构建 ReviewIssue，无效时返回 None."""
    category = _validate_category(data.get("category", ""))
    if category is None:
        return None

    issue_id = data.get("issue_id", f"issue_{index:03d}")
    if not issue_id:
        issue_id = f"issue_{index:03d}"

    return ReviewIssue(
        issue_id=issue_id,
        category=category,  # type: ignore[arg-type]
        severity=_validate_severity(data.get("severity", "minor")),  # type: ignore[arg-type]
        evidence_quote=data.get("evidence_quote", ""),
        evidence_location=data.get("evidence_location", ""),
        issue_description=data.get("issue_description", ""),
        expected=data.get("expected"),
        actual=data.get("actual"),
        suggested_fix=data.get("suggested_fix"),
        fix_type=_validate_fix_type(data.get("fix_type", "patch")),  # type: ignore[arg-type]
        confidence=float(data.get("confidence", 1.0)),
    )


def _build_llm_audit_result(data: dict[str, Any]) -> LLMAuditResult:
    """从解析后的字典构建 LLMAuditResult."""
    # 解析 issues
    issues: list[ReviewIssue] = []
    for i, item in enumerate(data.get("issues", [])):
        if isinstance(item, dict):
            issue = _build_issue(item, i)
            if issue is not None:
                issues.append(issue)

    # 解析 dimension_scores
    raw_scores = data.get("dimension_scores", {})
    dimension_scores: dict[str, float] = {}
    for dim in DEFAULT_DIMENSIONS:
        if dim in raw_scores:
            try:
                score = float(raw_scores[dim])
                dimension_scores[dim] = max(0.0, min(10.0, score))
            except (TypeError, ValueError):
                logger.warning("llm_auditor.invalid_score", dimension=dim, value=raw_scores[dim])

    # 文学性评分
    def _parse_score(key: str) -> float:
        try:
            return max(0.0, min(10.0, float(data.get(key, 0.0))))
        except (TypeError, ValueError):
            return 0.0

    return LLMAuditResult(
        auditor_id="llm_auditor",
        issues=issues,
        dimension_scores=dimension_scores,
        cliche_risk_score=_parse_score("cliche_risk_score"),
        character_autonomy_score=_parse_score("character_autonomy_score"),
        conceptual_idling_score=_parse_score("conceptual_idling_score"),
        summary=data.get("summary", ""),
    )


# ---------------------------------------------------------------------------
# Main Entry
# ---------------------------------------------------------------------------
async def run_llm_audit(
    content: str,
    context_package: ContextPackage | None = None,
    temperature: float = 0.3,
) -> LLMAuditResult:
    """运行 LLM 语义审查.

    Args:
        content: 章节正文
        context_package: 上下文包（提供角色状态、剧情背景等）
        temperature: LLM 温度（默认 0.3，要求稳定输出）

    Returns:
        LLMAuditResult
    """
    start_time = time.perf_counter()

    prompt = _render_prompt(content, context_package)
    llm_response = await call_llm(prompt, temperature=temperature)

    data = parse_llm_response(llm_response)
    result = _build_llm_audit_result(data)

    duration_ms = int((time.perf_counter() - start_time) * 1000)
    result.duration_ms = duration_ms

    logger.info(
        "llm_auditor.done",
        issues_count=len(result.issues),
        dimensions_scored=len(result.dimension_scores),
        cliche_risk=result.cliche_risk_score,
        duration_ms=duration_ms,
    )
    return result


async def save_llm_audit(
    db: ReviewReportRepository,
    version_id: str,
    result: LLMAuditResult,
    report_id: str | None = None,
) -> None:
    """保存 LLMAuditResult 到 review_reports 表.

    Args:
        db: ReviewReportRepository
        version_id: 章节版本 ID
        result: LLMAuditResult
        report_id: 可选的报告 ID，自动生成
    """
    if report_id is None:
        report_id = f"la-{version_id}-{uuid.uuid4().hex[:8]}"

    report = MergedReviewReport(
        chapter_version_id=version_id,
        llm_audit=result,
        issues=result.issues,
        dimension_scores=result.dimension_scores,
        overall_score=_compute_overall_score(result),
        summary=result.summary,
    )

    await db.create(report, report_id)
    logger.info(
        "llm_auditor.saved",
        report_id=report_id,
        version_id=version_id,
    )


def _compute_overall_score(result: LLMAuditResult) -> float:
    """计算综合评分（0-10）."""
    if result.dimension_scores:
        avg_dim = sum(result.dimension_scores.values()) / len(result.dimension_scores)
    else:
        avg_dim = 5.0

    # 文学性维度加权
    literary = (
        result.cliche_risk_score * 0.3
        + result.character_autonomy_score * 0.4
        + (10 - result.conceptual_idling_score) * 0.3
    )

    score = avg_dim * 0.7 + literary * 0.3

    # critical/major 问题扣分
    critical_major = sum(
        1 for i in result.issues if i.severity in ("critical", "major")
    )
    score -= min(critical_major * 0.5, 3.0)

    return max(0.0, round(score, 1))
