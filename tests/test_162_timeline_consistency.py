"""Task 162: 跨章时间线一致性诊断测试."""

from __future__ import annotations

from songyan.db.repository import (
    ChapterHeadRepository,
    ChapterVersionRepository,
    ProjectRepository,
)
from songyan.evals.db_metrics import render_stage_a_metrics
from songyan.evals.timeline_consistency import (
    collect_timeline_conflicts,
    detect_timeline_conflicts,
    extract_time_signals,
    render_timeline_consistency_section,
)
from songyan.models import ChapterHead, ChapterVersion, ProjectSetting


def _signals_by_chapter(contents: dict[int, str]):
    return {
        chapter: extract_time_signals(chapter, content)
        for chapter, content in contents.items()
    }


class TestExtractTimeSignals:
    def test_extracts_countdown_dates_and_relative_sequence(self) -> None:
        content = (
            "2040-07-03 08:30，主控台亮起。\n"
            "警报提示：还剩三天，潮汐墙就会抵达。\n"
            "次日，林渊把旧港区地图摊开。"
        )

        signals = extract_time_signals(7, content)

        assert {signal.signal_type for signal in signals} == {
            "countdown",
            "absolute_date",
            "relative_sequence",
        }
        countdown = next(signal for signal in signals if signal.signal_type == "countdown")
        assert countdown.value == 3
        assert countdown.unit == "天"
        assert countdown.normalized_value == 72.0
        date_signal = next(signal for signal in signals if signal.signal_type == "absolute_date")
        assert date_signal.value == "2040-07-03"
        relative = next(
            signal for signal in signals if signal.signal_type == "relative_sequence"
        )
        assert relative.normalized_value == 1

    def test_no_signal_for_subjective_time(self) -> None:
        content = "仿佛过了很久，灯光才重新亮起。"

        assert extract_time_signals(1, content) == []


class TestDetectTimelineConflicts:
    def test_detects_countdown_increase(self) -> None:
        signals = _signals_by_chapter(
            {
                74: "屏幕提示：还剩三天，潮汐墙抵达。",
                75: "控制台刷新后写着：还剩五天，潮汐墙抵达。",
            }
        )

        conflicts = detect_timeline_conflicts(signals)

        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == "countdown_increase"
        assert conflicts[0].previous_chapter == 74
        assert conflicts[0].current_chapter == 75
        assert conflicts[0].previous_value == 3
        assert conflicts[0].current_value == 5

    def test_detects_absolute_date_rewind(self) -> None:
        signals = _signals_by_chapter(
            {
                10: "2040-07-03，林渊抵达旧港。",
                11: "2040-07-01，队伍已经进入同一条巷道。",
            }
        )

        conflicts = detect_timeline_conflicts(signals)

        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == "date_rewind"

    def test_no_conflict_for_monotonic_countdown_and_dates(self) -> None:
        signals = _signals_by_chapter(
            {
                1: "2040-07-01，警报提示还剩三天。",
                2: "2040-07-02，警报提示还剩二天。",
                3: "2040-07-03，警报提示还剩二十四小时。",
            }
        )

        assert detect_timeline_conflicts(signals) == []

    def test_flashback_context_is_ignored_for_conflict(self) -> None:
        signals = _signals_by_chapter(
            {
                20: "2040-07-03，林渊站在旧港。",
                21: "闪回档案显示：2040-07-01，第一支队伍曾经抵达这里。",
            }
        )

        conflicts = detect_timeline_conflicts(signals)

        assert conflicts == []
        later_signal = signals[21][0]
        assert later_signal.ignored_for_conflict is True
        assert "flashback_context" in later_signal.ignore_reason


class TestTimelineReport:
    def test_render_section_includes_conflicts_and_signal_details(self) -> None:
        signals = _signals_by_chapter(
            {
                1: "警报提示还剩三天。",
                2: "警报提示还剩五天。",
            }
        )
        conflicts = detect_timeline_conflicts(signals)

        text = render_timeline_consistency_section(signals, conflicts)

        assert "跨章时间线一致性诊断" in text
        assert "countdown_increase" in text
        assert "时间信号明细" in text

    async def test_collects_from_accepted_versions(self, test_db) -> None:
        project_id = "timeline-proj"
        await ProjectRepository().create(
            ProjectSetting(title="Timeline", genre_id="scifi", protagonist_name="林渊"),
            project_id=project_id,
        )
        for chapter, content in {
            1: "警报提示还剩三天。",
            2: "警报提示还剩五天。",
        }.items():
            version_id = f"v-timeline-{chapter}"
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

        signals, conflicts = await collect_timeline_conflicts(project_id, 1, 2)

        assert set(signals) == {1, 2}
        assert len(conflicts) == 1

    async def test_stage_a_metrics_renders_timeline_section(self, test_db) -> None:
        project_id = "timeline-report-proj"
        await ProjectRepository().create(
            ProjectSetting(title="Timeline", genre_id="scifi", protagonist_name="林渊"),
            project_id=project_id,
        )
        version_id = "v-timeline-report-1"
        await ChapterVersionRepository().create(
            ChapterVersion(
                version_id=version_id,
                project_id=project_id,
                chapter_number=1,
                version_number=1,
                version_type="accepted",
                content="2040-07-01，警报提示还剩三天。",
                word_count=20,
            )
        )
        await ChapterHeadRepository().update(
            ChapterHead(
                project_id=project_id,
                chapter_number=1,
                current_version_id=version_id,
                accepted_version_id=version_id,
                status="accepted",
            )
        )

        report = await render_stage_a_metrics(project_id, 1, 1)

        assert "跨章时间线一致性诊断" in report
        assert "抽取确定性时间信号" in report
