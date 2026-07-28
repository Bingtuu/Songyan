"""Task 193.r tests — 评测口径修复包.

覆盖三块：
1. detect_halt 区分人工/成本暂停与质量熔断（project_runs.pause_reason）。
2. ProjectRunRepository pause_reason 持久化；_persist_run_progress 恢复 running 时清理。
3. segment_audit orphan 阈值与运行时同源（GenreRuntimeProfile 注册表基线 + 目标库 DB 覆盖层）。
4. V10 harness 成本预算接线（--cost-budget / SONGYAN_RUN_COST_BUDGET / --status 展示）。
"""

from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from songyan.evals.five_gate_acceptance import detect_halt
from songyan.evals.segment_audit import collect_segment_audit
from songyan.models.genre_runtime_profile import GenreRuntimeProfile

ROOT = Path(__file__).resolve().parents[1]


def _load_harness():
    spec = importlib.util.spec_from_file_location(
        "run_v10_ch200_climb", ROOT / "scripts" / "run_v10_ch200_climb.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


HARNESS = _load_harness()

# ---------------------------------------------------------------------------
# 1. detect_halt pause_reason 语义
# ---------------------------------------------------------------------------


def _halt_db(*, with_pause_reason: bool = True) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    pause_col = ", pause_reason TEXT" if with_pause_reason else ""
    conn.execute(
        "CREATE TABLE project_runs (run_id TEXT, project_id TEXT, status TEXT, "
        f"current_chapter INTEGER, updated_at TEXT{pause_col})"
    )
    return conn


def _insert_run(
    conn: sqlite3.Connection,
    *,
    status: str,
    current_chapter: int,
    pause_reason: object = ...,  # ... = 列不存在/不插入
    project_id: str = "p1",
) -> None:
    cols = ["run_id", "project_id", "status", "current_chapter", "updated_at"]
    vals: list[object] = ["r1", project_id, status, current_chapter, "2026-07-28 00:00:00"]
    if pause_reason is not ...:
        cols.append("pause_reason")
        vals.append(pause_reason)
    placeholders = ", ".join("?" for _ in vals)
    conn.execute(f"INSERT INTO project_runs ({', '.join(cols)}) VALUES ({placeholders})", vals)
    conn.commit()


class TestDetectHaltPauseReason:
    def test_user_requested_pause_is_not_halt(self) -> None:
        conn = _halt_db()
        _insert_run(conn, status="paused", current_chapter=5, pause_reason="user_requested")
        assert detect_halt(conn, "p1", 10) is None

    def test_cost_budget_pause_is_not_halt(self) -> None:
        conn = _halt_db()
        _insert_run(conn, status="paused", current_chapter=5, pause_reason="cost_budget")
        assert detect_halt(conn, "p1", 10) is None

    def test_auto_halt_pause_is_halt(self) -> None:
        conn = _halt_db()
        _insert_run(
            conn, status="paused", current_chapter=5,
            pause_reason="auto_halt:health_low_streak_halt",
        )
        halt = detect_halt(conn, "p1", 10)
        assert halt is not None
        assert "auto_halt:health_low_streak_halt" in halt

    def test_null_pause_reason_keeps_legacy_halt(self) -> None:
        conn = _halt_db()
        _insert_run(conn, status="paused", current_chapter=5, pause_reason=None)
        assert detect_halt(conn, "p1", 10) == "project_run_paused@Ch5"

    def test_missing_pause_reason_column_keeps_legacy_halt(self) -> None:
        conn = _halt_db(with_pause_reason=False)
        _insert_run(conn, status="paused", current_chapter=5)
        assert detect_halt(conn, "p1", 10) == "project_run_paused@Ch5"

    def test_failed_run_is_halt(self) -> None:
        conn = _halt_db()
        _insert_run(conn, status="failed", current_chapter=5, pause_reason=None)
        assert detect_halt(conn, "p1", 10) == "project_run_failed@Ch5"

    def test_running_run_is_not_halt(self) -> None:
        conn = _halt_db()
        _insert_run(conn, status="running", current_chapter=5, pause_reason=None)
        assert detect_halt(conn, "p1", 10) is None

    def test_pause_beyond_boundary_is_not_halt(self) -> None:
        conn = _halt_db()
        _insert_run(
            conn, status="paused", current_chapter=12, pause_reason="auto_halt:adaptive_halt"
        )
        assert detect_halt(conn, "p1", 10) is None


# ---------------------------------------------------------------------------
# 2. pause_reason 持久化与清理
# ---------------------------------------------------------------------------

PID = "proj-193r"
RID = "run-193r"


async def _seed_run(*, status: str = "running", suffix: str = "") -> object:
    from songyan.db.project_run_repo import ProjectRunRepository
    from songyan.db.repository import ProjectRepository
    from songyan.models import ProjectRunState, ProjectSetting

    await ProjectRepository().create(
        ProjectSetting(genre_id="wuxia", protagonist_name="甲"), f"{PID}{suffix}"
    )
    state = ProjectRunState(
        run_id=f"{RID}{suffix}",
        project_id=f"{PID}{suffix}",
        chapter_range_start=1,
        chapter_range_end=5,
        current_chapter=1,
        status=status,
    )
    await ProjectRunRepository().create(state)
    return state


class TestProjectRunPauseReasonPersistence:
    async def test_pause_reason_roundtrip(self, test_db: Path) -> None:
        from songyan.db.project_run_repo import ProjectRunRepository

        state = await _seed_run(status="paused", suffix="-a")
        state.pause_reason = "auto_halt:test"
        repo = ProjectRunRepository()
        await repo.update(state)
        loaded = await repo.get(f"{RID}-a")
        assert loaded is not None
        assert loaded.pause_reason == "auto_halt:test"

        loaded.status = "running"
        loaded.pause_reason = None
        await repo.update(loaded)
        reloaded = await repo.get(f"{RID}-a")
        assert reloaded is not None
        assert reloaded.pause_reason is None

    async def test_pause_run_for_auto_halt_records_reason(self, test_db: Path) -> None:
        from songyan.db.project_run_repo import ProjectRunRepository
        from songyan.workflows.phase2_graph import _pause_run_for_auto_halt

        state = await _seed_run(suffix="-b")
        await _pause_run_for_auto_halt(
            state, [], [], "", pause_reason="auto_halt:health_low_streak_halt"
        )
        persisted = await ProjectRunRepository().get(f"{RID}-b")
        assert persisted is not None
        assert persisted.status == "paused"
        assert persisted.pause_reason == "auto_halt:health_low_streak_halt"

    async def test_persist_progress_clears_reason_when_running(self, test_db: Path) -> None:
        from songyan.db.project_run_repo import ProjectRunRepository
        from songyan.workflows.phase2_graph import (
            _pause_run_for_auto_halt,
            _persist_run_progress,
        )

        state = await _seed_run(suffix="-c")
        await _pause_run_for_auto_halt(state, [], [], "", pause_reason="cost_budget")
        await _persist_run_progress(state, [], [], "", status="running")
        persisted = await ProjectRunRepository().get(f"{RID}-c")
        assert persisted is not None
        assert persisted.status == "running"
        assert persisted.pause_reason is None


# ---------------------------------------------------------------------------
# 3. segment_audit 阈值与运行时同源
# ---------------------------------------------------------------------------


def _init_segment_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE chapter_heads (
            project_id TEXT, chapter_number INTEGER, accepted_version_id TEXT
        );
        CREATE TABLE chapter_versions (
            version_id TEXT, project_id TEXT, chapter_number INTEGER
        );
        CREATE TABLE review_reports (chapter_version_id TEXT, issues TEXT);
        CREATE TABLE setting_tracking (
            project_id TEXT, setting_key TEXT, status TEXT, category TEXT,
            last_mentioned_chapter INTEGER
        );
        CREATE TABLE continuity_reports (
            project_id TEXT, checked_up_to_chapter INTEGER, overall_health_score REAL
        );
        CREATE TABLE genre_runtime_profiles (
            genre TEXT PRIMARY KEY, version TEXT, profile_json TEXT
        );
        """
    )
    conn.close()


def _seed_segment_rows(db_path: Path, *, project_id: str = "p1") -> None:
    conn = sqlite3.connect(db_path)
    conn.executemany(
        "INSERT INTO chapter_heads VALUES (?, ?, ?)",
        [(project_id, ch, f"v{ch}") for ch in range(1, 11)],
    )
    # up_to=10 -> next_audit=12；与运行时 find_orphaned 同语义（silent > threshold 才算孤儿）
    conn.executemany(
        "INSERT INTO setting_tracking VALUES (?, ?, ?, ?, ?)",
        [
            (project_id, "k.boundary", "active", "critical", 9),   # 12-9=3，不 orphan
            (project_id, "k.orphan", "active", "critical", 8),     # 12-8=4>3 → critical
            (project_id, "k.bg", "active", "background", 6),       # 12-6=6>5 → total
            (project_id, "k.null", "active", "critical", None),    # 从未提及，不计
            (project_id, "k.done", "resolved", "critical", 1),     # 非 active，不计
        ],
    )
    conn.commit()
    conn.close()


def _store_profile_override(db_path: Path, profile: GenreRuntimeProfile) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO genre_runtime_profiles VALUES (?, ?, ?)",
        (profile.genre, profile.version, json.dumps(profile.model_dump(mode="json"))),
    )
    conn.commit()
    conn.close()


class TestSegmentAuditThresholds:
    def test_threshold_boundary_matches_runtime(self, tmp_path: Path) -> None:
        db = tmp_path / "seg.db"
        _init_segment_db(db)
        _seed_segment_rows(db)
        report = collect_segment_audit(db, project_id="p1", up_to=10)
        assert report.critical_orphans == 1
        assert report.total_orphans == 2

    def test_genre_registry_profile_matches_default(self, tmp_path: Path) -> None:
        db = tmp_path / "seg.db"
        _init_segment_db(db)
        _seed_segment_rows(db)
        report = collect_segment_audit(db, project_id="p1", up_to=10, genre="wuxia")
        assert report.critical_orphans == 1
        assert report.total_orphans == 2

    def test_db_override_replaces_thresholds(self, tmp_path: Path) -> None:
        db = tmp_path / "seg.db"
        _init_segment_db(db)
        _seed_segment_rows(db)
        override = GenreRuntimeProfile(genre="wuxia")
        override.continuity.orphaned_thresholds = {
            key: 99 for key in override.continuity.orphaned_thresholds
        }
        _store_profile_override(db, override)

        with_override = collect_segment_audit(db, project_id="p1", up_to=10, genre="wuxia")
        assert with_override.critical_orphans == 0
        assert with_override.total_orphans == 0

        legacy = collect_segment_audit(db, project_id="p1", up_to=10)
        assert legacy.critical_orphans == 1
        assert legacy.total_orphans == 2

    def test_override_same_as_default_keeps_registry(self, tmp_path: Path) -> None:
        db = tmp_path / "seg.db"
        _init_segment_db(db)
        _seed_segment_rows(db)
        _store_profile_override(db, GenreRuntimeProfile(genre="wuxia"))
        report = collect_segment_audit(db, project_id="p1", up_to=10, genre="wuxia")
        assert report.critical_orphans == 1
        assert report.total_orphans == 2

    def test_unknown_genre_falls_back_to_scifi_default(self, tmp_path: Path) -> None:
        db = tmp_path / "seg.db"
        _init_segment_db(db)
        _seed_segment_rows(db)
        report = collect_segment_audit(db, project_id="p1", up_to=10, genre="no-such-genre")
        assert report.critical_orphans == 1
        assert report.total_orphans == 2


# ---------------------------------------------------------------------------
# 4. harness 成本预算接线
# ---------------------------------------------------------------------------


class TestHarnessCostBudget:
    def test_resolve_cost_budget_from_args(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SONGYAN_RUN_COST_BUDGET", raising=False)
        args = SimpleNamespace(cost_budget=2.5)
        assert HARNESS.resolve_cost_budget(args) == 2.5

    def test_resolve_cost_budget_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SONGYAN_RUN_COST_BUDGET", "1.5")
        args = SimpleNamespace(cost_budget=None)
        assert HARNESS.resolve_cost_budget(args) == 1.5

    def test_resolve_cost_budget_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SONGYAN_RUN_COST_BUDGET", raising=False)
        args = SimpleNamespace(cost_budget=None)
        assert HARNESS.resolve_cost_budget(args) is None

    def test_to_plan_carries_cost_budget(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SONGYAN_RUN_COST_BUDGET", raising=False)
        args = SimpleNamespace(
            to=125,
            run_id=None,
            dry_run=True,
            baseline=Path("tasks/189-scifi-ch200-baseline.json"),
            cost_budget=3.0,
        )
        plan = HARNESS.build_to_plan(
            genre="wuxia", args=args, paths=HARNESS.harness_paths("wuxia", tmp_path)
        )
        assert plan["cost_budget"] == 3.0
        assert "--cost-budget" in plan["wrapper_command"]

    def test_real_to_without_budget_fails(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SONGYAN_RUN_COST_BUDGET", raising=False)
        rc = HARNESS.main(
            ["--to", "125", "--genre", "wuxia", "--work-dir", str(tmp_path)]
        )
        assert rc == 2

    def test_dry_run_to_without_budget_ok(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SONGYAN_RUN_COST_BUDGET", raising=False)
        rc = HARNESS.main(
            ["--to", "125", "--genre", "wuxia", "--work-dir", str(tmp_path), "--dry-run"]
        )
        assert rc == 0

    def test_apply_cost_budget_updates_settings(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from songyan.config import settings

        monkeypatch.setattr(settings, "run_cost_budget", 0.0)
        HARNESS.apply_cost_budget(4.25)
        assert settings.run_cost_budget == 4.25


class TestHarnessEnsureTargetSchema:
    async def test_ensure_target_schema_migrates_old_db(self, tmp_path: Path) -> None:
        """193.u: 旧 source 复制库缺 pause_reason 列时，--to 前必须先迁移."""
        db = tmp_path / "old.db"
        conn = sqlite3.connect(db)
        conn.executescript(
            "CREATE TABLE projects (project_id TEXT PRIMARY KEY);"
            "CREATE TABLE project_runs (run_id TEXT PRIMARY KEY, project_id TEXT, "
            "status TEXT, current_chapter INTEGER);"
        )
        conn.close()

        await HARNESS.ensure_target_schema(db)

        check = sqlite3.connect(db)
        cols = {row[1] for row in check.execute("PRAGMA table_info(project_runs)")}
        assert "pause_reason" in cols
        check.close()

    async def test_ensure_target_schema_idempotent(self, tmp_path: Path) -> None:
        db = tmp_path / "old.db"
        conn = sqlite3.connect(db)
        conn.executescript(
            "CREATE TABLE projects (project_id TEXT PRIMARY KEY);"
            "CREATE TABLE project_runs (run_id TEXT PRIMARY KEY, project_id TEXT, "
            "status TEXT, current_chapter INTEGER);"
        )
        conn.close()

        await HARNESS.ensure_target_schema(db)
        await HARNESS.ensure_target_schema(db)

        check = sqlite3.connect(db)
        cols = {row[1] for row in check.execute("PRAGMA table_info(project_runs)")}
        assert "pause_reason" in cols
        check.close()


class TestHarnessStatusRunInfo:
    def _seed_status_fixture(
        self, tmp_path: Path, *, with_pause_reason: bool
    ) -> object:
        paths = HARNESS.harness_paths("wuxia", tmp_path)
        tmp_path.mkdir(parents=True, exist_ok=True)
        paths.project_file.write_text(
            json.dumps({"project_id": "p1", "run_id": "r1"}), encoding="utf-8"
        )
        pause_col = ", pause_reason TEXT" if with_pause_reason else ""
        conn = sqlite3.connect(paths.db)
        conn.executescript(
            "CREATE TABLE chapter_heads ("
            "project_id TEXT, chapter_number INTEGER, accepted_version_id TEXT);"
            "CREATE TABLE project_runs (run_id TEXT, project_id TEXT, status TEXT, "
            f"current_chapter INTEGER, total_cost REAL, updated_at TEXT{pause_col});"
        )
        conn.execute("INSERT INTO chapter_heads VALUES ('p1', 1, 'v1')")
        if with_pause_reason:
            conn.execute(
                "INSERT INTO project_runs VALUES "
                "('r1', 'p1', 'paused', 5, 1.5, '2026-07-28', 'user_requested')"
            )
        else:
            conn.execute(
                "INSERT INTO project_runs VALUES ('r1', 'p1', 'paused', 5, 1.5, '2026-07-28')"
            )
        conn.commit()
        conn.close()
        return paths

    def test_status_shows_run_and_budget(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        paths = self._seed_status_fixture(tmp_path, with_pause_reason=True)
        monkeypatch.setenv("SONGYAN_RUN_COST_BUDGET", "2.0")
        payload = HARNESS.build_status_payload("wuxia", paths)
        assert payload["run"]["status"] == "paused"
        assert payload["run"]["pause_reason"] == "user_requested"
        assert payload["run"]["total_cost"] == 1.5
        assert payload["cost_budget"] == 2.0

    def test_status_without_pause_reason_column(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        paths = self._seed_status_fixture(tmp_path, with_pause_reason=False)
        monkeypatch.delenv("SONGYAN_RUN_COST_BUDGET", raising=False)
        payload = HARNESS.build_status_payload("wuxia", paths)
        assert payload["run"]["status"] == "paused"
        assert payload["run"]["pause_reason"] is None
        assert payload["cost_budget"] is None
