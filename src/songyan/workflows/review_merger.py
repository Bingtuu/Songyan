"""ReviewMerger — 轻量合并 RuleAuditor + LLMAuditor 结果."""

from __future__ import annotations

import uuid

import structlog

from songyan.db.review_repo import ReviewReportRepository
from songyan.models import (
    LLMAuditResult,
    MergedReviewReport,
    ReviewCategory,
    ReviewIssue,
    RuleAuditResult,
)

logger = structlog.get_logger(__name__)

# P1: 认知豁免 — 认知动词列表
_COGNITIVE_PHRASES: tuple[str, ...] = (
    "理解了",
    "意识到",
    "得出结论",
    "他知道",
    "他看到了",
    "结论很清晰",
    "这意味着",
    "不是巧合",
    "必须有一个",
    "然后他理解了",
    "他理解了",
    "林渊知道",
    "林渊理解了",
    "林渊意识到",
)

# P1: 动作支撑关键词（简单判断 evidence 附近是否有动作描写）
_ACTION_KEYWORDS: tuple[str, ...] = (
    "盯",
    "握",
    "退",
    "站",
    "滑",
    "按",
    "收",
    "抬",
    "转",
    "走",
    "坐",
    "靠",
    "摸",
    "指",
    "看",
    "望",
    "低",
    "挤",
    "僵",
    "垂",
    "起身",
    "后退",
    "前倾",
    "侧头",
    "收紧",
    "泛白",
    "颤抖",
    "停顿",
)


def _apply_cognitive_exemption(content: str, issues: list[ReviewIssue]) -> list[ReviewIssue]:
    """P1: show_dont_tell 认知豁免.

    第三人称限知视角中，认知动词若伴随动作支撑，降级为 minor。
    """
    for issue in issues:
        if issue.severity != "major" or issue.category != ReviewCategory.SHOW_DONT_TELL:
            continue
        text = (issue.issue_description or "") + (issue.evidence_quote or "")
        if not any(p in text for p in _COGNITIVE_PHRASES):
            continue
        eq = issue.evidence_quote or ""
        idx = content.find(eq)
        if idx < 0:
            continue
        surrounding = content[max(0, idx - 100) : idx + len(eq) + 100]
        if any(a in surrounding for a in _ACTION_KEYWORDS):
            issue.severity = "minor"
            logger.info(
                "review_merger.cognitive_exemption",
                issue_id=issue.issue_id,
                evidence_quote=eq[:60],
            )
    return issues


def _detect_auditor_conflicts(
    current_issues: list[ReviewIssue],
    previous_issues: list[ReviewIssue] | None,
) -> list[ReviewIssue]:
    """P0: 审查矛盾检测 — dialogue_distinctness 长短矛盾降级.

    若同一角色在连续修订轮次中，dialogue_distinctness 同时出现
    '太长' 和 '太短' 判定，视为审者标准矛盾，降级为 minor。
    """
    if not previous_issues:
        return current_issues

    prev_dialogue = [
        i
        for i in previous_issues
        if i.category == ReviewCategory.DIALOGUE_DISTINCTNESS
        and i.severity in ("critical", "major")
    ]
    if not prev_dialogue:
        return current_issues

    prev_desc = " ".join(i.issue_description or "" for i in prev_dialogue)
    prev_has_long = "长" in prev_desc
    prev_has_short = "短" in prev_desc

    for issue in current_issues:
        if issue.category != ReviewCategory.DIALOGUE_DISTINCTNESS:
            continue
        if issue.severity not in ("critical", "major"):
            continue
        curr_desc = issue.issue_description or ""
        curr_has_long = "长" in curr_desc
        curr_has_short = "短" in curr_desc
        if (prev_has_long and curr_has_short) or (prev_has_short and curr_has_long):
            issue.severity = "minor"
            logger.info(
                "review_merger.auditor_conflict_resolved",
                issue_id=issue.issue_id,
                category=issue.category,
                prev_desc=prev_desc[:80],
                curr_desc=curr_desc[:80],
            )
    return current_issues


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
        f"AI腔: {rule_result.ai_tell_count}处 | 疲劳词: {rule_result.fatigue_word_count}处"
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


