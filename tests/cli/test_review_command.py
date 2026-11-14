"""M4 步 4 切片 1/5: ``songyan review`` CLI（tech-m4 §4.4 / B8 / B11）。

exit 码三态：0 = 报告输出（含发现问题）/ 1 = 缺库、缺项目、参数非法 /
2 = 指定章不存在（不在章宇宙）。默认章 = 章宇宙最大章号。
markdown 按严重度分组 + 证据引用；--json 七源分区全字段锁死。
夹具模式参照 tests/cli/test_chapter_continue_gates.py。
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from click.testing import CliRunner, Result

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

_PROJECT = "p-m4-review-cli"
_JSON_KEYS = {
    "project_id",
    "chapter",
    "workdraft_version_id",
    "deep_count",  # task 250：--deep 深审条数（默认 0，不带 --deep 也在）
    "gate",
    "gate_note",
    "audits",
    "literary",
    "repetition_hits",
    "repetition_note",
    "proper_noun_hits",
    "variant_notes",
    "human_marks",
    "findings",
}

_CH1 = "第一章正文：陈照到了南站。末班车在午夜十二点准时进站了。"
_CH2 = (
    "末班车在午夜十二点准时进站了。\n末班车在午夜十二点准时进站了。\n"
    "末班车在午夜十二点准时进站了。\n陈照握紧了手里的铜牌。"
)


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
async def review_cli_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "m4-review-cli.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="mystery_noir",
            mode_id="webnovel",
            protagonist_name="陈照",
            title="m4 review cli",
        ),
        _PROJECT,
    )
    return db_path


async def _seed_chapter(chapter: int, version_id: str, content: str) -> None:
    version = ChapterVersion(
        version_id=version_id,
        project_id=_PROJECT,
        chapter_number=chapter,
        version_number=1,
        version_type="draft",
        content=content,
        word_count=len(content),
    )
    await ChapterVersionRepository().create(version)
    await ChapterHeadRepository().update(
        ChapterHead(
            project_id=_PROJECT,
            chapter_number=chapter,
            current_version_id=version_id,
            accepted_version_id=None,
            status="draft",
        )
    )


async def _mark_accepted(chapter: int, version_id: str) -> None:
    await ChapterHeadRepository().update(
        ChapterHead(
            project_id=_PROJECT,
            chapter_number=chapter,
            current_version_id=version_id,
            accepted_version_id=version_id,
            status="accepted",
        )
    )


def _invoke(runner: CliRunner, *extra: str) -> Result:
    return runner.invoke(cli, ["review", "--project-id", _PROJECT, *extra])


# --- exit 码三态 ---------------------------------------------------------------


def test_findings_exit_0(review_cli_db: Path, runner: CliRunner) -> None:
    """发现问题（复读命中）仍 exit 0（B11：报告即产出）。"""
    asyncio.run(_seed_chapter(1, "v-cli-1", _CH1))
    asyncio.run(_seed_chapter(2, "v-cli-2", _CH2))
    result = _invoke(runner, "--chapter", "2")
    assert result.exit_code == 0, result.output
    assert "第 2 章" in result.output


def test_missing_db_exit_1(
    tmp_path: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """缺库 → exit 1。"""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path}/nope.db")
    result = _invoke(runner)
    assert result.exit_code == 1


def test_missing_project_exit_1(
    review_cli_db: Path, runner: CliRunner
) -> None:
    """缺项目 → exit 1。"""
    result = runner.invoke(cli, ["review", "--project-id", "p-not-exist"])
    assert result.exit_code == 1


def test_chapter_not_in_universe_exit_2(
    review_cli_db: Path, runner: CliRunner
) -> None:
    """指定章不在章宇宙 → exit 2。"""
    asyncio.run(_seed_chapter(1, "v-cli-1", _CH1))
    result = _invoke(runner, "--chapter", "9")
    assert result.exit_code == 2


def test_invalid_chapter_arg_exit_1(
    review_cli_db: Path, runner: CliRunner
) -> None:
    """参数非法（chapter < 1）→ exit 1。"""
    result = _invoke(runner, "--chapter", "0")
    assert result.exit_code == 1


# --- 默认章 = 章宇宙最大章号 ----------------------------------------------------


def test_default_chapter_is_max(review_cli_db: Path, runner: CliRunner) -> None:
    asyncio.run(_seed_chapter(1, "v-cli-1", _CH1))
    asyncio.run(_seed_chapter(3, "v-cli-3", "第三章草稿。夜雨还下着。"))
    result = _invoke(runner)
    assert result.exit_code == 0, result.output
    assert "第 3 章" in result.output


def test_empty_universe_reports_empty(
    review_cli_db: Path, runner: CliRunner
) -> None:
    """章宇宙为空 → 空报告 exit 0，不炸。"""
    result = _invoke(runner)
    assert result.exit_code == 0, result.output
    assert "还没有任何章节工作记录" in result.output


# --- 呈现切片 -------------------------------------------------------------------


def test_markdown_groups_by_severity_with_evidence(
    review_cli_db: Path, runner: CliRunner
) -> None:
    """markdown：严重度分组标题 + 复读证据引用。"""
    asyncio.run(_seed_chapter(1, "v-cli-1", _CH1))
    asyncio.run(_seed_chapter(2, "v-cli-2", _CH2))
    result = _invoke(runner, "--chapter", "2")
    assert result.exit_code == 0, result.output
    assert "硬伤" in result.output  # gate 通过无硬伤 → 组存在但可空
    assert "提示" in result.output
    assert "末班车在午夜十二点准时进站了。" in result.output  # 证据引用
    assert "复读" in result.output


def test_json_full_keys_locked(
    review_cli_db: Path, runner: CliRunner
) -> None:
    """--json：七源分区全字段锁死。"""
    asyncio.run(_seed_chapter(1, "v-cli-1", _CH1))
    asyncio.run(_mark_accepted(1, "v-cli-1"))
    asyncio.run(_seed_chapter(2, "v-cli-2", _CH2))
    result = _invoke(runner, "--chapter", "2", "--json")
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert set(payload.keys()) == _JSON_KEYS
    assert payload["project_id"] == _PROJECT
    assert payload["chapter"] == 2
    assert payload["workdraft_version_id"] == "v-cli-2"
    assert payload["gate"]["passed"] is True
    assert payload["repetition_note"] == ""
    assert len(payload["repetition_hits"]) >= 1
    kinds = {h["kind"] for h in payload["repetition_hits"]}
    assert "sentence" in kinds
    assert "cross_chapter" in kinds  # ch1 accepted 含同款句


def test_json_no_workdraft_notes(
    review_cli_db: Path, runner: CliRunner
) -> None:
    """无工作稿章：依赖正文的分区注明，exit 0。"""
    asyncio.run(_seed_chapter(1, "v-cli-1", _CH1))
    head = ChapterHead(
        project_id=_PROJECT,
        chapter_number=2,
        current_version_id=None,
        accepted_version_id=None,
        status="draft",
    )
    asyncio.run(ChapterHeadRepository().update(head))
    result = _invoke(runner, "--chapter", "2", "--json")
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["workdraft_version_id"] is None
    assert "无工作稿" in payload["gate_note"]
    assert payload["repetition_hits"] == []
    assert "无工作稿" in payload["repetition_note"]
