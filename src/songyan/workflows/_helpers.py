"""Workflow 辅助函数 — 数据加载和上下文组装."""

from __future__ import annotations

import sqlite3
import uuid
from typing import Any

import structlog

from songyan.db.context_repo import CharacterStateRepository, SummaryRepository
from songyan.db.continuity_repo import SettingTrackingRepository
from songyan.db.layered_context_repo import (
    ArcSummaryRepository,
    PermanentSceneRepository,
    VolumeSummaryRepository,
)
from songyan.db.repository import (
    ChapterVersionRepository,
    CharacterRepository,
    ProjectRepository,
)
from songyan.db.review_repo import CreativeBriefRepository, ReviewReportRepository
from songyan.db.settlement_repo import (
    ForeshadowingRepository,
    SettingSnapshotRepository,
)
from songyan.exceptions import LLMError, LLMResponseParseError
from songyan.genres.loader import load_genre_profile
from songyan.models import (
    ArcSummary,
    ChapterGoal,
    ChapterSummary,
    ChapterVersion,
    ContextPackage,
    CreativeBrief,
    LLMAuditResult,
    MergedReviewReport,
    OpenThread,
    PermanentScene,
    ProjectSetting,
    RuleAuditResult,
    VolumeSummary,
)
from songyan.models.rag import RAGConfig
from songyan.workflows._narrative_context import NarrativeGoalContext, load_narrative_goal_context

logger = structlog.get_logger(__name__)


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


async def load_project(project_id: str) -> ProjectSetting | None:
    return await ProjectRepository().get(project_id)


async def load_characters(project_id: str) -> list[Any]:
    return await CharacterRepository().list_by_project(project_id)


async def ensure_protagonist_character(
    project_id: str,
    project: ProjectSetting | None = None,
) -> bool:
    """确保项目至少有一条 protagonist Character 记录（幂等）.

    Task 170e 根因：`songyan create` 只把 protagonist_name 存进 projects 表，
    从不建 Character 记录；settlement 遇未知 character_id 是 skip 而非新建。
    因此未经脚本 seed 的项目 characters 表为空，DialogueStyleCard 声纹机制
    （generate_dialogue_style_cards 只为已存在的角色生成）永远不激活，
    对白全员塌陷成旁白腔。

    本函数在项目创建与流水线启动处调用，用 project.protagonist_name 补建
    一条最小 protagonist 记录，让声纹机制有落点。

    幂等保证（不干扰已 seed 的项目/测试）：
    - 项目不存在 → 直接返回 False，不写任何数据。
    - 已存在任意 protagonist 角色 → 返回 False，不新建。
    - protagonist_name 为空 → 返回 False，不新建。

    Returns:
        True 表示本次新建了 protagonist；False 表示无需新建。
    """
    if project is None:
        project = await load_project(project_id)
    if project is None:
        return False

    existing = await CharacterRepository().list_by_project(project_id)
    if any(c.role_type == "protagonist" for c in existing):
        return False

    name = (project.protagonist_name or "").strip()
    if not name:
        return False

    from songyan.models.character import Character

    character = Character(
        character_id=new_id("char"),
        project_id=project_id,
        name=name,
        role_type="protagonist",
        background=project.protagonist_background or "",
    )
    await CharacterRepository().create(character)
    logger.info(
        "ensure_protagonist_character.created",
        project_id=project_id,
        character_id=character.character_id,
        name=name,
    )
    return True


# Task 170g Phase2: 非角色声源（建造者/残影/守门人 等）声纹卡工程化.
# 这些声源在正文里以"独白/揭示"形式说话，但不是 characters 表里的人物，
# 声纹机制不会为它们生成 DialogueStyleCard，导致它们全员同质冷静腔。
# 本 helper 为已知非角色声源补一张确定性声纹卡，注入 Writer 时区分声线。
_NON_CHARACTER_VOICE_NAMES: frozenset[str] = frozenset(
    {"建造者", "建造者文明", "残影", "前代", "碎片", "守门人", "舰队之手", "意识"}
)

