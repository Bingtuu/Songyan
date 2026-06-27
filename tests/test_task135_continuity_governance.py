"""Task 135: setting recycling and continuity health score governance."""

from __future__ import annotations

from typing import Any

import pytest

from songyan.agents.continuity_auditor import ContinuityAuditor
from songyan.agents.continuity_auditor._scanners import (
    ORPHANED_THRESHOLDS,
    _find_orphaned_settings,
)
from songyan.agents.creative_director import (
    _format_active_settings_to_recycle,
)
from songyan.agents.setting_evaporator import (
    SettingEvaporator,
)
from songyan.models.continuity import OrphanedSetting


class TestHealthScoreGovernance:
    def test_high_orphaned_count_floor_for_early_chapters(self) -> None:
        """Task 135: 早期章节健康分有 3.0 floor，避免快速归零."""
        auditor = ContinuityAuditor()
        orphaned = [
            OrphanedSetting(
                tracking_id=f"t{i}",
                setting_key="k",
                setting_name="n",
                introduced_in_chapter=1,
                last_mentioned_chapter=2,
                chapters_since_mention=10,
                category="critical",
            )
            for i in range(30)
        ]
        score = auditor._compute_health_score(
            orphaned=orphaned,
            forgotten=[],
            mismatches=[],
            overdue=[],
            chapter_number=15,
        )
        assert score >= 3.0

    def test_diminishing_penalty_above_10(self) -> None:
        """超过 10 个同类别 orphaned 后边际扣分递减."""
        auditor = ContinuityAuditor()
        score_10 = auditor._compute_health_score(
            orphaned=[
                OrphanedSetting(
                    tracking_id=f"t{i}", setting_key="k", setting_name="n",
                    introduced_in_chapter=1, last_mentioned_chapter=2,
                    chapters_since_mention=5, category="background",
                )
                for i in range(10)
            ],
            forgotten=[], mismatches=[], overdue=[],
            chapter_number=10,
        )
        score_40 = auditor._compute_health_score(
            orphaned=[
                OrphanedSetting(
                    tracking_id=f"t{i}", setting_key="k", setting_name="n",
                    introduced_in_chapter=1, last_mentioned_chapter=2,
                    chapters_since_mention=5, category="background",
                )
                for i in range(40)
            ],
            forgotten=[], mismatches=[], overdue=[],
            chapter_number=10,
        )
        # 背景扣分权重低，40 个仍不应低于 floor，但衰减应使扣分增长变缓
        assert score_10 == 9.0  # 10 * 0.1 = 1.0
        assert score_40 >= 7.0  # 线性的话会是 6.0；衰减后应更高

    def test_existing_small_counts_unchanged(self) -> None:
        """小数量时保持 Task 094 的既有权重."""
        auditor = ContinuityAuditor()
        score = auditor._compute_health_score(
            orphaned=[
                OrphanedSetting(
                    tracking_id="t1", setting_key="k", setting_name="n",
                    introduced_in_chapter=1, last_mentioned_chapter=2,
                    chapters_since_mention=5, category="critical",
                )
            ],
            forgotten=[], mismatches=[], overdue=[],
            chapter_number=10,
        )
        assert score == 8.0


class TestOrphanThresholdsByCategory:
    @pytest.mark.asyncio
    async def test_find_orphaned_uses_category_thresholds(self) -> None:
        calls: list[tuple[int, list[str] | None]] = []

        class FakeRepo:
            async def find_orphaned(
                self,
                project_id: str,
                up_to_chapter: int,
                threshold: int,
                categories: list[str] | None = None,
            ) -> list[dict]:
                calls.append((threshold, categories))
                return []

        await _find_orphaned_settings("p1", 20, FakeRepo())  # type: ignore[arg-type]

        seen = {(t, tuple(c or [])) for t, c in calls}
        for category, expected in ORPHANED_THRESHOLDS.items():
            assert (expected, (category,)) in seen


