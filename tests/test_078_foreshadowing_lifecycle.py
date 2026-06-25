"""Task 078: 伏笔生命周期管理 + ContinuityAuditor 输出预算化 — 单元测试."""

from __future__ import annotations

from pathlib import Path

import pytest

from songyan.agents.continuity_auditor import ContinuityAuditor
from songyan.agents.continuity_auditor._constraints import _generate_constraints
from songyan.db import ProjectRepository
from songyan.db.migrations import init_schema
from songyan.db.settlement_repo import ForeshadowingRepository
from songyan.models import (
    ContinuityReport,
    ForeshadowingItem,
    ForgottenItem,
    OrphanedSetting,
    OverdueForeshadowing,
    StateMismatch,
)
from songyan.models.creative_mode import HumanMemoryConfig


@pytest.fixture
async def fs_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point get_db() at a temporary initialized database."""
    import songyan.db.connection as conn_mod

    db_path = tmp_path / "fs.db"
    monkeypatch.setattr(
        conn_mod,
        "settings",
        type("S", (), {"database_url": f"sqlite:///{db_path}"})(),
    )
    await init_schema(db_path)
    return db_path


async def _seed_project(project_id: str = "p1") -> None:
    from songyan.models import ProjectSetting

    await ProjectRepository().create(
        ProjectSetting(
            genre_id="scifi",
            mode_id="webnovel",
            protagonist_name="Lin Yuan",
        ),
        project_id,
    )


# =============================================================================
# Foreshadowing 自动归档
# =============================================================================


class TestArchiveOverdue:
    @pytest.mark.asyncio
    async def test_archives_expected_resolve_past_threshold(self, fs_db: Path) -> None:
        await _seed_project("p1")
        repo = ForeshadowingRepository()
        # current_chapter=60, threshold = 60/1.2 = 50
        # expected_resolve_chapter < 50 → archived
        await repo.create(
            ForeshadowingItem(
                foreshadowing_id="fs-old",
                description="旧伏笔",
                planted_in_chapter=10,
                expected_resolve_chapter=40,
                status="overdue",
            ),
            "p1",
        )
        await repo.create(
            ForeshadowingItem(
                foreshadowing_id="fs-recent",
                description="近伏笔",
                planted_in_chapter=45,
                expected_resolve_chapter=55,
                status="planted",
            ),
            "p1",
        )
        archived = await repo.archive_overdue("p1", current_chapter=60)
        assert archived == 1

        active = await repo.list_active("p1")
        ids = {fs.foreshadowing_id for fs in active}
        assert "fs-old" not in ids
        assert "fs-recent" in ids

    @pytest.mark.asyncio
    async def test_does_not_archive_resolved(self, fs_db: Path) -> None:
        await _seed_project("p1")
        repo = ForeshadowingRepository()
        await repo.create(
            ForeshadowingItem(
                foreshadowing_id="fs-resolved",
                description="已回收",
                planted_in_chapter=5,
                expected_resolve_chapter=20,
                status="resolved",
            ),
            "p1",
        )
        archived = await repo.archive_overdue("p1", current_chapter=60)
        assert archived == 0

    @pytest.mark.asyncio
    async def test_archives_zero_expected(self, fs_db: Path) -> None:
        await _seed_project("p1")
        repo = ForeshadowingRepository()
        # expected_resolve_chapter is None → not archived
        await repo.create(
            ForeshadowingItem(
                foreshadowing_id="fs-no-expect",
                description="无预期",
                planted_in_chapter=5,
                expected_resolve_chapter=None,
                status="planted",
            ),
            "p1",
        )
        archived = await repo.archive_overdue("p1", current_chapter=60)
        assert archived == 0


# =============================================================================
# list_active 排除 archived
# =============================================================================


class TestListActiveExcludesArchived:
    @pytest.mark.asyncio
    async def test_list_active_no_archived(self, fs_db: Path) -> None:
        await _seed_project("p1")
        repo = ForeshadowingRepository()
        await repo.create(
            ForeshadowingItem(
                foreshadowing_id="fs-active",
                description="活跃",
                planted_in_chapter=1,
                expected_resolve_chapter=10,
                status="planted",
            ),
            "p1",
        )
        await repo.create(
            ForeshadowingItem(
                foreshadowing_id="fs-archived",
                description="已归档",
                planted_in_chapter=1,
                expected_resolve_chapter=5,
                status="archived",
            ),
            "p1",
        )
        active = await repo.list_active("p1")
        assert len(active) == 1
        assert active[0].foreshadowing_id == "fs-active"


# =============================================================================
# HumanMemoryConfig chapter_window
# =============================================================================


class TestHumanMemoryConfig:
    def test_chapter_window_default(self) -> None:
        cfg = HumanMemoryConfig()
        assert cfg.chapter_window == 3


# =============================================================================
# ContinuityAuditor 输出预算化
# =============================================================================


class TestHealthScoreRelaxation:
    def test_strict_for_early_chapters_background(self) -> None:
        """Task 094: background 设定 orphaned 扣分极低（0.1）."""
        auditor = ContinuityAuditor()
        score = auditor._compute_health_score(
            orphaned=[
                OrphanedSetting(
                    tracking_id="t1",
                    setting_key="k",
                    setting_name="n",
                    introduced_in_chapter=1,
                    last_mentioned_chapter=2,
                    chapters_since_mention=5,
                )
            ],
            forgotten=[],
            mismatches=[],
            overdue=[],
            chapter_number=10,
        )
        assert score == 9.9  # 10 - 1*0.1

    def test_strict_for_early_chapters_critical(self) -> None:
        """Task 094: critical 设定 orphaned 扣分高（2.0）."""
        auditor = ContinuityAuditor()
        score = auditor._compute_health_score(
            orphaned=[
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
            forgotten=[],
            mismatches=[],
            overdue=[],
            chapter_number=10,
        )
        assert score == 8.0  # 10 - 1*2.0

    def test_relaxed_for_late_chapters(self) -> None:
        auditor = ContinuityAuditor()
        score = auditor._compute_health_score(
            orphaned=[
                OrphanedSetting(
                    tracking_id="t1",
                    setting_key="k",
                    setting_name="n",
                    introduced_in_chapter=1,
                    last_mentioned_chapter=2,
                    chapters_since_mention=5,
                )
            ],
            forgotten=[],
            mismatches=[],
            overdue=[],
            chapter_number=50,
        )
        # 10 - 1*0.1*0.5 = 10 - 0.05 = 9.95 → 9.9 (round half to even)
        assert score == 9.9

    def test_floor_at_2_for_late_chapters(self) -> None:
        auditor = ContinuityAuditor()
        # 大量 critical 问题让 score 低于 0，但被 floor 到 2.0
        score = auditor._compute_health_score(
            orphaned=[
                OrphanedSetting(
                    tracking_id=f"t{i}",
                    setting_key="k",
                    setting_name="n",
                    introduced_in_chapter=1,
                    last_mentioned_chapter=2,
                    chapters_since_mention=5,
                    category="critical",
                )
                for i in range(50)
            ],
            forgotten=[],
            mismatches=[],
            overdue=[],
            chapter_number=50,
        )
        assert score == 2.0


class TestGenerateConstraintsBudget:
    def test_truncates_at_30(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # 临时提高分类上限使总数 > 30，验证总预算截断生效
        import songyan.agents.continuity_auditor._constraints as _c

        monkeypatch.setattr(_c, "MAX_ORPHANED", 20)
        monkeypatch.setattr(_c, "MAX_FORGOTTEN", 15)
        report = ContinuityReport(
            report_id="r1",
            project_id="p1",
            checked_up_to_chapter=50,
            orphaned_settings=[
                OrphanedSetting(
                    tracking_id=f"t{i}",
                    setting_key=f"k{i}",
                    setting_name=f"n{i}",
                    introduced_in_chapter=1,
                    last_mentioned_chapter=2,
                    chapters_since_mention=5,
                )
                for i in range(25)
            ],
            forgotten_items=[
                ForgottenItem(
                    track_id=f"i{i}",
                    character_id="c1",
                    item_name=f"item{i}",
                    acquired_in_chapter=1,
                    last_used_chapter=2,
                )
                for i in range(25)
            ],
        )
        marks = _generate_constraints(report)
        assert len(marks) == 30  # 20 + 15 = 35 → truncated to 30


class TestWriteConstraintsBudget:
    @pytest.mark.asyncio
    async def test_skips_when_budget_exhausted(self, fs_db: Path) -> None:
        await _seed_project("p1")
        from songyan.db.human_mark_repo import HumanMarkRepository
        from songyan.models.human_mark import HumanMark

        # 先写入 20 条约束（达到上限）
        repo = HumanMarkRepository()
        for i in range(20):
            await repo.create(
                HumanMark(
                    mark_id=f"m{i}",
                    project_id="p1",
                    mark_type="setting",
                    target_key=f"key{i}",
                    priority=10,
                    created_at_chapter=50,
                    source="continuity_auditor",
                ),
                replace=True,
            )

        report = ContinuityReport(
            report_id="r1",
            project_id="p1",
            checked_up_to_chapter=50,
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
        from songyan.agents.continuity_auditor._constraints import write_constraints

        written = await write_constraints(report)
        assert written == 0  # 预算已耗尽，跳过写入

    @pytest.mark.asyncio
    async def test_writes_when_under_budget(self, fs_db: Path) -> None:
        await _seed_project("p1")
        report = ContinuityReport(
            report_id="r1",
            project_id="p1",
            checked_up_to_chapter=50,
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
        from songyan.agents.continuity_auditor._constraints import write_constraints

        written = await write_constraints(report)
        assert written == 1  # 预算充足，正常写入


class TestConstraintsIdempotentWrite:
    @pytest.mark.asyncio
    async def test_same_mark_not_duplicated(self, fs_db: Path) -> None:
        """验证 INSERT OR REPLACE 幂等: 同一断点更新而非重复."""
        await _seed_project("p1")
        report = ContinuityReport(
            report_id="r1",
            project_id="p1",
            checked_up_to_chapter=50,
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
        from songyan.agents.continuity_auditor._constraints import write_constraints
        from songyan.db.human_mark_repo import HumanMarkRepository

        written_first = await write_constraints(report)
        assert written_first == 1

        written_second = await write_constraints(report)
        assert written_second == 1  # 再次写入同一份报告不应失败

        # 验证数据库中只有 1 条 unresolved 约束
        repo = HumanMarkRepository()
        count = await repo.count_unresolved_by_chapter("p1", 50)
        assert count == 1


class TestConstraintsRespectLimits:
    def test_respects_max_orphaned(self) -> None:
        """验证 MAX_ORPHANED=8 上限."""
        report = ContinuityReport(
            report_id="r1",
            project_id="p1",
            checked_up_to_chapter=50,
            orphaned_settings=[
                OrphanedSetting(
                    tracking_id=f"t{i}",
                    setting_key=f"k{i}",
                    setting_name=f"n{i}",
                    introduced_in_chapter=1,
                    last_mentioned_chapter=2,
                    chapters_since_mention=5,
                )
                for i in range(20)
            ],
        )
        marks = _generate_constraints(report)
        orphaned_marks = [m for m in marks if m.mark_type == "setting"]
        assert len(orphaned_marks) == 8

    def test_respects_max_forgotten(self) -> None:
        """验证 MAX_FORGOTTEN=5 上限."""
        report = ContinuityReport(
            report_id="r1",
            project_id="p1",
            checked_up_to_chapter=50,
            forgotten_items=[
                ForgottenItem(
                    track_id=f"i{i}",
                    character_id="c1",
                    item_name=f"item{i}",
                    acquired_in_chapter=1,
                    last_used_chapter=2,
                )
                for i in range(20)
            ],
        )
        marks = _generate_constraints(report)
        forgotten_marks = [m for m in marks if m.mark_type == "item"]
        assert len(forgotten_marks) == 5

    def test_respects_max_mismatches(self) -> None:
        """验证 MAX_MISMATCHES=5 上限."""
        report = ContinuityReport(
            report_id="r1",
            project_id="p1",
            checked_up_to_chapter=50,
            state_mismatches=[
                StateMismatch(
                    character_id=f"c{i}",
                    field="mood",
                    chapter_a=1,
                    value_a="a",
                    chapter_b=2,
                    value_b="b",
                    issue="矛盾",
                )
                for i in range(20)
            ],
        )
        marks = _generate_constraints(report)
        mismatch_marks = [m for m in marks if m.mark_type == "character"]
        assert len(mismatch_marks) == 5

    def test_respects_max_overdue(self) -> None:
        """验证 MAX_OVERDUE=10 上限."""
        report = ContinuityReport(
            report_id="r1",
            project_id="p1",
            checked_up_to_chapter=50,
            overdue_foreshadowings=[
                OverdueForeshadowing(
                    foreshadowing_id=f"fs{i}",
                    description=f"伏笔{i}",
                    planted_in_chapter=1,
                    expected_resolve_chapter=10,
                    overdue_by=i + 1,
                )
                for i in range(20)
            ],
        )
        marks = _generate_constraints(report)
        overdue_marks = [m for m in marks if m.mark_type == "foreshadowing"]
        assert len(overdue_marks) == 10
        # 验证保留的是 overdue_by 最大的（最紧急的）
        assert overdue_marks[0].note == "伏笔 '伏笔19' 已逾期 20 章未回收" \
            "（预期回收: 第10章），本章必须回收。"
