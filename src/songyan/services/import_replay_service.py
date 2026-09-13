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

from songyan.agents.settlement_extractor import apply_settlement, extract_settlement
from songyan.agents.summary_writer import write_chapter_summary_with_fact_check
from songyan.db.connection import get_db
from songyan.db.context_repo import SummaryRepository
from songyan.db.genre_runtime_profile_repo import load_profile
from songyan.db.import_replay_repo import ImportReplayRepository
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
from songyan.models import ChapterHead, ChapterVersion, StateSettlement
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
# Task 3: 回放循环核心
# ---------------------------------------------------------------------------


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
    resolved_run_id = run_id or f"run-{uuid.uuid4().hex[:8]}"

    repo = ImportReplayRepository()
    report = ReplayReport(run_id=resolved_run_id, project_id=project_id)
    for boundary in manifest.boundaries:
        if chapters and boundary.chapter_number not in chapters:
            continue
        existing = await repo.get_mark(project_id, boundary.chapter_number)
        if existing is not None and existing.source_fingerprint == manifest.source_sha256:
            report.outcomes.append(
                ChapterReplayOutcome(
                    chapter_number=boundary.chapter_number,
                    title=boundary.title,
                    status="skipped",
                    accepted_version_id=existing.accepted_version_id,
                    over_token_budget=boundary.over_token_budget,
                )
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
    logger.info(
        "import_replay.completed",
        project_id=project_id,
        run_id=resolved_run_id,
        applied=len(report.by_status("applied")),
        skipped=len(report.by_status("skipped")),
        failed=len(report.by_status("failed")),
    )
    return report


async def _replay_one(
    project_id: str,
    run_id: str,
    manifest: SegmentManifest,
    boundary: ChapterBoundary,
    normalized: str,
) -> ChapterReplayOutcome:
    """单章回放：draft → extract → 原子回放事务 → summary（失败不阻断）."""
    title, body = slice_chapter_body(normalized, boundary)
    draft_version_id = await get_or_create_import_draft(
        project_id,
        boundary,
        body,
        source_fingerprint=manifest.source_sha256,
        confirmed_at=manifest.confirmed_at.isoformat() if manifest.confirmed_at else None,
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
    summary_id, missing_facts_count = await _write_replay_summary(
        body=body,
        settlement=settlement,
        project_id=project_id,
        chapter_number=boundary.chapter_number,
    )
    if summary_id is not None:
        await _update_mark_summary_id(project_id, boundary.chapter_number, summary_id)
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
    )


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
