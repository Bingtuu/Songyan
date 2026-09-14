"""V15 Task 236: 逐章 settlement 回放（replay 阶段）.

对已确认切分清单逐章执行 SettlementExtractor（只提取不生成），
原子写入事实库；幂等标记保证断点续跑零重复 LLM 调用。
设计冻结见 tasks/236-v15-import-replay.md 与 docs/reports/234-v15-import-pipeline-audit.md。
"""

from __future__ import annotations

import uuid
from pathlib import Path
from sqlite3 import Row

import structlog
from structlog.contextvars import bind_contextvars, reset_contextvars

from songyan.agents.settlement_extractor import apply_settlement, extract_settlement
from songyan.agents.summary_writer import write_chapter_summary_with_fact_check
from songyan.db.connection import get_db
from songyan.db.context_repo import SummaryRepository
from songyan.db.genre_runtime_profile_repo import load_profile
from songyan.db.import_replay_repo import ImportReplayRepository
from songyan.db.llm_call_usage_repo import LlmCallUsageRepository
from songyan.db.project_run_repo import ProjectRunRepository
from songyan.db.repository import (
    ChapterHeadRepository,
    ChapterVersionRepository,
    CharacterRepository,
    ProjectRepository,
)
from songyan.exceptions import (
    ImportReplayError,
    LLMError,
    LLMResponseParseError,
    SettlementError,
)
from songyan.models import (
    ChapterHead,
    ChapterVersion,
    NumericalUpdate,
    ProjectRunState,
    StateSettlement,
)
from songyan.models.import_manifest import ChapterBoundary, SegmentManifest
from songyan.models.import_replay import (
    ChapterReplayOutcome,
    ReplayMark,
    ReplayReport,
)
from songyan.services.import_segment_service import (
    assert_replay_allowed,
    slice_chapter_body,
)
from songyan.utils.word_count import count_chinese_words

logger = structlog.get_logger(__name__)


async def preflight_replay(project_id: str, manifest: SegmentManifest) -> None:
    """回放前置检查：项目存在 + 主角档案已建档（F1 拦截）.

    主角档案必须在 extract 之前落库，否则 settlement 的 character_updates
    会因 character_id 不在 valid_char_ids 而被静默 skip。
    缺失时抛 ImportReplayError，消息含可操作建议。
    """
    project = await ProjectRepository().get(project_id)
    if project is None:
        msg = (
            f"回放被拒绝：项目不存在（project_id={project_id}）。"
            "请先创建项目（songyan create-project）再回放。"
        )
        raise ImportReplayError(msg)
    characters = await CharacterRepository().list_by_project(project_id)
    if not any(c.role_type == "protagonist" for c in characters):
        msg = (
            f"回放被拒绝：项目 {project_id} 缺少主角档案（role_type='protagonist'）。"
            "请先在 characters 表建立主角档案再回放，"
            "否则 settlement 的角色更新会被静默跳过。"
        )
        raise ImportReplayError(msg)
    logger.info(
        "import_replay.preflight_passed",
        project_id=project_id,
        chapter_count=manifest.chapter_count,
    )


async def get_or_create_import_draft(
    project_id: str,
    boundary: ChapterBoundary,
    body: str,
    *,
    source_fingerprint: str,
    confirmed_at: str | None,
) -> str:
    """返回 version_id。同章同指纹 import draft 已存在 → 复用；
    否则 version_number=max+1 新建（version_type='draft'，
    generation_metadata 含 import 标记）并独立提交.

    独立提交是回放事务的前置：accept_version 内部另开连接读 draft，
    draft 必须先持久化可见。
    """
    async with get_db() as conn:
        conn.row_factory = Row
        cursor = await conn.execute(
            """SELECT version_id FROM chapter_versions
               WHERE project_id = ? AND chapter_number = ? AND version_type = 'draft'
                 AND json_extract(generation_metadata, '$.import.source_fingerprint') = ?
               ORDER BY version_number""",
            (project_id, boundary.chapter_number, source_fingerprint),
        )
        row = await cursor.fetchone()
    if row is not None:
        logger.info(
            "import_replay.draft_reused",
            project_id=project_id,
            chapter_number=boundary.chapter_number,
            version_id=row["version_id"],
        )
        return str(row["version_id"])

    repo = ChapterVersionRepository()
    version = ChapterVersion(
        version_id=f"v-{uuid.uuid4().hex[:8]}",
        project_id=project_id,
        chapter_number=boundary.chapter_number,
        version_number=await repo.get_next_version_number(
            project_id, boundary.chapter_number
        ),
        version_type="draft",
        content=body,
        word_count=count_chinese_words(body),
        generation_metadata={
            "import": {
                "source_fingerprint": source_fingerprint,
                "segment_chapter": boundary.chapter_number,
                "chapter_title": boundary.title,
                "confirmed_at": confirmed_at,
            }
        },
    )
    await repo.create(version)
    logger.info(
        "import_replay.draft_created",
        project_id=project_id,
        chapter_number=boundary.chapter_number,
        version_id=version.version_id,
        version_number=version.version_number,
    )
    return version.version_id


