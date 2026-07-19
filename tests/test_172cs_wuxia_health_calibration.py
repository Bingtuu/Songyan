"""Task 172c.s: wuxia long-window horizon and health calibration tests."""

from __future__ import annotations

from importlib.resources import files

import scripts.run_172b_ch100_climb as climb
from songyan.agents.continuity_auditor import ContinuityAuditor
from songyan.agents.continuity_auditor.continuity_health import classify_continuity_mark
from songyan.agents.creative_director import _DIALOGUE_STYLE_PROMPT_TEMPLATE
from songyan.db.genre_runtime_profile_repo import load_profile_from_registry
from songyan.models.continuity import (
    ContinuityReport,
    OrphanedSetting,
    OverdueForeshadowing,
    StateMismatch,
)


def test_wuxia_long_window_horizon_floor_is_48() -> None:
    """172c.s: wuxia uses the long-window floor after Ch21 health halt."""
    profile = load_profile_from_registry("wuxia")

    assert profile.foreshadowing_horizon_floor == 48


def test_wuxia_profile_keeps_character_voice_context_for_ced() -> None:
    """172c.s: wuxia CED hotspots need the long-window character context tier."""
    profile = load_profile_from_registry("wuxia")

    assert profile.base_budget == 10500
    assert profile.max_character_states == 8
    assert profile.character_decay.dormant_window == 20
    assert profile.character_decay.focal_gaps == {
        "full": 8,
        "compact": 20,
        "symbol": 60,
    }


def test_dialogue_style_generation_avoids_absolute_voice_rules() -> None:
    """Voice cards are anchors; rigid per-line rules inflate dialogue CED."""
    prompt = _DIALOGUE_STYLE_PROMPT_TEMPLATE

    assert "不要输出\"每句话必须\"" in prompt
    assert "0-2 个可选常用开头语" in prompt
    assert "每个角色至少给出 2 个口头禅" not in prompt
    assert "愤怒时冷笑+反问" not in prompt


def test_writer_and_auditor_treat_voice_cards_as_anchors() -> None:
    """172c.s: missing a tick is not a major consistency issue by itself."""
    cards_dir = files("songyan.prompts") / "cards"
    writer_card = (cards_dir / "writer" / "1.1.0.yaml").read_text(encoding="utf-8")
    auditor_card = (cards_dir / "llm_auditor" / "1.0.2.yaml").read_text(
        encoding="utf-8"
    )

    assert "不要求每章或每次出场必出现" in writer_card
    assert "每个角色的口头禅必须在对话中至少出现 1 次" not in writer_card
    assert "风格卡是声纹锚点，不是逐句打卡清单" in auditor_card
    assert "不要仅因某章未使用口头禅" in auditor_card
    assert "最多记为 minor/info" in auditor_card


def test_state_mismatch_constraint_is_p3_observation_not_p1() -> None:
    """state_mismatch no longer creates hard P1 pressure in human marks."""
    report = ContinuityReport(
        report_id="r-172cs",
        project_id="p1",
        checked_up_to_chapter=21,
        state_mismatches=[
            StateMismatch(
                character_id="char-1",
                field="goal",
                chapter_a=20,
                value_a="查真相",
                chapter_b=21,
                value_b="查真相并救人",
                issue="goal 发生演进",
            )
        ],
    )

    marks = ContinuityAuditor()._generate_constraints(report)

    assert len(marks) == 1
    mark = marks[0]
    assert mark.mark_type == "character"
    assert mark.priority == 5
    assert mark.severity == "P3"
    assert classify_continuity_mark(mark) == "P3"


def test_critical_orphan_and_overdue_keep_blocking_severity() -> None:
    """172c.s only downgrades state_mismatch; hard continuity signals remain."""
    report = ContinuityReport(
        report_id="r-172cs",
        project_id="p1",
        checked_up_to_chapter=21,
        orphaned_settings=[
            OrphanedSetting(
                tracking_id="track-critical",
                setting_key="world.core",
                setting_name="核心设定",
                introduced_in_chapter=1,
                last_mentioned_chapter=10,
                chapters_since_mention=11,
                category="critical",
            )
        ],
        overdue_foreshadowings=[
            OverdueForeshadowing(
                foreshadowing_id="fs-1",
                description="盟主府地下密室",
                planted_in_chapter=1,
                expected_resolve_chapter=13,
                overdue_by=8,
            )
        ],
    )

    marks = ContinuityAuditor()._generate_constraints(report)
    by_type = {mark.mark_type: mark for mark in marks}

    assert by_type["setting"].severity == "P1"
    assert by_type["setting"].priority == 10
    assert by_type["foreshadowing"].severity == "P2"
    assert by_type["foreshadowing"].priority == 10


def test_172c_report_title_and_halt_route_are_not_172b(tmp_path, monkeypatch) -> None:
    """RUN_ID=172c report should route to the latest wuxia repair path."""
    report_path = tmp_path / "172c-wuxia-ch100-climb.md"
    monkeypatch.setattr(climb, "RUN_ID", "172c")
    monkeypatch.setattr(climb, "REPORT_PATH", report_path)

    climb._write_report(
        project_id="proj-wuxia",
        genre="wuxia",
        target=100,
        segments=[
            {
                "up_to": 25,
                "accepted": 21,
                "budget_used_peak": 0.9739,
                "budget_used_before_emergency_peak": 1.2847,
                "context_emergency_count": 27,
                "overdue_foreshadowing": 25,
                "health_latest": 5.1,
                "ced_per_1k_words": 8.9173,
            }
        ],
        halt_reason="health_low_streak_halt (last chapter 21)",
    )

    text = report_path.read_text(encoding="utf-8")
    assert text.startswith("# Task 172c: wuxia Ch100 爬坡验证报告")
    assert "172c.t" in text
    assert "172b.p" not in text
