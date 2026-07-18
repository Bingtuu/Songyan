"""Tests for ContinuityAuditor health governance — Task 118.

Layer 1: 分类测试
Layer 2: 数据追踪测试
Layer 3: 报告集成测试
"""

from __future__ import annotations

from songyan.agents.continuity_auditor.continuity_health import (
    classify_continuity_mark,
    classify_health_score,
    classify_report,
)
from songyan.models.continuity import (
    ContinuityReport,
    OrphanedSetting,
    OverdueForeshadowing,
    StateMismatch,
)
from songyan.models.human_mark import HumanMark


class TestClassifyContinuityMark:
    """Layer 1: 分类测试."""

    def test_orphaned_critical_is_p1(self) -> None:
        """critical category orphaned setting → P1."""
        result = classify_continuity_mark({
            "mark_type": "setting",
            "priority": 10,
            "note": "critical setting orphaned for 5 chapters",
        })
        assert result == "P1"

    def test_orphaned_background_is_p3(self) -> None:
        """background category orphaned setting → P3."""
        result = classify_continuity_mark({
            "mark_type": "setting",
            "priority": 10,
            "note": "background setting 自第3章后已 5 章未被提及。",
        })
        assert result == "P3"

    def test_state_mismatch_is_p1(self) -> None:
        """character state mismatch → P1."""
        result = classify_continuity_mark({
            "mark_type": "character",
            "priority": 9,
            "note": "角色 X 的 location 状态矛盾：第3章为'北京'，第5章变为'上海'",
        })
        assert result == "P1"

    def test_overdue_foreshadowing_is_p2(self) -> None:
        """overdue foreshadowing → P2."""
        result = classify_continuity_mark({
            "mark_type": "foreshadowing",
            "priority": 10,
            "note": "伏笔 '奇怪低语' 已逾期 4 章未回收",
        })
        assert result == "P2"

    def test_forgotten_item_is_p3(self) -> None:
        """forgotten item → P3."""
        result = classify_continuity_mark({
            "mark_type": "item",
            "priority": 10,
            "note": "物品 '钥匙碎片' 自第6章后未再使用",
        })
        assert result == "P3"

    def test_human_mark_instance(self) -> None:
        """HumanMark 实例传入也能正确分类."""
        mark = HumanMark(
            mark_id="cont-set-t1",
            project_id="p1",
            mark_type="setting",
            target_key="X",
            priority=10,
            note="critical setting",
            source="continuity_auditor",
        )
        result = classify_continuity_mark(mark)
        assert result == "P1"


class TestClassifyHealthScore:
    """Layer 1: health_score 分类测试."""

    def test_score_below_3_is_p1(self) -> None:
        assert classify_health_score(2.0) == "P1"
        assert classify_health_score(0.5) == "P1"

    def test_score_3_to_5_is_p2(self) -> None:
        assert classify_health_score(3.5) == "P2"
        assert classify_health_score(4.9) == "P2"

    def test_score_5_to_7_is_p3(self) -> None:
        assert classify_health_score(5.5) == "P3"
        assert classify_health_score(6.9) == "P3"

    def test_score_with_state_mismatch_is_p1(self) -> None:
        """有 state_mismatch 时 health_score 无论如何都返回 P1."""
        mismatch = StateMismatch(
            character_id="c1",
            field="location",
            chapter_a=3,
            value_a="A",
            chapter_b=5,
            value_b="B",
            issue="矛盾",
        )
        result = classify_health_score(6.5, state_mismatches=[mismatch])
        assert result == "P1"

    def test_score_with_critical_orphaned_is_p1(self) -> None:
        """有 critical orphaned settings 时 health_score < 3 即为 P1."""
        setting = OrphanedSetting(
            tracking_id="t1",
            setting_key="k",
            setting_name="n",
            introduced_in_chapter=1,
            last_mentioned_chapter=2,
            chapters_since_mention=5,
            category="critical",
        )
        result = classify_health_score(2.0, orphaned_settings=[setting])
        assert result == "P1"


