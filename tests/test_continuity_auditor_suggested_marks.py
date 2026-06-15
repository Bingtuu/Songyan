"""Tests for ContinuityAuditor suggested marks — Phase 7."""

from __future__ import annotations

from songyan.agents.continuity_auditor import ContinuityAuditor
from songyan.models.continuity import (
    ContinuityReport,
    ForgottenItem,
    OrphanedSetting,
    OverdueForeshadowing,
    StateMismatch,
)


class TestGenerateSuggestedMarks:
    def test_orphaned_setting_generates_suggested_mark(self) -> None:
        auditor = ContinuityAuditor()
        orphaned = [
            OrphanedSetting(
                tracking_id="t1",
                setting_key="认知补丁",
                setting_name="认知补丁",
                introduced_in_chapter=3,
                last_mentioned_chapter=4,
                chapters_since_mention=5,
            )
        ]
        forgotten: list[ForgottenItem] = []
        suggested = auditor._generate_suggested_marks(orphaned, forgotten)

        assert len(suggested) == 1
        assert suggested[0].target_key == "认知补丁"
        assert suggested[0].mark_type == "setting"
        assert suggested[0].suggested_priority == 8
        assert "t1" in suggested[0].source_tracking_id

    def test_forgotten_item_generates_suggested_mark(self) -> None:
        auditor = ContinuityAuditor()
        orphaned: list[OrphanedSetting] = []
        forgotten = [
            ForgottenItem(
                track_id="i1",
                character_id="c1",
                item_name="钥匙碎片",
                acquired_in_chapter=5,
                last_used_chapter=6,
            )
        ]
        suggested = auditor._generate_suggested_marks(orphaned, forgotten)

        assert len(suggested) == 1
        assert suggested[0].target_key == "钥匙碎片"
        assert suggested[0].mark_type == "item"
        assert suggested[0].suggested_priority == 7

    def test_combined_orphaned_and_forgotten(self) -> None:
        auditor = ContinuityAuditor()
        orphaned = [
            OrphanedSetting(
                tracking_id="t1",
                setting_key="A",
                setting_name="A",
                introduced_in_chapter=1,
                last_mentioned_chapter=2,
                chapters_since_mention=3,
            )
        ]
        forgotten = [
            ForgottenItem(
                track_id="i1",
                character_id="c1",
                item_name="B",
                acquired_in_chapter=1,
                last_used_chapter=2,
            )
        ]
        suggested = auditor._generate_suggested_marks(orphaned, forgotten)

        assert len(suggested) == 2
        types = {s.mark_type for s in suggested}
        assert types == {"setting", "item"}

    def test_empty_input_returns_empty(self) -> None:
        auditor = ContinuityAuditor()
        suggested = auditor._generate_suggested_marks([], [])
        assert suggested == []


class TestGenerateConstraints:
    def test_orphaned_setting_becomes_human_mark(self) -> None:
        auditor = ContinuityAuditor()
        report = ContinuityReport(
            report_id="r1",
            project_id="p1",
            checked_up_to_chapter=9,
            orphaned_settings=[
                OrphanedSetting(
                    tracking_id="t1",
                    setting_key="认知补丁",
                    setting_name="认知补丁",
                    introduced_in_chapter=3,
                    last_mentioned_chapter=4,
                    chapters_since_mention=5,
                )
            ],
        )
        marks = auditor._generate_constraints(report)

        assert len(marks) == 1
        assert marks[0].mark_type == "setting"
        assert marks[0].target_key == "认知补丁"
        assert marks[0].priority == 10
        assert marks[0].source == "continuity_auditor"
        assert "认知补丁" in marks[0].note

    def test_forgotten_item_becomes_human_mark(self) -> None:
        auditor = ContinuityAuditor()
        report = ContinuityReport(
            report_id="r1",
            project_id="p1",
            checked_up_to_chapter=9,
            forgotten_items=[
                ForgottenItem(
                    track_id="i1",
                    character_id="c1",
                    item_name="钥匙碎片",
                    acquired_in_chapter=5,
                    last_used_chapter=6,
                )
            ],
        )
        marks = auditor._generate_constraints(report)

        assert len(marks) == 1
        assert marks[0].mark_type == "item"
        assert marks[0].target_key == "钥匙碎片"
        assert marks[0].priority == 10
        assert marks[0].source == "continuity_auditor"

    def test_state_mismatch_becomes_human_mark(self) -> None:
        auditor = ContinuityAuditor()
        report = ContinuityReport(
            report_id="r1",
            project_id="p1",
            checked_up_to_chapter=9,
            state_mismatches=[
                StateMismatch(
                    character_id="c1",
                    field="location",
                    chapter_a=3,
                    value_a="北京",
                    chapter_b=5,
                    value_b="上海",
                    issue="location 在第3章为'北京'，第5章变为'上海'",
                )
            ],
        )
        marks = auditor._generate_constraints(report)

        assert len(marks) == 1
        assert marks[0].mark_type == "character"
        assert marks[0].target_key == "c1"
        assert marks[0].priority == 9
        assert "上海" in marks[0].note

    def test_overdue_foreshadowing_becomes_human_mark(self) -> None:
        auditor = ContinuityAuditor()
        report = ContinuityReport(
            report_id="r1",
            project_id="p1",
            checked_up_to_chapter=9,
            overdue_foreshadowings=[
                OverdueForeshadowing(
                    foreshadowing_id="f1",
                    description="主角听到奇怪的低语声",
                    planted_in_chapter=2,
                    expected_resolve_chapter=5,
                    overdue_by=4,
                )
            ],
        )
        marks = auditor._generate_constraints(report)

        assert len(marks) == 1
        assert marks[0].mark_type == "foreshadowing"
        assert "低语声" in marks[0].target_key
        assert marks[0].priority == 10

    def test_deterministic_mark_ids(self) -> None:
        """同一断点应生成相同的 mark_id（幂等）."""
        auditor = ContinuityAuditor()
        report = ContinuityReport(
            report_id="r1",
            project_id="p1",
            checked_up_to_chapter=9,
            orphaned_settings=[
                OrphanedSetting(
                    tracking_id="t1",
                    setting_key="A",
                    setting_name="A",
                    introduced_in_chapter=1,
                    last_mentioned_chapter=2,
                    chapters_since_mention=3,
                )
            ],
        )
        marks1 = auditor._generate_constraints(report)
        marks2 = auditor._generate_constraints(report)
        assert marks1[0].mark_id == marks2[0].mark_id
