"""Integration test fixtures and helpers."""

from __future__ import annotations

import contextlib
import json
from typing import Any
from unittest.mock import patch

import pytest

from songyan.db.repository import (
    CharacterRepository,
    ProjectRepository,
)
from songyan.models import Character, ProjectSetting

# ---------------------------------------------------------------------------
# Seed helper
# ---------------------------------------------------------------------------


async def seed_project(project_id: str = "test-proj-001") -> str:
    """Insert a minimal xuanhuan+webnovel project with one character."""
    project = ProjectSetting(
        title="测试玄幻",
        genre_id="xuanhuan",
        mode_id="webnovel",
        protagonist_name="林动",
        protagonist_background="出身卑微的少年",
        core_hook="废柴逆袭",
        target_reader_expectation="热血爽文",
        taboos=["绿帽"],
        target_word_count=100_000,
        tone="热血",
    )
    await ProjectRepository().create(project, project_id)

    from songyan.models.character import DialogueStyleCard
    char = Character(
        character_id="char-001",
        project_id=project_id,
        name="林动",
        role_type="protagonist",
        background="出身卑微",
        dialogue_style_card=DialogueStyleCard(
            character_id="char-001",
            project_id=project_id,
            sentence_length_preference="short",
            common_openers=["哼", "小子"],
            anger_expression="冷笑+反问",
            pause_habit="愤怒时停顿",
        ),
    )
    await CharacterRepository().create(char)
    return project_id


# ---------------------------------------------------------------------------
# Mock LLM fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_call_llm():
    """Fixture that patches all Agent call_llm imports with a sequenced mock.

    Usage in test::

        mock_call_llm.responses = [
            json.dumps({...}),   # goal_planner
            json.dumps({...}),   # creative_director
            "正文内容...",        # writer
            ...
        ]
    """
    async def _mock(
        prompt: str = "",
        *,
        temperature: float = 0.7,
        max_retries: int = 3,
        **kwargs: Any,
    ) -> str:
        responses = _mock.responses  # type: ignore[attr-defined]
        count = _mock._call_count  # type: ignore[attr-defined]
        if count >= len(responses):
            raise RuntimeError(
                f"mock_call_llm ran out of responses (call {count}, "
                f"only {len(responses)} configured). Prompt snippet: {prompt[:80]}"
            )
        resp = responses[count]
        _mock._call_count = count + 1  # type: ignore[attr-defined]
        return resp

    _mock.responses: list[str] = []  # type: ignore[attr-defined]
    _mock._call_count: int = 0  # type: ignore[attr-defined]

    targets = [
        "songyan.agents.goal_planner.call_llm",
        "songyan.agents.creative_director.call_llm",
        "songyan.agents.writer.call_llm",
        "songyan.agents.llm_auditor.call_llm",
        "songyan.agents.literary_auditor.call_llm",
        "songyan.agents.revision_handler.call_llm",
        "songyan.agents.settlement_extractor.call_llm",
        "songyan.agents.summary_writer.call_llm",
    ]

    with contextlib.ExitStack() as stack:
        for target in targets:
            stack.enter_context(patch(target, _mock))
        yield _mock


# ---------------------------------------------------------------------------
# Response builders
# ---------------------------------------------------------------------------


def goal_resp() -> str:
    return json.dumps(
        {
            "target_events": ["发现秘境入口", "击退守卫"],
            "emotional_arc": "紧张→兴奋",
            "hooks": {"opening": "悬崖边被追杀", "closing": "秘境大门开启"},
            "obligations": ["保持主角性格"],
            "word_count_target": 150,
            "chapter_type": "action",
        }
    )


def brief_resp() -> str:
    return json.dumps(
        {
            "creative_intent": "展现主角在绝境中的果敢",
            "required_tensions": [
                {
                    "tension_type": "生存危机",
                    "description": "被强敌追杀至悬崖",
                    "intensity": 8,
                }
            ],
            "forbidden_patterns": ["旁白解释内心", "突然获得无名力量"],
            "allowed_fissures": [],
            "style_constraints": ["快节奏打斗"],
            "reader_contract": "每800字一个爽点",
        }
    )


