"""ContextManager 分区构建器 — 各上下文分区的组装函数."""

from __future__ import annotations

import re
from typing import Literal

import structlog

from songyan.models import (
    ChapterGoal,
    ChapterSummary,
    Character,
    CharacterState,
    CharacterStateSnapshot,
    CreativeModeProfile,
    GenreProfile,
    GenreRules,
    HardConstraint,
    HumanMark,
    ModeRules,
    NewSetting,
    ProjectSetting,
    RecentPlot,
    RetrievedChunk,
    SoftReference,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# 077a: 关键词工具函数
# ---------------------------------------------------------------------------

_STOP_WORDS: frozenset[str] = frozenset({
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人",
    "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去",
    "你", "会", "着", "没有", "看", "好", "自己", "这", "他", "她",
    "它", "们", "某", "那", "对", "与", "为", "把", "被", "让",
    "从", "以", "而", "但", "却", "可", "还", "又", "再", "才",
    "将", "这个", "那个", "什么", "怎么", "如何", "为何", "因为", "所以", "如果",
    "虽然", "但是", "然后", "之后", "之前", "时候", "已经", "可以", "可能",
    "需要", "应该", "必须", "非常", "比较", "有些", "所有", "每个", "任何", "其他",
})


def _split_terms(text: str) -> list[str]:
    """将文本按标点/空格切分为 term 列表."""
    parts = re.split("[\\s,，。！？、；：\\\"'（）()\\[\\]【】…—\u3000]+", text)
    return [p.strip() for p in parts if p.strip()]


def _extract_keywords(chapter_goal: ChapterGoal) -> list[str]:
    """从 ChapterGoal 提取关键词（重要实词）.

    来源: target_events + hooks + chapter_type
    过滤: 长度 >= 2 且不是停用词
    去重: 保留首次出现顺序
    """
    words: list[str] = []
    for text in chapter_goal.target_events + chapter_goal.hooks:
        words.extend(t for t in _split_terms(text) if len(t) >= 2)
    if chapter_goal.chapter_type:
        words.append(chapter_goal.chapter_type)
    # 去停用词 + 去重
    return list(dict.fromkeys(w for w in words if w not in _STOP_WORDS))


def _is_setting_critical(setting: NewSetting, chapter_goal: ChapterGoal) -> bool:
    """判断设定是否关键：设定名出现在 target_events 或 obligations 中."""
    combined = chapter_goal.target_events + chapter_goal.obligations
    for event in combined:
        if setting.setting_name in event:
            return True
        if setting.setting_key and setting.setting_key in event:
            return True
    return False


def _compute_keyword_overlap(setting_name: str, setting_key: str, keywords: list[str]) -> float:
    """计算设定名与关键词的重叠度.

    返回: [0.0, 1.0]，越高表示与本章目标越相关.
    """
    if not keywords:
        return 0.0
    matches = 0
    text = f"{setting_name} {setting_key}"
    for kw in keywords:
        if kw in text:
            matches += 1
    return matches / len(keywords)


# ---------------------------------------------------------------------------
# Dynamic Budget & Relevance
# ---------------------------------------------------------------------------
DEFAULT_BASE_BUDGET: int = 8000
BUDGET_INCREMENT_PER_CHAPTER: int = 80


def _dynamic_budget(chapter_number: int, base_budget: int = DEFAULT_BASE_BUDGET) -> int:
    """动态预算公式: base + chapter_number * increment.

    验证值:
    - Ch1  = 8080
    - Ch50 = 12000
    - Ch70 = 13600
    - Ch100 = 16000
    """
    return base_budget + chapter_number * BUDGET_INCREMENT_PER_CHAPTER


def _calculate_dynamic_relevance(
    soft_ref: SoftReference,
    current_chapter: int,
    recent_chapters: list[int],
    chapter_goal: ChapterGoal | None = None,
) -> float:
    """基于时间衰减 + 关联强度计算动态相关性."""
    base = soft_ref.relevance_score
    if soft_ref.last_mentioned_chapter:
        age = current_chapter - soft_ref.last_mentioned_chapter
        decay = max(0.3, 1.0 - age * 0.05)
        base *= decay
    if soft_ref.last_mentioned_chapter in recent_chapters:
        base *= 1.3
    if soft_ref.is_critical:
        base = max(base, 0.9)
    # 077a: 关键词重叠维度 — 仅在有 chapter_goal 时激活
    if chapter_goal:
        keywords = _extract_keywords(chapter_goal)
        if keywords:
            # 从 content 中提取 setting_name（格式: "name: description"）
            setting_name = soft_ref.content.split(":")[0] if ":" in soft_ref.content else ""
            kw_score = _compute_keyword_overlap(setting_name, "", keywords)
            # 加权融合: time_decay x 0.6 + keyword_overlap x 0.4
            base = base * 0.6 + kw_score * 0.4
    # is_critical 保障（即使 kw_score 很低也保留高值）
    if soft_ref.is_critical:
        base = max(base, 0.9)
    return min(base, 1.0)


# ---------------------------------------------------------------------------
# Partition Builders
# ---------------------------------------------------------------------------
def _max_obligations_for_chapter(chapter_number: int) -> int:
    """Task 110b: 按章节阶段动态调整 obligations 保留数量."""
    if chapter_number <= 30:
        return 10
    if chapter_number <= 80:
        return 8
    return 6


def _estimate_tokens(text: str) -> int:
    """粗略估算中文字符 token 数（按 2 字符 ≈ 1 token）."""
    return max(1, len(text) // 2)


def _build_hard_constraints(
    chapter_goal: ChapterGoal,
    genre_profile: GenreProfile,
    project: ProjectSetting,
    human_marks: list[HumanMark] | None = None,
    chapter_number: int = 0,
) -> list[HardConstraint]:
    """构建硬约束 — obligations + taboos.

    Task 110b:
    - obligations 按章节阶段动态上限

    Task 111c:
    - human_marks 保留在 ContextPackage.human_marks 独立分区；
      进入 hard_constraints 的内容不可裁剪。
    """
    # 动态 obligations 上限
    effective_chapter = chapter_number or chapter_goal.chapter_number
    max_obligations = _max_obligations_for_chapter(effective_chapter)
    constraints: list[HardConstraint] = []
    # 只保留最近 N 条 obligations
    obligations = chapter_goal.obligations
    if len(obligations) > max_obligations:
        obligations = obligations[-max_obligations:]
    for obligation in obligations:
        constraints.append(
            HardConstraint(
                type="obligation",
                description=obligation,
                source="chapter_goal",
            )
        )
    for taboo in genre_profile.taboos:
        constraints.append(
            HardConstraint(
                type="taboo",
                description=taboo,
                source="genre_profile",
            )
        )
    for taboo in project.taboos:
        constraints.append(
            HardConstraint(
                type="taboo",
                description=taboo,
                source="project_setting",
            )
        )

    _ = human_marks
    current_token = sum(_estimate_tokens(c.description) for c in constraints)

    logger.info(
        "context_manager.hard_constraints_built",
        chapter_number=effective_chapter,
        obligation_count=len(obligations),
        mark_count=0,
        total_constraints=len(constraints),
        estimated_tokens=current_token,
    )
    return constraints


def _resolve_profile_level(
    character_id: str,
    is_protagonist: bool,
    is_antagonist: bool,
    current_chapter: int,
    last_appeared_chapters: dict[str, int] | None,
) -> Literal["full", "compact", "symbol", "skip"]:
    """V5.0 Task 102: 按未出场章数解析档案衰减级别.

    衰减规则：
    - 0-3 章：完整档案
    - 4-10 章：精简档案
    - 11-30 章：符号档案
    - 30+ 章：不加载（skip）

    protagonist / antagonist 核心角色永不衰减（保留完整档案）。
    """
    if is_protagonist or is_antagonist:
        return "full"
    if not last_appeared_chapters:
        return "full"
    last_chapter = last_appeared_chapters.get(character_id, 0)
    if last_chapter == 0:
        return "full"
    gap = current_chapter - last_chapter
    if gap <= 3:
        return "full"
    elif gap <= 10:
        return "compact"
    elif gap <= 30:
        return "symbol"
    return "skip"


def _build_character_snapshots(
    characters: list[Character],
    character_states: list[CharacterState],
    recent_summaries: list[ChapterSummary] | None = None,
    arc_boundaries: list[int] | None = None,
    current_chapter: int = 0,
    character_focus: list[dict] | None = None,
    last_appeared_chapters: dict[str, int] | None = None,
) -> list[CharacterStateSnapshot]:
    """构建角色状态快照 — 合并角色档案和最新状态.

    只加载出场角色 + 主角，防止长尺度角色膨胀（AGENTS.md #42）。
    080: 新增 Arc 出场窗口过滤 — 只加载当前 arc 内出场过的角色完整档案。
    Task 098: 支持 character_focus 的 full / compressed / skip 粒度控制。
    Task 102: 新增 CharacterFocalDecay — 按未出场章数四级衰减。
    """
    from songyan.agents.arc_boundary_resolver import ArcBoundaryResolver

    # 按角色 ID 分组状态
    state_map: dict[str, list[CharacterState]] = {}
    for state in character_states:
        state_map.setdefault(state.character_id, []).append(state)

    # 080: 确定当前 arc 范围
    arc_start = 1
    arc_end = current_chapter
    if current_chapter > 0:
        resolver = ArcBoundaryResolver()
        arc_start, arc_end = resolver.resolve(current_chapter, arc_boundaries)

    # 提取最近剧情中出现的角色（全量，用于向后兼容）
    appeared_names_recent: set[str] = set()
    if recent_summaries:
        for s in recent_summaries:
            appeared_names_recent.update(s.characters_appeared or [])

    # 080: 提取当前 arc 内出现的角色
    appeared_names_arc: set[str] = set()
    if recent_summaries and current_chapter > 0:
        for s in recent_summaries:
            if arc_start <= s.chapter_number <= arc_end:
                appeared_names_arc.update(s.characters_appeared or [])

    # 080: 确定过滤策略
    use_arc_window = current_chapter > 0 and (arc_boundaries is not None)

    if use_arc_window:
        # 080: 按 arc 窗口过滤 — 所有角色都加载，非 arc 角色用精简档案
        filtered_chars = list(characters)
    elif not recent_summaries:
        # 若未提供出场记录（如测试场景），不过滤，保持向后兼容
        filtered_chars = list(characters)
    else:
        # 回退：基于最近 summaries 的 characters_appeared 过滤（原有行为）
        filtered_chars = []
        for char in characters:
            is_protagonist = char.role_type == "protagonist"
            has_appeared = char.name in appeared_names_recent
            if is_protagonist or has_appeared:
                filtered_chars.append(char)

        # 回退：若过滤后为空，保留主角 + importance_score 最高的 3 个
        if not filtered_chars and characters:
            protagonists = [c for c in characters if c.role_type == "protagonist"]
            others = sorted(
                [c for c in characters if c.role_type != "protagonist"],
                key=lambda c: getattr(c, "importance_score", 0.5),
                reverse=True,
            )
            filtered_chars = protagonists + others[: max(0, 3 - len(protagonists))]

    # Task 098: 构建 character_focus 映射
    focus_map: dict[str, str] = {}
    if character_focus:
        for item in character_focus:
            if isinstance(item, dict):
                cid = str(item.get("character_id", ""))
                if cid:
                    focus_map[cid] = str(item.get("detail_level", "full"))

    snapshots: list[CharacterStateSnapshot] = []
    for char in filtered_chars:
        states = state_map.get(char.character_id, [])
        is_protagonist = char.role_type == "protagonist"
        is_antagonist = char.role_type == "antagonist"
        in_arc = char.name in appeared_names_arc if use_arc_window else True

        # Task 098: 检查 character_focus 指定的粒度
        focus_level = focus_map.get(char.character_id)
        if focus_level == "skip":
            continue  # 完全跳过

        # Task 102: 通过 focal decay 解析档案级别
        profile_level = _resolve_profile_level(
            char.character_id,
            is_protagonist,
            is_antagonist,
            current_chapter,
            last_appeared_chapters,
        )

        # character_focus 覆盖 decay 规则（人工指定优先）
        if focus_level == "full":
            profile_level = "full"
        elif focus_level == "compressed":
            profile_level = "compact"

        # Task 110c: 非 arc 角色直接 skip（protagonist/antagonist 除外）
        if (
            use_arc_window and not in_arc
            and not is_protagonist and not is_antagonist
            and not focus_level
        ):
            continue

        if profile_level == "skip":
            continue

        # 按 field 取最新状态（所有级别共用）
        latest_by_field: dict[str, str] = {}
        for state in states:
            latest_by_field[state.field] = state.value

        if profile_level == "full":
            importance = 1.0 if is_protagonist else 0.8
            snapshot = CharacterStateSnapshot(
                character_id=char.character_id,
                name=char.name,
                current_location=latest_by_field.get("location"),
                current_cultivation=latest_by_field.get("cultivation"),
                emotional_state=latest_by_field.get("emotional_state"),
                active_relationships=list(char.relationships.keys()),
                unresolved_issues=char.goals.copy(),
                importance_score=importance,
            )
        elif profile_level == "compact":
            summary_parts: list[str] = []
            if latest_by_field.get("location"):
                summary_parts.append(f"位置:{latest_by_field['location']}")
            if latest_by_field.get("emotional_state"):
                summary_parts.append(f"状态:{latest_by_field['emotional_state']}")
            _summary = "; ".join(summary_parts) if summary_parts else ""
            snapshot = CharacterStateSnapshot(
                character_id=char.character_id,
                name=char.name,
                current_location=latest_by_field.get("location"),
                current_cultivation=latest_by_field.get("cultivation"),
                emotional_state=_summary if _summary else latest_by_field.get("emotional_state"),
                active_relationships=[],
                unresolved_issues=[],
                importance_score=0.4 if not is_protagonist else 0.9,
            )
        else:  # symbol
            if last_appeared_chapters:
                last_ch = last_appeared_chapters.get(char.character_id, 0)
            else:
                last_ch = 0
            last_state = latest_by_field.get("emotional_state", "状态未知")
            last_loc = latest_by_field.get("location", "位置未知")
            symbol_summary = (
                f"【符号档案】最后出场Ch{last_ch}，"
                f"位置:{last_loc}，状态:{last_state}"
            )
            snapshot = CharacterStateSnapshot(
                character_id=char.character_id,
                name=char.name,
                current_location=None,
                current_cultivation=None,
                emotional_state=symbol_summary,
                active_relationships=[],
                unresolved_issues=[],
                importance_score=0.2,
            )
        snapshots.append(snapshot)
    return snapshots


def _build_recent_plot(
    summaries: list[ChapterSummary],
    last_chapter_ending: str = "",
    open_threads: list[str] | None = None,
) -> RecentPlot:
    """构建最近剧情 — 对每个 summary 按来源做长度截断防止上下文膨胀.

    V3.1 Layer 2: 更激进的截断策略，应对 Ch48+ 上下文膨胀
    （current_tokens 28469 / budget 9600，final_tokens 19398）。
    """
    # 按来源类型设置截断长度
    max_lengths = {
        "chapter": 120,
        "arc": 280,
        "volume": 180,
    }

    truncated_summaries: list[ChapterSummary] = []
    for s in summaries:
        max_len = max_lengths.get(s.source_type, 120)
        summary_text = s.summary
        if len(summary_text) > max_len:
            # 尽量在句子边界截断
            cut = summary_text[:max_len]
            last_period = max(cut.rfind("。"), cut.rfind("."), cut.rfind("；"))
            if last_period > max_len * 0.7:
                cut = cut[: last_period + 1]
            summary_text = cut + "..."
        truncated_summaries.append(
            ChapterSummary(
                chapter_number=s.chapter_number,
                summary=summary_text,
                key_events=s.key_events[:2] if s.key_events else [],
                characters_appeared=s.characters_appeared[:3] if s.characters_appeared else [],
                emotional_tone=s.emotional_tone,
                impact_score=s.impact_score,
                source_type=s.source_type,
            )
        )

    return RecentPlot(
        summaries=truncated_summaries,
        last_chapter_ending=last_chapter_ending,
        open_threads=open_threads or [],
    )


def _build_soft_references(
    settings: list[NewSetting],
    current_chapter: int = 0,
    recent_chapters: list[int] | None = None,
    chapter_goal: ChapterGoal | None = None,
) -> list[SoftReference]:
    """构建软参考 — 从设定快照转换，应用动态相关性."""
    refs: list[SoftReference] = []
    n = len(settings)
    for setting in settings:
        i = len(refs)
        # 077a: 从列表位置估计 last_mentioned_chapter
        # i=0 是最旧，i=n-1 是最新
        estimated_chapter: int | None = None
        if current_chapter > 0:
            if n > 1:
                estimated_chapter = round(1 + (i / (n - 1)) * (current_chapter - 1))
            else:
                estimated_chapter = current_chapter
        # 077a: 判断是否关键设定（在 target_events/obligations 中出现）
        is_critical = False
        if chapter_goal:
            is_critical = _is_setting_critical(setting, chapter_goal)
        ref = SoftReference(
            type="world_setting",
            content=f"{setting.setting_name}: {setting.description}",
            relevance_score=0.7,
            last_mentioned_chapter=estimated_chapter,
            is_critical=is_critical,
        )
        if current_chapter > 0:
            ref.relevance_score = _calculate_dynamic_relevance(
                ref, current_chapter, recent_chapters or [], chapter_goal=chapter_goal
            )
        refs.append(ref)
    return refs


def _build_rag_soft_references(
    retrieved_chunks: list[RetrievedChunk],
) -> list[SoftReference]:
    """将 RAG 检索结果转换为 SoftReference.

    relevance_score = similarity + 0.3，确保 RAG 结果优先于普通 setting snapshots。
    """
    refs: list[SoftReference] = []
    for chunk in retrieved_chunks:
        refs.append(
            SoftReference(
                type="rag_retrieval",
                content=chunk.text,
                relevance_score=min(chunk.similarity + 0.3, 1.0),
                source_chapter=chunk.chapter_number,
                similarity=chunk.similarity,
            )
        )
    return refs


def _build_genre_rules(
    genre_profile: GenreProfile,
    project: ProjectSetting,
    chapter_goal: ChapterGoal,
) -> GenreRules:
    """从 GenreProfile 构建 GenreRules，注入子类型规则，按需过滤.

    V3.1: 按 chapter_type 过滤 reviewer_focus 和 satisfaction_types。
    """
    from ._genre_filter import filter_genre_profile

    filtered = filter_genre_profile(genre_profile, chapter_goal)

    sub_genre_rules: list[str] = []
    if project.sub_genre_id and filtered.sub_genres:
        sub = next(
            (
                s
                for s in filtered.sub_genres
                if s.sub_genre_id == project.sub_genre_id
            ),
            None,
        )
        if sub:
            sub_genre_rules = sub.differentiation_rules

    # V4.0: 按 chapter_type 分组加载 writer_rules
    chapter_type = (chapter_goal.chapter_type or "").lower()
    if genre_profile.writer_rules_by_type and chapter_type in genre_profile.writer_rules_by_type:
        writer_rules = genre_profile.writer_rules_by_type[chapter_type]
    else:
        writer_rules = filtered.writer_rules

    return GenreRules(
        genre_id=filtered.id,
        writer_rules=writer_rules,
        fatigue_words=filtered.fatigue_words,
        satisfaction_types=filtered.satisfaction_types,
        pacing_rule=filtered.pacing_rule,
        taboos=filtered.taboos,
        style_baseline=filtered.style_baseline,
        pacing_templates=[pt.model_dump() for pt in filtered.pacing_templates],
        sensory_templates=[st.model_dump() for st in filtered.sensory_templates],
        sub_genre_rules=sub_genre_rules,
        reviewer_focus=filtered.reviewer_focus,
    )


def _build_mode_rules(mode_profile: CreativeModeProfile) -> ModeRules:
    """从 CreativeModeProfile 构建 ModeRules."""
    tolerance = mode_profile.tolerance or {}
    return ModeRules(
        mode_id=mode_profile.id,
        revision_policy=mode_profile.revision_policy,
        tolerance_max_ai_tells=tolerance.get("max_ai_tells", 2.0),
        tolerance_max_fatigue_words=tolerance.get("max_fatigue_words", 3.0),
        tolerance_max_cliche_risk=tolerance.get("max_cliche_risk", 2.0),
        context_pruning_strategy=mode_profile.context_pruning_strategy,
    )
