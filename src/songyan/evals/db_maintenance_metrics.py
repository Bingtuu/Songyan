"""DB 维护相关遥测（Task 156）：库尺寸、WAL 尺寸、连续性扫描耗时.

所有采样函数只读不改业务数据；维护动作（wal_checkpoint / optimize / VACUUM）
由 ``workflows.phase2_graph._run_db_maintenance`` 在章节边界触发。
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel

from songyan.db.connection import get_db, get_db_path
from songyan.db.continuity_repo import SettingTrackingRepository

if TYPE_CHECKING:
    pass


class DbSizeMetrics(BaseModel):
    """某时刻 DB 文件与 WAL 尺寸快照."""

    db_size_bytes: int
    wal_size_bytes: int
    page_count: int
    page_size: int


class ContinuityScanLatency(BaseModel):
    """代表性连续性扫描耗时样本."""

    project_id: str
    up_to_chapter: int
    elapsed_ms: float


async def collect_db_size_metrics() -> DbSizeMetrics:
    """采样当前 DB 文件尺寸、WAL 尺寸、page_count / page_size.

    使用独立短连接，只读 PRAGMA，不持有写锁。
    """
    db_path = get_db_path()
    wal_path = db_path.with_suffix(db_path.suffix + "-wal")

    async with get_db() as conn:
        cursor = await conn.execute("PRAGMA page_count")
        row = await cursor.fetchone()
        page_count = int(row[0]) if row else 0

        cursor = await conn.execute("PRAGMA page_size")
        row = await cursor.fetchone()
        page_size = int(row[0]) if row else 0

    return DbSizeMetrics(
        db_size_bytes=_safe_file_size(db_path),
        wal_size_bytes=_safe_file_size(wal_path),
        page_count=page_count,
        page_size=page_size,
    )


def _safe_file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


async def measure_continuity_scan_latency(
    project_id: str,
    up_to_chapter: int,
) -> float:
    """以 ``find_orphaned`` 为代表性连续性扫描，计时返回 ``elapsed_ms``.

    该查询与 ContinuityAuditor 的 orphan 检测同源，能反映 setting_tracking
    表随章数增长的扫描退化情况。
    """
    repo = SettingTrackingRepository()
    start = time.monotonic()
    await repo.find_orphaned(project_id, up_to_chapter, threshold=3)
    elapsed_ms = (time.monotonic() - start) * 1000.0
    return elapsed_ms


def check_t5_size_redline(
    metrics: DbSizeMetrics,
    *,
    max_db_bytes: int = 300 * 1024 * 1024,
) -> bool:
    """T5 尺寸红线：DB 文件尺寸超过阈值.

    注意：这是运行时快速判定；干净 150 章基线由 Task 158 长跑实测后校准。
    """
    return metrics.db_size_bytes > max_db_bytes


def check_t5_latency_redline(
    elapsed_ms: float,
    baseline_ms: float,
    *,
    factor: float = 1.5,
) -> bool:
    """T5 耗时红线：扫描耗时超过基线 1.5 倍.

    基线不足（<=0）时不判红线，避免小样本误判。
    """
    if baseline_ms <= 0:
        return False
    return elapsed_ms > baseline_ms * factor
