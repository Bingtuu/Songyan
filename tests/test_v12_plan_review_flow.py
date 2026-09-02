from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from songyan.db.connection import get_db
from songyan.db.repository import ChapterGoalRepository, ProjectRepository
from songyan.db.review_repo import CreativeBriefRepository
from songyan.models import (
    ChapterGoal,
    CreativeBrief,
    PlanOnlyResult,
    ProjectSetting,
    SupervisionSpec,
)
from songyan.services.plan_review import (
    PlanReviewError,
    approve_plan_review,
    ensure_plan_approved,
    load_approved_plan,
    review_plan_documents,
    review_plan_only_result,
    run_plan_only,
    save_approved_plan,
)


def _spec_data() -> dict[str, object]:
    return {
        "version": "v12.1",
        "stage": "startup_ch1_3",
        "word_count": {"target": 3000, "hard_min": 2700, "hard_max": 3300},
        "chapters": {
            "1": {
                "allowed_beats": [
                    {
                        "visible_action": "沈砚复核当前责任质量通知。",
                        "current_friction": "责任质量归属与实测质量不一致。",
                        "feedback": "终端只返回当前数值链。",
                        "micro_decision": "沈砚决定先保存当前数值链。",
                        "landing": "缺口被写入离线记录。",
                    }
                ],
                "required_phrases": ["沈砚决定先保存当前数值链。"],
                "forbidden_literals": ["陈屿"],
                "forbidden_patterns": [r"D区.*储物柜"],
                "stage_policy": {
                    "allow_new_characters": False,
                    "allow_past_backstory": False,
                    "allow_cross_location_chase": False,
                    "allow_identity_secret_reveal": False,
                    "allow_relative_time": False,
                    "allow_coordinates": False,
                },
            }
        },
    }


def _spec() -> SupervisionSpec:
    return SupervisionSpec.model_validate(_spec_data())


def _clean_goal() -> ChapterGoal:
    return ChapterGoal(
        chapter_number=1,
        previous_summary="",
        target_events=["沈砚复核当前责任质量通知"],
        hooks=["责任质量归属与实测质量不一致"],
        obligations=["沈砚决定先保存当前数值链。"],
        word_count_target=3000,
        chapter_type="opening",
    )


def _clean_brief(goal: ChapterGoal | None = None) -> CreativeBrief:
    return CreativeBrief(
        mode_id="webnovel",
        chapter_goal=goal or _clean_goal(),
        creative_intent="只写当前责任质量矛盾，不解释历史来源。",
        reader_contract="当前动作推进。",
        style_constraints=["现场动作优先"],
    )


async def _count_chapter_versions() -> int:
    async with get_db() as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM chapter_versions")
        row = await cursor.fetchone()
    return int(row[0])


@pytest.mark.asyncio
async def test_run_plan_only_creates_plan_artifacts_without_versions(test_db: Path) -> None:
    async def fake_goal_node(state: dict[str, Any]) -> dict[str, Any]:
        goal = _clean_goal()
        goal_id = f"goal-{state['chapter_number']}"
        await ChapterGoalRepository().create(goal, goal_id, state["project_id"])
        return {"chapter_goal_id": goal_id, "status": "creative_direction", "error": None}

    async def fake_director_node(state: dict[str, Any]) -> dict[str, Any]:
        goal = _clean_goal()
        brief = _clean_brief(goal)
        brief_id = f"brief-{state['chapter_number']}"
        await CreativeBriefRepository().create(
            brief,
            brief_id,
            state["project_id"],
            state["chapter_number"],
        )
        return {"creative_brief_id": brief_id, "status": "context_assembly", "error": None}

    before = await _count_chapter_versions()
    await ProjectRepository().create(
        ProjectSetting(genre_id="scifi", protagonist_name="沈砚"),
        "p1",
    )

    result = await run_plan_only(
        project_id="p1",
        chapters=[1],
        goal_node=fake_goal_node,
        director_node=fake_director_node,
    )

    after = await _count_chapter_versions()
    assert before == after == 0
    assert result.chapters == [1]
    assert result.artifacts[0].chapter_goal_id == "goal-1"
    assert result.artifacts[0].creative_brief_id == "brief-1"

    review = await review_plan_only_result(result, _spec())
    assert review.passed is True


