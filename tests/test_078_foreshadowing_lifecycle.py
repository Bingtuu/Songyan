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
)
from songyan.models.creative_mode import HumanMemoryConfig

pytestmark = pytest.mark.asyncio


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
