"""RevisionHandler Agent — issue-driven patch 修订，不整章重写."""

from __future__ import annotations

import re
import time
import uuid
from typing import Any

import structlog

from songyan.db.repository import ChapterHeadRepository, ChapterVersionRepository
from songyan.llm.client import call_llm
from songyan.llm.parsing import parse_llm_response
from songyan.models import (
    ChapterHead,
    ChapterVersion,
    LiteraryAuditResult,
    MergedReviewReport,
    Patch,
    ReviewCategory,
    ReviewIssue,
    RevisionOutput,
    RuleAuditResult,
)
from songyan.utils.token_estimator import truncate_to_tokens

from ._diff import (
    _difflib_fuzzy_search as _difflib_fuzzy_search,
)
from ._diff import (
    _paragraph_fallback_search as _paragraph_fallback_search,
)
from ._patch_engine import (
    _apply_patches,
    _determine_issues_fixed,
)
from ._patch_engine import (
    _find_text_span as _find_text_span,
)
from ._segmented_revision import run_segmented_revision

logger = structlog.get_logger(__name__)

MAX_CONTENT_TOKENS = 6000
_MAX_PREVIOUS_EVIDENCE_CHARS = 1000
MIN_CONTENT_RATIO = 0.85  # 修订后字数不得低于原文 85% (Task 100a)


def _load_prompt_template() -> str:
    """加载 RevisionHandler Prompt 模板 — 已迁移到工艺卡系统."""
    from songyan.prompts import get_prompt_loader
    return get_prompt_loader().load_card("revision_handler").system_prompt


def filter_patchable_issues(report: MergedReviewReport) -> list[ReviewIssue]:
    """仅保留有证据、fix_type=patch、允许自动修复的 critical/major issue."""
    return [
        issue
        for issue in report.issues
        if issue.severity in ("critical", "major")
        and issue.fix_type == "patch"
        and bool(issue.evidence_quote.strip())
    ]


def _filter_scene_split_issues(report: MergedReviewReport) -> list[ReviewIssue]:
    """保留 fix_type=scene_split 的 major issue，用于结构拆分路径."""
    return [
        issue
        for issue in report.issues
        if issue.severity in ("critical", "major")
        and issue.fix_type == "scene_split"
        and bool(issue.evidence_quote.strip())
    ]


def _filter_patchable_issues(report: MergedReviewReport) -> list[ReviewIssue]:
    """兼容旧测试与内部调用的别名."""
    return filter_patchable_issues(report)


def _readability_metrics_from_report(
    report: MergedReviewReport,
) -> dict[str, Any]:
    """从 report 提取 readability 指标，用于渲染 readability 专精 prompt."""
    rule_audit = report.rule_audit or RuleAuditResult()
    return {
        "ai_tell_count": rule_audit.ai_tell_count,
        "fatigue_word_count": rule_audit.fatigue_word_count,
        "paragraph_rhythm_score": getattr(rule_audit, "paragraph_rhythm_score", 5.0),
    }


def _readability_driven(
    report: MergedReviewReport,
    score_card: dict[str, Any] | None,
) -> bool:
    """判断是否需要进入 readability 专精修订路径.

    Task 128c: 当 score_card 标记 readability_ok=False，或 report 中可读性指标
    明显异常时，使用 readability 专精 prompt 和 issues。
    """
    if score_card is not None:
        flags = score_card.get("flags") or {}
        if flags.get("readability_ok") is False:
            return True

    rule_audit = report.rule_audit
    if rule_audit is None:
        return False

    # 即使没有 readability_ok 标志，只要指标明显异常也进入专精路径
    if rule_audit.ai_tell_count >= 2:
        return True
    if rule_audit.fatigue_word_count >= 5:
        return True
    rhythm_score = getattr(rule_audit, "paragraph_rhythm_score", 5.0)
    if rhythm_score < 4.0:
        return True
    return False


