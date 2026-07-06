"""RuleAuditor Agent — 纯代码规则检测，复用 Quality Utils."""

from __future__ import annotations

import re
import time
import uuid
from difflib import SequenceMatcher
from typing import Any

import structlog

from songyan.db.review_repo import ReviewReportRepository
from songyan.models import (
    DuplicateParagraphMatch,
    GenreRules,
    MergedReviewReport,
    MetaTagLeakMatch,
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
from songyan.utils._helpers import locate_position, split_paragraphs
from songyan.utils.generic_names import detect_generic_names
from songyan.utils.numerical_validator import (
    NumericalContext,
)
from songyan.utils.truncation import word_count_bounds
from songyan.utils.word_count import count_chinese_words as _count_chinese_words

logger = structlog.get_logger(__name__)

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


_META_TAG_PATTERNS: list[tuple[str, str]] = [
    (r"(?s)<!--.*?-->", "HTML注释"),
    (r"(?s)<mark>.*?</mark>", "Mark标签"),
    (r"(?im)^\s*meta:.*", "Meta前缀"),
    (r"(?s)\[\[.*?\]\]", "旧式可见标记"),
]

_MARKDOWN_SCENE_PATTERNS: list[tuple[str, str]] = [
    (r"(?im)^\s*#{1,6}\s*Scene\s+(?:\d+|[A-Z]).*$", "Markdown场景标题"),
    (r"(?im)^\s*Scene\s+(?:\d+|[A-Z])(?:\s*[:：].*)?\s*$", "裸场景标题"),
    (r"(?im)^\s*\*\*Scene\s+(?:\d+|[A-Z])\*\*.*$", "加粗场景标题"),
    (r"(?im)^\s*#{1,6}\s*场景\s*(?:\d+|[A-Z]|[一二三四五六七八九十]+).*$", "Markdown中文场景标题"),
    (r"(?im)^\s*场景\s*(?:\d+|[A-Z]|[一二三四五六七八九十]+)(?:\s*[:：].*)?\s*$", "裸中文场景标题"),
    (r"(?im)^\s*\*\*场景\s*(?:\d+|[A-Z]|[一二三四五六七八九十]+)\*\*.*$", "加粗中文场景标题"),
]


def detect_meta_tag_leaks(text: str) -> list[MetaTagLeakMatch]:
    """检测元标记泄漏."""
    matches: list[MetaTagLeakMatch] = []
    seen: set[tuple[int, int]] = set()
    for pattern, tag_type in _META_TAG_PATTERNS:
        for m in re.finditer(pattern, text):
            key = (m.start(), m.end())
            if key in seen:
                continue
            seen.add(key)
            location = locate_position(text, m.start())
            matches.append(
                MetaTagLeakMatch(
                    pattern=f"{tag_type}: {pattern}",
                    matched_text=m.group(),
                    location=location,
                    severity="major",
                    message="检测到元标记泄漏",
                )
            )
    matches.sort(key=lambda x: text.find(x.matched_text))
    return matches


def detect_markdown_scene_titles(text: str) -> list[MetaTagLeakMatch]:
    """检测正文中的 Markdown / 裸场景标题."""
    matches: list[MetaTagLeakMatch] = []
    seen: set[tuple[int, int]] = set()
    for pattern, tag_type in _MARKDOWN_SCENE_PATTERNS:
        for m in re.finditer(pattern, text):
            key = (m.start(), m.end())
            if key in seen:
                continue
            seen.add(key)
            location = locate_position(text, m.start())
            matches.append(
                MetaTagLeakMatch(
                    pattern=f"{tag_type}: {pattern}",
                    matched_text=m.group(),
                    location=location,
                    severity="major",
                    message="检测到 Markdown 场景标题（应使用空行分隔场景）",
                )
            )
    matches.sort(key=lambda x: text.find(x.matched_text))
    return matches


def _normalize_paragraph_for_similarity(paragraph: str) -> str:
    """归一化段落空白，供重复检测计算相似度."""
    return re.sub(r"\s+", "", paragraph.strip())


def _paragraphs_with_offsets(text: str) -> list[tuple[int, str, int]]:
    """返回 1-based 段落序号、段落文本和起始偏移."""
    paragraphs = split_paragraphs(text)
    result: list[tuple[int, str, int]] = []
    cursor = 0
    for idx, paragraph in enumerate(paragraphs, 1):
        start = text.find(paragraph, cursor)
        if start < 0:
            start = text.find(paragraph)
        if start < 0:
            start = cursor
        result.append((idx, paragraph, start))
        cursor = start + len(paragraph)
    return result


def detect_duplicate_paragraphs(
    text: str,
    *,
    min_chars: int = 40,
    similarity_threshold: float = 0.9,
    long_paragraph_chars: int = 100,
    short_similarity_threshold: float = 0.95,
) -> list[DuplicateParagraphMatch]:
    """检出同章内重复长段落并定位（诊断项，不直接阻断）.

    分级阈值：归一化长度 >= long_paragraph_chars 的长段用 similarity_threshold；
    落在 [min_chars, long_paragraph_chars) 的中段改用更严的 short_similarity_threshold，
    只抓近乎逐字的重复。这样既能捕获 70-95 字的近似重复（170c Ch31 漏报），
    又不会误伤刻意的短句 refrain（< min_chars 直接跳过）。
    """
    matches: list[DuplicateParagraphMatch] = []
    seen: list[tuple[int, str, str, int]] = []

    for paragraph_index, paragraph, start in _paragraphs_with_offsets(text):
        normalized = _normalize_paragraph_for_similarity(paragraph)
        if len(normalized) < min_chars:
            continue

        for original_index, original, original_normalized, original_start in seen:
            similarity = (
                1.0
                if normalized == original_normalized
                else SequenceMatcher(None, original_normalized, normalized).ratio()
            )
            effective_threshold = (
                similarity_threshold
                if min(len(normalized), len(original_normalized)) >= long_paragraph_chars
                else short_similarity_threshold
            )
            if similarity < effective_threshold:
                continue
            matches.append(
                DuplicateParagraphMatch(
                    paragraph_index=paragraph_index,
                    duplicate_of_index=original_index,
                    matched_text=paragraph,
                    original_text=original,
                    location=locate_position(text, start),
                    original_location=locate_position(text, original_start),
                    similarity=round(similarity, 4),
                )
            )
            break

        seen.append((paragraph_index, paragraph, normalized, start))

    return matches


def _split_scenes(text: str) -> list[str]:
    """按空行（\n\n+）分割场景."""
    normalized = text.replace("\r\n", "\n")
    scenes = [block.strip() for block in re.split(r"\n\s*\n", normalized) if block.strip()]
    return scenes if scenes else [text.strip()] if text.strip() else []


def _short_paragraph_ratio(text: str, threshold: int = 50) -> float:
    """计算短段落（< threshold 字）占比."""
    paragraphs = split_paragraphs(text)
    if not paragraphs:
        return 0.0
    short_count = sum(1 for p in paragraphs if len(p) < threshold)
    return round(short_count / len(paragraphs), 3)


def _check_punch_points(
    content: str,
    punch_points: list[PunchPoint],
    word_count: int,
) -> PunchCheck:
    """检查刺激点执行情况和情绪转折密度."""
    # 按空行分割场景（与 Writer Prompt 1.1.0+ 一致）
    scenes = _split_scenes(content)
    if not scenes:
        scenes = [content] if content else []

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


def _check_mandatory_references(
    content: str,
    mandatory_references: list[dict] | None,
) -> tuple[bool, list[dict[str, Any]]]:
    """Task 138h: 检测正文中是否缺失 mandatory_reference 的提及.

    匹配策略：检查 setting_key 的最后一个 segment 或 setting_name
    是否在正文中出现（不区分中英文标点）。

    Returns:
        (passed, issues)
    """
    if not mandatory_references:
        return True, []

    issues: list[str] = []
    text = content.lower()
    for ref in mandatory_references:
        key = str(ref.get("setting_key") or "").lower()
        name = str(ref.get("setting_name") or "").lower()
        # 取 key 的最后一个 segment 作为别名（如 surface_material）
        key_alias = key.split(".")[-1] if key else ""

        found = False
        for candidate in (name, key_alias, key):
            if candidate and candidate in text:
                found = True
                break

        if not found:
            silent = ref.get("silent_chapters", 0)
            setting_name = ref.get("setting_name") or key or "未命名设定"
            issues.append(
                {
                    "setting_key": key or setting_name,
                    "setting_name": setting_name,
                    "silent_chapters": silent,
                    "message": f"强制连续性约束未回收：{setting_name}（已沉寂 {silent} 章）",
                }
            )

    return len(issues) == 0, issues


def run_rule_audit(
    content: str,
    genre_rules: GenreRules | None = None,
    word_count_target: int = 3000,
    chapter_type: str | None = None,
    scene_count_target: int = 2,
    numerical_contexts: list[NumericalContext] | None = None,
    punch_points: list[PunchPoint] | None = None,
    mandatory_references: list[dict] | None = None,
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
    lower_bound, upper_bound = word_count_bounds(word_count_target, chapter_type)
    word_count_ok = lower_bound <= word_count <= upper_bound
    word_count_ratio = round(word_count / word_count_target, 2) if word_count_target > 0 else 0.0

    # 6. 场景数量检测（按空行分割，与 Prompt 1.1.0+ 一致）
    scene_count = len(_split_scenes(content))
    scene_count_ok = scene_count >= scene_count_target

    # 7. 数值公式验证（占位）
    numerical_issues: list[str] = []

    # 8. 通用角色名检测
    generic_name_matches = detect_generic_names(content)
    generic_name_count = len(generic_name_matches)

    # 9. 元标记泄漏检测
    meta_tag_matches = detect_meta_tag_leaks(content)
    meta_tag_count = len(meta_tag_matches)

    # 10. Markdown 场景标题检测
    markdown_scene_title_matches = detect_markdown_scene_titles(content)
    markdown_scene_title_count = len(markdown_scene_title_matches)

    # 11. 重复长段落检测（观测指标，不直接阻断）
    duplicate_paragraph_matches = detect_duplicate_paragraphs(content)
    duplicate_paragraph_count = len(duplicate_paragraph_matches)

    # 12. 短段落比例（观测指标，不直接阻断）
    short_paragraph_ratio = _short_paragraph_ratio(content, threshold=50)

    # 13. 刺激度检查（Punch Engine）
    punch_check = _check_punch_points(content, punch_points or [], word_count)

    # 14. Task 138h: 强制连续性约束检查
    mr_passed, mr_issues = _check_mandatory_references(content, mandatory_references)

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
        meta_tag_matches=meta_tag_matches,
        meta_tag_count=meta_tag_count,
        markdown_scene_title_matches=markdown_scene_title_matches,
        markdown_scene_title_count=markdown_scene_title_count,
        duplicate_paragraph_matches=duplicate_paragraph_matches,
        duplicate_paragraph_count=duplicate_paragraph_count,
        short_paragraph_ratio=short_paragraph_ratio,
        numerical_issues=numerical_issues,
        punch_check=punch_check,
        mandatory_reference_issues=mr_issues,
        mandatory_reference_check_passed=mr_passed,
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
        mandatory_reference_check_passed=mr_passed,
        mandatory_reference_issue_count=len(mr_issues),
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

    # 元标记泄漏扣分：每个 -0.5，最多 -2
    score -= min(result.meta_tag_count * 0.5, 2.0)

    # Punch Engine 扣分
    if result.punch_check.expected_punch_count > 0:
        if not result.punch_check.punch_density_ok:
            score -= 1.0
        if not result.punch_check.emotion_switch_ok:
            score -= 0.5

    # Task 138h: 强制连续性约束扣分 — 每个缺失 -1.5，最多 -3
    if not result.mandatory_reference_check_passed:
        score -= min(len(result.mandatory_reference_issues) * 1.5, 3.0)

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
    if result.meta_tag_count > 0:
        parts.append(f"发现 {result.meta_tag_count} 处元标记泄漏")
    if result.markdown_scene_title_count > 0:
        parts.append(
            f"发现 {result.markdown_scene_title_count} 处 Markdown 场景标题（建议改为空行分隔）"
        )
    if result.duplicate_paragraph_count > 0:
        parts.append(f"发现 {result.duplicate_paragraph_count} 处重复长段落")
    if result.short_paragraph_ratio > 0.50:
        parts.append(
            f"短段落占比偏高（{result.short_paragraph_ratio:.0%}，建议控制 <50%）"
        )

    if result.punch_check.expected_punch_count > 0:
        if not result.punch_check.punch_density_ok:
            parts.append("刺激点密度不足")
        if not result.punch_check.emotion_switch_ok:
            parts.append("情绪转折不足")

    if not result.mandatory_reference_check_passed:
        parts.append(
            f"强制连续性约束未回收：{len(result.mandatory_reference_issues)} 项"
        )

    if not parts:
        return "规则检测通过，未发现明显问题。"
    return "；".join(parts) + "。"