def test_review_plan_documents_blocks_redline_violations() -> None:
    goal = ChapterGoal(
        chapter_number=1,
        target_events=[
            "陈屿提示两年前旧事故坐标 31.23, 121.47，线索指向D区四号舱储物柜。"
        ],
        hooks=["沈弥账号权限异常"],
        obligations=["沈砚追踪到D区"],
        word_count_target=3000,
        chapter_type="opening",
    )
    brief = CreativeBrief(
        mode_id="webnovel",
        chapter_goal=goal,
        creative_intent="用三年前的历史记录解释当前异常。",
        reader_contract="跨区追踪。",
    )

    findings = review_plan_documents(goal=goal, brief=brief, spec=_spec())
    codes = {finding.code for finding in findings}

    assert "forbidden_literal" in codes
    assert "forbidden_pattern" in codes
    assert "new_character" in codes
    assert "past_backstory" in codes
    assert "cross_location_chase" in codes
    assert "identity_secret_reveal" in codes
    assert "relative_time" in codes
    assert "coordinates" in codes


def test_review_plan_documents_ignores_negated_policy_mentions() -> None:
    goal = ChapterGoal(
        chapter_number=1,
        target_events=["沈砚只处理当前责任质量异常。"],
        hooks=["不提前揭示任何家庭旧事或身份秘密。"],
        obligations=["避免跨区追踪和坐标推进。"],
        word_count_target=3000,
        chapter_type="opening",
    )
    brief = CreativeBrief(
        mode_id="webnovel",
        chapter_goal=goal,
        creative_intent="不展开旧事故，不引入新角色，只在当前交接廊完成现场复核。",
        reader_contract="禁止使用外部地点追踪。",
    )

    findings = review_plan_documents(goal=goal, brief=brief, spec=_spec())

    assert findings == []


def _spec_data_with(
    *,
    forbidden_literals: list[str] | None = None,
    forbidden_patterns: list[str] | None = None,
) -> dict[str, object]:
    data = _spec_data()
    chapters = data["chapters"]
    assert isinstance(chapters, dict)
    chapter1 = chapters["1"]
    assert isinstance(chapter1, dict)
    if forbidden_literals is not None:
        chapter1["forbidden_literals"] = forbidden_literals
    if forbidden_patterns is not None:
        chapter1["forbidden_patterns"] = forbidden_patterns
    return data


def test_review_plan_documents_ignores_negated_forbidden_pattern() -> None:
    spec = SupervisionSpec.model_validate(
        _spec_data_with(forbidden_literals=[], forbidden_patterns=[r"旧(案|事故|记录)"])
    )
    goal = _clean_goal()
    brief = CreativeBrief(
        mode_id="webnovel",
        chapter_goal=goal,
        creative_intent="只写当前工程反馈，不引入外部解释或旧事故。",
        reader_contract="当前动作推进。",
    )

    findings = review_plan_documents(goal=goal, brief=brief, spec=spec)

    assert findings == []


def test_review_plan_documents_ignores_negated_forbidden_literal() -> None:
    goal = _clean_goal()
    brief = CreativeBrief(
        mode_id="webnovel",
        chapter_goal=goal,
        creative_intent="禁止陈屿出场，只写当前责任质量链。",
        reader_contract="当前动作推进。",
    )

    findings = review_plan_documents(goal=goal, brief=brief, spec=_spec())

    assert findings == []


def test_review_plan_documents_ignores_bushi_negated_policy_mentions() -> None:
    goal = _clean_goal()
    brief = CreativeBrief(
        mode_id="webnovel",
        chapter_goal=goal,
        creative_intent="责任质量差值缓慢漂移，暗示异常仍在持续，不是历史记录的问题。",
        reader_contract="当前动作推进。",
    )

    findings = review_plan_documents(goal=goal, brief=brief, spec=_spec())

    assert findings == []