_NON_CHARACTER_VOICE_STYLE: dict[str, str] = {
    "sentence_length_preference": "medium",
    "anger_expression": "不升调，用更精确、更冷的措辞表达压迫感",
    "fear_expression": "以停顿和信息缺口暗示，不直述恐惧",
    "joy_expression": "近乎没有，至多是一丝机械的满足",
    "sadness_expression": "以事实陈述承载，不外露",
    "pause_habit": "在关键概念前后留一次刻意停顿",
    "social_role_speech_pattern": "以宣告/协议/裁决式语气说话，不寒暄、不解释动机",
}


def _build_non_character_voice_cards(
    appeared_names: set[str],
    project_id: str,
    existing_character_names: set[str],
) -> list[Any]:
    """Task 170g Phase2: 为本章出场的非角色声源构造声纹卡.

    Args:
        appeared_names: 本章出场/发声的名字集合。
        project_id: 项目 ID。
        existing_character_names: 已有 Character 记录的角色名（跳过，避免与真人重复）。

    Returns:
        DialogueStyleCard 列表，character_id 形如 ``voice-建造者``。
        只为 ``_NON_CHARACTER_VOICE_NAMES`` 内、且不在 existing 里的名字生成。
    """
    from songyan.models.character import DialogueStyleCard

    cards: list[Any] = []
    for name in sorted(appeared_names):
        if name not in _NON_CHARACTER_VOICE_NAMES:
            continue
        if name in existing_character_names:
            continue
        cards.append(
            DialogueStyleCard(
                character_id=f"voice-{name}",
                project_id=project_id,
                sentence_length_preference="medium",
                common_openers=[f"{name}的声音", "在你听清之前"],
                common_closers=["——仅此一次。", "剩下的你自己看。"],
                anger_expression=_NON_CHARACTER_VOICE_STYLE["anger_expression"],
                fear_expression=_NON_CHARACTER_VOICE_STYLE["fear_expression"],
                joy_expression=_NON_CHARACTER_VOICE_STYLE["joy_expression"],
                sadness_expression=_NON_CHARACTER_VOICE_STYLE["sadness_expression"],
                metaphor_frequency="rare",
                pause_habit=_NON_CHARACTER_VOICE_STYLE["pause_habit"],
                social_role_speech_pattern=_NON_CHARACTER_VOICE_STYLE[
                    "social_role_speech_pattern"
                ],
            )
        )
    return cards


async def load_character_states(project_id: str) -> list[Any]:
    return await CharacterStateRepository().list_latest_by_project(project_id)


async def load_recent_summaries(project_id: str, chapter_number: int) -> list[Any]:
    return await SummaryRepository().list_recent(project_id, chapter_number)


