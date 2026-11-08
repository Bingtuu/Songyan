"""M4 步 2: chapter accept CLI（tech-m4 §5 步 2 / B2/B11，task 239）.

exit 码表（B11）：0 = 已确认；1 = 缺库 / 缺项目 / 参数非法（含文件错误）；
2 = 无可确认稿 / 重复 accept（幂等提示）。
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
from songyan.utils.word_count import count_chinese_words

_PROJECT = "p-m4-accept-cli"
_DRAFT_CONTENT = "原始草稿：陈照走进南站。"
_EDITED_CONTENT = "编辑后的正文：陈照走出南站，雨停了。"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
async def accept_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "m4-accept-cli.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="mystery",
            mode_id="webnovel",
            protagonist_name="陈照",
            title="m4 accept cli",
        ),
        _PROJECT,
    )
    return db_path


async def _seed_draft_with_head() -> str:
    version = ChapterVersion(
        version_id="v-draft-1",
        project_id=_PROJECT,
        chapter_number=1,
        version_number=1,
        version_type="draft",
        content=_DRAFT_CONTENT,
        word_count=count_chinese_words(_DRAFT_CONTENT),
    )
    await ChapterVersionRepository().create(version)
    await ChapterHeadRepository().update(
        ChapterHead(
            project_id=_PROJECT,
            chapter_number=1,
            current_version_id=version.version_id,
            accepted_version_id=None,
            status="draft",
        )
    )
    return version.version_id


def _invoke_accept(runner: CliRunner, *extra: str) -> Result:
    return runner.invoke(
        cli,
        ["chapter", "accept", "--project-id", _PROJECT, "--chapter", "1", *extra],
    )


# --- 成功路径 -------------------------------------------------------------


def test_accept_text_output(
    runner: CliRunner, accept_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    asyncio.run(_seed_draft_with_head())
    result = _invoke_accept(runner)
    assert result.exit_code == 0, result.output
    assert "accepted_version_id" in result.output
    assert "chapter=1" in result.output


def test_accept_json_output(
    runner: CliRunner, accept_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    draft_id = asyncio.run(_seed_draft_with_head())
    result = _invoke_accept(runner, "--json")
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["chapter"] == 1
    assert payload["accepted_version_id"] != draft_id
    assert payload["source_version_id"] == draft_id
    assert payload["edited_version_id"] is None
    assert payload["word_count"] == count_chinese_words(_DRAFT_CONTENT)


def test_accept_from_file_json_output(
    runner: CliRunner, accept_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    asyncio.run(_seed_draft_with_head())
    edit_file = accept_db.parent / "edit.txt"
    edit_file.write_text(_EDITED_CONTENT, encoding="utf-8")
    result = _invoke_accept(runner, "--from-file", str(edit_file), "--json")
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["edited_version_id"] is not None
    assert payload["source_version_id"] == payload["edited_version_id"]
    assert payload["word_count"] == count_chinese_words(_EDITED_CONTENT)
    assert payload["accepted_version_id"] != payload["edited_version_id"]


# --- exit 1：缺库 / 缺项目 / 参数非法 ------------------------------------


def test_missing_database_exit_1(
    runner: CliRunner, accept_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        settings,
        "database_url",
        f"sqlite:///{accept_db.parent / 'no-such.db'}",
    )
    result = _invoke_accept(runner)
    assert result.exit_code == 1


def test_missing_project_exit_1(runner: CliRunner, accept_db: Path) -> None:
    result = runner.invoke(
        cli,
        ["chapter", "accept", "--project-id", "p-nope", "--chapter", "1"],
    )
    assert result.exit_code == 1


def test_invalid_chapter_exit_1(runner: CliRunner, accept_db: Path) -> None:
    result = runner.invoke(
        cli,
        ["chapter", "accept", "--project-id", _PROJECT, "--chapter", "0"],
    )
    assert result.exit_code == 1


def test_from_file_missing_exit_1(
    runner: CliRunner, accept_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    asyncio.run(_seed_draft_with_head())
    result = _invoke_accept(runner, "--from-file", str(accept_db.parent / "nope.txt"))
    assert result.exit_code == 1


def test_from_file_empty_exit_1(
    runner: CliRunner, accept_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    asyncio.run(_seed_draft_with_head())
    edit_file = accept_db.parent / "edit.txt"
    edit_file.write_text("\n  \n", encoding="utf-8")
    result = _invoke_accept(runner, "--from-file", str(edit_file))
    assert result.exit_code == 1


# --- exit 2：无可确认稿 / 重复 accept ------------------------------------


def test_no_head_exit_2(runner: CliRunner, accept_db: Path) -> None:
    result = _invoke_accept(runner)
    assert result.exit_code == 2


def test_head_without_current_version_exit_2(
    runner: CliRunner, accept_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def _seed_empty_head() -> None:
        await ChapterHeadRepository().update(
            ChapterHead(
                project_id=_PROJECT,
                chapter_number=1,
                current_version_id=None,
                accepted_version_id=None,
                status="draft",
            )
        )

    asyncio.run(_seed_empty_head())
    result = _invoke_accept(runner)
    assert result.exit_code == 2


def test_repeat_accept_exit_2(
    runner: CliRunner, accept_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    asyncio.run(_seed_draft_with_head())
    first = _invoke_accept(runner, "--json")
    assert first.exit_code == 0, first.output
    accepted_id = json.loads(first.stdout)["accepted_version_id"]

    again = _invoke_accept(runner)
    assert again.exit_code == 2

    versions = asyncio.run(ChapterVersionRepository().list_by_chapter(_PROJECT, 1))
    assert [v.version_id for v in versions] == ["v-draft-1", accepted_id]
