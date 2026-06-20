"""CreativeDirector Brief 构建器 — 从 LLM 响应构建 CreativeBrief."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any

import structlog

from songyan.exceptions import LLMResponseParseError
from songyan.models.chapter import ChapterGoal
from songyan.models.creative_mode import (
    CreativeBrief,
    EmotionArcItem,
    PunchPoint,
    Tension,
)

logger = structlog.get_logger(__name__)

VALID_TENSION_TYPES = {
    "value_conflict",
    "information_asymmetry",
    "power_imbalance",
    "emotional_contrast",
    "temporal_pressure",
}

VALID_PUNCH_TYPES = {
    "sensory_shock",
    "emotional_switch",
    "revelation",
    "physical_cost",
    "cognitive_twist",
}

VALID_DOMINANT_SENSES = {
    "visual",
    "auditory",
    "tactile",
    "pain",
    "proprioception",
}

MIN_FORBIDDEN_PATTERNS = 3
DEFAULT_FORBIDDEN_PATTERNS = [
    "避免使用陈词滥调的表达方式",
    "禁止空洞的环境描写堆砌",
    "不要让角色做出毫无铺垫的行为转变",
]

_SETTING_CONSISTENCY_PATTERN = (
    "禁止引入与种子设定无逻辑推导关系的新组织、新机构、新概念"
    "（如种子设定中没有的机构名称，就不能凭空出现）"
)


def _extract_json(text: str) -> str:
    """从 LLM 响应中提取 JSON 字符串."""
    code_block_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if code_block_match:
        return code_block_match.group(1).strip()

    json_match = re.search(r"(\{.*\})", text, re.DOTALL)
    if json_match:
        return json_match.group(1).strip()

    return text.strip()


def _parse_llm_response(text: str) -> dict[str, Any]:
    """解析 LLM 响应为字典."""
    json_text = _extract_json(text)
    try:
        return json.loads(json_text)
    except json.JSONDecodeError as e:
        msg = f"LLM 返回内容无法解析为 JSON: {e}"
        raise LLMResponseParseError(msg, raw_response=text) from e


def _validate_tension(tension_data: dict[str, Any]) -> Tension | None:
    """验证并构建 Tension 对象，无效时返回 None."""
    tension_type = tension_data.get("tension_type", "")
    if tension_type not in VALID_TENSION_TYPES:
        logger.warning(
            "creative_director.invalid_tension_type",
            received=tension_type,
            valid=list(VALID_TENSION_TYPES),
        )
        return None

    intensity = tension_data.get("intensity", 0.5)
    try:
        intensity = float(intensity)
        intensity = max(0.0, min(1.0, intensity))
    except (ValueError, TypeError):
        intensity = 0.5

    characters_involved = tension_data.get("characters_involved", [])
    if not isinstance(characters_involved, list):
        characters_involved = []

    return Tension(
        tension_id=tension_data.get("tension_id", "") or f"tension_{uuid.uuid4().hex[:6]}",
        description=(
            tension_data.get("description", "")
            if isinstance(tension_data.get("description"), str)
            else ""
        ),
        tension_type=tension_type,
        characters_involved=[str(c) for c in characters_involved],
        resolution=(
            tension_data.get("resolution", "")
            if isinstance(tension_data.get("resolution"), str)
            else ""
        ),
        intensity=intensity,
    )


def _validate_punch_point(data: dict[str, Any]) -> PunchPoint | None:
    """验证并构建单个 PunchPoint 对象."""
    ptype = data.get("punch_type")
    if ptype not in VALID_PUNCH_TYPES:
        return None
    intensity = data.get("intensity", 0.5)
    if not isinstance(intensity, (int, float)):
        intensity = 0.5
    intensity = max(0.0, min(1.0, intensity))
    target_scene = data.get("target_scene", 1)
    if not isinstance(target_scene, int) or target_scene < 1:
        target_scene = 1
    dominant = data.get("dominant_sense")
    if dominant not in VALID_DOMINANT_SENSES:
        dominant = None
    return PunchPoint(
        punch_id=str(data.get("punch_id", "")),
        description=str(data.get("description", "")),
        punch_type=ptype,
        target_scene=target_scene,
        intensity=intensity,
        dominant_sense=dominant,
    )


def _validate_emotion_arc_item(data: dict[str, Any]) -> EmotionArcItem | None:
    """验证并构建单个 EmotionArcItem 对象."""
    scene = data.get("scene")
    if not isinstance(scene, int) or scene < 1:
        return None
    return EmotionArcItem(
        scene=scene,
        from_emotion=str(data.get("from_emotion", "")),
        to_emotion=str(data.get("to_emotion", "")),
    )


def _ensure_forbidden_patterns(patterns: list[Any]) -> list[str]:
    """确保 forbidden_patterns 至少 MIN_FORBIDDEN_PATTERNS 个具体条目，并包含设定连续性约束."""
    valid = [str(p) for p in patterns if isinstance(p, str) and p.strip()]

    # 自动注入设定连续性约束（如果 LLM 没有提供）
    if not any("种子设定" in p or "逻辑推导" in p for p in valid):
        valid.append(_SETTING_CONSISTENCY_PATTERN)

    if len(valid) < MIN_FORBIDDEN_PATTERNS:
        needed = MIN_FORBIDDEN_PATTERNS - len(valid)
        valid.extend(DEFAULT_FORBIDDEN_PATTERNS[:needed])
        logger.warning(
            "creative_director.patterns_filled",
            original_count=len(valid) - needed,
            filled_count=needed,
        )
    return valid


def _build_creative_brief(
    data: dict[str, Any],
    mode_id: str,
    chapter_goal: ChapterGoal,
) -> CreativeBrief:
    """从解析后的字典构建 CreativeBrief，处理缺失字段和越界值."""
    # 解析 required_tensions
    tensions: list[Tension] = []
    raw_tensions = data.get("required_tensions", [])
    if isinstance(raw_tensions, list):
        for item in raw_tensions:
            if isinstance(item, dict):
                tension = _validate_tension(item)
                if tension is not None:
                    tensions.append(tension)

    # 解析 forbidden_patterns
    raw_patterns = data.get("forbidden_patterns", [])
    if isinstance(raw_patterns, list):
        forbidden_patterns = _ensure_forbidden_patterns(raw_patterns)
    else:
        forbidden_patterns = DEFAULT_FORBIDDEN_PATTERNS.copy()

    # 解析 punch_points
    punch_points: list[PunchPoint] = []
    raw_punches = data.get("punch_points", [])
    if isinstance(raw_punches, list):
        for item in raw_punches:
            if isinstance(item, dict):
                punch = _validate_punch_point(item)
                if punch is not None:
                    punch_points.append(punch)

    # 解析 emotion_arc
    emotion_arc: list[EmotionArcItem] = []
    raw_arc = data.get("emotion_arc", [])
    if isinstance(raw_arc, list):
        for item in raw_arc:
            if isinstance(item, dict):
                arc_item = _validate_emotion_arc_item(item)
                if arc_item is not None:
                    emotion_arc.append(arc_item)

    # 解析其他列表字段
    def _to_str_list(value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(v) for v in value if isinstance(v, (str, int, float))]
        return []

    # Task 098: 解析四信号
    _narrative_fullness = 0.0
    _raw_fullness = data.get("narrative_fullness")
    if isinstance(_raw_fullness, (int, float)):
        _narrative_fullness = max(0.0, min(1.0, float(_raw_fullness)))

    _character_focus: list[dict] = []
    _raw_focus = data.get("character_focus")
    if isinstance(_raw_focus, list):
        for item in _raw_focus:
            if isinstance(item, dict):
                _character_focus.append(
                    {
                        "character_id": str(item.get("character_id", "")),
                        "detail_level": str(item.get("detail_level", "full")),
                    }
                )

    _foreshadowing_due: list[str] = []
    _raw_due = data.get("foreshadowing_due")
    if isinstance(_raw_due, list):
        _foreshadowing_due = [str(v) for v in _raw_due if isinstance(v, (str, int, float))]

    _focal_distance = "mid"
    _raw_fd = data.get("focal_distance")
    if isinstance(_raw_fd, str) and _raw_fd in ("close", "mid", "wide", "disruption"):
        _focal_distance = _raw_fd

    return CreativeBrief(
        mode_id=data.get("mode_id", mode_id),
        chapter_goal=chapter_goal,
        creative_intent=(
            data.get("creative_intent", "") if isinstance(data.get("creative_intent"), str) else ""
        ),
        required_tensions=tensions,
        forbidden_patterns=forbidden_patterns,
        allowed_fissures=_to_str_list(data.get("allowed_fissures")),
        style_constraints=_to_str_list(data.get("style_constraints")),
        reader_contract=(
            data.get("reader_contract", "") if isinstance(data.get("reader_contract"), str) else ""
        ),
        polyphony_notes=_to_str_list(data.get("polyphony_notes")),
        punch_points=punch_points,
        emotion_arc=emotion_arc,
        narrative_fullness=_narrative_fullness,
        character_focus=_character_focus,
        foreshadowing_due=_foreshadowing_due,
        focal_distance=_focal_distance,
    )
