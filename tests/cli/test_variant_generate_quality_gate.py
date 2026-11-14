"""task 245 P2/P3: variant generate 拒写质量门的 CLI 口径与重试 prompt。

- 全槽拒写（重试后仍失败）→ exit 2（B11 业务拒绝）
- 部分成功 → exit 0，stderr 列出失败槽及原因
- default_slot_draft 重试时注入坚持指令
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest
from click.testing import CliRunner

from songyan.cli.main import cli
from songyan.config import settings
from songyan.db.migrations import init_schema
from songyan.db.repository import ProjectRepository
from songyan.models.project import ProjectSetting
from songyan.services.variant_generate import SlotDraft, default_slot_draft

_PROJECT = "p-qgate"
_CHAPTER = 2

GOOD = "末班铜牌在指间发沉，" * 12  # 108 字
REFUSAL = "事实圣经不足，无法完成草稿。"
REFUSAL_B = "仍无法完成，事实集缺项。"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
async def qg_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "variant-quality-gate.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="mystery",
            mode_id="webnovel",
            protagonist_name="陈照",
            title="quality gate",
        ),
        _PROJECT,
    )
    return db_path


def _install_seq_draft(
    monkeypatch: pytest.MonkeyPatch, contents: list[str]
) -> AsyncMock:
    drafts = iter(
        [SlotDraft(content=c, cost_cny_estimate=0.01) for c in contents]
    )

    async def _draft(**_kwargs: Any) -> SlotDraft:
        return next(drafts)

    mock = AsyncMock(side_effect=_draft)
    monkeypatch.setattr(
        "songyan.services.variant_generate.default_slot_draft",
        mock,
    )
    return mock


def test_all_slots_failed_exit_2(
    runner: CliRunner, qg_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # n=2：每槽首抽 + 重试各 1 次，全部拒写
    mock = _install_seq_draft(
        monkeypatch,
        [REFUSAL, REFUSAL, REFUSAL_B, REFUSAL_B],
    )

    result = runner.invoke(
        cli,
        [
            "variant",
            "generate",
            "--project-id",
            _PROJECT,
            "--chapter",
            str(_CHAPTER),
            "--json",
        ],
    )

    assert result.exit_code == 2, result.output
    assert "拒写" in result.stderr or "quality_flag" in result.stderr
    payload = json.loads(result.stdout)
    assert len(payload["variants"]) == 2
    assert all(v["quality_flag"] for v in payload["variants"])
    assert mock.await_count == 4


def test_partial_failure_exit_0_with_failed_listing(
    runner: CliRunner, qg_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # 槽1 成功；槽2 首抽拒写、重试仍拒写
    mock = _install_seq_draft(monkeypatch, [GOOD, REFUSAL, REFUSAL_B])

    result = runner.invoke(
        cli,
        [
            "variant",
            "generate",
            "--project-id",
            _PROJECT,
            "--chapter",
            str(_CHAPTER),
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "槽 2" in result.stderr
    payload = json.loads(result.stdout)
    by_slot = {v["slot_index"]: v for v in payload["variants"]}
    assert by_slot[1]["quality_flag"] is None
    assert by_slot[2]["quality_flag"] == "refusal_keyword"
    assert mock.await_count == 3


def test_retry_prompt_injects_persistence_instruction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen_prompts: list[str] = []

    async def _fake_call_llm(prompt: str, *, role: str) -> str:
        seen_prompts.append(prompt)
        return GOOD

    monkeypatch.setattr("songyan.llm.call_llm", _fake_call_llm)
    monkeypatch.setattr(
        "songyan.llm.client.resolve_llm_config",
        lambda _role: type("C", (), {"model": "mock-model"})(),
    )

    asyncio.run(
        default_slot_draft(
            project_id="p",
            chapter=1,
            slot_index=1,
            bible_text="（空）",
            fingerprint="fp",
            retry_reason="too_short",
        )
    )

    assert len(seen_prompts) == 1
    assert "too_short" in seen_prompts[0]
    assert "严禁" in seen_prompts[0] or "必须" in seen_prompts[0]
