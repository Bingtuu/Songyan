"""RAG A/B 测试框架 — 验证 RAG 自动层对长篇小说一致性的提升效果."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

from songyan.agents.continuity_auditor import ContinuityAuditor
from songyan.db.chunk_repo import ChunkRepository
from songyan.db.continuity_repo import ContinuityReportRepository
import aiosqlite
from songyan.db.connection import get_db
from songyan.db.migrations import init_schema
from songyan.models.continuity import ContinuityReport
from songyan.models.rag import RAGConfig
from songyan.workflows.phase2_graph import run_project_pipeline

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class ControlResult:
    """对照组结果."""

    project_id: str
    chapters: list[int]
    setting_forget_rate: float = 0.0
    continuity_health_scores: dict[int, float] = field(default_factory=dict)
    setting_retention_rate: float = 0.0
    raw_continuity_report: ContinuityReport | None = None


@dataclass
class ExperimentResult:
    """实验组结果."""

    project_id: str
    chapters: list[int]
    setting_forget_rate: float = 0.0
    continuity_health_scores: dict[int, float] = field(default_factory=dict)
    setting_retention_rate: float = 0.0
    raw_continuity_report: ContinuityReport | None = None
    avg_rag_results_per_chapter: float = 0.0


@dataclass
class FailureCase:
    """失败案例分析."""

    chapter: int
    setting_key: str
    control_status: str = ""
    experiment_status: str = ""
    rag_chunks: list[str] = field(default_factory=list)
    diagnosis: str = ""


@dataclass
class ComparisonReport:
    """A/B 对比报告."""

    control: ControlResult
    experiment: ExperimentResult
    setting_forget_rate_delta: float = 0.0
    continuity_health_delta: float = 0.0
    setting_retention_delta: float = 0.0
    meets_success_criteria: bool = False
    failure_cases: list[FailureCase] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        """生成 Markdown 格式报告."""
        lines = [
            "# RAG A/B 测试报告",
            "",
            f"**生成时间**: {datetime.now().isoformat()}",
            f"**对照组项目**: {self.control.project_id}",
            f"**实验组项目**: {self.experiment.project_id}",
            f"**章节范围**: {self.control.chapters[0] if self.control.chapters else 'N/A'} - {self.control.chapters[-1] if self.control.chapters else 'N/A'}",
            "",
            "## 指标对比",
            "",
            "| 指标 | 对照组 (RAG 关闭) | 实验组 (RAG 开启) | 变化 |",
            "|------|------------------|------------------|------|",
            f"| 设定遗忘率 | {self.control.setting_forget_rate:.1%} | {self.experiment.setting_forget_rate:.1%} | {self.setting_forget_rate_delta:+.1%} |",
            f"| 设定保留率 | {self.control.setting_retention_rate:.1%} | {self.experiment.setting_retention_rate:.1%} | {self.setting_retention_delta:+.1%} |",
            f"| 连续性健康分 (最终) | {self._last_health(self.control):.1f} | {self._last_health(self.experiment):.1f} | {self.continuity_health_delta:+.1f} |",
            "",
            "## 逐章连续性健康分",
            "",
            "| 章节 | 对照组 | 实验组 |",
            "|------|--------|--------|",
        ]
        all_chapters = sorted(set(self.control.continuity_health_scores) | set(self.experiment.continuity_health_scores))
        for ch in all_chapters:
            c_score = self.control.continuity_health_scores.get(ch, "—")
            e_score = self.experiment.continuity_health_scores.get(ch, "—")
            c_str = f"{c_score:.1f}" if isinstance(c_score, float) else c_score
            e_str = f"{e_score:.1f}" if isinstance(e_score, float) else e_score
            lines.append(f"| {ch} | {c_str} | {e_str} |")

        lines.extend([
            "",
            "## 成功标准判断",
            "",
            f"- 设定遗忘率降低 ≥ 20%: {'✅' if self.setting_forget_rate_delta <= -0.20 else '❌'} ({abs(self.setting_forget_rate_delta):.1%})",
            f"- 连续性健康分提升 ≥ 0.5: {'✅' if self.continuity_health_delta >= 0.5 else '❌'} ({self.continuity_health_delta:+.1f})",
            f"- 设定保留率提升 ≥ 10%: {'✅' if self.setting_retention_delta >= 0.10 else '❌'} ({self.setting_retention_delta:+.1%})",
            f"- **总体达标**: {'✅ 是' if self.meets_success_criteria else '❌ 否'}",
            "",
        ])

        if self.failure_cases:
            lines.extend([
                "## 失败案例分析",
                "",
            ])
            for fc in self.failure_cases[:10]:
                lines.append(f"- **第 {fc.chapter} 章 / {fc.setting_key}**: {fc.diagnosis}")

        if self.recommendations:
            lines.extend([
                "",
                "## 建议",
                "",
            ])
            for rec in self.recommendations:
                lines.append(f"- {rec}")

        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _last_health(result: ControlResult | ExperimentResult) -> float:
        if result.continuity_health_scores:
            return result.continuity_health_scores[max(result.continuity_health_scores)]
        return 0.0


# ---------------------------------------------------------------------------
# A/B Test Runner
# ---------------------------------------------------------------------------


class RAGABTest:
    """RAG A/B 测试运行器."""

    def __init__(
        self,
        seed_config_path: str,
        seed_chapter_path: str,
        chapter_range: tuple[int, int],
        mode_id: str = "webnovel",
        sample_count: int = 20,
        dry_run: bool = False,
    ) -> None:
        self.seed_config_path = seed_config_path
        self.seed_chapter_path = seed_chapter_path
        self.chapter_range = chapter_range
        self.mode_id = mode_id
        self.sample_count = sample_count
        self.dry_run = dry_run
        self._continuity_repo = ContinuityReportRepository()

    async def _setup_project(self) -> str:
        """导入 seed 项目并返回 project_id."""
        from evals.runner import import_seed_project, import_seed_chapter, _import_seed_character_states
        from evals.models import SeedProjectConfig

        await init_schema()
        project_id = await import_seed_project(self.seed_config_path)
        config = SeedProjectConfig.model_validate_json(
            Path(self.seed_config_path).read_text(encoding="utf-8")
        )
        version_id = await import_seed_chapter(project_id, self.seed_chapter_path, chapter_number=1)
        await _import_seed_character_states(project_id, config, version_id)
        logger.info("ab_test.project_ready", project_id=project_id)
        return project_id

    async def _run_chapters(self, project_id: str, skip_rag: bool = False) -> None:
        """运行指定章节范围."""
        if self.dry_run:
            logger.info("ab_test.dry_run", project_id=project_id, skip_rag=skip_rag)
            return

        # 通过环境变量控制 RAG
        env_key = "SONGYAN_RAG_MODE"
        old_val = os.environ.get(env_key)
        try:
            if skip_rag:
                os.environ[env_key] = "never"
            elif env_key in os.environ:
                del os.environ[env_key]

            await run_project_pipeline(
                project_id=project_id,
                chapter_range=self.chapter_range,
                mode_id=self.mode_id,
                auto_confirm=True,
            )
        finally:
            if old_val is not None:
                os.environ[env_key] = old_val
            elif env_key in os.environ:
                del os.environ[env_key]

    async def _collect_metrics(
        self, project_id: str, up_to_chapter: int
    ) -> tuple[float, dict[int, float], float, ContinuityReport | None]:
        """收集指标: (设定遗忘率, 健康分字典, 设定保留率, 最新 continuity 报告)."""
        if self.dry_run:
            return 0.30, {up_to_chapter: 6.0}, 0.70, None

        # 1. 运行最终 continuity audit
        auditor = ContinuityAuditor()
        report = await auditor.audit(project_id=project_id, up_to_chapter=up_to_chapter)

        # 2. 设定遗忘率
        total_settings = await self._count_active_settings(project_id)
        orphaned = len(report.orphaned_settings) if report else 0
        forget_rate = orphaned / max(total_settings, 1)

        # 3. 连续性健康分 — 收集所有历史报告
        health_scores: dict[int, float] = {}
        async with get_db() as conn:
            cursor = await conn.execute(
                "SELECT checked_up_to_chapter, overall_health_score FROM continuity_reports WHERE project_id = ? ORDER BY checked_up_to_chapter",
                (project_id,),
            )
            rows = await cursor.fetchall()
            for row in rows:
                health_scores[row["checked_up_to_chapter"]] = row["overall_health_score"]
        if report and up_to_chapter not in health_scores:
            health_scores[up_to_chapter] = report.overall_health_score

        # 4. 设定保留率（简化：从 consistency_test 复用逻辑太复杂，用 orphaned 反推）
        retention_rate = 1.0 - forget_rate

        return forget_rate, health_scores, retention_rate, report

    async def _count_active_settings(self, project_id: str) -> int:
        """统计项目活跃设定总数."""


        async with get_db() as conn:
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM setting_tracking WHERE project_id = ? AND status = 'active'",
                (project_id,),
            )
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def _cleanup_project_vectors(self, project_id: str) -> None:
        """清理项目的向量索引."""
        repo = ChunkRepository()
        await repo.delete_by_project(project_id)
        logger.info("ab_test.vectors_cleaned", project_id=project_id)

    async def run_control(self) -> ControlResult:
        """运行对照组（RAG 关闭）."""
        logger.info("ab_test.control_start")
        project_id = await self._setup_project()
        await self._run_chapters(project_id, skip_rag=True)
        up_to = self.chapter_range[1]
        forget_rate, health_scores, retention, report = await self._collect_metrics(
            project_id, up_to
        )
        return ControlResult(
            project_id=project_id,
            chapters=list(range(self.chapter_range[0], self.chapter_range[1] + 1)),
            setting_forget_rate=forget_rate,
            continuity_health_scores=health_scores,
            setting_retention_rate=retention,
            raw_continuity_report=report,
        )

    async def run_experiment(self) -> ExperimentResult:
        """运行实验组（RAG 开启）."""
        logger.info("ab_test.experiment_start")
        project_id = await self._setup_project()
        await self._run_chapters(project_id, skip_rag=False)
        up_to = self.chapter_range[1]
        forget_rate, health_scores, retention, report = await self._collect_metrics(
            project_id, up_to
        )
        # dry-run 下模拟 RAG 改善效果
        if self.dry_run:
            forget_rate = 0.05
            health_scores = {up_to: 9.0}
            retention = 0.95
            avg_rag = 3.5
        else:
            # 统计平均每章 RAG chunk 数（从 chunk_repo）
            repo = ChunkRepository()
            chunks = await repo.get_by_project(project_id)
            chapter_count = self.chapter_range[1] - self.chapter_range[0] + 1
            avg_rag = len(chunks) / max(chapter_count, 1)

        return ExperimentResult(
            project_id=project_id,
            chapters=list(range(self.chapter_range[0], self.chapter_range[1] + 1)),
            setting_forget_rate=forget_rate,
            continuity_health_scores=health_scores,
            setting_retention_rate=retention,
            raw_continuity_report=report,
            avg_rag_results_per_chapter=avg_rag,
        )

    async def run(self) -> ComparisonReport:
        """运行完整 A/B 测试并返回对比报告."""
        control = await self.run_control()
        experiment = await self.run_experiment()

        # 计算差异
        forget_delta = experiment.setting_forget_rate - control.setting_forget_rate
        health_delta = self._last_health(experiment) - self._last_health(control)
        retention_delta = experiment.setting_retention_rate - control.setting_retention_rate

        # 成功标准
        meets_criteria = (
            forget_delta <= -0.20
            and health_delta >= 0.5
            and retention_delta >= 0.10
        )

        # 失败案例分析
        failure_cases = self._analyze_failures(control, experiment)

        # 建议
        recommendations = self._generate_recommendations(
            forget_delta, health_delta, retention_delta, meets_criteria
        )

        return ComparisonReport(
            control=control,
            experiment=experiment,
            setting_forget_rate_delta=forget_delta,
            continuity_health_delta=health_delta,
            setting_retention_delta=retention_delta,
            meets_success_criteria=meets_criteria,
            failure_cases=failure_cases,
            recommendations=recommendations,
        )

    def _analyze_failures(
        self, control: ControlResult, experiment: ExperimentResult
    ) -> list[FailureCase]:
        """分析实验组未能改善的案例."""
        cases: list[FailureCase] = []
        if not experiment.raw_continuity_report:
            return cases

        for orphaned in experiment.raw_continuity_report.orphaned_settings:
            cases.append(
                FailureCase(
                    chapter=orphaned.last_mentioned_chapter or 0,
                    setting_key=orphaned.setting_key,
                    control_status="forgotten",
                    experiment_status="forgotten",
                    diagnosis=f"设定 '{orphaned.setting_name}' 在实验组中仍被 orphaned，"
                    f"最后提及于第 {orphaned.last_mentioned_chapter} 章，"
                    f"已遗忘 {orphaned.chapters_since_mention} 章。"
                    "可能原因：RAG query 未包含该设定关键词，或相似度门槛过滤。",
                )
            )
        return cases[:20]

    def _generate_recommendations(
        self,
        forget_delta: float,
        health_delta: float,
        retention_delta: float,
        meets_criteria: bool,
    ) -> list[str]:
        """生成调优建议."""
        recs: list[str] = []
        if meets_criteria:
            recs.append("RAG 自动层达到成功标准，建议进入 Phase 9 全面部署。")
        else:
            if forget_delta > -0.20:
                recs.append(
                    f"设定遗忘率仅降低 {abs(forget_delta):.1%}（目标 20%），"
                    "建议降低 min_similarity 门槛或增大 max_results。"
                )
            if health_delta < 0.5:
                recs.append(
                    f"连续性健康分仅提升 {health_delta:+.1f}（目标 0.5），"
                    "建议优化 query 构造策略（增加 obligations 权重）。"
                )
            if retention_delta < 0.10:
                recs.append(
                    f"设定保留率仅提升 {retention_delta:+.1%}（目标 10%），"
                    "建议增大 chunk_overlap 防止关键信息被切分。"
                )
        return recs

    @staticmethod
    def _last_health(result: ControlResult | ExperimentResult) -> float:
        if result.continuity_health_scores:
            return result.continuity_health_scores[max(result.continuity_health_scores)]
        return 0.0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_chapter_range(text: str) -> tuple[int, int]:
    if "-" in text:
        start, end = text.split("-")
        return (int(start), int(end))
    n = int(text)
    return (n, n)


async def main() -> None:
    parser = argparse.ArgumentParser(description="RAG A/B 测试")
    parser.add_argument("--seed-config", required=True, help="种子项目配置 JSON 路径")
    parser.add_argument("--seed-chapter", required=True, help="种子章节 markdown 路径")
    parser.add_argument("--chapters", default="12-20", help="章节范围，如 12-20")
    parser.add_argument("--mode-id", default="webnovel", help="创作模式 ID")
    parser.add_argument("--sample-count", type=int, default=20, help="抽样验证设定数")
    parser.add_argument("--output-dir", default="evals/output", help="输出目录")
    parser.add_argument("--dry-run", action="store_true", help="Mock 模式，不实际运行 pipeline")
    args = parser.parse_args()

    chapter_range = _parse_chapter_range(args.chapters)

    test = RAGABTest(
        seed_config_path=args.seed_config,
        seed_chapter_path=args.seed_chapter,
        chapter_range=chapter_range,
        mode_id=args.mode_id,
        sample_count=args.sample_count,
        dry_run=args.dry_run,
    )

    report = await test.run()

    # 输出 Markdown
    md = report.to_markdown()
    md_path = Path(args.output_dir) / f"rag_ab_test_{int(time.time())}.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(md, encoding="utf-8")
    print(f"\n报告已保存: {md_path}")

    # 输出 JSON
    json_data = {
        "timestamp": datetime.now().isoformat(),
        "config": {
            "seed_config": args.seed_config,
            "seed_chapter": args.seed_chapter,
            "chapter_range": chapter_range,
            "mode_id": args.mode_id,
            "sample_count": args.sample_count,
            "dry_run": args.dry_run,
        },
        "control": asdict(report.control),
        "experiment": asdict(report.experiment),
        "comparison": {
            "setting_forget_rate_delta": report.setting_forget_rate_delta,
            "continuity_health_delta": report.continuity_health_delta,
            "setting_retention_delta": report.setting_retention_delta,
            "meets_success_criteria": report.meets_success_criteria,
            "failure_cases": [asdict(fc) for fc in report.failure_cases],
            "recommendations": report.recommendations,
        },
    }
    json_path = Path(args.output_dir) / f"rag_ab_test_{int(time.time())}.json"
    json_path.write_text(json.dumps(json_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"JSON 已保存: {json_path}")

    print(f"\n{'=' * 60}")
    print(md)


if __name__ == "__main__":
    asyncio.run(main())
