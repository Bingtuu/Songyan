"""ContinuityAuditor Agent — 跨章一致性引擎.

扫描设定追踪、道具追踪、角色状态、伏笔线索，
生成连续性健康报告。
"""

from __future__ import annotations

import uuid

import structlog

from songyan.db.continuity_repo import (
    ContinuityReportRepository,
    InventoryTrackerRepository,
    LocationTrackerRepository,
    SettingTrackingRepository,
)
from songyan.db.settlement_repo import ForeshadowingRepository
from songyan.models.continuity import (
    ContinuityReport,
    ForgottenItem,
    OrphanedSetting,
    OverdueForeshadowing,
    StateMismatch,
)
from songyan.models.human_mark import HumanMark

from ._constraints import _generate_constraints, write_constraints
from ._scanners import (
    _find_forgotten_items,
    _find_orphaned_settings,
    _find_overdue_foreshadowings,
    _find_state_mismatches,
    _generate_suggested_marks,
)

logger = structlog.get_logger(__name__)


class ContinuityAuditor:
    """跨章一致性审计器.

    核心指标:
    - orphaned settings = 0
    - forgotten items = 0
    - character state mismatch = 0
    """

    ORPHANED_THRESHOLD = 3  # 3 章未提及即视为 orphaned
    FORGOTTEN_THRESHOLD = 3  # 3 章未使用即视为 forgotten
    STATE_MISMATCH_WINDOW = 2  # 2 章内剧烈变化视为 mismatch

    def __init__(self) -> None:
        self.setting_repo = SettingTrackingRepository()
        self.inventory_repo = InventoryTrackerRepository()
        self.location_repo = LocationTrackerRepository()
        self.foreshadowing_repo = ForeshadowingRepository()
        self.report_repo = ContinuityReportRepository()

    async def audit(self, project_id: str, up_to_chapter: int) -> ContinuityReport:
        """运行连续性审计.

        Args:
            project_id: 项目 ID
            up_to_chapter: 已完成的最新章节号

        Returns:
            ContinuityReport
        """
        logger.info(
            "continuity_auditor.start",
            project_id=project_id,
            up_to_chapter=up_to_chapter,
        )

        report_id = f"cont_{uuid.uuid4().hex[:8]}"

        orphaned = await _find_orphaned_settings(
            project_id, up_to_chapter, self.setting_repo
        )
        forgotten = await _find_forgotten_items(
            project_id, up_to_chapter, self.inventory_repo
        )
        mismatches = await _find_state_mismatches(project_id, up_to_chapter)
        overdue = await _find_overdue_foreshadowings(
            project_id, up_to_chapter, self.foreshadowing_repo
        )

        suggested = _generate_suggested_marks(orphaned, forgotten)
        health = self._compute_health_score(orphaned, forgotten, mismatches, overdue, up_to_chapter)

        report = ContinuityReport(
            report_id=report_id,
            project_id=project_id,
            checked_up_to_chapter=up_to_chapter,
            orphaned_settings=orphaned,
            forgotten_items=forgotten,
            state_mismatches=mismatches,
            overdue_foreshadowings=overdue,
            suggested_marks=suggested,
            overall_health_score=health,
        )

        await self.report_repo.create(report)

        logger.info(
            "continuity_auditor.done",
            project_id=project_id,
            score=health,
            orphaned=len(orphaned),
            forgotten=len(forgotten),
            mismatches=len(mismatches),
            overdue=len(overdue),
            suggested=len(suggested),
        )
        return report

    async def _find_state_mismatches(
        self, project_id: str, up_to_chapter: int
    ) -> list[StateMismatch]:
        """委托给独立函数以保持接口兼容."""
        return await _find_state_mismatches(project_id, up_to_chapter)

    def _generate_suggested_marks(
        self,
        orphaned: list[OrphanedSetting],
        forgotten: list[ForgottenItem],
    ) -> list:
        """委托给独立函数以保持接口兼容."""
        return _generate_suggested_marks(orphaned, forgotten)

    def _generate_constraints(self, report: ContinuityReport) -> list:
        """委托给独立函数以保持接口兼容."""
        return _generate_constraints(report)

    async def write_constraints(
        self,
        report: ContinuityReport,
    ) -> int:
        """将连续性断点写入 human_marks 表，返回写入数量.

        委托给独立函数以保持接口兼容。
        """
        return await write_constraints(report)

    def _compute_health_score(
        self,
        orphaned: list[OrphanedSetting],
        forgotten: list[ForgottenItem],
        mismatches: list[StateMismatch],
        overdue: list[OverdueForeshadowing],
        chapter_number: int = 0,
    ) -> float:
        """基于问题数量计算 0-10 健康分.

        Task 094: 按 setting 分类加权扣分，避免一次性背景设定压低分数。
        critical(2.0) > recurring(1.0) > background(0.1) > technical(0.05)
        """
        score = 10.0
        factor = 1.0
        if chapter_number > 30:
            factor = 0.5

        # 按分类统计 orphaned 数量
        orphaned_critical = sum(1 for o in orphaned if o.category == "critical")
        orphaned_recurring = sum(1 for o in orphaned if o.category == "recurring")
        orphaned_background = sum(1 for o in orphaned if o.category == "background")
        orphaned_technical = sum(1 for o in orphaned if o.category == "technical")
        orphaned_historical = sum(1 for o in orphaned if o.category == "historical")

        score -= orphaned_critical * 2.0 * factor
        score -= orphaned_recurring * 1.0 * factor
        score -= orphaned_background * 0.1 * factor
        score -= orphaned_technical * 0.05 * factor
        score -= orphaned_historical * 0.05 * factor
        score -= len(forgotten) * 0.5 * factor
        score -= len(mismatches) * 1.0 * factor
        score -= len(overdue) * 0.3 * factor
        return max(2.0 if chapter_number > 30 else 0.0, round(score, 1))
