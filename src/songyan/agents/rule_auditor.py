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
    PunchCheck,
    PunchPoint,
    RuleAuditResult,
)
from songyan.utils import (
    analyze_paragraph_rhythm,
    check_ending_hook,
    check_opening_hook,
    detect_ai_tells,
    detect_fatigue_words,
)
from songyan.utils.generic_names import detect_generic_names
from songyan.utils.numerical_validator import (
    NumericalContext,
)
from songyan.utils.word_count import count_chinese_words as _count_chinese_words

logger = structlog.get_logger(__name__)

WORD_COUNT_TOLERANCE = 0.10  # ±10%


# 简易情感词表（用于情绪转折检测）
_POSITIVE_WORDS = {
    "笑", "喜", "乐", "安", "静", "暖", "光", "希望", "胜利", "成功",
    "轻松", "愉快", "幸福", "满足", "信任", "勇敢", "坚定", "温柔",
}
_NEGATIVE_WORDS = {
    "恐", "惧", "怕", "悲", "痛", "死", "血", "暗", "冷", "绝望",
    "愤怒", "仇恨", "悲伤", "痛苦", "惊恐", "焦虑", "压抑", "窒息",
    "崩溃", "疯狂", "扭曲", "腐烂", "冰冷", "阴冷", "刺骨",
}


def _analyze_scene_emotion(text: str) -> str:
    """基于情感词频判断场景的 dominant emotion."""
    pos = sum(1 for w in _POSITIVE_WORDS if w in text)
    neg = sum(1 for w in _NEGATIVE_WORDS if w in text)
    if neg > pos:
        return "negative"
    if pos > neg:
        return "positive"
    return "neutral"


def _check_punch_points(
    content: str,
    punch_points: list[PunchPoint],
    word_count: int,
) -> PunchCheck:
    """检查刺激点执行情况和情绪转折密度."""
    # 按场景分割
    scene_pattern = re.compile(r"^###\s*Scene\s+\d+", re.MULTILINE)
    splits = list(scene_pattern.finditer(content))
    scenes: list[str] = []
    if not splits:
        scenes = [content]
    else:
        for i, m in enumerate(splits):
            start = m.end()
            end = splits[i + 1].start() if i + 1 < len(splits) else len(content)
            scenes.append(content[start:end])

    # 刺激点密度
    expected = len(punch_points)
    # 简化检查：只要 planned 了至少 1 个且 target_scene 在有效范围内就算通过
    # （严格的内容级检查留给 LLMAuditor 做语义判断）
    valid_targets = 0
    for p in punch_points:
        if 1 <= p.target_scene <= len(scenes):
            valid_targets += 1

    punch_density_ok = expected == 0 or valid_targets >= 1

    # 情绪转折检测
    scene_emotions = [_analyze_scene_emotion(s) for s in scenes]
    switch_count = 0
    for i in range(1, len(scene_emotions)):
        if scene_emotions[i] != scene_emotions[i - 1]:
            switch_count += 1

    # 每 1500 字至少 1 次情绪转折
    required_switches = max(1, word_count // 1500)
    emotion_switch_ok = switch_count >= required_switches or expected == 0

    issues: list[str] = []
    if expected > 0 and valid_targets < expected:
        issues.append(f"刺激点场景匹配不足：规划 {expected} 个，有效匹配 {valid_targets} 个")
    if expected > 0 and not emotion_switch_ok:
        issues.append(
            f"情绪转折不足：检测到 {switch_count} 次，要求至少 {required_switches} 次"
        )

    return PunchCheck(
        punch_count=valid_targets,
        expected_punch_count=expected,
        punch_density_ok=punch_density_ok,
        emotion_switch_count=switch_count,
        emotion_switch_ok=emotion_switch_ok,
        dominant_senses=[p.dominant_sense for p in punch_points if p.dominant_sense],
        issues=issues,
    )


def run_rule_audit(
    content: str,
    genre_rules: GenreRules | None = None,
    word_count_target: int = 3000,
    scene_count_target: int = 2,
    numerical_contexts: list[NumericalContext] | None = None,
    punch_points: list[PunchPoint] | None = None,
) -> RuleAuditResult:
    """运行规则检测（纯代码，无 LLM）.

    Args:
        content: 章节正文
        genre_rules: 题材规则（含 fatigue_words）
        word_count_target: 目标字数
        numerical_contexts: 数值上下文（玄幻题材用）
        punch_points: CreativeBrief 规划的刺激点（Punch Engine 用）

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
    word_count_ratio = round(word_count / word_count_target, 2) if word_count_target > 0 else 0.0

    # 6. 场景数量检测
    scene_count = len(re.findall(r"^###\s*Scene\s+\d+", content, re.MULTILINE))
    scene_count_ok = scene_count >= scene_count_target

    # 6. 数值公式验证（占位）
    numerical_issues: list[str] = []

    # 7. 通用角色名检测
    generic_name_matches = detect_generic_names(content)
    generic_name_count = len(generic_name_matches)

    # 8. 刺激度检查（Punch Engine）
    punch_check = _check_punch_points(content, punch_points or [], word_count)

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
        word_count_ratio=word_count_ratio,
        word_count_ok=word_count_ok,
        scene_count=scene_count,
        scene_count_target=scene_count_target,
        scene_count_ok=scene_count_ok,
        generic_name_matches=generic_name_matches,
        generic_name_count=generic_name_count,
        numerical_issues=numerical_issues,
        punch_check=punch_check,
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
        punch_density_ok=punch_check.punch_density_ok,
        emotion_switch_ok=punch_check.emotion_switch_ok,
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
        scene_count=result.scene_count,
        scene_count_ok=result.scene_count_ok,
        overall_score=_compute_overall_score(result),
        summary=_generate_summary(result),
    )

    await db.create(report, report_id, audit_type="rule")
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
    if not result.word_count_ok and result.word_count_target > 0:
        deviation = abs(result.word_count - result.word_count_target) / result.word_count_target
        score -= min(deviation * 5, 2.0)

    # 场景数不足扣分（硬约束）
    if not result.scene_count_ok:
        score -= 3.0

    # 通用角色名扣分：每个 -0.3，最多 -1.5
    score -= min(result.generic_name_count * 0.3, 1.5)

    # Punch Engine 扣分
    if result.punch_check.expected_punch_count > 0:
        if not result.punch_check.punch_density_ok:
            score -= 1.0
        if not result.punch_check.emotion_switch_ok:
            score -= 0.5

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
    if not result.scene_count_ok:
        parts.append(
            f"场景数不足：{result.scene_count} 个（要求至少 {result.scene_count_target} 个）"
        )
    if result.generic_name_count > 0:
        names = "、".join(m.name for m in result.generic_name_matches)
        parts.append(f"发现 {result.generic_name_count} 个通用角色名（{names}）")

    if result.punch_check.expected_punch_count > 0:
        if not result.punch_check.punch_density_ok:
            parts.append("刺激点密度不足")
        if not result.punch_check.emotion_switch_ok:
            parts.append("情绪转折不足")

    if not parts:
        return "规则检测通过，未发现明显问题。"
    return "；".join(parts) + "。"
