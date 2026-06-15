"""Tests for RandomConsistencyTest engine."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from evals.consistency_test import (
    ConsistencyTestReport,
    ForeshadowingResult,
    InventoryTrackingResult,
    RandomConsistencyTest,
    SettingConsistencyResult,
    _keyword_in_content,
    _quick_ratio,
)
from songyan.models import ChapterHead, ChapterVersion, ForeshadowingItem

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_head(chapter_number: int, accepted_version_id: str) -> ChapterHead:
    return ChapterHead(
        project_id="p1",
        chapter_number=chapter_number,
        accepted_version_id=accepted_version_id,
        status="accepted",
    )


def _make_version(version_id: str, content: str) -> ChapterVersion:
    return ChapterVersion(
        version_id=version_id,
        project_id="p1",
        chapter_number=1,
        version_number=1,
        version_type="accepted",
        content=content,
        word_count=len(content),
    )


# ---------------------------------------------------------------------------
# Text scanning helpers
# ---------------------------------------------------------------------------


class TestKeywordInContent:
    def test_exact_match(self) -> None:
        assert _keyword_in_content("灵石", "他取出一枚灵石开始吸收") is True

    def test_no_match(self) -> None:
        assert _keyword_in_content("灵石", "这是一段无关文字") is False

    def test_empty_keyword_passes(self) -> None:
        assert _keyword_in_content("", "任何内容") is True

    def test_fuzzy_match(self) -> None:
        # 相似但非精确匹配
        assert _keyword_in_content("灵气涌", "灵气涌入体内") is True


class TestQuickRatio:
    def test_identical(self) -> None:
        assert _quick_ratio("abc", "abc") == 1.0

    def test_completely_different(self) -> None:
        assert _quick_ratio("abc", "xyz") == 0.0

    def test_partial_overlap(self) -> None:
        ratio = _quick_ratio("abcd", "abce")
        assert 0.0 < ratio < 1.0


# ---------------------------------------------------------------------------
# Data model tests
# ---------------------------------------------------------------------------


class TestConsistencyTestReport:
    def test_overall_recall_rate_empty(self) -> None:
        report = ConsistencyTestReport("p1", 5, [], [], [])
        assert report.overall_recall_rate == 0.0

    def test_overall_recall_rate_settings_only(self) -> None:
        results = [
            SettingConsistencyResult("k1", "n1", 1, None, [2], [3], 0.5),
            SettingConsistencyResult("k2", "n2", 1, None, [2, 3], [], 1.0),
        ]
        report = ConsistencyTestReport("p1", 5, results, [], [])
        assert report.overall_recall_rate == 0.75

    def test_overall_recall_rate_weighted(self) -> None:
        settings = [SettingConsistencyResult("k1", "n1", 1, None, [], [2], 0.0)]
        inventory = [InventoryTrackingResult("item", "c1", 1, [2], [], 1.0)]
        report = ConsistencyTestReport("p1", 5, settings, inventory, [])
        # (0.0 * 1 + 1.0 * 1) / 2 = 0.5
        assert report.overall_recall_rate == 0.5

    def test_overall_score_with_foreshadowing(self) -> None:
        settings = [SettingConsistencyResult("k1", "n1", 1, None, [2], [], 1.0)]
        fs = [ForeshadowingResult("fs1", "desc", 1, 5, True, False)]
        report = ConsistencyTestReport("p1", 5, settings, [], fs)
        # recall=1.0, fs_rate=1.0 -> 1.0*7 + 1.0*3 = 10.0
        assert report.overall_score == 10.0

    def test_foreshadowing_recovery_rate_none(self) -> None:
        fs = [ForeshadowingResult("fs1", "desc", 1, None, False, False)]
        report = ConsistencyTestReport("p1", 5, [], [], fs)
        assert report.foreshadowing_recovery_rate is None

    def test_foreshadowing_recovery_rate_50(self) -> None:
        fs = [
            ForeshadowingResult("fs1", "desc", 1, 5, True, False),
            ForeshadowingResult("fs2", "desc", 1, 5, False, True),
        ]
        report = ConsistencyTestReport("p1", 5, [], [], fs)
        assert report.foreshadowing_recovery_rate == 0.5


# ---------------------------------------------------------------------------
# RandomConsistencyTest engine tests
# ---------------------------------------------------------------------------


class TestRandomConsistencyTest:
    @pytest.fixture
    def engine(self) -> RandomConsistencyTest:
        return RandomConsistencyTest(
            setting_repo=AsyncMock(),
            inventory_repo=AsyncMock(),
            foreshadowing_repo=AsyncMock(),
            version_repo=AsyncMock(),
            head_repo=AsyncMock(),
        )

    async def test_empty_project(self, engine: RandomConsistencyTest) -> None:
        engine.head_repo.list_by_project.return_value = []
        report = await engine.run("p1", sample_count=5)
        assert report.overall_recall_rate == 0.0
        assert report.setting_results == []

    async def test_setting_consistency_recall(self, engine: RandomConsistencyTest) -> None:
        # Ch1: 引入设定 "灵石"
        # Ch2: 提及灵石
        # Ch3: 未提及
        engine.head_repo.list_by_project.return_value = [
            _make_head(1, "v1"),
            _make_head(2, "v2"),
            _make_head(3, "v3"),
        ]
        engine.version_repo.get.side_effect = [
            _make_version("v1", "主角发现了一枚灵石"),
            _make_version("v2", "他用灵石修炼"),
            _make_version("v3", " unrelated content "),
        ]
        engine.setting_repo.list_by_project.return_value = [
            {
                "setting_key": "spirit_stone",
                "setting_name": "灵石",
                "introduced_in_chapter": 1,
                "last_mentioned_chapter": None,
            }
        ]
        engine.inventory_repo.list_by_project.return_value = []
        engine.foreshadowing_repo.list_all.return_value = []

        report = await engine.run("p1", sample_count=5)
        assert len(report.setting_results) == 1
        result = report.setting_results[0]
        assert result.recall_rate == 0.5  # 1 recall (ch2) / 2 total (ch2, ch3)
        assert result.recall_chapters == [2]
        assert result.missed_chapters == [3]

    async def test_inventory_tracking(self, engine: RandomConsistencyTest) -> None:
        engine.head_repo.list_by_project.return_value = [
            _make_head(1, "v1"),
            _make_head(2, "v2"),
        ]
        engine.version_repo.get.side_effect = [
            _make_version("v1", "他获得了一把古剑"),
            _make_version("v2", "古剑发出光芒"),
        ]
        engine.setting_repo.list_by_project.return_value = []
        engine.inventory_repo.list_by_project.return_value = [
            {
                "item_name": "古剑",
                "character_id": "c1",
                "acquired_in_chapter": 1,
            }
        ]
        engine.foreshadowing_repo.list_all.return_value = []

        report = await engine.run("p1", sample_count=5)
        assert len(report.inventory_results) == 1
        assert report.inventory_results[0].recall_rate == 1.0

    async def test_foreshadowing_resolved(self, engine: RandomConsistencyTest) -> None:
        engine.head_repo.list_by_project.return_value = [_make_head(1, "v1")]
        engine.version_repo.get.return_value = _make_version("v1", "content")
        engine.setting_repo.list_by_project.return_value = []
        engine.inventory_repo.list_by_project.return_value = []
        engine.foreshadowing_repo.list_all.return_value = [
            ForeshadowingItem(
                foreshadowing_id="fs1",
                description="上古遗迹",
                planted_in_chapter=1,
                expected_resolve_chapter=3,
                status="resolved",
            )
        ]

        report = await engine.run("p1", sample_count=5)
        assert len(report.foreshadowing_results) == 1
        assert report.foreshadowing_results[0].resolved is True
        assert report.foreshadowing_results[0].overdue is False

    async def test_foreshadowing_overdue(self, engine: RandomConsistencyTest) -> None:
        engine.head_repo.list_by_project.return_value = [
            _make_head(1, "v1"),
            _make_head(2, "v2"),
            _make_head(3, "v3"),
            _make_head(4, "v4"),
        ]
        engine.version_repo.get.return_value = _make_version("v1", "content")
        engine.setting_repo.list_by_project.return_value = []
        engine.inventory_repo.list_by_project.return_value = []
        engine.foreshadowing_repo.list_all.return_value = [
            ForeshadowingItem(
                foreshadowing_id="fs1",
                description="上古遗迹",
                planted_in_chapter=1,
                expected_resolve_chapter=3,
                status="planted",
            )
        ]

        report = await engine.run("p1", sample_count=5)
        assert report.foreshadowing_results[0].overdue is True

    async def test_reproducible_sampling(self, engine: RandomConsistencyTest) -> None:
        """相同 project_id 应产生相同的抽样结果."""
        from itertools import cycle

        engine.head_repo.list_by_project.return_value = [
            _make_head(i, f"v{i}") for i in range(1, 11)
        ]
        engine.version_repo.get.side_effect = cycle([
            _make_version(f"v{i}", f"content {i}") for i in range(1, 11)
        ])
        engine.setting_repo.list_by_project.return_value = [
            {
                "setting_key": f"key_{i}",
                "setting_name": f"name_{i}",
                "introduced_in_chapter": i,
                "last_mentioned_chapter": None,
            }
            for i in range(1, 11)
        ]
        engine.inventory_repo.list_by_project.return_value = []
        engine.foreshadowing_repo.list_all.return_value = []

        report1 = await engine.run("same_seed", sample_count=3)
        report2 = await engine.run("same_seed", sample_count=3)

        keys1 = [r.setting_key for r in report1.setting_results]
        keys2 = [r.setting_key for r in report2.setting_results]
        assert keys1 == keys2

    async def test_different_seed_different_samples(self, engine: RandomConsistencyTest) -> None:
        """不同 project_id 应产生不同的抽样结果（高概率）."""
        from itertools import cycle

        engine.head_repo.list_by_project.return_value = [
            _make_head(i, f"v{i}") for i in range(1, 21)
        ]
        engine.version_repo.get.side_effect = cycle([
            _make_version(f"v{i}", f"content {i}") for i in range(1, 21)
        ])
        engine.setting_repo.list_by_project.return_value = [
            {
                "setting_key": f"key_{i}",
                "setting_name": f"name_{i}",
                "introduced_in_chapter": i,
                "last_mentioned_chapter": None,
            }
            for i in range(1, 21)
        ]
        engine.inventory_repo.list_by_project.return_value = []
        engine.foreshadowing_repo.list_all.return_value = []

        report1 = await engine.run("seed_a", sample_count=5)
        report2 = await engine.run("seed_b", sample_count=5)

        keys1 = [r.setting_key for r in report1.setting_results]
        keys2 = [r.setting_key for r in report2.setting_results]
        # 20 个样本中随机抽 5 个，两个不同 seed 结果相同的概率极低
        assert keys1 != keys2