def test_review_plan_documents_allows_operational_permission_wording() -> None:
    """离港权限等操作性权限不属于身份秘密揭示（V12-224f scanner 校准）."""
    goal = _clean_goal()
    brief = CreativeBrief(
        mode_id="webnovel",
        chapter_goal=goal,
        creative_intent="沈砚决定手动锁定货舱C-227的离港权限，等待下一轮复核。",
        reader_contract="当前动作推进。",
    )

    findings = review_plan_documents(goal=goal, brief=brief, spec=_spec())

    assert findings == []


def test_review_plan_documents_flags_unnegated_forbidden_pattern_alongside_negated() -> None:
    spec = SupervisionSpec.model_validate(
        _spec_data_with(forbidden_literals=[], forbidden_patterns=[r"旧(案|事故|记录)"])
    )
    goal = _clean_goal()
    brief = CreativeBrief(
        mode_id="webnovel",
        chapter_goal=goal,
        creative_intent="不引入外部解释或旧事故。",
        reader_contract="当前动作推进到封口阶段，此处直接搬出旧事故记录来解释异常来源。",
    )

    findings = review_plan_documents(goal=goal, brief=brief, spec=spec)
    codes = {finding.code for finding in findings}

    assert "forbidden_pattern" in codes


def test_review_plan_documents_allows_professional_identity_wording() -> None:
    goal = ChapterGoal(
        chapter_number=1,
        target_events=["通过沈砚的工程动作展现他的专业身份。"],
        hooks=["沈砚复核当前责任质量链。"],
        obligations=["不引入新角色。"],
        word_count_target=3000,
        chapter_type="opening",
    )
    brief = CreativeBrief(
        mode_id="webnovel",
        chapter_goal=goal,
        creative_intent="只写当前工程反馈和载荷差值。",
        reader_contract="当前现场压迫感。",
    )

    findings = review_plan_documents(goal=goal, brief=brief, spec=_spec())

    assert findings == []


def test_review_plan_documents_blocks_object_identity_wording() -> None:
    goal = ChapterGoal(
        chapter_number=1,
        target_events=["沈砚校验货舱身份。"],
        hooks=["对象身份出现异常。"],
        word_count_target=3000,
        chapter_type="opening",
    )
    brief = _clean_brief(goal)

    findings = review_plan_documents(goal=goal, brief=brief, spec=_spec())

    assert "identity_secret_reveal" in {finding.code for finding in findings}


def test_review_plan_documents_ignores_previous_summary_recap() -> None:
    """previous_summary 是已 accepted 章节的系统摘要回顾，不计入 forbidden 扫描。

    V12-225 scanner 校准：Ch2 plan-only 的 goal.previous_summary 含 Ch1 摘要原文
    "他前往交接廊实地复核"（已 accepted 内容），命中 cross_location_chase /
    forbidden_pattern 造成误报。摘要不是新规划内容，扫描它只会产生假阳性。
    brief.chapter_goal 是 goal 的冗余拷贝，一并排除（goal 本体已直接扫描）。
    """
    spec = SupervisionSpec.model_validate(
        _spec_data_with(forbidden_literals=[], forbidden_patterns=[r"跨区|追踪到|前往"])
    )
    goal = ChapterGoal(
        chapter_number=1,
        previous_summary="他前往交接廊实地复核，发现地面磁锁显示承重27公斤。",
        target_events=["沈砚复核当前责任质量通知"],
        hooks=["责任质量归属与实测质量不一致"],
        obligations=["沈砚决定先保存当前数值链。"],
        word_count_target=3000,
        chapter_type="opening",
    )
    brief = _clean_brief(goal)

    findings = review_plan_documents(goal=goal, brief=brief, spec=spec)

    assert findings == []


