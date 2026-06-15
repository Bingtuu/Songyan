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

# V5.0 Task 103: resolve_confidence 阈值
CONFIDENCE_ARCHIVE_THRESHOLD: float = 0.3
# 设定合并相似度阈值（关键词重叠度代理）
MERGE_SIMILARITY_THRESHOLD: float = 0.9
# 每 N 章执行一次合并扫描
MERGE_SCAN_INTERVAL: int = 50


def _calculate_resolve_confidence(
    setting_row: dict,
    current_chapter: int,
    chapter_goal: ChapterGoal | None,
) -> float:
    """计算设定的 resolve_confidence（纯规则，<10ms/条）.

    公式:
        confidence = 0.5 * (1 - chapters_since_last_reference / 50)
                   + 0.3 * narrative_relevance_score
                   + 0.2 * (is_hard_constraint ? 1.0 : 0.0)

    narrative_relevance_score 使用已有 _compute_keyword_overlap 实现，
    避免调用 Embedder 保证性能。
    """
    last_mentioned = setting_row.get("last_mentioned_chapter") or 0
    setting_name = setting_row.get("setting_name", "")
    setting_key = setting_row.get("setting_key", "")

    # 1. 时间衰减因子（最近引用离当前章节越远，confidence 越低）
    chapters_since = max(0, current_chapter - last_mentioned)
    time_factor = max(0.0, 1.0 - chapters_since / 50.0)

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
            if conf < CONFIDENCE_ARCHIVE_THRESHOLD:
                low_confidence_keys.append(key)
                logger.info(
                    "setting_evaporator.archive_candidate",
                    project_id=project_id,
                    setting_key=key,
                    confidence=conf,
                    threshold=CONFIDENCE_ARCHIVE_THRESHOLD,
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
    ) -> list[tuple[str, str]]:
        """合并 embedding 相似度高的重复设定。

        使用 _compute_keyword_overlap 作为轻量相似度代理，
        避免调用 Embedder（保性能）。每 50 章扫描一次。

        返回: [(被合并的 key, 保留的 key), ...]
        """
        if settings is None:
            settings = await self.repo.list_active_with_tracking(project_id)
        if len(settings) < 2:
            return []

        merged: list[tuple[str, str]] = []
        keys_to_archive: list[str] = []

        # O(n^2) 两两比较，适合设定数量 < 200 的场景
        for i, s1 in enumerate(settings):
            key1 = s1.get("setting_key", "")
            name1 = s1.get("setting_name", "")
            if not key1 or key1 in keys_to_archive:
                continue
            for s2 in settings[i + 1 :]:
                key2 = s2.get("setting_key", "")
                name2 = s2.get("setting_name", "")
                if not key2 or key2 in keys_to_archive:
                    continue
                sim_fwd = _compute_keyword_overlap(name1, key1, [name2, key2])
                sim_rev = _compute_keyword_overlap(name2, key2, [name1, key1])
                sim = max(sim_fwd, sim_rev)
                if sim >= similarity_threshold:
                    # 保留最早创建的 setting_key，archive 另一个
                    created1 = s1.get("created_at", "")
                    created2 = s2.get("created_at", "")
                    keep = key1 if created1 <= created2 else key2
                    drop = key2 if keep == key1 else key1
                    if drop not in keys_to_archive:
                        keys_to_archive.append(drop)
                        merged.append((drop, keep))
                        logger.info(
                            "setting_evaporator.merge_candidate",
                            project_id=project_id,
                            drop=drop,
                            keep=keep,
                            similarity=sim,
                        )

        if keys_to_archive:
            await self.repo.archive_by_confidence(project_id, keys_to_archive)
            logger.info(
                "setting_evaporator.merge_complete",
                project_id=project_id,
                merged_count=len(merged),
            )
        return merged
