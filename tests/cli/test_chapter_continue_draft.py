"""M4 步 3 切片 3: chapter continue 组装 + 生成（tech-m4 §5 步 3 / B6 / B12 / 评审 M3）。

last_chapter_ending 透传断言（1200 字 → 末尾 800；不足全取；恰好 800 边界）；
chapter_goal 回退（无行 → words_per_chapter 兜底）；brief 缺失 None 继续；
draft 版本追加 + head 指针；--json 全字段锁死。每测试钉死 approved / accepted 集不变。
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest
from click.testing import CliRunner, Result

import songyan.agents.context_manager as context_manager
from songyan.cli.main import cli
from songyan.config import settings
from songyan.db.migrations import init_schema
from songyan.db.plan_fact_repo import PlanFactRepository
from songyan.db.repository import (
    ChapterHeadRepository,
    ChapterVersionRepository,
    ProjectRepository,
)
from songyan.models.chapter import ChapterHead, ChapterVersion
from songyan.models.project import ProjectSetting
from songyan.models.settlement import StateSettlement
from songyan.services.chapter_accept import accept_chapter
from songyan.utils.word_count import count_chinese_words

_PROJECT = "p-m4-cont-draft"
_BODY = "夜雨落在南站站台。\n\n陈照收起铜镜，转身走进雨里。\n\n末班车进站了。"
_SUMMARY_JSON = (
    '{"plot_summary": "陈照抵达北站。", "key_events": ["陈照到北站"], '
    '"characters_appeared": ["陈照"], "emotional_tone": "沉静"}'
)


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
async def draft_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "m4-cont-draft.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")
    await init_schema(db_path)
    await ProjectRepository().create(
        ProjectSetting(
            genre_id="mystery_noir",
            mode_id="webnovel",
            protagonist_name="陈照",
            title="m4 continue draft",
            words_per_chapter=2500,
        ),
        _PROJECT,
    )
    return db_path


def _install_mocks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("songyan.agents.writer.call_llm", AsyncMock(return_value=_BODY))
    monkeypatch.setattr(
        "songyan.agents.summary_writer.call_llm", AsyncMock(return_value=_SUMMARY_JSON)
    )
    monkeypatch.setattr(
        "songyan.services.chapter_continue.extract_settlement",
        AsyncMock(return_value=StateSettlement(validation_status="valid")),
    )


async def _seed_accepted(chapter: int, content: str) -> str:
    version = ChapterVersion(
        version_id=f"v-draft-{chapter}-draft",
        project_id=_PROJECT,
        chapter_number=chapter,
        version_number=1,
        version_type="draft",
        content=content,
        word_count=count_chinese_words(content),
    )
    await ChapterVersionRepository().create(version)
    await ChapterHeadRepository().update(
        ChapterHead(
            project_id=_PROJECT,
            chapter_number=chapter,
            current_version_id=version.version_id,
            accepted_version_id=None,
            status="draft",
        )
    )
    outcome = await accept_chapter(_PROJECT, chapter)
    # 让下一章进入章宇宙（目标章），否则全 accepted 直接返回 None。
    await ChapterHeadRepository().update(
        ChapterHead(
            project_id=_PROJECT,
            chapter_number=chapter + 1,
            current_version_id=None,
            accepted_version_id=None,
            status="draft",
        )
    )
    return outcome.accepted_version_id


def _spy_assemble(
    monkeypatch: pytest.MonkeyPatch, recorded: list[dict[str, Any]]
) -> None:
    original = context_manager.assemble_context_package

    def _spy(**kwargs: Any) -> Any:
        recorded.append(kwargs)
        return original(**kwargs)

    monkeypatch.setattr(context_manager, "assemble_context_package", _spy)


def _invoke_continue(runner: CliRunner, *extra: str) -> Result:
    return runner.invoke(cli, ["chapter", "continue", "--project-id", _PROJECT, *extra])


async def _seed_empty_head(chapter: int) -> None:
    await ChapterHeadRepository().update(
        ChapterHead(
            project_id=_PROJECT,
            chapter_number=chapter,
            current_version_id=None,
            accepted_version_id=None,
            status="draft",
        )
    )


async def _approved_snapshot() -> frozenset[tuple[str, str]]:
    repo = PlanFactRepository()
    pairs: set[tuple[str, str]] = set()
    for row in await repo.list_canon_entities(_PROJECT):
        pairs.add(("entity", row.entity_id))
    for row in await repo.list_canon_attributes(_PROJECT):
        pairs.add(("attribute", row.attribute_id))
    for row in await repo.list_canon_events(_PROJECT):
        pairs.add(("event", row.event_id))
    for row in await repo.list_canon_clues(_PROJECT):
        pairs.add(("clue", row.clue_id))
    for row in await repo.list_canon_time_anchors(_PROJECT):
        pairs.add(("time_anchor", row.anchor_id))
    return frozenset(pairs)


async def _accepted_snapshot() -> frozenset[tuple[int, str]]:
    heads = await ChapterHeadRepository().list_by_project(_PROJECT)
    return frozenset(
        (h.chapter_number, h.accepted_version_id)
        for h in heads
        if h.accepted_version_id is not None
    )


# --- last_chapter_ending 透传（B6 节选注入通道） ------------------------------


def test_last_chapter_ending_truncated_to_800(
    runner: CliRunner, draft_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    content = "雨" * 1199 + "尾"
    asyncio.run(_seed_accepted(1, content))
    _install_mocks(monkeypatch)
    recorded: list[dict[str, Any]] = []
    _spy_assemble(monkeypatch, recorded)

    result = _invoke_continue(runner)
    assert result.exit_code == 0, result.output
    assert len(recorded) == 1
    ending = recorded[0]["last_chapter_ending"]
    assert len(ending) == 800
    assert ending == content[-800:]
    assert ending.endswith("尾")


def test_last_chapter_ending_short_content_full(
    runner: CliRunner, draft_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    content = "短章结尾：铜镜发烫。"
    asyncio.run(_seed_accepted(1, content))
    _install_mocks(monkeypatch)
    recorded: list[dict[str, Any]] = []
    _spy_assemble(monkeypatch, recorded)

    result = _invoke_continue(runner)
    assert result.exit_code == 0, result.output
    assert recorded[0]["last_chapter_ending"] == content


def test_last_chapter_ending_exact_800_boundary(
    runner: CliRunner, draft_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    content = "八" * 799 + "尾"
    assert len(content) == 800
    asyncio.run(_seed_accepted(1, content))
    _install_mocks(monkeypatch)
    recorded: list[dict[str, Any]] = []
    _spy_assemble(monkeypatch, recorded)

    result = _invoke_continue(runner)
    assert result.exit_code == 0, result.output
    ending = recorded[0]["last_chapter_ending"]
    assert len(ending) == 800
    assert ending == content


def test_first_chapter_empty_ending(
    runner: CliRunner, draft_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """首章无上一章 → last_chapter_ending 默认空串。"""
    asyncio.run(_seed_empty_head(1))
    _install_mocks(monkeypatch)
    recorded: list[dict[str, Any]] = []
    _spy_assemble(monkeypatch, recorded)

    result = _invoke_continue(runner)
    assert result.exit_code == 0, result.output
    assert recorded[0]["last_chapter_ending"] == ""


# --- chapter_goal 回退 + previous_summary 注入 + brief 缺失 --------------------


def test_chapter_goal_fallback_and_previous_summary(
    runner: CliRunner, draft_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    asyncio.run(_seed_accepted(1, "第一章：陈照到了北站。"))
    _install_mocks(monkeypatch)
    recorded: list[dict[str, Any]] = []
    _spy_assemble(monkeypatch, recorded)

    result = _invoke_continue(runner)
    assert result.exit_code == 0, result.output
    goal = recorded[0]["chapter_goal"]
    assert goal.chapter_number == 2
    # 无 chapter_goal 行 → words_per_chapter 兜底（项目 2500）。
    assert goal.word_count_target == 2500
    # 120 字 plot_summary 经既有 recent_plot 注入（settlement 后 summaries 行）。
    assert "陈照抵达北站" in goal.previous_summary
    # brief 缺失 → None 继续。
    assert recorded[0]["creative_brief"] is None


# --- draft 版本追加 + head 指针 + --json 锁死 ---------------------------------


def test_draft_version_appended_and_head_pointer(
    runner: CliRunner, draft_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    asyncio.run(_seed_accepted(1, "第一章：陈照到了北站。"))
    before_approved = asyncio.run(_approved_snapshot())
    before_accepted = asyncio.run(_accepted_snapshot())
    _install_mocks(monkeypatch)

    result = _invoke_continue(runner, "--json")
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)

    version = asyncio.run(
        ChapterVersionRepository().get(payload["version_id"])
    )
    assert version is not None
    assert version.chapter_number == 2
    assert version.version_type == "draft"
    assert "末班车进站" in version.content
    assert version.word_count == payload["word_count"]
    assert payload["word_count"] == count_chinese_words(version.content)

    head = asyncio.run(ChapterHeadRepository().get(_PROJECT, 2))
    assert head is not None
    assert head.current_version_id == payload["version_id"]
    assert head.accepted_version_id is None
    assert head.status == "draft"

    assert asyncio.run(_approved_snapshot()) == before_approved
    assert asyncio.run(_accepted_snapshot()) == before_accepted


def test_json_output_fields_locked(
    runner: CliRunner, draft_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    asyncio.run(_seed_accepted(1, "第一章：陈照到了北站。"))
    _install_mocks(monkeypatch)

    result = _invoke_continue(runner, "--json")
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert set(payload.keys()) == {"chapter", "version_id", "word_count", "cost_cny", "next_hint"}
    assert payload["chapter"] == 2
    assert payload["version_id"]
    assert payload["word_count"] > 0
    assert isinstance(payload["cost_cny"], (int, float))
    assert "chapter accept --chapter 2" in payload["next_hint"]
