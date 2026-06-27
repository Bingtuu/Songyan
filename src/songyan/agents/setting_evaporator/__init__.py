"""Task 103: SettingEvaporator — 设定蒸发器.

纯规则节点，不调用 LLM。基于 resolve_confidence 和关键词相似度
自动 archive 低价值设定、合并重复设定。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from songyan.agents.context_manager._assemblers import (
    _compute_keyword_overlap,
    _is_setting_critical,
)
from songyan.db.settlement_repo import SettingSnapshotRepository

if TYPE_CHECKING:
    from songyan.models import ChapterGoal

logger = structlog.get_logger(__name__)

# Task 135: 按设定类别设置差异化 archive 阈值。
# critical/recurring 保留更久；background/technical/historical 更快回收。
CONFIDENCE_ARCHIVE_THRESHOLDS: dict[str, float] = {
    "critical": 0.25,
    "recurring": 0.20,
    "background": 0.15,
    "technical": 0.12,
    "historical": 0.10,
}
# Task 137: 按类别调整时间衰减分母，避免 background/technical 在 Ch20 前无法蒸发。
CATEGORY_TIME_DENOMINATORS: dict[str, int] = {
    "critical": 100,
    "recurring": 80,
    "background": 25,
    "technical": 30,
    "historical": 20,
}
# 保留旧常量，供未分类/向后兼容使用。
CONFIDENCE_ARCHIVE_THRESHOLD: float = 0.15
TIME_DECAY_DENOMINATOR: int = 50
# 设定合并相似度阈值（关键词重叠度代理）
MERGE_SIMILARITY_THRESHOLD: float = 0.9
# 每 N 章执行一次合并扫描
MERGE_SCAN_INTERVAL: int = 50
MERGE_SOURCE_WINDOW: int = 50


def _calculate_resolve_confidence(
    setting_row: dict,
    current_chapter: int,
    chapter_goal: ChapterGoal | None,
) -> float:
    """计算设定的 resolve_confidence（纯规则，<10ms/条）.

    公式:
        confidence = 0.5 * (1 - chapters_since_last_reference / denom)
                   + 0.3 * narrative_relevance_score
                   + 0.2 * (is_hard_constraint ? 1.0 : 0.0)

    其中 denom 按 setting 类别调整（background/technical/historical 衰减更快）。
    narrative_relevance_score 使用已有 _compute_keyword_overlap 实现，
    避免调用 Embedder 保证性能。
    """
    last_mentioned = setting_row.get("last_mentioned_chapter") or 0
    setting_name = setting_row.get("setting_name", "")
    setting_key = setting_row.get("setting_key", "")

    # 1. 时间衰减因子（最近引用离当前章节越远，confidence 越低）
    chapters_since = max(0, current_chapter - last_mentioned)
    category = setting_row.get("category", "background")
    denom = CATEGORY_TIME_DENOMINATORS.get(category, TIME_DECAY_DENOMINATOR)
    time_factor = max(0.0, 1.0 - chapters_since / float(denom))

    # 2. 叙事相关性（与当前 ChapterGoal 的关键词重叠度）
    relevance = 0.0
    goal_keywords = getattr(chapter_goal, "keywords", None)
    if chapter_goal and goal_keywords:
        relevance = _compute_keyword_overlap(
            setting_name, setting_key, goal_keywords
        )
    # 若无 keywords 或 chapter_goal，给中等默认值
    if relevance == 0.0:
        relevance = 0.3

    # 3. hard_constraint 因子（critical 类别或出现在 target_events 中）
    is_hard = False
    category = setting_row.get("category", "")
    if category == "critical":
        is_hard = True
    elif chapter_goal:
        from songyan.models import NewSetting

        temp_setting = NewSetting(
            setting_name=setting_name,
            description=setting_row.get("description", ""),
            source_quote=setting_row.get("source_quote", ""),
            setting_key=setting_key,
        )
        is_hard = _is_setting_critical(temp_setting, chapter_goal)

    hard_factor = 1.0 if is_hard else 0.0

    confidence = 0.5 * time_factor + 0.3 * relevance + 0.2 * hard_factor
    return round(min(max(confidence, 0.0), 1.0), 4)


def _setting_bucket(row: dict) -> tuple[str, str]:
    """按 category 与 setting_key 前缀缩小合并候选集."""
    category = str(row.get("category") or "uncategorized")
    setting_key = str(row.get("setting_key") or "")
    key_parts = [part for part in setting_key.split(".") if part] if "." in setting_key else []
    if key_parts:
        prefix = ".".join(key_parts[:2])
    else:
        prefix = setting_key.split("_", maxsplit=1)[0] or setting_key[:8]
    return (category, prefix)


def _is_recent_setting(row: dict, current_chapter: int | None, window: int) -> bool:
    """仅让最近新增/提及的设定主动探测重复项."""
    if current_chapter is None:
        return True
    chapter_values = [
        row.get("chapter_number"),
        row.get("introduced_in_chapter"),
        row.get("last_mentioned_chapter"),
    ]
    for value in chapter_values:
        if (
            isinstance(value, int)
            and current_chapter - window <= value <= current_chapter
        ):
            return True
    return False


def _stable_setting_order(row: dict) -> tuple[str, str]:
    """稳定排序，保证合并结果确定性."""
    return (str(row.get("created_at") or ""), str(row.get("setting_key") or ""))


def _setting_similarity(s1: dict, s2: dict) -> float:
    """计算设定相似度；同名设定保持旧合并语义."""
    name1 = s1.get("setting_name", "")
    name2 = s2.get("setting_name", "")
    if name1 and name1 == name2:
        return 1.0
    key1 = s1.get("setting_key", "")
    key2 = s2.get("setting_key", "")
    sim_fwd = _compute_keyword_overlap(name1, key1, [name2, key2])
    sim_rev = _compute_keyword_overlap(name2, key2, [name1, key1])
    return max(sim_fwd, sim_rev)

class SettingEvaporator:
    """设定蒸发器 — 轻量规则节点."""

    def __init__(self) -> None:
        self.repo = SettingSnapshotRepository()

    async def run(
        self,
        project_id: str,
        current_chapter: int,
        chapter_goal: ChapterGoal | None = None,
    ) -> list[str]:
        """执行蒸发：archive 低 confidence 设定。

        返回: 被 archive 的 setting_key 列表。
        """
        active_settings = await self.repo.list_active_with_tracking(project_id)
        if not active_settings:
            return []

        low_confidence_keys: list[str] = []
        for row in active_settings:
            key = row.get("setting_key", "")
            if not key:
                continue
            conf = _calculate_resolve_confidence(row, current_chapter, chapter_goal)
            category = row.get("category", "background")
            threshold = CONFIDENCE_ARCHIVE_THRESHOLDS.get(
                category, CONFIDENCE_ARCHIVE_THRESHOLD
            )
            if conf < threshold:
                low_confidence_keys.append(key)
                logger.info(
                    "setting_evaporator.archive_candidate",
                    project_id=project_id,
                    setting_key=key,
                    category=category,
                    confidence=conf,
                    threshold=threshold,
                )

        if low_confidence_keys:
            archived = await self.repo.archive_by_confidence(
                project_id, low_confidence_keys
            )
            logger.info(
                "setting_evaporator.run_complete",
                project_id=project_id,
                current_chapter=current_chapter,
                active_total=len(active_settings),
                archived_count=archived,
                archived_keys=low_confidence_keys,
            )
        else:
            logger.info(
                "setting_evaporator.run_complete",
                project_id=project_id,
                current_chapter=current_chapter,
                active_total=len(active_settings),
                archived_count=0,
            )

        return low_confidence_keys

    async def merge_similar_settings(
        self,
        project_id: str,
        settings: list[dict] | None = None,
        similarity_threshold: float = MERGE_SIMILARITY_THRESHOLD,
        current_chapter: int | None = None,
        source_window: int = MERGE_SOURCE_WINDOW,
    ) -> list[tuple[str, str]]:
        """合并相似重复设定，按 bucket/recent window 控制比较规模."""
        if settings is None:
            settings = await self.repo.list_active_with_tracking(project_id)
        if len(settings) < 2:
            return []

        ordered_settings = sorted(settings, key=_stable_setting_order)
        buckets: dict[tuple[str, str], list[dict]] = {}
        for row in ordered_settings:
            key = row.get("setting_key", "")
            if not key:
                continue
            buckets.setdefault(_setting_bucket(row), []).append(row)

        merged: list[tuple[str, str]] = []
        keys_to_archive: set[str] = set()

        for bucket_settings in buckets.values():
            probes = [
                row
                for row in bucket_settings
                if _is_recent_setting(row, current_chapter, source_window)
            ]
            for s1 in probes:
                key1 = s1.get("setting_key", "")
                if not key1 or key1 in keys_to_archive:
                    continue
                for s2 in bucket_settings:
                    key2 = s2.get("setting_key", "")
                    if key1 == key2 or not key2 or key2 in keys_to_archive:
                        continue
                    sim = _setting_similarity(s1, s2)
                    if sim >= similarity_threshold:
                        created1 = s1.get("created_at", "")
                        created2 = s2.get("created_at", "")
                        keep = key1 if created1 <= created2 else key2
                        drop = key2 if keep == key1 else key1
                        if drop not in keys_to_archive:
                            keys_to_archive.add(drop)
                            merged.append((drop, keep))
                            logger.info(
                                "setting_evaporator.merge_candidate",
                                project_id=project_id,
                                drop=drop,
                                keep=keep,
                                similarity=sim,
                            )

        if keys_to_archive:
            await self.repo.archive_by_confidence(project_id, sorted(keys_to_archive))
            logger.info(
                "setting_evaporator.merge_complete",
                project_id=project_id,
                merged_count=len(merged),
                buckets_count=len(buckets),
            )
        return merged
