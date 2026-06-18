"""LLMAuditor Agent — LLM 语义审查，覆盖 12 个维度."""

from __future__ import annotations

import time
import uuid
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
from songyan.utils.token_estimator import truncate_to_tokens

logger = structlog.get_logger(__name__)

MAX_CONTENT_TOKENS = 4000  # 正文 Token 上限，超出时截断（保守估计）
VALID_SEVERITIES = {"critical", "major", "minor", "info"}
VALID_FIX_TYPES = {"patch", "rewrite_scene", "confirm", "register_setting"}
DEFAULT_DIMENSIONS = [c.value for c in ReviewCategory]


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
            if cs.current_location:
                info += f"（位置：{cs.current_location}）"
            if cs.current_cultivation:
                info += f"（修为：{cs.current_cultivation}）"
            if cs.active_relationships:
                info += f"（关系：{'，'.join(cs.active_relationships)}）"
            if cs.unresolved_issues:
                info += f"（目标：{'，'.join(cs.unresolved_issues)}）"
            char_lines.append(info)
        lines.append(f"**出场角色**：{'；'.join(char_lines)}")

    # Task 074: 注入对话风格卡供审查使用
    if ctx.dialogue_style_cards:
        lines.append("")
        lines.append("**角色对话风格指纹（Writer 必须遵循）**：")
        for dsc in ctx.dialogue_style_cards:
            style_parts = []
            if dsc.common_openers:
                style_parts.append(f"口头禅：{'/'.join(dsc.common_openers)}")
            style_parts.append(f"句式：{dsc.sentence_length_preference}")
            if dsc.anger_expression:
                style_parts.append(f"愤怒模式：{dsc.anger_expression}")
            if dsc.pause_habit:
                style_parts.append(f"停顿：{dsc.pause_habit}")
            lines.append(f"- {dsc.character_id}: {'；'.join(style_parts)}")

    if ctx.recent_plot.last_chapter_ending:
        lines.append(f"**上一章结尾**：{ctx.recent_plot.last_chapter_ending}")

    return "\n".join(lines)


def _render_prompt(content: str, context_package: ContextPackage | None) -> str:
    """渲染 LLMAuditor Prompt."""
    from songyan.prompts import get_prompt_loader

    loader = get_prompt_loader()
    card = loader.load_card("llm_auditor")
    context_info = _render_context_info(context_package)

    # 按 Token 预算截断正文
    content = truncate_to_tokens(content, MAX_CONTENT_TOKENS)

    rendered = loader.render_card(card, {
        "context_info": context_info,
        "content": content,
    })
    return rendered.full_prompt


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

    severity = _validate_severity(data.get("severity", "minor"))
    evidence_quote = str(data.get("evidence_quote", "") or "")
    if severity in {"critical", "major"} and not evidence_quote.strip():
        logger.warning(
            "llm_auditor.missing_evidence_quote",
            issue_id=issue_id,
            severity=severity,
            category=category,
        )
        return None

    return ReviewIssue(
        issue_id=issue_id,
        category=category,  # type: ignore[arg-type]
        severity=severity,  # type: ignore[arg-type]
        evidence_quote=evidence_quote,
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

    await db.create(report, report_id, audit_type="llm")
    logger.info(
        "llm_auditor.saved",
        report_id=report_id,
        version_id=version_id,
    )


def _compress_review_history(
    reviews: list[LLMAuditResult],
    max_issues_per_round: int = 3,
    max_total_length: int = 1500,
) -> str:
    """将多轮 review 压缩为摘要，控制 token 增长.

    策略：
    1. 只保留最近 2 轮 review
    2. 每轮只保留 top issues（critical/major 优先）
    3. 去重：相同 category + evidence_quote 的 issue 只保留一次
    4. 输出格式为结构化文本，便于 LLMAuditor prompt 引用

    Args:
        reviews: 多轮 LLMAuditResult（按时间顺序）
        max_issues_per_round: 每轮保留的最大 issue 数
        max_total_length: 压缩后总字符数上限

    Returns:
        压缩后的 review 摘要文本
    """
    if not reviews:
        return ""

    # 只保留最近 2 轮
    recent = reviews[-2:]

    lines: list[str] = []
    seen_issues: set[str] = set()  # 去重键：category + evidence_quote[:30]

    for i, result in enumerate(recent, 1):
        round_label = f"第{i}轮审查" if len(recent) > 1 else "上一轮审查"
        lines.append(f"=== {round_label} ===")

        # 按 severity 排序，优先 critical/major
        sorted_issues = sorted(
            result.issues,
            key=lambda issue: (
                0 if issue.severity == "critical" else 1 if issue.severity == "major" else 2
            ),
        )

        kept = 0
        for issue in sorted_issues:
            # 去重键：category + description 前 40 字符（evidence_quote 可能在多轮中略有变化）
            dedup_key = f"{issue.category}:{issue.issue_description[:40]}"
            if dedup_key in seen_issues:
                continue
            seen_issues.add(dedup_key)

            lines.append(
                f"- [{issue.severity}] {issue.category}: {issue.issue_description[:80]}"
            )
            kept += 1
            if kept >= max_issues_per_round:
                break

        # 添加维度评分摘要（如果有多轮）
        if result.dimension_scores:
            low_dims = [
                f"{dim}={score:.1f}"
                for dim, score in result.dimension_scores.items()
                if score < 6.0
            ]
            if low_dims:
                lines.append(f"  低分维度：{'，'.join(low_dims)}")

    compressed = "\n".join(lines)

    # 截断到上限
    if len(compressed) > max_total_length:
        compressed = compressed[:max_total_length]
        # 尝试在最后一个完整行截断
        last_newline = compressed.rfind("\n")
        if last_newline > max_total_length * 0.8:
            compressed = compressed[:last_newline]
        compressed += "\n...（已截断）"

    return compressed


def _compute_overall_score(result: LLMAuditResult) -> float:
    """计算综合评分（0-10）."""
    if result.dimension_scores:
        avg_dim = sum(result.dimension_scores.values()) / len(result.dimension_scores)
    else:
        avg_dim = 5.0

    # 文学性维度加权
    # cliche_risk_score 和 conceptual_idling_score 是「风险/空转」指标，
    # 越高越差，因此用 (10 - score) 转化为正向得分。
    literary = (
        (10 - result.cliche_risk_score) * 0.3
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
