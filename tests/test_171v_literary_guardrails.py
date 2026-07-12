"""Task 171v: Ch200+ 文学性与可读性护栏测试."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

from songyan.agents.creative_director import _build_creative_brief, generate_creative_brief
from songyan.agents.rule_auditor import detect_fatigue_motifs, run_rule_audit
from songyan.agents.writer import _build_creative_brief_snapshot, _render_prompt
from songyan.models import (
    ChapterGoal,
    Character,
    ContextPackage,
    CreativeBrief,
    CreativeModeProfile,
    FatigueMotifReplacement,
    GenreProfile,
    NewConceptBudget,
    ProtagonistActiveChoice,
    SupportingCharacterGoal,
)
from songyan.models.project import ProjectSetting


def _goal(chapter_number: int = 201) -> ChapterGoal:
    return ChapterGoal(
        chapter_number=chapter_number,
        target_events=["切断审判序列的外部供能"],
        hooks=["观察者延迟回应"],
        chapter_type="转折",
        word_count_target=3000,
    )


def _project() -> ProjectSetting:
    return ProjectSetting(
        title="松岩测试",
        genre_id="scifi",
        protagonist_name="林渊",
        core_hook="协议尽头仍有人类选择",
    )


def _genre() -> GenreProfile:
    return GenreProfile(
        id="scifi",
        name="硬科幻",
        writer_rules=["行动承载设定"],
    )


def _mode() -> CreativeModeProfile:
    return CreativeModeProfile(id="webnovel", name="网文模式")


def _characters() -> list[Character]:
    return [
        Character(
            character_id="c-linyuan",
            project_id="proj-171v",
            name="林渊",
            role_type="protagonist",
        ),
        Character(
            character_id="c-zhaoming",
            project_id="proj-171v",
            name="赵铭",
            role_type="supporting",
            goals=["把小周安全带离审判舱"],
        ),
    ]


def _llm_response(**overrides: object) -> str:
    data: dict[str, object] = {
        "mode_id": "webnovel",
        "creative_intent": "推进审判序列冲突",
        "required_tensions": [],
        "forbidden_patterns": ["禁止空洞协议解释"],
        "style_constraints": ["短句推进"],
        "reader_contract": "保持悬念",
    }
    data.update(overrides)
    return json.dumps(data, ensure_ascii=False)


def test_build_creative_brief_parses_171v_fields() -> None:
    """CreativeDirector 解析 LLM 输出的 171v 结构字段."""
    brief = _build_creative_brief(
        {
            "protagonist_active_choice": {
                "choice": "林渊主动切断供能",
                "alternatives": ["继续等待", "交给观察者处理"],
                "cost": "暴露自己的位置",
                "irreversible_consequence": "审判舱失去回滚机会",
            },
            "new_concept_budget": {
                "max_new_core_concepts": 1,
                "grounding_scene": "供能断路现场",
                "forbidden_mode": "禁止连续解释协议机制",
            },
            "fatigue_motif_replacements": [
                {
                    "overused": "左臂发烫",
                    "alternatives": ["设备回震", "呼吸节奏"],
                }
            ],
            "supporting_character_goal": {
                "character": "赵铭",
                "goal": "带小周离开",
                "conflict_with_protagonist": "不愿继续深入",
                "scene_consequence": "迫使林渊改变路线",
            },
        },
        "webnovel",
        _goal(),
    )

    assert brief.protagonist_active_choice is not None
    assert brief.protagonist_active_choice.cost == "暴露自己的位置"
    assert brief.new_concept_budget is not None
    assert brief.new_concept_budget.max_new_core_concepts == 1
    assert brief.fatigue_motif_replacements[0].overused == "左臂发烫"
    assert brief.supporting_character_goal is not None
    assert brief.supporting_character_goal.character == "赵铭"


async def test_generate_creative_brief_injects_default_171v_guardrails() -> None:
    """LLM 未输出 171v 字段时，CreativeDirector 仍注入可执行护栏."""
    with patch(
        "songyan.agents.creative_director.call_llm",
        new_callable=AsyncMock,
        return_value=_llm_response(),
    ), patch(
        "songyan.agents.creative_director._load_active_settings_to_recycle",
        new=AsyncMock(return_value=[]),
    ), patch(
        "songyan.agents.creative_director.build_concept_budget_constraint",
        new=AsyncMock(return_value=""),
    ), patch(
        "songyan.agents.creative_director._load_recent_accepted_chapter_texts",
        new=AsyncMock(return_value=[]),
    ):
        brief = await generate_creative_brief(
            project_id="proj-171v",
            project=_project(),
            chapter_goal=_goal(chapter_number=205),
            genre_profile=_genre(),
            mode_profile=_mode(),
            characters=_characters(),
        )

    assert brief.protagonist_active_choice is not None
    assert "林渊主动选择" in brief.protagonist_active_choice.choice
    assert brief.new_concept_budget is not None
    assert brief.new_concept_budget.max_new_core_concepts == 1
    assert brief.supporting_character_goal is not None
    assert brief.supporting_character_goal.character == "赵铭"
    assert any("角色主动选择护栏" in item for item in brief.style_constraints)
    assert any("概念密度护栏" in item for item in brief.style_constraints)
    assert any("配角独立目标护栏" in item for item in brief.style_constraints)


async def test_generate_creative_brief_injects_recent_motif_replacements() -> None:
    """近期 accepted 正文母题过密时，向 Writer 注入替代表达建议."""
    recent_text = "左臂发烫。\n左臂发烫。\n左臂发烫。\n金属化左臂再次收紧。"
    with patch(
        "songyan.agents.creative_director.call_llm",
        new_callable=AsyncMock,
        return_value=_llm_response(),
    ), patch(
        "songyan.agents.creative_director._load_active_settings_to_recycle",
        new=AsyncMock(return_value=[]),
    ), patch(
        "songyan.agents.creative_director.build_concept_budget_constraint",
        new=AsyncMock(return_value=""),
    ), patch(
        "songyan.agents.creative_director._load_recent_accepted_chapter_texts",
        new=AsyncMock(return_value=[recent_text]),
    ):
        brief = await generate_creative_brief(
            project_id="proj-171v",
            project=_project(),
            chapter_goal=_goal(),
            genre_profile=_genre(),
            mode_profile=_mode(),
            characters=_characters(),
        )

    assert brief.fatigue_motif_replacements
    assert brief.fatigue_motif_replacements[0].overused == "左臂发烫"
    assert any("母题疲劳替代表达" in item for item in brief.style_constraints)
    assert any("设备回震" in item for item in brief.style_constraints)


def test_writer_prompt_and_snapshot_carry_171v_guardrails() -> None:
    """Writer 能通过 style_constraints 看到 171v 护栏，metadata 也能回放."""
    goal = _goal()
    brief = CreativeBrief(
        mode_id="webnovel",
        chapter_goal=goal,
        style_constraints=[
            "## 角色主动选择护栏（Task 171v）\n- 主动选择：林渊主动切断供能",
            "## 概念密度护栏（Task 171v）\n- 本章最多新增核心概念：1",
        ],
        protagonist_active_choice=ProtagonistActiveChoice(
            choice="林渊主动切断供能",
            alternatives=["等待观察者"],
            cost="暴露位置",
            irreversible_consequence="审判舱失去回滚机会",
        ),
        new_concept_budget=NewConceptBudget(
            max_new_core_concepts=1,
            grounding_scene="供能断路现场",
        ),
        fatigue_motif_replacements=[
            FatigueMotifReplacement(
                overused="左臂发烫",
                alternatives=["设备回震"],
            )
        ],
        supporting_character_goal=SupportingCharacterGoal(
            character="赵铭",
            goal="带小周离开",
            conflict_with_protagonist="路线冲突",
            scene_consequence="迫使林渊改变路线",
        ),
    )
    ctx = ContextPackage(chapter_goal=goal, creative_brief=brief)

    prompt = _render_prompt(ctx)
    snapshot = _build_creative_brief_snapshot(ctx)

    assert "角色主动选择护栏" in prompt
    assert "本章最多新增核心概念：1" in prompt
    assert snapshot["protagonist_active_choice"]["choice"] == "林渊主动切断供能"
    assert snapshot["new_concept_budget"]["max_new_core_concepts"] == 1
    assert snapshot["fatigue_motif_replacements"][0]["overused"] == "左臂发烫"
    assert snapshot["supporting_character_goal"]["character"] == "赵铭"


def test_rule_auditor_motif_fatigue_is_observe_only() -> None:
    """母题疲劳扫描产生 observe 信号，不作为硬清洁问题."""
    text = (
        "林渊的指尖悬停在控制台上。\n\n"
        "手指悬停的半秒里，他改写了路线。\n\n"
        "指尖再次悬停，却没有等待协议回应。"
    )

    matches = detect_fatigue_motifs(text, threshold=2)
    result = run_rule_audit(text)

    assert matches[0].motif == "指尖悬停"
    assert result.motif_fatigue_count == 1
    assert result.text_artifact_count == 0
