"""Tests for Task 034: 遗留验证补齐（A3）."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from songyan.agents.arc_summary_generator import (
    auto_generate_arc_summaries,
    generate_arc_summary,
    generate_volume_summary,
)
from songyan.agents.continuity_auditor import ContinuityAuditor
from songyan.db.context_repo import SummaryRepository
from songyan.db.repository import (
    ChapterVersionRepository,
    CharacterRepository,
    ProjectRepository,
)
from songyan.db.review_repo import CreativeBriefRepository
from songyan.evals.punch_metrics import PunchMetrics, evaluate_punch_metrics, save_punch_metrics
from songyan.evals.simulation_50ch import (
    SimulationReport,
    run_50chapter_simulation,
    save_simulation_report,
)
from songyan.models import (
    ChapterGoal,
    ChapterSummary,
    ChapterVersion,
    Character,
    CharacterState,
    CreativeBrief,
    EmotionArcItem,
    ProjectSetting,
    PunchPoint,
)
from songyan.workflows._helpers import new_id

pytestmark = pytest.mark.performance

# ---------------------------------------------------------------------------
# A3-1: Punch Engine 自动评估
# ---------------------------------------------------------------------------


class TestPunchMetrics:
    """Punch Engine 量化评估测试."""

    async def test_evaluate_empty_project(self, test_db: Path) -> None:
        """空项目应返回空列表."""
        metrics = await evaluate_punch_metrics("nonexistent-project")
        assert metrics == []

    async def test_evaluate_with_creative_briefs(self, test_db: Path) -> None:
        """有 creative_briefs 数据时应正确计算指标."""
        project_id = new_id("proj")
        await ProjectRepository().create(
            ProjectSetting(
                title="测试项目",
                genre_id="scifi",
                mode_id="webnovel",
                protagonist_name="主角",
            ),
            project_id,
        )
        # 插入 creative_brief
        brief = CreativeBrief(
            mode_id="webnovel_intense",
            chapter_goal=ChapterGoal(chapter_number=2, word_count_target=3000),
            punch_points=[
                PunchPoint(
                    punch_id="p1", description="刺激点1",
                    punch_type="revelation", target_scene=1,
                ),
            ],
            emotion_arc=[
                EmotionArcItem(scene=1, from_emotion="紧张", to_emotion="震惊"),
                EmotionArcItem(scene=2, from_emotion="震惊", to_emotion="恐惧"),
            ],
        )
        await CreativeBriefRepository().create(brief, new_id("brief"), project_id, 2)

        # 插入 chapter_version（用于字数统计）
        version = ChapterVersion(
            version_id=new_id("v"),
            project_id=project_id,
            chapter_number=2,
            version_number=1,
            version_type="accepted",
            content="测试内容" * 100,
            word_count=3000,
        )
        await ChapterVersionRepository().create(version)

        metrics = await evaluate_punch_metrics(project_id)
        assert len(metrics) == 1
        m = metrics[0]
        assert m.chapter_number == 2
        assert m.punch_count == 1
        assert m.emotion_switches == 2
        assert m.punch_density > 0
        assert m.emotion_switch_rate > 0

    def test_save_punch_metrics(self, tmp_path: Path) -> None:
        """保存 JSON 文件."""
        metrics = [
            PunchMetrics(chapter_number=1, word_count=3000, punch_count=2, emotion_switches=3),
        ]
        path = save_punch_metrics(metrics, tmp_path / "test_punch.json")
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["total_chapters"] == 1
        assert data["chapters"][0]["chapter_number"] == 1


# ---------------------------------------------------------------------------
# A3-2: ContinuityAuditor state_mismatches
# ---------------------------------------------------------------------------


class TestStateMismatches:
    """角色状态矛盾检测测试."""

    async def test_no_mismatch_single_state(self, test_db: Path) -> None:
        """单条状态记录不应触发 mismatch."""
        auditor = ContinuityAuditor()
        mismatches = await auditor._find_state_mismatches("proj-1", 10)
        assert mismatches == []

    async def test_detect_location_jump(self, test_db: Path) -> None:
        """检测角色位置在短时间内跳变."""
        project_id = new_id("proj")
        char_id = new_id("char")

        # 创建项目
        await ProjectRepository().create(
            ProjectSetting(
                title="测试项目",
                genre_id="scifi",
                mode_id="webnovel",
                protagonist_name="林渊",
            ),
            project_id,
        )

        # 创建角色
        await CharacterRepository().create(
            Character(
                character_id=char_id,
                project_id=project_id,
                name="林渊",
                role_type="protagonist",
            )
        )

        # 插入两个 version（第2章和第3章）
        v2 = ChapterVersion(
            version_id=new_id("v"),
            project_id=project_id,
            chapter_number=2,
            version_number=1,
            version_type="accepted",
            content="ch2",
            word_count=100,
        )
        v3 = ChapterVersion(
            version_id=new_id("v"),
            project_id=project_id,
            chapter_number=3,
            version_number=1,
            version_type="accepted",
            content="ch3",
            word_count=100,
        )
        await ChapterVersionRepository().create(v2)
        await ChapterVersionRepository().create(v3)

        # 第2章：林渊在实验室
        await CharacterRepository().add_state_snapshot(
            CharacterState(
                character_id=char_id,
                field="location",
                value="实验室",
                source_version_id=v2.version_id,
            )
        )
        # 第3章：林渊在太空站（1章内跳变，应触发 mismatch）
        await CharacterRepository().add_state_snapshot(
            CharacterState(
                character_id=char_id,
                field="location",
                value="太空站",
                source_version_id=v3.version_id,
            )
        )

        auditor = ContinuityAuditor()
        mismatches = await auditor._find_state_mismatches(project_id, 10)

        assert len(mismatches) >= 1
        mm = mismatches[0]
        assert mm.character_id == char_id
        assert mm.field == "location"
        assert mm.value_a == "实验室"
        assert mm.value_b == "太空站"
        assert mm.chapter_a == 2
        assert mm.chapter_b == 3

    async def test_no_mismatch_same_value(self, test_db: Path) -> None:
        """值不变不应触发 mismatch."""
        project_id = new_id("proj")
        char_id = new_id("char")

        await ProjectRepository().create(
            ProjectSetting(
                title="测试项目",
                genre_id="scifi",
                mode_id="webnovel",
                protagonist_name="林渊",
            ),
            project_id,
        )
        await CharacterRepository().create(
            Character(
                character_id=char_id,
                project_id=project_id,
                name="林渊",
                role_type="protagonist",
            )
        )

        v2 = ChapterVersion(
            version_id=new_id("v"),
            project_id=project_id,
            chapter_number=2,
            version_number=1,
            version_type="accepted",
            content="ch2",
            word_count=100,
        )
        v4 = ChapterVersion(
            version_id=new_id("v"),
            project_id=project_id,
            chapter_number=4,
            version_number=1,
            version_type="accepted",
            content="ch4",
            word_count=100,
        )
        await ChapterVersionRepository().create(v2)
        await ChapterVersionRepository().create(v4)

        await CharacterRepository().add_state_snapshot(
            CharacterState(
                character_id=char_id,
                field="location",
                value="实验室",
                source_version_id=v2.version_id,
            )
        )
        await CharacterRepository().add_state_snapshot(
            CharacterState(
                character_id=char_id,
                field="location",
                value="实验室",
                source_version_id=v4.version_id,
            )
        )

        auditor = ContinuityAuditor()
        mismatches = await auditor._find_state_mismatches(project_id, 10)
        assert mismatches == []


# ---------------------------------------------------------------------------
# A3-3: Arc/Volume 摘要自动生成
# ---------------------------------------------------------------------------


class TestArcSummaryGenerator:
    """Arc/Volume 摘要生成测试."""

    _ARC_LLM_RESPONSE = json.dumps({
        "arc_title": "觉醒篇",
        "arc_summary": "主角在这一弧中经历了重大转变，从普通人成长为觉醒者。",
        "key_events": ["事件1-A", "事件2-B"],
        "resolved_threads": [],
        "new_threads": ["新线索"],
        "character_arcs": {"林渊": "从普通人觉醒为战士"},
    })

    _VOLUME_LLM_RESPONSE = json.dumps({
        "volume_title": "第一卷：觉醒",
        "volume_summary": "主角从平凡世界踏入非凡之路，经历了初次觉醒和试炼。",
        "major_revelations": ["世界真相揭露"],
        "world_state": "世界处于混乱与秩序交替之中",
    })

    async def test_generate_arc_summary(self, test_db: Path) -> None:
        """基于 ChapterSummary 生成 Arc 摘要."""
        project_id = new_id("proj")
        await ProjectRepository().create(
            ProjectSetting(
                title="测试项目",
                genre_id="scifi",
                mode_id="webnovel",
                protagonist_name="主角",
            ),
            project_id,
        )

        # 插入 summaries
        repo = SummaryRepository()
        for i in range(1, 6):
            summary = ChapterSummary(
                chapter_number=i,
                summary=f"第{i}章的剧情摘要。",
                key_events=[f"事件{i}-A", f"事件{i}-B"],
                characters_appeared=["林渊"],
                impact_score=0.3,
            )
            await repo.create(summary, project_id, new_id("sum"))

        with patch(
            "songyan.agents.arc_summary_generator.call_llm",
            new_callable=AsyncMock,
            return_value=self._ARC_LLM_RESPONSE,
        ):
            arc = await generate_arc_summary(project_id, 1, 5)

        assert arc.arc_title == "觉醒篇"
        assert arc.arc_summary != ""
        assert len(arc.key_events) >= 2
        assert "林渊" in arc.character_arcs

    async def test_generate_volume_summary(self, test_db: Path) -> None:
        """基于 ArcSummary 生成 Volume 摘要."""
        project_id = new_id("proj")
        await ProjectRepository().create(
            ProjectSetting(
                title="测试项目",
                genre_id="scifi",
                mode_id="webnovel",
                protagonist_name="主角",
            ),
            project_id,
        )

        # 先创建 summaries
        repo = SummaryRepository()
        for i in range(1, 11):
            summary = ChapterSummary(
                chapter_number=i,
                summary=f"第{i}章摘要。",
                key_events=[f"事件{i}"],
                characters_appeared=["主角"],
                impact_score=0.5,
            )
            await repo.create(summary, project_id, new_id("sum"))

        # 创建 ArcSummary（为 Volume 摘要提供上游数据）
        with patch(
            "songyan.agents.arc_summary_generator.call_llm",
            new_callable=AsyncMock,
            return_value=self._ARC_LLM_RESPONSE,
        ):
            await generate_arc_summary(project_id, 1, 5)

        # 生成 Volume 摘要
        with patch(
            "songyan.agents.arc_summary_generator.call_llm",
            new_callable=AsyncMock,
            return_value=self._VOLUME_LLM_RESPONSE,
        ):
            volume = await generate_volume_summary(project_id, 1, 10)

        assert volume.volume_title == "第一卷：觉醒"
        assert volume.volume_summary != ""
        assert len(volume.major_revelations) >= 0

    async def test_auto_generate_arc_summaries(self, test_db: Path) -> None:
        """根据边界自动生成多个 Arc."""
        project_id = new_id("proj")
        await ProjectRepository().create(
            ProjectSetting(
                title="测试项目",
                genre_id="scifi",
                mode_id="webnovel",
                protagonist_name="主角",
            ),
            project_id,
        )

        repo = SummaryRepository()
        for i in range(1, 16):
            summary = ChapterSummary(
                chapter_number=i,
                summary=f"第{i}章。",
                key_events=[],
                impact_score=0.2,
            )
            await repo.create(summary, project_id, new_id("sum"))

        with patch(
            "songyan.agents.arc_summary_generator.call_llm",
            new_callable=AsyncMock,
            return_value=self._ARC_LLM_RESPONSE,
        ):
            arcs = await auto_generate_arc_summaries(project_id, arc_boundaries=[5, 10, 15])

        assert len(arcs) == 3
        assert arcs[0].start_chapter == 1
        assert arcs[0].end_chapter == 5
        assert arcs[1].start_chapter == 6
        assert arcs[1].end_chapter == 10
        assert arcs[2].start_chapter == 11
        assert arcs[2].end_chapter == 15


# ---------------------------------------------------------------------------
# A3-4: 50 章模拟测试
# ---------------------------------------------------------------------------


class TestSimulation50Ch:
    """50 章模拟测试."""

    def test_run_simulation(self) -> None:
        """运行 50 章模拟，验证 budget_used 和保留率."""
        report = run_50chapter_simulation(
            real_chapters=10,
            simulated_chapters=40,
            budget_tokens=8000,
        )

        assert report.total_chapters == 50
        assert report.budget_used <= 1.0, (
            f"budget_used={report.budget_used} exceeds 1.0"
        )
        assert report.retention_rate >= 0.9, (
            f"retention_rate={report.retention_rate} below 0.9"
        )
        assert report.critical_loss_count == 0

    def test_simulation_report_model(self) -> None:
        """SimulationReport 模型测试."""
        report = SimulationReport(
            total_chapters=50,
            budget_used=0.85,
            retention_rate=0.95,
            critical_loss_count=0,
            open_thread_count=5,
            permanent_scene_count=3,
        )
        data = report.to_dict()
        assert data["budget_ok"] is True
        assert data["retention_ok"] is True
        assert data["budget_used"] == 0.85

    def test_save_simulation_report(self, tmp_path: Path) -> None:
        """保存模拟报告."""
        report = SimulationReport(
            total_chapters=50,
            budget_used=0.8,
            retention_rate=0.92,
            critical_loss_count=0,
            open_thread_count=5,
            permanent_scene_count=3,
        )
        path = save_simulation_report(report, tmp_path / "sim.json")
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["total_chapters"] == 50
        assert data["budget_ok"] is True
