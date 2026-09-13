"""V15 Task 236: 逐章 settlement 回放（replay 阶段）.

对已确认切分清单逐章执行 SettlementExtractor（只提取不生成），
原子写入事实库；幂等标记保证断点续跑零重复 LLM 调用。
设计冻结见 tasks/236-v15-import-replay.md 与 docs/reports/234-v15-import-pipeline-audit.md。
"""

from __future__ import annotations

import uuid
from sqlite3 import Row

import structlog

from songyan.db.connection import get_db
from songyan.db.repository import (
    ChapterVersionRepository,
    CharacterRepository,
    ProjectRepository,
)
from songyan.exceptions import ImportReplayError
from songyan.models import ChapterVersion
from songyan.models.import_manifest import ChapterBoundary, SegmentManifest
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
