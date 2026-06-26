"""Tests for _run_logger — chapter run log collection and JSONL writing."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from songyan.models import ChapterRunLog
from songyan.models.review import (
    LLMAuditResult,
    MergedReviewReport,
    ReviewCategory,
    ReviewIssue,
    RuleAuditResult,
)
from songyan.workflows._run_logger import (
    _compute_rule_score,
    build_chapter_run_log,
    collect_chapter_metrics,
    write_run_log,
)

# ---------------------------------------------------------------------------
# _compute_rule_score
# ---------------------------------------------------------------------------


def test_compute_rule_score_perfect() -> None:
    """无任何违规时 score 为 1.0."""
    ra = RuleAuditResult(
        ai_tell_count=0,
        fatigue_word_count=0,
        has_opening_hook=True,
        has_ending_hook=True,
    )
    assert _compute_rule_score(ra) == 1.0


def test_compute_rule_score_with_violations() -> None:
    """有违规时按公式扣分."""
    ra = RuleAuditResult(
        ai_tell_count=2,
        fatigue_word_count=5,
        has_opening_hook=False,
        has_ending_hook=False,
    )
    score = _compute_rule_score(ra)
    expected = 1.0 - 0.1 - 0.1 - 0.1 - 0.05
    assert score == round(expected, 2)


def test_compute_rule_score_none() -> None:
    """rule_audit 为 None 时返回 0.0."""
    assert _compute_rule_score(None) == 0.0


# ---------------------------------------------------------------------------
# collect_chapter_metrics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_metrics_with_data() -> None:
    """数据库有数据时正确收集指标."""
    version = AsyncMock()
    version.word_count = 3500

    report = MergedReviewReport(
        chapter_version_id="v-1",
        rule_audit=RuleAuditResult(
            ai_tell_count=1,
            fatigue_word_count=2,
            has_opening_hook=True,
            has_ending_hook=True,
        ),
        llm_audit=LLMAuditResult(
            issues=[
                ReviewIssue(
                    issue_id="i1",
                    category=ReviewCategory.NARRATIVE_PACING,
                    severity="critical",
                    evidence_quote="q1",
                    evidence_location="loc1",
                    issue_description="pacing too slow",
                ),
                ReviewIssue(
                    issue_id="i2",
                    category=ReviewCategory.DESCRIPTION_SENSORY,
                    severity="major",
                    evidence_quote="q2",
                    evidence_location="loc2",
                    issue_description="lack of sensory detail",
                ),
            ]
        ),
        overall_score=7.5,
        ai_tell_count=1,
        fatigue_word_count=2,
    )

    with (
        patch(
            "songyan.workflows._run_logger.ChapterVersionRepository"
        ) as mock_ver_repo_cls,
        patch(
            "songyan.workflows._run_logger.ReviewReportRepository"
        ) as mock_report_repo_cls,
    ):
        mock_ver_repo_cls.return_value.get = AsyncMock(return_value=version)
        mock_ver_repo_cls.return_value.get_chain = AsyncMock(return_value=[])
        mock_report_repo_cls.return_value.get_by_version = AsyncMock(
            return_value=report
        )

        metrics = await collect_chapter_metrics(
            project_id="proj-1",
            chapter_number=1,
            final_version_id="v-1",
        )

    assert metrics["word_count"] == 3500
    assert metrics["rule_violations"] == 3  # 1 + 2
    assert metrics["rule_audit_score"] == pytest.approx(0.91, rel=1e-2)
    assert metrics["llm_audit_issues"] == 2
    assert metrics["llm_audit_critical"] == 1


@pytest.mark.asyncio
async def test_collect_metrics_no_version() -> None:
    """version_id 为 None 时返回空指标."""
    metrics = await collect_chapter_metrics(
        project_id="proj-1",
        chapter_number=1,
        final_version_id=None,
    )
    assert metrics == {}


@pytest.mark.asyncio
async def test_collect_metrics_missing_report() -> None:
    """report 不存在时返回零值."""
    version = AsyncMock()
    version.word_count = 2000

    with (
        patch(
            "songyan.workflows._run_logger.ChapterVersionRepository"
        ) as mock_ver_repo_cls,
        patch(
            "songyan.workflows._run_logger.ReviewReportRepository"
        ) as mock_report_repo_cls,
    ):
        mock_ver_repo_cls.return_value.get = AsyncMock(return_value=version)
        mock_ver_repo_cls.return_value.get_chain = AsyncMock(return_value=[])
        mock_report_repo_cls.return_value.get_by_version = AsyncMock(
            return_value=None
        )

        metrics = await collect_chapter_metrics(
            project_id="proj-1",
            chapter_number=1,
            final_version_id="v-1",
        )

    assert metrics["word_count"] == 2000
    assert metrics["rule_violations"] == 0
    assert metrics["rule_audit_score"] == 0.0
    assert metrics["llm_audit_issues"] == 0
    assert metrics["llm_audit_critical"] == 0


# ---------------------------------------------------------------------------
# build_chapter_run_log
# ---------------------------------------------------------------------------


def test_build_chapter_run_log_success() -> None:
    """成功场景构建日志."""
    started = datetime(2024, 1, 1, 12, 0, 0)
    finished = datetime(2024, 1, 1, 12, 1, 30)

    log = build_chapter_run_log(
        run_id="run-1",
        project_id="proj-1",
        chapter_number=3,
        started_at=started,
        finished_at=finished,
        success=True,
        final_state={
            "revision_round": 2,
            "_content_preservation_ratio": 0.92,
            "_settlement_needs_human_review": False,
        },
        metrics={
            "word_count": 3500,
            "rule_violations": 3,
            "rule_audit_score": 0.85,
            "llm_audit_issues": 2,
            "llm_audit_critical": 1,
        },
        continuity_health_score=8.5,
        duration_sec=90.0,
    )

    assert log.run_id == "run-1"
    assert log.project_id == "proj-1"
    assert log.chapter_number == 3
    assert log.success is True
    assert log.word_count == 3500
    assert log.revision_rounds == 2
    assert log.content_preservation_ratio == 0.92
    assert log.continuity_health_score == 8.5
    assert log.duration_sec == 90.0
    assert log.settlement_needs_human_review is False


def test_build_chapter_run_log_uses_metric_context_fallback() -> None:
    """final_state 缺少 context 时，从数据库指标兜底填充 V5 指标."""
    started = datetime(2024, 1, 1, 12, 0, 0)
    finished = datetime(2024, 1, 1, 12, 1, 0)

    log = build_chapter_run_log(
        run_id="run-1",
        project_id="proj-1",
        chapter_number=3,
        started_at=started,
        finished_at=finished,
        success=True,
        final_state={"revision_round": 1},
        metrics={
            "word_count": 3500,
            "_context_metrics": {
                "budget_used": 0.82,
                "character_states_loaded": 4,
                "soft_refs_loaded": 3,
                "context_emergency": False,
                "context_pressure": {"token_budget": 0.82},
            },
        },
        duration_sec=60.0,
    )

    assert log.budget_used == 0.82
    assert log.character_states_loaded == 4
    assert log.soft_refs_loaded == 3
    assert log.context_emergency is False
    assert log.context_pressure == {"token_budget": 0.82}


def test_build_chapter_run_log_failure() -> None:
    """失败场景构建日志."""
    started = datetime(2024, 1, 1, 12, 0, 0)
    finished = datetime(2024, 1, 1, 12, 0, 5)

    log = build_chapter_run_log(
        run_id="run-1",
        project_id="proj-1",
        chapter_number=2,
        started_at=started,
        finished_at=finished,
        success=False,
        error="writer_timeout",
        error_stage="writing",
        final_state={"revision_round": 0},
        duration_sec=5.0,
    )

    assert log.success is False
    assert log.error == "writer_timeout"
    assert log.error_stage == "writing"
    assert log.revision_rounds == 0
    assert log.content_preservation_ratio is None


def test_build_chapter_run_log_terminal_success_with_stale_error_ignored() -> None:
    """Task 121f: 终态成功路径写入时 settlement_success 以 success=True 为准."""
    started = datetime(2024, 1, 1, 12, 0, 0)
    finished = datetime(2024, 1, 1, 12, 3, 0)

    log = build_chapter_run_log(
        run_id="run-1",
        project_id="proj-1",
        chapter_number=18,
        started_at=started,
        finished_at=finished,
        success=True,
        final_state={
            "status": "done",
            "error": "CreativeDirector LLM call failed: parse error",
            "current_version_id": "v-18",
            "settlement_id": "st-18",
            "summary_id": "sum-18",
            "_settlement_needs_human_review": False,
            "_skip_settlement": False,
        },
        metrics={"word_count": 4058},
        duration_sec=180.0,
    )

    assert log.success is True
    assert log.error is None
    assert log.error_stage is None
    assert log.settlement_success is True
    assert log.summary_success is True


def test_build_chapter_run_log_degraded_accept() -> None:
    """Task 128a: degraded_accept 章节日志正确记录并跳过 settlement."""
    started = datetime(2024, 1, 1, 12, 0, 0)
    finished = datetime(2024, 1, 1, 12, 3, 0)

    log = build_chapter_run_log(
        run_id="run-1",
        project_id="proj-1",
        chapter_number=2,
        started_at=started,
        finished_at=finished,
        success=True,
        final_state={
            "status": "done",
            "current_version_id": "v-2",
            "_quality_gate_passed": False,
            "_degraded_accept": True,
            "_settlement_needs_human_review": False,
            "_skip_settlement": False,
        },
        metrics={"word_count": 2800},
        duration_sec=120.0,
    )

    assert log.success is True
    assert log.degraded_accept is True
    assert log.quality_gate_passed is False
    assert log.settlement_success is False
    assert log.summary_success is False
    assert log.skip_settlement is False


# ---------------------------------------------------------------------------
# write_run_log
# ---------------------------------------------------------------------------


def test_write_run_log_creates_jsonl() -> None:
    """写入 JSONL 并验证内容."""
    log = ChapterRunLog(
        log_id="log-1",
        run_id="run-1",
        project_id="proj-1",
        chapter_number=1,
        started_at=datetime(2024, 1, 1, 12, 0, 0),
        finished_at=datetime(2024, 1, 1, 12, 1, 0),
        success=True,
        word_count=3000,
        duration_sec=60.0,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("songyan.workflows._run_logger._LOGS_DIR", Path(tmpdir)):
            filepath = write_run_log(log, run_id="run-1")

        assert Path(filepath).exists()
        with open(filepath, encoding="utf-8") as f:
            line = f.readline().strip()
            data = json.loads(line)

        assert data["log_id"] == "log-1"
        assert data["project_id"] == "proj-1"
        assert data["chapter_number"] == 1
        assert data["success"] is True
        assert data["word_count"] == 3000


def test_write_run_log_appends() -> None:
    """同一 run_id 的日志追加到同一文件."""
    log1 = ChapterRunLog(
        log_id="log-1",
        run_id="run-1",
        project_id="proj-1",
        chapter_number=1,
        started_at=datetime(2024, 1, 1, 12, 0, 0),
        finished_at=datetime(2024, 1, 1, 12, 1, 0),
        success=True,
        duration_sec=60.0,
    )
    log2 = ChapterRunLog(
        log_id="log-2",
        run_id="run-1",
        project_id="proj-1",
        chapter_number=2,
        started_at=datetime(2024, 1, 1, 12, 2, 0),
        finished_at=datetime(2024, 1, 1, 12, 3, 0),
        success=True,
        duration_sec=60.0,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("songyan.workflows._run_logger._LOGS_DIR", Path(tmpdir)):
            write_run_log(log1, run_id="run-1")
            write_run_log(log2, run_id="run-1")

        filepath = Path(tmpdir) / "run-1.jsonl"
        with open(filepath, encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]

        assert len(lines) == 2
        data1 = json.loads(lines[0])
        data2 = json.loads(lines[1])
        assert data1["chapter_number"] == 1
        assert data2["chapter_number"] == 2


def test_write_run_log_os_error_graceful() -> None:
    """写入失败时不抛出异常，只记录警告."""
    log = ChapterRunLog(
        log_id="log-1",
        run_id="run-1",
        project_id="proj-1",
        chapter_number=1,
        started_at=datetime(2024, 1, 1, 12, 0, 0),
        finished_at=datetime(2024, 1, 1, 12, 1, 0),
        success=True,
        duration_sec=60.0,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        # 制造只读目录导致写入失败
        Path(tmpdir).chmod(0o555)
        with patch("songyan.workflows._run_logger._LOGS_DIR", Path(tmpdir) / "sub"):
            filepath = write_run_log(log, run_id="run-1")
            # 应返回路径但文件未实际写入，不抛异常
            assert "run-1.jsonl" in filepath


# ---------------------------------------------------------------------------
# ChapterRunLog serialization
# ---------------------------------------------------------------------------



def test_chapter_run_log_to_jsonl() -> None:
    """to_jsonl outputs valid JSON."""
    log = ChapterRunLog(
        log_id="log-1",
        run_id="run-1",
        project_id="proj-1",
        chapter_number=1,
        started_at=datetime(2024, 1, 1, 12, 0, 0),
        finished_at=datetime(2024, 1, 1, 12, 1, 0),
        success=True,
        word_count=3000,
        duration_sec=60.0,
    )
    raw = log.to_jsonl()
    data = json.loads(raw)
    assert data["log_id"] == "log-1"
    assert data["word_count"] == 3000


# ---------- _metrics_version -- Task 059 ----------


def test_metrics_version_default() -> None:
    """ChapterRunLog instantiation sets metrics_version to v5.0."""
    log = ChapterRunLog(
        log_id="l-1",
        project_id="p-1",
        chapter_number=1,
        started_at=datetime(2024, 1, 1, 12, 0, 0),
        finished_at=datetime(2024, 1, 1, 12, 1, 0),
        success=True,
        duration_sec=60.0,
    )
    assert log.metrics_version == "v5.0"


def test_to_jsonl_includes_metrics_version() -> None:
    """to_jsonl output includes _metrics_version field."""
    log = ChapterRunLog(
        log_id="l-1",
        project_id="p-1",
        chapter_number=1,
        started_at=datetime(2024, 1, 1, 12, 0, 0),
        finished_at=datetime(2024, 1, 1, 12, 1, 0),
        success=True,
        duration_sec=60.0,
    )
    raw = log.to_jsonl()
    data = json.loads(raw)
    assert data["_metrics_version"] == "v5.0"


def test_old_jsonl_without_metrics_version() -> None:
    """Old JSONL without _metrics_version deserializes without error (defaults to v5.0)."""
    old = (
        '{"log_id":"l-1","project_id":"p-1","chapter_number":1,'
        '"started_at":"2024-01-01T12:00:00",'
        '"finished_at":"2024-01-01T12:01:00","success":true,'
        '"word_count":3000,"duration_sec":60.0}'
    )
    log = ChapterRunLog.model_validate_json(old)
    assert log.log_id == "l-1"
    assert log.metrics_version == "v5.0"


def test_build_chapter_run_log_includes_metrics_version() -> None:
    """build_chapter_run_log includes default metrics_version."""
    started = datetime(2024, 1, 1, 12, 0, 0)
    finished = datetime(2024, 1, 1, 12, 1, 0)
    log = build_chapter_run_log(
        run_id="r-1",
        project_id="p-1",
        chapter_number=3,
        started_at=started,
        finished_at=finished,
        success=True,
    )
    assert log.metrics_version == "v5.0"
