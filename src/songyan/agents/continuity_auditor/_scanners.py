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


# Task 135: 按设定类别设置不同的回收期望窗口。
ORPHANED_THRESHOLDS: dict[str, int] = {
    "critical": 3,
    "recurring": 4,
    "background": 5,
    "technical": 7,
    "historical": 10,
}
FORGOTTEN_THRESHOLD = 3  # 3 章未使用即视为 forgotten
STATE_MISMATCH_WINDOW = 2  # 2 章内剧烈变化视为 mismatch

# Task 171p + 171r: 构念修正——本就该逐章演进/单调累积的 field，其"变化"是角色发展，
# 不是连续性矛盾。这些 field 从 state-mismatch 检测中排除，避免把情绪推进、
# 知识累积误判为 P1 矛盾（Task 171 小窗口实证：Ch3 P1=11 全为此类假阳性、
# 假阻塞长跑）。仅对"应稳定、变了才可能是真矛盾"的 field 保留检测。
#
# Task 171r 扩展：增加 ability/physical_state 精确匹配，以及 knowledge_*/relationship_*
# 前缀匹配——覆盖 D1 全量长跑 Ch3 实证的 9 个假阳性字段（ability、
# knowledge_of_partner_death、physical_state、relationship_with_commander、
# relationship_with_linyuan）。这些字段共享同一构念：在叙事中会自然演进的属性。
_EVOLVING_STATE_FIELDS: frozenset[str] = frozenset(
    {
        "emotional_state",  # 情绪随剧情推进，本就该变
        "knowledge",         # 角色认知单调累积（学到更多），非矛盾
        "ability",           # 能力渐进增长，非矛盾
        "physical_state",    # 伤情/身体状态随剧情变化，非矛盾
    }
)
# 前缀匹配：字段名以这些前缀开头的均视为演进型。
# knowledge_*（如 knowledge_of_partner_death）是认知累积子类；
# relationship_*（如 relationship_with_commander）是关系演进——叙事中关系只应深化/转变。
_EVOLVING_STATE_FIELD_PREFIXES: tuple[str, ...] = (
    "knowledge_",
    "relationship_",
)


async def _find_orphaned_settings(
    project_id: str, up_to_chapter: int,
    setting_repo: SettingTrackingRepository,
) -> list[OrphanedSetting]:
    """按类别阈值找出 last_mentioned_chapter 距离当前过远的 setting."""
    get_human_marked_keys = getattr(setting_repo, "active_setting_mark_keys", None)
    human_marked_keys = (
        await get_human_marked_keys(project_id, current_chapter=up_to_chapter)
        if get_human_marked_keys is not None
        else set()
    )
    rows: list[dict] = []
    for category, threshold in ORPHANED_THRESHOLDS.items():
        rows.extend(
            await setting_repo.find_orphaned(
                project_id,
                up_to_chapter,
                threshold=threshold,
                categories=[category],
            )
        )
    rows = [
        r
        for r in rows
        if not (
            r.get("category") not in {"critical", "recurring"}
            and r.get("setting_key") in human_marked_keys
        )
    ]
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
        # Task 171p + 171r: 排除演进型 field（精确匹配 + 前缀匹配）。
        field = row["field"]
        if field in _EVOLVING_STATE_FIELDS:
            continue
        if field.startswith(_EVOLVING_STATE_FIELD_PREFIXES):
            continue
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
