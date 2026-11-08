"""M4 步 4 切片 1/2: review 只读聚合（tech-m4 §4.4 / B8 / B11）。

切片 1 硬断言：12 表行数前后不变 + merge_reviews 未被调用（mock + 模块级断言）+ gate 现算
（mock 断言入参正文 = head.current_version_id 工作稿）。
切片 2 输入并集：七源 fixture 各源分区计数；缺源 → 分区空而不炸；
无工作稿章 → 依赖正文的分区注明。
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from songyan.config import settings
from songyan.db.chapter_variant_repo import ChapterVariantRepository
from songyan.db.connection import get_db
from songyan.db.human_mark_repo import HumanMarkRepository
from songyan.db.migrations import init_schema
from songyan.db.plan_fact_repo import PlanFactRepository
from songyan.db.repository import (
    ChapterHeadRepository,
    ChapterVersionRepository,
    ProjectRepository,
)
from songyan.db.review_repo import LiteraryObservationRepository, ReviewReportRepository
from songyan.models.chapter import ChapterHead, ChapterVersion
from songyan.models.human_mark import HumanMark
from songyan.models.literary import LiteraryAuditResult, LiteraryObservation
from songyan.models.plan_facts import PlanEntity
from songyan.models.project import ProjectSetting
from songyan.models.review import (
    LLMAuditResult,
    MergedReviewReport,
    ReviewCategory,
    ReviewIssue,
    RuleAuditResult,
)
from songyan.models.variant import ChapterVariant
from songyan.plan_checks.gate import PlanFactGateReport
from songyan.plan_checks.must_mention import MissingMention
from songyan.services.review_report import (
    ZERO_WRITE_TABLES,
    build_chapter_review,
    list_chapter_universe,
)

_PROJECT = "p-m4-review-svc"
_TS = "2026-11-08T00:00:00Z"

# ch2 工作稿：含句子复读（≥12×3）、未登记拉丁专名、未登记 CJK 专名（≥3 次）；
# Kessel 经 approved alias 登记 → 不命中。
_CH1_ACCEPTED = (
    "第一章正文：陈照到了南站。末班车在午夜十二点准时进站了。他收好车票，走进雨里。"
)
_CH2_WORKDRAFT = (
    "末班车在午夜十二点准时进站了。\n陈照握紧Kessel铜牌，抬头看见Ashford。\n"
    "黑潮会馆的灯还亮着。\n\n末班车在午夜十二点准时进站了。\n"
    "末班车在午夜十二点准时进站了。\n黑潮会馆的灯还亮着。\n黑潮会馆的灯还亮着。"
)

_GATE_REPORT = PlanFactGateReport(
    project_id=_PROJECT,
    chapter=2,
    missing_mentions=[
        MissingMention(point_id="clue-1", label="末班铜牌", chapter=2, missing_terms=["末班铜牌"])
    ],
    passed=False,
)


@pytest.fixture
async def review_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "m4-review-svc.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="mystery_noir",
            mode_id="webnovel",
            protagonist_name="陈照",
            title="m4 review svc",
        ),
        _PROJECT,
    )
    return db_path


async def _seed_chapter(chapter: int, version_id: str, content: str) -> None:
    version = ChapterVersion(
        version_id=version_id,
        project_id=_PROJECT,
        chapter_number=chapter,
        version_number=1,
        version_type="draft",
        content=content,
        word_count=len(content),
    )
    await ChapterVersionRepository().create(version)
    await ChapterHeadRepository().update(
        ChapterHead(
            project_id=_PROJECT,
            chapter_number=chapter,
            current_version_id=version_id,
            accepted_version_id=None,
            status="draft",
        )
    )


async def _mark_accepted(chapter: int, version_id: str) -> None:
    head = await ChapterHeadRepository().get(_PROJECT, chapter)
    assert head is not None
    await ChapterHeadRepository().update(
        ChapterHead(
            project_id=_PROJECT,
            chapter_number=chapter,
            current_version_id=version_id,
            accepted_version_id=version_id,
            status="accepted",
        )
    )


async def _clear_head(chapter: int) -> None:
    """head 双指针置 NULL：该章在章宇宙内但无工作稿。"""
    await ChapterHeadRepository().update(
        ChapterHead(
            project_id=_PROJECT,
            chapter_number=chapter,
            current_version_id=None,
            accepted_version_id=None,
            status="draft",
        )
    )


async def _seed_full_fixture() -> None:
    """七源齐全：ch1 accepted + ch2 工作稿 + gate 硬伤 + 三审 draft 版 + literary
    + 复读命中 + 专名命中 + variant stale + 人的 mark（一章内一章外）。"""
    await _seed_chapter(1, "v-rev-1", _CH1_ACCEPTED)
    await _mark_accepted(1, "v-rev-1")
    await _seed_chapter(2, "v-rev-2-draft", _CH2_WORKDRAFT)

    # ① gate 由 mock 现算（见测试内 monkeypatch）；这里只备 approved 实体别名。
    await PlanFactRepository().write_entity(
        PlanEntity(
            entity_id="entity-copper-token",
            project_id=_PROJECT,
            entity_type="item",
            aliases=["Kessel"],
            approval_status="approved",
        )
    )

    # ② 三审报告落在生成时的 draft 版上（rule + llm 各一）。
    rule_report = MergedReviewReport(
        chapter_version_id="v-rev-2-draft",
        rule_audit=RuleAuditResult(ai_tell_count=2, word_count=100),
        overall_score=6.0,
        summary="rule pass",
    )
    await ReviewReportRepository().create(rule_report, "rr-rule-1", audit_type="rule")
    llm_report = MergedReviewReport(
        chapter_version_id="v-rev-2-draft",
        llm_audit=LLMAuditResult(
            issues=[
                ReviewIssue(
                    issue_id="iss-1",
                    category=ReviewCategory.WORLD_CONSISTENCY,
                    severity="major",
                    evidence_quote="黑潮会馆的灯还亮着",
                    evidence_location="第3段",
                    issue_description="世界观不一致示例",
                )
            ],
            summary="llm found issues",
        ),
        overall_score=5.0,
        summary="llm issues",
    )
    await ReviewReportRepository().create(llm_report, "rr-llm-1", audit_type="llm")

    # ③ literary_observations 挂在 draft 版上。
    await LiteraryObservationRepository().create(
        LiteraryAuditResult(
            observations=[
                LiteraryObservation(
                    observation_id="lo-1",
                    observation_type="cliche_risk",
                    description="套路化风险示例",
                    evidence_quote="末班车进站了",
                    severity="critical",
                )
            ],
            summary="literary summary",
        ),
        "obs-1",
        "v-rev-2-draft",
    )

    # ⑥ variant 备注（stale 槽）。
    await ChapterVariantRepository().insert(
        ChapterVariant(
            variant_id="var-rev-2-1",
            project_id=_PROJECT,
            chapter_number=2,
            slot_index=1,
            status="generated",
            parent_canon_fingerprint="fp-rev",
            content_ref="v-rev-2-draft",
            stale_vs_canon=1,
            cost_cny_estimate=0.35,
            created_at=_TS,
            updated_at=_TS,
        )
    )

    # ⑦ 人的 mark：ch1 ≤ 被审章 2（入选），ch5 > 2（过滤）。
    await HumanMarkRepository().create(
        HumanMark(mark_id="hm-in", project_id=_PROJECT, mark_type="foreshadowing",
                  target_key="铜镜", note="铜镜来历待交代", priority=7,
                  created_at_chapter=1)
    )
    await HumanMarkRepository().create(
        HumanMark(mark_id="hm-out", project_id=_PROJECT, mark_type="custom",
                  target_key="后文", note="未来章节的标记", priority=5,
                  created_at_chapter=5)
    )


async def _table_counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    async with get_db() as conn:
        for table in ZERO_WRITE_TABLES:
            cursor = await conn.execute(f"SELECT COUNT(*) FROM {table}")
            row = await cursor.fetchone()
            counts[table] = int(row[0]) if row else 0
    return counts


# --- 切片 2: 输入并集 ----------------------------------------------------------


def test_union_of_seven_sources(
    review_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    asyncio.run(_seed_full_fixture())
    gate_mock = AsyncMock(return_value=_GATE_REPORT)
    monkeypatch.setattr("songyan.services.review_report.run_plan_fact_gate", gate_mock)

    report = asyncio.run(build_chapter_review(_PROJECT, 2))

    assert report.chapter == 2
    assert report.workdraft_version_id == "v-rev-2-draft"

    # ① gate 现算：mock 断言入参正文 = 工作稿；不传 extracts（typed 腿恒空，同 check 生产路径）。
    gate_mock.assert_awaited_once_with(_PROJECT, 2, _CH2_WORKDRAFT)
    assert report.gate is not None
    assert report.gate.passed is False
    assert len(report.gate.missing_mentions) == 1

    # ② 三审：draft 版各取最新，rule + llm 两条。
    assert len(report.audits) == 1
    snapshot = report.audits[0]
    assert snapshot.version_id == "v-rev-2-draft"
    assert snapshot.rule is not None and snapshot.llm is not None
    assert [i.severity for i in snapshot.llm.issues] == ["major"]

    # ③ literary：按章回读 1 条。
    assert len(report.literary) == 1
    assert report.literary[0]["observation_id"] == "obs-1"

    # ④ 复读：句子腿（3 次）+ 跨章腿（ch1 accepted 同款句）。
    kinds = sorted(h.kind for h in report.repetition_hits)
    assert kinds == ["cross_chapter", "sentence"]

    # ⑤ 专名：Ashford + 黑潮会馆 命中；Kessel（approved alias）与陈照（主角名）不命中。
    #    CJK 腿按规格会对 ≥3 次复读句产生边界 n-gram（固有噪声），断言含意不变式。
    names = {h.name for h in report.proper_noun_hits}
    assert {"Ashford", "黑潮会馆"} <= names
    assert "Kessel" not in names
    assert "陈照" not in names
    assert all(h.kind == "latin" or h.kind == "cjk" for h in report.proper_noun_hits)

    # ⑥ variant 备注：stale 槽直读 list_for_chapter（不经 list_variant_rows）。
    assert len(report.variant_notes) == 1
    note = report.variant_notes[0]
    assert note.variant_id == "var-rev-2-1"
    assert note.stale_vs_canon == 1

    # ⑦ 人的 mark：只收 created_at_chapter ≤ 2。
    assert [m.mark_id for m in report.human_marks] == ["hm-in"]


def test_missing_sources_empty_sections(review_db: Path) -> None:
    """缺某源 → 分区空而不炸（head 双指针 NULL 的章无工作稿，三源注明）。"""
    asyncio.run(_seed_chapter(1, "v-rev-1", _CH1_ACCEPTED))
    asyncio.run(_clear_head(1))
    report = asyncio.run(build_chapter_review(_PROJECT, 1))

    assert report.workdraft_version_id is None
    assert report.gate is None
    assert "无工作稿" in report.gate_note
    assert report.repetition_hits == []
    assert "无工作稿" in report.repetition_note
    assert report.proper_noun_hits == []
    assert report.audits == []
    assert report.literary == []
    assert report.variant_notes == []
    assert report.human_marks == []


def test_cross_chapter_leg_skipped_without_previous_accepted(
    review_db: Path,
) -> None:
    """上一章无 accepted 正文 → 跨章复读腿跳过并注明。"""
    asyncio.run(_seed_chapter(1, "v-rev-1", _CH1_ACCEPTED))  # 有 head 但无 accepted
    asyncio.run(_seed_chapter(2, "v-rev-2", _CH2_WORKDRAFT))

    report = asyncio.run(build_chapter_review(_PROJECT, 2))
    kinds = [h.kind for h in report.repetition_hits]
    assert "cross_chapter" not in kinds
    assert "跨章" in report.repetition_note


def test_chapter_universe_is_head_rows(review_db: Path) -> None:
    """章宇宙 = chapter_heads 行；默认章 = 章号最大者。"""
    asyncio.run(_seed_chapter(1, "v-rev-1", _CH1_ACCEPTED))
    asyncio.run(_seed_chapter(3, "v-rev-3", "第三章草稿正文。"))
    assert asyncio.run(list_chapter_universe(_PROJECT)) == [1, 3]


# --- 切片 1: 零写库 ------------------------------------------------------------


def test_zero_writes_eight_tables_and_no_merge(
    review_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    asyncio.run(_seed_full_fixture())
    gate_mock = AsyncMock(return_value=_GATE_REPORT)
    monkeypatch.setattr("songyan.services.review_report.run_plan_fact_gate", gate_mock)
    merge_mock = AsyncMock()
    monkeypatch.setattr("songyan.workflows.review_merger.merge_reviews", merge_mock)

    before = asyncio.run(_table_counts())
    report = asyncio.run(build_chapter_review(_PROJECT, 2))
    after = asyncio.run(_table_counts())

    assert report.chapter == 2
    assert after == before  # 12 表（plan_* 五表 + 七张业务表）行数不变
    merge_mock.assert_not_awaited()  # merge_reviews 未调用（其写 review_reports）
    # 模块级断言：review_report 未绑定 merge_reviews 名字（防未来 from-import 绕过 mock）
    import songyan.services.review_report as review_report_module

    assert not hasattr(review_report_module, "merge_reviews")
    gate_mock.assert_awaited_once_with(_PROJECT, 2, _CH2_WORKDRAFT)  # gate 现算锁死
