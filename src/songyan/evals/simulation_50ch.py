"""50 章模拟测试 — 验证分层上下文的 budget_used 和保留率."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import structlog

from songyan.agents.context_manager import BudgetPruner
from songyan.models import (
    ArcSummary,
    ChapterGoal,
    ChapterSummary,
    ContextPackage,
    GenreRules,
    ModeRules,
    OpenThread,
    PermanentScene,
    RecentPlot,
    SoftReference,
    VolumeSummary,
)

logger = structlog.get_logger(__name__)

DEFAULT_OUTPUT_DIR = Path("evals/output")


class SimulationReport:
    """50 章模拟测试报告."""

    def __init__(
        self,
        total_chapters: int,
        budget_used: float,
        retention_rate: float,
        critical_loss_count: int,
        open_thread_count: int,
        permanent_scene_count: int,
    ) -> None:
        self.total_chapters = total_chapters
        self.budget_used = budget_used
        self.retention_rate = retention_rate
        self.critical_loss_count = critical_loss_count
        self.open_thread_count = open_thread_count
        self.permanent_scene_count = permanent_scene_count

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_chapters": self.total_chapters,
            "budget_used": round(self.budget_used, 3),
            "retention_rate": round(self.retention_rate, 3),
            "critical_loss_count": self.critical_loss_count,
            "open_thread_count": self.open_thread_count,
            "permanent_scene_count": self.permanent_scene_count,
            "budget_ok": self.budget_used <= 1.0,
            "retention_ok": self.retention_rate >= 0.9,
        }


def _build_mock_context_package(chapter_number: int) -> ContextPackage:
    """构造模拟的 ContextPackage（随 chapter_number 增长规模）."""
    # 基础组件
    goal = ChapterGoal(
        chapter_number=chapter_number,
        previous_summary=f"第{chapter_number-1}章结束时的剧情摘要...",
        target_events=["事件A", "事件B"],
        word_count_target=3000,
    )

    # recent_plot: 3 章精细摘要（固定规模）
    recent_summaries = [
        ChapterSummary(
            chapter_number=chapter_number - i,
            summary=f"第{chapter_number - i}章的剧情摘要，包含足够长度的文本以模拟真实场景。",
            key_events=[f"事件{chapter_number - i}-A"],
            impact_score=0.3 + (i * 0.1),
        )
        for i in range(1, 4)
        if chapter_number - i > 0
    ]
    recent_plot = RecentPlot(
        summaries=recent_summaries,
        last_chapter_ending=f"第{chapter_number-1}章结尾...",
    )

    # soft_references: 随 chapter_number 线性增长（模拟累积效应）
    soft_refs = [
        SoftReference(
            type="world_setting",
            content=f"设定{i}: 这是一个世界设定描述...",
            relevance_score=0.5,
            last_mentioned_chapter=max(1, chapter_number - i * 2),
            is_critical=(i == 0),
        )
        for i in range(min(chapter_number // 2, 20))
    ]

    # open_threads: 随 chapter_number 增长
    open_threads = [
        OpenThread(
            thread_id=f"thread-{i}",
            description=f"未完结线索{i}的描述...",
            source_type="foreshadowing",
            source_chapter=max(1, chapter_number - i * 3),
            priority=0.5 + (i % 3) * 0.1,
        )
        for i in range(min(chapter_number // 3, 10))
    ]

    # permanent_scenes: 高 impact 章节保留
    permanent_scenes = [
        PermanentScene(
            scene_id=f"scene-{i}",
            chapter_number=max(1, chapter_number - i * 5),
            excerpt=f"关键场景{i}的前200字摘录...",
            impact_tags=["世界观颠覆"],
        )
        for i in range(min(chapter_number // 5, 5))
    ]

    # Arc/Volume 上下文（10 章后注入 Arc，30 章后注入 Volume）
    arc_context = None
    if chapter_number > 10:
        arc_context = ArcSummary(
            arc_id="arc-1",
            start_chapter=1,
            end_chapter=20,
            arc_title="第一 Arc",
            arc_summary="第一 Arc 的摘要，包含关键事件和角色弧光...",
            key_events=["事件1", "事件2"],
        )

    volume_context = None
    if chapter_number > 30:
        volume_context = VolumeSummary(
            volume_id="vol-1",
            start_chapter=1,
            end_chapter=50,
            volume_title="第一卷",
            volume_summary="第一卷的宏观摘要，包含重大揭示和世界观状态...",
            major_revelations=["揭示1", "揭示2"],
        )

    return ContextPackage(
        chapter_goal=goal,
        recent_plot=recent_plot,
        soft_references=soft_refs,
        open_threads=open_threads,
        permanent_scenes=permanent_scenes,
        arc_context=arc_context,
        volume_context=volume_context,
        genre_rules=GenreRules(),
        mode_rules=ModeRules(),
    )


def run_50chapter_simulation(
    real_chapters: int = 10,
    simulated_chapters: int = 40,
    budget_tokens: int = 8000,
) -> SimulationReport:
    """运行 50 章模拟，验证分层上下文性能.

    策略：
    1. 构造模拟 ContextPackage（规模随 chapter_number 增长）
    2. 运行 BudgetPruner
    3. 记录 budget_used 和关键信息保留率
    """
    total_chapters = real_chapters + simulated_chapters
    pruner = BudgetPruner()

    max_budget_used = 0.0
    total_retention = 0.0
    total_critical_loss = 0
    max_open_threads = 0
    max_permanent_scenes = 0

    for chapter_number in range(1, total_chapters + 1):
        ctx = _build_mock_context_package(chapter_number)

        # 记录裁剪前的关键信息数
        critical_before = sum(1 for ref in ctx.soft_references if ref.is_critical)
        open_threads_before = len(ctx.open_threads)
        scenes_before = len(ctx.permanent_scenes)

        pruned = pruner.prune(ctx, budget_tokens)

        # 记录 budget_used
        max_budget_used = max(max_budget_used, pruned.budget_used)

        # 计算保留率
        critical_after = sum(
            1 for ref in pruned.soft_references if ref.is_critical
        )
        open_threads_after = len(pruned.open_threads)
        scenes_after = len(pruned.permanent_scenes)

        retained = critical_after + open_threads_after + scenes_after
        total_before = critical_before + min(open_threads_before, 5) + min(scenes_before, 3)
        # 注意：BudgetPruner 有硬上限，所以 total_before 应该按上限计算
        retention = retained / max(total_before, 1)
        total_retention += retention

        total_critical_loss += critical_before - critical_after
        max_open_threads = max(max_open_threads, open_threads_after)
        max_permanent_scenes = max(max_permanent_scenes, scenes_after)

    avg_retention = total_retention / total_chapters if total_chapters > 0 else 1.0

    report = SimulationReport(
        total_chapters=total_chapters,
        budget_used=max_budget_used,
        retention_rate=avg_retention,
        critical_loss_count=total_critical_loss,
        open_thread_count=max_open_threads,
        permanent_scene_count=max_permanent_scenes,
    )

    logger.info(
        "simulation_50ch.done",
        total_chapters=total_chapters,
        budget_used=max_budget_used,
        retention_rate=avg_retention,
    )
    return report


def save_simulation_report(
    report: SimulationReport,
    output_path: Path | None = None,
) -> Path:
    """保存模拟报告到 JSON 文件.

    Returns:
        输出文件路径
    """
    if output_path is None:
        DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = DEFAULT_OUTPUT_DIR / "50ch_simulation_report.json"

    output_path.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("simulation_report.saved", path=str(output_path))
    return output_path
