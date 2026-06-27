"""Task 079: 分段修订模式 — 按 scene 边界分段调用 LLM 修订.

解决 patch_not_found、content_truncated、partial_patches 等文本匹配脆弱问题。
"""

from __future__ import annotations

import re
import uuid

import structlog

from songyan.llm.client import call_llm
from songyan.models import Patch, ReviewIssue, RevisionOutput, RuleAuditResult
from songyan.utils.scene_parser import SCENE_PATTERN, _merge_short_blocks
from songyan.utils.token_estimator import truncate_to_tokens
from songyan.utils.word_count import count_chinese_words

logger = structlog.get_logger(__name__)

MAX_SCENE_CONTENT_TOKENS = 4000
MIN_PRESERVATION_RATIO = 0.85  # Task 100a: 从 0.50 提升至 0.85


def _split_content_by_scenes(content: str) -> list[dict]:
    """按 ### Scene N 或空行分块分割为 scene 段，含原始位置信息.

    Returns:
        [{"scene_number": int, "content": str, "start": int, "end": int, "header": str}, ...]
    """
    if not content.strip():
        return []

    matches = list(SCENE_PATTERN.finditer(content))
    if matches:
        scenes: list[dict] = []
        for i, match in enumerate(matches):
            scene_number = int(match.group(1))
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            scene_content = content[start:end].strip()
            scenes.append({
                "scene_number": scene_number,
                "content": scene_content,
                "start": start,
                "end": end,
                "header": match.group(0),
            })
        return scenes

    # Task 133: 无显式标记时按空行分块，过滤过渡碎块
    normalized = content.replace("\r\n", "\n")
    blocks = [block.strip() for block in re.split(r"\n\s*\n", normalized) if block.strip()]
    merged = _merge_short_blocks(blocks)
    if not merged:
        return [{
            "scene_number": 1,
            "content": content.strip(),
            "start": 0,
            "end": len(content),
            "header": "",
        }]

    scenes = []
    cursor = 0
    for idx, scene_content in enumerate(merged):
        start = content.find(scene_content, cursor)
        if start < 0:
            start = cursor
        end = start + len(scene_content)
        cursor = end
        scenes.append({
            "scene_number": idx + 1,
            "content": scene_content,
            "start": start,
            "end": end,
            "header": "",
        })
    return scenes


def _map_issues_to_scenes(
    issues: list[ReviewIssue],
    scenes: list[dict],
    full_content: str,
) -> tuple[dict[int, list[ReviewIssue]], list[ReviewIssue]]:
    """将 issue 映射到 scene.

    策略：
    1. 用 evidence_quote 在全文中查找位置 → 确定所属 scene
    2. evidence_quote 为空或找不到 → 用 evidence_location 关键词匹配最近 scene
    3. 完全无法定位 → 归入全局 issues

    Returns:
        (scene_number → issues 映射, 全局 issues 列表)
    """
    mapped: dict[int, list[ReviewIssue]] = {s["scene_number"]: [] for s in scenes}
    global_issues: list[ReviewIssue] = []

    for issue in issues:
        quote = issue.evidence_quote or ""
        located = False

        # 1. evidence_quote 定位
        if len(quote) >= 3:
            idx = full_content.find(quote)
            if idx != -1:
                for scene in scenes:
                    if scene["start"] <= idx < scene["end"]:
                        mapped[scene["scene_number"]].append(issue)
                        located = True
                        break

        if located:
            continue

        # 2. evidence_location 关键词匹配最近 scene
        loc = issue.evidence_location or ""
        if loc:
            best_scene = None
            best_score = -1
            for scene in scenes:
                score = 0
                scene_text = scene["content"]
                # 简单关键词重叠（按字符）
                for char in loc:
                    if char in scene_text:
                        score += 1
                if score > best_score:
                    best_score = score
                    best_scene = scene
            if best_scene and best_score > 0:
                mapped[best_scene["scene_number"]].append(issue)
                located = True

        if not located:
            global_issues.append(issue)

    return mapped, global_issues


def _render_scene_issues(issues: list[ReviewIssue]) -> str:
    """将 scene 相关 issues 渲染为文本."""
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