class TestClassifyReport:
    """Layer 1: ContinuityReport 分组计数测试."""

    def test_empty_report(self) -> None:
        report = ContinuityReport(
            report_id="r1",
            project_id="p1",
            checked_up_to_chapter=10,
        )
        counts = classify_report(report)
        assert counts == {"P1": 0, "P2": 0, "P3": 0}

    def test_critical_orphaned_is_p1(self) -> None:
        report = ContinuityReport(
            report_id="r1",
            project_id="p1",
            checked_up_to_chapter=10,
            orphaned_settings=[
                OrphanedSetting(
                    tracking_id="t1",
                    setting_key="k",
                    setting_name="n",
                    introduced_in_chapter=1,
                    last_mentioned_chapter=2,
                    chapters_since_mention=5,
                    category="critical",
                )
            ],
        )
        counts = classify_report(report)
        assert counts["P1"] == 1

    def test_recurring_orphaned_is_p2(self) -> None:
        report = ContinuityReport(
            report_id="r1",
            project_id="p1",
            checked_up_to_chapter=10,
            orphaned_settings=[
                OrphanedSetting(
                    tracking_id="t1",
                    setting_key="k",
                    setting_name="n",
                    introduced_in_chapter=1,
                    last_mentioned_chapter=2,
                    chapters_since_mention=5,
                    category="recurring",
                )
            ],
        )
        counts = classify_report(report)
        assert counts["P2"] == 1

    def test_background_orphaned_is_p3(self) -> None:
        report = ContinuityReport(
            report_id="r1",
            project_id="p1",
            checked_up_to_chapter=10,
            orphaned_settings=[
                OrphanedSetting(
                    tracking_id="t1",
                    setting_key="k",
                    setting_name="n",
                    introduced_in_chapter=1,
                    last_mentioned_chapter=2,
                    chapters_since_mention=5,
                    category="background",
                )
            ],
        )
        counts = classify_report(report)
        assert counts["P3"] == 1

    def test_state_mismatch_is_p3(self) -> None:
        """Task 171r: state_mismatch 降为 P3（Tier 2 观测，不参与阻塞）."""
        report = ContinuityReport(
            report_id="r1",
            project_id="p1",
            checked_up_to_chapter=10,
            state_mismatches=[
                StateMismatch(
                    character_id="c1",
                    field="location",
                    chapter_a=3,
                    value_a="A",
                    chapter_b=5,
                    value_b="B",
                    issue="矛盾",
                )
            ],
        )
        counts = classify_report(report)
        assert counts["P1"] == 0
        assert counts["P3"] == 1

    def test_overdue_foreshadowing_is_p2(self) -> None:
        report = ContinuityReport(
            report_id="r1",
            project_id="p1",
            checked_up_to_chapter=10,
            overdue_foreshadowings=[
                OverdueForeshadowing(
                    foreshadowing_id="f1",
                    description="奇怪低语",
                    planted_in_chapter=2,
                    expected_resolve_chapter=5,
                    overdue_by=5,
                )
            ],
        )
        counts = classify_report(report)
        assert counts["P2"] == 1