class TestSettingEvaporatorThresholds:
    @pytest.mark.asyncio
    async def test_category_thresholds_archive_differently(self, monkeypatch: Any) -> None:
        evap = SettingEvaporator()

        mock_settings = [
            {"setting_name": "A", "setting_key": "critical.a", "category": "critical"},
            {"setting_name": "B", "setting_key": "background.b", "category": "background"},
            {"setting_name": "C", "setting_key": "historical.c", "category": "historical"},
        ]

        async def mock_list(_pid: str) -> list[dict]:
            return mock_settings

        archived_keys: list[str] = []

        async def mock_archive(_pid: str, keys: list[str]) -> int:
            archived_keys.extend(keys)
            return len(keys)

        # 让 critical=0.22（低于 0.25），background=0.14，historical=0.09
        def fake_conf(row: dict, *_args: object, **_kwargs: object) -> float:
            thresholds = {"critical": 0.22, "background": 0.14, "historical": 0.09}
            return thresholds.get(row.get("category"), 0.5)

        monkeypatch.setattr(evap.repo, "list_active_with_tracking", mock_list)
        monkeypatch.setattr(evap.repo, "archive_by_confidence", mock_archive)
        monkeypatch.setattr(
            "songyan.agents.setting_evaporator._calculate_resolve_confidence",
            fake_conf,
        )

        result = await evap.run(project_id="p1", current_chapter=10)

        # critical 0.22 < 0.25 -> archive
        assert "critical.a" in result
        # background 0.14 < 0.15 -> archive
        assert "background.b" in result
        # historical 0.09 < 0.10 -> archive
        assert "historical.c" in result

        # 如果 background 阈值仍是旧的 0.3，则 background.b 不会被 archive；现在应该被 archive
        assert "background.b" in archived_keys


class TestCreativeDirectorRecycleHint:
    def test_format_active_settings_empty(self) -> None:
        assert "无近期活跃设定" in _format_active_settings_to_recycle([])

    def test_format_active_settings_includes_key_and_chapters(self) -> None:
        settings = [
            {
                "setting_name": "测试设定",
                "setting_key": "test.category.example",
                "category": "recurring",
                "introduced_in_chapter": 3,
                "last_mentioned_chapter": 6,
            }
        ]
        rendered = _format_active_settings_to_recycle(settings)
        assert "测试设定" in rendered
        assert "test.category.example" in rendered
        assert "recurring" in rendered
        assert "引入第3章" in rendered
        assert "最近提及第6章" in rendered

    @pytest.mark.asyncio
    async def test_load_active_settings_filters_active_status(self, monkeypatch: Any) -> None:
        from songyan.agents.creative_director import _load_active_settings_to_recycle

        rows = [
            {
                "setting_key": "active.a", "status": "active",
                "introduced_in_chapter": 1, "last_mentioned_chapter": 2,
            },
            {
                "setting_key": "archived.b", "status": "archived",
                "introduced_in_chapter": 1, "last_mentioned_chapter": 2,
            },
        ]

        async def mock_list(_pid: str) -> list[dict]:
            return rows

        monkeypatch.setattr(
            "songyan.agents.creative_director.SettingTrackingRepository.list_by_project",
            staticmethod(mock_list),  # type: ignore[arg-type]
        )
        result = await _load_active_settings_to_recycle("p1", 5)
        assert len(result) == 1
        assert result[0]["setting_key"] == "active.a"


class TestWriterPromptRecycleConstraint:
    def test_writer_110_includes_recycle_constraint(self) -> None:
        from songyan.prompts import get_prompt_loader

        loader = get_prompt_loader()
        card = loader.load_card("writer", version="1.1.0")
        assert "设定回收约束" in card.system_prompt
        assert "禁止让设定“引入即遗忘”" in card.system_prompt

    def test_writer_120_includes_recycle_constraint(self) -> None:
        from songyan.prompts import get_prompt_loader

        loader = get_prompt_loader()
        card = loader.load_card("writer", version="1.2.0")
        assert "设定回收约束" in card.system_prompt
