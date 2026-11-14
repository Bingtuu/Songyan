"""tech-m4-followup 步 1：``songyan chapter status`` 只读章进度面（B1/B2）。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from songyan.cli.main import cli
from songyan.config import settings
from songyan.db.chapter_variant_repo import ChapterVariantRepository
from songyan.db.llm_call_usage_repo import LlmCallUsageRepository
from songyan.db.migrations import init_schema
from songyan.db.repository import (
    ChapterHeadRepository,
    ChapterVersionRepository,
    ProjectRepository,
)
from songyan.models.chapter import ChapterHead, ChapterVersion
from songyan.models.project import ProjectSetting
from songyan.models.variant import ChapterVariant

_PROJECT = "p-cstat"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
async def status_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "chapter-status.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="mystery",
            mode_id="webnovel",
            protagonist_name="陈照",
            title="chapter status",
        ),
        _PROJECT,
    )

    heads = ChapterHeadRepository()
    versions = ChapterVersionRepository()
    variants = ChapterVariantRepository()

    async def _version(ch: int, vid: str) -> None:
        await versions.create(
            ChapterVersion(
                version_id=vid,
                project_id=_PROJECT,
                chapter_number=ch,
                version_number=1,
                version_type="draft",
                content="正文" * 80,
                word_count=160,
            )
        )

    async def _head(ch: int, current: str | None, accepted: str | None) -> None:
        await heads.update(
            ChapterHead(
                project_id=_PROJECT,
                chapter_number=ch,
                current_version_id=current,
                accepted_version_id=accepted,
                status="draft",
            )
        )

    # ch1 empty：空 head，无版本无槽
    await _head(1, None, None)
    # ch2 drafting：有 current 工作稿
    await _version(2, "ver-ch2")
    await _head(2, "ver-ch2", None)
    # ch3 picked：槽被 pick
    await _version(3, "ver-ch3")
    await _head(3, "ver-ch3", None)
    picked = ChapterVariant(
        variant_id="var-ch3",
        project_id=_PROJECT,
        chapter_number=3,
        slot_index=1,
        status="picked",
        parent_canon_fingerprint="fp",
        content_ref="ver-ch3",
        cost_cny_estimate=0.01,
        created_at="2026-11-12T00:00:00Z",
        updated_at="2026-11-12T00:00:00Z",
    )
    await variants.insert(picked)
    # ch4 settled：accepted 且未 stale
    await _version(4, "ver-ch4")
    await _head(4, "ver-ch4", "ver-ch4")
    # ch5 stale：accepted + content_stale
    await _version(5, "ver-ch5")
    await _head(5, "ver-ch5", "ver-ch5")
    await heads.mark_content_stale(_PROJECT, [5])
    # ch6 variants_ready：有 generated 槽未 pick
    await _version(6, "ver-ch6")
    await _head(6, None, None)
    ready = picked.model_copy(
        update={
            "variant_id": "var-ch6",
            "chapter_number": 6,
            "slot_index": 1,
            "status": "generated",
            "content_ref": "ver-ch6",
            "quality_flag": "too_short",
        }
    )
    await variants.insert(ready)

    # ch2 两条费用遥测
    usage = LlmCallUsageRepository()
    for i, cost in enumerate((0.01, 0.02), start=1):
        await usage.record(
            model="mock-model",
            token_source="estimate",
            cost_source="pricing_estimate",
            project_id=_PROJECT,
            chapter_number=2,
            agent="writer",
            cost_cny=cost,
        )
    return db_path


def _invoke(runner: CliRunner, chapter: int, *extra: str):
    return runner.invoke(
        cli,
        [
            "chapter",
            "status",
            "--project-id",
            _PROJECT,
            "--chapter",
            str(chapter),
            *extra,
        ],
    )


def test_empty_state(runner: CliRunner, status_db: Path) -> None:
    result = _invoke(runner, 1, "--json")
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["state"] == "empty"
    assert payload["current_version_id"] is None
    assert payload["accepted_version_id"] is None
    assert payload["variants"] == []


def test_drafting_state_and_cost_sums(
    runner: CliRunner, status_db: Path
) -> None:
    result = _invoke(runner, 2, "--json")
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["state"] == "drafting"
    assert payload["current_version_id"] == "ver-ch2"
    assert payload["accepted_version_id"] is None
    assert payload["llm_cost_sum"] == pytest.approx(0.03)
    assert payload["slot_cost_sum"] == 0.0


def test_picked_state(runner: CliRunner, status_db: Path) -> None:
    result = _invoke(runner, 3, "--json")
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["state"] == "picked"
    assert len(payload["variants"]) == 1
    assert payload["variants"][0]["status"] == "picked"
    assert payload["slot_cost_sum"] == pytest.approx(0.01)


def test_settled_state(runner: CliRunner, status_db: Path) -> None:
    result = _invoke(runner, 4, "--json")
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["state"] == "settled"
    assert payload["accepted_version_id"] == "ver-ch4"
    assert payload["content_stale"] == 0


def test_stale_state(runner: CliRunner, status_db: Path) -> None:
    result = _invoke(runner, 5, "--json")
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["state"] == "stale"
    assert payload["content_stale"] == 1


def test_variants_ready_state(runner: CliRunner, status_db: Path) -> None:
    result = _invoke(runner, 6, "--json")
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["state"] == "variants_ready"
    assert payload["variants"][0]["status"] == "generated"
    assert payload["variants"][0]["quality_flag"] == "too_short"


def test_chapter_not_in_universe_exit_2(
    runner: CliRunner, status_db: Path
) -> None:
    result = _invoke(runner, 99)
    assert result.exit_code == 2
    assert "还没有章节工作记录" in result.stderr


def test_zero_writes(runner: CliRunner, status_db: Path) -> None:
    async def _snapshot() -> dict[str, int]:
        from songyan.db.connection import get_db

        out: dict[str, int] = {}
        async with get_db() as conn:
            for table in (
                "chapter_heads",
                "chapter_variants",
                "chapter_versions",
                "llm_call_usage",
                "plan_entities",
            ):
                cur = await conn.execute(f"SELECT COUNT(*) FROM {table}")
                out[table] = (await cur.fetchone())[0]
        return out

    import asyncio

    before = asyncio.run(_snapshot())
    result = _invoke(runner, 3)
    assert result.exit_code == 0, result.output
    after = asyncio.run(_snapshot())
    assert after == before, f"chapter status 必须零写库：{before} -> {after}"
