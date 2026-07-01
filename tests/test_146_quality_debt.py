"""Tests for Task 146 — quality-debt ledger.

覆盖：compute_quality_debt 计数/占比/50 章滑窗 T4/边界/窗口不足；run_quality_debt
表迁移 + repo 增量 upsert；jsonl 适配器；渲染段。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import aiosqlite

from songyan.db.migrations import _EXPECTED_TABLES
from songyan.db.project_run_repo import ProjectRunRepository
from songyan.db.repository import ProjectRepository
from songyan.db.run_quality_debt_repo import RunQualityDebtRepository, RunQualityDebtRow
from songyan.evals.db_metrics import (
    compute_quality_debt,
    quality_debt_from_metrics_jsonl,
    quality_debt_row,
    render_run_quality_debt_section,
)
from songyan.models import ChapterRunLog, ProjectRunState, ProjectSetting

PID = "proj-146"
RID = "run-146"


def _log(chapter: int, *, degraded: bool = False, convergence: bool = False,
         qg: bool | None = None) -> ChapterRunLog:
    return ChapterRunLog(
        log_id=f"log-{chapter}",
        project_id=PID,
        chapter_number=chapter,
        started_at=datetime.now(),
        finished_at=datetime.now(),
        success=True,
        degraded_accept=degraded,
        convergence_failed=convergence,
        quality_gate_passed=qg,
    )


async def _seed_run() -> None:
    await ProjectRepository().create(
        ProjectSetting(genre_id="xuanhuan", protagonist_name="英雄"), PID
    )
    await ProjectRunRepository().create(
        ProjectRunState(run_id=RID, project_id=PID, chapter_range_start=1, chapter_range_end=60)
    )


# --------------------------------------------------------------------------- #
# compute_quality_debt
# --------------------------------------------------------------------------- #
class TestComputeQualityDebt:
    def test_counts_and_ratios(self) -> None:
        logs = [
            _log(1, degraded=True, qg=False),
            _log(2, convergence=True),
            _log(3, qg=True),
            _log(4),
        ]
        r = compute_quality_debt(logs)
        assert r.total_chapters == 4
        assert r.degraded_chapters == [1]
        assert r.convergence_failed_chapters == [2]
        assert r.qg_false_chapters == [1]
        assert r.degraded_ratio == 0.25
        assert r.convergence_ratio == 0.25

    def test_window_insufficient(self) -> None:
        r = compute_quality_debt([_log(i) for i in range(1, 11)])
        assert r.window_sufficient is False
        assert r.windows == []
        assert r.t4_breached is False

    def test_50_window_degraded_breach(self) -> None:
        # 60 章，第 1-50 窗内 11 个 degraded → 22% > 20% → 破线
        logs = [_log(i, degraded=(i <= 11)) for i in range(1, 61)]
        r = compute_quality_debt(logs)
        assert r.window_sufficient is True
        assert r.t4_breached is True
        assert r.windows[0].degraded_ratio == 11 / 50

    def test_50_window_boundary_not_breached(self) -> None:
        # 恰好 10/50 = 20% degraded（≤20% 合规）→ 不破线
        logs = [_log(i, degraded=(i <= 10)) for i in range(1, 61)]
        r = compute_quality_debt(logs)
        assert all(not w.t4_breached for w in r.windows)
        assert r.t4_breached is False

    def test_50_window_convergence_breach(self) -> None:
        # 6/50 = 12% convergence > 10% → 破线
        logs = [_log(i, convergence=(i <= 6)) for i in range(1, 61)]
        r = compute_quality_debt(logs)
        assert r.t4_breached is True


# --------------------------------------------------------------------------- #
# run_quality_debt table + repo
# --------------------------------------------------------------------------- #
class TestRunQualityDebtRepo:
    async def test_table_registered_and_created(self, test_db: Path) -> None:
        assert "run_quality_debt" in _EXPECTED_TABLES

    async def test_upsert_idempotent(self, test_db: Path) -> None:
        await _seed_run()
        repo = RunQualityDebtRepository()
        report = compute_quality_debt([_log(1, degraded=True), _log(2)])
        await repo.upsert(quality_debt_row(RID, PID, report))
        got = await repo.get(RID)
        assert got is not None and got.degraded_count == 1 and got.total_chapters == 2

        # 再次 upsert 覆盖同一行（增量场景）
        report2 = compute_quality_debt([_log(i, degraded=(i == 1)) for i in range(1, 4)])
        await repo.upsert(quality_debt_row(RID, PID, report2))
        got2 = await repo.get(RID)
        assert got2 is not None and got2.total_chapters == 3
        rows = await repo.list_by_project(PID)
        assert len(rows) == 1  # 仍是一行

    async def test_fk_cascade(self, test_db: Path) -> None:
        await _seed_run()
        repo = RunQualityDebtRepository()
        await repo.upsert(RunQualityDebtRow(run_id=RID, project_id=PID, total_chapters=1))
        async with aiosqlite.connect(str(test_db)) as conn:
            await conn.execute("PRAGMA foreign_keys = ON")
            await conn.execute("DELETE FROM project_runs WHERE run_id = ?", (RID,))
            await conn.commit()
            cur = await conn.execute(
                "SELECT COUNT(*) FROM run_quality_debt WHERE run_id = ?", (RID,)
            )
            assert (await cur.fetchone())[0] == 0


# --------------------------------------------------------------------------- #
# jsonl adapter + rendering
# --------------------------------------------------------------------------- #
class TestAdapterAndRender:
    def test_jsonl_adapter_qg_false(self, tmp_path: Path) -> None:
        path = tmp_path / "m.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for ch in range(1, 6):
                f.write(json.dumps({"chapter": ch, "quality_gate_passed": ch % 2 == 0}) + "\n")
        r = quality_debt_from_metrics_jsonl(str(path))
        assert r.total_chapters == 5
        assert r.qg_false_chapters == [1, 3, 5]
        # 历史 jsonl 无 degraded/convergence
        assert r.degraded_chapters == [] and r.convergence_failed_chapters == []

    def test_render_empty_and_rows(self) -> None:
        assert "无 run 质量债记录" in render_run_quality_debt_section([])
        rows = [RunQualityDebtRow(run_id=RID, project_id=PID, total_chapters=60,
                                  degraded_count=15, degraded_ratio=0.25, t4_breached=True)]
        md = render_run_quality_debt_section(rows)
        assert "质量债账本" in md and "破线" in md and RID in md
