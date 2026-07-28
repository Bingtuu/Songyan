"""ContinuityAuditor 扫描器 — 各维度连续性检测."""

from __future__ import annotations

import re
from typing import Any

import structlog
from aiosqlite import Row

from songyan.agents.settlement_extractor._apply import (
    _LOW_INFO_REFERENCE_TOKENS,
    _cjk_runs,
    _term_in_content,
)
from songyan.db.connection import get_db
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
from songyan.models.genre_runtime_profile import GenreRuntimeProfile
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
    project_id: str,
    up_to_chapter: int,
    setting_repo: SettingTrackingRepository,
    runtime_profile: GenreRuntimeProfile | None = None,
) -> list[OrphanedSetting]:
    """按类别阈值找出 last_mentioned_chapter 距离当前过远的 setting."""
    thresholds = (
        runtime_profile.continuity.orphaned_thresholds
        if runtime_profile is not None
        else ORPHANED_THRESHOLDS
    )

    get_human_marked_keys = getattr(setting_repo, "active_setting_mark_keys", None)
    human_marked_keys = (
        await get_human_marked_keys(project_id, current_chapter=up_to_chapter)
        if get_human_marked_keys is not None
        else set()
    )
    rows: list[dict[str, Any]] = []
    for category, threshold in thresholds.items():
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


_ITEM_REFERENCE_SPLIT_RE = re.compile(
    r"[·—\-_/（）()\[\]【】,，、;；:\s'‘’\"“”]+"
)


def _item_reference_terms(item_name: str) -> set[str]:
    """提取物品核心名，用于正文回查.

    与 172b 引号 matcher 同纪律：同一分隔符集（含中英文引号）切分 +
    low-info 过滤 + len>=2 约束，避免「系统」「刀」这类泛词/单字误刷新。
    """
    terms: set[str] = set()
    for part in _ITEM_REFERENCE_SPLIT_RE.split(item_name):
        cleaned = part.strip()
        if len(cleaned) >= 2 and cleaned not in _LOW_INFO_REFERENCE_TOKENS:
            terms.add(cleaned)
    return terms


def _item_reference_tokens(item_name: str) -> set[str]:
    """复合物品名（CJK 片段 len>=4）的 2-4 gram token，用于多 token 共现回查.

    172c.p（B 方案）：wuxia 正文常以短名指代 verbose 登记名（「断刀门刀谱」在正文
    写作 断刀+刀谱 共现）。复用 172b `_has_multi_token_setting_reference` 的语义：
    单个短 token 命中不构成使用，>=3 个不同 token 且至少一个 len>=3 同章共现才算。
    短名（CJK 片段 <4）不生成 token，只走 full-term 路径。
    """
    tokens: set[str] = set()
    for run in _cjk_runs(item_name):
        if len(run) < 4:
            continue
        for n in (2, 3, 4):
            for i in range(0, len(run) - n + 1):
                token = run[i : i + n]
                if token not in _LOW_INFO_REFERENCE_TOKENS:
                    tokens.add(token)
    return tokens


def _item_mentioned_in_content(item_name: str, terms: set[str], content: str) -> bool:
    """物品是否在正文中被使用：full-term 边界命中，或多 token 共现."""
    if any(_term_in_content(term, content) for term in terms):
        return True
    tokens = _item_reference_tokens(item_name)
    if len(tokens) < 3:
        return False
    lowered = content.lower()
    matched = {token for token in tokens if token.lower() in lowered}
    return len(matched) >= 3 and any(len(token) >= 3 for token in matched)


async def _load_recent_accepted_contents(
    project_id: str, from_chapter: int, to_chapter: int
) -> list[tuple[int, str]]:
    """加载 [from_chapter, to_chapter] 范围 accepted 版本的正文（供正文回查）.

    DB 不可用（如纯 mock 单测环境）时退化为空列表——正文回查失效，
    forgotten 判定回退为纯阈值行为（172c.p 前的旧行为）。
    """
    try:
        async with get_db() as conn:
            conn.row_factory = Row
            cursor = await conn.execute(
                """SELECT h.chapter_number AS chapter_number, cv.content AS content
                   FROM chapter_heads h
                   JOIN chapter_versions cv ON cv.version_id = h.current_version_id
                   WHERE h.project_id = ? AND h.status = 'accepted'
                     AND h.chapter_number BETWEEN ? AND ?
                   ORDER BY h.chapter_number""",
                (project_id, from_chapter, to_chapter),
            )
            rows = await cursor.fetchall()
    except Exception as exc:
        logger.warning(
            "continuity.forgotten_text_recheck_unavailable",
            project_id=project_id,
            error=str(exc),
        )
        return []
    return [(int(r["chapter_number"]), str(r["content"] or "")) for r in rows]


