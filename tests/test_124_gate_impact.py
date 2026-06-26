"""Task 124: 离线门禁影响面分析脚本单元测试."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

from songyan.db.continuity_repo import ContinuityReportRepository
from songyan.db.project_run_repo import ProjectRunRepository
from songyan.db.repository import ProjectRepository
from songyan.models import (
    ContinuityReport,
    OrphanedSetting,
    ProjectRunState,
    ProjectSetting,
    StateMismatch,
)

SCRIPT_PATH = Path(__file__).parent.parent / "scripts" / "analyze_124_gate_impact.py"


def _load_script_module() -> Any:
    """动态加载 scripts/analyze_124_gate_impact.py（非包内模块）."""
    spec = importlib.util.spec_from_file_location("analyze_124_gate_impact", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def script():
    return _load_script_module()


def _make_project(project_id: str) -> ProjectSetting:
    return ProjectSetting(
        title=f"Test {project_id}",
        genre_id="urban",
        mode_id="webnovel",
        protagonist_name="Tester",
    )


def _write_jsonl(directory: Path, run_id: str, logs: list[dict[str, Any]]) -> Path:
    path = directory / f"{run_id}.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for log in logs:
            f.write(json.dumps(log, ensure_ascii=False) + "\n")
    return path


# ---------------------------------------------------------------------------
# Data loading tests
# ---------------------------------------------------------------------------


def test_load_jsonl_logs_sorted_and_filtered(script, tmp_path, monkeypatch):
    monkeypatch.setattr(script, "_LOGS_DIR", tmp_path)
    logs = [
        {"chapter_number": 2, "success": True},
        {"chapter_number": 1, "success": False},
        "",  # blank line to be ignored
    ]
    path = tmp_path / "run-test.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for entry in logs:
            f.write((json.dumps(entry, ensure_ascii=False) if entry else "") + "\n")

    loaded = script._load_jsonl_logs("run-test")
    assert [r["chapter_number"] for r in loaded] == [1, 2]


def test_load_jsonl_logs_missing_file(script, tmp_path, monkeypatch):
    monkeypatch.setattr(script, "_LOGS_DIR", tmp_path)
    with pytest.raises(FileNotFoundError):
        script._load_jsonl_logs("run-missing")


async def test_resolve_project_id(script, test_db):
    project_id = "proj-resolve-124"
    await ProjectRepository().create(_make_project(project_id), project_id)
    run_state = ProjectRunState(
        run_id="run-resolve-124",
        project_id=project_id,
        chapter_range_start=1,
        chapter_range_end=10,
    )
    await ProjectRunRepository().create(run_state)

    resolved = await script._resolve_project_id("run-resolve-124")
    assert resolved == project_id


async def test_resolve_project_id_not_found(script, test_db):
    with pytest.raises(ValueError, match="Run not found"):
        await script._resolve_project_id("run-does-not-exist")


async def test_load_continuity_reports(script, test_db):
    project_id = "proj-cont-124"
    await ProjectRepository().create(_make_project(project_id), project_id)
    reports = [
        ContinuityReport(
            report_id="rpt-1",
            project_id=project_id,
            checked_up_to_chapter=3,
            overall_health_score=10.0,
        ),
        ContinuityReport(
            report_id="rpt-2",
            project_id=project_id,
            checked_up_to_chapter=6,
            overall_health_score=9.0,
        ),
    ]
    repo = ContinuityReportRepository()
    for report in reports:
        await repo.create(report)

    loaded = await script._load_continuity_reports(project_id, 1, 10)
    assert set(loaded.keys()) == {3, 6}
    assert loaded[3].overall_health_score == 10.0
    assert loaded[6].overall_health_score == 9.0


# ---------------------------------------------------------------------------
# Analyzer logic tests
# ---------------------------------------------------------------------------


def _make_log(chapter_number: int, **overrides) -> dict[str, Any]:
    defaults = {
        "chapter_number": chapter_number,
        "success": True,
        "quality_gate_passed": True,
        "context_emergency": False,
        "settlement_success": True,
        "summary_success": True,
    }
    defaults.update(overrides)
    return defaults


def _make_report(
    project_id: str,
    chapter: int,
    health_score: float = 10.0,
    state_mismatches: list[StateMismatch] | None = None,
    orphaned_settings: list[OrphanedSetting] | None = None,
) -> ContinuityReport:
    return ContinuityReport(
        report_id=f"rpt-{chapter}",
        project_id=project_id,
        checked_up_to_chapter=chapter,
        overall_health_score=health_score,
        state_mismatches=state_mismatches or [],
        orphaned_settings=orphaned_settings or [],
    )


def _state_mismatches(count: int, start_chapter: int = 1) -> list[StateMismatch]:
    """批量生成指定数量的 StateMismatch（每个计 1 P1）."""
    return [
        StateMismatch(
            character_id=f"c{i}",
            field="health",
            chapter_a=start_chapter,
            value_a="fine",
            chapter_b=start_chapter + 1,
            value_b="dead",
            issue="inconsistent",
        )
        for i in range(count)
    ]


def test_analyzer_no_trigger(script):
    logs = [_make_log(i) for i in range(1, 4)]
    reports = {3: _make_report("proj", 3, health_score=10.0)}
    analyzer = script.GateImpactAnalyzer(logs, reports)
    result = analyzer.analyze()

    assert result["total_chapters"] == 3
    assert result["summary"]["any_gate"]["count"] == 0
    assert result["summary"]["any_gate"]["first_chapter"] is None


def test_analyzer_health_low_p1_halt(script):
    """P1 数量超过滚动基线且满足最小绝对阈值时触发."""
    logs = [_make_log(i) for i in range(1, 4)]
    reports = {
        1: _make_report("proj", 1, health_score=10.0, state_mismatches=_state_mismatches(10)),
        3: _make_report(
            "proj",
            3,
            health_score=10.0,
            state_mismatches=_state_mismatches(50),
        ),
    }
    result = script.GateImpactAnalyzer(logs, reports).analyze()

    assert result["summary"]["health_low_p1_halt"]["count"] == 1
    assert result["summary"]["health_low_p1_halt"]["first_chapter"] == 3
    assert result["summary"]["health_low_score_halt"]["count"] == 0


def test_analyzer_health_low_score_halt(script):
    """overall_health_score 创历史新低且同章 P1 激增时触发."""
    logs = [_make_log(i) for i in range(1, 4)]
    reports = {
        1: _make_report("proj", 1, health_score=8.0, state_mismatches=_state_mismatches(10)),
        3: _make_report("proj", 3, health_score=2.0, state_mismatches=_state_mismatches(50)),
    }
    result = script.GateImpactAnalyzer(logs, reports).analyze()

    assert result["summary"]["health_low_score_halt"]["count"] == 1
    assert result["summary"]["health_low_score_halt"]["first_chapter"] == 3


def test_analyzer_health_low_streak_halt_carries_over(script):
    """连续 3 个审计点 P1 累计超过固定高阈值时触发 streak gate."""
    logs = [_make_log(i) for i in range(1, 10)]
    reports = {
        3: _make_report("proj", 3, health_score=10.0, state_mismatches=_state_mismatches(100)),
        6: _make_report("proj", 6, health_score=10.0, state_mismatches=_state_mismatches(100)),
        9: _make_report("proj", 9, health_score=10.0, state_mismatches=_state_mismatches(100)),
    }
    result = script.GateImpactAnalyzer(logs, reports).analyze()

    streak = result["summary"]["health_low_streak_halt"]
    assert streak["count"] >= 1
    assert 9 in streak["chapters"]


def test_analyzer_context_emergency_budget_ratio_halt(script):
    logs = [
        _make_log(1),
        _make_log(2, context_emergency=True, budget_used_before_emergency=1.5),
    ]
    result = script.GateImpactAnalyzer(logs, {}).analyze()

    rule = result["summary"]["context_emergency_budget_ratio_halt"]
    assert rule["count"] == 1
    assert rule["first_chapter"] == 2


def test_analyzer_context_emergency_failure_halt(script):
    logs = [
        _make_log(1),
        _make_log(2, context_emergency=True, settlement_success=False),
    ]
    result = script.GateImpactAnalyzer(logs, {}).analyze()

    rule = result["summary"]["context_emergency_failure_halt"]
    assert rule["count"] == 1
    assert rule["first_chapter"] == 2


def test_analyzer_blocked_from_first_halt(script):
    logs = [_make_log(i) for i in range(1, 6)]
    reports = {
        1: _make_report("proj", 1, health_score=10.0, state_mismatches=_state_mismatches(10)),
        3: _make_report("proj", 3, health_score=10.0, state_mismatches=_state_mismatches(50)),
    }
    result = script.GateImpactAnalyzer(logs, reports).analyze()

    any_gate = result["summary"]["any_gate"]
    assert any_gate["first_chapter"] == 3
    assert any_gate["blocked_from_first_halt"] == 3  # chapters 3,4,5


# ---------------------------------------------------------------------------
# Report rendering tests
# ---------------------------------------------------------------------------


def test_render_report_sections(script):
    logs = [_make_log(i) for i in range(1, 4)]
    reports = {3: _make_report("proj", 3, health_score=2.0)}
    result = script.GateImpactAnalyzer(logs, reports).analyze()
    result["run_id"] = "run-test"
    result["project_id"] = "proj-test"

    md = script._render_report(result)
    assert "# Task 124" in md
    assert "## 1. 汇总表" in md
    assert "## 2. 关键发现" in md
    assert "## 3. 审计点 severity 分布" in md
    assert "## 4. 逐章触发明细" in md
    assert "## 5. 建议" in md
    assert "run-test" in md
    assert "proj-test" in md


def test_render_report_zero_trigger(script):
    logs = [_make_log(i) for i in range(1, 4)]
    reports = {3: _make_report("proj", 3, health_score=10.0)}
    result = script.GateImpactAnalyzer(logs, reports).analyze()
    result["run_id"] = "run-clean"
    result["project_id"] = "proj-clean"

    md = script._render_report(result)
    assert "所有候选硬门禁规则均未触发" in md
    assert "无" in md or "| - |" in md


def test_severity_distribution(script):
    logs = [_make_log(i) for i in range(1, 4)]
    reports = {
        3: _make_report(
            "proj",
            3,
            health_score=5.0,
            state_mismatches=[
                StateMismatch(
                    character_id="c1",
                    field="health",
                    chapter_a=1,
                    value_a="a",
                    chapter_b=2,
                    value_b="b",
                    issue="x",
                )
            ],
        )
    }
    per_chapter = script.GateImpactAnalyzer(logs, reports).analyze()["per_chapter"]
    dist = script._severity_distribution(per_chapter)

    assert dist["audit_chapters"] == 1
    assert dist["health_score"]["avg"] == 5.0
    assert dist["P1"]["sum"] == 1
    assert dist["P2"]["sum"] == 0


# ---------------------------------------------------------------------------
# End-to-end CLI test
# ---------------------------------------------------------------------------


async def test_main_end_to_end(script, test_db, tmp_path, monkeypatch):
    import sys

    project_id = "proj-e2e-124"
    run_id = "run-e2e-124"
    await ProjectRepository().create(_make_project(project_id), project_id)
    await ProjectRunRepository().create(
        ProjectRunState(
            run_id=run_id,
            project_id=project_id,
            chapter_range_start=1,
            chapter_range_end=3,
        )
    )

    logs = [_make_log(i) for i in range(1, 4)]
    monkeypatch.setattr(script, "_LOGS_DIR", tmp_path)
    _write_jsonl(tmp_path, run_id, logs)

    output_path = tmp_path / "report.md"
    monkeypatch.setattr(
        sys,
        "argv",
        ["analyze_124_gate_impact.py", "--run-id", run_id, "--output", str(output_path)],
    )
    await script.main()

    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert run_id in content
    assert project_id in content
    assert "## 1. 汇总表" in content