class TestHumanMarkSeverityFields:
    """Layer 2: 数据追踪测试 — HumanMark 新增字段验证."""

    def test_severity_field_in_human_mark(self) -> None:
        """HumanMark 支持 severity 字段."""
        mark = HumanMark(
            mark_id="test-1",
            project_id="p1",
            mark_type="setting",
            target_key="k",
            priority=10,
            source="continuity_auditor",
            severity="P1",
        )
        assert mark.severity == "P1"

    def test_version_id_field_in_human_mark(self) -> None:
        """HumanMark 支持 version_id 字段."""
        mark = HumanMark(
            mark_id="test-1",
            project_id="p1",
            mark_type="setting",
            target_key="k",
            priority=10,
            source="continuity_auditor",
            version_id="rev-120-9-666f50c1",
        )
        assert mark.version_id == "rev-120-9-666f50c1"

    def test_generate_constraints_sets_severity(self) -> None:
        """_generate_constraints 为每类问题设置正确的 severity."""
        from songyan.agents.continuity_auditor import ContinuityAuditor

        auditor = ContinuityAuditor()
        report = ContinuityReport(
            report_id="r1",
            project_id="p1",
            checked_up_to_chapter=10,
            orphaned_settings=[
                OrphanedSetting(
                    tracking_id="t1",
                    setting_key="critical_set",
                    setting_name="critical_set",
                    introduced_in_chapter=1,
                    last_mentioned_chapter=2,
                    chapters_since_mention=5,
                    category="critical",
                ),
                OrphanedSetting(
                    tracking_id="t2",
                    setting_key="background_set",
                    setting_name="background_set",
                    introduced_in_chapter=1,
                    last_mentioned_chapter=2,
                    chapters_since_mention=5,
                    category="background",
                ),
            ],
            state_mismatches=[
                StateMismatch(
                    character_id="c1",
                    field="loc",
                    chapter_a=3,
                    value_a="A",
                    chapter_b=5,
                    value_b="B",
                    issue="矛盾",
                )
            ],
            overdue_foreshadowings=[
                OverdueForeshadowing(
                    foreshadowing_id="f1",
                    description="伏笔",
                    planted_in_chapter=2,
                    expected_resolve_chapter=5,
                    overdue_by=5,
                )
            ],
        )
        marks = auditor._generate_constraints(report)

        marks_dict = {m.target_key: m for m in marks}

        # critical orphaned → P1
        assert marks_dict["critical_set"].severity == "P1"
        # background orphaned → P3
        assert marks_dict["background_set"].severity == "P3"
        # state_mismatch → P3 (172c.s: observation, not hard pressure)
        assert marks_dict["c1"].severity == "P3"
        assert marks_dict["c1"].priority == 5
        # overdue foreshadowing → P2
        fs_mark = next(m for m in marks if m.mark_type == "foreshadowing")
        assert fs_mark.severity == "P2"

    def test_generate_constraints_sets_version_id(self) -> None:
        """_generate_constraints 正确传递 version_id."""
        from songyan.agents.continuity_auditor import ContinuityAuditor

        auditor = ContinuityAuditor()
        report = ContinuityReport(
            report_id="r1",
            project_id="p1",
            checked_up_to_chapter=10,
            orphaned_settings=[
                OrphanedSetting(
                    tracking_id="t1",
                    setting_key="k",
                    setting_name="n",
                    introduced_in_chapter=1,
                    last_mentioned_chapter=2,
                    chapters_since_mention=5,
                )
            ],
        )
        marks = auditor._generate_constraints(report, version_id="rev-120-9-xyz")
        assert marks[0].version_id == "rev-120-9-xyz"

    def test_generate_constraints_version_id_defaults_to_none(self) -> None:
        """version_id 未指定时默认为 None（向后兼容）."""
        from songyan.agents.continuity_auditor import ContinuityAuditor

        auditor = ContinuityAuditor()
        report = ContinuityReport(
            report_id="r1",
            project_id="p1",
            checked_up_to_chapter=10,
            orphaned_settings=[
                OrphanedSetting(
                    tracking_id="t1",
                    setting_key="k",
                    setting_name="n",
                    introduced_in_chapter=1,
                    last_mentioned_chapter=2,
                    chapters_since_mention=5,
                )
            ],
        )
        marks = auditor._generate_constraints(report)
        assert marks[0].version_id is None

    def test_human_mark_note_contains_chapter_info(self) -> None:
        """HumanMark note 包含章节信息，便于追踪."""
        from songyan.agents.continuity_auditor import ContinuityAuditor

        auditor = ContinuityAuditor()
        report = ContinuityReport(
            report_id="r1",
            project_id="p1",
            checked_up_to_chapter=120,
            orphaned_settings=[
                OrphanedSetting(
                    tracking_id="t1",
                    setting_key="protocol_7",
                    setting_name="协议第7条",
                    introduced_in_chapter=110,
                    last_mentioned_chapter=115,
                    chapters_since_mention=5,
                )
            ],
        )
        marks = auditor._generate_constraints(report)
        note = marks[0].note
        assert marks[0].created_at_chapter == 120  # created_at_chapter field
        assert "协议第7条" in note