def _build_readability_issues(
    report: MergedReviewReport,
) -> list[ReviewIssue]:
    """从 rule_audit 构造 readability-focused issues.

    当原有 patchable issues 不足或 readability 未达标时，补充具体修复指令。
    """
    issues: list[ReviewIssue] = []
    rule_audit = report.rule_audit
    if rule_audit is None:
        return issues

    # AI 腔 — 取前 2 处
    if rule_audit.ai_tell_count > 0:
        for idx, match in enumerate(rule_audit.ai_tell_matches[:2]):
            issues.append(
                ReviewIssue(
                    issue_id=f"rh-ai-{idx}",
                    category=ReviewCategory.SHOW_DONT_TELL,
                    severity="major",
                    evidence_quote=match.matched_text,
                    evidence_location=match.location or f"第{idx + 1}处AI腔",
                    issue_description=(
                        f"AI腔命中（模式: {match.pattern}）— 需要改为展示而非讲述。"
                    ),
                    expected="通过动作、感官细节、环境反应展示情绪与状态。",
                    actual=f'原文直接陈述: "{match.matched_text}"',
                    suggested_fix="改写成具体场景：用动作、表情、身体感受替代抽象描述。",
                    fix_type="patch",
                    confidence=0.95,
                )
            )

    # 疲劳词 — 取前 3 处
    if rule_audit.fatigue_word_count > 0:
        for idx, match in enumerate(rule_audit.fatigue_word_matches[:3]):
            loc = match.locations[0] if match.locations else f"第{idx + 1}处"
            issues.append(
                ReviewIssue(
                    issue_id=f"rh-fatigue-{idx}",
                    category=ReviewCategory.DESCRIPTION_SENSORY,
                    severity="major",
                    evidence_quote=match.word,
                    evidence_location=loc,
                    issue_description=(
                        f'疲劳词 — "{match.word}" 累计出现 {match.count} 次。'
                    ),
                    expected="同一概念使用多样表达，轮换词汇、比喻和感官通道。",
                    actual=f'"{match.word}" 重复出现。',
                    suggested_fix=(
                        f'将部分 "{match.word}" 替换为同义词、比喻或具体描写；'
                        "无法替换时删除冗余 occurrence。"
                    ),
                    fix_type="patch",
                    confidence=0.9,
                )
            )

    # 段落节奏
    rhythm_score = getattr(rule_audit, "paragraph_rhythm_score", 5.0)
    if rhythm_score < 5.0 and rule_audit.rhythm_issues:
        issues.append(
            ReviewIssue(
                issue_id="rh-rhythm-0",
                category=ReviewCategory.NARRATIVE_PACING,
                severity="major",
                evidence_quote="; ".join(rule_audit.rhythm_issues[:3]),
                evidence_location="全章段落结构",
                issue_description=(
                    f"段落节奏欠佳（评分 {rhythm_score:.1f}/10）— 需要调整段落长度分布。"
                ),
                expected="段落长度有变化：短句制造紧张，中长段落推进叙事。",
                actual="; ".join(rule_audit.rhythm_issues[:3]),
                suggested_fix=(
                    "拆分过长叙述段落；在关键动作处使用短句/短段；"
                    "合并过度碎片化的单句段落。"
                ),
                fix_type="patch",
                confidence=0.85,
            )
        )

    return issues


def _extract_protected_fissures(
    literary_result: LiteraryAuditResult | None,
) -> list[str]:
    """提取 valuable_fissure 的 evidence_quote 作为保护内容."""
    if literary_result is None:
        return []
    fissures: list[str] = []
    for obs in literary_result.observations:
        if (
            obs.observation_type == "valuable_fissure"
            and obs.preserve
            and obs.evidence_quote
        ):
            fissures.append(obs.evidence_quote)
    return fissures


def _render_issues(issues: list[ReviewIssue]) -> str:
    """将 issues 渲染为文本列表."""
    if not issues:
        return "（无需要修复的问题）"
    lines: list[str] = []
    for i, issue in enumerate(issues, 1):
        lines.append(f"### 问题 {i} [{issue.issue_id}]")
        lines.append(f"- 类型：{issue.category}")
        lines.append(f"- 严重程度：{issue.severity}")
        lines.append(f"- 原文引用：{issue.evidence_quote}")
        lines.append(f"- 位置：{issue.evidence_location}")
        lines.append(f"- 问题描述：{issue.issue_description}")
        if issue.expected:
            lines.append(f"- 期望：{issue.expected}")
        if issue.actual:
            lines.append(f"- 实际：{issue.actual}")
        if issue.suggested_fix:
            lines.append(f"- 建议修复：{issue.suggested_fix}")
        lines.append("")
    return "\n".join(lines)


def _render_protected_fissures(fissures: list[str]) -> str:
    """将保护内容渲染为文本列表."""
    if not fissures:
        return "（无）"
    lines = [f"{i}. {f}" for i, f in enumerate(fissures, 1)]
    return "\n".join(lines)