async def _find_forgotten_items(
    project_id: str,
    up_to_chapter: int,
    inventory_repo: InventoryTrackerRepository,
    runtime_profile: GenreRuntimeProfile | None = None,
) -> list[ForgottenItem]:
    """找出 last_used_chapter 距离当前超过阈值的物品.

    172c.p 检测兜底：超阈值候选先回查近 ``threshold`` 章 accepted 正文——物品核心名
    在正文中出现即视为真实使用（刷新 last_used 且不计 forgotten）；正文也不出现的才
    判 forgotten（真遗忘仍被捕获）。覆盖 settlement 漏记 inventory 更新的失败模式。
    """
    threshold = (
        runtime_profile.continuity.forgotten_threshold
        if runtime_profile is not None
        else FORGOTTEN_THRESHOLD
    )
    rows = await inventory_repo.list_by_project(project_id)
    candidates: list[tuple[dict[str, Any], int]] = []
    for r in rows:
        if r["status"] != "held":
            continue
        last_used = r["last_used_chapter"] or r["acquired_in_chapter"]
        if up_to_chapter - last_used >= threshold:
            candidates.append((r, last_used))
    if not candidates:
        return []

    from_chapter = max(1, up_to_chapter - threshold + 1)
    recent_contents = await _load_recent_accepted_contents(
        project_id, from_chapter, up_to_chapter
    )

    result: list[ForgottenItem] = []
    for r, last_used in candidates:
        terms = _item_reference_terms(r["item_name"])
        if recent_contents:
            matched_chapters = [
                chapter_number
                for chapter_number, content in recent_contents
                if _item_mentioned_in_content(r["item_name"], terms, content)
            ]
            if matched_chapters:
                latest = max(matched_chapters)
                if latest > last_used:
                    await inventory_repo.update_last_used(r["track_id"], latest)
                    logger.info(
                        "continuity.forgotten_item_refreshed_by_text",
                        project_id=project_id,
                        track_id=r["track_id"],
                        item_name=r["item_name"],
                        last_used_chapter=latest,
                    )
                continue
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
    project_id: str,
    up_to_chapter: int,
    runtime_profile: GenreRuntimeProfile | None = None,
) -> list[StateMismatch]:
    """检测角色状态在短时间内剧烈变化.

    扫描 character_states 表，通过 source_version_id 关联 chapter_versions
    获取 chapter_number，检测同一角色同一 field 在窗口内出现不同值。
    """
    from songyan.db.context_repo import CharacterStateRepository

    window = (
        runtime_profile.continuity.state_mismatch_window
        if runtime_profile is not None
        else STATE_MISMATCH_WINDOW
    )

    mismatches: list[StateMismatch] = []

    rows = await CharacterStateRepository().list_state_history_by_project(
        project_id, up_to_chapter
    )

    # 按 character_id + field 分组
    state_history: dict[str, list[dict[str, Any]]] = {}
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
                chapter_diff <= window
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
    """找出 expected_resolve_chapter < up_to_chapter 且未 resolved 的伏笔.

    172c.r: 改用 ``list_overdue_unresolved``（与 vdim 冻结验收口径一致）——
    旧实现复用 ``list_active()``，同时漏计 archived/dormant overdue 与
    active 但 status='overdue' 的条目，导致 health 指标与 vdim overdue 门割裂。

    193.t: 切换为 ``list_overdue_actionable``——本函数的唯一消费者是
    continuity health / streak halt 的 **operational 决策**（要不要停 run），
    而 dormant（>5 章逾期系统停放）/ archived（>15 章退役）是生命周期调度器
    已退休的条目，不应再产生急性 P2 压力（192.ad 实证）。vdim / five-gate 的
    overdue 验收门走 five_gate 自有 SQL（冻结全计口径），不受影响；两口径的
    分工自此显式分离：验收门看全量债务，operational 只看当前可操作债务。
    """
    overdue_items = await foreshadowing_repo.list_overdue_actionable(
        project_id, up_to_chapter
    )
    result: list[OverdueForeshadowing] = []
    for fs in overdue_items:
        expected = fs.expected_resolve_chapter
        if expected is None:
            continue
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
