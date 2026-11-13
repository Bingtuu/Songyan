"""task 252：variant list / pick 对 stale_vs_storyline 的 CLI 露出（B5/B7）。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from songyan.cli.main import cli
from songyan.config import settings
from songyan.db.chapter_variant_repo import ChapterVariantRepository
from songyan.db.migrations import init_schema
from songyan.db.narrative_repo import NarrativeRepository
from songyan.db.repository import ChapterVersionRepository, ProjectRepository
from songyan.models.chapter import ChapterVersion
from songyan.models.narrative import ArcPlan
from songyan.models.project import ProjectSetting
from songyan.models.variant import ChapterVariant

_PROJECT = "p-slstale"
_CHAPTER = 4


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
async def sl_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "variant-storyline.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="mystery",
            mode_id="webnovel",
            protagonist_name="陈照",
            title="storyline stale",
        ),
        _PROJECT,
    )
    await ChapterVersionRepository().create(
        ChapterVersion(
            version_id="ver-sl",
            project_id=_PROJECT,
            chapter_number=_CHAPTER,
            version_number=1,
            version_type="draft",
            content="正文" * 80,
            word_count=160,
        )
    )
    row = ChapterVariant(
        variant_id="var-sl",
        project_id=_PROJECT,
        chapter_number=_CHAPTER,
        slot_index=1,
        status="generated",
        parent_canon_fingerprint="fp",
        content_ref="ver-sl",
        stale_vs_storyline=1,
        storyline_fingerprint="fp-old",
        created_at="2026-11-13T00:00:00Z",
        updated_at="2026-11-13T00:00:00Z",
    )
    await ChapterVariantRepository().insert(row)
    return db_path


def test_list_json_exposes_stale_vs_storyline(
    runner: CliRunner, sl_db: Path
) -> None:
    result = runner.invoke(
        cli,
        [
            "variant",
            "list",
            "--project-id",
            _PROJECT,
            "--chapter",
            str(_CHAPTER),
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["variants"][0]["stale_vs_storyline"] == 1


def test_list_text_shows_storyline_stale(
    runner: CliRunner, sl_db: Path
) -> None:
    result = runner.invoke(
        cli,
        [
            "variant",
            "list",
            "--project-id",
            _PROJECT,
            "--chapter",
            str(_CHAPTER),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "slStale=1" in result.output


def test_pick_warns_but_exit_0(runner: CliRunner, sl_db: Path) -> None:
    result = runner.invoke(
        cli,
        [
            "variant",
            "pick",
            "--project-id",
            _PROJECT,
            "--chapter",
            str(_CHAPTER),
            "--slot",
            "1",
            "--allow-stale",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "故事线" in result.stderr
    assert "stale_vs_storyline=1" in result.stderr


def test_list_lazy_refresh_marks_after_storyline_change(
    runner: CliRunner, sl_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """故事线演进后 list 懒标脏：baseline 槽（fp 为当前值）被标 1。"""
    import asyncio

    from songyan.services.storyline_fingerprint import storyline_fingerprint

    # 先把行指纹刷成当前值（模拟 generate 落库后的状态）
    current = asyncio.run(storyline_fingerprint(_PROJECT, _CHAPTER))

    async def _sync() -> None:
        await ChapterVariantRepository().sync_storyline_state(
            [("var-sl", 0, current)]
        )

    asyncio.run(_sync())

    # 故事线演进：加一条覆盖本章的弧
    async def _add_arc() -> None:
        await NarrativeRepository().add_arc_plan(
            ArcPlan(
                arc_id="arc-new",
                project_id=_PROJECT,
                arc_index=0,
                start_chapter=1,
                end_chapter=10,
                arc_goal="新弧",
            )
        )

    asyncio.run(_add_arc())

    result = runner.invoke(
        cli,
        [
            "variant",
            "list",
            "--project-id",
            _PROJECT,
            "--chapter",
            str(_CHAPTER),
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["variants"][0]["stale_vs_storyline"] == 1