# ---------------------------------------------------------------------------
# Task 3/4: 回放循环核心 + run 壳（project_runs）+ contextvars 遥测归因
# ---------------------------------------------------------------------------


async def _get_or_create_run(
    project_id: str, manifest: SegmentManifest, run_id: str | None
) -> ProjectRunState:
    """建/复用 run 壳（project_runs 记录，惯例同 phase2_graph 的 _save_run_state）.

    调用方传入 run_id：已存在则复用（跨项目复用拒绝），不存在则以该 id 新建；
    未传入则按 run-<uuid8> 新建。chapter_range 取清单全量范围（与 chapters
    过滤无关）。返回的 run 壳已持久化、状态 running。
    """
    repo = ProjectRunRepository()
    if run_id is not None:
        existing = await repo.get(run_id)
        if existing is not None:
            if existing.project_id != project_id:
                msg = (
                    f"回放被拒绝：run_id {run_id} 属于项目 "
                    f"{existing.project_id}，不能复用于项目 {project_id}。"
                )
                raise ImportReplayError(msg)
            existing.status = "running"
            existing.pause_reason = None
            await repo.update(existing)
            return existing
    chapter_numbers = [b.chapter_number for b in manifest.boundaries]
    run_state = ProjectRunState(
        run_id=run_id or f"run-{uuid.uuid4().hex[:8]}",
        project_id=project_id,
        chapter_range_start=min(chapter_numbers),
        chapter_range_end=max(chapter_numbers),
        current_chapter=min(chapter_numbers),
        status="running",
    )
    await repo.create(run_state)
    return run_state


async def _persist_replay_progress(
    run_state: ProjectRunState, chapter_number: int, status: str
) -> None:
    """每章（含幂等跳过）后更新 run 壳进度并落盘.

    completed 含 applied + skipped（skipped 章的事实已在库中，等价于完成）；
    复用 run 时与既有清单按章号 reconcile，失败章重跑成功后自动移出失败清单。
    """
    run_state.current_chapter = chapter_number
    completed = [c for c in run_state.completed_chapters if c != chapter_number]
    failed = [c for c in run_state.failed_chapters if c != chapter_number]
    if status == "failed":
        failed.append(chapter_number)
    else:
        completed.append(chapter_number)
    run_state.completed_chapters = sorted(completed)
    run_state.failed_chapters = sorted(failed)
    await ProjectRunRepository().update(run_state)


async def _refresh_run_total_cost(run_state: ProjectRunState) -> None:
    """从 llm_call_usage 合计刷新 run_state.total_cost（Task 175 口径）；
    读取失败保留既有值，不阻断回放."""
    try:
        total = await LlmCallUsageRepository().sum_cost_for_run(run_state.run_id)
    except Exception as exc:  # 成本合计失败不应阻断回放
        logger.warning(
            "import_replay.total_cost_refresh_failed",
            run_id=run_state.run_id,
            error=str(exc),
        )
        return
    run_state.total_cost = total


