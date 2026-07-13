"""Task 122d: 150 章长序列压力测试 — 验证上下文管理、状态机和 AutoHalt.

测试策略：
- 不调用真实 LLM；直接驱动 ContextManager、Repository、AutoHalt 等核心逻辑。
- 覆盖 5 个压力场景：上下文预算趋势、human_marks 蒸发、AutoHalt 真阳性 /
  假阳性、accepted 章节跳过。
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch

import pytest

from songyan.agents.context_manager import assemble_context_package
from songyan.creative_modes import load_creative_mode_profile
from songyan.db.human_mark_repo import HumanMarkRepository
from songyan.db.repository import (
    ChapterHeadRepository,
    ChapterVersionRepository,
    CharacterRepository,
    ProjectRepository,
)
from songyan.genres import load_genre_profile
from songyan.models import (
    ChapterGoal,
    ChapterHead,
    ChapterSummary,
    ChapterVersion,
    Character,
    CharacterState,
    CreativeBrief,
    DialogueStyleCard,
    HumanMark,
    ProjectSetting,
)
from songyan.workflows._helpers import new_id
from songyan.workflows.phase2_graph import (
    AutoHaltException,
    _check_auto_halt_window,
    run_project_pipeline,
)

from .conftest import writer_resp

pytestmark = pytest.mark.performance

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _seed_project(project_id: str = "test-proj-122d") -> str:
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


async def _build_chapter_history(project_id: str, chapter_number: int) -> str:
    """Directly write one accepted chapter into DB for history construction."""
    version_id = new_id("v")
    content = (
        f"【第{chapter_number}章正文】\n\n"
        f"林动在第{chapter_number}章继续冒险，遭遇新的挑战和敌人。\n"
        f"他运用智慧化解危机，实力略有提升。\n"
    )
    await ChapterVersionRepository().create(
        ChapterVersion(
            version_id=version_id,
            project_id=project_id,
            chapter_number=chapter_number,
            version_number=1,
            version_type="accepted",
            content=content,
            word_count=len(content),
        )
    )
    await ChapterHeadRepository().update(
        ChapterHead(
            project_id=project_id,
            chapter_number=chapter_number,
            current_version_id=version_id,
            accepted_version_id=version_id,
            status="accepted",
        )
    )
    return version_id


def _chapter_responses(n: int) -> list[str]:
    """Minimal mock responses for a single clean-path chapter."""
    content = f"【第{n}章】\n\n{writer_resp()}"
    return [
        json.dumps(
            {
                "target_events": ["发现秘境入口"],
                "emotional_arc": "紧张→兴奋",
                "hooks": {"opening": "悬崖边被追杀", "closing": "秘境大门开启"},
                "obligations": ["保持主角性格"],
                "word_count_target": 150,
                "chapter_type": "action",
            }
        ),
        json.dumps(
            {
                "mode_id": "webnovel",
                "chapter_goal": {
                    "chapter_number": n,
                    "target_events": ["推进剧情"],
                    "word_count_target": 150,
                },
                "creative_intent": "展现主角在绝境中的果敢",
                "required_tensions": [],
                "forbidden_patterns": [],
                "allowed_fissures": [],
                "style_constraints": [],
                "reader_contract": "",
            }
        ),
        content,
        json.dumps(
            {
                "issues": [],
                "dimension_scores": {f"dim_{k}": 8.0 for k in range(12)},
                "cliche_risk_score": 3.0,
                "character_autonomy_score": 7.0,
                "conceptual_idling_score": 2.0,
                "summary": "整体良好",
            }
        ),
        json.dumps(
            {
                "observations": [],
                "overall_quality_score": 6.5,
                "protected_elements": [],
            }
        ),
        json.dumps(
            {
                "character_updates": [],
                "new_settings": [],
                "foreshadowing_updates": [],
                "numerical_updates": [],
                "validation_status": "valid",
                "validation_errors": [],
            }
        ),
        json.dumps({"plot_summary": "剧情推进", "emotional_tone": "紧张"}),
    ]


# ---------------------------------------------------------------------------
# 1. Context budget over 150 chapters
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_context_budget_150_chapters(test_db) -> None:
    """模拟 150 章历史，验证 budget_used 平滑增长且无异常跳变."""
    project_id = await _seed_project()
    genre = load_genre_profile("xuanhuan")
    mode = load_creative_mode_profile("webnovel")

    # Build 150 chapter summaries of increasing length to stress the budget.
    summaries: list[ChapterSummary] = []
    for ch in range(1, 151):
        text = f"第{ch}章剧情摘要：" + "林动继续冒险。" * (5 + ch // 10)
        summaries.append(
            ChapterSummary(
                chapter_number=ch,
                summary=text,
                key_events=[f"事件{ch}-A"],
                characters_appeared=["林动"],
                emotional_tone="紧张",
                impact_score=0.3,
            )
        )

    project = ProjectSetting(
        title="测试",
        genre_id="xuanhuan",
        mode_id="webnovel",
        protagonist_name="林动",
        protagonist_background="出身卑微",
        core_hook="废柴逆袭",
        target_reader_expectation="热血爽文",
        taboos=["绿帽"],
        target_word_count=100_000,
        tone="热血",
    )
    character = Character(
        character_id="char-001",
        project_id=project_id,
        name="林动",
        role_type="protagonist",
        background="出身卑微",
    )

    budgets: list[float] = []
    emergencies: list[int] = []

    for ch in range(1, 151):
        goal = ChapterGoal(chapter_number=ch, target_events=["推进剧情"])
        brief = CreativeBrief(
            mode_id="webnovel",
            chapter_goal=goal,
            creative_intent="测试预算压力",
            required_tensions=[],
            forbidden_patterns=[],
            allowed_fissures=[],
        )
        package = assemble_context_package(
            chapter_goal=goal,
            creative_brief=brief,
            genre_profile=genre,
            mode_profile=mode,
            project=project,
            characters=[character],
            character_states=[
                CharacterState(
                    character_id="char-001",
                    field="location",
                    value=f"地点{ch}",
                    source_version_id="v-test",
                )
            ],
            recent_summaries=summaries[:ch],
            active_foreshadowings=[],
            setting_snapshots=[],
            budget_tokens=8000,
        )
        budgets.append(package.budget_used)
        emergencies.append(1 if package.context_emergency else 0)

    # Assert monotonic-ish growth and no abnormal spike > 1.2.
    max_budget = max(budgets)
    max_delta = max(
        (budgets[i] - budgets[i - 1] for i in range(1, len(budgets))),
        default=0.0,
    )
    assert max_budget <= 1.2, f"Abnormal budget spike: {max_budget:.4f}"
    assert max_delta <= 0.35, f"Abnormal single-chapter budget jump: {max_delta:.4f}"
    assert sum(emergencies) <= 5, f"Too many context emergencies: {sum(emergencies)}"

    print("\n=== Context Budget 150 Chapters ===")
    print(f"Max budget_used: {max_budget:.4f}")
    print(f"Max single-chapter delta: {max_delta:.4f}")
    print(f"Context emergencies: {sum(emergencies)}")
    print("===================================")


# ---------------------------------------------------------------------------
# 2. Human marks decay over 6 chapters
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_human_marks_decay_6_chapters(test_db) -> None:
    """验证 priority<8 的 human_marks 在 6 章窗口后蒸发."""
    project_id = await _seed_project()
    repo = HumanMarkRepository()

    created_chapter = 10
    marks = [
        HumanMark(
            mark_id=new_id("hm"),
            project_id=project_id,
            mark_type="custom",
            target_key=f"mark-{i}",
            note="测试标记",
            priority=5,
            created_at_chapter=created_chapter,
            source="human",
        )
        for i in range(3)
    ]
    for mark in marks:
        await repo.create(mark)

    # At chapter 16 the marks are still within the 6-chapter window.
    archived_16 = await repo.archive_stale(project_id, current_chapter=16)
    active_16 = await repo.list_by_project(project_id)
    assert archived_16 == 0
    assert len(active_16) == 3

    # At chapter 17 they have just crossed the window and become dormant.
    archived_17 = await repo.archive_stale(project_id, current_chapter=17)
    active_17 = await repo.list_by_project(project_id)
    assert archived_17 == 3
    assert len(active_17) == 0


# ---------------------------------------------------------------------------
# 3. AutoHalt false positive / true positive
# ---------------------------------------------------------------------------


def _make_recent_results(
    start_ch: int,
    *,
    emergency: bool,
    qg_pass: bool,
    settlement_success: bool = True,
    summary_success: bool = True,
    success: bool = True,
) -> list[dict[str, Any]]:
    return [
        {
            "chapter_number": start_ch + i,
            "success": success,
            "quality_gate_passed": qg_pass,
            "context_emergency": emergency,
            "settlement_success": settlement_success,
            "summary_success": summary_success,
        }
        for i in range(3)
    ]


@pytest.mark.asyncio
async def test_auto_halt_false_positive(test_db) -> None:
    """连续 3 章 ContextEmergency 但全部成功/QG 通过，AutoHalt 不触发."""
    from songyan.models.project_run import ProjectRunState

    project_id = await _seed_project("test-proj-fp")
    run_state = ProjectRunState(
        run_id="run-fp",
        project_id=project_id,
        chapter_range_start=20,
        chapter_range_end=25,
    )
    recent = _make_recent_results(20, emergency=True, qg_pass=True)
    completed: list[int] = []
    failed: list[int] = []

    # Should complete without raising.
    await _check_auto_halt_window(
        run_state,
        recent,
        completed,
        failed,
        "",
        run_id=run_state.run_id,
        chapter_number=22,
    )
    assert run_state.status == "running"
    assert failed == []


@pytest.mark.asyncio
async def test_auto_halt_true_positive(test_db) -> None:
    """连续 3 章 ContextEmergency 且 QG 失败，AutoHalt 触发."""
    from songyan.models.project_run import ProjectRunState

    project_id = await _seed_project("test-proj-tp")
    run_state = ProjectRunState(
        run_id="run-tp",
        project_id=project_id,
        chapter_range_start=20,
        chapter_range_end=25,
    )
    recent = _make_recent_results(
        20,
        emergency=True,
        qg_pass=True,
        settlement_success=False,
    )
    completed: list[int] = []
    failed: list[int] = []

    with pytest.raises(AutoHaltException) as exc_info:
        await _check_auto_halt_window(
            run_state,
            recent,
            completed,
            failed,
            "",
            run_id=run_state.run_id,
            chapter_number=22,
        )

    assert "context_emergency_degraded_streak" in str(exc_info.value.reason)
    assert run_state.status == "paused"


# ---------------------------------------------------------------------------
# 4. Accepted chapter skip
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_accepted_chapter_skip(test_db, mock_call_llm) -> None:
    """Ch5 已 accepted 时，pipeline 跳过它且不生成新版本."""
    project_id = await _seed_project()

    # Only Ch5 is accepted; Ch1-Ch4 and Ch6-Ch10 will be generated by pipeline.
    await _build_chapter_history(project_id, 5)

    # Pre-create responses for Ch1-Ch10 pipeline (Ch5 should be skipped).
    responses: list[str] = []
    for ch in range(1, 11):
        if ch == 5:
            continue
        responses.extend(_chapter_responses(ch))
        if ch == 10:
            responses.append(
                json.dumps(
                    {
                        "arc_title": "Arc",
                        "arc_summary": "Arc summary",
                        "key_events": ["事件A"],
                        "resolved_threads": [],
                        "new_threads": [],
                        "character_arcs": {"林动": "成长"},
                    }
                )
            )

    mock_call_llm.responses = responses

    with patch("songyan.workflows._helpers._index_accepted_chapter"):
        with patch("songyan.agents.arc_summary_generator.call_llm", mock_call_llm):
            result = await run_project_pipeline(
                project_id=project_id,
                chapter_range=(1, 10),
                mode_id="webnovel",
                auto_confirm=True,
                on_failure="abort",
            )

    assert result.final_status == "completed"
    assert result.chapters_failed == []
    assert 5 in result.chapters_completed

    # Ch5 should still have exactly one accepted version (no new drafts).
    ch5_versions = await ChapterVersionRepository().list_by_chapter(
        project_id, 5, include_abandoned=True
    )
    assert len(ch5_versions) == 1
    assert ch5_versions[0].version_type == "accepted"
