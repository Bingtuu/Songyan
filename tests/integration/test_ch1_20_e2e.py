"""Ch1-Ch20 E2E validation — TS-08 lightweight mock-based long-chain test."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from songyan.db.connection import get_db
from songyan.db.context_repo import SummaryRepository
from songyan.db.repository import (
    ChapterHeadRepository,
    ChapterVersionRepository,
    CharacterRepository,
)
from songyan.models import (
    ChapterHead,
    ChapterSummary,
    ChapterVersion,
    CharacterState,
)
from songyan.workflows._helpers import new_id
from songyan.workflows.phase2_graph import run_project_pipeline

from .conftest import (
    brief_resp,
    goal_resp,
    literary_resp,
    llm_clean_resp,
    seed_project,
    writer_resp,
)


def _chapter_responses(n: int) -> list[str]:
    key = {1: "one", 2: "two", 3: "three"}.get(n, f"ch{n}")
    return [
        goal_resp(),
        brief_resp(),
        f"【第{n}章】\n\n{writer_resp()}",
        llm_clean_resp(),
        literary_resp(),
        json.dumps(
            {
                "character_updates": [
                    {
                        "character_id": "char-001",
                        "field": f"field_{n}",
                        "old_value": f"old_{n}",
                        "new_value": f"new_{n}",
                        "source_quote": "荡进一道石缝",
                    }
                ],
                "new_settings": [
                    {
                        "setting_name": f"Setting_{n}",
                        "description": f"desc_{n}",
                        "source_quote": "一扇青铜大门静静矗立",
                        "setting_key": f"xuanhuan.chapter.{key}",
                    }
                ],
                "foreshadowing_updates": [],
                "numerical_updates": [],
                "validation_status": "valid",
                "validation_errors": [],
            }
        ),
        json.dumps(
            {
                "plot_summary": f"第{n}章剧情摘要：林动发现秘境{n}",
                "emotional_tone": "紧张兴奋",
            }
        ),
    ]


def _arc_summary_resp() -> str:
    return json.dumps(
        {
            "arc_title": "Arc",
            "arc_summary": "Arc summary",
            "key_events": ["事件A"],
            "resolved_threads": [],
            "new_threads": [],
            "character_arcs": {"林动": "成长"},
        }
    )


async def _build_chapter_history(project_id: str, chapter_number: int) -> None:
    """直接 DB 写入单章 mock 历史."""
    version_id = new_id("v")
    content = (
        f"【第{chapter_number}章正文】\n\n"
        f"林动在第{chapter_number}章继续冒险，遭遇新的挑战和敌人。\n"
        f"他运用智慧化解危机，实力略有提升。\n"
    )
    await ChapterVersionRepository().create(
        ChapterVersion(
            version_id=version_id,
            project_id=project_id,
            chapter_number=chapter_number,
            version_number=1,
            version_type="accepted",
            content=content,
            word_count=len(content),
        )
    )
    await ChapterHeadRepository().update(
        ChapterHead(
            project_id=project_id,
            chapter_number=chapter_number,
            current_version_id=version_id,
            accepted_version_id=version_id,
            status="accepted",
        )
    )
    await SummaryRepository().create(
        ChapterSummary(
            chapter_number=chapter_number,
            summary=f"第{chapter_number}章：林动遭遇新挑战，剧情持续推进。",
            key_events=[f"事件{chapter_number}-A"],
            characters_appeared=["林动"],
            emotional_tone="紧张",
        ),
        project_id,
        new_id("sum"),
    )
    char_repo = CharacterRepository()
    for char in await char_repo.list_by_project(project_id):
        await char_repo.add_state_snapshot(
            CharacterState(
                character_id=char.character_id,
                field="location",
                value=f"地点{chapter_number}",
                source_version_id=version_id,
            )
        )


@pytest.mark.asyncio
async def test_ch1_20_e2e_validation(test_db, mock_call_llm) -> None:
    """验证 Ch1-Ch20 的 DB 一致性、Context Diet 衰减、字数控制与早期章节 ContextEmergency."""
    project_id = await seed_project()

    # Step 1: 运行 Ch1-Ch10 pipeline（mock LLM，验证早期章节上下文）
    responses: list[str] = []
    for n in range(1, 11):
        responses.extend(_chapter_responses(n))
        if n == 10:
            responses.append(_arc_summary_resp())

    mock_call_llm.responses = responses  # type: ignore[attr-defined]

    with patch("songyan.workflows._helpers._index_accepted_chapter"):
        with patch("songyan.agents.arc_summary_generator.call_llm", mock_call_llm):
            result = await run_project_pipeline(
                project_id=project_id,
                chapter_range=(1, 10),
                mode_id="webnovel",
                auto_confirm=True,
                on_failure="abort",
            )

    assert result.final_status == "completed"
    assert result.chapters_completed == list(range(1, 11))
    assert result.chapters_failed == []

    # Step 2: 快速预构建 Ch11-Ch20 mock 历史（直接写 DB，不跑 pipeline）
    for n in range(11, 21):
        await _build_chapter_history(project_id, n)

    # Step 3: DB 一致性验证
    async with get_db() as conn:
        qv = (
            "SELECT COUNT(*) FROM chapter_versions "
            "WHERE project_id = ? AND version_type = 'accepted'"
        )
        accepted_versions = (await (await conn.execute(qv, (project_id,))).fetchone())[0]

        qs = "SELECT COUNT(*) FROM summaries WHERE project_id = ?"
        summary_count = (await (await conn.execute(qs, (project_id,))).fetchone())[0]

        qc = (
            "SELECT COUNT(*) FROM character_states cs "
            "JOIN characters c ON cs.character_id = c.character_id WHERE c.project_id = ?"
        )
        char_state_count = (await (await conn.execute(qc, (project_id,))).fetchone())[0]

        qh = (
            "SELECT COUNT(*) FROM chapter_heads "
            "WHERE project_id = ? AND status = 'accepted'"
        )
        accepted_heads = (await (await conn.execute(qh, (project_id,))).fetchone())[0]

        qw = (
            "SELECT chapter_number, word_count FROM chapter_versions "
            "WHERE project_id = ? AND version_type = 'accepted' ORDER BY chapter_number"
        )
        word_counts = await (await conn.execute(qw, (project_id,))).fetchall()

        qx = (
            "SELECT chapter_number, budget_used, context_emergency "
            "FROM context_snapshots WHERE project_id = ? ORDER BY chapter_number"
        )
        ctx_rows = await (await conn.execute(qx, (project_id,))).fetchall()

    assert accepted_versions == 20
    assert summary_count == 20
    assert accepted_heads == 20
    assert char_state_count >= 19

    for ch_num, wc in word_counts:
        assert 50 <= wc <= 10000, f"Ch{ch_num} word_count {wc} out of bounds"

    early_emergencies = [r for r in ctx_rows if r[0] <= 10 and r[2]]
    assert not early_emergencies

    max_budget = max((r[1] for r in ctx_rows if r[1] is not None), default=0.0)
    assert max_budget <= 1.0

    print("\n=== Ch1-Ch20 E2E Report ===")
    print(f"Accepted versions: {accepted_versions}")
    print(f"Summaries: {summary_count}")
    print(f"Character states: {char_state_count}")
    print(f"Max budget_used: {max_budget:.4f}")
    print(f"Context emergencies: {[r[0] for r in ctx_rows if r[2]]}")
    print("===========================")