def _render_scene_prompt(
    scene_content: str,
    issues: list[ReviewIssue],
    protected_fissures: list[str],
) -> str:
    """渲染单个 scene 的修订 Prompt."""
    scene_content = truncate_to_tokens(scene_content, MAX_SCENE_CONTENT_TOKENS)

    prompt = f"""你是小说修订助手。请根据以下问题列表，修改给定的场景段落。

【场景段落】
{scene_content}

【需要修复的问题】
{_render_scene_issues(issues)}

【保护内容 — 请勿修改】
{_render_protected_fissures(protected_fissures)}

要求：
1. 只修改与问题相关的部分，保留其余内容不变
2. 不要添加、删除或重排段落
3. 不要修改保护内容
4. 直接输出修改后的完整场景段落，不要添加解释
5. 输出格式：直接输出正文，不要用 markdown 代码块包裹
6. 保持 ### Scene N 标题之前的场景编号不变（如果有）
"""
    return prompt


def _compute_preservation_ratio(original: str, revised: str) -> float:
    """计算内容保留率（基于字数）."""
    if not original:
        return 1.0
    return round(min(len(revised) / len(original), 1.0), 4)


async def _revise_single_scene(
    scene: dict,
    issues: list[ReviewIssue],
    protected_fissures: list[str],
    temperature: float = 0.3,
) -> tuple[str, list[Patch], bool]:
    """对单个 scene 调用 LLM 修订.

    Returns:
        (revised_scene_content, patches, fallback)
        fallback=True 表示保留率 < MIN_PRESERVATION_RATIO，已回退到原始内容
    """
    prompt = _render_scene_prompt(scene["content"], issues, protected_fissures)
    llm_response = await call_llm(prompt, temperature=temperature)

    # 清理 LLM 输出（去除代码块标记等）
    revised = llm_response.strip()
    if revised.startswith("```"):
        lines = revised.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        revised = "\n".join(lines).strip()

    ratio = _compute_preservation_ratio(scene["content"], revised)
    if ratio < MIN_PRESERVATION_RATIO:
        logger.warning(
            "revision_handler.scene_fallback",
            scene_number=scene["scene_number"],
            ratio=ratio,
            original_len=len(scene["content"]),
            revised_len=len(revised),
        )
        return scene["content"], [], True

    # 生成伪 patches（用于 RevisionOutput 兼容）
    patches: list[Patch] = []
    if revised != scene["content"]:
        patches.append(
            Patch(
                issue_id=f"seg-{scene['scene_number']}-{uuid.uuid4().hex[:6]}",
                original_text=scene["content"][:200],
                revised_text=revised[:200],
                location=f"Scene {scene['scene_number']}",
            )
        )

    return revised, patches, False


