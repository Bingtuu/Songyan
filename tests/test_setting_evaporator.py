"""Task 103: SettingEvaporator — 设定蒸发器测试."""

from __future__ import annotations

import pytest

import songyan.agents.setting_evaporator as setting_evaporator
from songyan.agents.setting_evaporator import (
    CONFIDENCE_ARCHIVE_THRESHOLD,
    MERGE_SIMILARITY_THRESHOLD,
    SettingEvaporator,
    _calculate_resolve_confidence,
)
from songyan.models import ChapterGoal


class TestCalculateResolveConfidence:
    """测试 resolve_confidence 计算逻辑."""

    def test_critical_category_never_low(self) -> None:
        """critical 类别设定 confidence 较高，不会低于阈值."""
        row = {
            "setting_name": "天道法则",
            "setting_key": "heavenly_dao",
            "last_mentioned_chapter": 1,
            "category": "critical",
        }
        conf = _calculate_resolve_confidence(row, current_chapter=60, chapter_goal=None)
        # hard_factor = 1.0 → confidence >= 0.2
        assert conf >= 0.2
        # time_factor ≈ 0，relevance=0.3 → conf = 0.5*0 + 0.3*0.3 + 0.2*1.0 = 0.29
        # 即使 last_mentioned 很早，critical 也能保 confidence

    def test_recently_mentioned_high_confidence(self) -> None:
        """最近引用的设定 confidence 高."""
        row = {
            "setting_name": "新法宝",
            "setting_key": "new_treasure",
            "last_mentioned_chapter": 58,
            "category": "background",
        }
        conf = _calculate_resolve_confidence(row, current_chapter=60, chapter_goal=None)
        # time_factor = 1 - 2/50 = 0.96, relevance=0.3
        # conf = 0.5*0.96 + 0.3*0.3 + 0.2*0 = 0.48 + 0.09 = 0.57
        assert conf > 0.5

    def test_long_unmentioned_low_confidence(self) -> None:
        """长期未引用的设定 confidence 低."""
        row = {
            "setting_name": "旧设定",
            "setting_key": "old_setting",
            "last_mentioned_chapter": 10,
            "category": "background",
        }
        conf = _calculate_resolve_confidence(row, current_chapter=60, chapter_goal=None)
        # time_factor = 1 - 50/50 = 0, relevance=0.3
        # conf = 0.5*0 + 0.3*0.3 + 0.2*0 = 0.09
        assert conf < CONFIDENCE_ARCHIVE_THRESHOLD

    def test_keyword_relevance_boosts_confidence(self) -> None:
        """target_events 重叠提升 relevance（ChapterGoal 无 keywords 字段）."""
        row = {
            "setting_name": "黑木崖最终决战",
            "setting_key": "black_cliff_battle",
            "last_mentioned_chapter": 30,
            "category": "background",
        }
        goal = ChapterGoal(
            chapter_number=60,
            target_events=["黑木崖最终决战", "黑木崖"],
            obligations=["决战准备"],
        )
        conf = _calculate_resolve_confidence(row, current_chapter=60, chapter_goal=goal)
        # hard_factor = 1.0（setting_name 在 target_events 中）
        # conf = 0.5*0.4 + 0.3*0.3 + 0.2*1.0 = 0.49
        assert conf >= 0.4

    def test_hard_constraint_via_keywords(self) -> None:
        """setting_name 出现在 target_events 中 → hard_constraint."""
        row = {
            "setting_name": "天道碎片",
            "setting_key": "dao_fragment",
            "last_mentioned_chapter": 10,
            "category": "background",
        }
        goal = ChapterGoal(
            chapter_number=60,
            target_events=["寻找天道碎片"],
            obligations=[],
        )
        conf = _calculate_resolve_confidence(row, current_chapter=60, chapter_goal=goal)
        # hard_factor = 1.0，即使时间衰减到 0，conf >= 0.2
        assert conf >= 0.2

    def test_no_last_mentioned_defaults(self) -> None:
        """last_mentioned_chapter 缺失时使用 0."""
        row = {
            "setting_name": "无引用设定",
            "setting_key": "no_ref",
        }
        conf = _calculate_resolve_confidence(row, current_chapter=60, chapter_goal=None)
        # chapters_since = 60, time_factor = 0, relevance=0.3
        assert conf == 0.09


