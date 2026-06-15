"""ContinuityAuditor 约束生成 — 连续性断点转 HumanMark."""

from __future__ import annotations

import structlog

from songyan.models.continuity import (
    ContinuityReport,
)
from songyan.models.human_mark import HumanMark

logger = structlog.get_logger(__name__)

# 上限配置
MAX_ORPHANED = 8
MAX_FORGOTTEN = 5
MAX_MISMATCHES = 5
MAX_OVERDUE = 10
MAX_CONSTRAINTS_GENERATED = 30  # 078: 生成总预算


def _generate_constraints(report: ContinuityReport) -> list[HumanMark]:
    """将连续性断点转化为 HumanMark 硬约束.

    使用确定性 mark_id 实现幂等写入：同一断点不会重复生成。
    V3.1 Layer 2: 限制各类约束数量，防止 Ch40+ 累积到 200+ 条 human_marks。
    078: 增加生成总预算，单次生成不超过 30 条。
    """
    marks: list[HumanMark] = []

    orphaned = report.orphaned_settings[:MAX_ORPHANED]
    forgotten = report.forgotten_items[:MAX_FORGOTTEN]
    mismatches = report.state_mismatches[:MAX_MISMATCHES]
    # 逾期伏笔按逾期程度排序，保留最紧急的
    overdue_sorted = sorted(
        report.overdue_foreshadowings,
        key=lambda fs: fs.overdue_by,
        reverse=True,
    )[:MAX_OVERDUE]

    for setting in orphaned:
        marks.append(
            HumanMark(
                mark_id=f"cont-set-{setting.tracking_id}",
                project_id=report.project_id,
                mark_type="setting",
                target_key=setting.setting_key,
                note=(
                    f"设定 '{setting.setting_name}' 自第{setting.last_mentioned_chapter}章后"
                    f"已 {setting.chapters_since_mention} 章未被提及，本章必须回收或提及。"
                ),
                priority=10,
                created_at_chapter=report.checked_up_to_chapter,
                source="continuity_auditor",
            )
        )

    for item in forgotten:
        marks.append(
            HumanMark(
                mark_id=f"cont-item-{item.track_id}",
                project_id=report.project_id,
                mark_type="item",
                target_key=item.item_name,
                note=(
                    f"物品 '{item.item_name}' 自第{item.last_used_chapter}章后未再使用"
                    f"（获得章节: 第{item.acquired_in_chapter}章），本章必须提及或使用。"
                ),
                priority=10,
                created_at_chapter=report.checked_up_to_chapter,
                source="continuity_auditor",
            )
        )

    for mismatch in mismatches:
        marks.append(
            HumanMark(
                mark_id=f"cont-mis-{mismatch.character_id}-{mismatch.field}",
                project_id=report.project_id,
                mark_type="character",
                target_key=mismatch.character_id,
                note=(
                    f"角色 {mismatch.character_id} 的 {mismatch.field} 状态矛盾："
                    f"第{mismatch.chapter_a}章为'{mismatch.value_a}'，"
                    f"第{mismatch.chapter_b}章变为'{mismatch.value_b}'，"
                    f"本章必须解释或合理化此变化。"
                ),
                priority=9,
                created_at_chapter=report.checked_up_to_chapter,
                source="continuity_auditor",
            )
        )

    for fs in overdue_sorted:
        marks.append(
            HumanMark(
                mark_id=f"cont-fs-{fs.foreshadowing_id}",
                project_id=report.project_id,
                mark_type="foreshadowing",
                target_key=fs.description[:50],
                note=(
                    f"伏笔 '{fs.description}' 已逾期 {fs.overdue_by} 章未回收"
                    f"（预期回收: 第{fs.expected_resolve_chapter}章），本章必须回收。"
                ),
                priority=10,
                created_at_chapter=report.checked_up_to_chapter,
                source="continuity_auditor",
            )
        )

    # 078: 生成总预算截断
    if len(marks) > MAX_CONSTRAINTS_GENERATED:
        dropped = len(marks) - MAX_CONSTRAINTS_GENERATED
        marks = marks[:MAX_CONSTRAINTS_GENERATED]
        logger.info(
            "continuity_auditor.constraints_truncated",
            project_id=report.project_id,
            chapter_number=report.checked_up_to_chapter,
            dropped=dropped,
            kept=MAX_CONSTRAINTS_GENERATED,
        )

    return marks


async def write_constraints(
    report: ContinuityReport,
) -> int:
    """将连续性断点写入 human_marks 表，返回写入数量.

    使用 INSERT OR REPLACE 确保幂等：同一断点更新而非重复。
    078: 增加输出预算 — 每章 unresolved constraints 不超过 20 条。
    """
    from songyan.db.human_mark_repo import HumanMarkRepository

    MAX_CONSTRAINTS_PER_CHAPTER = 20

    # 078: 检查当前章已有 unresolved constraints 数
    existing_count = 0
    try:
        repo = HumanMarkRepository()
        existing_count = await repo.count_unresolved_by_chapter(
            report.project_id, report.checked_up_to_chapter
        )
    except (RuntimeError, OSError, ConnectionError, ValueError, TypeError):
        logger.warning("continuity_auditor.budget_check_failed", project_id=report.project_id)

    if existing_count >= MAX_CONSTRAINTS_PER_CHAPTER:
        logger.info(
            "continuity_auditor.constraints_skipped_budget",
            project_id=report.project_id,
            chapter_number=report.checked_up_to_chapter,
            existing=existing_count,
            limit=MAX_CONSTRAINTS_PER_CHAPTER,
        )
        return 0

    marks = _generate_constraints(report)
    repo = HumanMarkRepository()
    written = 0
    for mark in marks:
        try:
            await repo.create(mark, replace=True)
            written += 1
        except (RuntimeError, OSError, ConnectionError, ValueError, TypeError):
            logger.warning(
                "continuity_auditor.write_constraint_failed",
                mark_id=mark.mark_id,
                project_id=mark.project_id,
            )
    logger.info(
        "continuity_auditor.constraints_written",
        project_id=report.project_id,
        total=len(marks),
        written=written,
        existing=existing_count,
    )
    return written
