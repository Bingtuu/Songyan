"""M4 步 2: 章级人确认写径（tech-m4 §5 步 2 / B2/B3/B5，task 239）.

accepted 写径唯一服务函数：单事务内只做两件事（B5）——
① ``ChapterVersionRepository.accept_version`` 追加 ``version_type='accepted'`` 副本；
② ``ChapterHeadRepository.update`` 双指针（current/accepted 一并指向副本）+ status。
不跑 SettlementExtractor、不写结算库、不产生 ``plan_*`` pending 提案、不动 variant 行。
事务骨架镜像 ``accept_with_settlement_boundary``（``workflows/_nodes.py``）去掉 settlement 部分。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import aiosqlite
import structlog

from songyan.db.connection import get_db
from songyan.db.repository import ChapterHeadRepository, ChapterVersionRepository
from songyan.exceptions import SongyanError
from songyan.models.chapter import ChapterVersion
from songyan.utils.word_count import count_chinese_words
from songyan.workflows._helpers import new_id

logger = structlog.get_logger(__name__)


class NothingToAcceptError(SongyanError):
    """无可确认稿：head 行不存在，或 current_version_id 为空（exit 2）。"""

    exit_code = 2


class AlreadyAcceptedError(SongyanError):
    """章已 accepted：重复 accept 幂等提示（exit 2），不产生新版本。"""

    exit_code = 2


class ChapterFileError(SongyanError):
    """--from-file 读取失败或文件为空（exit 1，参数非法口径）。"""

    exit_code = 1


@dataclass(frozen=True)
class AcceptOutcome:
    """``accept_chapter`` 结果。"""

    chapter_number: int
    accepted_version_id: str
    source_version_id: str
    edited_version_id: str | None
    word_count: int
    edit_ratio: float = 0.0


async def accept_chapter(
    project_id: str,
    chapter_number: int,
    from_file: Path | None = None,
) -> AcceptOutcome:
    """确认一章：current 工作稿（或 --from-file 外置编辑稿）→ accepted 副本。

    ``--from-file`` 时事务内先物化 ``version_type='edited'`` 行
    （parent = 原工作稿、word_count 按文件实算、version_number 同一 conn MAX+1），
    再对 edited 行走 accept_version 副本链（edited → accepted）。
    """
    if chapter_number < 1:
        raise ValueError("chapter_number must be >= 1")

    # head 先取后判：upsert 会静默建新行，必须先 get（tech-m4 B2 / task 239）。
    head_repo = ChapterHeadRepository()
    head = await head_repo.get(project_id, chapter_number)
    if head is None:
        raise NothingToAcceptError(
            f"章 {chapter_number} 无工作稿（chapter_heads 无该行）；"
            f"请先通过 continue / variant pick 产生工作稿"
        )
    if head.status == "accepted":
        raise AlreadyAcceptedError(
            f"章 {chapter_number} 已 accepted（accepted_version_id={head.accepted_version_id}）；"
            f"重复 accept 不产生新版本"
        )
    if not head.current_version_id:
        raise NothingToAcceptError(
            f"章 {chapter_number} 的 current_version_id 为空，无可确认稿"
        )

    edited_content: str | None = None
    if from_file is not None:
        try:
            edited_content = from_file.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise ChapterFileError(f"读取编辑稿失败: {from_file}: {exc}") from exc
        if not edited_content.strip():
            raise ChapterFileError(f"编辑稿文件为空: {from_file}")

    version_repo = ChapterVersionRepository()
    source_version_id = head.current_version_id
    # task 257 / S5：人改率在事务前现算（editted 对原工作稿；纯复制 = 0），
    # 事务内经 set_edit_ratio 落 chapter_heads.edit_ratio 列（照 content_stale 先例）。
    edit_ratio = 0.0
    if edited_content is not None:
        source_version = await version_repo.get(head.current_version_id)
        if source_version is not None:
            from songyan.services.human_edit import compute_edit_ratio

            edit_ratio = compute_edit_ratio(source_version.content, edited_content)
    async with get_db() as conn:
        try:
            edited_version_id: str | None = None
            if edited_content is not None:
                edited = await _materialize_edited(
                    conn,
                    project_id=project_id,
                    chapter_number=chapter_number,
                    parent_version_id=head.current_version_id,
                    content=edited_content,
                )
                edited_version_id = edited.version_id
                source_version_id = edited.version_id
            accepted_version_id = await version_repo.accept_version(
                source_version_id, conn=conn
            )
            await head_repo.update(
                head.model_copy(
                    update={
                        "current_version_id": accepted_version_id,
                        "accepted_version_id": accepted_version_id,
                        "status": "accepted",
                        "updated_at": datetime.now(),
                    }
                ),
                conn=conn,
            )
            await head_repo.set_edit_ratio(
                project_id, chapter_number, edit_ratio, conn=conn
            )
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise

    accepted = await version_repo.get(accepted_version_id)
    assert accepted is not None
    logger.info(
        "chapter.accept",
        project_id=project_id,
        chapter_number=chapter_number,
        accepted_version_id=accepted_version_id,
        source_version_id=source_version_id,
        edited_version_id=edited_version_id,
        word_count=accepted.word_count,
        edit_ratio=edit_ratio,
    )
    return AcceptOutcome(
        chapter_number=chapter_number,
        accepted_version_id=accepted_version_id,
        source_version_id=source_version_id,
        edited_version_id=edited_version_id,
        word_count=accepted.word_count,
        edit_ratio=edit_ratio,
    )


async def _materialize_edited(
    conn: aiosqlite.Connection,
    *,
    project_id: str,
    chapter_number: int,
    parent_version_id: str,
    content: str,
) -> ChapterVersion:
    """在同一 conn 上物化 edited 行：version_number 走本事务 MAX+1（不另开连接）。"""
    cursor = await conn.execute(
        """SELECT COALESCE(MAX(version_number), 0) + 1
           FROM chapter_versions
           WHERE project_id = ? AND chapter_number = ?""",
        (project_id, chapter_number),
    )
    row = await cursor.fetchone()
    next_version_number = int(row[0]) if row is not None else 1
    edited = ChapterVersion(
        version_id=new_id("v"),
        project_id=project_id,
        chapter_number=chapter_number,
        version_number=next_version_number,
        version_type="edited",
        content=content,
        word_count=count_chinese_words(content),
        parent_version_id=parent_version_id,
    )
    await ChapterVersionRepository().create(edited, conn=conn)
    return edited
