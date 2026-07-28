"""Task 193.w tests — 段审计判定消费修复.

F1：five-gate health 门输出报告章号（health_report_chapter），192.aw 型
stale health 假 FAIL 可鉴别；F2：harness run_audit 生成 verdict 块
（segment halt_would_fire 上浮）；F3：stale health 预警（lag>=2）。
判定逻辑本身不变。
"""

from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace

from songyan.evals.five_gate_acceptance import (
    BaselinePoint,
    collect_metrics,
    evaluate_metrics,
)

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
# F1 · five-gate health 报告章号
# ---------------------------------------------------------------------------


def _init_gate_db(path: Path, *, health_rows: list[tuple[int, float]]) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE chapter_heads (
            project_id TEXT, chapter_number INTEGER, accepted_version_id TEXT, status TEXT
        );
        CREATE TABLE chapter_versions (
            version_id TEXT, project_id TEXT, chapter_number INTEGER,
            content TEXT, parent_version_id TEXT
        );
        CREATE TABLE review_reports (chapter_version_id TEXT, audit_type TEXT, issues TEXT);
        CREATE TABLE context_snapshots (project_id TEXT, chapter_number INTEGER, budget_used REAL);
        CREATE TABLE foreshadowings (
            project_id TEXT, expected_resolve_chapter INTEGER, status TEXT
        );
        CREATE TABLE continuity_reports (
            project_id TEXT, checked_up_to_chapter INTEGER, overall_health_score REAL
        );
        """
    )
    text = "甲" * 500
    conn.executemany(
        "INSERT INTO chapter_heads VALUES (?, ?, ?, ?)",
        [("p1", 1, "v1", "accepted"), ("p1", 2, "v2", "accepted")],
    )
    conn.executemany(
        "INSERT INTO chapter_versions VALUES (?, ?, ?, ?, ?)",
        [("v1", "p1", 1, text, None), ("v2", "p1", 2, text, None)],
    )
    conn.executemany(
        "INSERT INTO review_reports VALUES (?, ?, ?)",
        [("v1", "merged", "[]"), ("v2", "merged", "[]")],
    )
    conn.executemany(
        "INSERT INTO context_snapshots VALUES (?, ?, ?)",
        [("p1", 1, 0.7), ("p1", 2, 0.8)],
    )
    conn.executemany(
        "INSERT INTO continuity_reports VALUES (?, ?, ?)",
        [("p1", ch, score) for ch, score in health_rows],
    )
    conn.commit()
    conn.close()


def _baseline() -> BaselinePoint:
    return BaselinePoint(
        up_to=2,
        accepted=2,
        budget_used_peak=0.99,
        overdue_foreshadowing=10,
        health_latest=9.0,
        ced_per_1k_words=3.0,
    )


class TestHealthReportChapter:
    def test_chapter_surfaced_in_metrics(self, tmp_path: Path) -> None:
        db = tmp_path / "gate.db"
        _init_gate_db(db, health_rows=[(1, 8.5), (2, 8.1)])
        metrics = collect_metrics(db, project_id="p1", up_to=2, genre="wuxia")
        assert metrics.health_latest == 8.1
        assert metrics.health_report_chapter == 2
        assert metrics.to_dict()["health_report_chapter"] == 2

    def test_latest_wins_when_multiple_reports(self, tmp_path: Path) -> None:
        db = tmp_path / "gate.db"
        _init_gate_db(db, health_rows=[(1, 7.0), (2, 8.5)])
        metrics = collect_metrics(db, project_id="p1", up_to=2, genre="wuxia")
        assert metrics.health_latest == 8.5
        assert metrics.health_report_chapter == 2

    def test_no_report_gives_none(self, tmp_path: Path) -> None:
        db = tmp_path / "gate.db"
        _init_gate_db(db, health_rows=[])
        metrics = collect_metrics(db, project_id="p1", up_to=2, genre="wuxia")
        assert metrics.health_latest is None
        assert metrics.health_report_chapter is None

    def test_gate_detail_includes_chapter(self, tmp_path: Path) -> None:
        db = tmp_path / "gate.db"
        _init_gate_db(db, health_rows=[(1, 8.5)])
        metrics = collect_metrics(db, project_id="p1", up_to=2, genre="wuxia")
        report = evaluate_metrics(metrics, _baseline())
        health_gate = next(g for g in report.gates if g.name == "health")
        assert "@Ch1" in health_gate.detail
        assert health_gate.passed is True

    def test_gate_detail_marks_missing_report(self, tmp_path: Path) -> None:
        db = tmp_path / "gate.db"
        _init_gate_db(db, health_rows=[])
        metrics = collect_metrics(db, project_id="p1", up_to=2, genre="wuxia")
        report = evaluate_metrics(metrics, _baseline())
        health_gate = next(g for g in report.gates if g.name == "health")
        assert "no continuity report" in health_gate.detail
        assert health_gate.passed is False


# ---------------------------------------------------------------------------
# F2/F3 · harness run_audit verdict 块
# ---------------------------------------------------------------------------

_FG_JSON = json.dumps(
    {
        "verdict": "PASS",
        "metrics": {"health_report_chapter": 124, "health_latest": 8.1},
        "gates": [],
    }
)
_SA_JSON = json.dumps(
    {"critical_orphans": 0, "total_orphans": 5, "halt_would_fire": False}
)


def _fake_run_capture(command: list[str], env: object = None) -> SimpleNamespace:
    joined = " ".join(command)
    if "five_gate_check.py" in joined:
        return SimpleNamespace(stdout=_FG_JSON, returncode=0)
    if "segment_audit.py" in joined:
        return SimpleNamespace(stdout=_SA_JSON, returncode=0)
    return SimpleNamespace(stdout="# metrics\n", returncode=0)


def _audit_plan(tmp_path: Path, *, up_to: int = 125) -> dict:
    db = tmp_path / "target.db"
    db.touch()
    return {
        "task": "191",
        "action": "audit",
        "dry_run": False,
        "genre": "wuxia",
        "up_to": up_to,
        "paths": {
            "db": db.as_posix(),
            "five_gate": (tmp_path / "fg.json").as_posix(),
            "segment_audit": (tmp_path / "sa.json").as_posix(),
            "metrics": (tmp_path / "metrics.md").as_posix(),
        },
        "commands": {
            "five_gate": ["python", "scripts/five_gate_check.py"],
            "segment_audit": ["python", "scripts/segment_audit.py"],
            "metrics": ["songyan", "metrics"],
        },
        "environment": {"DATABASE_URL": f"sqlite:///{db.as_posix()}"},
    }


class TestRunAuditVerdict:
    def test_verdict_block_complete(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setattr(HARNESS, "_run_capture", _fake_run_capture)
        payload = HARNESS.run_audit(_audit_plan(tmp_path))
        verdict = payload["verdict"]
        assert verdict["five_gate"] == "PASS"
        assert verdict["segment_halt_would_fire"] is False
        assert verdict["critical_orphans"] == 0
        assert verdict["health_report_chapter"] == 124
        assert verdict["stale_health_warning"] is False
        assert "health_note" not in verdict

    def test_stale_health_warning(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        stale_fg = json.dumps(
            {"verdict": "FAIL", "metrics": {"health_report_chapter": 123}, "gates": []}
        )

        def fake(command: list[str], env: object = None) -> SimpleNamespace:
            if "five_gate_check.py" in " ".join(command):
                return SimpleNamespace(stdout=stale_fg, returncode=0)
            return _fake_run_capture(command, env)

        monkeypatch.setattr(HARNESS, "_run_capture", fake)
        payload = HARNESS.run_audit(_audit_plan(tmp_path, up_to=125))
        verdict = payload["verdict"]
        assert verdict["five_gate"] == "FAIL"
        assert verdict["stale_health_warning"] is True
        assert "continuity audit" in verdict["health_note"]

    def test_segment_halt_surfaced(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        halt_sa = json.dumps(
            {"critical_orphans": 3, "total_orphans": 9, "halt_would_fire": True}
        )

        def fake(command: list[str], env: object = None) -> SimpleNamespace:
            if "segment_audit.py" in " ".join(command):
                return SimpleNamespace(stdout=halt_sa, returncode=0)
            return _fake_run_capture(command, env)

        monkeypatch.setattr(HARNESS, "_run_capture", fake)
        payload = HARNESS.run_audit(_audit_plan(tmp_path))
        verdict = payload["verdict"]
        assert verdict["segment_halt_would_fire"] is True
        assert verdict["critical_orphans"] == 3

    def test_stale_boundary_lag_one_no_warning(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # _FG_JSON health_report_chapter=124, up_to=125 -> lag 1 -> no warning
        monkeypatch.setattr(HARNESS, "_run_capture", _fake_run_capture)
        payload = HARNESS.run_audit(_audit_plan(tmp_path, up_to=125))
        assert payload["verdict"]["stale_health_warning"] is False
