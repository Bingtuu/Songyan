"""RuleAuditor Agent — 纯代码规则检测，复用 Quality Utils."""

from __future__ import annotations

import re
import time
import uuid

import structlog

from songyan.db.review_repo import ReviewReportRepository
from songyan.models import (
    GenreRules,
    MergedReviewReport,
    RuleAuditResult,
)
from songyan.utils import (
    analyze_paragraph_rhythm,
    check_ending_hook,
    check_opening_hook,
    detect_ai_tells,
    detect_fatigue_words,
)
from songyan.utils.numerical_validator import (
    NumericalContext,
)

logger = structlog.get_logger(__name__)

WORD_COUNT_TOLERANCE = 0.10  # ±10%


def _count_chinese_words(text: str) -> int:
    """统计中文字数（中文字符 + 连续英文/数字词）."""
    if not text:
        return 0
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    other_words = len(re.findall(r"[a-zA-Z0-9]+", text))
    return chinese_chars + other_words


async def run_rule_audit(
    content: str,
    genre_rules: GenreRules | None = None,
    word_count_target: int = 3000,
    numerical_contexts: list[NumericalContext] | None = None,
) -> RuleAuditResult:
    """运行规则检测（纯代码，无 LLM）.

    Args:
        content: 章节正文
        genre_rules: 题材规则（含 fatigue_words）
        word_count_target: 目标字数
        numerical_contexts: 数值上下文（玄幻题材用）

    Returns:
        RuleAuditResult
    """
    start_time = time.perf_counter()

    # 1. AI 腔检测
    ai_tell_matches = detect_ai_tells(content)
    ai_tell_count = len(ai_tell_matches)

    # 2. 疲劳词检测
    fatigue_words = genre_rules.fatigue_words if genre_rules else []
    fatigue_word_matches = detect_fatigue_words(content, fatigue_words)
    fatigue_word_count = sum(m.count for m in fatigue_word_matches)

    # 3. 钩子检测
    has_opening_hook = check_opening_hook(content)
    has_ending_hook = check_ending_hook(content)

    # 4. 段落节奏
    rhythm = analyze_paragraph_rhythm(content)
    paragraph_rhythm_score = rhythm.score
    rhythm_issues = rhythm.issues

    # 5. 字数统计
    word_count = _count_chinese_words(content)
    lower_bound = int(word_count_target * (1 - WORD_COUNT_TOLERANCE))
    upper_bound = int(word_count_target * (1 + WORD_COUNT_TOLERANCE))
    word_count_ok = lower_bound <= word_count <= upper_bound

    # 6. 数值公式验证（可选）
    numerical_issues: list[str] = []
    if numerical_contexts:
        # 注意：validate_numerical_update 需要 NumericalUpdate 对象
        # 这里简化处理：numerical_contexts 仅用于标记是否有数值上下文
        # 实际的数值验证由 SettlementExtractor 在后续处理
        for _ in numerical_contexts:
            # 占位：numerical_issues 在 SettlementExtractor 中填充
            pass

    duration_ms = int((time.perf_counter() - start_time) * 1000)

    result = RuleAuditResult(
        auditor_id="rule_auditor",
        ai_tell_matches=ai_tell_matches,
        ai_tell_count=ai_tell_count,
        fatigue_word_matches=fatigue_word_matches,
        fatigue_word_count=fatigue_word_count,
        has_opening_hook=has_opening_hook,
        has_ending_hook=has_ending_hook,
        paragraph_rhythm_score=paragraph_rhythm_score,
        rhythm_issues=rhythm_issues,
        word_count=word_count,
        word_count_target=word_count_target,
        word_count_ok=word_count_ok,
        numerical_issues=numerical_issues,
        duration_ms=duration_ms,
    )

    logger.info(
        "rule_auditor.done",
        ai_tell_count=ai_tell_count,
        fatigue_word_count=fatigue_word_count,
        has_opening_hook=has_opening_hook,
        has_ending_hook=has_ending_hook,
        rhythm_score=paragraph_rhythm_score,
        word_count=word_count,
        word_count_ok=word_count_ok,
        duration_ms=duration_ms,
    )
    return result


async def save_rule_audit(
    db: ReviewReportRepository,
    version_id: str,
    result: RuleAuditResult,
    report_id: str | None = None,
) -> None:
    """保存 RuleAuditResult 到 review_reports 表.

    Args:
        db: ReviewReportRepository
        version_id: 章节版本 ID
        result: RuleAuditResult
        report_id: 可选的报告 ID，自动生成
    """
    if report_id is None:
        report_id = f"ra-{version_id}-{uuid.uuid4().hex[:8]}"

    report = MergedReviewReport(
        chapter_version_id=version_id,
        rule_audit=result,
        ai_tell_count=result.ai_tell_count,
        fatigue_word_count=result.fatigue_word_count,
        has_opening_hook=result.has_opening_hook,
        has_ending_hook=result.has_ending_hook,
        overall_score=_compute_overall_score(result),
        summary=_generate_summary(result),
    )

    await db.create(report, report_id)
    logger.info(
        "rule_auditor.saved",
        report_id=report_id,
        version_id=version_id,
    )


def _compute_overall_score(result: RuleAuditResult) -> float:
    """计算综合评分（0-10）."""
    score = 10.0

    # AI 腔扣分：每个 -0.5，最多 -3
    score -= min(result.ai_tell_count * 0.5, 3.0)

    # 疲劳词扣分：每个 -0.3，最多 -2
    score -= min(result.fatigue_word_count * 0.3, 2.0)

    # 无首屏钩子 -1
    if not result.has_opening_hook:
        score -= 1.0

    # 无章末钩子 -1.5
    if not result.has_ending_hook:
        score -= 1.5

    # 段落节奏扣分：低于 5 分每差 1 分扣 0.3
    if result.paragraph_rhythm_score < 5.0:
        score -= (5.0 - result.paragraph_rhythm_score) * 0.3

    # 字数偏差扣分
    if not result.word_count_ok:
        deviation = abs(result.word_count - result.word_count_target) / result.word_count_target
        score -= min(deviation * 5, 2.0)

    return max(0.0, round(score, 1))


def _generate_summary(result: RuleAuditResult) -> str:
    """生成检测摘要."""
    parts: list[str] = []
    if result.ai_tell_count > 0:
        parts.append(f"发现 {result.ai_tell_count} 处 AI 腔")
    if result.fatigue_word_count > 0:
        parts.append(f"发现 {result.fatigue_word_count} 个疲劳词")
    if not result.has_opening_hook:
        parts.append("缺少首屏钩子")
    if not result.has_ending_hook:
        parts.append("缺少章末钩子")
    if result.paragraph_rhythm_score < 5.0:
        parts.append(f"段落节奏欠佳（{result.paragraph_rhythm_score:.1f}/10）")
    if not result.word_count_ok:
        parts.append(
            f"字数偏差：{result.word_count}/{result.word_count_target}"
        )

    if not parts:
        return "规则检测通过，未发现明显问题。"
    return "；".join(parts) + "。"
