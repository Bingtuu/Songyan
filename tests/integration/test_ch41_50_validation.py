"""Ch41-Ch50 端到端验证 — 长链上下文压力测试.

验证目标：
1. 40 章历史数据下 pipeline 的稳定性（10 章连续运行）
2. 分层摘要系统的 budget_used 趋势
3. Task 074 对话风格卡注入不破坏长链
4. Settlement / Summary 正常生成

注意：
- 禁用 RAG 索引避免 Embedder 模型加载耗时
- 使用 MemorySaver 替代 AsyncSqliteSaver 避免 Windows 下 compile 卡顿
  （生产环境仍使用 AsyncSqliteSaver，此为测试环境变通）

记录方式：pytest 输出结构化 JSON 报告。
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from evals.runner import import_seed_chapter
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
    settlement_resp,
    summary_resp,
    writer_resp,
)

# ---------------------------------------------------------------------------
# Helpers: 构建 Ch2-Ch40 历史数据
# ---------------------------------------------------------------------------


async def _build_chapter_history(project_id: str, chapter_number: int) -> str:
    """直接 DB 写入单章 mock 历史（模拟已完成的章节）.

    Returns:
        创建的 version_id
    """
    version_id = new_id("v")
    content = (
        f"【第{chapter_number}章正文】\n\n"
        f"林动在第{chapter_number}章继续冒险，遭遇新的挑战和敌人。\n"
        f"他运用智慧化解危机，实力略有提升。\n"
    )
    version = ChapterVersion(
        version_id=version_id,
        project_id=project_id,
        chapter_number=chapter_number,
        version_number=1,
        version_type="accepted",
        content=content,
        word_count=len(content),
    )
    await ChapterVersionRepository().create(version)

    head = ChapterHead(
        project_id=project_id,
        chapter_number=chapter_number,
        current_version_id=version_id,
        accepted_version_id=version_id,
        status="accepted",
    )
    await ChapterHeadRepository().update(head)

    summary = ChapterSummary(
        chapter_number=chapter_number,
        summary=f"第{chapter_number}章：林动遭遇新挑战，剧情持续推进。",
        key_events=[f"事件{chapter_number}-A"],
        characters_appeared=["林动"],
        emotional_tone="紧张",
        impact_score=0.3,
    )
    summary_id = new_id("sum")
    await SummaryRepository().create(summary, project_id, summary_id)

    char_repo = CharacterRepository()
    characters = await char_repo.list_by_project(project_id)
    for char in characters:
        state = CharacterState(
            character_id=char.character_id,
            field="location",
            value=f"地点{chapter_number}",
            source_version_id=version_id,
        )
        await char_repo.add_state_snapshot(state)

    return version_id


# ---------------------------------------------------------------------------
# Mock response builders
# ---------------------------------------------------------------------------


def _writer_resp_ch(n: int) -> str:
    base = writer_resp()
    return f"【第{n}章】\n\n{base}"


def _chapter_responses(chapter_number: int) -> list[str]:
    """生成单章 clean path 的 mock responses（7 个）."""
    return [
        goal_resp(),
        brief_resp(),
        _writer_resp_ch(chapter_number),
        llm_clean_resp(),
        literary_resp(),
        settlement_resp(),
        summary_resp(),
    ]


def _arc_summary_resp() -> str:
    return json.dumps({
        "arc_title": "第四 Arc",
        "arc_summary": "第41-50章：林动面临最终试炼，实力大幅提升。",
        "key_events": ["事件41", "事件50"],
        "resolved_threads": [],
        "new_threads": ["新线索1"],
        "character_arcs": {"林动": "从稚嫩到成熟"},
    })


# ---------------------------------------------------------------------------
# Metrics collector
# ---------------------------------------------------------------------------


async def _collect_metrics(project_id: str) -> dict:
    async with get_db() as conn:
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM summaries WHERE project_id = ?",
            (project_id,),
        )
        summary_count = (await cursor.fetchone())[0]

        cursor = await conn.execute(
            """SELECT COUNT(*) FROM character_states cs
            JOIN characters c ON cs.character_id = c.character_id
            WHERE c.project_id = ?""",
            (project_id,),
        )
        character_state_count = (await cursor.fetchone())[0]

        cursor = await conn.execute(
            "SELECT COUNT(*) FROM chapter_versions WHERE project_id = ?",
            (project_id,),
        )
        version_count = (await cursor.fetchone())[0]

    budget_data: dict[int, dict] = {}
    for ch in range(41, 51):
        versions = await ChapterVersionRepository().list_by_chapter(
            project_id, ch, include_abandoned=True
        )
        for v in versions:
            if v.generation_metadata and "context_snapshot" in v.generation_metadata:
                snap = v.generation_metadata["context_snapshot"]
                budget_data[ch] = {
                    "tokens": snap.get("estimated_tokens", 0),
                    "budget_used": round(snap.get("budget_used", 0.0), 4),
                }
                break

    async with get_db() as conn:
        cursor = await conn.execute(
            """SELECT COUNT(*) FROM setting_snapshots
            WHERE project_id = ? AND source_quote != ''""",
            (project_id,),
        )
        setting_with_quote = (await cursor.fetchone())[0]

    return {
        "summary_count": summary_count,
        "character_state_count": character_state_count,
        "version_count": version_count,
        "budget_used_per_chapter": budget_data,
        "setting_with_source_quote": setting_with_quote,
    }


# ---------------------------------------------------------------------------
# Main test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ch41_50_long_chain_validation(test_db, mock_call_llm) -> None:
    """Ch41-Ch50 长链上下文端到端验证.

    Steps:
        1. 创建种子项目（Ch1）
        2. 快速构建 Ch2-Ch40 mock 历史
        3. 运行 Ch41-Ch50 pipeline（mock LLM）
        4. 收集并验证关键指标
    """
    project_id = await seed_project()

    # Step 1: 导入 Ch1 种子
    await import_seed_chapter(
        project_id, "evals/seeds/chapters/xuanhuan_ch1.md", chapter_number=1
    )

    # Step 2: 构建 Ch2-Ch40 历史
    for ch in range(2, 41):
        await _build_chapter_history(project_id, ch)

    async with get_db() as conn:
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM summaries WHERE project_id = ?",
            (project_id,),
        )
        assert (await cursor.fetchone())[0] == 40

    # Step 3: 准备 mock responses
    responses: list[str] = []
    for ch in range(41, 50):  # Ch41-Ch49
        responses.extend(_chapter_responses(ch))
    responses.extend(_chapter_responses(50))   # Ch50 基础
    responses.append(_arc_summary_resp())       # Ch50 arc_summary

    mock_call_llm.responses = responses  # type: ignore[attr-defined]

    # Patch: 禁用 RAG 索引（避免 Embedder 模型加载耗时）
    # checkpointer 已在 conftest test_db fixture 中自动切换为 MemorySaver
    with patch("songyan.workflows._helpers._index_accepted_chapter"):
        with patch("songyan.agents.arc_summary_generator.call_llm", mock_call_llm):
            result = await run_project_pipeline(
                project_id=project_id,
                chapter_range=(41, 50),
                mode_id="webnovel",
                auto_confirm=True,
                on_failure="abort",
            )

    # ===== 基础断言 =====
    assert result.final_status == "completed"
    assert result.chapters_completed == list(range(41, 51))
    assert result.chapters_failed == []

    # ===== 指标收集 =====
    metrics = await _collect_metrics(project_id)

    assert metrics["summary_count"] == 50
    assert metrics["character_state_count"] >= 39

    # Ch1 seed(1) + Ch2-40 mock(39) + Ch41-50 pipeline(各1版本 draft→accepted) = 50
    expected_versions = 1 + 39 + 10
    assert metrics["version_count"] == expected_versions

    budget_data = metrics["budget_used_per_chapter"]
    assert len(budget_data) == 10

    max_budget = max(d["budget_used"] for d in budget_data.values())
    assert max_budget <= 1.0, f"Budget exceeded! max={max_budget:.2%}"

    report = {
        "validation": "Ch41-Ch50 Long Chain",
        "project_id": project_id,
        "chapters_completed": result.chapters_completed,
        "total_duration_sec": round(result.total_duration_sec, 2),
        "history_summaries": 40,
        "generated_summaries": metrics["summary_count"],
        "character_state_count": metrics["character_state_count"],
        "version_count": metrics["version_count"],
        "max_budget_used": round(max_budget, 4),
        "budget_used_by_chapter": {
            f"Ch{ch}": data for ch, data in budget_data.items()
        },
        "setting_with_source_quote": metrics["setting_with_source_quote"],
        "llm_mock_calls_total": mock_call_llm._call_count,  # type: ignore[attr-defined]
        "status": "PASS",
    }

    print("\n" + "=" * 60)
    print("Ch41-Ch50 长链端到端验证报告")
    print("=" * 60)
    print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    print("=" * 60)
