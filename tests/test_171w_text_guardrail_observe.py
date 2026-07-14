"""Task 171w-c: text guardrail observe tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from songyan.db.connection import get_db
from songyan.db.continuity_repo import SettingTrackingRepository
from songyan.db.repository import ChapterHeadRepository, ChapterVersionRepository, ProjectRepository
from songyan.db.review_repo import CreativeBriefRepository
from songyan.evals.literary_guardrail_observe import (
    audit_171w_text_guardrails,
    check_supporting_character_goal_presence,
    observe_active_choice,
    observe_concept_budget,
    observe_supporting_character_goal,
    render_text_guardrail_observe_section,
)
from songyan.models import (
    ChapterGoal,
    ChapterHead,
    ChapterVersion,
    CreativeBrief,
    NewConceptBudget,
    ProjectSetting,
    SupportingCharacterGoal,
)

pytestmark = pytest.mark.performance


def _brief(chapter_number: int, max_concepts: int = 1) -> CreativeBrief:
    return CreativeBrief(
        mode_id="webnovel",
        chapter_goal=ChapterGoal(chapter_number=chapter_number),
        new_concept_budget=NewConceptBudget(
            max_new_core_concepts=max_concepts,
            grounding_scene="量子锁阈值被迫落地",
        ),
        supporting_character_goal=SupportingCharacterGoal(
            character="赵铭",
            goal="带小周离开",
            conflict_with_protagonist="不愿继续深入",
            scene_consequence="迫使林渊改变路线",
        ),
    )


async def _seed_project(project_id: str) -> None:
    await ProjectRepository().create(
        ProjectSetting(
            title="171w-c 测试",
            genre_id="scifi",
            protagonist_name="林渊",
        ),
        project_id,
    )


async def _seed_setting_snapshot(
    project_id: str,
    setting_key: str,
    setting_name: str,
    source_quote: str,
) -> None:
    async with get_db() as conn:
        await conn.execute(
            """INSERT INTO setting_snapshots (
                setting_id, project_id, setting_name, description,
                source_quote, setting_key
            ) VALUES (?, ?, ?, ?, ?, ?)""",
            (
                f"ss-{setting_key}",
                project_id,
                setting_name,
                "测试设定",
                source_quote,
                setting_key,
            ),
        )
        await conn.commit()


def test_supporting_character_goal_observe_passes_with_consequence() -> None:
    text = "赵铭拒绝按原路线撤离，坚持带小周离开，这迫使林渊改变路线。"

    result = observe_supporting_character_goal(
        text,
        {"character": "赵铭", "goal": "带小周离开"},
    )

    assert result.character_present
    assert result.action_evidence
    assert result.consequence_evidence
    assert result.passed


def test_supporting_character_goal_observe_fails_when_character_missing() -> None:
    result = observe_supporting_character_goal(
        "林渊独自穿过控制室，没有任何人打断。",
        {"character": "赵铭", "goal": "带小周离开"},
    )

    assert not result.character_present
    assert not result.passed


def test_active_choice_observe_distinguishes_passive_continuation() -> None:
    passed = observe_active_choice("林渊主动切断供能，代价是暴露位置。", "林渊")
    failed = observe_active_choice("林渊继续破解协议，等待倒计时逼近。", "林渊")

    assert passed.passed
    assert passed.cost_evidence
    assert not failed.passed
    assert failed.passive_only


def test_concept_budget_groups_related_settings() -> None:
    result = observe_concept_budget(
        "量子锁阈值被迫落地，控制台给出回震。",
        [
            {
                "setting_key": "quantum_lock.threshold",
                "setting_name": "量子锁-阈值",
                "source_quote": "量子锁阈值被迫落地",
            },
            {
                "setting_key": "quantum_lock.console",
                "setting_name": "量子锁-控制台",
                "source_quote": "控制台给出回震",
            },
        ],
        max_new_core_concepts=1,
    )

    assert result.raw_new_settings_count == 2
    assert result.core_concept_count == 1
    assert result.grounded_new_concept_count == 1
    assert result.passed


async def test_audit_171w_text_guardrails_reads_db_facts(test_db: Path) -> None:
    project_id = "proj-171w-c"
    await _seed_project(project_id)
    await CreativeBriefRepository().create(_brief(205), "cb-205", project_id, 205)
    content = (
        "赵铭拒绝按原路线撤离，坚持带小周离开，这迫使林渊改变路线。\n"
        "林渊主动切断供能，代价是暴露位置。\n"
        "量子锁阈值被迫落地，控制台给出回震。"
    )
    await ChapterVersionRepository().create(
        ChapterVersion(
            version_id="v-205",
            project_id=project_id,
            chapter_number=205,
            version_number=1,
            version_type="accepted",
            content=content,
            creative_brief_id="cb-205",
        )
    )
    await ChapterHeadRepository().update(
        ChapterHead(
            project_id=project_id,
            chapter_number=205,
            current_version_id="v-205",
            accepted_version_id="v-205",
            status="accepted",
        )
    )
    await SettingTrackingRepository().create(
        "st-1",
        project_id,
        "quantum_lock.threshold",
        "量子锁-阈值",
        "阈值",
        205,
    )
    await SettingTrackingRepository().create(
        "st-2",
        project_id,
        "quantum_lock.console",
        "量子锁-控制台",
        "控制台",
        205,
    )
    await _seed_setting_snapshot(
        project_id,
        "quantum_lock.threshold",
        "量子锁-阈值",
        "量子锁阈值被迫落地",
    )
    await _seed_setting_snapshot(
        project_id,
        "quantum_lock.console",
        "量子锁-控制台",
        "控制台给出回震",
    )

    rows = await audit_171w_text_guardrails(project_id, 205, 205)

    assert len(rows) == 1
    row = rows[0]
    assert row.supporting_goal.passed
    assert row.active_choice is not None
    assert row.active_choice.passed
    assert row.concept_budget.raw_new_settings_count == 2
    assert row.concept_budget.core_concept_count == 1
    assert row.concept_budget.passed
    assert row.passed


async def test_audit_171w_text_guardrails_flags_concept_budget_spike(
    test_db: Path,
) -> None:
    project_id = "proj-171w-c-spike"
    await _seed_project(project_id)
    await CreativeBriefRepository().create(_brief(217), "cb-217", project_id, 217)
    await ChapterVersionRepository().create(
        ChapterVersion(
            version_id="v-217",
            project_id=project_id,
            chapter_number=217,
            version_number=1,
            version_type="accepted",
            content="林渊主动关闭终端，代价是暴露位置。赵铭拒绝撤离，迫使林渊改变路线。",
            creative_brief_id="cb-217",
        )
    )
    await ChapterHeadRepository().update(
        ChapterHead(
            project_id=project_id,
            chapter_number=217,
            current_version_id="v-217",
            accepted_version_id="v-217",
            status="accepted",
        )
    )
    await SettingTrackingRepository().create(
        "st-a", project_id, "concept.alpha", "量子锁-阈值", "a", 217
    )
    await SettingTrackingRepository().create(
        "st-b", project_id, "concept.beta", "审判序列-阈值", "b", 217
    )

    rows = await audit_171w_text_guardrails(project_id, 217, 217)

    assert rows[0].concept_budget.raw_new_settings_count == 2
    assert rows[0].concept_budget.core_concept_count == 2
    assert not rows[0].concept_budget.passed


def test_render_text_guardrail_observe_section() -> None:
    active = observe_active_choice("林渊主动切断供能，代价是暴露位置。", "林渊")
    supporting = observe_supporting_character_goal(
        "赵铭拒绝撤离，迫使林渊改变路线。",
        {"character": "赵铭", "goal": "撤离"},
    )
    concept = observe_concept_budget("", [], max_new_core_concepts=1)

    from songyan.evals.literary_guardrail_observe import LiteraryGuardrailObservationRow

    section = render_text_guardrail_observe_section(
        [
            LiteraryGuardrailObservationRow(
                chapter_number=205,
                accepted_version_id="v-205",
                supporting_goal=supporting,
                active_choice=active,
                concept_budget=concept,
            )
        ]
    )

    assert "171w-c 正文护栏 observe" in section
    assert "主动选择通过：1/1" in section


class TestSupportingCharacterGoalIssue:
    """check_supporting_character_goal_presence → ReviewIssue."""

    def test_returns_none_when_character_appears(self) -> None:
        brief = CreativeBrief(
            mode_id="webnovel",
            chapter_goal=ChapterGoal(chapter_number=205),
            supporting_character_goal=SupportingCharacterGoal(
                character="赵铭", goal="撤离",
            ),
        )
        result = check_supporting_character_goal_presence(
            "赵铭拦在门前，拒绝让路。", brief, version_id="v-205",
        )
        assert result is None

    def test_returns_issue_when_character_missing(self) -> None:
        brief = CreativeBrief(
            mode_id="webnovel",
            chapter_goal=ChapterGoal(chapter_number=205),
            supporting_character_goal=SupportingCharacterGoal(
                character="赵铭", goal="撤离",
            ),
        )
        result = check_supporting_character_goal_presence(
            "林渊独自走向控制台。", brief, version_id="v-205",
        )
        assert result is not None
        assert result.severity == "major"
        assert result.category.value == "character_behavior"
        assert result.fix_type == "patch"
        assert "赵铭" in result.issue_description
        assert "赵铭" in result.expected

    def test_returns_none_when_no_goal(self) -> None:
        brief = CreativeBrief(
            mode_id="webnovel",
            chapter_goal=ChapterGoal(chapter_number=205),
        )
        result = check_supporting_character_goal_presence(
            "正文内容。", brief,
        )
        assert result is None

    def test_returns_none_when_goal_character_empty(self) -> None:
        brief = CreativeBrief(
            mode_id="webnovel",
            chapter_goal=ChapterGoal(chapter_number=205),
            supporting_character_goal=SupportingCharacterGoal(
                character="", goal="撤离",
            ),
        )
        result = check_supporting_character_goal_presence(
            "正文内容。", brief,
        )
        assert result is None

    def test_returns_none_when_brief_is_none(self) -> None:
        result = check_supporting_character_goal_presence("正文。", None)
        assert result is None