def writer_resp() -> str:
    filler = (
        "林动稳住呼吸，沿着石壁缓慢前进，灵气在经脉中一寸寸回流。"
        "他没有急着冲动出手，而是观察符文的明暗变化，确认追兵的脚步正在远去。"
    ) * 16
    return (
        "### Scene 1\n\n"
        "林动被逼到悬崖边缘，身后是追来的黑风寨众人。\n\n"
        "「小子，交出玉佩，留你全尸！」领头大汉狞笑道。\n\n"
        "林动冷笑一声，纵身跃下悬崖。\n\n"
        "下落途中，他抓住岩壁上一根藤蔓，荡进一道石缝。\n\n"
        f"{filler}\n\n"
        "### Scene 2\n\n"
        "石缝尽头，一扇青铜大门静静矗立，门上刻满古老符文。\n\n"
        "「这是……古修士洞府？」林动瞳孔一缩。\n\n"
        "他深吸一口气，将手掌按在门上。符文亮起，大门缓缓开启，\n"
        "一股浓郁的灵气扑面而来。\n\n"
        "门后，是一条通往未知的甬道，幽深得看不见尽头。\n"
        f"{filler}\n"
    )


def llm_clean_resp() -> str:
    return json.dumps(
        {
            "issues": [],
            "dimension_scores": {
                "world_consistency": 8.0,
                "character_behavior": 8.0,
                "timeline": 8.0,
                "new_setting_unregistered": 8.0,
                "narrative_pacing": 8.0,
                "narrative_hook": 8.0,
                "info_dump": 8.0,
                "dialogue_distinctness": 8.0,
                "dialogue_subtext": 8.0,
                "description_sensory": 8.0,
                "show_dont_tell": 8.0,
                "genre_numerical": 8.0,
            },
            "cliche_risk_score": 3.0,
            "character_autonomy_score": 7.0,
            "conceptual_idling_score": 2.0,
            "summary": "整体良好",
        }
    )


def llm_critical_resp() -> str:
    return json.dumps(
        {
            "issues": [
                {
                    "issue_id": "i1",
                    "category": "world_consistency",
                    "severity": "critical",
                    "evidence_quote": "古修士洞府",
                    "evidence_location": "第5段",
                    "issue_description": "前文未提及古修士存在",
                    "expected": "应有伏笔铺垫",
                    "actual": "突兀出现",
                    "suggested_fix": "改为发现前人遗迹",
                    "fix_type": "patch",
                    "confidence": 0.9,
                }
            ],
            "dimension_scores": {"world_consistency": 4.0},
            "cliche_risk_score": 5.0,
            "character_autonomy_score": 6.0,
            "conceptual_idling_score": 3.0,
            "summary": "设定一致性有问题",
        }
    )


def literary_resp() -> str:
    return json.dumps(
        {
            "observations": [
                {
                    "observation_type": "excessive_smoothing",
                    "description": "转折略显突兀",
                    "severity": "minor",
                    "affected_text": "纵身跃下悬崖",
                    "recommendation": "可铺垫犹豫瞬间",
                }
            ],
            "overall_quality_score": 6.5,
            "protected_elements": [],
        }
    )


def revision_resp() -> str:
    return json.dumps(
        {
            "patches": [
                {
                    "issue_id": "i1",
                    "original_text": "古修士洞府",
                    "revised_text": "前人遗留的修行之地",
                    "location": "第5段",
                }
            ],
            "revision_notes": "已替换突兀设定",
        }
    )


def settlement_resp() -> str:
    return json.dumps(
        {
            "character_updates": [
                {
                    "character_id": "char-001",
                    "field": "location",
                    "old_value": "悬崖顶",
                    "new_value": "古修洞府入口",
                    "source_quote": "荡进一道石缝",
                }
            ],
            "new_settings": [
                {
                    "setting_name": "青铜大门",
                    "description": "刻满符文的古老门户",
                    "source_quote": "一扇青铜大门静静矗立",
                    "setting_key": "bronze_gate",
                }
            ],
            "foreshadowing_updates": [],
            "numerical_updates": [],
            "validation_status": "valid",
            "validation_errors": [],
        }
    )


