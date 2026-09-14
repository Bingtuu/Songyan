"""Task 238-1: H 组观察列 — observation_counts 计数 + F6 跨章 diff + 报告聚合.

纯计数透出：在线路径零行为变化（observation_counts 默认空字典），
计数只在对应丢弃/回收实际发生时 +1；F6 为回放事务提交后的只读比较，
report-only，不进 hard gate、不影响 exit code。
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from songyan.agents.settlement_extractor import _validate_settlement
from songyan.db.continuity_repo import SettingTrackingRepository
from songyan.db.repository import CharacterRepository, ProjectRepository
from songyan.models import ProjectSetting, StateSettlement
from songyan.models.import_replay import ChapterReplayOutcome, ReplayReport
from songyan.models.settlement import (
    CharacterUpdate,
    ForeshadowingUpdate,
    NewSetting,
    NumericalUpdate,
)
from songyan.services.import_replay_service import replay_import
from songyan.services.import_segment_service import (
    build_manifest,
    confirm_manifest,
    write_segment_artifacts,
)
from songyan.workflows._helpers import ensure_protagonist_character

_SOURCE_TEXT = (
    "第一章 荒山\n林凡睁开眼睛，发现自己躺在荒山之中。\n\n"
    "第二章 下山\n林凡拍了拍尘土，朝山下走去。\n"
)


def _confirmed_manifest(tmp_path: Path, out_name: str = "segment_out") -> Path:
    """用 Task 235 的真实产物链路造 2 章 confirmed 清单，返回 manifest 路径."""
    source = tmp_path / "novel.txt"
    source.write_text(_SOURCE_TEXT, encoding="utf-8")
    manifest, normalized, bodies = build_manifest(source, token_budget=6000)
    manifest_path, _ = write_segment_artifacts(
        tmp_path / out_name, manifest, normalized, bodies
    )
    confirm_manifest(manifest_path)
    return manifest_path


async def _seed_project(with_protagonist: bool = True) -> str:
    await ProjectRepository().create(
        ProjectSetting(title="测试项目", genre_id="scifi", protagonist_name="林凡"),
        "proj-1",
    )
    if with_protagonist:
        created = await ensure_protagonist_character("proj-1")
        assert created, "测试种子应新建 protagonist 角色"
    characters = await CharacterRepository().list_by_project("proj-1")
    return next(c.character_id for c in characters if c.role_type == "protagonist")


@pytest.fixture
def mock_summary():
    with patch(
        "songyan.services.import_replay_service.write_chapter_summary_with_fact_check",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = ("sum-test", None, [])
        yield mock


@pytest.fixture
def mock_extract():
    with patch(
        "songyan.services.import_replay_service.extract_settlement",
        new_callable=AsyncMock,
    ) as mock:
        yield mock


class TestObservationCountsModel:
    """StateSettlement.observation_counts：默认空字典，在线路径零行为变化."""

    def test_default_empty(self) -> None:
        assert StateSettlement().observation_counts == {}

    def test_serialization_roundtrip(self) -> None:
        settlement = StateSettlement(observation_counts={"key_a": 2})
        restored = StateSettlement.model_validate(settlement.model_dump())
        assert restored.observation_counts == {"key_a": 2}
        # 默认构造序列化后为默认值，不携带多余状态
        assert StateSettlement().model_dump()["observation_counts"] == {}


class TestDuplicateSettingCounts:
    """重复 setting 簇：命中库内同簇 canonical → recycled；同章内重复 → skipped."""

    pytestmark = pytest.mark.asyncio

    async def test_recycled_when_cluster_canonical_exists(
        self, test_db: Path, tmp_path: Path, mock_extract, mock_summary
    ) -> None:
        await _seed_project()
        await SettingTrackingRepository().create(
            tracking_id="trk-1",
            project_id="proj-1",
            setting_key="world.spacetime.marking",
            setting_name="时空标记系统",
            description="基于时空标记的定位系统",
            introduced_in_chapter=1,
        )
        canned = StateSettlement(
            new_settings=[
                NewSetting(
                    setting_name="时空标记网络",
                    description="基于时空标记的定位网络",
                    source_quote="林凡睁开眼睛",
                    setting_key="world.spacetime.marking_v2",
                )
            ],
        )
        mock_extract.side_effect = lambda *args, **kwargs: canned
        manifest_path = _confirmed_manifest(tmp_path)

        report = await replay_import("proj-1", manifest_path, chapters={1})

        outcome = report.outcomes[0]
        assert outcome.status == "applied"
        assert outcome.observation_counts.get("setting_duplicate_recycled") == 1
        assert "setting_duplicate_skipped" not in outcome.observation_counts
        # 既有语义不变：重复 setting 被回收，不再登记新快照
        assert canned.new_settings == []

    async def test_skipped_when_duplicate_within_same_chapter(
        self, test_db: Path, tmp_path: Path, mock_extract, mock_summary
    ) -> None:
        await _seed_project()
        canned = StateSettlement(
            new_settings=[
                NewSetting(
                    setting_name="时空标记系统",
                    description="基于时空标记的定位系统",
                    source_quote="林凡睁开眼睛",
                    setting_key="world.spacetime.marking_a",
                ),
                NewSetting(
                    setting_name="时空标记网络",
                    description="基于时空标记的定位网络",
                    source_quote="林凡睁开眼睛",
                    setting_key="world.spacetime.marking_b",
                ),
            ],
        )
        mock_extract.side_effect = lambda *args, **kwargs: canned
        manifest_path = _confirmed_manifest(tmp_path)

        report = await replay_import("proj-1", manifest_path, chapters={1})

        outcome = report.outcomes[0]
        assert outcome.status == "applied"
        assert outcome.observation_counts.get("setting_duplicate_skipped") == 1
        assert "setting_duplicate_recycled" not in outcome.observation_counts
        # 既有语义不变：同簇首条保留、第二条丢弃
        assert len(canned.new_settings) == 1
        assert canned.new_settings[0].setting_key == "world.spacetime.marking_a"

    async def test_no_duplicate_no_count(
        self, test_db: Path, tmp_path: Path, mock_extract, mock_summary
    ) -> None:
        await _seed_project()
        canned = StateSettlement(
            new_settings=[
                NewSetting(
                    setting_name="普通设定",
                    description="无簇标记的普通设定",
                    source_quote="林凡睁开眼睛",
                    setting_key="world.misc.ordinary",
                )
            ],
        )
        mock_extract.side_effect = lambda *args, **kwargs: canned
        manifest_path = _confirmed_manifest(tmp_path)

        report = await replay_import("proj-1", manifest_path, chapters={1})

        assert report.outcomes[0].observation_counts == {}


class TestDroppedResolveCounts:
    """dropped resolve：缺 id / 未知 id → 计数 +1 且条目按既有语义丢弃（不阻断）.

    计数点在 _validate_settlement（extract 阶段，回放与在线共享同一函数），
    此处直接驱动真实 validate。
    """

    pytestmark = pytest.mark.asyncio

    async def test_missing_id_counted_and_dropped(self) -> None:
        settlement = StateSettlement(
            foreshadowing_updates=[
                ForeshadowingUpdate(
                    operation="resolve",
                    description="回收某伏笔",
                    source_version_id="v1",
                )
            ],
        )
        errors = await _validate_settlement(
            settlement,
            "正文",
            [],
            [],
            chapter_number=2,
            project_id="p1",
            resolvable_foreshadowing_ids={"fs-1"},
        )
        assert errors == []
        assert settlement.observation_counts["foreshadowing_resolve_missing_id"] == 1
        # 既有语义：条目被丢弃，不阻断整章结算
        assert settlement.foreshadowing_updates == []

    async def test_unknown_id_counted_and_dropped(self) -> None:
        settlement = StateSettlement(
            foreshadowing_updates=[
                ForeshadowingUpdate(
                    foreshadowing_id="fs-999",
                    operation="resolve",
                    description="回收不存在的伏笔",
                    source_version_id="v1",
                )
            ],
        )
        errors = await _validate_settlement(
            settlement,
            "正文",
            [],
            [],
            chapter_number=2,
            project_id="p1",
            resolvable_foreshadowing_ids={"fs-1"},
        )
        assert errors == []
        assert settlement.observation_counts["foreshadowing_resolve_unknown_id"] == 1
        assert settlement.foreshadowing_updates == []

    async def test_valid_resolve_not_counted(self) -> None:
        settlement = StateSettlement(
            foreshadowing_updates=[
                ForeshadowingUpdate(
                    foreshadowing_id="fs-1",
                    operation="resolve",
                    description="正常回收",
                    source_version_id="v1",
                )
            ],
        )
        errors = await _validate_settlement(
            settlement,
            "正文",
            [],
            [],
            chapter_number=2,
            project_id="p1",
            resolvable_foreshadowing_ids={"fs-1"},
        )
        assert errors == []
        assert settlement.observation_counts == {}
        assert len(settlement.foreshadowing_updates) == 1


class TestSkippedUpdateCounts:
    """未知 character_id 的 character_update / numerical_update 被跳过时计数."""

    pytestmark = pytest.mark.asyncio

    async def test_character_update_skipped_counted(
        self, test_db: Path, tmp_path: Path, mock_extract, mock_summary
    ) -> None:
        await _seed_project()
        canned = StateSettlement(
            character_updates=[
                CharacterUpdate(
                    character_id="char-ghost",
                    field="location",
                    old_value="未知",
                    new_value="荒山",
                    source_quote="林凡睁开眼睛",
                )
            ],
        )
        mock_extract.side_effect = lambda *args, **kwargs: canned
        manifest_path = _confirmed_manifest(tmp_path)

        report = await replay_import("proj-1", manifest_path, chapters={1})

        outcome = report.outcomes[0]
        assert outcome.status == "applied"
        assert outcome.observation_counts.get("character_update_skipped") == 1

    async def test_numerical_update_skipped_counted(
        self, test_db: Path, tmp_path: Path, mock_extract, mock_summary
    ) -> None:
        await _seed_project()
        canned = StateSettlement(
            numerical_updates=[
                NumericalUpdate(
                    character_id="char-ghost",
                    attribute_name="spirit_stones",
                    opening_value=0.0,
                    closing_value=10.0,
                )
            ],
        )
        mock_extract.side_effect = lambda *args, **kwargs: canned
        manifest_path = _confirmed_manifest(tmp_path)

        report = await replay_import("proj-1", manifest_path, chapters={1})

        outcome = report.outcomes[0]
        assert outcome.status == "applied"
        assert outcome.observation_counts.get("numerical_update_skipped") == 1
        # 未知角色未写台账 → F6 无前行可比对，不计 mismatch
        assert outcome.opening_closing_mismatch == 0


class TestOpeningClosingMismatch:
    """F6 跨章 diff：本章 opening_value 对前章最新 closing_value."""

    pytestmark = pytest.mark.asyncio

    def _numerical(self, character_id: str, opening: float, closing: float) -> StateSettlement:
        return StateSettlement(
            numerical_updates=[
                NumericalUpdate(
                    character_id=character_id,
                    attribute_name="spirit_stones",
                    opening_value=opening,
                    closing_value=closing,
                )
            ],
        )

    async def test_mismatch_counted_when_opening_differs(
        self, test_db: Path, tmp_path: Path, mock_extract, mock_summary
    ) -> None:
        pid = await _seed_project()
        mock_extract.side_effect = lambda body, project_id, chapter_number, *args, **kwargs: (
            self._numerical(pid, 0.0, 100.0)
            if chapter_number == 1
            else self._numerical(pid, 50.0, 60.0)
        )
        manifest_path = _confirmed_manifest(tmp_path)

        report = await replay_import("proj-1", manifest_path)

        assert [o.status for o in report.outcomes] == ["applied", "applied"]
        # 首章无前行 → 不计
        assert report.outcomes[0].opening_closing_mismatch == 0
        # 第二章 opening=50 ≠ 第一章 closing=100 → mismatch
        assert report.outcomes[1].opening_closing_mismatch == 1

    async def test_consistent_opening_not_counted(
        self, test_db: Path, tmp_path: Path, mock_extract, mock_summary
    ) -> None:
        pid = await _seed_project()
        mock_extract.side_effect = lambda body, project_id, chapter_number, *args, **kwargs: (
            self._numerical(pid, 0.0, 100.0)
            if chapter_number == 1
            else self._numerical(pid, 100.0, 120.0)
        )
        manifest_path = _confirmed_manifest(tmp_path)

        report = await replay_import("proj-1", manifest_path)

        assert all(o.opening_closing_mismatch == 0 for o in report.outcomes)

    async def test_first_chapter_only_never_counted(
        self, test_db: Path, tmp_path: Path, mock_extract, mock_summary
    ) -> None:
        pid = await _seed_project()
        mock_extract.side_effect = lambda *args, **kwargs: self._numerical(
            pid, 999.0, 1000.0
        )
        manifest_path = _confirmed_manifest(tmp_path)

        report = await replay_import("proj-1", manifest_path, chapters={1})

        assert report.outcomes[0].opening_closing_mismatch == 0


class TestRenderTextHGroup:
    """render_text H 组观察段：有计数时列出（逐章明细仅非零章），全零省略."""

    def test_h_group_rendered_with_counts(self) -> None:
        report = ReplayReport(
            run_id="run-h",
            project_id="proj-1",
            outcomes=[
                ChapterReplayOutcome(
                    chapter_number=1,
                    title="第一章",
                    status="applied",
                    observation_counts={"setting_duplicate_recycled": 1},
                ),
                ChapterReplayOutcome(
                    chapter_number=2,
                    title="第二章",
                    status="applied",
                    observation_counts={
                        "setting_duplicate_recycled": 2,
                        "foreshadowing_resolve_missing_id": 1,
                    },
                    opening_closing_mismatch=1,
                ),
                ChapterReplayOutcome(
                    chapter_number=3,
                    title="第三章",
                    status="skipped",
                ),
            ],
        )
        text = report.render_text()
        assert "H 组观察项" in text
        assert "setting_duplicate_recycled" in text
        assert "共 3" in text
        assert "foreshadowing_resolve_missing_id" in text
        assert "opening_closing_mismatch" in text
        # 逐章明细仅列非零章：skipped 的第 3 章（全零）不出现在明细
        h_section = text.split("H 组观察项", 1)[1]
        assert "第 1 章" in h_section
        assert "第 2 章" in h_section
        assert "第 3 章" not in h_section

    def test_h_group_omitted_when_all_zero(self) -> None:
        report = ReplayReport(
            run_id="run-zero",
            project_id="proj-1",
            outcomes=[
                ChapterReplayOutcome(
                    chapter_number=1, title="第一章", status="applied"
                )
            ],
        )
        text = report.render_text()
        assert "H 组" not in text
        assert "opening_closing_mismatch" not in text