class TestSettingEvaporatorUnit:
    """测试 SettingEvaporator 行为（mock repo，无需 DB）."""

    @pytest.mark.asyncio
    async def test_run_archives_low_confidence(self, monkeypatch) -> None:
        """低 confidence 设定被 archive."""
        evap = SettingEvaporator()

        # Mock repo.list_active_with_tracking
        mock_settings = [
            {
                "setting_name": "旧设定A",
                "setting_key": "old_a",
                "last_mentioned_chapter": 10,
                "category": "background",
                "created_at": "2024-01-01",
            },
            {
                "setting_name": "新设定B",
                "setting_key": "new_b",
                "last_mentioned_chapter": 58,
                "category": "background",
                "created_at": "2024-06-01",
            },
        ]
        archived_keys: list[str] = []

        async def mock_list(_pid: str) -> list[dict]:
            return mock_settings

        async def mock_archive(_pid: str, keys: list[str]) -> int:
            archived_keys.extend(keys)
            return len(keys)

        monkeypatch.setattr(evap.repo, "list_active_with_tracking", mock_list)
        monkeypatch.setattr(evap.repo, "archive_by_confidence", mock_archive)

        result = await evap.run(project_id="p1", current_chapter=60)

        assert "old_a" in result
        assert "old_a" in archived_keys
        assert "new_b" not in result
        assert "new_b" not in archived_keys

    @pytest.mark.asyncio
    async def test_run_no_active_settings(self, monkeypatch) -> None:
        """无 active 设定时不 archive."""
        evap = SettingEvaporator()

        async def mock_list(_pid: str) -> list[dict]:
            return []

        monkeypatch.setattr(evap.repo, "list_active_with_tracking", mock_list)

        result = await evap.run(project_id="p1", current_chapter=60)
        assert result == []

    @pytest.mark.asyncio
    async def test_merge_similar_settings(self, monkeypatch) -> None:
        """相似设定合并，保留最早创建的 key."""
        evap = SettingEvaporator()

        mock_settings = [
            {
                "setting_name": "天道法则",
                "setting_key": "heavenly_dao",
                "created_at": "2024-01-01",
            },
            {
                "setting_name": "天道法则",
                "setting_key": "heavenly_dao_duplicate",
                "created_at": "2024-02-01",
            },
        ]
        archived_keys: list[str] = []

        async def mock_archive(_pid: str, keys: list[str]) -> int:
            archived_keys.extend(keys)
            return len(keys)

        monkeypatch.setattr(evap.repo, "archive_by_confidence", mock_archive)

        merged = await evap.merge_similar_settings(
            project_id="p1",
            settings=mock_settings,
            similarity_threshold=MERGE_SIMILARITY_THRESHOLD,
        )

        # 完全相同的 setting_name，关键词重叠度 = 1.0
        assert len(merged) == 1
        drop, keep = merged[0]
        # 保留最早创建的
        assert keep == "heavenly_dao"
        assert drop == "heavenly_dao_duplicate"
        assert drop in archived_keys

    @pytest.mark.asyncio
    async def test_merge_no_similar(self, monkeypatch) -> None:
        """无相似设定时不合并."""
        evap = SettingEvaporator()

        mock_settings = [
            {
                "setting_name": "火焰山",
                "setting_key": "flame_mountain",
                "created_at": "2024-01-01",
            },
            {
                "setting_name": "东海龙宫",
                "setting_key": "dragon_palace",
                "created_at": "2024-02-01",
            },
        ]

        merged = await evap.merge_similar_settings(
            project_id="p1",
            settings=mock_settings,
            similarity_threshold=MERGE_SIMILARITY_THRESHOLD,
        )

        assert merged == []

    @pytest.mark.asyncio
    async def test_merge_does_not_re_archive(self, monkeypatch) -> None:
        """已标记为 archive 的 key 不会被重复处理."""
        evap = SettingEvaporator()

        mock_settings = [
            {
                "setting_name": "天道法则",
                "setting_key": "dao_1",
                "created_at": "2024-01-01",
            },
            {
                "setting_name": "天道法则",
                "setting_key": "dao_1_duplicate",
                "created_at": "2024-02-01",
            },
            {
                "setting_name": "天道法则",
                "setting_key": "dao_1_copy",
                "created_at": "2024-03-01",
            },
        ]
        archived_keys: list[str] = []

        async def mock_archive(_pid: str, keys: list[str]) -> int:
            archived_keys.extend(keys)
            return len(keys)

        monkeypatch.setattr(evap.repo, "archive_by_confidence", mock_archive)

        merged = await evap.merge_similar_settings(
            project_id="p1",
            settings=mock_settings,
            similarity_threshold=MERGE_SIMILARITY_THRESHOLD,
        )

        # dao_1 与 dao_1_duplicate 合并，dao_1 与 dao_1_copy 也可能合并
        # 但 dao_1_duplicate 已被 archive，不应再被考虑
        assert len(merged) >= 1
        # 确保没有重复的 drop key
        drops = [drop for drop, _ in merged]
        assert len(drops) == len(set(drops))

    @pytest.mark.asyncio
    async def test_merge_uses_bucket_and_recent_window(self, monkeypatch) -> None:
        """合并扫描不再对全部 active settings 做无条件两两比较."""
        evap = SettingEvaporator()
        mock_settings = [
            {
                "setting_name": f"设定{i}",
                "setting_key": f"cat{i % 10}.group{i % 5}.setting{i}",
                "category": f"cat{i % 10}",
                "created_at": f"2024-01-{i % 28 + 1:02d}",
                "last_mentioned_chapter": 1,
            }
            for i in range(120)
        ]
        mock_settings.append(
            {
                "setting_name": "天道法则",
                "setting_key": "critical.dao.source",
                "category": "critical",
                "created_at": "2024-01-01",
                "last_mentioned_chapter": 95,
            }
        )
        mock_settings.append(
            {
                "setting_name": "天道法则",
                "setting_key": "critical.dao.duplicate",
                "category": "critical",
                "created_at": "2024-02-01",
                "last_mentioned_chapter": 100,
            }
        )
        calls = 0
        archived_keys: list[str] = []

        def fake_overlap(*_args: object) -> float:
            nonlocal calls
            calls += 1
            return 1.0

        async def mock_archive(_pid: str, keys: list[str]) -> int:
            archived_keys.extend(keys)
            return len(keys)

        monkeypatch.setattr(setting_evaporator, "_compute_keyword_overlap", fake_overlap)
        monkeypatch.setattr(evap.repo, "archive_by_confidence", mock_archive)

        merged = await evap.merge_similar_settings(
            project_id="p1",
            settings=mock_settings,
            current_chapter=100,
            source_window=10,
        )

        full_pair_overlap_calls = len(mock_settings) * (len(mock_settings) - 1)
        assert calls < full_pair_overlap_calls // 10
        assert ("critical.dao.duplicate", "critical.dao.source") in merged
        assert archived_keys == ["critical.dao.duplicate"]