def _render_previous_show_dont_tell_feedback(
    previous_issues: list[ReviewIssue] | None,
) -> str:
    """渲染上一轮 show-dont-tell 的 evidence 作为 feedback."""
    if not previous_issues:
        return ""

    show_dont_tell_issues = [
        i
        for i in previous_issues
        if i.category == ReviewCategory.SHOW_DONT_TELL and i.evidence_quote
    ]

    if not show_dont_tell_issues:
        return ""

    lines: list[str] = [
        "## 上一轮审查的具体证据",
        "",
        '以下句子在上一轮审查中被标记为"展示而非讲述"（show-dont-tell）问题，请优先修改这些句子：',
        "",
    ]

    for i, issue in enumerate(show_dont_tell_issues, 1):
        desc = issue.issue_description or ""
        lines.append(f'{i}. "{issue.evidence_quote}" — {desc}')

    lines.append("")
    lines.append("修改时请保留原文的叙事位置和角色视角，只替换被标记的句子。")

    result = "\n".join(lines)
    if len(result) > _MAX_PREVIOUS_EVIDENCE_CHARS:
        truncated = result[:_MAX_PREVIOUS_EVIDENCE_CHARS]
        last_newline = truncated.rfind("\n")
        if last_newline > 0:
            truncated = truncated[:last_newline]
        result = truncated + "\n...（证据列表已截断）"
    return result


def _render_prompt(
    content: str,
    issues: list[ReviewIssue],
    protected_fissures: list[str],
    previous_issues: list[ReviewIssue] | None = None,
    *,
    prompt_version: str | None = None,
    readability_metrics: dict[str, Any] | None = None,
) -> str:
    """渲染 RevisionHandler Prompt.

    Task 128c: 支持 readability 专精 prompt 版本和可读性指标变量。
    """
    from songyan.prompts import get_prompt_loader

    loader = get_prompt_loader()
    card = loader.load_card("revision_handler", version=prompt_version)

    content = truncate_to_tokens(content, MAX_CONTENT_TOKENS)

    variables: dict[str, Any] = {
        "content": content,
        "issues": _render_issues(issues),
        "protected_fissures": _render_protected_fissures(protected_fissures),
    }
    if readability_metrics is not None:
        variables.update(readability_metrics)

    rendered = loader.render_card(card, variables)
    prompt = rendered.full_prompt

    feedback = _render_previous_show_dont_tell_feedback(previous_issues)
    if feedback:
        prompt += "\n\n" + feedback
    return prompt


# ---------------------------------------------------------------------------
# Scene Structure Strategies (Task 095)
# ---------------------------------------------------------------------------
async def _handle_scene_split(content: str, target_scenes: int = 2) -> str:
    """当场景数不足时，调用 LLM 将长场景拆分为多个空行分隔场景.

    Task 133: 输出使用空行分隔，不再使用 ### Scene N 标记；
    每个新场景至少 600 字（中文），保持原有叙事连贯性。
    """
    prompt = (
        f"你是小说编辑。以下章节场景数不足，需要拆分为至少 {target_scenes} 个场景。\n\n"
        "要求：\n"
        "1. 在情节转折点或时空切换处插入**空行**作为场景分隔，"
        "**禁止使用** `### Scene N`、`Scene 1:` 等任何形式的场景标题或编号。\n"
        "2. 每个新场景应有独立的开始和收束，且字数不少于 600 字（中文）。\n"
        "3. 保持原有叙事连贯性和角色视角，不要删除原有内容。\n"
        "4. 输出完整修订后的正文，不要添加解释、总结、JSON 或 markdown 代码块。\n\n"
        f"正文：\n{content}"
    )
    llm_response = await call_llm(prompt, temperature=0.3)
    from songyan.agents.writer import _extract_body

    revised = _extract_body(llm_response)
    return revised if revised.strip() else content


# 兼容旧测试与外部调用：保留旧名称
_handle_scene_shortage = _handle_scene_split


async def _handle_scene_overflow(content: str, target_words: int) -> str:
    """当字数严重超标且场景过多时，调用 LLM 合并次要场景."""
    prompt = f"""你是小说编辑。以下章节场景过多且字数超标，需要合并次要场景。

要求：
1. 保留主要场景的完整性
2. 将次要过渡场景压缩为简短段落
3. 合并后保留 2-3 个核心场景
4. 控制总字数在 {target_words} 字左右
5. 输出完整修订后的正文，不要添加解释

正文：
{content}
"""
    llm_response = await call_llm(prompt, temperature=0.3)
    from songyan.agents.writer import _extract_body

    revised = _extract_body(llm_response)
    return revised if revised.strip() else content