async def _finalize_run(run_state: ProjectRunState) -> None:
    """写 run 壳终态：completed（无失败）/ partial（有失败但有完成）/ failed（全灭）.

    状态公式与 phase2_graph 收尾一致；落盘前刷新 total_cost，
    保证 project_runs.total_cost 与 llm_call_usage 合计一致。
    """
    if run_state.failed_chapters:
        run_state.status = "partial" if run_state.completed_chapters else "failed"
    else:
        run_state.status = "completed"
    await _refresh_run_total_cost(run_state)
    await ProjectRunRepository().update(run_state)
    logger.info(
        "import_replay.run_finalized",
        run_id=run_state.run_id,
        status=run_state.status,
        completed=len(run_state.completed_chapters),
        failed=len(run_state.failed_chapters),
        total_cost=run_state.total_cost,
    )


async def _fail_run(run_state: ProjectRunState) -> None:
    """未预期异常中断兜底：尽力落 failed 终态；持久化失败只告警，不掩盖原异常."""
    run_state.status = "failed"
    try:
        await _refresh_run_total_cost(run_state)
        await ProjectRunRepository().update(run_state)
    except Exception as exc:
        logger.warning(
            "import_replay.run_fail_persist_failed",
            run_id=run_state.run_id,
            error=str(exc),
        )


async def replay_import(
    project_id: str,
    manifest_path: Path,
    *,
    chapters: set[int] | None = None,
    run_id: str | None = None,
) -> ReplayReport:
    """对已确认切分清单逐章回放 settlement。断点续跑：已应用章零 LLM 调用跳过."""
    manifest = assert_replay_allowed(manifest_path)
    normalized = (manifest_path.parent / "source.normalized.txt").read_text(
        encoding="utf-8"
    )
    await preflight_replay(project_id, manifest)
    run_state = await _get_or_create_run(project_id, manifest, run_id)
    resolved_run_id = run_state.run_id

    repo = ImportReplayRepository()
    report = ReplayReport(run_id=resolved_run_id, project_id=project_id)
    try:
        for boundary in manifest.boundaries:
            if chapters and boundary.chapter_number not in chapters:
                continue
            existing = await repo.get_mark(project_id, boundary.chapter_number)
            if (
                existing is not None
                and existing.source_fingerprint == manifest.source_sha256
            ):
                report.outcomes.append(
                    ChapterReplayOutcome(
                        chapter_number=boundary.chapter_number,
                        title=boundary.title,
                        status="skipped",
                        accepted_version_id=existing.accepted_version_id,
                        over_token_budget=boundary.over_token_budget,
                    )
                )
                await _persist_replay_progress(
                    run_state, boundary.chapter_number, "skipped"
                )
                continue
            if existing is not None:
                msg = (
                    f"回放被拒绝：第 {boundary.chapter_number} 章已应用过，"
                    "但源文件指纹已变化。请重新 segment 并确认后再回放。"
                )
                raise ImportReplayError(msg)
            try:
                outcome = await _replay_one(
                    project_id, resolved_run_id, manifest, boundary, normalized
                )
            except (LLMError, SettlementError, ImportReplayError) as exc:
                logger.warning(
                    "import_replay.chapter_failed",
                    project_id=project_id,
                    chapter_number=boundary.chapter_number,
                    error=str(exc),
                )
                outcome = ChapterReplayOutcome(
                    chapter_number=boundary.chapter_number,
                    title=boundary.title,
                    status="failed",
                    over_token_budget=boundary.over_token_budget,
                    error=str(exc),
                )
            report.outcomes.append(outcome)
            await _persist_replay_progress(
                run_state, boundary.chapter_number, outcome.status
            )
    except Exception:
        # 未预期异常（如 sqlite3.Error）或指纹拒绝：落 failed 终态后 re-raise
        await _fail_run(run_state)
        raise
    await _finalize_run(run_state)
    logger.info(
        "import_replay.completed",
        project_id=project_id,
        run_id=resolved_run_id,
        applied=len(report.by_status("applied")),
        skipped=len(report.by_status("skipped")),
        failed=len(report.by_status("failed")),
    )
    return report


