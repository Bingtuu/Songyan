"""M4 步 3: ``chapter continue`` — W2 短环核心编排（tech-m4 §5 步 3）。

B1 目标章判定 / B4 逐章停闸 / B5 准备阶段 settlement / B6 衔接段注入 /
B7 ``--variants`` 转调 / B9 run 壳 / B11 exit 语义 / B12 ``--require-plan``。

边界（任务文档「明确不做」）：不 auto-pick / auto-accept / 自动重生成；不内嵌
第二套生成逻辑；RAG 索引 / lifecycle 清理 / SettingEvaporator 不进 settlement
序列；``plan_*`` approved 集全程不变（settlement 只产 pending 提案，M2 语义）。
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from typing import Any

import structlog
from structlog.contextvars import bound_contextvars

from songyan.agents.settlement_extractor import apply_settlement, extract_settlement
from songyan.agents.summary_writer import write_chapter_summary_with_fact_check
from songyan.agents.writer import write_chapter
from songyan.db.chapter_variant_repo import ChapterVariantRepository
from songyan.db.connection import get_db
from songyan.db.context_repo import SummaryRepository
from songyan.db.llm_call_usage_repo import LlmCallUsageRepository
from songyan.db.plan_fact_repo import PlanFactRepository
from songyan.db.project_run_repo import ProjectRunRepository
from songyan.db.repository import (
    ChapterGoalRepository,
    ChapterHeadRepository,
    ChapterVersionRepository,
    ProjectRepository,
)
from songyan.db.review_repo import CreativeBriefRepository
from songyan.exceptions import (
    LLMBudgetExceededError,
    LLMError,
    LLMResponseParseError,
    SongyanError,
)
from songyan.models.chapter import ChapterGoal, ChapterHead
from songyan.models.project import ProjectSetting
from songyan.models.project_run import ProjectRunState
from songyan.models.variant import ChapterVariant
from songyan.plan_checks.bible import select_chapter_plan_bible_cards
from songyan.services.chapter_progress import load_chapter_progress
from songyan.services.variant_generate import VariantGenerateLLMError, generate_chapter_variants
from songyan.workflows._helpers import assemble_context_package, new_id
from songyan.workflows._nodes import _write_fallback_chapter_summary

logger = structlog.get_logger(__name__)

#: continue 衔接段（上一章 accepted 正文结尾节选）硬顶（tech-m4 B6）。
MAX_ENDING_CHARS = 800

#: run 壳可收养状态（现网值；completed/failed 不收养）。
_ADOPTABLE_STATUSES = ("running", "paused")


def _prior_unaccepted_picked(
    picked_slots: Sequence[ChapterVariant],
    *,
    accepted_chapters: AbstractSet[int],
    target: int,
) -> ChapterVariant | None:
    """B1 前置①（章级）：目标章之前**未 accepted**且残留 picked 槽的章。

    tech-m4 B1：picked 稿进入可续写态的唯一路径 = ``chapter accept``；accept 完成后
    该章即续写就绪，M3 pick 留下的 picked 槽（pick 只改 head 工作指针）不再阻塞。
    B1 口径下章号 < target 必已 accepted，本守卫仅防御未来章宇宙口径变化
    （task 244 / 冒烟发现 5）。
    """
    return next(
        (
            row
            for row in picked_slots
            if row.chapter_number < target
            and row.chapter_number not in accepted_chapters
        ),
        None,
    )


class ContinueGateError(SongyanError):
    """B1 两前置 / ``--require-plan`` 拒绝（exit 2）。"""

    exit_code = 2


class ContinueSettlementError(SongyanError):
    """准备阶段 settlement 失败（exit 1，run 壳已写 pause_reason）。"""

    exit_code = 1


class ContinueLLMError(SongyanError):
    """生成阶段 LLM 失败（exit 1，run 壳已写 pause_reason）。"""

    exit_code = 1


class ContinueBudgetExceeded(SongyanError):  # noqa: N818
    """预算熔断（exit 3，已写保留，沿用 variant 语义）。"""

    exit_code = 3


@dataclass(frozen=True)
class ContinueOutcome:
    """``continue_chapters`` 结果（单章；停闸结构决定单次最多一章）。"""

    chapter_number: int
    version_id: str | None
    word_count: int
    cost_cny: float
    next_hint: str
    settled_previous: bool
    generated_variants: int


async def _resolve_explicit_target(
    project_id: str,
    chapter: int,
    progress: Any,
) -> int:
    """task 263 / 形态 A：显式目标章解析（开章语义）。

    - N 不在章宇宙 → 章号跳跃校验（1..N-1 全部已 accepted，防 settlement
      上一章断档）后内联铺 empty head（产品原生 seeding）。
    - N 已 accepted → 拒绝。
    - 返回目标章号（已存在 empty head 时原样返回）。
    """
    universe = {entry.chapter_number for entry in progress.chapters}
    if chapter in universe:
        heads = await ChapterHeadRepository().list_by_project(project_id)
        by_ch = {h.chapter_number: h for h in heads}
        head = by_ch.get(chapter)
        if head is not None and head.accepted_version_id is not None:
            raise ContinueGateError(
                f"章 {chapter} 已 accepted；无需 continue（重复生成不产生新版本）"
            )
        return chapter
    accepted = {
        h.chapter_number
        for h in await ChapterHeadRepository().list_by_project(project_id)
        if h.accepted_version_id is not None
    }
    holes = [c for c in range(1, chapter) if c not in accepted]
    if holes:
        raise ContinueGateError(
            f"章 {chapter} 之前还有未写的章（{holes[0]} 等）；"
            f"请先逐章 continue 到章 {chapter - 1} 并 accept，再开章 {chapter}"
        )
    await ChapterHeadRepository().update(
        ChapterHead(
            project_id=project_id,
            chapter_number=chapter,
            current_version_id=None,
            accepted_version_id=None,
            status="draft",
        )
    )
    return chapter


async def continue_chapters(
    project_id: str,
    *,
    count: int = 1,
    variants: int | None = None,
    require_plan: bool = False,
    chapter: int | None = None,
    notice: Callable[[str], None] | None = None,
) -> ContinueOutcome | None:
    """推进一章：准备（settlement）→ 组装 → 生成（草稿或抽卡转调）。

    - ``count`` 仅校验 1..3；停闸结构决定单次 invocation 最多生成一章（B4）。
    - ``variants`` 非 None → 函数级转调 ``generate_chapter_variants``（B7）。
    - ``chapter`` 显式目标章（task 263 / 形态 A）：省略 = 自动 targeting（B1）
      零变化；传入 = 开章语义——N 不在章宇宙则内联铺 empty head（产品原生
      seeding，替代 runbook SQL）；N-1 之前有未写章（settlement 上一章会
      断档）→ ``ContinueGateError``；N 已 accepted → ``ContinueGateError``。
    - 返回 ``None`` = 空项目 / 全 accepted（CLI exit 0 提示）。
    - LLM 失败 / settlement 失败 → run 壳 ``paused`` + ``pause_reason`` 后抛
      ``ContinueLLMError`` / ``ContinueSettlementError``（exit 1）；预算熔断 →
      ``ContinueBudgetExceeded``（exit 3）。
    """
    if count < 1 or count > 3:
        raise ValueError(f"--count 必须在 1..3 之间（收到 {count}）")
    if variants is not None and variants < 1:
        raise ValueError(f"--variants 必须 >= 1（收到 {variants}）")
    if chapter is not None and chapter < 1:
        raise ValueError(f"--chapter 必须 >= 1（收到 {chapter}）")

    project = await ProjectRepository().get(project_id)
    if project is None:
        raise ValueError(f"项目不存在: {project_id}")

    progress = await load_chapter_progress(project_id)
    if chapter is not None:
        target = await _resolve_explicit_target(project_id, chapter, progress)
    else:
        target = progress.next_chapter
    if target is None:
        return None

    picked_slots = [
        row
        for row in await ChapterVariantRepository().list_by_project(project_id)
        if row.status == "picked"
    ]
    # B1 前置①（章级）：目标章之前存在**未 accepted**且 picked 的章 → 拒绝。
    # accepted 章的残留 picked 槽（M3 pick 不改 variant 行）不阻塞——B1：picked 稿
    # 进入可续写态唯一路径 = chapter accept（task 244 / 冒烟发现 5）。
    heads = await ChapterHeadRepository().list_by_project(project_id)
    accepted_chapters = {
        h.chapter_number for h in heads if h.accepted_version_id is not None
    }
    prior_picked = _prior_unaccepted_picked(
        picked_slots, accepted_chapters=accepted_chapters, target=target
    )
    if prior_picked is not None:
        raise ContinueGateError(
            f"章 {target} 之前存在 picked 未 accept 的章"
            f"（chapter {prior_picked.chapter_number} slot {prior_picked.slot_index}）；"
            f"请先 chapter accept 或 variant pick|abandon 后再 continue"
        )
    # B1 前置②：目标章已有未确认工作稿（draft / picked）；无自动重生成旗标。
    head = await ChapterHeadRepository().get(project_id, target)
    if head is not None and head.accepted_version_id is None:
        if head.current_version_id is not None:
            raise ContinueGateError(
                f"章 {target} 已有未确认工作稿；请先 chapter accept 或 "
                f"variant pick|abandon 后再 continue（无自动重生成）"
            )
    if any(v.chapter_number == target for v in picked_slots):
        raise ContinueGateError(
            f"章 {target} 已有 picked 未 accept 的工作稿；"
            f"请先 chapter accept 或 variant pick|abandon 后再 continue"
        )

    # B12：--require-plan（判定 = 五类 approved 卡全空或缺 chapter_goal）。
    plan_missing = await _plan_missing(project_id, target)
    if plan_missing and require_plan:
        raise ContinueGateError(
            f"--require-plan：本章计划缺失：{'；'.join(plan_missing)}"
        )

    # B9：run 壳（单章壳；收养 running/paused 且章号匹配；engine 多章壳不收养）。
    run_repo = ProjectRunRepository()
    run_state = await _find_adoptable_run(run_repo, project_id, target)
    resumed = run_state is not None
    if run_state is None:
        run_state = ProjectRunState(
            run_id=new_id("run"),
            project_id=project_id,
            chapter_range_start=target,
            chapter_range_end=target,
            current_chapter=target,
            status="running",
        )
        await run_repo.create(run_state)

    with bound_contextvars(
        project_id=project_id,
        chapter_number=target,
        run_id=run_state.run_id,
        agent="chapter.continue",
    ):
        try:
            settled = await _settle_previous_if_needed(
                project_id, target, project, notice=notice
            )
            if plan_missing and notice is not None:
                notice(f"警告：本章计划缺失：{'；'.join(plan_missing)}（--require-plan 可拒绝）")
            outcome = await _generate_one(
                project_id,
                target,
                project,
                variants=variants,
                settled_previous=settled,
                run_id=run_state.run_id,
            )
        except LLMBudgetExceededError as exc:
            await _pause_run(run_repo, run_state, resumed, f"cost_budget: {exc}")
            raise ContinueBudgetExceeded(str(exc)) from exc
        except ContinueSettlementError as exc:
            await _pause_run(run_repo, run_state, resumed, f"settlement_error: {exc}")
            raise
        except (LLMError, LLMResponseParseError, VariantGenerateLLMError) as exc:
            await _pause_run(run_repo, run_state, resumed, f"llm_error: {exc}")
            raise ContinueLLMError(f"章 {target} 生成失败: {exc}") from exc

    # 成功：刷新 run 成本并完成本章壳（completed 壳不再被收养）。
    run_state.status = "completed"
    run_state.pause_reason = None
    await _refresh_run_cost(run_state)
    await run_repo.update(run_state)
    logger.info(
        "chapter.continue.done",
        project_id=project_id,
        chapter_number=target,
        version_id=outcome.version_id,
        generated_variants=outcome.generated_variants,
        settled_previous=outcome.settled_previous,
        cost_cny=outcome.cost_cny,
    )
    return outcome


async def _generate_one(
    project_id: str,
    target: int,
    project: ProjectSetting,
    *,
    variants: int | None,
    settled_previous: bool,
    run_id: str,
) -> ContinueOutcome:
    """单章生成：抽卡转调（B7）或组装 + write_chapter（B6）。"""
    if variants is not None:
        result = await generate_chapter_variants(project_id, target, n=variants)
        cost = await _run_cost_or_zero(run_id)
        return ContinueOutcome(
            chapter_number=target,
            version_id=None,
            word_count=0,
            cost_cny=cost,
            next_hint=f"先 variant pick --chapter {target}（或 variant abandon）后再 continue",
            settled_previous=settled_previous,
            generated_variants=len(result.variants),
        )

    # chapter_goal 回退（B12 默认模式可继续）：无行 → words_per_chapter 兜底。
    goal = await ChapterGoalRepository().get_by_chapter(project_id, target)
    if goal is None:
        goal = ChapterGoal(
            chapter_number=target,
            word_count_target=project.words_per_chapter,
        )
    goal = goal.model_copy(
        update={"previous_summary": await _previous_summary_120(project_id, target)}
    )
    brief = await CreativeBriefRepository().get_by_chapter(project_id, target)
    ending = await _last_chapter_ending(project_id, target)
    package = await assemble_context_package(
        project_id,
        target,
        goal,
        brief,
        last_chapter_ending=ending,
    )
    version = await write_chapter(
        ChapterVersionRepository(),
        ChapterHeadRepository(),
        project_id,
        package,
    )
    cost = await _run_cost_or_zero(run_id)
    return ContinueOutcome(
        chapter_number=target,
        version_id=version.version_id,
        word_count=version.word_count,
        cost_cny=cost,
        next_hint=f"先 chapter accept --chapter {target} 后再 continue",
        settled_previous=settled_previous,
        generated_variants=0,
    )


async def _settle_previous_if_needed(
    project_id: str,
    target: int,
    project: ProjectSetting,
    *,
    notice: Callable[[str], None] | None,
) -> bool:
    """B5 准备阶段：紧邻上一章 accepted 且未 settlement → 重跑完整序列。

    复合判定（评审 M2）：``summaries`` 无该章记录 **且** 结算观测层
    （``character_states.source_version_id = accepted_version_id``）无行，
    两条件皆无才重跑。首章（无上一章）跳过。
    """
    if target <= 1:
        return False
    head_repo = ChapterHeadRepository()
    head = await head_repo.get(project_id, target - 1)
    if head is None or head.accepted_version_id is None:
        return False
    version_repo = ChapterVersionRepository()
    version = await version_repo.get(head.accepted_version_id)
    if version is None:
        return False

    async with get_db() as conn:
        cursor = await conn.execute(
            "SELECT 1 FROM summaries WHERE project_id = ? AND chapter_number = ? LIMIT 1",
            (project_id, target - 1),
        )
        has_summary = await cursor.fetchone() is not None
        cursor = await conn.execute(
            "SELECT 1 FROM character_states WHERE source_version_id = ? LIMIT 1",
            (head.accepted_version_id,),
        )
        has_settlement_row = await cursor.fetchone() is not None
    if has_summary or has_settlement_row:
        return False

    if notice is not None:
        notice(
            f"章 {target - 1} 已 accepted 但未 settlement；"
            f"补跑 settlement 序列（extract + apply + 摘要）"
        )
    logger.info(
        "chapter.continue.settlement_rerun",
        project_id=project_id,
        chapter_number=target - 1,
        accepted_version_id=head.accepted_version_id,
    )

    try:
        settlement = await extract_settlement(
            content=version.content,
            project_id=project_id,
            chapter_number=target - 1,
            version_id=version.version_id,
        )
    except (LLMError, LLMResponseParseError) as exc:
        raise ContinueSettlementError(
            f"章 {target - 1} settlement 提取失败: {exc}"
        ) from exc
    if settlement.validation_status != "valid":
        logger.warning(
            "chapter.continue.settlement_invalid_skip",
            project_id=project_id,
            chapter_number=target - 1,
            validation_status=settlement.validation_status,
            validation_errors=settlement.validation_errors,
        )
        return False

    async with get_db() as conn:
        try:
            await apply_settlement(
                settlement,
                project_id,
                target - 1,
                version.version_id,
                conn,
            )
            await conn.commit()
        except Exception as exc:
            await conn.rollback()
            raise ContinueSettlementError(
                f"章 {target - 1} settlement 应用失败: {exc}"
            ) from exc

    try:
        await write_chapter_summary_with_fact_check(
            content=version.content,
            settlement=settlement,
            project_id=project_id,
            chapter_number=target - 1,
            db=SummaryRepository(),
            protagonist_name=project.protagonist_name,
        )
    except (LLMError, LLMResponseParseError) as exc:
        logger.warning(
            "chapter.continue.summary_failed_fallback",
            project_id=project_id,
            chapter_number=target - 1,
            error=str(exc),
        )
        await _write_fallback_chapter_summary(
            content=version.content,
            settlement=settlement,
            project_id=project_id,
            chapter_number=target - 1,
            db=SummaryRepository(),
        )
    return True


async def _plan_missing(project_id: str, chapter: int) -> list[str]:
    """B12 判定：五类 approved 圣经卡全空（非 text==""）或缺 chapter_goal。"""
    repo = PlanFactRepository()
    cards = select_chapter_plan_bible_cards(
        project_id=project_id,
        chapter=chapter,
        entities=await repo.list_canon_entities(project_id),
        attributes=await repo.list_canon_attributes(project_id),
        events=await repo.list_canon_events(project_id),
        clues=await repo.list_canon_clues(project_id),
        time_anchors=await repo.list_canon_time_anchors(project_id),
    )
    missing: list[str] = []
    if not (
        cards.entities
        or cards.attributes
        or cards.events
        or cards.clues
        or cards.time_anchors
    ):
        missing.append("approved 圣经五类卡全空")
    if await ChapterGoalRepository().get_by_chapter(project_id, chapter) is None:
        missing.append("缺 chapter_goal")
    return missing


async def _last_chapter_ending(project_id: str, target: int) -> str:
    """B6 衔接段：上一章 accepted 正文结尾 ≤800 字；无上一章 → 空串。"""
    if target <= 1:
        return ""
    head = await ChapterHeadRepository().get(project_id, target - 1)
    if head is None or head.accepted_version_id is None:
        return ""
    version = await ChapterVersionRepository().get(head.accepted_version_id)
    if version is None:
        return ""
    content = version.content or ""
    if len(content) > MAX_ENDING_CHARS:
        return content[-MAX_ENDING_CHARS:]
    return content


async def _previous_summary_120(project_id: str, chapter: int) -> str:
    """既有 recent_plot 注入路径同款读取（``_get_previous_summary`` 口径不变）。

    取上一章最新 ``plot_summary``，120 字截断 + 省略号。
    """
    if chapter <= 1:
        return ""
    async with get_db() as conn:
        cursor = await conn.execute(
            """SELECT plot_summary FROM summaries
            WHERE project_id = ? AND chapter_number = ?
            ORDER BY created_at DESC LIMIT 1""",
            (project_id, chapter - 1),
        )
        row = await cursor.fetchone()
    text = row[0] if row else ""
    text = text or ""
    if len(text) > 120:
        text = text[:120] + "..."
    return text


async def _find_adoptable_run(
    run_repo: ProjectRunRepository,
    project_id: str,
    target: int,
) -> ProjectRunState | None:
    """B9 收养：单章壳（start == end == target）且 status ∈ running/paused。

    ``list_by_project`` 按 created_at DESC——收养最近一个可续跑壳。
    engine 多章 run 壳不匹配 → 不收养（调用方新建）。
    """
    for run in await run_repo.list_by_project(project_id):
        if (
            run.status in _ADOPTABLE_STATUSES
            and run.chapter_range_start == run.chapter_range_end == target
        ):
            return run
    return None


async def _pause_run(
    run_repo: ProjectRunRepository,
    run_state: ProjectRunState,
    resumed: bool,
    pause_reason: str,
) -> None:
    """失败/熔断：status=paused + pause_reason（现网值，非 pause）；保留已写。"""
    run_state.status = "paused"
    run_state.pause_reason = pause_reason
    await _refresh_run_cost(run_state)
    await run_repo.update(run_state)
    logger.warning(
        "chapter.continue.paused",
        run_id=run_state.run_id,
        project_id=run_state.project_id,
        chapter_number=run_state.current_chapter,
        resumed=resumed,
        pause_reason=pause_reason,
    )


async def _refresh_run_cost(run_state: ProjectRunState) -> None:
    try:
        run_state.total_cost = await LlmCallUsageRepository().sum_cost_for_run(
            run_state.run_id
        )
    except Exception as exc:  # 成本合计失败不阻断（同 phase2_graph 哲学）
        logger.warning(
            "chapter.continue.total_cost_refresh_failed",
            run_id=run_state.run_id,
            error=str(exc),
        )


async def _run_cost_or_zero(run_id: str) -> float:
    try:
        return await LlmCallUsageRepository().sum_cost_for_run(run_id)
    except Exception as exc:  # 遥测表缺失等：费用可见降级为 0，不阻断
        logger.warning(
            "chapter.continue.run_cost_read_failed", run_id=run_id, error=str(exc)
        )
        return 0.0
