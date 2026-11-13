"""tech-m4-followup 步 3：``review --deep`` 显式 LLM 深审（B4 成本门 / B5 零写库 / B6 口径）。"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from click.testing import CliRunner

from songyan.cli.main import cli
from songyan.config import settings
from songyan.db.migrations import init_schema
from songyan.db.repository import (
    ChapterHeadRepository,
    ChapterVersionRepository,
    ProjectRepository,
)
from songyan.models.chapter import ChapterHead, ChapterVersion
from songyan.models.project import ProjectSetting

_PROJECT = "p-deep"
_CHAPTER = 1

_CONTENT = "夜色压低站台，陈屿攥着末班铜牌等车。" * 30  # ≥100 字工作稿

_DEEP_JSON = """
[
  {"severity": "hard", "check": "fact",
   "message": "与圣经矛盾：铜牌应为古铜色",
   "evidence": "原文：铜牌泛着冷冽的青光",
   "location": "第2段"},
  {"severity": "info", "check": "voice",
   "message": "视角短暂漂移，建议人复核",
   "evidence": "", "location": ""}
]
"""


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
async def deep_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "review-deep.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="mystery",
            mode_id="webnovel",
            protagonist_name="陈照",
            title="deep review",
        ),
        _PROJECT,
    )
    await ChapterVersionRepository().create(
        ChapterVersion(
            version_id="ver-deep-1",
            project_id=_PROJECT,
            chapter_number=_CHAPTER,
            version_number=1,
            version_type="draft",
            content=_CONTENT,
            word_count=len(_CONTENT),
        )
    )
    await ChapterHeadRepository().update(
        ChapterHead(
            project_id=_PROJECT,
            chapter_number=_CHAPTER,
            current_version_id="ver-deep-1",
            accepted_version_id=None,
            status="draft",
        )
    )
    return db_path


def _install_llm_mock(
    monkeypatch: pytest.MonkeyPatch, response: str
) -> AsyncMock:
    mock = AsyncMock(return_value=response)
    monkeypatch.setattr("songyan.llm.call_llm", mock)
    return mock


def _invoke(runner: CliRunner, *extra: str, input: str | None = None):
    return runner.invoke(
        cli,
        ["review", "--project-id", _PROJECT, "--chapter", str(_CHAPTER), *extra],
        input=input,
    )


def test_non_tty_without_yes_exit_2(
    runner: CliRunner, deep_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_llm_mock(monkeypatch, "[]")
    result = _invoke(runner, "--deep")
    assert result.exit_code == 2
    assert "非交互" in result.stderr
    assert "--yes" in result.stderr


def test_budget_reject_exit_2(
    runner: CliRunner, deep_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_llm_mock(monkeypatch, "[]")
    result = _invoke(runner, "--deep", "--yes", "--budget-cny", "0.0000001")
    assert result.exit_code == 2
    assert "budget" in result.stderr or "超过" in result.stderr


def test_yes_proceeds_findings_merged(
    runner: CliRunner, deep_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock = _install_llm_mock(monkeypatch, _DEEP_JSON)

    result = _invoke(runner, "--deep", "--yes", "--json")

    assert result.exit_code == 0, result.output
    assert mock.await_count == 1
    payload = json.loads(result.stdout)
    deep_findings = [f for f in payload["findings"] if f["source"] == "deep"]
    assert len(deep_findings) == 2
    assert any(f["severity"] == "hard" for f in deep_findings)
    assert payload["deep_count"] == 2


def test_interactive_decline_exit_2(
    runner: CliRunner, deep_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import songyan.cli.commands.review as review_mod

    _install_llm_mock(monkeypatch, "[]")
    monkeypatch.setattr(review_mod, "_stdin_isatty", lambda: True)
    result = _invoke(runner, "--deep", input="n\n")
    assert result.exit_code == 2
    assert mock_not_called(monkeypatch)


def mock_not_called(monkeypatch: pytest.MonkeyPatch) -> bool:
    from songyan.llm import call_llm

    return isinstance(call_llm, AsyncMock) and call_llm.await_count == 0


def test_interactive_accept_proceeds(
    runner: CliRunner, deep_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import songyan.cli.commands.review as review_mod

    mock = _install_llm_mock(monkeypatch, _DEEP_JSON)
    monkeypatch.setattr(review_mod, "_stdin_isatty", lambda: True)
    result = _invoke(runner, "--deep", input="y\n")
    assert result.exit_code == 0, result.output
    assert mock.await_count == 1
    assert "铜牌应为古铜色" in result.output


def test_garbage_response_exit_1_base_report_kept(
    runner: CliRunner, deep_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_llm_mock(monkeypatch, "我什么也不是，更不是 JSON")

    result = _invoke(runner, "--deep", "--yes")

    assert result.exit_code == 1
    assert "# 共审报告" in result.output  # 基础报告照出
    assert "deep" in result.stderr


def test_invalid_severity_defaults_info(
    runner: CliRunner, deep_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = '[{"severity": "fatal", "check": "fact", "message": "级联失败"}]'
    _install_llm_mock(monkeypatch, raw)
    result = _invoke(runner, "--deep", "--yes", "--json")
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    deep_findings = [f for f in payload["findings"] if f["source"] == "deep"]
    assert deep_findings[0]["severity"] == "info"


def test_zero_writes(
    runner: CliRunner, deep_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_llm_mock(monkeypatch, _DEEP_JSON)

    async def _snapshot() -> dict[str, int]:
        from songyan.db.connection import get_db

        out: dict[str, int] = {}
        async with get_db() as conn:
            for table in ("chapter_heads", "chapter_versions", "review_reports"):
                cur = await conn.execute(f"SELECT COUNT(*) FROM {table}")
                out[table] = (await cur.fetchone())[0]
        return out

    import asyncio

    before = asyncio.run(_snapshot())
    result = _invoke(runner, "--deep", "--yes")
    assert result.exit_code == 0, result.output
    after = asyncio.run(_snapshot())
    assert after == before, f"--deep 必须零写库：{before} -> {after}"
