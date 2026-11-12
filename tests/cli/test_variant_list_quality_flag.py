"""task 245 P3: variant list 露出 quality_flag；variant pick 拒绝打标槽。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from songyan.cli.main import cli
from songyan.config import settings
from songyan.db.chapter_variant_repo import ChapterVariantRepository
from songyan.db.migrations import init_schema
from songyan.db.repository import ProjectRepository
from songyan.models.project import ProjectSetting
from songyan.models.variant import ChapterVariant

_PROJECT = "p-qflag"
_CHAPTER = 4


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
async def flag_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "variant-quality-flag.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="mystery",
            mode_id="webnovel",
            protagonist_name="陈照",
            title="quality flag",
        ),
        _PROJECT,
    )
    from songyan.db.repository import ChapterVersionRepository
    from songyan.models.chapter import ChapterVersion

    version_repo = ChapterVersionRepository()
    for i, (vid, content) in enumerate(
        [("ver-flagged", "占位"), ("ver-clean", "正文" * 80)], start=1
    ):
        await version_repo.create(
            ChapterVersion(
                version_id=vid,
                project_id=_PROJECT,
                chapter_number=_CHAPTER,
                version_number=i,
                version_type="draft",
                content=content,
                word_count=len(content),
            )
        )
    repo = ChapterVariantRepository()
    flagged = ChapterVariant(
        variant_id="var-flagged",
        project_id=_PROJECT,
        chapter_number=_CHAPTER,
        slot_index=1,
        status="generated",
        parent_canon_fingerprint="fp-flag",
        content_ref="ver-flagged",
        quality_flag="too_short",
        created_at="2026-11-11T00:00:00Z",
        updated_at="2026-11-11T00:00:00Z",
    )
    await repo.insert(flagged)
    clean = flagged.model_copy(
        update={
            "variant_id": "var-clean",
            "slot_index": 2,
            "content_ref": "ver-clean",
            "quality_flag": None,
        }
    )
    await repo.insert(clean)
    return db_path


def test_list_json_exposes_quality_flag(
    runner: CliRunner, flag_db: Path
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
    by_slot = {v["slot_index"]: v for v in payload["variants"]}
    assert by_slot[1]["quality_flag"] == "too_short"
    assert by_slot[2]["quality_flag"] is None


def test_list_text_shows_flag(runner: CliRunner, flag_db: Path) -> None:
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
    assert "slot=1" in result.output
    assert "flag=too_short" in result.output
    assert "flag=too_short" not in result.output.split("slot=2")[1]


def test_pick_rejects_flagged_slot_exit_2(
    runner: CliRunner, flag_db: Path
) -> None:
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
    assert result.exit_code == 2
    assert "quality_flag" in result.stderr


def test_pick_clean_slot_still_works(
    runner: CliRunner, flag_db: Path
) -> None:
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
            "2",
            "--allow-stale",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "picked slot=2" in result.output