async def run_segmented_revision(
    content: str,
    issues: list[ReviewIssue],
    protected_fissures: list[str] | None = None,
    temperature: float = 0.3,
    original_rule_result: RuleAuditResult | None = None,
    revised_rule_result: RuleAuditResult | None = None,
    target_word_count: int = 3000,
) -> tuple[RevisionOutput, str]:
    """按 scene 分段修订主入口.

    1. 分割 content 为 scene 段
    2. 将 issues 映射到各 scene
    3. 对每个有 issue 的 scene 段调用 LLM 修订
    4. 验证每段保留率，回退失败段
    5. 拼接结果
    6. 全局 issues 不计入 patches
    7. V4.0: 字数硬约束（上限 1.5x / 下限 0.7x）

    Returns:
        (RevisionOutput, revised_content)
    """
    scenes = _split_content_by_scenes(content)

    # 无 issue 时没有局部修订目标，交给调用方回退到 patch_engine。
    if not issues:
        logger.info("revision_handler.segmented_not_enough_scenes", scene_count=len(scenes))
        output = RevisionOutput(
            new_version_id="",
            patches_applied=[],
            issues_fixed=[],
            issues_remaining=[i.issue_id for i in issues],
            new_issues_introduced=[],
            content_preservation_ratio=1.0,
            segmented=False,
            scenes_modified=0,
            scenes_fallback_count=0,
        )
        return output, content

    # Task 114c: 单 scene 章节仍可做 scene-scoped patch。
    # Ch120 暴露了只有 1 个 scene 时直接回退 patch_engine 会更容易触发整章输出截断；
    # 这里保留同一套保留率守卫，只把唯一 scene 当作局部修订单元。
    if len(scenes) == 1:
        logger.info("revision_handler.segmented_single_scene", issue_count=len(issues))

    mapped, global_issues = _map_issues_to_scenes(issues, scenes, content)
    protected = protected_fissures or []

    # 如果没有任何 issue 被映射到 scene，回退到 patch_engine
    has_mapped = any(mapped[s["scene_number"]] for s in scenes)
    if not has_mapped:
        logger.info("revision_handler.segmented_no_mapped_issues")
        output = RevisionOutput(
            new_version_id="",
            patches_applied=[],
            issues_fixed=[],
            issues_remaining=[i.issue_id for i in issues],
            new_issues_introduced=[],
            content_preservation_ratio=1.0,
            segmented=False,
            scenes_modified=0,
            scenes_fallback_count=0,
        )
        return output, content

    revised_scenes: list[str] = []
    all_patches: list[Patch] = []
    fixed_issue_ids: list[str] = []
    scenes_modified = 0
    scenes_fallback = 0

    for scene in scenes:
        scene_issues = mapped.get(scene["scene_number"], [])
        if not scene_issues:
            # 无 issue 的 scene 直接保留
            revised_scenes.append(scene["content"])
            continue

        revised_scene, patches, fallback = await _revise_single_scene(
            scene, scene_issues, protected, temperature
        )
        revised_scenes.append(revised_scene)
        all_patches.extend(patches)
        fixed_issue_ids.extend(i.issue_id for i in scene_issues)

        if fallback:
            scenes_fallback += 1
        elif revised_scene != scene["content"]:
            scenes_modified += 1

    # 按 scene 编号拼接（注意：不保留 header，因为 content 中的 header 在 split 时被排除）
    # 实际上 scenes[i]["content"] 不包含 header，需要重新加上
    full_revised = _reassemble_content(scenes, revised_scenes)

    content_preservation_ratio = _compute_preservation_ratio(content, full_revised)

    # Task 100a: 全局字数下限守卫 — 拼接后若保留率 < 0.85，直接回退到原始内容
    if content_preservation_ratio < MIN_PRESERVATION_RATIO:
        logger.warning(
            "revision_handler.segmented_global_floor_guard",
            preservation_ratio=content_preservation_ratio,
            min_ratio=MIN_PRESERVATION_RATIO,
            action="revert_to_original",
        )
        output = RevisionOutput(
            new_version_id="",
            patches_applied=[],
            issues_fixed=[],
            issues_remaining=[i.issue_id for i in issues],
            new_issues_introduced=[],
            content_preservation_ratio=1.0,
            segmented=True,
            scenes_modified=0,
            scenes_fallback_count=len(scenes),
        )
        return output, content

    # 全局 issues 计入 remaining
    remaining_ids = [i.issue_id for i in global_issues]

    # 检测新问题
    from . import _detect_new_issues

    new_issues = _detect_new_issues(original_rule_result, revised_rule_result)

    # V4.0 Task 088: 字数硬约束
    from songyan.utils.scene_parser import parse_scenes as _parse_scenes

    revised_scenes_parsed = _parse_scenes(full_revised)
    constrained_content, constrained_scenes, constrained_wc, adjusted, reason = (
        _enforce_revision_word_count(
            full_revised, revised_scenes_parsed, content, target_word_count
        )
    )
    if adjusted:
        logger.info(
            "revision_handler.word_count_adjusted",
            reason=reason,
            original_wc=count_chinese_words(full_revised),
            adjusted_wc=constrained_wc,
            target=target_word_count,
        )
        # 更新 preservation_ratio（基于约束后的内容）
        content_preservation_ratio = _compute_preservation_ratio(
            content, constrained_content
        )
        full_revised = constrained_content

    output = RevisionOutput(
        new_version_id="",
        patches_applied=all_patches,
        issues_fixed=fixed_issue_ids,
        issues_remaining=remaining_ids,
        new_issues_introduced=new_issues,
        content_preservation_ratio=content_preservation_ratio,
        segmented=True,
        scenes_modified=scenes_modified,
        scenes_fallback_count=scenes_fallback,
    )

    logger.info(
        "revision_handler.segmented_done",
        scenes_total=len(scenes),
        scenes_modified=scenes_modified,
        scenes_fallback=scenes_fallback,
        issues_fixed=len(fixed_issue_ids),
        issues_global=len(global_issues),
        preservation_ratio=content_preservation_ratio,
        word_count_adjusted=adjusted,
        word_count_reason=reason if adjusted else "",
    )
    return output, full_revised


