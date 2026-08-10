"""Task 221: V12 startup smoke harness tests."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from songyan.config import settings
from songyan.db.migrations import init_schema
from songyan.db.project_run_repo import ProjectRunRepository
from songyan.db.repository import ProjectRepository
from songyan.models import ProjectSetting
from songyan.models.project_run import ProjectRunResult, ProjectRunState
from songyan.models.run_log import ChapterRunLog
from songyan.services.startup_smoke_harness import (
    chapter_range_for_startup_smoke,
    run_startup_smoke_harness,
)


def _spec_data(chapters: tuple[int, ...] = (1, 2, 3)) -> dict[str, Any]:
    return {
        "version": "v12.1",
        "stage": "startup_ch1_3",
        "word_count": {"target": 3000, "hard_min": 2700, "hard_max": 3300},
        "chapters": {
            str(chapter): {
                "allowed_beats": [
                    {
                        "visible_action": f"沈砚复核 Ch{chapter} 当前数值链。",
                        "current_friction": "责任质量归属与实测质量不一致。",
                        "feedback": "终端只返回当前数值链。",
                        "micro_decision": "沈砚决定先保存离线记录。",
                        "landing": "缺口被写入本地记录。",
                    }
                ],
                "required_phrases": [],
                "forbidden_literals": [],
                "forbidden_patterns": [],
                "stage_policy": {},
            }
            for chapter in chapters
        },
    }


async def _seed_project(project_id: str = "proj-startup") -> None:
    await ProjectRepository().create(
        ProjectSetting(
            title="启动测试",
            genre_id="scifi",
            mode_id="webnovel",
            protagonist_name="沈砚",
        ),
        project_id,
    )


def _write_spec(root: Path, chapters: tuple[int, ...] = (1, 2, 3)) -> None:
    planning = root / "planning"
    planning.mkdir(parents=True)
    (planning / "supervision_spec.json").write_text(
        json.dumps(_spec_data(chapters), ensure_ascii=False),
        encoding="utf-8",
    )


@pytest.fixture
async def startup_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "startup.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    return db_path


def test_chapter_range_for_startup_smoke() -> None:
    assert chapter_range_for_startup_smoke("ch1_only") == (1, 1)
    assert chapter_range_for_startup_smoke("ch1_3") == (1, 3)


@pytest.mark.anyio
async def test_dry_run_writes_report_and_does_not_call_pipeline(
    startup_db: Path,
    tmp_path: Path,
) -> None:
    await _seed_project()
    _write_spec(tmp_path)
    called = False

    async def fake_runner(**_kwargs: Any) -> ProjectRunResult:
        nonlocal called
        called = True
        raise AssertionError("dry-run must not call pipeline")

    result = await run_startup_smoke_harness(
        project_id="proj-startup",
        mode="ch1_only",
        dry_run=True,
        project_root=tmp_path,
        output_dir=tmp_path / "startup-output",
        pipeline_runner=fake_runner,
    )

    assert startup_db.exists()
    assert called is False
    assert result.status == "dry_run"
    assert result.run_id is None
    assert result.preflight_findings == []
    assert result.artifact("reading_review") is not None
    assert result.artifact("harness_report") is not None
    assert result.artifact("export") is not None
    assert result.artifact("export").status == "safe_no_accepted"

    review_path = Path(result.artifact("reading_review").path or "")
    assert review_path.exists()
    review_text = review_path.read_text(encoding="utf-8")
    assert "GO" in review_text
    assert "STOP" in review_text
    assert "REVISE-METHOD" in review_text


@pytest.mark.anyio
async def test_missing_supervision_spec_blocks_preflight(
    startup_db: Path,
    tmp_path: Path,
) -> None:
    await _seed_project()

    result = await run_startup_smoke_harness(
        project_id="proj-startup",
        mode="ch1_3",
        dry_run=True,
        project_root=tmp_path,
        output_dir=tmp_path / "startup-output",
    )

    assert startup_db.exists()
    assert result.status == "preflight_failed"
    assert any("supervision spec invalid" in item for item in result.preflight_findings)
    assert result.artifact("harness_report") is not None


@pytest.mark.anyio
async def test_failed_run_can_still_build_bundle(
    startup_db: Path,
    tmp_path: Path,
) -> None:
    await _seed_project()
    _write_spec(tmp_path)
    await ProjectRunRepository().create(
        ProjectRunState(
            run_id="run-startup-failed",
            project_id="proj-startup",
            chapter_range_start=1,
            chapter_range_end=1,
            current_chapter=1,
            completed_chapters=[],
            failed_chapters=[1],
            status="failed",
            pause_reason="chapter_failed",
        )
    )
    log_dir = tmp_path / "logs" / "chapter_runs"
    log_dir.mkdir(parents=True)
    log = ChapterRunLog(
        log_id="log-startup-1",
        run_id="run-startup-failed",
        project_id="proj-startup",
        chapter_number=1,
        started_at=datetime(2026, 1, 1, 0, 0),
        finished_at=datetime(2026, 1, 1, 0, 1),
        success=False,
        error_stage="writer",
        error="mock failure",
        word_count=0,
        duration_sec=60,
    )
    (log_dir / "run-startup-failed.jsonl").write_text(
        log.to_jsonl() + "\n",
        encoding="utf-8",
    )

    result = await run_startup_smoke_harness(
        project_id="proj-startup",
        mode="ch1_only",
        dry_run=True,
        project_root=tmp_path,
        output_dir=tmp_path / "startup-output",
        run_id="run-startup-failed",
    )

    assert startup_db.exists()
    assert result.status == "dry_run"
    assert result.artifact("run_report").status == "written"
    assert result.artifact("bundle").status == "written"
    assert Path(result.artifact("bundle").path or "").exists()


@pytest.mark.anyio
async def test_real_smoke_uses_injected_runner_without_direct_llm(
    startup_db: Path,
    tmp_path: Path,
) -> None:
    await _seed_project()
    _write_spec(tmp_path)
    captured: dict[str, Any] = {}

    async def fake_runner(**kwargs: Any) -> ProjectRunResult:
        captured.update(kwargs)
        return ProjectRunResult(
            project_id="proj-startup",
            run_id="run-fake-real",
            chapters_completed=[1],
            chapters_failed=[],
            final_status="completed",
        )

    result = await run_startup_smoke_harness(
        project_id="proj-startup",
        mode="ch1_only",
        dry_run=False,
        project_root=tmp_path,
        output_dir=tmp_path / "startup-output",
        pipeline_runner=fake_runner,
    )

    assert startup_db.exists()
    assert result.status == "completed"
    assert result.run_id == "run-fake-real"
    assert captured["project_id"] == "proj-startup"
    assert captured["chapter_range"] == (1, 1)
    assert captured["auto_confirm"] is True
    assert captured["on_failure"] == "isolate"
