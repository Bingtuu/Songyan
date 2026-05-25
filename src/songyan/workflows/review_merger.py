"""ReviewMerger — 轻量合并 RuleAuditor + LLMAuditor 结果."""

from __future__ import annotations

import uuid

import structlog

from songyan.db.review_repo import ReviewReportRepository
from songyan.models import LLMAuditResult, MergedReviewReport, RuleAuditResult

logger = structlog.get_logger(__name__)


def _compute_overall_score(rule_result: RuleAuditResult, llm_result: LLMAuditResult) -> float:
    """计算综合评分（0-10）.

    权重分配：
    - LLM 维度评分平均：60%
    - Rule 指标（反向：AI腔越少越好）：40%
    """
    llm_score = 0.0
    if llm_result.dimension_scores:
        llm_score = sum(llm_result.dimension_scores.values()) / len(llm_result.dimension_scores)

    # Rule 指标：AI腔、疲劳词、段落节奏、钩子
    rule_penalty = 0.0
    if rule_result.ai_tell_count > 0:
        rule_penalty += min(rule_result.ai_tell_count * 0.5, 2.0)
    if rule_result.fatigue_word_count > 0:
        rule_penalty += min(rule_result.fatigue_word_count * 0.3, 1.5)
    if not rule_result.has_opening_hook:
        rule_penalty += 1.0
    if not rule_result.has_ending_hook:
        rule_penalty += 0.5
    if rule_result.paragraph_rhythm_score < 5.0:
        rule_penalty += (5.0 - rule_result.paragraph_rhythm_score) * 0.2

    rule_score = max(10.0 - rule_penalty, 0.0)

    return round(llm_score * 0.6 + rule_score * 0.4, 2)


def _merge_summary(rule_result: RuleAuditResult, llm_result: LLMAuditResult) -> str:
    """合并 Rule + LLM 的文本摘要."""
    parts: list[str] = []
    parts.append(f"综合评分: {_compute_overall_score(rule_result, llm_result)}/10")
    parts.append(
        f"AI腔: {rule_result.ai_tell_count}处 | "
        f"疲劳词: {rule_result.fatigue_word_count}处"
    )
    parts.append(f"首屏钩子: {'有' if rule_result.has_opening_hook else '无'}")
    parts.append(f"章末钩子: {'有' if rule_result.has_ending_hook else '无'}")
    if rule_result.word_count > 0:
        parts.append(f"字数: {rule_result.word_count}/{rule_result.word_count_target}")
    if llm_result.issues:
        critical = sum(1 for i in llm_result.issues if i.severity == "critical")
        major = sum(1 for i in llm_result.issues if i.severity == "major")
        minor = sum(1 for i in llm_result.issues if i.severity == "minor")
        parts.append(f"问题: {critical} critical, {major} major, {minor} minor")
    if llm_result.summary:
        parts.append(f"LLM总结: {llm_result.summary}")
    return " | ".join(parts)


async def merge_reviews(
    version_id: str,
    rule_result: RuleAuditResult,
    llm_result: LLMAuditResult,
    db: ReviewReportRepository,
    report_id: str | None = None,
) -> MergedReviewReport:
    """合并 RuleAuditor + LLMAuditor 结果，写入 review_reports 表.

    Args:
        version_id: 章节版本 ID
        rule_result: RuleAuditor 检测结果
        llm_result: LLMAuditor 语义审查结果
        db: ReviewReportRepository
        report_id: 可选报告 ID

    Returns:
        合并后的 MergedReviewReport
    """
    if report_id is None:
        report_id = f"mr-{version_id}-{uuid.uuid4().hex[:8]}"

    report = MergedReviewReport(
        chapter_version_id=version_id,
        rule_audit=rule_result,
        llm_audit=llm_result,
        issues=llm_result.issues,
        overall_score=_compute_overall_score(rule_result, llm_result),
        ai_tell_count=rule_result.ai_tell_count,
        fatigue_word_count=rule_result.fatigue_word_count,
        has_opening_hook=rule_result.has_opening_hook,
        has_ending_hook=rule_result.has_ending_hook,
        dimension_scores=llm_result.dimension_scores,
        summary=_merge_summary(rule_result, llm_result),
    )

    await db.create(report, report_id)
    logger.info(
        "review_merger.merged",
        report_id=report_id,
        version_id=version_id,
        overall_score=report.overall_score,
        issue_count=len(report.issues),
    )
    return report
