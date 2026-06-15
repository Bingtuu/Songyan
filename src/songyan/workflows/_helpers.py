"""Workflow 辅助函数 — 数据加载和上下文组装."""

from __future__ import annotations

import uuid

import structlog

from songyan.db.context_repo import CharacterStateRepository, SummaryRepository
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

logger = structlog.get_logger(__name__)

from songyan.models import (
    ArcSummary,
    ChapterGoal,
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


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


async def load_project(project_id: str) -> ProjectSetting | None:
    return await ProjectRepository().get(project_id)


async def load_characters(project_id: str) -> list:
    return await CharacterRepository().list_by_project(project_id)


async def load_character_states(project_id: str) -> list:
    return await CharacterStateRepository().list_latest_by_project(project_id)


async def load_recent_summaries(project_id: str, chapter_number: int) -> list:
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
    from songyan.models import ChapterSummary

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


async def load_active_foreshadowings(project_id: str) -> list:
    return await ForeshadowingRepository().list_active(project_id)


async def load_setting_snapshots(project_id: str) -> list:
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
    character_focus: list[dict] | None = None,
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
        from songyan.models.rag import RAGConfig

        rag_config = RAGConfig(**rag_config.model_dump())
        rag_config.enabled = cli_rag_mode  # type: ignore[assignment]

    from songyan.db.human_mark_repo import HumanMarkRepository
    from songyan.rag.utils import should_enable_rag

    if should_enable_rag(chapter_number, project, rag_config):
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
                rag_config=rag_config,
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

    dialogue_style_cards: list = []
    for char in characters:
        if char.dialogue_style_card is None:
            continue
        if char.role_type == "protagonist" or char.name in appeared_names:
            dialogue_style_cards.append(char.dialogue_style_card)

    # Task 102: 加载角色最后出场章节，用于 CharacterFocalDecay
    last_appeared = await CharacterStateRepository().get_last_appeared_chapters(
        project_id
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
    )


# ---------------------------------------------------------------------------
# Phase 8b: RAG indexing
# ---------------------------------------------------------------------------


async def _index_accepted_chapter(
    project_id: str,
    chapter_number: int,
    version_id: str,
    content: str,
    rag_config,
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
        known_settings = [s.get("setting_key") for s in settings if s.get("setting_key")]

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
    except (RuntimeError, OSError, ConnectionError, ValueError, TypeError):
        logger.exception(
            "rag.index_failed",
            project_id=project_id,
            chapter_number=chapter_number,
        )
