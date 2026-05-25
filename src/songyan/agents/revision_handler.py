"""RevisionHandler Agent — issue-driven patch 修订，不整章重写."""

from __future__ import annotations

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
    ReviewIssue,
    RevisionOutput,
)

logger = structlog.get_logger(__name__)

MAX_CONTENT_LENGTH = 8000


def _load_prompt_template() -> str:
    """加载 RevisionHandler Prompt 模板 — 已迁移到工艺卡系统."""
    from songyan.prompts import get_prompt_loader
    return get_prompt_loader().load_card("revision_handler").system_prompt


def _filter_patchable_issues(report: MergedReviewReport) -> list[ReviewIssue]:
    """筛选可 patch 的 issues."""
    return report.patchable_issues


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


def _render_prompt(
    content: str,
    issues: list[ReviewIssue],
    protected_fissures: list[str],
) -> str:
    """渲染 RevisionHandler Prompt."""
    from songyan.prompts import get_prompt_loader

    loader = get_prompt_loader()
    card = loader.load_card("revision_handler")

    if len(content) > MAX_CONTENT_LENGTH:
        content = content[:MAX_CONTENT_LENGTH] + "\n...（正文已截断）"

    rendered = loader.render_card(card, {
        "content": content,
        "issues": _render_issues(issues),
        "protected_fissures": _render_protected_fissures(protected_fissures),
    })
    return rendered.full_prompt


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


def _apply_patches(content: str, patches: list[Patch]) -> str:
    """从后往前应用 patch，避免位置偏移.

    按 original_text 在 content 中最后一次出现的位置倒序处理。
    """
    if not patches:
        return content

    def _last_index(patch: Patch) -> int:
        return content.rfind(patch.original_text)

    sorted_patches = sorted(patches, key=_last_index, reverse=True)

    result = content
    for patch in sorted_patches:
        idx = result.rfind(patch.original_text)
        if idx == -1:
            logger.warning(
                "revision_handler.patch_not_found",
                issue_id=patch.issue_id,
                original_text=patch.original_text[:50],
            )
            continue
        result = (
            result[:idx]
            + patch.revised_text
            + result[idx + len(patch.original_text) :]
        )
        logger.info(
            "revision_handler.patch_applied",
            issue_id=patch.issue_id,
            location=patch.location,
        )
    return result


def _determine_issues_fixed(
    patches: list[Patch], original_issues: list[ReviewIssue]
) -> tuple[list[str], list[str]]:
    """确定哪些 issue 被修复，哪些未修复."""
    patched_ids = {p.issue_id for p in patches}
    fixed: list[str] = []
    remaining: list[str] = []
    for issue in original_issues:
        if issue.issue_id in patched_ids:
            fixed.append(issue.issue_id)
        else:
            remaining.append(issue.issue_id)
    return fixed, remaining


def _build_revision_output(
    data: dict[str, Any],
    original_issues: list[ReviewIssue],
    new_version_id: str,
) -> RevisionOutput:
    """从解析后的字典构建 RevisionOutput."""
    patches = _parse_patches(data)
    fixed, remaining = _determine_issues_fixed(patches, original_issues)
    return RevisionOutput(
        new_version_id=new_version_id,
        patches_applied=patches,
        issues_fixed=fixed,
        issues_remaining=remaining,
        new_issues_introduced=[],
    )


# ---------------------------------------------------------------------------
# Main Entry
# ---------------------------------------------------------------------------
async def run_revision(
    content: str,
    report: MergedReviewReport,
    literary_result: LiteraryAuditResult | None = None,
    temperature: float = 0.3,
) -> RevisionOutput:
    """运行修订 — 按 issue 局部 patch，不整章重写.

    Args:
        content: 原始章节正文
        report: 合并审查报告（含 patchable_issues）
        literary_result: 可选的 LiteraryAuditor 结果，用于保护 valuable_fissure
        temperature: LLM 温度（默认 0.3，精确修改）

    Returns:
        (RevisionOutput, revised_content)
    """
    start_time = time.perf_counter()

    patchable_issues = _filter_patchable_issues(report)

    if not patchable_issues:
        logger.info("revision_handler.no_patchable_issues")
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        output = RevisionOutput(
            new_version_id="",
            patches_applied=[],
            issues_fixed=[],
            issues_remaining=[],
            new_issues_introduced=[],
        )
        return output, content

    protected_fissures = _extract_protected_fissures(literary_result)
    prompt = _render_prompt(content, patchable_issues, protected_fissures)

    llm_response = await call_llm(prompt, temperature=temperature)
    data = parse_llm_response(llm_response)

    duration_ms = int((time.perf_counter() - start_time) * 1000)

    # 使用 LLM 返回的 content 作为修订后正文
    revised_content = data.get("content", content)

    # 也尝试从 patches 应用（如果 LLM 返回的 content 与 patches 不一致，
    # 以代码应用 patches 的结果为准，保证确定性）
    patches = _parse_patches(data)
    if patches:
        patch_applied_content = _apply_patches(content, patches)
        if patch_applied_content != content:
            # patches 成功应用，优先使用代码层结果
            revised_content = patch_applied_content

    # revised_content 由调用方通过 RevisionOutput + 正文配合使用
    # 本函数返回 RevisionOutput，调用方可自行决定保存策略
    logger.info(
        "revision_handler.done",
        patches_count=len(patches),
        issues_count=len(patchable_issues),
        duration_ms=duration_ms,
    )

    # new_version_id 由 save 阶段生成
    output = _build_revision_output(data, patchable_issues, new_version_id="")
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
    # 确定版本号
    existing = await version_db.list_by_chapter(project_id, chapter_number)
    version_number = len(existing) + 1

    version_id = f"rev-{chapter_number}-{version_number}-{uuid.uuid4().hex[:8]}"

    # 字数统计
    import re

    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", revised_content))
    other_words = len(re.findall(r"[a-zA-Z0-9]+", revised_content))
    word_count = chinese_chars + other_words

    version = ChapterVersion(
        version_id=version_id,
        project_id=project_id,
        chapter_number=chapter_number,
        version_number=version_number,
        version_type="revision",
        content=revised_content,
        word_count=word_count,
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