def _convert_rule_to_issues(
    content: str,
    rule_result: RuleAuditResult,
    version_id: str,
) -> list[ReviewIssue]:
    """将 RuleAuditor 严重问题转化为 ReviewIssue.

    只转化 severity >= major 的问题，上限 5 个，避免 RevisionHandler 过载。
    evidence_quote 尽量从正文中提取实际文本片段，便于 LLM 定位。
    """
    issues: list[ReviewIssue] = []
    issue_counter = 0

    def _next_id() -> str:
        nonlocal issue_counter
        issue_counter += 1
        return f"rule-{version_id}-{issue_counter:03d}"

    def _clamp(text: str, max_len: int = 200) -> str:
        if len(text) <= max_len:
            return text
        return text[:max_len] + "..."

    # 1. 章末钩子缺失 (critical)
    if not rule_result.has_ending_hook:
        ending_snippet = _clamp(content[-200:]) if content else ""
        issues.append(
            ReviewIssue(
                issue_id=_next_id(),
                category=ReviewCategory.NARRATIVE_HOOK,
                severity="critical",
                evidence_quote=ending_snippet,
                evidence_location="章节末尾",
                issue_description=(
                    "缺少章末钩子 — 当前章节结尾没有设置悬念或转折，"
                    "读者缺乏继续阅读的动力。"
                ),
                expected="结尾处应有悬念、冲突升级、新发现或情感冲击，迫使读者点击下一章。",
                actual="结尾平淡收束，没有留下未解之谜或强烈的情感张力。",
                suggested_fix="在结尾最后1-2段添加一个钩子：可以是新危机的征兆、角色发现的秘密、未预期的访客、或主角面临的艰难抉择。",
                fix_type="patch",
                confidence=1.0,
            )
        )

    # 2. 首屏钩子缺失 (critical)
    if not rule_result.has_opening_hook:
        opening_snippet = _clamp(content[:200]) if content else ""
        issues.append(
            ReviewIssue(
                issue_id=_next_id(),
                category=ReviewCategory.NARRATIVE_HOOK,
                severity="critical",
                evidence_quote=opening_snippet,
                evidence_location="章节开头",
                issue_description=(
                    "缺少首屏钩子 — 章节开头没有在第一段建立悬念或冲突，"
                    "读者容易流失。"
                ),
                expected="首段应直接切入动作、冲突、悬念或强烈情绪，避免铺垫和解释。",
                actual="开头缺乏即时的叙事张力，可能以描述、解释或平淡的日常开场。",
                suggested_fix="重写开头首段，以动作、对话、冲突或悬念切入；删除开头的背景铺垫。",
                fix_type="patch",
                confidence=1.0,
            )
        )

    # 3. AI腔集中 (major) — 取前2处
    if rule_result.ai_tell_count >= 2:
        for idx, match in enumerate(rule_result.ai_tell_matches[:2]):
            issues.append(
                ReviewIssue(
                    issue_id=_next_id(),
                    category=ReviewCategory.SHOW_DONT_TELL,
                    severity="major",
                    evidence_quote=match.matched_text,
                    evidence_location=match.location or f"第{idx + 1}处AI腔",
                    issue_description=(
                        f"AI腔命中（模式: {match.pattern}）— "
                        "使用了过于抽象、概括或模型化的叙述方式，"
                        "缺乏具体的感官细节和角色视角。"
                    ),
                    expected="通过角色的感官体验、动作反应和具体细节来展示情绪与状态，而非直接告诉读者。",
                    actual=f'原文直接陈述: "{match.matched_text}"',
                    suggested_fix="改写成具体场景：用动作、表情、环境反应、身体感受替代抽象描述。保持角色视角。",
                    fix_type="patch",
                    confidence=0.95,
                )
            )

    # 4. 疲劳词爆发 (major) — 取前3处
    if rule_result.fatigue_word_count >= 3:
        for idx, match in enumerate(rule_result.fatigue_word_matches[:3]):
            loc = match.locations[0] if match.locations else f"第{idx + 1}处"
            issues.append(
                ReviewIssue(
                    issue_id=_next_id(),
                    category=ReviewCategory.DESCRIPTION_SENSORY,
                    severity="major",
                    evidence_quote=match.word,
                    evidence_location=loc,
                    issue_description=(
                        f'疲劳词爆发 — "{match.word}" 累计出现 {match.count} 次，'
                        "造成阅读疲劳和词汇单调感。"
                    ),
                    expected="同一概念或情绪应使用多样的表达，轮换词汇、比喻和感官通道。",
                    actual=f'"{match.word}" 重复出现，缺乏语言变化。',
                    suggested_fix=(
                        f'将部分 "{match.word}" 替换为同义词、比喻或具体描写；'
                        "如果无法替换，删除冗余 occurrence。"
                    ),
                    fix_type="patch",
                    confidence=0.9,
                )
            )

    # 5. 字数严重超标 (major) — > 120% 目标字数（Task 056：从 130% 收紧到 120%）
    if rule_result.word_count_target > 0:
        excess_ratio = rule_result.word_count / rule_result.word_count_target
        if excess_ratio >= 1.2:
            excess_percent = round((excess_ratio - 1) * 100)
            issues.append(
                ReviewIssue(
                    issue_id=_next_id(),
                    category=ReviewCategory.NARRATIVE_PACING,
                    severity="major",
                    evidence_quote=(
                        f"实际字数 {rule_result.word_count}，"
                        f"目标 {rule_result.word_count_target}，超标 {excess_percent}%"
                    ),
                    evidence_location="全章",
                    issue_description=(
                        f"字数严重超标 — 章节长度超出目标 {excess_percent}%，"
                        "可能导致节奏拖沓、读者疲劳。"
                    ),
                    expected=(
                        f"控制在目标字数 ±10% 范围内"
                        f"（约 {rule_result.word_count_target} 字）。"
                    ),
                    actual=f"实际 {rule_result.word_count} 字，超出 {excess_percent}%。",
                    suggested_fix="删减冗余描写、重复对话、过度内心独白；压缩过渡场景；保留核心冲突和关键情节。",
                    fix_type="patch",
                    confidence=1.0,
                )
            )

    # 6. 段落节奏差 (major) — score < 4.0
    if rule_result.paragraph_rhythm_score < 4.0 and rule_result.rhythm_issues:
        issues.append(
            ReviewIssue(
                issue_id=_next_id(),
                category=ReviewCategory.NARRATIVE_PACING,
                severity="major",
                evidence_quote="; ".join(rule_result.rhythm_issues[:3]),
                evidence_location="全章段落结构",
                issue_description=(
                    f"段落节奏欠佳（评分 {rule_result.paragraph_rhythm_score:.1f}/10）— "
                    "段落长度分布失衡，影响阅读呼吸感。"
                ),
                expected="段落长度应有变化：短句制造紧张，中长段落推进叙事，避免连续超长段落或过度碎片化。",
                actual="; ".join(rule_result.rhythm_issues[:3]),
                suggested_fix="拆分过长的叙述段落；在关键动作处使用短句/短段；合并过度碎片化的单句段落。",
                fix_type="patch",
                confidence=0.85,
            )
        )

    # 7. 场景结构问题 (Task 095)
    if rule_result.scene_count == 1:
        issues.append(
            ReviewIssue(
                issue_id=_next_id(),
                category=ReviewCategory.NARRATIVE_PACING,
                severity="major",
                evidence_quote=f"当前仅 {rule_result.scene_count} 个场景",
                evidence_location="全章结构",
                issue_description="章节仅有 1 个场景，叙事节奏可能过于集中，缺乏层次感和节奏变化。",
                expected="章节应包含至少 2 个场景，通过场景切换推进叙事、调节节奏。",
                actual=f"当前仅 {rule_result.scene_count} 个场景。",
                suggested_fix="将长场景拆分为 2-3 个场景：在情节转折点插入场景分隔，增加叙事层次。",
                fix_type="rewrite_scene",
                confidence=0.95,
            )
        )
    elif rule_result.scene_count >= 5:
        issues.append(
            ReviewIssue(
                issue_id=_next_id(),
                category=ReviewCategory.NARRATIVE_PACING,
                severity="minor",
                evidence_quote=f"当前共 {rule_result.scene_count} 个场景",
                evidence_location="全章结构",
                issue_description=(
                    f"章节场景数过多（{rule_result.scene_count} 个），"
                    "可能导致叙事碎片化，读者难以沉浸。"
                ),
                expected="每章 2-4 个场景为宜，每个场景应有独立的情节推进功能。",
                actual=f"当前共 {rule_result.scene_count} 个场景。",
                suggested_fix="合并关联度高的短场景，将次要过渡内容压缩为段落。",
                fix_type="patch",
                confidence=0.8,
            )
        )

    # 上限保护
    max_rule_issues = 5
    if len(issues) > max_rule_issues:
        issues = issues[:max_rule_issues]
        logger.warning(
            "review_merger.rule_issues_capped",
            version_id=version_id,
            total_found=len(issues) + (1 if len(issues) > max_rule_issues else 0),
            cap=max_rule_issues,
        )

    return issues


