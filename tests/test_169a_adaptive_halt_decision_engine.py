"""Task 169a: adaptive halt decision engine tests."""

from __future__ import annotations

from pathlib import Path

import aiosqlite

from songyan.db.adaptive_halt_repo import AdaptiveHaltDecisionRepository
from songyan.db.migrations import _EXPECTED_TABLES
from songyan.db.repository import ProjectRepository
from songyan.evals.adaptive_halt import evaluate_adaptive_halt
from songyan.models import (
    AdaptiveGateDataPlaneReport,
    AdaptiveGateSignalWindow,
    AdaptiveHaltPolicy,
    ProjectSetting,
)

PID = "proj-169a"


async def _seed_project(project_id: str = PID) -> str:
    await ProjectRepository().create(
        ProjectSetting(title=project_id, genre_id="scifi", protagonist_name="林渊"),
        project_id=project_id,
    )
    return project_id


def _status_counts(*, present: bool = True) -> dict[str, dict[str, int]]:
    domains = ("continuity", "quality", "literary", "cleanliness", "context", "narrative")
    return {
        domain: {
            "present": 1 if present else 0,
            "missing": 0 if present else 1,
            "insufficient": 0,
            "observation": 0,
        }
        for domain in domains
    }


def _report(
    *,
    chapter_end: int = 20,
    windows: list[AdaptiveGateSignalWindow] | None = None,
    present: bool = True,
) -> AdaptiveGateDataPlaneReport:
    return AdaptiveGateDataPlaneReport(
        project_id=PID,
        run_id="run-169a",
        chapter_start=1,
        chapter_end=chapter_end,
        window_size=5,
        snapshot_count=chapter_end,
        source_status_counts=_status_counts(present=present),
        windows=windows or [],
    )


def _window(**kwargs) -> AdaptiveGateSignalWindow:
    base = {
        "start_chapter": 16,
        "end_chapter": 20,
        "sample_count": 5,
        "window_size": 5,
        "source_status_counts": _status_counts(present=True),
    }
    base.update(kwargs)
    return AdaptiveGateSignalWindow(**base)


class TestAdaptiveHaltDecisionSchema:
    async def test_table_registered_and_created(self, test_db: Path) -> None:
        assert "adaptive_halt_decisions" in _EXPECTED_TABLES
        async with aiosqlite.connect(test_db) as conn:
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                ("adaptive_halt_decisions",),
            )
            row = await cursor.fetchone()
        assert row is not None


class TestAdaptiveHaltDecisionEngine:
    def test_empty_report_observes(self) -> None:
        decision = evaluate_adaptive_halt(_report(windows=[]))

        assert decision.status == "observe"
        assert decision.reasons[0].code == "insufficient_samples"

    def test_missing_sources_observe(self) -> None:
        decision = evaluate_adaptive_halt(
            _report(
                present=False,
                windows=[
                    _window(
                        health_min=1.0,
                        p1_median=99.0,
                        degraded_ratio=1.0,
                    )
                ],
            )
        )

        assert decision.status == "observe"
        assert decision.reasons[0].code == "insufficient_samples"

    def test_warmup_anomaly_does_not_halt(self) -> None:
        decision = evaluate_adaptive_halt(
            _report(
                chapter_end=5,
                windows=[
                    _window(
                        start_chapter=1,
                        end_chapter=5,
                        health_min=4.0,
                        p1_median=3.0,
                        degraded_ratio=0.8,
                    )
                ],
            ),
            AdaptiveHaltPolicy(warmup_chapters=10),
        )

        assert decision.status == "warn"
        assert {reason.code for reason in decision.reasons} >= {
            "health_p1_spike",
            "quality_debt_streak",
            "warmup_protection",
        }

    def test_single_signal_spike_warns(self) -> None:
        decision = evaluate_adaptive_halt(
            _report(
                windows=[
                    _window(
                        health_min=4.0,
                        p1_median=3.0,
                    )
                ],
            ),
            AdaptiveHaltPolicy(warmup_chapters=0),
        )

        assert decision.status == "warn"
        assert [reason.code for reason in decision.reasons] == ["health_p1_spike"]

    def test_multi_signal_degradation_is_halt_candidate_in_observe(self) -> None:
        decision = evaluate_adaptive_halt(
            _report(
                windows=[
                    _window(
                        health_min=4.0,
                        p1_median=3.0,
                        degraded_ratio=0.7,
                    )
                ],
            ),
            AdaptiveHaltPolicy(warmup_chapters=0, mode="observe"),
        )

        assert decision.status == "halt_candidate"
        assert {reason.signal_domain for reason in decision.reasons} == {
            "continuity",
            "quality",
        }

    def test_multi_signal_degradation_can_halt_in_enforce(self) -> None:
        decision = evaluate_adaptive_halt(
            _report(
                windows=[
                    _window(
                        health_min=4.0,
                        p1_median=3.0,
                        degraded_ratio=0.7,
                    )
                ],
            ),
            AdaptiveHaltPolicy(warmup_chapters=0, mode="enforce"),
        )

        assert decision.status == "halt"

    def test_does_not_import_legacy_gates(self) -> None:
        import songyan.evals.adaptive_halt as adaptive_halt

        assert "evaluate_all_gates" not in adaptive_halt.__dict__
        assert "check_health_low_single_gate" not in adaptive_halt.__dict__


class TestAdaptiveHaltDecisionRepository:
    async def test_decision_ledger_round_trip(self, test_db: Path) -> None:
        await _seed_project()
        repo = AdaptiveHaltDecisionRepository()
        decision = evaluate_adaptive_halt(
            _report(
                windows=[
                    _window(
                        health_min=4.0,
                        p1_median=3.0,
                        degraded_ratio=0.7,
                    )
                ],
            ),
            AdaptiveHaltPolicy(warmup_chapters=0, mode="observe"),
        )

        await repo.create(decision)
        got = await repo.get(decision.decision_id)
        by_project = await repo.list_by_project(PID, run_id="run-169a")
        by_chapter = await repo.list_by_chapter(PID, 20, run_id="run-169a")

        assert got is not None
        assert got.status == "halt_candidate"
        assert got.run_id == "run-169a"
        assert got.reasons[0].code == "health_p1_spike"
        assert by_project == [got]
        assert by_chapter == [got]
