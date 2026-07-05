"""Task 168a: adaptive gate signal snapshot tests."""

from __future__ import annotations

from pathlib import Path

import aiosqlite

from songyan.db.adaptive_gate_repo import AdaptiveGateSignalRepository
from songyan.db.migrations import _EXPECTED_TABLES
from songyan.db.repository import ProjectRepository
from songyan.evals.adaptive_gate import build_adaptive_gate_signal_snapshot
from songyan.models import (
    AdaptiveGateContextSignals,
    AdaptiveGateSignalSnapshot,
    ProjectSetting,
)
from songyan.models.adaptive_gate import ADAPTIVE_GATE_SIGNAL_DOMAINS

PID = "proj-168a"


async def _seed_project(project_id: str = PID) -> str:
    await ProjectRepository().create(
        ProjectSetting(title=project_id, genre_id="scifi", protagonist_name="林渊"),
        project_id=project_id,
    )
    return project_id


class TestAdaptiveGateSignalSchema:
    async def test_table_registered_and_created(self, test_db: Path) -> None:
        assert "adaptive_gate_signal_snapshots" in _EXPECTED_TABLES
        async with aiosqlite.connect(test_db) as conn:
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                ("adaptive_gate_signal_snapshots",),
            )
            row = await cursor.fetchone()
            assert row is not None

            cursor = await conn.execute(
                "PRAGMA table_info(adaptive_gate_signal_snapshots)"
            )
            columns = {row[1]: row for row in await cursor.fetchall()}

        assert columns["source_status_json"][3] == 1
        assert columns["continuity_json"][4] == "'{}'"
        assert columns["run_id"][4] == "''"


class TestAdaptiveGateSignalModels:
    async def test_snapshot_model_defaults_are_complete(self) -> None:
        snapshot = AdaptiveGateSignalSnapshot(
            snapshot_id="ags-default",
            project_id=PID,
            chapter_number=1,
        )

        assert snapshot.run_id is None
        assert set(snapshot.source_status) == set(ADAPTIVE_GATE_SIGNAL_DOMAINS)
        assert all(status == "missing" for status in snapshot.source_status.values())
        assert snapshot.continuity.orphan_total == 0
        assert snapshot.quality.degraded_accept is False
        assert snapshot.context.context_emergency is False
        assert snapshot.narrative.schedule_missed_count == 0

    async def test_builder_marks_missing_and_present_sources(self) -> None:
        snapshot = build_adaptive_gate_signal_snapshot(
            project_id=PID,
            chapter_number=3,
            continuity={"health_score": 8.5, "orphan_total": 2},
            context=AdaptiveGateContextSignals(
                context_emergency=True,
                budget_used=1.2,
            ),
            source_status={"cleanliness": "observation"},
        )

        assert snapshot.snapshot_id == f"ags-{PID}-norun-3"
        assert snapshot.source_status["continuity"] == "present"
        assert snapshot.source_status["context"] == "present"
        assert snapshot.source_status["cleanliness"] == "observation"
        assert snapshot.source_status["quality"] == "missing"
        assert snapshot.continuity.health_score == 8.5
        assert snapshot.context.context_emergency is True