async def _count_opening_closing_mismatches(
    *,
    project_id: str,
    chapter_number: int,
    numerical_updates: list[NumericalUpdate],
) -> int:
    """F6 跨章 diff 观察项：本章 opening_value 对前章最新 closing_value.

    在回放事务提交后执行（只读 SELECT），比较失败只告警、不影响已提交章。
    不复用 ``NumericalLedgerRepository.get_latest``——它不按 project_id 过滤；
    此处用参数化 SQL 按 (project_id, character_id, attribute_name) 取
    chapter_number < 本章的最新台账行。首章或该键无前章行 → 不计。
    """
    if not numerical_updates:
        return 0
    mismatches = 0
    try:
        async with get_db() as conn:
            for num in numerical_updates:
                cursor = await conn.execute(
                    """SELECT closing_value FROM numerical_ledgers
                       WHERE project_id = ? AND character_id = ?
                         AND attribute_name = ? AND chapter_number < ?
                       ORDER BY chapter_number DESC, created_at DESC
                       LIMIT 1""",
                    (
                        project_id,
                        num.character_id,
                        num.attribute_name,
                        chapter_number,
                    ),
                )
                row = await cursor.fetchone()
                if row is None:
                    continue
                previous_closing = float(row[0])
                if previous_closing != float(num.opening_value):
                    mismatches += 1
                    logger.info(
                        "import_replay.opening_closing_mismatch",
                        project_id=project_id,
                        chapter_number=chapter_number,
                        character_id=num.character_id,
                        attribute_name=num.attribute_name,
                        opening_value=num.opening_value,
                        previous_closing_value=previous_closing,
                    )
    except Exception as exc:  # 观察项失败不应影响已提交章
        logger.warning(
            "import_replay.opening_closing_diff_failed",
            project_id=project_id,
            chapter_number=chapter_number,
            error=str(exc),
        )
        return 0
    return mismatches


async def _replay_one(
    project_id: str,
    run_id: str,
    manifest: SegmentManifest,
    boundary: ChapterBoundary,
    normalized: str,
) -> ChapterReplayOutcome:
    """单章回放：draft → extract → 原子回放事务 → summary（失败不阻断）.

    进入时按章绑定 structlog contextvars（run_id/project_id/chapter_number），
    保证章内 LLM 调用写入 llm_call_usage 时正确归因；章末 reset token
    恢复原上下文，避免泄漏到下一章或调用方。
    """
    context_tokens = bind_contextvars(
        run_id=run_id,
        project_id=project_id,
        chapter_number=boundary.chapter_number,
    )
    try:
        title, body = slice_chapter_body(normalized, boundary)
        draft_version_id = await get_or_create_import_draft(
            project_id,
            boundary,
            body,
            source_fingerprint=manifest.source_sha256,
            confirmed_at=(
                manifest.confirmed_at.isoformat() if manifest.confirmed_at else None
            ),
        )
        settlement = await extract_settlement(
            body,
            project_id,
            boundary.chapter_number,
            draft_version_id,
            genre_rules=None,
        )
        if settlement.validation_status != "valid":
            details = "；".join(settlement.validation_errors) or "（无详细错误）"
            msg = (
                f"第 {boundary.chapter_number} 章 settlement 校验未通过 "
                f"(validation_status={settlement.validation_status}): {details}"
            )
            raise SettlementError(msg)
        accepted_version_id = await _accept_with_replay_mark(
            project_id=project_id,
            chapter_number=boundary.chapter_number,
            draft_version_id=draft_version_id,
            settlement=settlement,
            body=body,
            run_id=run_id,
            source_fingerprint=manifest.source_sha256,
        )
        # Task 238 F6：回放事务提交后做跨章 opening/closing 只读比对（观察项）
        opening_closing_mismatch = await _count_opening_closing_mismatches(
            project_id=project_id,
            chapter_number=boundary.chapter_number,
            numerical_updates=settlement.numerical_updates,
        )
        summary_id, missing_facts_count = await _write_replay_summary(
            body=body,
            settlement=settlement,
            project_id=project_id,
            chapter_number=boundary.chapter_number,
        )
        if summary_id is not None:
            await _update_mark_summary_id(
                project_id, boundary.chapter_number, summary_id
            )
        logger.info(
            "import_replay.chapter_applied",
            project_id=project_id,
            chapter_number=boundary.chapter_number,
            draft_version_id=draft_version_id,
            accepted_version_id=accepted_version_id,
        )
        return ChapterReplayOutcome(
            chapter_number=boundary.chapter_number,
            title=title,
            status="applied",
            accepted_version_id=accepted_version_id,
            summary_missing_facts=missing_facts_count,
            over_token_budget=boundary.over_token_budget,
            # Task 238: H 组观察计数从 settlement 拷贝（validate/apply 阶段填充），
            # observation_counts 为新增字段，不被既有 settlement 改写逻辑触碰。
            observation_counts=dict(settlement.observation_counts),
            opening_closing_mismatch=opening_closing_mismatch,
        )
    finally:
        reset_contextvars(**context_tokens)