async def merge_reviews(
    version_id: str,
    content: str,
    rule_result: RuleAuditResult,
    llm_result: LLMAuditResult,
    db: ReviewReportRepository,
    report_id: str | None = None,
    previous_new_issues: list[ReviewIssue] | None = None,
    previous_all_issues: list[ReviewIssue] | None = None,
) -> MergedReviewReport:
    """合并 RuleAuditor + LLMAuditor 结果，写入 review_reports 表.

    Args:
        version_id: 章节版本 ID
        content: 章节正文（用于提取规则问题的 evidence_quote）
        rule_result: RuleAuditor 检测结果
        llm_result: LLMAuditor 语义审查结果
        db: ReviewReportRepository
        report_id: 可选报告 ID
        previous_new_issues: 058d — 上一轮 revision 引入的新问题
        previous_all_issues: 前一轮全部 issues（用于审查矛盾检测）

    Returns:
        合并后的 MergedReviewReport
    """
    if report_id is None:
        report_id = f"mr-{version_id}-{uuid.uuid4().hex[:8]}"

    # P1: 认知豁免 + P0: 审查矛盾检测（在 ScoreAggregator 之前净化）
    llm_result.issues = _apply_cognitive_exemption(content, llm_result.issues)
    llm_result.issues = _detect_auditor_conflicts(llm_result.issues, previous_all_issues)

    # 将 RuleAuditor 严重问题转化为 ReviewIssue
    rule_issues = _convert_rule_to_issues(content, rule_result, version_id)
    all_issues = list(llm_result.issues) + rule_issues
    # 058d: 合并上一轮 revision 引入的新问题
    if previous_new_issues:
        all_issues.extend(previous_new_issues)

    report = MergedReviewReport(
        chapter_version_id=version_id,
        rule_audit=rule_result,
        llm_audit=llm_result,
        issues=all_issues,
        overall_score=_compute_overall_score(rule_result, llm_result),
        ai_tell_count=rule_result.ai_tell_count,
        fatigue_word_count=rule_result.fatigue_word_count,
        has_opening_hook=rule_result.has_opening_hook,
        has_ending_hook=rule_result.has_ending_hook,
        scene_count=rule_result.scene_count,
        scene_count_ok=rule_result.scene_count_ok,
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
        rule_issues=len(rule_issues),
        llm_issues=len(llm_result.issues),
    )
    return report