def test_review_plan_documents_still_flags_plan_own_forbidden_pattern() -> None:
    """plan 自身内容（target_events 等）命中 forbidden pattern 仍然拦截."""
    spec = SupervisionSpec.model_validate(
        _spec_data_with(forbidden_literals=[], forbidden_patterns=[r"跨区|追踪到|前往"])
    )
    goal = ChapterGoal(
        chapter_number=1,
        previous_summary="",
        target_events=["沈砚前往交接廊复核当前责任质量通知"],
        hooks=["责任质量归属与实测质量不一致"],
        word_count_target=3000,
        chapter_type="opening",
    )
    brief = _clean_brief(goal)

    findings = review_plan_documents(goal=goal, brief=brief, spec=spec)
    codes = {finding.code for finding in findings}

    assert "forbidden_pattern" in codes
    assert "cross_location_chase" in codes


def test_review_plan_documents_ignores_negated_buqueren_identity() -> None:
    """"不确认对象身份" 是 spec required_phrase 要求的禁令措辞，不应误报（V12-225）."""
    goal = ChapterGoal(
        chapter_number=1,
        target_events=["沈砚只确认测试结果，不确认对象身份。"],
        hooks=["责任质量归属与实测质量不一致"],
        word_count_target=3000,
        chapter_type="opening",
    )
    brief = _clean_brief(goal)

    findings = review_plan_documents(goal=goal, brief=brief, spec=_spec())

    assert findings == []


def test_review_plan_documents_blocks_missing_chapter_spec() -> None:
    goal = ChapterGoal(chapter_number=2, target_events=["当前动作"], word_count_target=3000)
    brief = _clean_brief(goal)

    findings = review_plan_documents(goal=goal, brief=brief, spec=_spec())

    assert [finding.code for finding in findings] == ["missing_chapter_spec"]


def test_rejected_plan_cannot_be_approved() -> None:
    goal = ChapterGoal(chapter_number=1, target_events=["陈屿出现"], word_count_target=3000)
    brief = _clean_brief(goal)
    findings = review_plan_documents(goal=goal, brief=brief, spec=_spec())
    review = PlanOnlyResult(
        project_id="p1",
        artifacts=[
            {
                "project_id": "p1",
                "chapter_number": 1,
                "chapter_goal_id": "goal-1",
                "creative_brief_id": "brief-1",
            }
        ],
    )
    from songyan.models import PlanReviewResult

    review_result = PlanReviewResult(
        project_id=review.project_id,
        artifacts=review.artifacts,
        findings=findings,
    )

    with pytest.raises(PlanReviewError, match="cannot approve"):
        approve_plan_review(review_result)


def test_approved_plan_marker_allows_writer_continuation(tmp_path: Path) -> None:
    result = PlanOnlyResult(
        project_id="p1",
        artifacts=[
            {
                "project_id": "p1",
                "chapter_number": 1,
                "chapter_goal_id": "goal-1",
                "creative_brief_id": "brief-1",
            }
        ],
    )
    from songyan.models import PlanReviewResult

    review = PlanReviewResult(project_id="p1", artifacts=result.artifacts, findings=[])
    approval = approve_plan_review(review, approved_by="human-supervisor")
    path = tmp_path / "approved-plan.json"

    save_approved_plan(path, approval)
    loaded = load_approved_plan(path)

    ensure_plan_approved(result, loaded)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["approved_by"] == "human-supervisor"


def test_missing_or_mismatched_approval_blocks_writer_continuation() -> None:
    result = PlanOnlyResult(
        project_id="p1",
        artifacts=[
            {
                "project_id": "p1",
                "chapter_number": 1,
                "chapter_goal_id": "goal-1",
                "creative_brief_id": "brief-1",
            }
        ],
    )

    with pytest.raises(PlanReviewError, match="approval is required"):
        ensure_plan_approved(result, None)

    from songyan.models import PlanReviewResult

    review = PlanReviewResult(project_id="p1", artifacts=result.artifacts, findings=[])
    approval = approve_plan_review(review)
    tampered = approval.model_copy(update={"chapters": [2]})

    with pytest.raises(PlanReviewError, match="chapters do not match"):
        ensure_plan_approved(result, tampered)