async def _accept_with_replay_mark(
    *,
    project_id: str,
    chapter_number: int,
    draft_version_id: str,
    settlement: StateSettlement,
    body: str,
    run_id: str,
    source_fingerprint: str,
) -> str:
    """回放事务：apply_settlement + accept_version + chapter_heads + 幂等标记，
    单 conn 单 commit；异常 rollback 并 re-raise.

    镜像 workflows/_nodes.py 的 accept_with_settlement_boundary 事务序列，
    把幂等标记并入同一事务（crash 在边界提交后不会产生无标记的重复回放）。
    draft 必须先独立提交：accept_version 内部另开连接读 draft。
    """
    # 对齐 _nodes.py：按体裁解析伏笔 horizon 下限（load_profile 永不抛错，
    # 无匹配返回 scifi baseline → floor=0 → 旧行为不变）。
    horizon_floor = 0
    project = await ProjectRepository().get(project_id)
    if project is not None:
        runtime_profile = await load_profile(project.genre_id)
        horizon_floor = runtime_profile.foreshadowing_horizon_floor

    async with get_db() as conn:
        try:
            await apply_settlement(
                settlement=settlement,
                project_id=project_id,
                chapter_number=chapter_number,
                version_id=draft_version_id,
                conn=conn,
                content=body,
                foreshadowing_horizon_floor=horizon_floor,
            )
            accepted_version_id = await ChapterVersionRepository().accept_version(
                draft_version_id, conn=conn
            )
            await ChapterHeadRepository().update(
                ChapterHead(
                    project_id=project_id,
                    chapter_number=chapter_number,
                    current_version_id=accepted_version_id,
                    accepted_version_id=accepted_version_id,
                    status="accepted",
                ),
                conn=conn,
            )
            await ImportReplayRepository().insert_mark(
                ReplayMark(
                    project_id=project_id,
                    run_id=run_id,
                    chapter_number=chapter_number,
                    draft_version_id=draft_version_id,
                    accepted_version_id=accepted_version_id,
                    summary_id=None,
                    source_fingerprint=source_fingerprint,
                ),
                conn=conn,
            )
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise
    return accepted_version_id


async def _write_replay_summary(
    *,
    body: str,
    settlement: StateSettlement,
    project_id: str,
    chapter_number: int,
) -> tuple[str | None, int]:
    """SummaryWriter 一键入口；返回 (summary_id, missing_facts 计数).

    LLM/解析异常捕获后记 warning，不阻断 accept（对齐 _nodes.py 的
    摘要失败不阻塞语义）；失败时 summary_id 为 None。
    """
    try:
        summary_id, _summary, missing_facts = (
            await write_chapter_summary_with_fact_check(
                content=body,
                settlement=settlement,
                project_id=project_id,
                chapter_number=chapter_number,
                db=SummaryRepository(),
            )
        )
    except (LLMError, LLMResponseParseError) as exc:
        logger.warning(
            "import_replay.summary_failed",
            project_id=project_id,
            chapter_number=chapter_number,
            error=str(exc),
        )
        return None, 0
    return summary_id, len(missing_facts)


async def _update_mark_summary_id(
    project_id: str, chapter_number: int, summary_id: str
) -> None:
    """摘要成功后回填标记的 summary_id（元数据列，独立于回放事务）."""
    async with get_db() as conn:
        await conn.execute(
            "UPDATE import_replay_marks SET summary_id = ? "
            "WHERE project_id = ? AND chapter_number = ?",
            (summary_id, project_id, chapter_number),
        )
        await conn.commit()