async def _patch_mandatory_reference_missing(
    content: str,
    missing_refs: list[dict],
    word_count_target: int = 3000,
) -> tuple[str, list[str]]:
    """为缺失的 mandatory reference 插入自然提及.

    返回修订后正文与已修复 setting_key 列表。
    """
    if not missing_refs:
        return content, []

    names = [
        str(r.get("setting_name") or r.get("setting_key") or "")
        for r in missing_refs
    ]
    names = [n for n in names if n]

    prompt = (
        "你是小说编辑。以下章节缺少一些前文的 critical 设定回收。"
        "请在保持原有叙事、不删除已有内容的前提下，为每个设定在合适位置插入一处自然提及。\n\n"
        "要求：\n"
        "1. 只能通过角色对话、环境细节、动作触发或剧情事件来提及，禁止直接罗列设定。\n"
        "2. 不要新增大段解释，每处提及 1-2 句话即可。\n"
        "3. 不要改变本章主要情节走向。\n"
        "4. 输出完整修订后的正文，不要添加解释、总结或 markdown 代码块。\n\n"
        f"缺失设定：{names}\n\n"
        f"正文：\n{content}"
    )
    llm_response = await call_llm(prompt, temperature=0.3)
    from songyan.agents.writer import _extract_body

    revised = _extract_body(llm_response) or content

    fixed: list[str] = []
    text_lower = revised.lower()
    for r in missing_refs:
        key = str(r.get("setting_key") or "")
        name = str(r.get("setting_name") or "")
        key_alias = key.split(".")[-1].lower() if key else ""
        if key_alias and key_alias in text_lower:
            fixed.append(key)
        elif name and name.lower() in text_lower:
            fixed.append(key)
        elif key and key.lower() in text_lower:
            fixed.append(key)
    return revised, fixed


def _parse_patches(data: dict[str, Any]) -> list[Patch]:
    """从字典解析 patches 列表."""
    patches: list[Patch] = []
    for item in data.get("patches", []):
        if not isinstance(item, dict):
            continue
        issue_id = item.get("issue_id", "")
        original_text = item.get("original_text", "")
        revised_text = item.get("revised_text", "")
        location = item.get("location", "")
        if not issue_id or not original_text:
            logger.warning(
                "revision_handler.invalid_patch",
                issue_id=issue_id,
                has_original=bool(original_text),
            )
            continue
        patches.append(
            Patch(
                issue_id=issue_id,
                original_text=original_text,
                revised_text=revised_text,
                location=location,
            )
        )
    return patches


def _detect_new_issues(
    original: RuleAuditResult | None,
    revised: RuleAuditResult | None,
) -> list[ReviewIssue]:
    """对比 revision 前后的 RuleAuditResult，检测新问题.

    检测维度：
    - AI 腔增加
    - 疲劳词增加
    - 首屏钩子丢失
    - 章末钩子丢失
    """
    if original is None or revised is None:
        return []

    new_issues: list[ReviewIssue] = []

    # 1. AI 腔增加
    if revised.ai_tell_count > original.ai_tell_count:
        new_issues.append(
            ReviewIssue(
                issue_id=f"rev-ai_tell-{uuid.uuid4().hex[:8]}",
                category=ReviewCategory.SHOW_DONT_TELL,
                severity="major",
                evidence_quote=(
                    f"AI腔从 {original.ai_tell_count} 处"
                    f"增加到 {revised.ai_tell_count} 处"
                ),
                evidence_location="revision后全文",
                issue_description=(
                    "Revision 引入了新的 AI 腔 — "
                    "LLM 在 patch 过程中使用了抽象概括或模型化叙述。"
                ),
                expected="保持具体、感官化的描写，避免抽象概括。",
                actual=f"revision后 AI 腔增加至 {revised.ai_tell_count} 处",
                suggested_fix=(
                    "重写 patch 区域，用角色感官体验和具体动作"
                    "替代抽象描述。"
                ),
                fix_type="patch",
                confidence=0.9,
            )
        )

    # 2. 疲劳词增加
    if revised.fatigue_word_count > original.fatigue_word_count:
        new_issues.append(
            ReviewIssue(
                issue_id=f"rev-fatigue-{uuid.uuid4().hex[:8]}",
                category=ReviewCategory.DESCRIPTION_SENSORY,
                severity="major",
                evidence_quote=(
                    f"疲劳词从 {original.fatigue_word_count} 处"
                    f"增加到 {revised.fatigue_word_count} 处"
                ),
                evidence_location="revision后全文",
                issue_description=(
                    "Revision 引入了新的疲劳词 — "
                    "patch 过程中重复使用同一词汇，造成阅读疲劳。"
                ),
                expected="同一概念应使用多样的表达，轮换词汇和感官通道。",
                actual=f"revision后疲劳词增加至 {revised.fatigue_word_count} 处",
                suggested_fix=(
                    "将重复出现的疲劳词替换为同义词、比喻或具体描写；"
                    "删除冗余 occurrence。"
                ),
                fix_type="patch",
                confidence=0.9,
            )
        )

    # 3. 首屏钩子丢失
    if original.has_opening_hook and not revised.has_opening_hook:
        new_issues.append(
            ReviewIssue(
                issue_id=f"rev-open_hook-{uuid.uuid4().hex[:8]}",
                category=ReviewCategory.NARRATIVE_HOOK,
                severity="critical",
                evidence_quote="首屏钩子在 revision 后消失",
                evidence_location="章节开头",
                issue_description=(
                    "Revision 破坏了首屏钩子 — "
                    "patch 过程中删除了或弱化了开头的悬念/冲突。"
                ),
                expected="首段应直接切入动作、冲突、悬念或强烈情绪。",
                actual="首屏钩子消失，开头变得平淡。",
                suggested_fix="恢复或重建首屏钩子：以动作、对话、冲突切入。",
                fix_type="patch",
                confidence=1.0,
            )
        )

    # 4. 章末钩子丢失
    if original.has_ending_hook and not revised.has_ending_hook:
        new_issues.append(
            ReviewIssue(
                issue_id=f"rev-end_hook-{uuid.uuid4().hex[:8]}",
                category=ReviewCategory.NARRATIVE_HOOK,
                severity="critical",
                evidence_quote="章末钩子在 revision 后消失",
                evidence_location="章节末尾",
                issue_description=(
                    "Revision 破坏了章末钩子 — "
                    "patch 过程中删除了或弱化了结尾的悬念/转折。"
                ),
                expected="结尾应有悬念、冲突升级、新发现或情感冲击。",
                actual="章末钩子消失，结尾变得平淡收束。",
                suggested_fix=(
                    "恢复或重建章末钩子："
                    "添加悬念、新危机征兆或角色发现的秘密。"
                ),
                fix_type="patch",
                confidence=1.0,
            )
        )

    return new_issues


