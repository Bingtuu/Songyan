from __future__ import annotations

import pytest

from songyan.agents.writer import _render_prompt
from songyan.models import (
    ApprovedPlan,
    BeatSpec,
    ChapterGoal,
    ContextPackage,
    CreativeBrief,
    PlanOnlyResult,
    PlanReviewResult,
    SupervisionSpec,
)
from songyan.services.plan_review import (
    PlanReviewError,
    approve_plan_review,
    approved_beat_sheet_for_writer,
)


def _beat() -> BeatSpec:
    return BeatSpec(
        visible_action="沈砚复核当前责任质量通知。",
        current_friction="责任质量归属与实测质量不一致。",
        feedback="终端只返回当前数值链，不显示历史日志。",
        micro_decision="沈砚决定先保存当前数值链。",
        landing="缺口被写入离线记录。",
    )


def _spec() -> SupervisionSpec:
    return SupervisionSpec.model_validate(
        {
            "version": "v12.1",
            "stage": "startup_ch1_3",
            "word_count": {"target": 3000, "hard_min": 2700, "hard_max": 3300},
            "chapters": {
                "1": {
                    "allowed_beats": [_beat().model_dump(mode="json")],
                    "required_phrases": ["沈砚决定先保存当前数值链。"],
                    "forbidden_literals": ["三天前", "陈屿", "D区储物柜"],
                    "forbidden_patterns": [r"\d+\.\d+,\s*\d+\.\d+"],
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
    )


def _goal() -> ChapterGoal:
    return ChapterGoal(
        chapter_number=1,
        target_events=["沈砚复核当前责任质量通知"],
        hooks=["责任质量归属与实测质量不一致"],
        obligations=["沈砚决定先保存当前数值链。"],
        word_count_target=3000,
        chapter_type="opening",
    )


def _context(beats: list[BeatSpec]) -> ContextPackage:
    goal = _goal()
    return ContextPackage(
        chapter_goal=goal,
        creative_brief=CreativeBrief(
            mode_id="webnovel",
            chapter_goal=goal,
            creative_intent="只写当前责任质量矛盾。",
            reader_contract="当前动作推进。",
        ),
        startup_beat_sheet=beats,
    )


def test_writer_prompt_renders_structured_startup_beat_sheet() -> None:
    prompt = _render_prompt(_context([_beat()]))

    assert "V12 启动施工单" in prompt
    assert "Beat 1" in prompt
    assert "可见动作：沈砚复核当前责任质量通知。" in prompt
    assert "当前阻力：责任质量归属与实测质量不一致。" in prompt
    assert "仪器/环境反馈：终端只返回当前数值链，不显示历史日志。" in prompt
    assert "主角微决策：沈砚决定先保存当前数值链。" in prompt
    assert "落点：缺口被写入离线记录。" in prompt


def test_writer_prompt_does_not_render_supervision_forbidden_terms() -> None:
    spec = _spec()
    ctx = _context(spec.beat_sheet_for_chapter(1))

    prompt = _render_prompt(ctx)

    assert "三天前" not in prompt
    assert "陈屿" not in prompt
    assert "D区储物柜" not in prompt
    assert r"\d+\.\d+" not in prompt


def test_startup_beat_sheet_includes_per_beat_word_floor() -> None:
    """V12-224d: 施工单注入按校准下限均摊的单 Beat 字数下限."""
    ctx = _context([_beat()] * 6)

    prompt = _render_prompt(ctx)

    # Ch1 target=3000 → 校准下限 2700；6 个 Beat → 每个 Beat ≥ 450 字
    assert "每个 Beat 展开不得少于 450 字" in prompt
    assert "本 Beat 不得少于 450 字" in prompt


def test_startup_beat_sheet_word_floor_rounds_up() -> None:
    """V12-224d: 不能整除时单 Beat 下限向上取整，保证总和覆盖校准下限."""
    ctx = _context([_beat()] * 5)

    prompt = _render_prompt(ctx)

    # 2700 / 5 = 540，恰好整除；再验证 4 beats 时 675
    assert "每个 Beat 展开不得少于 540 字" in prompt

    ctx4 = _context([_beat()] * 4)
    prompt4 = _render_prompt(ctx4)
    assert "每个 Beat 展开不得少于 675 字" in prompt4


def test_approved_beat_sheet_for_writer_requires_matching_approval() -> None:
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
    review = PlanReviewResult(project_id="p1", artifacts=result.artifacts, findings=[])
    approval = approve_plan_review(review, approved_by="human-supervisor")

    beats = approved_beat_sheet_for_writer(
        result=result,
        approval=approval,
        spec=_spec(),
        chapter_number=1,
    )

    assert beats == [_beat()]


def test_mismatched_approval_blocks_beat_sheet_for_writer() -> None:
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
    bad_approval = ApprovedPlan(
        project_id="p1",
        chapters=[2],
        artifact_token="bad-token",
    )

    with pytest.raises(PlanReviewError):
        approved_beat_sheet_for_writer(
            result=result,
            approval=bad_approval,
            spec=_spec(),
            chapter_number=1,
        )

