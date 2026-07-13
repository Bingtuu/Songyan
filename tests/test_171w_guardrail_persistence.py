"""Task 171w: guardrail persistence audit tests."""

from __future__ import annotations

from pathlib import Path

from songyan.db.repository import ChapterHeadRepository, ChapterVersionRepository, ProjectRepository
from songyan.db.review_repo import CreativeBriefRepository
from songyan.evals.literary_guardrails import (
    audit_171v_guardrail_persistence,
    render_guardrail_persistence_section,
)
from songyan.models import (
    ChapterGoal,
    ChapterHead,
    ChapterVersion,
    CreativeBrief,
    FatigueMotifReplacement,
    NewConceptBudget,
    ProjectSetting,
    ProtagonistActiveChoice,
    SupportingCharacterGoal,
)


def _brief(chapter_number: int) -> CreativeBrief:
    return CreativeBrief(
        mode_id="webnovel",
        chapter_goal=ChapterGoal(chapter_number=chapter_number),
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
            FatigueMotifReplacement(overused="左臂发烫", alternatives=["设备回震"])
        ],
        supporting_character_goal=SupportingCharacterGoal(
            character="赵铭",
            goal="带小周离开",
            conflict_with_protagonist="路线冲突",
            scene_consequence="迫使林渊改变路线",
        ),
    )


def _snapshot() -> dict:
    return {
        "creative_brief_snapshot": {
            "protagonist_active_choice": {
                "choice": "林渊主动切断供能",
                "alternatives": ["等待观察者"],
                "cost": "暴露位置",
                "irreversible_consequence": "审判舱失去回滚机会",
            },
            "new_concept_budget": {
                "max_new_core_concepts": 1,
                "grounding_scene": "供能断路现场",
                "forbidden_mode": "禁止连续解释协议机制",
            },
            "fatigue_motif_replacements": [
                {"overused": "左臂发烫", "alternatives": ["设备回震"]}
            ],
            "supporting_character_goal": {
                "character": "赵铭",
                "goal": "带小周离开",
                "conflict_with_protagonist": "路线冲突",
                "scene_consequence": "迫使林渊改变路线",
            },
        }
    }


async def _seed_project(project_id: str) -> None:
    await ProjectRepository().create(
        ProjectSetting(
            title="171w 测试",
            genre_id="scifi",
            protagonist_name="林渊",
        ),
        project_id,
    )


async def test_guardrail_persistence_audit_passes_complete_chain(test_db: Path) -> None:
    project_id = "proj-171w-pass"
    await _seed_project(project_id)
    await CreativeBriefRepository().create(_brief(205), "cb-205", project_id, 205)
    await ChapterVersionRepository().create(
        ChapterVersion(
            version_id="v-205-1",
            project_id=project_id,
            chapter_number=205,
            version_number=1,
            version_type="accepted",
            generation_metadata=_snapshot(),
            creative_brief_id="cb-205",
        )
    )
    await ChapterHeadRepository().update(
        ChapterHead(
            project_id=project_id,
            chapter_number=205,
            current_version_id="v-205-1",
            accepted_version_id="v-205-1",
            status="accepted",
        )
    )

    rows = await audit_171v_guardrail_persistence(project_id, 205, 205)

    assert len(rows) == 1
    row = rows[0]
    assert row.brief_complete
    assert row.accepted_snapshot_complete
    assert row.accepted_replayable
    assert row.revision_metadata_complete


async def test_guardrail_persistence_audit_accepts_brief_table_replay(
    test_db: Path,
) -> None:
    project_id = "proj-171w-brief-replay"
    await _seed_project(project_id)
    await CreativeBriefRepository().create(_brief(210), "cb-210", project_id, 210)
    await ChapterVersionRepository().create(
        ChapterVersion(
            version_id="v-210-1",
            project_id=project_id,
            chapter_number=210,
            version_number=1,
            version_type="accepted",
            generation_metadata={},
            creative_brief_id="cb-210",
        )
    )
    await ChapterHeadRepository().update(
        ChapterHead(
            project_id=project_id,
            chapter_number=210,
            current_version_id="v-210-1",
            accepted_version_id="v-210-1",
            status="accepted",
        )
    )

    rows = await audit_171v_guardrail_persistence(project_id, 210, 210)

    assert rows[0].brief_complete
    assert not rows[0].accepted_snapshot_complete
    assert rows[0].accepted_replayable


async def test_guardrail_persistence_audit_flags_revision_metadata_gap(
    test_db: Path,
) -> None:
    project_id = "proj-171w-revision-gap"
    await _seed_project(project_id)
    await CreativeBriefRepository().create(_brief(215), "cb-215", project_id, 215)
    await ChapterVersionRepository().create(
        ChapterVersion(
            version_id="v-215-1",
            project_id=project_id,
            chapter_number=215,
            version_number=1,
            version_type="draft",
        )
    )
    await ChapterVersionRepository().create(
        ChapterVersion(
            version_id="rev-215-2",
            project_id=project_id,
            chapter_number=215,
            version_number=2,
            version_type="revision",
            generation_metadata={},
            creative_brief_id=None,
            parent_version_id="v-215-1",
        )
    )

    rows = await audit_171v_guardrail_persistence(project_id, 215, 215)

    assert rows[0].brief_complete
    assert rows[0].revision_versions_missing_guardrail_metadata == ["rev-215-2"]
    assert not rows[0].revision_metadata_complete


def test_render_guardrail_persistence_section() -> None:
    from songyan.evals.literary_guardrails import GuardrailPersistenceAuditRow

    section = render_guardrail_persistence_section(
        [
            GuardrailPersistenceAuditRow(
                chapter_number=205,
                brief_id="cb-205",
                accepted_version_id="v-205-1",
                accepted_creative_brief_id="cb-205",
                brief_fields_present={
                    "protagonist_active_choice": True,
                    "new_concept_budget": True,
                    "fatigue_motif_replacements": True,
                    "supporting_character_goal": True,
                },
                accepted_snapshot_fields_present={
                    "protagonist_active_choice": True,
                    "new_concept_budget": True,
                    "fatigue_motif_replacements": True,
                    "supporting_character_goal": True,
                },
                accepted_replayable=True,
            )
        ]
    )

    assert "171v 护栏持久化审计" in section
    assert "accepted 可回放：1/1" in section
