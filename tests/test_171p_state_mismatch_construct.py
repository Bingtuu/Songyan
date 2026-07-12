"""Task 171p + 171r: state-mismatch construct fix —
evolving fields excluded (exact + prefix), stable ones kept.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from songyan.agents.continuity_auditor._scanners import (
    _EVOLVING_STATE_FIELD_PREFIXES,
    _EVOLVING_STATE_FIELDS,
    _find_state_mismatches,
)
from songyan.agents.continuity_auditor.continuity_health import (
    classify_report,
    count_hard_p1_for_halt,
)
from songyan.models import ContinuityReport, OrphanedSetting, StateMismatch


def _row(character_id: str, field: str, value: str, chapter: int) -> dict:
    return {
        "character_id": character_id,
        "field": field,
        "value": value,
        "chapter_number": chapter,
    }


async def _run_with_history(history: list[dict]):
    with patch(
        "songyan.db.context_repo.CharacterStateRepository"
    ) as mock_repo_cls:
        inst = mock_repo_cls.return_value
        inst.list_state_history_by_project = AsyncMock(return_value=history)
        return await _find_state_mismatches("proj-1", up_to_chapter=3)


class TestEvolvingFieldsExcluded:
    async def test_emotional_state_change_not_flagged(self) -> None:
        """情绪逐章演进不应判 mismatch（171p 假阳性修复）."""
        history = [
            _row("c1", "emotional_state", "警觉、压抑的愤怒", 1),
            _row("c1", "emotional_state", "震惊、决绝、嘲讽", 2),
            _row("c1", "emotional_state", "平静", 3),
        ]
        mismatches = await _run_with_history(history)
        assert mismatches == []

    async def test_knowledge_accumulation_not_flagged(self) -> None:
        """知识单调累积（学到更多）不应判 mismatch."""
        history = [
            _row("c1", "knowledge", "确认A", 1),
            _row("c1", "knowledge", "确认A；确认B", 2),
            _row("c1", "knowledge", "确认A；确认B；确认C", 3),
        ]
        mismatches = await _run_with_history(history)
        assert mismatches == []

    async def test_evolving_fields_constant_contents(self) -> None:
        assert "emotional_state" in _EVOLVING_STATE_FIELDS
        assert "knowledge" in _EVOLVING_STATE_FIELDS
        assert "ability" in _EVOLVING_STATE_FIELDS
        assert "physical_state" in _EVOLVING_STATE_FIELDS
        assert "knowledge_" in _EVOLVING_STATE_FIELD_PREFIXES
        assert "relationship_" in _EVOLVING_STATE_FIELD_PREFIXES

    async def test_ability_progression_not_flagged(self) -> None:
        """Task 171r: 能力渐进增长不应判 mismatch."""
        history = [
            _row("c1", "ability", "解码脉冲", 1),
            _row("c1", "ability", "深度共鸣", 2),
            _row("c1", "ability", "过载触发备份记忆", 3),
        ]
        mismatches = await _run_with_history(history)
        assert mismatches == []

    async def test_knowledge_of_partner_death_prefix_not_flagged(self) -> None:
        """Task 171r: knowledge_* 前缀匹配——认知累积子类."""
        history = [
            _row("c1", "knowledge_of_partner_death", "与黑色结构有关", 1),
            _row("c1", "knowledge_of_partner_death", "发现方舟秘密", 2),
            _row("c1", "knowledge_of_partner_death", "指挥官篡改钥匙", 3),
        ]
        mismatches = await _run_with_history(history)
        assert mismatches == []

    async def test_physical_state_progression_not_flagged(self) -> None:
        """Task 171r: 伤情/身体状态随剧情演进不应判 mismatch."""
        history = [
            _row("c1", "physical_state", "流鼻血", 1),
            _row("c1", "physical_state", "神经接口过载", 2),
            _row("c1", "physical_state", "手动切断修复", 3),
        ]
        mismatches = await _run_with_history(history)
        assert mismatches == []

    async def test_relationship_prefix_not_flagged(self) -> None:
        """Task 171r: relationship_* 前缀匹配——关系只应深化/转变."""
        history = [
            _row("c1", "relationship_with_commander", "猜疑与对抗", 1),
            _row("c1", "relationship_with_commander", "公开对抗与指控", 2),
            _row("c1", "relationship_with_commander", "信任彻底破裂", 3),
        ]
        mismatches = await _run_with_history(history)
        assert mismatches == []

    async def test_relationship_with_linyuan_prefix_not_flagged(self) -> None:
        """Task 171r: relationship_* 前缀匹配——不同 relationship 子类."""
        history = [
            _row("c1", "relationship_with_linyuan", "公开敌对", 2),
            _row("c1", "relationship_with_linyuan", "七年前设陷阱", 3),
        ]
        mismatches = await _run_with_history(history)
        assert mismatches == []

    async def test_mixed_evolving_fields_all_excluded(self) -> None:
        """Task 171r: 所有演进型字段混合场景，全排除."""
        history = [
            _row("c1", "emotional_state", "平静", 1),
            _row("c1", "emotional_state", "愤怒", 2),
            _row("c1", "knowledge", "确认A", 1),
            _row("c1", "knowledge", "确认A+B", 2),
            _row("c1", "ability", "基础", 1),
            _row("c1", "ability", "进阶", 2),
            _row("c1", "physical_state", "健康", 1),
            _row("c1", "physical_state", "受伤", 2),
            _row("c1", "knowledge_of_partner_death", "不知", 1),
            _row("c1", "knowledge_of_partner_death", "已知", 2),
            _row("c1", "relationship_with_commander", "中立", 1),
            _row("c1", "relationship_with_commander", "敌对", 2),
        ]
        mismatches = await _run_with_history(history)
        assert mismatches == []


class TestStableFieldsStillFlagged:
    async def test_status_contradiction_still_flagged(self) -> None:
        """稳定型 field（status）真变化仍应判 mismatch（不误放）."""
        history = [
            _row("c1", "status", "活着", 2),
            _row("c1", "status", "死亡", 3),
        ]
        mismatches = await _run_with_history(history)
        assert len(mismatches) == 1
        assert mismatches[0].field == "status"
        assert mismatches[0].value_a == "活着"
        assert mismatches[0].value_b == "死亡"

    async def test_location_change_still_flagged(self) -> None:
        """稳定型 field（location）真变化仍应判 mismatch（不误放）."""
        history = [
            _row("c1", "location", "控制舱", 2),
            _row("c1", "location", "旧港区", 3),
        ]
        mismatches = await _run_with_history(history)
        assert len(mismatches) == 1
        assert mismatches[0].field == "location"

    async def test_mixed_history_only_stable_flagged(self) -> None:
        """混合历史：演进型剔除、稳定型保留。"""
        history = [
            _row("c1", "emotional_state", "平静", 2),
            _row("c1", "emotional_state", "愤怒", 3),
            _row("c1", "knowledge", "确认A", 2),
            _row("c1", "knowledge", "确认A；确认B", 3),
            _row("c1", "status", "自由", 2),
            _row("c1", "status", "被捕", 3),
        ]
        mismatches = await _run_with_history(history)
        assert len(mismatches) == 1
        assert mismatches[0].field == "status"

    async def test_stable_field_unchanged_no_flag(self) -> None:
        history = [
            _row("c1", "status", "活着", 2),
            _row("c1", "status", "活着", 3),
        ]
        mismatches = await _run_with_history(history)
        assert mismatches == []


class TestCountHardP1ForHalt:
    """Task 171p2: 硬 halt P1 计数排除 state_mismatch，仅计 critical orphaned setting."""

    def _orphan(self, key: str, category: str) -> OrphanedSetting:
        return OrphanedSetting(
            tracking_id=f"t-{key}",
            setting_key=key,
            setting_name=key,
            introduced_in_chapter=1,
            last_mentioned_chapter=1,
            chapters_since_mention=5,
            category=category,
        )

    def _mismatch(self, i: int) -> StateMismatch:
        return StateMismatch(
            character_id=f"c{i}",
            field="status",
            chapter_a=1,
            value_a="a",
            chapter_b=2,
            value_b="b",
            issue="x",
        )

    def test_state_mismatch_not_counted_as_hard_p1(self) -> None:
        report = ContinuityReport(
            report_id="r",
            project_id="p",
            checked_up_to_chapter=3,
            state_mismatches=[self._mismatch(i) for i in range(11)],
            overall_health_score=3.0,
        )
        assert count_hard_p1_for_halt(report) == 0

    def test_critical_orphan_counted_as_hard_p1(self) -> None:
        report = ContinuityReport(
            report_id="r",
            project_id="p",
            checked_up_to_chapter=3,
            orphaned_settings=[
                self._orphan("k1", "critical"),
                self._orphan("k2", "critical"),
            ],
            overall_health_score=4.0,
        )
        assert count_hard_p1_for_halt(report) == 2

    def test_background_orphan_not_hard_p1(self) -> None:
        report = ContinuityReport(
            report_id="r",
            project_id="p",
            checked_up_to_chapter=3,
            orphaned_settings=[self._orphan("k1", "background")],
            overall_health_score=8.0,
        )
        assert count_hard_p1_for_halt(report) == 0

    def test_mixed_only_critical_orphan_counts(self) -> None:
        report = ContinuityReport(
            report_id="r",
            project_id="p",
            checked_up_to_chapter=3,
            state_mismatches=[self._mismatch(i) for i in range(5)],
            orphaned_settings=[self._orphan("k1", "critical")],
            overall_health_score=3.0,
        )
        assert count_hard_p1_for_halt(report) == 1


class TestClassifyReportMismatchDowngradedToP3:
    """Task 171r: classify_report 将 state_mismatch 归入 P3（Tier 2 观测）."""

    def _mismatch(self, i: int) -> StateMismatch:
        return StateMismatch(
            character_id=f"c{i}",
            field="location",
            chapter_a=1,
            value_a="a",
            chapter_b=2,
            value_b="b",
            issue="x",
        )

    def test_mismatches_are_p3_not_p1(self) -> None:
        report = ContinuityReport(
            report_id="r",
            project_id="p",
            checked_up_to_chapter=3,
            state_mismatches=[self._mismatch(i) for i in range(5)],
            overall_health_score=10.0,
        )
        counts = classify_report(report)
        assert counts["P1"] == 0
        assert counts["P3"] == 5

    def test_mismatches_do_not_affect_p1_p2_counts(self) -> None:
        """即使有 mismatch，P1/P2 仍仅由 orphaned/overdue 决定."""
        report = ContinuityReport(
            report_id="r",
            project_id="p",
            checked_up_to_chapter=3,
            state_mismatches=[self._mismatch(0)],
            orphaned_settings=[
                OrphanedSetting(
                    tracking_id="t1", setting_key="k", setting_name="n",
                    introduced_in_chapter=1, last_mentioned_chapter=1,
                    chapters_since_mention=5, category="critical",
                )
            ],
            overall_health_score=10.0,
        )
        counts = classify_report(report)
        assert counts["P1"] == 1  # only critical orphan
        assert counts["P3"] == 1  # mismatch


class TestHealthScoreUnaffectedByMismatches:
    """Task 171r: _compute_health_score 不受 mismatch 数量影响."""

    def test_many_mismatches_do_not_lower_health_score(self) -> None:
        """即使有 10 个 mismatch，健康分也不应被拖低."""
        from songyan.agents.continuity_auditor import ContinuityAuditor

        auditor = ContinuityAuditor()
        score = auditor._compute_health_score(
            orphaned=[],
            forgotten=[],
            mismatches=[StateMismatch(
                character_id="c1", field="f", chapter_a=1, value_a="a",
                chapter_b=2, value_b="b", issue="x",
            )] * 10,
            overdue=[],
            chapter_number=5,
        )
        # 无 orphaned/forgotten/overdue 时，健康分应为满分（floor 3.0 不触发）
        assert score == 10.0

    def test_mismatches_dont_compound_with_orphaned(self) -> None:
        """mismatch 不应叠加 orphaned 一起拖低健康分."""
        from songyan.agents.continuity_auditor import ContinuityAuditor

        auditor = ContinuityAuditor()
        score_without = auditor._compute_health_score(
            orphaned=[OrphanedSetting(
                tracking_id="t1", setting_key="k", setting_name="n",
                introduced_in_chapter=1, last_mentioned_chapter=1,
                chapters_since_mention=5, category="critical",
            )],
            forgotten=[],
            mismatches=[],
            overdue=[],
            chapter_number=5,
        )
        score_with = auditor._compute_health_score(
            orphaned=[OrphanedSetting(
                tracking_id="t1", setting_key="k", setting_name="n",
                introduced_in_chapter=1, last_mentioned_chapter=1,
                chapters_since_mention=5, category="critical",
            )],
            forgotten=[],
            mismatches=[StateMismatch(
                character_id="c1", field="f", chapter_a=1, value_a="a",
                chapter_b=2, value_b="b", issue="x",
            )] * 5,
            overdue=[],
            chapter_number=5,
        )
        # 有 vs 无 mismatch 的健康分应相同
        assert score_with == score_without