class TestAdaptiveGateSignalRepository:
    async def test_upsert_is_idempotent(self, test_db: Path) -> None:
        await _seed_project()
        repo = AdaptiveGateSignalRepository()
        first = build_adaptive_gate_signal_snapshot(
            project_id=PID,
            run_id="run-168a",
            chapter_number=1,
            snapshot_id="ags-first",
            continuity={"health_score": 8.0},
        )
        second = build_adaptive_gate_signal_snapshot(
            project_id=PID,
            run_id="run-168a",
            chapter_number=1,
            snapshot_id="ags-second",
            continuity={"health_score": 6.5, "p1_count": 2},
        )

        await repo.upsert(first)
        await repo.upsert(second)

        got = await repo.get(PID, 1, run_id="run-168a")
        rows = await repo.list_range(PID, 1, 1, run_id="run-168a")
        assert got is not None
        assert got.snapshot_id == "ags-second"
        assert got.continuity.health_score == 6.5
        assert got.continuity.p1_count == 2
        assert len(rows) == 1

    async def test_list_range_orders_by_chapter(self, test_db: Path) -> None:
        await _seed_project()
        repo = AdaptiveGateSignalRepository()
        await repo.upsert(
            build_adaptive_gate_signal_snapshot(
                project_id=PID,
                chapter_number=3,
                quality={"quality_gate_passed": True},
            )
        )
        await repo.upsert(
            build_adaptive_gate_signal_snapshot(
                project_id=PID,
                chapter_number=1,
                quality={"quality_gate_passed": False, "qg_false": True},
            )
        )

        rows = await repo.list_range(PID, 1, 3)

        assert [row.chapter_number for row in rows] == [1, 3]
        assert rows[0].quality.qg_false is True

    async def test_delete_range_scopes_to_project_run_and_range(
        self,
        test_db: Path,
    ) -> None:
        await _seed_project()
        repo = AdaptiveGateSignalRepository()
        await repo.upsert(
            build_adaptive_gate_signal_snapshot(
                project_id=PID,
                run_id="run-a",
                chapter_number=1,
            )
        )
        await repo.upsert(
            build_adaptive_gate_signal_snapshot(
                project_id=PID,
                run_id="run-a",
                chapter_number=2,
            )
        )
        await repo.upsert(
            build_adaptive_gate_signal_snapshot(
                project_id=PID,
                run_id="run-b",
                chapter_number=1,
            )
        )

        deleted = await repo.delete_range(PID, 1, 1, run_id="run-a")

        assert deleted == 1
        assert await repo.get(PID, 1, run_id="run-a") is None
        assert await repo.get(PID, 2, run_id="run-a") is not None
        assert await repo.get(PID, 1, run_id="run-b") is not None

    async def test_missing_sources_round_trip_as_missing(self, test_db: Path) -> None:
        await _seed_project()
        repo = AdaptiveGateSignalRepository()
        snapshot = build_adaptive_gate_signal_snapshot(
            project_id=PID,
            chapter_number=4,
        )

        await repo.upsert(snapshot)
        got = await repo.get(PID, 4)

        assert got is not None
        assert got.run_id is None
        assert all(status == "missing" for status in got.source_status.values())
        assert got.literary.conceptual_grounding_score is None
        assert got.narrative.schedule_active_count == 0

    async def test_json_fields_round_trip_with_typed_models(
        self,
        test_db: Path,
    ) -> None:
        await _seed_project()
        repo = AdaptiveGateSignalRepository()
        snapshot = build_adaptive_gate_signal_snapshot(
            project_id=PID,
            run_id="run-json",
            chapter_number=5,
            continuity={
                "health_score": 7.7,
                "p1_count": 1,
                "orphan_total": 4,
                "forgotten_count": 2,
            },
            quality={
                "quality_gate_passed": False,
                "degraded_accept": True,
                "convergence_failed": False,
                "qg_false": True,
                "revision_rounds": 2,
            },
            literary={
                "literary_quality_score": 7.0,
                "character_autonomy_score": 6.5,
                "conceptual_grounding_score": 6.0,
                "fissure_preservation_score": 7.5,
            },
            cleanliness={
                "meta_tag_leak_count": 0,
                "duplicate_paragraph_count": 1,
                "timeline_conflict_count": 3,
            },
            context={
                "context_emergency": True,
                "budget_used": 1.1,
                "db_size_bytes": 1024,
                "scan_latency_ms": 12.5,
            },
            narrative={
                "schedule_injected_count": 2,
                "schedule_satisfied_count": 1,
                "schedule_missed_count": 1,
                "overdue_foreshadowing_count": 3,
            },
            source_status={"cleanliness": "observation"},
        )

        await repo.upsert(snapshot)
        got = await repo.get(PID, 5, run_id="run-json")

        assert got is not None
        assert got.source_status["cleanliness"] == "observation"
        assert got.continuity.orphan_total == 4
        assert got.quality.degraded_accept is True
        assert got.literary.conceptual_grounding_score == 6.0
        assert got.cleanliness.timeline_conflict_count == 3
        assert got.context.scan_latency_ms == 12.5
        assert got.narrative.schedule_missed_count == 1