def _build_revision_output(
    data: dict[str, Any],
    original_issues: list[ReviewIssue],
    content: str,
    new_version_id: str,
    original_rule_result: RuleAuditResult | None = None,
    revised_rule_result: RuleAuditResult | None = None,
) -> RevisionOutput:
    """从解析后的字典构建 RevisionOutput.

    以实际成功应用的 patch 为准标记 issue 状态，避免 LLM 返回了 patch
    但 original_text 与正文不匹配导致的虚假修复。

    058d: 新增 revision 前后 RuleAuditResult 对比，检测新问题。
    """
    patches = _parse_patches(data)
    _, applied_patches = _apply_patches(content, patches)
    fixed, remaining = _determine_issues_fixed(applied_patches, original_issues)
    new_issues = _detect_new_issues(original_rule_result, revised_rule_result)
    return RevisionOutput(
        new_version_id=new_version_id,
        patches_applied=applied_patches,
        issues_fixed=fixed,
        issues_remaining=remaining,
        new_issues_introduced=new_issues,
    )


# ---------------------------------------------------------------------------
# Main Entry
# ---------------------------------------------------------------------------
async def run_revision(
    content: str,
    report: MergedReviewReport,
    literary_result: LiteraryAuditResult | None = None,
    temperature: float = 0.3,
    original_rule_result: RuleAuditResult | None = None,
    revised_rule_result: RuleAuditResult | None = None,
    previous_issues: list[ReviewIssue] | None = None,
    word_count_target: int = 3000,
    score_card: dict[str, Any] | None = None,
) -> tuple[RevisionOutput, str]:
    """运行修订 — 按 issue 局部 patch，不整章重写.

    Args:
        content: 原始章节正文
        report: 合并审查报告（含 patchable_issues）
        literary_result: 可选的 LiteraryAuditor 结果，用于保护 valuable_fissure
        temperature: LLM 温度（默认 0.3，精确修改）
        word_count_target: 目标字数（V4.0 Task 088 字数硬约束）
        score_card: 可选的 score_card dict（Task 128c：用于判断 readability 专精路径）

    Returns:
        (RevisionOutput, revised_content)
    """
    start_time = time.perf_counter()

    # Task 128c: 判断是否需要 readability 专精修订
    readability_driven = _readability_driven(report, score_card)
    readability_metrics = (
        _readability_metrics_from_report(report) if readability_driven else None
    )

    patchable_issues = _filter_patchable_issues(report)
    scene_split_issues = _filter_scene_split_issues(report)

    # Task 138n: 先处理 mandatory_reference_missing 聚合 issue
    mr_issues = [i for i in patchable_issues if i.issue_id.startswith("rule-mr-")]
    other_issues = [i for i in patchable_issues if not i.issue_id.startswith("rule-mr-")]
    mr_fixed_ids: set[str] = set()
    if mr_issues and report.rule_audit is not None:
        missing_refs = [
            ref
            for ref in (report.rule_audit.mandatory_reference_issues or [])
            if isinstance(ref, dict)
        ]
        if missing_refs:
            mr_revised, fixed_keys = await _patch_mandatory_reference_missing(
                content, missing_refs, word_count_target
            )
            original_len = len(content)
            preservation_ratio = (
                round(len(mr_revised) / original_len, 4)
                if original_len > 0
                else 1.0
            )
            if mr_revised.strip() and preservation_ratio >= MIN_CONTENT_RATIO:
                content = mr_revised
                mr_fixed_ids = {i.issue_id for i in mr_issues}
                logger.info(
                    "revision_handler.mr_patch_applied",
                    fixed_keys=fixed_keys,
                    preservation_ratio=preservation_ratio,
                    issue_ids=sorted(mr_fixed_ids),
                )
            else:
                logger.warning(
                    "revision_handler.mr_patch_fallback",
                    preservation_ratio=preservation_ratio,
                    reason="content_too_short_or_empty",
                )
    patchable_issues = other_issues

    # Task 133: 先处理 scene_split 类型的结构问题
    pre_fixed_issue_ids: set[str] = set()
    if scene_split_issues:
        split_content = await _handle_scene_split(content, target_scenes=2)
        original_len = len(content)
        split_len = len(split_content)
        preservation_ratio = round(split_len / original_len, 4) if original_len > 0 else 1.0
        if split_content.strip() and preservation_ratio >= MIN_CONTENT_RATIO:
            content = split_content
            pre_fixed_issue_ids = {i.issue_id for i in scene_split_issues}
            logger.info(
                "revision_handler.scene_split_applied",
                issue_ids=sorted(pre_fixed_issue_ids),
                preservation_ratio=preservation_ratio,
            )
        else:
            logger.warning(
                "revision_handler.scene_split_fallback",
                preservation_ratio=preservation_ratio,
                reason="content_too_short_or_empty",
            )

    if readability_driven:
        rh_issues = _build_readability_issues(report)
        # 合并并去重：保留原有 patchable issues，补充 readability 专精 issues
        existing_ids = {i.issue_id for i in patchable_issues}
        for issue in rh_issues:
            if issue.issue_id not in existing_ids:
                patchable_issues.append(issue)
                existing_ids.add(issue.issue_id)
        _rh_metrics: dict[str, Any] = readability_metrics or {}
        logger.info(
            "revision_handler.readability_driven",
            ai_tell_count=_rh_metrics.get("ai_tell_count"),
            fatigue_word_count=_rh_metrics.get("fatigue_word_count"),
            paragraph_rhythm_score=_rh_metrics.get("paragraph_rhythm_score"),
            total_issues=len(patchable_issues),
        )

    if not patchable_issues and not pre_fixed_issue_ids:
        logger.info("revision_handler.no_patchable_issues")
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        new_issues = _detect_new_issues(original_rule_result, revised_rule_result)
        output = RevisionOutput(
            new_version_id="",
            patches_applied=[],
            issues_fixed=list(pre_fixed_issue_ids),
            issues_remaining=[],
            new_issues_introduced=new_issues,
        )
        if mr_fixed_ids:
            output.issues_fixed = sorted(
                set(output.issues_fixed) | mr_fixed_ids
            )
        return output, content

    protected_fissures = _extract_protected_fissures(literary_result)

    # 079: 尝试分段修订模式
    segmented_output: RevisionOutput | None = None
    segmented_content: str | None = None
    use_segmented = len(patchable_issues) >= 1 and len(content) > 1500

    if use_segmented:
        try:
            segmented_output, segmented_content = await run_segmented_revision(
                content=content,
                issues=patchable_issues,
                protected_fissures=protected_fissures,
                temperature=temperature,
                original_rule_result=original_rule_result,
                revised_rule_result=revised_rule_result,
                target_word_count=word_count_target,
            )
            if segmented_output.segmented and segmented_content:
                logger.info(
                    "revision_handler.used_segmented",
                    scenes_modified=segmented_output.scenes_modified,
                    scenes_fallback=segmented_output.scenes_fallback_count,
                    preservation_ratio=segmented_output.content_preservation_ratio,
                )
                # 分段修订成功且被使用
                if segmented_output.content_preservation_ratio >= MIN_CONTENT_RATIO:
                    output = segmented_output
                    output.new_version_id = ""
                    if mr_fixed_ids:
                        fixed_set = set(output.issues_fixed) | mr_fixed_ids
                        output.issues_fixed = sorted(fixed_set)
                        output.issues_remaining = [
                            iid
                            for iid in output.issues_remaining
                            if iid not in mr_fixed_ids
                        ]
                    return output, segmented_content
                else:
                    logger.warning(
                        "revision_handler.segmented_poor_preservation",
                        ratio=segmented_output.content_preservation_ratio,
                        fallback="patch_engine",
                    )
        except (RuntimeError, ValueError, TypeError) as exc:
            logger.warning(
                "revision_handler.segmented_failed",
                error=str(exc),
                fallback="patch_engine",
            )

    # 回退到原有 patch_engine 路径
    # Task 128c: readability 驱动时使用 1.1.0 专精 prompt
    prompt = _render_prompt(
        content,
        patchable_issues,
        protected_fissures,
        previous_issues,
        prompt_version="1.1.0" if readability_driven else None,
        readability_metrics=readability_metrics,
    )

    llm_response = await call_llm(prompt, temperature=temperature)
    data = parse_llm_response(llm_response)

    duration_ms = int((time.perf_counter() - start_time) * 1000)

    # 使用 LLM 返回的 content 作为修订后正文
    revised_content = data.get("content", content)
    original_len = len(content)

    # 字数保护：LLM 可能未输出完整正文（只返回 patch 摘要）
    content_truncated = len(revised_content) < original_len * MIN_CONTENT_RATIO

    # 也尝试从 patches 应用（如果 LLM 返回的 content 与 patches 不一致，
    # 以代码应用 patches 的结果为准，保证确定性）
    patches = _parse_patches(data)
    patch_applied_content: str | None = None
    applied_patches: list[Patch] = []
    if patches:
        patch_applied_content, applied_patches = _apply_patches(content, patches)

    # 决策逻辑：选择最可靠的修订结果
    if content_truncated:
        logger.warning(
            "revision_handler.content_truncated",
            original_len=original_len,
            returned_len=len(revised_content),
            ratio=round(len(revised_content) / original_len, 2) if original_len > 0 else 0,
        )
        # 优先尝试 patch 应用结果（如果 patch 成功且字数合理）
        if patch_applied_content and len(patch_applied_content) >= original_len * MIN_CONTENT_RATIO:
            revised_content = patch_applied_content
            logger.info(
                "revision_handler.fallback_to_patches",
                patch_applied_len=len(patch_applied_content),
            )
        else:
            # patch 也失败或字数不足，回退到原始内容（只保留成功应用的 patch）
            if patch_applied_content and patch_applied_content != content:
                revised_content = patch_applied_content
                logger.warning(
                    "revision_handler.partial_fallback",
                    patch_applied_len=len(patch_applied_content),
                )
            else:
                revised_content = content
                logger.warning("revision_handler.revert_to_original")
    else:
        # LLM 返回的 content 字数正常，优先使用
        if patch_applied_content and patch_applied_content != content:
            # patches 成功应用，但与 LLM content 不同，优先使用代码层结果
            # 但同样检查 patch 后的字数是否合理
            if len(patch_applied_content) >= original_len * MIN_CONTENT_RATIO:
                revised_content = patch_applied_content
            else:
                logger.warning(
                    "revision_handler.patch_result_too_short",
                    patch_applied_len=len(patch_applied_content),
                    original_len=original_len,
                )
        # 日志：记录实际应用 vs 返回的 patch 数量差异
        if patches and len(applied_patches) != len(patches):
            logger.warning(
                "revision_handler.partial_patches",
                returned=len(patches),
                applied=len(applied_patches),
            )

    # V4.0 Task 088 + Task 100a: 字数硬约束（patch_engine 路径）
    from songyan.utils.scene_parser import parse_scenes as _parse_scenes

    from ._segmented_revision import _enforce_revision_word_count

    revised_scenes_parsed = _parse_scenes(revised_content)
    constrained_content, constrained_scenes, constrained_wc, adjusted, reason = (
        _enforce_revision_word_count(
            revised_content, revised_scenes_parsed, content, word_count_target
        )
    )
    if adjusted:
        _rev_wc = len(re.findall(r"[\u4e00-\u9fff]", revised_content)) + len(
            re.findall(r"[a-zA-Z0-9]+", revised_content)
        )
        if reason == "revision_underflow_needs_human_review":
            # Task 100a: 字数低于 0.85x original，标记需要人工审查
            # 保持 revision 内容不变（不回退到原始 draft），让 quality gate 处理
            logger.warning(
                "revision_handler.word_count_needs_human_review",
                reason=reason,
                original_wc=_rev_wc,
                adjusted_wc=constrained_wc,
                target=word_count_target,
            )
        else:
            logger.info(
                "revision_handler.word_count_adjusted",
                reason=reason,
                original_wc=_rev_wc,
                adjusted_wc=constrained_wc,
                target=word_count_target,
            )
        revised_content = constrained_content
        content_preservation_ratio = (
            round(min(len(revised_content) / original_len, 1.0), 4) if original_len > 0 else 0.0
        )

    # 计算内容保留率（用于监控和 Layer 2 采集）
    # 上限 1.0：保留率语义，内容膨胀不视为"保留不足"
    content_preservation_ratio = (
        round(min(len(revised_content) / original_len, 1.0), 4) if original_len > 0 else 0.0
    )
    logger.info(
        "revision_handler.content_preservation_ratio",
        ratio=content_preservation_ratio,
        original_len=original_len,
        revised_len=len(revised_content),
    )

    # revised_content 由调用方通过 RevisionOutput + 正文配合使用
    # 本函数返回 RevisionOutput，调用方可自行决定保存策略
    logger.info(
        "revision_handler.done",
        patches_count=len(patches),
        applied_count=len(applied_patches) if patches else 0,
        issues_count=len(patchable_issues),
        duration_ms=duration_ms,
        word_count_adjusted=adjusted,
        word_count_reason=reason if adjusted else "",
    )

    # new_version_id 由 save 阶段生成
    output = _build_revision_output(
        data,
        patchable_issues,
        content,
        new_version_id="",
        original_rule_result=original_rule_result,
        revised_rule_result=revised_rule_result,
    )
    output.content_preservation_ratio = content_preservation_ratio
    # Task 133: 把 scene_split 已修复的 issue 计入 fixed
    if pre_fixed_issue_ids:
        fixed_set = set(output.issues_fixed) | pre_fixed_issue_ids
        output.issues_fixed = sorted(fixed_set)
        output.issues_remaining = [
            iid for iid in output.issues_remaining if iid not in pre_fixed_issue_ids
        ]
    # Task 138n: 把 MR patch 已修复的 issue 计入 fixed
    if mr_fixed_ids:
        fixed_set = set(output.issues_fixed) | mr_fixed_ids
        output.issues_fixed = sorted(fixed_set)
        output.issues_remaining = [
            iid for iid in output.issues_remaining if iid not in mr_fixed_ids
        ]
    return output, revised_content