def summary_resp() -> str:
    return json.dumps(
        {
            "plot_summary": "林动被逼悬崖，发现洞府",
            "emotional_tone": "紧张兴奋",
        }
    )


def llm_major_resp() -> str:
    """LLM audit with major (not critical) issue — triggers revision."""
    return json.dumps(
        {
            "issues": [
                {
                    "issue_id": "i1",
                    "category": "world_consistency",
                    "severity": "major",
                    "evidence_quote": "古修士洞府",
                    "evidence_location": "第5段",
                    "issue_description": "前文未提及古修士存在",
                    "expected": "应有伏笔铺垫",
                    "actual": "突兀出现",
                    "suggested_fix": "改为发现前人遗迹",
                    "fix_type": "patch",
                    "confidence": 0.8,
                }
            ],
            "dimension_scores": {"world_consistency": 5.0},
            "cliche_risk_score": 4.0,
            "character_autonomy_score": 6.0,
            "conceptual_idling_score": 3.0,
            "summary": "设定一致性有问题",
        }
    )


def llm_non_patchable_resp() -> str:
    """LLM audit with rewrite_scene fix_type — no patchable issues."""
    return json.dumps(
        {
            "issues": [
                {
                    "issue_id": "i1",
                    "category": "world_consistency",
                    "severity": "critical",
                    "evidence_quote": "古修士洞府",
                    "evidence_location": "第5段",
                    "issue_description": "前文未提及古修士存在",
                    "expected": "应有伏笔铺垫",
                    "actual": "突兀出现",
                    "suggested_fix": "整段重写",
                    "fix_type": "rewrite_scene",
                    "confidence": 0.9,
                }
            ],
            "dimension_scores": {"world_consistency": 4.0},
            "cliche_risk_score": 5.0,
            "character_autonomy_score": 6.0,
            "conceptual_idling_score": 3.0,
            "summary": "设定一致性有问题",
        }
    )


def llm_worsening_resp() -> str:
    """LLM audit with more issues and lower score — triggers rebound."""
    return json.dumps(
        {
            "issues": [
                {
                    "issue_id": "i1",
                    "category": "world_consistency",
                    "severity": "critical",
                    "evidence_quote": "古修士洞府",
                    "evidence_location": "第5段",
                    "issue_description": "前文未提及古修士存在",
                    "expected": "应有伏笔铺垫",
                    "actual": "突兀出现",
                    "suggested_fix": "改为发现前人遗迹",
                    "fix_type": "patch",
                    "confidence": 0.9,
                },
                {
                    "issue_id": "i2",
                    "category": "character_behavior",
                    "severity": "critical",
                    "evidence_quote": "林动冷笑一声",
                    "evidence_location": "第3段",
                    "issue_description": "主角性格崩坏",
                    "expected": "应保持谨慎性格",
                    "actual": "突然冷笑",
                    "suggested_fix": "改为咬牙坚持",
                    "fix_type": "patch",
                    "confidence": 0.8,
                },
                {
                    "issue_id": "i3",
                    "category": "timeline",
                    "severity": "major",
                    "evidence_quote": "下落途中",
                    "evidence_location": "第4段",
                    "issue_description": "时间线混乱",
                    "expected": "应有时间感",
                    "actual": "时间跳跃",
                    "suggested_fix": "增加过渡",
                    "fix_type": "patch",
                    "confidence": 0.7,
                },
            ],
            "dimension_scores": {"world_consistency": 3.0, "character_behavior": 3.0},
            "cliche_risk_score": 6.0,
            "character_autonomy_score": 4.0,
            "conceptual_idling_score": 4.0,
            "summary": "多处严重问题",
        }
    )
