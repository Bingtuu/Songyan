"""ContinuityAuditor 扫描器 — 各维度连续性检测."""

from __future__ import annotations

import structlog

from songyan.db.continuity_repo import (
    InventoryTrackerRepository,
    SettingTrackingRepository,
)
from songyan.db.settlement_repo import ForeshadowingRepository
from songyan.models.continuity import (
    ForgottenItem,
    OrphanedSetting,
    OverdueForeshadowing,
    StateMismatch,
)
from songyan.models.human_mark import SuggestedMark

logger = structlog.get_logger(__name__)


ORPHANED_THRESHOLD = 3  # 3 章未提及即视为 orphaned
FORGOTTEN_THRESHOLD = 3  # 3 章未使用即视为 forgotten
STATE_MISMATCH_WINDOW = 2  # 2 章内剧烈变化视为 mismatch


async def _find_orphaned_settings(
    project_id: str, up_to_chapter: int,
    setting_repo: SettingTrackingRepository,
) -> list[OrphanedSetting]:
    """找出 last_mentioned_chapter 距离当前超过阈值的 setting."""
    rows = await setting_repo.find_orphaned(
        project_id, up_to_chapter, ORPHANED_THRESHOLD
    )
    return [
        OrphanedSetting(
            tracking_id=r["tracking_id"],
            setting_key=r["setting_key"],
            setting_name=r["setting_name"] or r["setting_key"],
            introduced_in_chapter=r["introduced_in_chapter"],
            last_mentioned_chapter=r["last_mentioned_chapter"],
            chapters_since_mention=up_to_chapter - r["last_mentioned_chapter"],
            category=r.get("category", "background"),
        )
        for r in rows
    ]


async def _find_forgotten_items(
    project_id: str, up_to_chapter: int,
    inventory_repo: InventoryTrackerRepository,
) -> list[ForgottenItem]:
    """找出 last_used_chapter 距离当前超过阈值的物品."""
    rows = await inventory_repo.list_by_project(project_id)
    result: list[ForgottenItem] = []
    for r in rows:
        if r["status"] != "held":
            continue
        last_used = r["last_used_chapter"] or r["acquired_in_chapter"]
        if up_to_chapter - last_used >= FORGOTTEN_THRESHOLD:
            result.append(
                ForgottenItem(
                    track_id=r["track_id"],
                    character_id=r["character_id"],
                    item_name=r["item_name"],
                    acquired_in_chapter=r["acquired_in_chapter"],
                    last_used_chapter=last_used,
                )
            )
    return result


async def _find_state_mismatches(
    project_id: str, up_to_chapter: int,
) -> list[StateMismatch]:
    """检测角色状态在短时间内剧烈变化.

    扫描 character_states 表，通过 source_version_id 关联 chapter_versions
    获取 chapter_number，检测同一角色同一 field 在 STATE_MISMATCH_WINDOW
    章内出现不同值。
    """
    from songyan.db.context_repo import CharacterStateRepository

    mismatches: list[StateMismatch] = []

    rows = await CharacterStateRepository().list_state_history_by_project(
        project_id, up_to_chapter
    )

    # 按 character_id + field 分组
    state_history: dict[str, list[dict]] = {}
    for row in rows:
        key = f"{row['character_id']}:{row['field']}"
        if key not in state_history:
            state_history[key] = []
        state_history[key].append(row)

    # 检测窗口内变化
    for key, history in state_history.items():
        if len(history) < 2:
            continue

        for i in range(1, len(history)):
            prev = history[i - 1]
            curr = history[i]
            chapter_diff = curr["chapter_number"] - prev["chapter_number"]

            if (
                chapter_diff <= STATE_MISMATCH_WINDOW
                and prev["value"] != curr["value"]
            ):
                mismatches.append(
                    StateMismatch(
                        character_id=curr["character_id"],
                        field=curr["field"],
                        chapter_a=prev["chapter_number"],
                        value_a=prev["value"],
                        chapter_b=curr["chapter_number"],
                        value_b=curr["value"],
                        issue=(
                            f"{curr['field']} 在第{prev['chapter_number']}章"
                            f"为'{prev['value']}'，"
                            f"第{curr['chapter_number']}章变为'{curr['value']}'"
                        ),
                    )
                )

    logger.info(
        "continuity_auditor.state_mismatches",
        project_id=project_id,
        mismatches_found=len(mismatches),
    )
    return mismatches


async def _find_overdue_foreshadowings(
    project_id: str, up_to_chapter: int,
    foreshadowing_repo: ForeshadowingRepository,
) -> list[OverdueForeshadowing]:
    """找出 expected_resolve_chapter < up_to_chapter 且未 resolved 的伏笔."""
    active = await foreshadowing_repo.list_active(project_id)
    result: list[OverdueForeshadowing] = []
    for fs in active:
        expected = fs.expected_resolve_chapter
        if expected is None:
            continue
        if expected < up_to_chapter and fs.status != "resolved":
            result.append(
                OverdueForeshadowing(
                    foreshadowing_id=fs.foreshadowing_id,
                    description=fs.description,
                    planted_in_chapter=fs.planted_in_chapter,
                    expected_resolve_chapter=expected,
                    overdue_by=up_to_chapter - expected,
                )
            )
    return result


def _generate_suggested_marks(
    orphaned: list[OrphanedSetting],
    forgotten: list[ForgottenItem],
) -> list[SuggestedMark]:
    """从 orphaned settings 和 forgotten items 生成建议标记."""
    suggested: list[SuggestedMark] = []
    for setting in orphaned:
        suggested.append(
            SuggestedMark(
                target_key=setting.setting_key,
                mark_type="setting",
                reason=(
                    f"设定自第{setting.last_mentioned_chapter}章后"
                    f"已 {setting.chapters_since_mention} 章未提及，"
                    f"可能被遗忘（原引入章节: 第{setting.introduced_in_chapter}章）"
                ),
                suggested_priority=8,
                source_tracking_id=setting.tracking_id,
            )
        )
    for item in forgotten:
        suggested.append(
            SuggestedMark(
                target_key=item.item_name,
                mark_type="item",
                reason=(
                    f"道具自第{item.last_used_chapter}章后未再使用"
                    f"（获得章节: 第{item.acquired_in_chapter}章）"
                ),
                suggested_priority=7,
                source_tracking_id=item.track_id,
            )
        )
    return suggested