async def save_revision_output(
    version_db: ChapterVersionRepository,
    head_db: ChapterHeadRepository,
    project_id: str,
    chapter_number: int,
    output: RevisionOutput,
    revised_content: str,
    parent_version: ChapterVersion,
) -> str:
    """保存修订结果 — 创建 revision 版本并更新 ChapterHead.

    Returns:
        新创建的 version_id
    """
    from songyan.agents.writer import _strip_scene_marker_lines

    revised_content = _strip_scene_marker_lines(revised_content).strip()

    # 确定版本号（包含废弃版本，避免编号冲突）
    version_number = await version_db.get_next_version_number(project_id, chapter_number)

    version_id = f"rev-{chapter_number}-{version_number}-{uuid.uuid4().hex[:8]}"

    # 字数统计
    import re

    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", revised_content))
    other_words = len(re.findall(r"[a-zA-Z0-9]+", revised_content))
    word_count = chinese_chars + other_words

    # 079: 解析场景 — 复用 writer 的 _parse_scenes
    from songyan.utils.scene_parser import parse_scenes as _parse_scenes

    scenes = _parse_scenes(revised_content)

    version = ChapterVersion(
        version_id=version_id,
        project_id=project_id,
        chapter_number=chapter_number,
        version_number=version_number,
        version_type="revision",
        content=revised_content,
        word_count=word_count,
        scenes=scenes,
        parent_version_id=parent_version.version_id,
    )

    await version_db.create(version)

    # 更新 ChapterHead
    head = await head_db.get(project_id, chapter_number)
    if head is None:
        head = ChapterHead(
            project_id=project_id,
            chapter_number=chapter_number,
            current_version_id=version_id,
            status="under_review",
        )
    else:
        head.current_version_id = version_id
        head.status = "under_review"
    await head_db.update(head)

    logger.info(
        "revision_handler.saved",
        version_id=version_id,
        version_number=version_number,
        word_count=word_count,
        patches_count=len(output.patches_applied),
    )

    output.new_version_id = version_id
    return version_id
