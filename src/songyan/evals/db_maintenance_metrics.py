"""DB 维护相关遥测（Task 156）：库尺寸、WAL 尺寸、连续性扫描耗时.

所有采样函数只读不改业务数据；维护动作（wal_checkpoint / optimize / VACUUM）
由 ``workflows.phase2_graph._run_db_maintenance`` 在章节边界触发。
"""

from __future__ import annotations

import time
from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import TYPE_CHECKING, Any

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


class T5LatencyAnalysis(BaseModel):
    """T5 扫描耗时稳健口径分析结果."""

    baseline_ms: float
    baseline_sample_count: int
    max_latency_ms: float
    max_latency_ratio: float
    observed_breach_chapters: list[int]
    hard_breach_chapters: list[int]
    consecutive_breach_chapters: list[int]
    extreme_breach_chapters: list[int]
    threshold_ms: float
    hard_failed: bool


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


def analyze_t5_latency_samples(
    samples: list[dict[str, Any]],
    *,
    factor: float = 2.0,
    extreme_factor: float = 5.0,
) -> T5LatencyAnalysis:
    """用稳健口径分析 T5 连续性扫描耗时.

    - 同一章多次采样先取该章中位数，避免 resume/report 追加样本放大权重。
    - 基线取所有章采样中位数，红线为 median × factor。
    - 单个孤立样本超过红线只记观察项；连续破线或极端破线才 hard fail。
    """
    by_chapter: dict[int, list[float]] = defaultdict(list)
    for sample in samples:
        value = sample.get("scan_latency_ms")
        if value is None:
            continue
        by_chapter[int(sample["chapter_number"])].append(float(value))

    chapter_samples = [
        (chapter, float(median(values)))
        for chapter, values in sorted(by_chapter.items())
        if values
    ]
    values = [value for _, value in chapter_samples]
    baseline_ms = float(median(values)) if values else 0.0
    threshold_ms = baseline_ms * factor if baseline_ms > 0 else 0.0
    extreme_threshold_ms = baseline_ms * extreme_factor if baseline_ms > 0 else 0.0

    observed_breaches: list[tuple[int, int, float]] = []
    extreme_breach_chapters: list[int] = []
    max_latency_ms = max(values) if values else 0.0
    max_latency_ratio = max_latency_ms / baseline_ms if baseline_ms > 0 else 0.0
    for idx, (chapter, value) in enumerate(chapter_samples):
        if baseline_ms <= 0 or value <= threshold_ms:
            continue
        observed_breaches.append((idx, chapter, value))
        if value > extreme_threshold_ms:
            extreme_breach_chapters.append(chapter)

    consecutive_breach_chapters: list[int] = []
    for left, right in zip(observed_breaches, observed_breaches[1:]):
        if right[0] == left[0] + 1:
            consecutive_breach_chapters.extend([left[1], right[1]])

    hard_breach_chapters = sorted(
        set(consecutive_breach_chapters + extreme_breach_chapters)
    )

    return T5LatencyAnalysis(
        baseline_ms=baseline_ms,
        baseline_sample_count=len(values),
        max_latency_ms=max_latency_ms,
        max_latency_ratio=max_latency_ratio,
        observed_breach_chapters=[chapter for _, chapter, _ in observed_breaches],
        hard_breach_chapters=hard_breach_chapters,
        consecutive_breach_chapters=sorted(set(consecutive_breach_chapters)),
        extreme_breach_chapters=extreme_breach_chapters,
        threshold_ms=threshold_ms,
        hard_failed=bool(hard_breach_chapters),
    )