async def load_layered_summaries(
    project_id: str, current_chapter: int
) -> list[ChapterSummary]:
    """分层加载摘要 — 金字塔结构（TemporalCompressor）.

    V5.0 Task 101: 从"平铺所有 Arc"改为"金字塔分层"，
    让历史信息的 token 占用从 O(n) 降到 O(log n)。

    策略：
    - 最近 5 章：逐章精细 ChapterSummary（source_type="chapter"）
    - 最近已完成弧：单个 ArcSummary（source_type="arc"），
      只取最近一个已完成弧，而非所有历史弧
    - 历史卷：单个 VolumeSummary（source_type="volume"），
      只取在 current_chapter 之前结束的最近一个卷
    """
    result: list[ChapterSummary] = []
    covered_chapters: set[int] = set()

    # 1. 精细层：最近 5 章（按 chapter_number 升序）
    recent = await SummaryRepository().list_recent(
        project_id, before_chapter=current_chapter + 1, limit=5
    )
    for s in recent:
        # 确保 source_type 标记为 chapter
        if getattr(s, "source_type", None) != "chapter":
            s = ChapterSummary(
                chapter_number=s.chapter_number,
                summary=s.summary,
                key_events=s.key_events,
                characters_appeared=s.characters_appeared,
                emotional_tone=getattr(s, "emotional_tone", ""),
                impact_score=s.impact_score,
                source_type="chapter",
            )
        result.append(s)
        covered_chapters.add(s.chapter_number)

    # 2. Arc 层：只取最近一个已完成弧（end_chapter < current_chapter）
    # 且不与精细层完全重叠，避免冗余
    all_arcs = await ArcSummaryRepository().list_by_project(project_id)
    completed_arcs = [a for a in all_arcs if a.end_chapter < current_chapter]
    if completed_arcs:
        # 取 end_chapter 最大的（最近完成的）
        latest_arc = max(completed_arcs, key=lambda a: a.end_chapter)
        arc_range = set(range(latest_arc.start_chapter, latest_arc.end_chapter + 1))
        if not arc_range.issubset(covered_chapters):
            result.append(
                ChapterSummary(
                    chapter_number=latest_arc.start_chapter,
                    summary=latest_arc.arc_summary,
                    key_events=latest_arc.key_events,
                    characters_appeared=list(latest_arc.character_arcs.keys()),
                    impact_score=0.0,
                    source_type="arc",
                )
            )
            covered_chapters.update(arc_range)

    # 3. Volume 层：只取在 current_chapter 之前结束的最近一个卷
    # 当前卷的信息由逐章摘要和弧摘要覆盖，无需重复加载
    prev_volume = await VolumeSummaryRepository().get_previous_volume(
        project_id, current_chapter
    )
    if prev_volume:
        result.append(
            ChapterSummary(
                chapter_number=0,  # 排在最前面
                summary=prev_volume.volume_summary,
                key_events=prev_volume.major_revelations,
                impact_score=0.0,
                source_type="volume",
            )
        )

    result.sort(key=lambda s: s.chapter_number)

    logger.info(
        "load_layered_summaries.pyramid",
        project_id=project_id,
        current_chapter=current_chapter,
        chapter_count=len([s for s in result if s.source_type == "chapter"]),
        arc_count=len([s for s in result if s.source_type == "arc"]),
        volume_count=len([s for s in result if s.source_type == "volume"]),
        total_count=len(result),
    )
    return result


async def load_active_foreshadowings(project_id: str) -> list[Any]:
    return await ForeshadowingRepository().list_active(project_id)


async def load_setting_snapshots(project_id: str) -> list[Any]:
    return await SettingSnapshotRepository().list_by_project(project_id)


# Phase 4: 分层上下文加载函数
async def load_arc_context(project_id: str, chapter_number: int) -> ArcSummary | None:
    return await ArcSummaryRepository().get_current_arc(project_id, chapter_number)


async def load_volume_context(project_id: str, chapter_number: int) -> VolumeSummary | None:
    return await VolumeSummaryRepository().get_current_volume(project_id, chapter_number)


async def load_permanent_scenes(project_id: str, limit: int = 5) -> list[PermanentScene]:
    return await PermanentSceneRepository().list_by_project(project_id, limit)


async def load_open_threads(project_id: str, up_to_chapter: int) -> list[OpenThread]:
    """从最近 10 章的 summaries 中聚合 open_threads.

    轻量级实现：扫描 summaries.open_threads（JSON 数组），
    为每个 thread 描述生成一个 OpenThread 对象。
    """
    summaries = await SummaryRepository().list_recent(
        project_id, before_chapter=up_to_chapter + 1, limit=10
    )

    threads: list[OpenThread] = []
    for summary in summaries:
        # 高 impact_score 的 summary 视为线索
        if summary.impact_score >= 0.5:
            threads.append(
                OpenThread(
                    thread_id=f"thread-{project_id}-{summary.chapter_number}",
                    description=summary.summary,
                    source_type="setting",
                    source_chapter=summary.chapter_number,
                    priority=min(summary.impact_score, 1.0),
                )
            )
    return threads


