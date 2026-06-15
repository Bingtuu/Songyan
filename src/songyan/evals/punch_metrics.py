"""Punch Engine 自动评估 — 刺激点密度与情绪转折量化."""

from __future__ import annotations

import json
from pathlib import Path

import structlog

from songyan.db.connection import get_db

logger = structlog.get_logger(__name__)

DEFAULT_OUTPUT_DIR = Path("evals/output")


class PunchMetrics:
    """单章 Punch Engine 量化指标."""

    def __init__(
        self,
        chapter_number: int,
        word_count: int,
        punch_count: int = 0,
        punch_density: float = 0.0,
        emotion_switches: int = 0,
        emotion_switch_rate: float = 0.0,
    ) -> None:
        self.chapter_number = chapter_number
        self.word_count = word_count
        self.punch_count = punch_count
        self.punch_density = punch_density
        self.emotion_switches = emotion_switches
        self.emotion_switch_rate = emotion_switch_rate

    def to_dict(self) -> dict:
        return {
            "chapter_number": self.chapter_number,
            "word_count": self.word_count,
            "punch_count": self.punch_count,
            "punch_density": round(self.punch_density, 3),
            "emotion_switches": self.emotion_switches,
            "emotion_switch_rate": round(self.emotion_switch_rate, 3),
            "punch_density_ok": self.punch_density >= 1.0,
            "emotion_switch_ok": self.emotion_switch_rate >= 1.0,
        }


async def evaluate_punch_metrics(project_id: str) -> list[PunchMetrics]:
    """对已有章节运行 Punch Engine 量化评估.

    策略：
    1. 优先从 creative_briefs 读取 punch_points / emotion_arc
    2. 如果 creative_briefs 无数据，尝试从 review_reports 的 punch_check 读取
    3. 计算 punch_density（punch_count / word_count * 1000）和 emotion_switch_rate

    Returns:
        每章的 PunchMetrics 列表（按 chapter_number 排序）
    """
    metrics: list[PunchMetrics] = []

    async with get_db() as conn:
        conn.row_factory = lambda c, r: {
            col[0]: r[idx] for idx, col in enumerate(c.description)
        }

        # 获取项目下所有章节的 creative_brief
        cursor = await conn.execute(
            """SELECT chapter_number, punch_points, emotion_arc
               FROM creative_briefs
               WHERE project_id = ?
               ORDER BY chapter_number""",
            (project_id,),
        )
        brief_rows = await cursor.fetchall()

        # 获取每章字数（从 chapter_versions）
        cursor = await conn.execute(
            """SELECT chapter_number, word_count
               FROM chapter_versions
               WHERE project_id = ? AND version_type = 'accepted'
               ORDER BY chapter_number""",
            (project_id,),
        )
        word_count_map = {
            row["chapter_number"]: row["word_count"] or 0
            for row in await cursor.fetchall()
        }

    for row in brief_rows:
        chapter_number = row["chapter_number"]
        word_count = word_count_map.get(chapter_number, 3000)

        # 解析 punch_points
        punch_points_raw = row["punch_points"] or "[]"
        try:
            punch_data = json.loads(punch_points_raw)
            punch_count = len(punch_data)
        except json.JSONDecodeError:
            punch_count = 0

        # 解析 emotion_arc
        emotion_arc_raw = row["emotion_arc"] or "[]"
        try:
            emotion_data = json.loads(emotion_arc_raw)
            emotion_switches = len(emotion_data)
        except json.JSONDecodeError:
            emotion_switches = 0

        punch_density = (punch_count / word_count * 1000) if word_count > 0 else 0.0
        emotion_switch_rate = (
            (emotion_switches / word_count * 1500) if word_count > 0 else 0.0
        )

        metrics.append(
            PunchMetrics(
                chapter_number=chapter_number,
                word_count=word_count,
                punch_count=punch_count,
                punch_density=punch_density,
                emotion_switches=emotion_switches,
                emotion_switch_rate=emotion_switch_rate,
            )
        )

    logger.info(
        "punch_metrics.evaluated",
        project_id=project_id,
        chapters_evaluated=len(metrics),
    )
    return metrics


def save_punch_metrics(
    metrics: list[PunchMetrics],
    output_path: Path | None = None,
) -> Path:
    """保存 PunchMetrics 到 JSON 文件.

    Returns:
        输出文件路径
    """
    if output_path is None:
        DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = DEFAULT_OUTPUT_DIR / "punch_metrics.json"

    data = {
        "total_chapters": len(metrics),
        "avg_punch_density": (
            round(sum(m.punch_density for m in metrics) / len(metrics), 3)
            if metrics else 0.0
        ),
        "avg_emotion_switch_rate": (
            round(sum(m.emotion_switch_rate for m in metrics) / len(metrics), 3)
            if metrics else 0.0
        ),
        "chapters": [m.to_dict() for m in metrics],
    }

    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("punch_metrics.saved", path=str(output_path))
    return output_path
