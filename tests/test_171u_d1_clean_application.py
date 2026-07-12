"""Task 171u: Ch200 D1 clean application and report fact-source refresh."""

from __future__ import annotations

from pathlib import Path

import pytest

from songyan.db.connection import get_db
from songyan.db.continuity_repo import ContinuityReportRepository, SettingTrackingRepository
from songyan.db.repository import (
    ChapterHeadRepository,
    ChapterVersionRepository,
    ProjectRepository,
)
from songyan.evals.db_metrics import collect_orphan_metrics
from songyan.models import (
    ChapterHead,
    ChapterVersion,
    ContinuityReport,
    OrphanedSetting,
    ProjectSetting,
    TextCleanlinessCleanIssue,
)
from songyan.services import text_cleanliness_cleaner as cleaner
from songyan.services.text_cleanliness_cleaner import (
    TextCleanlinessCleanError,
    TextCleanResult,
    apply_chapter_text_cleaning,
    clean_chapter_text,
)

PID = "proj-171u"


async def _seed_project(project_id: str = PID) -> None:
    await ProjectRepository().create(
        ProjectSetting(genre_id="scifi", protagonist_name="林渊"),
        project_id=project_id,
    )


async def _seed_accepted_chapter(
    project_id: str,
    chapter: int,
    content: str,
    *,
    version_id: str | None = None,
) -> str:
    version_id = version_id or f"v-{project_id}-{chapter}-accepted"
    await ChapterVersionRepository().create(
        ChapterVersion(
            version_id=version_id,
            project_id=project_id,
            chapter_number=chapter,
            version_number=1,
            version_type="accepted",
            content=content,
            word_count=len(content),
            generation_metadata={"seed": True},
            score_card={"overall": 0.9},
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


def _dirty_text() -> str:
    para = (
        "林渊把那段不断回放的警报压进日志里，确认每一个闪烁频率都指向同一处裂隙，"
        "也指向舱壁后方那条正在扩大的黑色缝隙。"
    )
    return "\n\n".join(
        [
            "# 第一章 方舟",
            "林渊推开舱门。",
            "【保护内容 — 请勿修改】",
            "他抬起左臂 / 然后把接口压进冷光里。",
            "……",
            "每句末尾加重语气，机械眼闪烁红色警告。",
            para,
            "过渡段。",
            para,
        ]
    )


class TestTextCleaner:
    def test_clean_chapter_text_removes_171u_known_artifacts(self) -> None:
        result = clean_chapter_text(_dirty_text(), chapter_number=1, version_id="v1")

        assert result.changed is True
        assert result.remaining_issues == []
        assert "# 第一章" not in result.cleaned_content
        assert "保护内容" not in result.cleaned_content
        assert "/" not in result.cleaned_content
        assert "每句末尾" not in result.cleaned_content
        assert "……\n" not in result.cleaned_content
        assert result.cleaned_content.count("不断回放的警报") == 1

    def test_clean_chapter_text_preserves_safe_slashes(self) -> None:
        text = "速度稳定在 12km/s，日志路径 C:/tmp/songyan/report.txt。"

        result = clean_chapter_text(text)

        assert result.changed is False
        assert result.cleaned_content == text

    def test_clean_chapter_text_removes_quote_splice_slash(self) -> None:
        text = "“十八秒。”雷哲说，“马上撤离。” / “我在撤离。”林渊冲回控制台。"

        result = clean_chapter_text(text)

        assert result.remaining_issues == []
        assert "/" not in result.cleaned_content
        assert "我在撤离" in result.cleaned_content

    def test_clean_chapter_text_removes_standalone_ellipsis_line(self) -> None:
        text = "林渊沉默了……然后继续向前。\n……\n赵铭关掉警报。"

        result = clean_chapter_text(text)

        assert result.remaining_issues == []
        assert "林渊沉默了……然后继续向前。" in result.cleaned_content
        assert "\n……\n" not in result.cleaned_content


class TestCleanApplication:
    async def test_clean_issue_creates_new_accepted_version_and_updates_head(
        self, test_db: Path
    ) -> None:
        await _seed_project()
        original_id = await _seed_accepted_chapter(PID, 1, _dirty_text())

        result = await apply_chapter_text_cleaning(PID, 1)

        assert result.changed is True
        assert result.original_version_id == original_id
        assert result.cleaned_version_id is not None
        assert result.remaining_issues == []

        old_version = await ChapterVersionRepository().get(original_id)
        new_version = await ChapterVersionRepository().get(result.cleaned_version_id)
        head = await ChapterHeadRepository().get(PID, 1)

        assert old_version is not None
        assert old_version.content == _dirty_text()
        assert new_version is not None
        assert new_version.version_type == "accepted"
        assert new_version.parent_version_id == original_id
        assert new_version.generation_metadata["task"] == "171u"
        assert new_version.generation_metadata["cleaned_from_version_id"] == original_id
        assert new_version.generation_metadata["clean_issues"]
        assert head is not None
        assert head.current_version_id == result.cleaned_version_id
        assert head.accepted_version_id == result.cleaned_version_id
        assert head.status == "accepted"

    async def test_clean_text_is_idempotent(self, test_db: Path) -> None:
        await _seed_project("proj-171u-clean")
        await _seed_accepted_chapter("proj-171u-clean", 1, "林渊推开舱门。")

        result = await apply_chapter_text_cleaning("proj-171u-clean", 1)

        assert result.changed is False
        assert result.cleaned_version_id is None
        versions = await ChapterVersionRepository().list_by_chapter("proj-171u-clean", 1)
        assert len(versions) == 1

    async def test_remaining_hard_issue_does_not_update_head(
        self, test_db: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        await _seed_project("proj-171u-blocked")
        original_id = await _seed_accepted_chapter(
            "proj-171u-blocked", 1, "# 第一章\n\n正文。"
        )
        issue = TextCleanlinessCleanIssue(
            issue_type="markdown_heading_leak",
            evidence_quote="# 第一章",
            evidence_location="第1段第1句",
            suggested_action="删除 Markdown 章节标题行。",
            deterministic_cleanable=True,
        )

        def _fake_clean(
            content: str,
            *,
            chapter_number: int | None = None,
            version_id: str | None = None,
        ) -> TextCleanResult:
            return TextCleanResult(
                original_content=content,
                cleaned_content="正文。",
                issues=[issue],
                remaining_issues=[issue],
            )

        monkeypatch.setattr(cleaner, "clean_chapter_text", _fake_clean)

        with pytest.raises(TextCleanlinessCleanError):
            await apply_chapter_text_cleaning("proj-171u-blocked", 1)

        head = await ChapterHeadRepository().get("proj-171u-blocked", 1)
        versions = await ChapterVersionRepository().list_by_chapter(
            "proj-171u-blocked", 1
        )
        assert head is not None
        assert head.accepted_version_id == original_id
        assert len(versions) == 1


def _orphan(key: str, category: str, up_to: int) -> OrphanedSetting:
    return OrphanedSetting(
        tracking_id=f"t-{key}",
        setting_key=key,
        setting_name=key,
        introduced_in_chapter=1,
        last_mentioned_chapter=1,
        chapters_since_mention=up_to - 1,
        category=category,
    )


class TestLatestContinuityReport:
    async def test_collect_orphan_metrics_uses_latest_report_per_chapter(
        self, test_db: Path
    ) -> None:
        project_id = "proj-171u-report"
        await _seed_project(project_id)
        repo = ContinuityReportRepository()
        await repo.create(
            ContinuityReport(
                report_id="zzz-old",
                project_id=project_id,
                checked_up_to_chapter=165,
                orphaned_settings=[_orphan("stale", "critical", 165)],
                overall_health_score=3.0,
            )
        )
        await repo.create(
            ContinuityReport(
                report_id="aaa-new",
                project_id=project_id,
                checked_up_to_chapter=165,
                orphaned_settings=[],
                overall_health_score=9.5,
            )
        )
        async with get_db() as conn:
            await conn.execute(
                "UPDATE continuity_reports SET created_at = ? WHERE report_id = ?",
                ("2026-07-12T10:00:00", "zzz-old"),
            )
            await conn.execute(
                "UPDATE continuity_reports SET created_at = ? WHERE report_id = ?",
                ("2026-07-12T11:00:00", "aaa-new"),
            )
            await conn.commit()

        points = await collect_orphan_metrics(project_id, 160, 170)
        reports = await repo.list_by_chapter_range(project_id, 160, 170)

        assert len(reports) == 1
        assert reports[0].report_id == "aaa-new"
        assert len(points) == 1
        assert points[0].orphan_critical == 0

    async def test_collect_orphan_metrics_filters_stale_orphan_when_tracking_refreshed(
        self, test_db: Path
    ) -> None:
        project_id = "proj-171u-stale"
        await _seed_project(project_id)
        await SettingTrackingRepository().create(
            tracking_id="t-stale",
            project_id=project_id,
            setting_key="protagonist.genetic_identity.reaper_maker_consistency",
            setting_name="林渊与收割者制造者的基因一致性",
            description="",
            introduced_in_chapter=154,
            category="critical",
        )
        await SettingTrackingRepository().update_last_mentioned("t-stale", 200)
        await ContinuityReportRepository().create(
            ContinuityReport(
                report_id="stale-report",
                project_id=project_id,
                checked_up_to_chapter=165,
                orphaned_settings=[_orphan("stale", "critical", 165)],
                overall_health_score=8.4,
            )
        )

        points = await collect_orphan_metrics(project_id, 160, 170)

        assert len(points) == 1
        assert points[0].orphan_total == 0
        assert points[0].orphan_critical == 0
