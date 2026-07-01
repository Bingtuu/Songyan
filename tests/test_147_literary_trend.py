"""Tests for Task 147 — literary quality trend.

覆盖：按章范围回读（每章取最新版本 observation）；T3/T8 趋势检出（下滑触线、
无下滑不误报、基线不足、恰好 20% 边界）；只诊断（无 accept/gate 接入）。
"""

from __future__ import annotations

from pathlib import Path

from songyan.db.repository import ChapterVersionRepository, ProjectRepository
from songyan.db.review_repo import LiteraryObservationRepository
from songyan.evals.db_metrics import (
    LiteraryScorePoint,
    collect_literary_scores,
    detect_literary_trend,
    render_literary_section,
)
from songyan.models import ChapterVersion, LiteraryAuditResult, ProjectSetting

PID = "proj-147"


async def _seed_project() -> None:
    await ProjectRepository().create(
        ProjectSetting(genre_id="xuanhuan", protagonist_name="英雄"), PID
    )


async def _seed_chapter_scores(
    chapter: int, scores: tuple[float, float, float, float], *, version_number: int = 1
) -> str:
    """建 chapter_version + literary_observation；返回 version_id."""
    vid = f"v-{chapter}-{version_number}"
    await ChapterVersionRepository().create(
        ChapterVersion(
            version_id=vid,
            project_id=PID,
            chapter_number=chapter,
            version_number=version_number,
            version_type="accepted",
            content="x",
            word_count=1,
        )
    )
    lit, autonomy, grounding, fissure = scores
    await LiteraryObservationRepository().create(
        LiteraryAuditResult(
            observations=[],
            literary_quality_score=lit,
            character_autonomy_score=autonomy,
            conceptual_grounding_score=grounding,
            fissure_preservation_score=fissure,
        ),
        observation_id=f"obs-{vid}",
        version_id=vid,
    )
    return vid


# --------------------------------------------------------------------------- #
# range read-back
# --------------------------------------------------------------------------- #
class TestCollectLiteraryScores:
    async def test_per_chapter_scores(self, test_db: Path) -> None:
        await _seed_project()
        await _seed_chapter_scores(1, (7.0, 8.0, 6.0, 9.0))
        await _seed_chapter_scores(2, (7.5, 8.5, 6.5, 9.5))
        points = await collect_literary_scores(PID, 1, 10)
        assert [p.chapter for p in points] == [1, 2]
        assert points[0].character_autonomy_score == 8.0
        assert points[1].conceptual_grounding_score == 6.5

    async def test_latest_version_per_chapter(self, test_db: Path) -> None:
        await _seed_project()
        await _seed_chapter_scores(1, (5.0, 5.0, 5.0, 5.0), version_number=1)
        # 同章更晚的版本（更晚 created_at）→ 应取此条
        await _seed_chapter_scores(1, (9.0, 9.0, 9.0, 9.0), version_number=2)
        points = await collect_literary_scores(PID, 1, 10)
        assert len(points) == 1
        assert points[0].literary_quality_score == 9.0

    async def test_empty(self, test_db: Path) -> None:
        await _seed_project()
        assert await collect_literary_scores(PID, 1, 10) == []


# --------------------------------------------------------------------------- #
# trend detection
# --------------------------------------------------------------------------- #
def _pts(values: list[float]) -> list[LiteraryScorePoint]:
    """构造仅 character_autonomy 维度变化的点序列（其余维度恒定高分）."""
    return [
        LiteraryScorePoint(
            chapter=i + 1,
            literary_quality_score=8.0,
            character_autonomy_score=v,
            conceptual_grounding_score=8.0,
            fissure_preservation_score=8.0,
        )
        for i, v in enumerate(values)
    ]


class TestDetectLiteraryTrend:
    def test_baseline_insufficient(self) -> None:
        result = detect_literary_trend(_pts([8.0] * 5))
        assert result.baseline_available is False
        assert result.breached_dimensions == []

    def test_no_breach_when_stable(self) -> None:
        result = detect_literary_trend(_pts([8.0] * 20))
        assert result.baseline_available is True
        assert "character_autonomy_score" not in result.breached_dimensions

    def test_breach_on_drop(self) -> None:
        # 前 10 章基线 8.0；后段跌到 5.0（降 37.5% > 20%）→ 触线
        values = [8.0] * 10 + [5.0] * 10
        result = detect_literary_trend(_pts(values))
        assert "character_autonomy_score" in result.breached_dimensions
        assert result.first_breach_window["character_autonomy_score"] is not None

    def test_boundary_exactly_20pct_triggers(self) -> None:
        # T3：下降 ≥20% 即触线。基线 10.0，窗口均值恰好 8.0 = 降 20% → 触线
        result = detect_literary_trend(_pts([10.0] * 10 + [8.0] * 10))
        assert "character_autonomy_score" in result.breached_dimensions

    def test_just_under_20pct_not_breached(self) -> None:
        # 降 19%（10.0 → 8.1）< 20% → 不触线
        result = detect_literary_trend(_pts([10.0] * 10 + [8.1] * 10))
        assert "character_autonomy_score" not in result.breached_dimensions

    def test_render_diagnose_only(self) -> None:
        # 渲染包含"只诊断不阻断"字样，确认无 gate 语义
        md = render_literary_section(_pts([8.0] * 10), detect_literary_trend(_pts([8.0] * 10)))
        assert "只诊断不阻断" in md
