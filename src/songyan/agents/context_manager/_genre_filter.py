"""GenreProfile 按需加载过滤器 — V3.1 Task 067."""

from __future__ import annotations

from songyan.models.chapter import ChapterGoal
from songyan.models.genre import GenreProfile

# chapter_type → 相关关键词映射（用于启发式过滤）
_CHAPTER_TYPE_KEYWORDS: dict[str, set[str]] = {
    "combat": {"战斗", "冲突", "动作", "紧张", "危机", "生存", "逆袭", "节奏", "刺激"},
    "battle": {"战斗", "冲突", "动作", "紧张", "危机", "生存", "逆袭", "节奏", "刺激"},
    "action": {"战斗", "冲突", "动作", "紧张", "危机", "生存", "逆袭", "节奏", "刺激"},
    "daily": {"日常", "角色", "描写", "情感", "世界", "生活", "温馨", "人际"},
    "slice_of_life": {"日常", "角色", "描写", "情感", "世界", "生活", "温馨", "人际"},
    "interlude": {"日常", "角色", "描写", "情感", "过渡", "铺垫", "世界", "生活"},
    "twist": {"转折", "揭示", "悬念", "意外", "反转", "真相", "伏笔", "秘密"},
    "revelation": {"转折", "揭示", "悬念", "意外", "反转", "真相", "伏笔", "秘密"},
    "turning_point": {"转折", "揭示", "悬念", "意外", "反转", "真相", "伏笔", "秘密"},
    "growth": {"成长", "突破", "修炼", "升级", "进化", "科技", "能力提升"},
    "breakthrough": {"成长", "突破", "修炼", "升级", "进化", "科技", "能力提升"},
}

# 每类最少保留数（防止过滤过度）
_MIN_RETAIN = 2


def _match_any_keyword(text: str, keywords: set[str]) -> bool:
    """检查文本是否包含任一关键词."""
    return any(kw in text for kw in keywords)


def filter_genre_profile(
    genre_profile: GenreProfile,
    chapter_goal: ChapterGoal,
) -> GenreProfile:
    """按章节类型过滤 GenreProfile，减少 Context Token 占用.

    过滤策略：
    1. reviewer_focus：按 chapter_type 关键词匹配，只保留相关的审查焦点
    2. satisfaction_types：按 chapter_type 关键词匹配，只保留相关的爽点类型
    3. writer_rules 和 taboos：不过滤（通用硬约束）
    4. 过滤后若少于 MIN_RETAIN，保留全部（不降级）

    Args:
        genre_profile: 原始 GenreProfile
        chapter_goal: 章节目标（含 chapter_type）

    Returns:
        过滤后的 GenreProfile（副本，不修改原对象）
    """
    chapter_type = (chapter_goal.chapter_type or "").lower()
    keywords = _CHAPTER_TYPE_KEYWORDS.get(chapter_type)

    if not keywords:
        # 未知类型，不过滤
        return genre_profile

    # 过滤 reviewer_focus
    filtered_focus = [
        f for f in genre_profile.reviewer_focus
        if _match_any_keyword(f, keywords)
    ]
    if len(filtered_focus) < _MIN_RETAIN:
        filtered_focus = list(genre_profile.reviewer_focus)

    # 过滤 satisfaction_types
    filtered_satisfaction = [
        s for s in genre_profile.satisfaction_types
        if _match_any_keyword(s, keywords)
    ]
    if len(filtered_satisfaction) < _MIN_RETAIN:
        filtered_satisfaction = list(genre_profile.satisfaction_types)

    return genre_profile.model_copy(
        update={
            "reviewer_focus": filtered_focus,
            "satisfaction_types": filtered_satisfaction,
        }
    )
