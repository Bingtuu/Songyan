"""RevisionHandler Patch 引擎 — 文本定位与应用."""

from __future__ import annotations

import re

import structlog

from songyan.models import Patch, ReviewIssue

from ._diff import _difflib_fuzzy_search, _paragraph_fallback_search

logger = structlog.get_logger(__name__)


def _find_text_span(
    text: str,
    target: str,
    issue_id: str = "",
    fuzzy_threshold: float = 0.90,
) -> tuple[int, int] | None:
    """在 text 中查找 target 的位置，支持精确/归一化/difflib/段落级四级匹配.

    Returns:
        (start, end) 如果找到，否则 None
    """
    if not target:
        return None

    # 1. 精确匹配
    idx = text.rfind(target)
    if idx != -1:
        return (idx, idx + len(target))

    # 2. 模糊匹配（归一化空白后）
    norm_target = " ".join(target.split())
    norm_text = " ".join(text.split())
    idx = norm_text.rfind(norm_target)
    if idx != -1:
        start = text.find(norm_target[:20])
        if start != -1:
            end = text.rfind(norm_target[-20:])
            if end != -1:
                return (start, end + len(norm_target[-20:]))

    # 3. difflib 滑动窗口模糊匹配（多级 threshold 回退）
    span = _difflib_fuzzy_search(text, target, issue_id, thresholds=(0.90, 0.85, 0.80))
    if span is not None:
        return span

    # 4. 段落级回退匹配：将 target 按段落分割，逐段查找最佳匹配
    span = _paragraph_fallback_search(text, target, issue_id)
    if span is not None:
        return span

    return None


def _apply_patches(content: str, patches: list[Patch]) -> tuple[str, list[Patch]]:
    """从后往前应用 patch，避免位置偏移与碰撞.

    按 original_text 在原始 content 中的位置从后往前排序，
    并检测已应用区间是否重叠，重叠则跳过。

    Returns:
        (修订后的文本, 实际成功应用的 patch 列表)
    """
    if not patches:
        return content, []

    # 计算原始位置并过滤找不到的 patch
    patch_spans: list[tuple[Patch, tuple[int, int]]] = []
    for patch in patches:
        span = _find_text_span(content, patch.original_text, issue_id=patch.issue_id)
        if span is None:
            logger.warning(
                "revision_handler.patch_not_found",
                issue_id=patch.issue_id,
                original_text=patch.original_text[:50],
            )
            continue
        patch_spans.append((patch, span))

    # 按结束位置从后往前排序（先应用靠后的 patch）
    patch_spans.sort(key=lambda x: x[1][1], reverse=True)

    result = content
    applied: list[Patch] = []
    applied_spans: list[tuple[int, int]] = []
    used_original_spans: list[tuple[int, int]] = []

    for patch, (orig_start, orig_end) in patch_spans:
        # 原始位置重叠则视为碰撞（多个 patch 指向同一处）
        if any(
            not (orig_end <= s or orig_start >= e)
            for s, e in used_original_spans
        ):
            logger.warning(
                "revision_handler.patch_collision_skipped",
                issue_id=patch.issue_id,
                original_text=patch.original_text[:50],
            )
            continue

        # 在当前的 result 中重新定位（content 可能已被前面 patch 修改）
        # 由于从后往前处理，后面的 patch 不影响前面 patch 的位置
        span = _find_text_span(result, patch.original_text, issue_id=patch.issue_id)
        if span is None:
            logger.warning(
                "revision_handler.patch_not_found_in_result",
                issue_id=patch.issue_id,
                original_text=patch.original_text[:50],
            )
            continue

        idx, patch_end = span

        # 再检测与已应用区间是否重叠（位置漂移导致）
        if any(
            not (patch_end <= s or idx >= e)
            for s, e in applied_spans
        ):
            logger.warning(
                "revision_handler.patch_collision_skipped",
                issue_id=patch.issue_id,
                original_text=patch.original_text[:50],
            )
            continue

        # 检测 revised_text 是否会导致重复文字（如 "林渊林渊"）
        candidate = result[:idx] + patch.revised_text + result[patch_end:]
        _repeat_re = re.compile(r"([\u4e00-\u9fff]{2,})\1")
        repeat_match = _repeat_re.search(candidate)
        if repeat_match:
            # 检查重复是否出现在 patch 边界附近（±20 字符）
            repeat_start = repeat_match.start()
            patch_boundary = idx
            if abs(repeat_start - patch_boundary) < 30:
                logger.warning(
                    "revision_handler.repeat_detected",
                    issue_id=patch.issue_id,
                    repeat=repeat_match.group(0),
                    location=patch.location,
                )
                continue

        result = candidate
        applied.append(patch)
        applied_spans.append((idx, idx + len(patch.revised_text)))
        used_original_spans.append((orig_start, orig_end))
        logger.info(
            "revision_handler.patch_applied",
            issue_id=patch.issue_id,
            location=patch.location,
        )
    return result, applied


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
