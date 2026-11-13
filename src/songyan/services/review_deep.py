"""tech-m4-followup 步 3：``review --deep`` 显式 LLM 深审（B4 成本前置 / B5 零写库 / B6 口径）。

输入三件套：被审工作稿正文 + 本章 approved 圣经 + 上一章 accepted 摘要（120 字截断口径，
与 continue 注入同源）。检查四条：fact（事实一致性）/ continuity（连续性）/
repetition（复读复核）/ voice（文风视角，只说「建议人复核」）。

全程零写库；LLM 调用走 ``call_llm`` 标准遥测（调用方绑 ``agent="review.deep"``）。
"""

from __future__ import annotations

import json
import re

import structlog
from structlog.contextvars import bound_contextvars

from songyan.exceptions import SongyanError
from songyan.services.review_report import ReviewFinding
from songyan.utils.cost_estimator import count_tokens, estimate_cost_from_tokens

logger = structlog.get_logger(__name__)

#: 深审检查口径（B6）；prompt 与解析共用
DEEP_CHECKS = ("fact", "continuity", "repetition", "voice")

#: completion token 估价常量（深审输出是结构化 findings，不是正文）
_COMPLETION_TOKEN_ESTIMATE = 600

_SEVERITIES = ("hard", "warning", "info")

_PROMPT_PREFIX = (
    "你是松烟的章内深审。只依据【事实圣经】与【上一章摘要】审【被审工作稿】，"
    "不要引用未入典事实，不要评价文学好坏。\n"
    "检查四条口径：\n"
    "- fact：正文与事实圣经的实体/属性/时间锚矛盾（severity=hard）；\n"
    "- continuity：与上一章摘要的人物状态/道具/位置断裂（hard 或 warning）；\n"
    "- repetition：段落或句子复读（warning 或 info，复核启发式命中）；\n"
    "- voice：人称/时态/视角漂移（info；只写「建议人复核」，不评优劣）。\n"
    "输出必须是 JSON 数组（不要前言后语），元素字段："
    "severity（hard|warning|info）、check（fact|continuity|repetition|voice）、"
    "message（问题一句话）、evidence（被审稿原文片段）、location（章节内位置）。\n"
    "没有问题输出空数组。严禁编造：evidence 必须引用被审稿原文。\n\n"
)


class DeepReviewError(SongyanError):
    """深审 LLM 产出无法解析为结构化 findings。"""


def build_deep_review_prompt(
    *,
    content: str,
    bible_text: str,
    previous_summary: str,
) -> str:
    """拼装深审 prompt（输入三件套，B6）。拼接而非 format——模板含 JSON 花括号。"""
    return (
        _PROMPT_PREFIX
        + "【事实圣经】\n"
        + (bible_text or "（空）")
        + "\n\n【上一章摘要】\n"
        + (previous_summary or "（无）")
        + "\n\n【被审工作稿】\n"
        + content
    )


def estimate_deep_review_cost(prompt: str) -> tuple[float, str]:
    """按 prompt token 估价（completion 取常量估计）；返回 (费用, 模型)。"""
    from songyan.llm.client import resolve_llm_config

    model = resolve_llm_config("reviewer").model
    prompt_tokens = count_tokens(prompt)
    cost = estimate_cost_from_tokens(
        prompt_tokens, _COMPLETION_TOKEN_ESTIMATE, model
    )
    return float(cost), model


def parse_deep_findings(raw: str) -> list[ReviewFinding]:
    """解析深审 JSON 输出为 ``ReviewFinding``（source 恒为 ``deep``）。

    容错：markdown 代码块包裹、非法 severity 降级 info、缺省字段补空。
    完全无法解析抛 ``DeepReviewError``。
    """
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if match is None:
        raise DeepReviewError(f"深审产出无 JSON 数组：{raw[:120]!r}")
    try:
        items = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise DeepReviewError(f"深审产出 JSON 解析失败：{exc}") from exc
    if not isinstance(items, list):
        raise DeepReviewError("深审产出 JSON 不是数组")

    findings: list[ReviewFinding] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        severity = str(item.get("severity", "info"))
        if severity not in _SEVERITIES:
            severity = "info"
        findings.append(
            ReviewFinding(
                severity=severity,  # type: ignore[arg-type]
                source="deep",
                message=str(item.get("message", "")),
                evidence=str(item.get("evidence", "")),
                location=str(item.get("location", "")),
            )
        )
    return findings


async def run_deep_review(
    project_id: str,
    chapter: int,
    *,
    content: str,
    bible_text: str,
    previous_summary: str,
) -> list[ReviewFinding]:
    """执行深审（单调用）；解析失败抛 ``DeepReviewError``。

    遥测归因：绑定 project/chapter/agent=review.deep，由 ``call_llm``
    内部记 ``llm_call_usage``（无第二记账，task 226 机制）。
    """
    from songyan.llm import call_llm

    prompt = build_deep_review_prompt(
        content=content,
        bible_text=bible_text,
        previous_summary=previous_summary,
    )
    with bound_contextvars(
        project_id=project_id, chapter_number=chapter, agent="review.deep"
    ):
        raw = await call_llm(prompt, role="reviewer")
    findings = parse_deep_findings(raw)
    logger.info(
        "review.deep.completed",
        project_id=project_id,
        chapter=chapter,
        findings=len(findings),
    )
    return findings
