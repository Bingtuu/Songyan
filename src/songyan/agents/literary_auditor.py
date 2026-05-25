"""LiteraryAuditor Agent — 文学性诊断，不阻塞流程."""

from __future__ import annotations

import time
import uuid
from typing import Any

import structlog

from songyan.db.review_repo import LiteraryObservationRepository
from songyan.llm.client import call_llm
from songyan.llm.parsing import parse_llm_response
from songyan.models import ContextPackage, LiteraryAuditResult, LiteraryObservation

logger = structlog.get_logger(__name__)

MAX_CONTENT_LENGTH = 8000
VALID_OBSERVATION_TYPES = {
    "character_tooling",
    "conceptual_idling",
    "excessive_smoothing",
    "valuable_fissure",
    "cliche_risk",
    "polyphony_weakness",
    "authorial_intrusion",
}
VALID_SEVERITIES = {"notice", "suggestion", "highlight"}


def _load_prompt_template() -> str:
    """加载 LiteraryAuditor Prompt 模板 — 已迁移到工艺卡系统."""
    from songyan.prompts import get_prompt_loader
    return get_prompt_loader().load_card("literary_auditor").system_prompt


def _render_context_info(ctx: ContextPackage | None) -> str:
    """将 ContextPackage 渲染为上下文信息文本."""
    if ctx is None:
        return "（无额外上下文）"

    lines: list[str] = []

    if ctx.creative_brief and ctx.creative_brief.creative_intent:
        lines.append(f"**创作意图**：{ctx.creative_brief.creative_intent}")

    if ctx.creative_brief and ctx.creative_brief.allowed_fissures:
        lines.append(
            f"**允许裂隙**：{'；'.join(ctx.creative_brief.allowed_fissures)}"
        )

    if ctx.creative_brief and ctx.creative_brief.required_tensions:
        tensions = [
            f"{t.tension_id}（{t.tension_type}，强度{t.intensity}）"
            for t in ctx.creative_brief.required_tensions
        ]
        lines.append(f"**张力地图**：{'；'.join(tensions)}")

    if ctx.chapter_goal and ctx.chapter_goal.target_events:
        lines.append(
            f"**目标事件**：{'；'.join(ctx.chapter_goal.target_events)}"
        )

    return "\n".join(lines) if lines else "（无额外上下文）"


def _render_prompt(content: str, context_package: ContextPackage | None) -> str:
    """渲染 LiteraryAuditor Prompt."""
    from songyan.prompts import get_prompt_loader
    loader = get_prompt_loader()
    card = loader.load_card("literary_auditor")
    template = card.system_prompt
    context_info = _render_context_info(context_package)

    if len(content) > MAX_CONTENT_LENGTH:
        content = content[:MAX_CONTENT_LENGTH] + "\n...（正文已截断）"

    prompt = template.replace("{{ context_info }}", context_info)
    prompt = prompt.replace("{{ content }}", content)
    return prompt


def _validate_observation_type(value: str) -> str | None:
    """验证 observation_type 是否有效，无效时返回 None."""
    if value in VALID_OBSERVATION_TYPES:
        return value
    logger.warning("literary_auditor.invalid_observation_type", observation_type=value)
    return None


def _validate_severity(value: str) -> str:
    """验证 severity，无效时回退到 'suggestion'."""
    if value in VALID_SEVERITIES:
        return value
    logger.warning("literary_auditor.invalid_severity", severity=value)
    return "suggestion"


def _build_observation(data: dict[str, Any], index: int) -> LiteraryObservation | None:
    """从字典构建 LiteraryObservation，无效时返回 None."""
    obs_type = _validate_observation_type(data.get("observation_type", ""))
    if obs_type is None:
        return None

    observation_id = data.get("observation_id", f"obs_{index:03d}")
    if not observation_id:
        observation_id = f"obs_{index:03d}"

    severity = _validate_severity(data.get("severity", "suggestion"))
    preserve = bool(data.get("preserve", False))

    # valuable_fissure 强制 preserve = True
    if obs_type == "valuable_fissure":
        preserve = True

    return LiteraryObservation(
        observation_id=observation_id,
        observation_type=obs_type,  # type: ignore[arg-type]
        description=data.get("description", ""),
        evidence_quote=data.get("evidence_quote"),
        severity=severity,  # type: ignore[arg-type]
        recommendation=data.get("recommendation", ""),
        preserve=preserve,
    )


def _parse_score(value: Any) -> float:
    """解析评分并 clamp 到 0-10."""
    try:
        return max(0.0, min(10.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _build_literary_audit_result(data: dict[str, Any]) -> LiteraryAuditResult:
    """从解析后的字典构建 LiteraryAuditResult."""
    observations: list[LiteraryObservation] = []
    for i, item in enumerate(data.get("observations", [])):
        if isinstance(item, dict):
            obs = _build_observation(item, i)
            if obs is not None:
                observations.append(obs)

    return LiteraryAuditResult(
        auditor_id="literary_auditor",
        observations=observations,
        literary_quality_score=_parse_score(data.get("literary_quality_score")),
        character_autonomy_score=_parse_score(data.get("character_autonomy_score")),
        conceptual_grounding_score=_parse_score(data.get("conceptual_grounding_score")),
        fissure_preservation_score=_parse_score(data.get("fissure_preservation_score")),
        summary=data.get("summary", ""),
    )


# ---------------------------------------------------------------------------
# Main Entry
# ---------------------------------------------------------------------------
async def run_literary_audit(
    content: str,
    context_package: ContextPackage | None = None,
    temperature: float = 0.5,
) -> LiteraryAuditResult:
    """运行文学性诊断（可选，不阻塞流程）.

    Args:
        content: 章节正文
        context_package: 上下文包（提供创作意图、张力地图、允许裂隙等）
        temperature: LLM 温度（默认 0.5，比 LLMAuditor 0.3 略高，鼓励创造性观察）

    Returns:
        LiteraryAuditResult
    """
    start_time = time.perf_counter()

    prompt = _render_prompt(content, context_package)
    llm_response = await call_llm(prompt, temperature=temperature)

    data = parse_llm_response(llm_response)
    result = _build_literary_audit_result(data)

    duration_ms = int((time.perf_counter() - start_time) * 1000)
    result.duration_ms = duration_ms

    logger.info(
        "literary_auditor.done",
        observations_count=len(result.observations),
        literary_quality=result.literary_quality_score,
        character_autonomy=result.character_autonomy_score,
        duration_ms=duration_ms,
    )
    return result


async def save_literary_audit(
    db: LiteraryObservationRepository,
    version_id: str,
    result: LiteraryAuditResult,
    observation_id: str | None = None,
) -> None:
    """保存 LiteraryAuditResult 到 literary_observations 表.

    Args:
        db: LiteraryObservationRepository
        version_id: 章节版本 ID
        result: LiteraryAuditResult
        observation_id: 可选的观察记录 ID，自动生成
    """
    if observation_id is None:
        observation_id = f"lit-{version_id}-{uuid.uuid4().hex[:8]}"

    await db.create(result, observation_id, version_id)
    logger.info(
        "literary_auditor.saved",
        observation_id=observation_id,
        version_id=version_id,
    )
