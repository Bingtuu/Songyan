"""Task 164: 文本洁净度度量与 T9 harness 测试."""

from __future__ import annotations

from pathlib import Path

from songyan.db.migrations import _EXPECTED_TABLES
from songyan.db.repository import (
    ChapterHeadRepository,
    ChapterVersionRepository,
    ProjectRepository,
)
from songyan.db.text_cleanliness_repo import TextCleanlinessMetricRepository
from songyan.evals.db_metrics import render_stage_a_metrics
from songyan.evals.text_cleanliness import (
    collect_text_cleanliness_metrics,
    render_text_cleanliness_section,
)
from songyan.evals.v6_acceptance import check_t9, evaluate_v6_acceptance
from songyan.models import ChapterHead, ChapterVersion, ProjectSetting

PID = "proj-164"


def _long_para() -> str:
    return (
        "林渊把观测记录压在掌心，沿着裂开的甲板向前。"
        "雾面屏上残留的光像被潮汐拖长的伤口，逐行显示旧港区的压力曲线。"
        "他没有立刻下结论，只把每一次金属回声、每一次管线震颤、"
        "每一处温度异常都写进临时日志，等待它们在下一次共振里互相印证。"
    )


async def _seed_project(project_id: str = PID) -> None:
    await ProjectRepository().create(
        ProjectSetting(title=project_id, genre_id="scifi", protagonist_name="林渊"),
        project_id=project_id,
    )


async def _seed_accepted_chapter(
    project_id: str,
    chapter: int,
    content: str,
) -> str:
    version_id = f"v-{project_id}-{chapter}"
    await ChapterVersionRepository().create(
        ChapterVersion(
            version_id=version_id,
            project_id=project_id,
            chapter_number=chapter,
            version_number=1,
            version_type="accepted",
            content=content,
            word_count=len(content),
        )
    )
    await ChapterHeadRepository().update(
        ChapterHead(
            project_id=project_id,
            chapter_number=chapter,
            current_version_id=version_id,
            accepted_version_id=version_id,
            status="accepted",
        )
    )
    return version_id


class TestTextCleanlinessStorage:
    async def test_table_registered(self, test_db: Path) -> None:
        assert "text_cleanliness_metrics" in _EXPECTED_TABLES

    async def test_collect_persists_and_reads_metrics(self, test_db: Path) -> None:
        await _seed_project()
        para = _long_para()
        await _seed_accepted_chapter(PID, 1, "警报提示还剩三天。")
        await _seed_accepted_chapter(
            PID,
            2,
            f"### Scene N\n<!-- debug -->\n警报提示还剩五天。\n\n{para}\n\n{para}",
        )

        rows = await collect_text_cleanliness_metrics(PID, 1, 2, persist=True)
        persisted = await TextCleanlinessMetricRepository().list_by_project(PID, 1, 2)
        by_chapter = {row.chapter_number: row for row in persisted}

        assert len(rows) == 2
        assert len(persisted) == 2
        assert by_chapter[2].meta_tag_leak_count == 2
        assert by_chapter[2].duplicate_paragraph_count == 1
        assert by_chapter[2].timeline_conflict_count == 1
        assert by_chapter[2].details["meta_tag_matches"]
        assert by_chapter[2].details["timeline_conflicts"]

    async def test_render_stage_a_metrics_includes_cleanliness_section(
        self, test_db: Path
    ) -> None:
        await _seed_project()
        await _seed_accepted_chapter(PID, 1, "干净正文。")

        report = await render_stage_a_metrics(PID, 1, 1)

        assert "文本洁净度" in report
        assert "T9 harness 数据源" in report


class TestTextCleanlinessRender:
    async def test_render_section_summary(self, test_db: Path) -> None:
        await _seed_project()
        await _seed_accepted_chapter(PID, 1, "干净正文。")
        await _seed_accepted_chapter(PID, 2, "### Scene N\n正文。")
        rows = await collect_text_cleanliness_metrics(PID, 1, 2, persist=False)

        text = render_text_cleanliness_section(rows)

        assert "元标记 **1**" in text
        assert "重复长段落 **0**" in text
        assert "元标记违规章：[2]" in text


class TestT9Harness:
    async def test_t9_passes_when_all_clean(self, test_db: Path) -> None:
        project_id = "proj-164-clean"
        await _seed_project(project_id)
        await _seed_accepted_chapter(project_id, 1, "干净正文一。")
        await _seed_accepted_chapter(project_id, 2, "干净正文二。")

        result = await check_t9(project_id, 1, 2)

        assert result.passed is True
        assert result.sufficient is True
        assert "meta=0" in str(result.measured)

    async def test_t9_fails_on_meta_or_duplicate(self, test_db: Path) -> None:
        project_id = "proj-164-fail"
        await _seed_project(project_id)
        para = _long_para()
        await _seed_accepted_chapter(project_id, 1, f"### Scene N\n{para}\n\n{para}")

        result = await check_t9(project_id, 1, 1)

        assert result.passed is False
        assert "元标记违规章" in result.detail
        assert "重复长段落违规章" in result.detail

    async def test_t9_timeline_is_report_only_by_default(self, test_db: Path) -> None:
        project_id = "proj-164-timeline"
        await _seed_project(project_id)
        await _seed_accepted_chapter(project_id, 1, "警报提示还剩三天。")
        await _seed_accepted_chapter(project_id, 2, "警报提示还剩五天。")

        result = await check_t9(project_id, 1, 2)
        strict = await check_t9(project_id, 1, 2, include_timeline_in_redline=True)

        assert result.passed is True
        assert "时间线诊断章" in result.detail
        assert strict.passed is False
        assert "时间线红线章" in strict.detail

    async def test_t9_undecided_when_missing_accepted_chapter(self, test_db: Path) -> None:
        project_id = "proj-164-missing"
        await _seed_project(project_id)
        await _seed_accepted_chapter(project_id, 1, "干净正文。")

        result = await check_t9(project_id, 1, 2)

        assert result.passed is None
        assert result.sufficient is False
        assert "缺失章" in result.detail

    async def test_evaluate_v6_acceptance_includes_t9(self, test_db: Path) -> None:
        project_id = "proj-164-aggregate"
        await _seed_project(project_id)
        await _seed_accepted_chapter(project_id, 1, "干净正文。")

        result = await evaluate_v6_acceptance(project_id, 1, 1)

        t9 = next(item for item in result.results if item.key == "T9")
        assert t9.passed is True