async def load_chapter_goal(goal_id: str) -> ChapterGoal | None:
    from songyan.db.repository import ChapterGoalRepository

    return await ChapterGoalRepository().get(goal_id)


async def load_creative_brief(brief_id: str) -> CreativeBrief | None:
    return await CreativeBriefRepository().get(brief_id)


async def load_version(version_id: str) -> ChapterVersion | None:
    return await ChapterVersionRepository().get(version_id)


async def trigger_layered_summaries(
    project_id: str,
    chapter_number: int,
    project: ProjectSetting,
) -> None:
    """章节 accept 后触发弧/卷摘要生成（异步，失败不阻塞主流程）.

    Args:
        project_id: 项目 ID.
        chapter_number: 当前章节号.
        project: 项目配置（用于读取 arc_boundaries / volume_boundaries）.
    """
    from songyan.agents.arc_boundary_resolver import ArcBoundaryResolver
    from songyan.agents.arc_summary_generator import (
        ArcSummaryGenerator,
        VolumeSummaryGenerator,
    )
    from songyan.db.layered_context_repo import ArcSummaryRepository

    resolver = ArcBoundaryResolver()
    boundaries = project.arc_boundaries if project.arc_boundaries else None

    # 1. 检查是否跨越弧边界
    arc_start, arc_end = resolver.resolve(chapter_number, boundaries)
    if arc_end == chapter_number:
        try:
            generator = ArcSummaryGenerator()
            await generator.generate(project_id, arc_start, arc_end)
        except (LLMError, LLMResponseParseError, RuntimeError, ValueError, TypeError):
            logger.exception(
                "trigger_layered_summaries.arc_failed",
                project_id=project_id,
                chapter_number=chapter_number,
                arc_start=arc_start,
                arc_end=arc_end,
            )

    # 2. 检查是否跨越卷边界
    volume_boundaries = project.volume_boundaries if project.volume_boundaries else []
    is_volume_boundary = False
    if volume_boundaries:
        is_volume_boundary = chapter_number in volume_boundaries
    else:
        # 默认每 30 章一个卷
        is_volume_boundary = chapter_number > 0 and chapter_number % 30 == 0

    if is_volume_boundary:
        try:
            arcs = await ArcSummaryRepository().list_by_project(project_id)
            # 只取当前卷范围内的 arcs
            if volume_boundaries:
                vol_start = 1
                for vb in volume_boundaries:
                    if chapter_number == vb:
                        break
                    vol_start = vb + 1
            else:
                vol_start = ((chapter_number - 1) // 30) * 30 + 1

            vol_arcs = [
                a for a in arcs
                if a.start_chapter >= vol_start and a.end_chapter <= chapter_number
            ]
            vol_gen = VolumeSummaryGenerator()
            await vol_gen.generate(project_id, vol_arcs)
        except (LLMError, LLMResponseParseError, RuntimeError, ValueError, TypeError):
            logger.exception(
                "trigger_layered_summaries.volume_failed",
                project_id=project_id,
                chapter_number=chapter_number,
            )


async def load_merged_report(version_id: str) -> MergedReviewReport | None:
    """加载指定版本的最新合并审查报告."""
    return await ReviewReportRepository().get_by_version(version_id)


async def load_latest_audits(
    version_id: str,
) -> tuple[RuleAuditResult | None, LLMAuditResult | None]:
    """加载指定版本的最新 rule 和 llm 审计结果."""
    repo = ReviewReportRepository()
    rule_report = await repo.get_by_version(version_id, audit_type="rule")
    llm_report = await repo.get_by_version(version_id, audit_type="llm")
    return (
        rule_report.rule_audit if rule_report else None,
        llm_report.llm_audit if llm_report else None,
    )


async def assemble_context_package(
    project_id: str,
    chapter_number: int,
    chapter_goal: ChapterGoal,
    creative_brief: CreativeBrief | None,
    *,
    narrative_fullness: float = 0.0,
    character_focus: list[dict[str, Any]] | None = None,
    foreshadowing_due: list[str] | None = None,
    focal_distance: str = "mid",
) -> ContextPackage:
    """组装 ContextPackage — 从 DB 加载所有依赖."""
    from songyan.agents.context_manager import assemble_context_package as _assemble
    from songyan.creative_modes.registry import load_creative_mode_profile

    project = await load_project(project_id)
    if project is None:
        raise ValueError(f"Project not found: {project_id}")

    genre_profile = load_genre_profile(project.genre_id)
    mode_profile = load_creative_mode_profile(project.mode_id)

    # Phase 8b: RAG 检索
    rag_chunks = None
    rag_config = mode_profile.rag_config

    # CLI 覆盖 RAG 模式
    import os
    cli_rag_mode = os.environ.get("SONGYAN_RAG_MODE")
    if cli_rag_mode:
        rag_config.enabled = cli_rag_mode  # type: ignore[assignment]

    from songyan.db.human_mark_repo import HumanMarkRepository
    from songyan.models.rag import RAGConfig
    from songyan.rag.utils import should_enable_rag

    effective_rag_config = RAGConfig(**rag_config.model_dump())

    if should_enable_rag(chapter_number, project, effective_rag_config):
        try:
            from songyan.db.chunk_repo import ChunkRepository
            from songyan.models.context import ChapterSummary, RecentPlot
            from songyan.rag.embedder import Embedder
            from songyan.rag.retriever import RAGRetriever
            from songyan.rag.vector_store import VectorStore

            recent_summaries = await load_recent_summaries(project_id, chapter_number)
            recent_plot = RecentPlot(
                summaries=[
                    ChapterSummary(
                        chapter_number=s.chapter_number,
                        summary=s.summary,
                        key_events=s.key_events,
                        characters_appeared=s.characters_appeared,
                        emotional_tone=s.emotional_tone,
                        impact_score=s.impact_score,
                    )
                    for s in recent_summaries
                ],
            )

            embedder = Embedder(model_name=rag_config.embedding_model)
            store = VectorStore(project_id, ChunkRepository())
            retriever = RAGRetriever(
                embedder=embedder,
                vector_store=store,
                rag_config=effective_rag_config,
            )
            rag_chunks = await retriever.retrieve_for_chapter(
                project_id=project_id,
                chapter_number=chapter_number,
                chapter_goal=chapter_goal,
                recent_plot=recent_plot,
            )
        except (RuntimeError, OSError, ConnectionError, ValueError, TypeError):
            logger.exception(
                "rag.retrieve_failed",
                project_id=project_id,
                chapter_number=chapter_number,
            )

    # Phase 7/054: 加载 human marks（含连续性审计生成的约束）
    human_marks = await HumanMarkRepository().list_by_project(
        project_id=project_id,
        include_resolved=False,
    )

    # V3.1 Layer 2: 先加载最近剧情摘要，用于过滤角色
    recent_summaries = await load_layered_summaries(project_id, chapter_number)

    # Task 074: 从角色档案中提取对话风格卡
    # V3.1 Layer 2: 只保留主角 + 最近剧情中出现的角色的风格卡，防止 Ch40+ 膨胀
    characters = await load_characters(project_id)
    appeared_names: set[str] = set()
    for s in recent_summaries:
        appeared_names.update(s.characters_appeared or [])

    dialogue_style_cards: list[Any] = []
    for char in characters:
        if char.dialogue_style_card is None:
            continue
        if char.role_type == "protagonist" or char.name in appeared_names:
            dialogue_style_cards.append(char.dialogue_style_card)

    # Task 102: 加载角色最后出场章节，用于 CharacterFocalDecay
    last_appeared = await CharacterStateRepository().get_last_appeared_chapters(
        project_id
    )

    # Task 138n/151: 查询 critical orphan 并注入 mandatory_references，带自适应上限与主线相关性排序
    scenes_count = 3
    if creative_brief is not None and getattr(creative_brief, "punch_points", None):
        scenes_count = max(len(creative_brief.punch_points), 3)
    active_critical_count, mainline_thread_keys = await _compute_mandatory_reference_inputs(
        project_id, chapter_number
    )
    mandatory_references = await _load_critical_mandatory_references(
        project_id,
        chapter_number,
        scenes_count=scenes_count,
        active_critical_count=active_critical_count,
        mainline_thread_keys=mainline_thread_keys,
    )

    return _assemble(
        chapter_goal=chapter_goal,
        creative_brief=creative_brief,
        genre_profile=genre_profile,
        mode_profile=mode_profile,
        project=project,
        characters=characters,
        character_states=await load_character_states(project_id),
        recent_summaries=recent_summaries,
        active_foreshadowings=await load_active_foreshadowings(project_id),
        setting_snapshots=await load_setting_snapshots(project_id),
        arc_context=await load_arc_context(project_id, chapter_number),
        volume_context=await load_volume_context(project_id, chapter_number),
        permanent_scenes=await load_permanent_scenes(project_id),
        open_threads=await load_open_threads(project_id, chapter_number),
        rag_chunks=rag_chunks,
        human_marks=human_marks,
        dialogue_style_cards=dialogue_style_cards,
        narrative_fullness=narrative_fullness,
        character_focus=character_focus,
        foreshadowing_due=foreshadowing_due,
        focal_distance=focal_distance,
        last_appeared_chapters=last_appeared,
        mandatory_references=mandatory_references,
    )


# Task 138j: 根据 setting_key 的 alias 推断回收提示
_RECYCLE_HINTS: dict[str, str] = {
    "surface_material": (
        "可通过环境描写（触感、视觉观察）、角色对话提及材料特性、"
        "或与其他材质对比来回收"
    ),
    "phase_flush_mechanism": (
        "可通过角色讨论技术原理、剧情中触发/关闭机制、"
        "或发现机制残留痕迹来回收"
    ),
    "team_7": (
        "可通过角色对话回忆团队行动、提及团队成员、"
        "或发现团队遗留痕迹来回收"
    ),
    "core_space": (
        "可通过空间环境描写、角色进入/离开核心区域的行动、"
        "或核心区域对剧情的影响来回收"
    ),
    "living_wall": (
        "可通过墙壁的异常行为描写、角色与墙壁的互动、"
        "或墙壁对环境的改变来回收"
    ),
}


def _infer_recycle_hint(key_alias: str) -> str:
    """根据 setting_key 的最后一个 segment 返回回收提示."""
    return _RECYCLE_HINTS.get(
        key_alias,
        "可通过角色对话回顾、环境细节呼应、或剧情事件直接触发来回收",
    )


def _extract_mainline_thread_keys(narrative_ctx: NarrativeGoalContext | None) -> set[str]:
    """Extract mainline thread keys (thread_id + title) from narrative context."""
    if narrative_ctx is None or not narrative_ctx.has_skeleton:
        return set()
    keys: set[str] = set()
    for thread in (*narrative_ctx.open_threads, *narrative_ctx.threads_to_resolve):
        if thread.get("is_mainline"):
            keys.add(str(thread.get("thread_id") or ""))
            keys.add(str(thread.get("title") or ""))
    return {k for k in keys if k}


async def _compute_mandatory_reference_inputs(
    project_id: str,
    chapter_number: int,
) -> tuple[int, set[str]]:
    """Compute inputs for adaptive MR cap and relevance sorting.

    Returns:
        (active_critical_count, mainline_thread_keys)
    """
    active_critical_count = 0
    try:
        rows = await SettingTrackingRepository().list_by_project(project_id)
        active_critical_count = sum(
            1
            for row in rows
            if row.get("status") == "active" and row.get("category") == "critical"
        )
    except sqlite3.OperationalError:
        logger.warning(
            "task151.setting_tracking_query_failed",
            project_id=project_id,
            chapter_number=chapter_number,
        )

    mainline_keys: set[str] = set()
    try:
        narrative_ctx = await load_narrative_goal_context(project_id, chapter_number)
        mainline_keys = _extract_mainline_thread_keys(narrative_ctx)
    except sqlite3.OperationalError:
        logger.warning(
            "task151.narrative_context_query_failed",
            project_id=project_id,
            chapter_number=chapter_number,
        )

    return active_critical_count, mainline_keys


async def _load_critical_mandatory_references(
    project_id: str,
    chapter_number: int,
    scenes_count: int = 3,
    max_mandatory_references: int | None = None,
    *,
    active_critical_count: int | None = None,
    mainline_thread_keys: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Task 138n/151: 从 SettingTrackingRepository 加载 critical orphan 作为强制回收约束.

    筛选条件：
    - status == "active"
    - category == "critical"
    - 沉寂章数 >= ORPHANED_THRESHOLDS["critical"]（默认 3 章）

    上限：默认自适应计算 ``cap = min(max(active_critical_count,
    scenes_count * 2, 6), 16)``；也可通过 ``max_mandatory_references`` 显式覆盖。

    排序：主线相关（setting_key/name 与 mainline_thread_keys 子串匹配）优先；
    其次按 ``silent_chapters`` 降序、``introduced_in_chapter`` 升序保留最紧急的 N 条。
    无骨架 / 无线索时退化为旧排序 ``(silent_chapters, -introduced_in_chapter)``。

    返回格式：
    [
        {
            "setting_key": str,
            "setting_name": str,
            "category": "critical",
            "silent_chapters": int,
            "introduced_in_chapter": int,
            "last_mentioned_chapter": int,
            "recycle_hint": str,
        },
        ...
    ]
    """
    from songyan.agents.continuity_auditor._scanners import ORPHANED_THRESHOLDS

    if max_mandatory_references is None:
        base_count = active_critical_count if active_critical_count is not None else 0
        max_mandatory_references = min(max(base_count, scenes_count * 2, 6), 16)

    rows = await SettingTrackingRepository().list_by_project(project_id)
    threshold = ORPHANED_THRESHOLDS.get("critical", 3)
    mainline_keys = mainline_thread_keys or set()
    mainline_keys_lower = {k.lower() for k in mainline_keys if k}

    result: list[dict[str, Any]] = []
    for row in rows:
        if row.get("status") != "active":
            continue
        if row.get("category") != "critical":
            continue
        last_mentioned = row.get("last_mentioned_chapter") or 0
        silent = chapter_number - last_mentioned
        if silent < threshold:
            continue
        setting_key = str(row.get("setting_key") or "")
        setting_name = str(
            row.get("setting_name") or row.get("setting_key") or "未命名设定"
        )
        key_alias = setting_key.split(".")[-1]

        haystacks = {setting_key.lower(), setting_name.lower()}
        is_mainline_related = False
        if mainline_keys_lower:
            for mainline_key in mainline_keys_lower:
                for haystack in haystacks:
                    if mainline_key in haystack or haystack in mainline_key:
                        is_mainline_related = True
                        break
                if is_mainline_related:
                    break

        result.append(
            {
                "setting_key": setting_key,
                "setting_name": setting_name,
                "category": "critical",
                "silent_chapters": silent,
                "introduced_in_chapter": int(row.get("introduced_in_chapter") or 0),
                "last_mentioned_chapter": last_mentioned,
                "recycle_hint": _infer_recycle_hint(key_alias),
                "is_mainline_related": is_mainline_related,
            }
        )

    # 按 (主线相关, 沉默章数, -引入章) 降序：主线相关优先，其次最紧急且越早引入的越优先
    result.sort(
        key=lambda r: (r["is_mainline_related"], r["silent_chapters"], -r["introduced_in_chapter"]),
        reverse=True,
    )

    mainline_related_count = sum(1 for r in result if r["is_mainline_related"])
    if len(result) > max_mandatory_references:
        dropped = result[max_mandatory_references:]
        result = result[:max_mandatory_references]
        logger.info(
            "task138n.mandatory_references_truncated",
            project_id=project_id,
            chapter_number=chapter_number,
            scenes_count=scenes_count,
            adaptive_cap=max_mandatory_references,
            active_critical_count=active_critical_count,
            mainline_related_count=mainline_related_count,
            kept=max_mandatory_references,
            dropped_keys=[r["setting_key"] for r in dropped],
        )
    logger.info(
        "task138n.mandatory_references_loaded",
        project_id=project_id,
        chapter_number=chapter_number,
        scenes_count=scenes_count,
        adaptive_cap=max_mandatory_references,
        active_critical_count=active_critical_count,
        mainline_related_count=mainline_related_count,
        count=len(result),
        keys=[r["setting_key"] for r in result],
    )
    return result


# ---------------------------------------------------------------------------
# Phase 8b: RAG indexing

# ---------------------------------------------------------------------------


async def _index_accepted_chapter(
    project_id: str,
    chapter_number: int,
    version_id: str,
    content: str,
    rag_config: RAGConfig,
) -> None:
    """为已接受的章节建立 RAG 向量索引.

    在 settlement_extractor_node 完成后非阻塞调用。
    失败仅记录日志，不阻塞主流程。
    """
    if rag_config.enabled == "never":
        return

    from songyan.db.chunk_repo import ChunkRepository
    from songyan.db.continuity_repo import SettingTrackingRepository
    from songyan.rag.chunker import Chunker
    from songyan.rag.embedder import Embedder

    try:
        # 获取已知角色名和设定 key（用于 metadata 提取）
        characters = await CharacterRepository().list_by_project(project_id)
        known_characters = [c.name for c in characters if c.name]

        settings = await SettingTrackingRepository().list_by_project(project_id)
        known_settings = [str(s["setting_key"]) for s in settings if s.get("setting_key")]

        # 切分
        chunker = Chunker(
            chunk_size=rag_config.chunk_size,
            chunk_overlap=rag_config.chunk_overlap,
        )
        chunks = chunker.chunk_chapter(
            content=content,
            project_id=project_id,
            chapter_number=chapter_number,
            version_id=version_id,
            known_characters=known_characters,
            known_settings=known_settings,
        )
        logger.info(
            "rag.chunked",
            project_id=project_id,
            chapter_number=chapter_number,
            chunk_count=len(chunks),
        )
        if not chunks:
            return

        # 编码
        embedder = Embedder(model_name=rag_config.embedding_model)
        embeddings = await embedder.aembed([c.text for c in chunks])
        logger.info(
            "rag.embedded",
            project_id=project_id,
            chapter_number=chapter_number,
            embedding_shape=embeddings.shape,
        )

        # 写入存储（先清理旧数据）
        repo = ChunkRepository()
        await repo.delete_by_chapter(project_id, chapter_number)
        await repo.bulk_insert(chunks, embeddings)

        logger.info(
            "rag.indexed",
            project_id=project_id,
            chapter_number=chapter_number,
            chunk_count=len(chunks),
            embedding_shape=embeddings.shape,
        )
    except (RuntimeError, OSError, ConnectionError, ValueError, TypeError, TimeoutError):
        logger.exception(
            "rag.index_failed",
            project_id=project_id,
            chapter_number=chapter_number,
        )
