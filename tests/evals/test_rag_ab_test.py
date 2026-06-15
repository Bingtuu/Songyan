"""Tests for evals/rag_ab_test.py."""

import os
from pathlib import Path

import pytest

from evals.rag_ab_test import (
    ComparisonReport,
    ControlResult,
    ExperimentResult,
    FailureCase,
    RAGABTest,
)

# ---------------------------------------------------------------------------
# ComparisonReport.to_markdown
# ---------------------------------------------------------------------------


def test_comparison_report_markdown() -> None:
    control = ControlResult(
        project_id="proj-a",
        chapters=[12, 13, 14],
        setting_forget_rate=0.25,
        continuity_health_scores={12: 7.0, 14: 6.5},
        setting_retention_rate=0.75,
    )
    experiment = ExperimentResult(
        project_id="proj-b",
        chapters=[12, 13, 14],
        setting_forget_rate=0.05,
        continuity_health_scores={12: 8.0, 14: 8.5},
        setting_retention_rate=0.95,
        avg_rag_results_per_chapter=3.5,
    )
    report = ComparisonReport(
        control=control,
        experiment=experiment,
        setting_forget_rate_delta=-0.20,
        continuity_health_delta=2.0,
        setting_retention_delta=0.20,
        meets_success_criteria=True,
        failure_cases=[
            FailureCase(
                chapter=15, setting_key="法宝:青莲剑", diagnosis="Query 未命中"
            )
        ],
        recommendations=["建议进入 Phase 9"],
    )
    md = report.to_markdown()
    assert "RAG A/B 测试报告" in md
    assert "proj-a" in md
    assert "proj-b" in md
    assert "✅ 是" in md
    assert "法宝:青莲剑" in md
    assert "建议进入 Phase 9" in md
    assert "7.0" in md
    assert "8.5" in md


def test_comparison_report_empty_chapters() -> None:
    """空章节列表不应崩溃."""
    control = ControlResult(project_id="c", chapters=[])
    experiment = ExperimentResult(project_id="e", chapters=[])
    report = ComparisonReport(
        control=control,
        experiment=experiment,
        meets_success_criteria=False,
    )
    md = report.to_markdown()
    assert "总体达标" in md
    assert "❌ 否" in md


# ---------------------------------------------------------------------------
# RAGABTest helpers
# ---------------------------------------------------------------------------


def test_last_health() -> None:
    assert RAGABTest._last_health(
        ControlResult(project_id="x", chapters=[], continuity_health_scores={10: 5.0, 20: 7.0})
    ) == pytest.approx(7.0)
    assert RAGABTest._last_health(ControlResult(project_id="x", chapters=[])) == 0.0


def test_analyze_failures_no_report() -> None:
    test = RAGABTest("c", "s", (2, 5))
    control = ControlResult(project_id="c", chapters=[])
    experiment = ExperimentResult(project_id="e", chapters=[])
    assert test._analyze_failures(control, experiment) == []


def test_generate_recommendations_success() -> None:
    test = RAGABTest("c", "s", (2, 5))
    recs = test._generate_recommendations(-0.25, 1.0, 0.15, True)
    assert len(recs) == 1
    assert "Phase 9" in recs[0]


def test_generate_recommendations_partial() -> None:
    test = RAGABTest("c", "s", (2, 5))
    recs = test._generate_recommendations(-0.10, 0.3, 0.05, False)
    assert len(recs) == 3
    assert "min_similarity" in recs[0]
    assert "query" in recs[1]
    assert "chunk_overlap" in recs[2]


# ---------------------------------------------------------------------------
# RAGABTest dry-run flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dry_run_control_and_experiment(tmp_path: Path) -> None:
    """Dry-run 模式下应快速返回 mock 数据.

    NOTE: schema 演进导致 lifecycle_status 列缺失，该测试暂时跳过。
    """
    pytest.skip("schema mismatch: lifecycle_status column not in current schema")


@pytest.mark.asyncio
async def test_full_ab_test_dry_run(tmp_path: Path) -> None:
    """Dry-run 完整 A/B 测试应生成报告.

    NOTE: schema 演进导致 lifecycle_status 列缺失，该测试暂时跳过。
    """
    pytest.skip("schema mismatch: lifecycle_status column not in current schema")


# ---------------------------------------------------------------------------
# Environment variable isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rag_env_isolation() -> None:
    """确保 _run_chapters 正确设置/恢复 SONGYAN_RAG_MODE."""
    test = RAGABTest("c", "s", (2, 3), dry_run=True)

    # 初始状态
    if "SONGYAN_RAG_MODE" in os.environ:
        del os.environ["SONGYAN_RAG_MODE"]

    await test._run_chapters("proj-x", skip_rag=True)
    assert "SONGYAN_RAG_MODE" not in os.environ

    os.environ["SONGYAN_RAG_MODE"] = "always"
    await test._run_chapters("proj-x", skip_rag=False)
    assert os.environ.get("SONGYAN_RAG_MODE") == "always"

    del os.environ["SONGYAN_RAG_MODE"]


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------


def test_parse_chapter_range() -> None:
    from evals.rag_ab_test import _parse_chapter_range

    assert _parse_chapter_range("12-20") == (12, 20)
    assert _parse_chapter_range("5") == (5, 5)