def _reassemble_content(original_scenes: list[dict], revised_scenes: list[str]) -> str:
    """按 scene 顺序拼接成完整正文，保留原始 header."""
    parts: list[str] = []
    for i, scene in enumerate(original_scenes):
        header = scene.get("header", "")
        if header:
            parts.append(header)
        parts.append(revised_scenes[i])
        parts.append("")
    return "\n\n".join(parts).strip()


def _enforce_revision_word_count(
    revision_content: str,
    revision_scenes: list[dict],
    original_content: str,
    target_word_count: int,
    min_preserve_ratio: float = 0.85,
) -> tuple[str, list[dict], int, bool, str]:
    """Revision 后字数硬约束 (Task 093 → V4.0 收紧到 ±20% → Task 100a 下限保护).

    Revision 字数约束：上限 1.20x，下限 0.80x（与达标标准一致）。
    之前为 ±25%，导致达标初稿在 revision 后被"合法地"破坏到超标状态。

    Task 100a 新增：
    - 保留率下限从 0.50 提升至 0.85
    - 低于 0.85x original 时不自动回退，而是标记 needs_human_review
      让上层 quality gate 决定是否继续 revision 或上报人工

    Returns:
        content, scenes, word_count, was_adjusted, reason
    """
    from songyan.utils.scene_parser import parse_scenes as _parse_scenes
    from songyan.utils.truncation import enforce_word_count as _enforce_word_count
    from songyan.utils.word_count import count_chinese_words

    upper = int(target_word_count * 1.20)
    lower = int(target_word_count * 0.80)
    current = count_chinese_words(revision_content)

    if current > upper:
        # 二次截断（复用 Writer 的截断逻辑）
        content, scenes, wc, _, reason = _enforce_word_count(
            revision_content, revision_scenes, target_word_count, current
        )
        # 保留率验证：二次截断后保留率仍 ≥ min_preserve_ratio (0.85)
        preservation = len(content) / len(revision_content) if revision_content else 1.0
        if preservation < min_preserve_ratio:
            # 保留率过低 → 回退到原始 draft
            original_scenes = _parse_scenes(original_content)
            original_wc = count_chinese_words(original_content)
            return (
                original_content,
                original_scenes,
                original_wc,
                True,
                "revision_truncated_preservation_too_low_fallback",
            )
        return content, scenes, wc, True, f"revision_truncated:{reason}"

    if current < lower:
        original_wc = count_chinese_words(original_content)
        # 若原始内容本身就不足下限，说明是测试/短内容场景，不强制 fallback
        if original_wc < lower:
            return (
                revision_content,
                revision_scenes,
                current,
                False,
                "revision_accepted_short_original",
            )

        # Task 100a: 若 revision 后字数低于 original 的 min_preserve_ratio (0.85)
        # 不自动回退到原始 draft，而是标记 needs_human_review
        # 让 quality gate 决定是否继续 revision 或上报人工
        if current < original_wc * min_preserve_ratio:
            logger.warning(
                "revision_handler.underflow_needs_human_review",
                current=current,
                original_wc=original_wc,
                ratio=round(current / original_wc, 3) if original_wc else 0,
                min_preserve_ratio=min_preserve_ratio,
            )
            return (
                revision_content,
                revision_scenes,
                current,
                True,
                "revision_underflow_needs_human_review",
            )

        # 回退到原始 draft
        original_scenes = _parse_scenes(original_content)
        return (
            original_content,
            original_scenes,
            original_wc,
            True,
            "revision_underflow_fallback",
        )

    return revision_content, revision_scenes, current, False, "revision_accepted"
