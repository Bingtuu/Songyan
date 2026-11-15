"""task 269 切片2：承诺管理写径——人确认到期日 + 归档（放弃）。

- ``confirm_due``：人显式确认到期日（confirmed_due_chapter）。
  未确认前 LLM 的 expected_resolve_chapter 只是建议，不驱动 overdue/+2 紧迫。
- ``archive_promise``：放弃的承诺 lifecycle_status='archived'（幂等 noop）；
  归档后出开放集 / today overdue / 上下文紧迫；不是 ``confirm promise``
  （那个仍是人确认回收为 resolved）。
写径独立显式，不与入典 batch 绑定。
"""

from __future__ import annotations

import structlog

from songyan.db.settlement_repo import ForeshadowingRepository
from songyan.exceptions import SongyanError

logger = structlog.get_logger(__name__)

_OPEN_STATUSES = ("planted", "due", "overdue")


class PromiseAdminError(SongyanError):
    """承诺管理业务拒绝（CLI 映射 exit 2）。"""

    exit_code = 2


async def confirm_due(project_id: str, foreshadowing_id: str, chapter: int) -> str:
    """人确认到期日；仅开放承诺集（active + planted/due/overdue）可写。"""
    if chapter < 1:
        raise PromiseAdminError("chapter 须为正整数")
    repo = ForeshadowingRepository()
    row = await repo.get_row(foreshadowing_id)
    if row is None or row["project_id"] != project_id:
        raise PromiseAdminError(f"承诺不存在：{foreshadowing_id}")
    lifecycle = row.get("lifecycle_status") or "active"
    status = row["status"]
    if lifecycle != "active" or status not in _OPEN_STATUSES:
        raise PromiseAdminError(
            f"承诺不在开放集，不能确认到期日: {foreshadowing_id} "
            f"(status={status}, lifecycle_status={lifecycle})"
        )
    count = await repo.set_confirmed_due(foreshadowing_id, chapter)
    if count != 1:
        raise PromiseAdminError(
            f"承诺不在开放集（并发或状态已变）: {foreshadowing_id}"
        )
    logger.info(
        "promise.confirm_due",
        project_id=project_id,
        foreshadowing_id=foreshadowing_id,
        chapter=chapter,
    )
    return f"confirmed due ch{chapter}：{foreshadowing_id}"


async def archive_promise(project_id: str, foreshadowing_id: str) -> str:
    """归档放弃的承诺（幂等）；已归档返回 'noop'。"""
    repo = ForeshadowingRepository()
    row = await repo.get_row(foreshadowing_id)
    if row is None or row["project_id"] != project_id:
        raise PromiseAdminError(f"承诺不存在：{foreshadowing_id}")
    lifecycle = row.get("lifecycle_status") or "active"
    if lifecycle == "archived":
        return "noop"
    await repo.set_lifecycle_status(foreshadowing_id, "archived")
    logger.info(
        "promise.archive",
        project_id=project_id,
        foreshadowing_id=foreshadowing_id,
    )
    return "archive"
