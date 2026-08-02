"""Task 213: run bundle service tests."""

from __future__ import annotations

import json
import zipfile
from datetime import datetime
from pathlib import Path

import pytest

from songyan.config import settings
from songyan.db.llm_call_usage_repo import LlmCallUsageRepository
from songyan.db.migrations import init_schema
from songyan.db.project_run_repo import ProjectRunRepository
from songyan.db.repository import ProjectRepository
from songyan.exceptions import SongyanError
from songyan.models import ProjectSetting
from songyan.models.project_run import ProjectRunState
from songyan.models.run_log import ChapterRunLog
from songyan.services.run_bundle_service import (
    BUNDLE_JSON_MEMBER,
    BUNDLE_MARKDOWN_MEMBER,
    LOG_INDEX_MEMBER,
    RUN_BUNDLE_FORMAT,
    bundle_run,
)


@pytest.fixture
async def run_bundle_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "bundle.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    monkeypatch.setattr(settings, "llm_api_key", "secret-test-key")
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            title="诊断包项目",
            genre_id="scifi",
            mode_id="webnovel",
            protagonist_name="林远",
        ),
        "proj-bundle",
    )
    await ProjectRunRepository().create(
        ProjectRunState(
            run_id="run-bundle",
            project_id="proj-bundle",
            chapter_range_start=1,
            chapter_range_end=2,
            current_chapter=2,
            completed_chapters=[1],
            failed_chapters=[2],
            total_cost=0.12,
            status="failed",
            pause_reason="chapter_failed",
        )
    )
    await LlmCallUsageRepository().record(
        run_id="run-bundle",
        project_id="proj-bundle",
        chapter_number=1,
        agent="writer",
        stage="draft",
        model="test-model",
        prompt_tokens=100,
        completion_tokens=50,
        cost_cny=0.12,
        token_source="estimate",
        cost_source="pricing_estimate",
    )

    log_dir = tmp_path / "logs" / "chapter_runs"
    report_dir = tmp_path / "logs" / "reports"
    log_dir.mkdir(parents=True)
    report_dir.mkdir(parents=True)
    logs = [
        ChapterRunLog(
            log_id="log-1",
            run_id="run-bundle",
            project_id="proj-bundle",
            chapter_number=1,
            started_at=datetime(2026, 1, 1, 0, 0),
            finished_at=datetime(2026, 1, 1, 0, 1),
            success=True,
            word_count=3200,
            budget_used=0.8,
            quality_gate_passed=True,
            settlement_success=True,
            summary_success=True,
            duration_sec=60,
        ),
        ChapterRunLog(
            log_id="log-2",
            run_id="run-bundle",
            project_id="proj-bundle",
            chapter_number=2,
            started_at=datetime(2026, 1, 1, 0, 2),
            finished_at=datetime(2026, 1, 1, 0, 3),
            success=False,
            error_stage="llm",
            error=f"secret-test-key leaked at {tmp_path / 'private' / 'trace.log'}",
            word_count=0,
            budget_used=None,
            quality_gate_passed=False,
            gate_triggered=True,
            gate_reasons=["quality_gate_fail_streak"],
            duration_sec=30,
        ),
    ]
    (log_dir / "run-bundle.jsonl").write_text(
        "\n".join(log.to_jsonl() for log in logs) + "\n",
        encoding="utf-8",
    )
    (report_dir / "report-run-bundle.md").write_text(
        "# report\nsecret-test-key should not be bundled\n",
        encoding="utf-8",
    )
    return db_path


@pytest.mark.asyncio
async def test_run_bundle_contains_json_markdown_log_index_and_no_secrets(
    run_bundle_db: Path,
    tmp_path: Path,
) -> None:
    result = await bundle_run("run-bundle", output=tmp_path / "bundles")

    assert result.bundle_path.is_file()
    with zipfile.ZipFile(result.bundle_path) as archive:
        names = set(archive.namelist())
        assert BUNDLE_JSON_MEMBER in names
        assert BUNDLE_MARKDOWN_MEMBER in names
        assert LOG_INDEX_MEMBER in names
        bundle = json.loads(archive.read(BUNDLE_JSON_MEMBER).decode("utf-8"))
        markdown = archive.read(BUNDLE_MARKDOWN_MEMBER).decode("utf-8")
        index = json.loads(archive.read(LOG_INDEX_MEMBER).decode("utf-8"))
        all_text = "\n".join(
            archive.read(name).decode("utf-8") for name in sorted(names)
        )

    assert bundle["format"] == RUN_BUNDLE_FORMAT
    assert bundle["run"]["run_id"] == "run-bundle"
    assert bundle["project"]["project_id"] == "proj-bundle"
    assert bundle["chapters"]["summary"]["failed"] == [2]
    assert bundle["chapters"]["items"][1]["failure_category"] == "config_error"
    assert bundle["cost"]["total_cost_cny"] == pytest.approx(0.12)
    assert bundle["quality_signals"]["from_run_log"]["quality_gate"]["fail"] == 1
    assert bundle["quality_signals"]["external"]["t9"]["status"] == "external_not_embedded"
    assert index["content_included"] is False
    assert "Songyan Run Bundle" in markdown
    assert "secret-test-key" not in all_text
    assert str(tmp_path) not in all_text
    assert "report-run-bundle.md" in all_text


@pytest.mark.asyncio
async def test_run_bundle_missing_log_fails(run_bundle_db: Path, tmp_path: Path) -> None:
    with pytest.raises(SongyanError, match="run log not found"):
        await bundle_run("missing-run", output=tmp_path / "bundles")


@pytest.mark.asyncio
async def test_run_bundle_rejects_project_id_mismatch(
    run_bundle_db: Path,
    tmp_path: Path,
) -> None:
    with pytest.raises(SongyanError, match="project_id mismatch"):
        await bundle_run(
            "run-bundle",
            project_id="other-project",
            output=tmp_path / "bundles",
        )
