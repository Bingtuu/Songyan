"""M4 步 3 切片 5: chapter continue run 壳（tech-m4 §5 步 3 / B9 / 评审 M4）。

LLM 失败 → status=paused + pause_reason + exit 1；再次 continue 续跑只追加新版本；
预算熔断 → 已写保留 + exit 3；engine run 壳（多章范围）不收养，新建单章壳。
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from click.testing import CliRunner, Result

from songyan.cli.main import cli
from songyan.config import settings
from songyan.db.migrations import init_schema
from songyan.db.project_run_repo import ProjectRunRepository
from songyan.db.repository import ChapterVersionRepository, ProjectRepository
from songyan.exceptions import LLMBudgetExceededError, LLMError
from songyan.models.project import ProjectSetting
from songyan.models.project_run import ProjectRunState

_PROJECT = "p-m4-cont-runshell"
_BODY = "夜雨落在南站站台。\n\n陈照收起铜镜，转身走进雨里。\n\n末班车进站了。"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
async def runshell_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "m4-cont-runshell.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="mystery_noir",
            mode_id="webnovel",
            protagonist_name="陈照",
            title="m4 continue runshell",
        ),
        _PROJECT,
    )
    return db_path


def _invoke_continue(runner: CliRunner, *extra: str) -> Result:
    return runner.invoke(cli, ["chapter", "continue", "--project-id", _PROJECT, *extra])


async def _seed_empty_head(chapter: int) -> None:
    from songyan.db.repository import ChapterHeadRepository
    from songyan.models.chapter import ChapterHead

    await ChapterHeadRepository().update(
        ChapterHead(
            project_id=_PROJECT,
            chapter_number=chapter,
            current_version_id=None,
            accepted_version_id=None,
            status="draft",
        )
    )


async def _single_chapter_shells() -> list[ProjectRunState]:
    runs = await ProjectRunRepository().list_by_project(_PROJECT)
    return [
        r
        for r in runs
        if r.chapter_range_start == r.chapter_range_end and r.status in ("running", "paused")
    ]


def test_llm_failure_pauses_run_exit_1(
    runner: CliRunner, runshell_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    asyncio.run(_seed_empty_head(1))
    monkeypatch.setattr(
        "songyan.agents.writer.call_llm", AsyncMock(side_effect=LLMError("boom"))
    )
    result = _invoke_continue(runner)
    assert result.exit_code == 1, result.output

    shells = asyncio.run(_single_chapter_shells())
    assert len(shells) == 1
    assert shells[0].chapter_range_start == 1
    assert shells[0].status == "paused"
    assert shells[0].pause_reason is not None
    assert "llm_error" in shells[0].pause_reason


def test_variants_llm_failure_pauses_run_exit_1(
    runner: CliRunner, runshell_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--variants 路径 LLM 失败同享暂停语义（review major M1 回归锁）。

    generate_chapter_variants 抛 VariantGenerateLLMError（非 LLMError 子类）；
    未被捕获会让 run 壳滞留 running + CLI 裸 traceback。
    """
    asyncio.run(_seed_empty_head(1))
    monkeypatch.setattr(
        "songyan.services.variant_generate.default_slot_draft",
        AsyncMock(side_effect=LLMError("variants boom")),
    )
    result = _invoke_continue(runner, "--variants", "2")
    assert result.exit_code == 1, result.output

    shells = asyncio.run(_single_chapter_shells())
    assert len(shells) == 1
    assert shells[0].status == "paused"
    assert shells[0].pause_reason is not None
    assert "llm_error" in shells[0].pause_reason


def test_resume_after_failure_appends_only_new_version(
    runner: CliRunner, runshell_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    asyncio.run(_seed_empty_head(1))
    monkeypatch.setattr(
        "songyan.agents.writer.call_llm", AsyncMock(side_effect=LLMError("boom"))
    )
    first = _invoke_continue(runner)
    assert first.exit_code == 1, first.output

    monkeypatch.setattr("songyan.agents.writer.call_llm", AsyncMock(return_value=_BODY))
    second = _invoke_continue(runner)
    assert second.exit_code == 0, second.output

    versions = asyncio.run(ChapterVersionRepository().list_by_chapter(_PROJECT, 1))
    assert len(versions) == 1
    assert "末班车进站" in versions[0].content

    runs = asyncio.run(ProjectRunRepository().list_by_project(_PROJECT))
    assert len(runs) == 1
    assert runs[0].status == "completed"
    assert runs[0].pause_reason is None


def test_budget_exceeded_exit_3_keeps_written(
    runner: CliRunner, runshell_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    budget_error = LLMBudgetExceededError(
        message="单 run 成本预算耗尽", used_calls=5, budget=5, last_chapter=1
    )
    asyncio.run(_seed_empty_head(1))
    monkeypatch.setattr(
        "songyan.agents.writer.call_llm", AsyncMock(side_effect=budget_error)
    )
    result = _invoke_continue(runner)
    assert result.exit_code == 3, result.output

    shells = asyncio.run(_single_chapter_shells())
    assert len(shells) == 1
    assert shells[0].status == "paused"
    assert shells[0].pause_reason is not None
    assert "cost_budget" in shells[0].pause_reason
    # 已写保留：预算熔断前无版本落库（mock 在 LLM 入口抛出）。
    assert asyncio.run(ChapterVersionRepository().list_by_chapter(_PROJECT, 1)) == []


def test_engine_multi_chapter_shell_not_adopted(
    runner: CliRunner, runshell_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    asyncio.run(_seed_empty_head(1))
    asyncio.run(_create_engine_shell())
    monkeypatch.setattr("songyan.agents.writer.call_llm", AsyncMock(return_value=_BODY))

    result = _invoke_continue(runner)
    assert result.exit_code == 0, result.output

    runs = asyncio.run(ProjectRunRepository().list_by_project(_PROJECT))
    assert len(runs) == 2
    engine = next(r for r in runs if r.run_id == "run-engine")
    assert engine.status == "running"
    assert engine.chapter_range_end == 5
    # 新壳：单章壳，完成态。
    new_shells = [r for r in runs if r.run_id != "run-engine"]
    assert len(new_shells) == 1
    assert new_shells[0].chapter_range_start == new_shells[0].chapter_range_end == 1
    assert new_shells[0].status == "completed"


async def _create_engine_shell() -> None:
    await ProjectRunRepository().create(
        ProjectRunState(
            run_id="run-engine",
            project_id=_PROJECT,
            chapter_range_start=1,
            chapter_range_end=5,
            current_chapter=1,
            status="running",
        )
    )
