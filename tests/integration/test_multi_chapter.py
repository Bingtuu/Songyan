"""Integration tests for multi-chapter pipeline (Phase2)."""

from __future__ import annotations

import json

import pytest

from songyan.db.connection import get_db
from songyan.workflows.phase2_graph import run_project_pipeline

from .conftest import (
    brief_resp,
    goal_resp,
    literary_resp,
    llm_clean_resp,
    seed_project,
    writer_resp,
)

pytestmark = pytest.mark.performance


def _writer_resp_ch(n: int) -> str:
    """为第 n 章生成不同的 writer 响应."""
    base = writer_resp()
    return f"【第{n}章】\n\n{base}"


def _settlement_resp_ch(n: int) -> str:
    """为第 n 章生成不同的 settlement 响应."""
    key_suffix = {1: "one", 2: "two", 3: "three"}.get(n, "later")
    return json.dumps(
        {
            "character_updates": [
                {
                    "character_id": "char-001",
                    "field": f"field_{n}",
                    "old_value": f"new_{n - 1}" if n > 1 else f"old_{n}",
                    "new_value": f"new_{n}",
                    "source_quote": "荡进一道石缝",
                }
            ],
            "new_settings": [
                {
                    "setting_name": f"Setting_{n}",
                    "description": f"desc_{n}",
                    "source_quote": "一扇青铜大门静静矗立",
                    "setting_key": f"xuanhuan.chapter.{key_suffix}",
                }
            ],
            "foreshadowing_updates": [],
            "numerical_updates": [],
            "validation_status": "valid",
            "validation_errors": [],
        }
    )


def _summary_resp_ch(n: int) -> str:
    """为第 n 章生成不同的 summary 响应."""
    return json.dumps(
        {
            "plot_summary": f"第{n}章剧情摘要：林动发现秘境{n}",
            "emotional_tone": "紧张兴奋",
        }
    )


# ---------------------------------------------------------------------------
# Integration: 3 chapters success
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multi_chapter_3_success(test_db, mock_call_llm) -> None:
    """完整 3 章链路：验证 DB 中生成 3 个 summary 和 3 个 chapter_goals."""
    project_id = await seed_project()

    # 构建 3 章的 mock responses（每章 7 个 LLM call）
    mock_call_llm.responses = [  # type: ignore[attr-defined]
        # Chapter 1
        goal_resp(),
        brief_resp(),
        _writer_resp_ch(1),
        llm_clean_resp(),
        literary_resp(),
        _settlement_resp_ch(1),
        _summary_resp_ch(1),
        # Chapter 2
        goal_resp(),
        brief_resp(),
        _writer_resp_ch(2),
        llm_clean_resp(),
        literary_resp(),
        _settlement_resp_ch(2),
        _summary_resp_ch(2),
        # Chapter 3
        goal_resp(),
        brief_resp(),
        _writer_resp_ch(3),
        llm_clean_resp(),
        literary_resp(),
        _settlement_resp_ch(3),
        _summary_resp_ch(3),
    ]

    result = await run_project_pipeline(
        project_id=project_id,
        chapter_range=(1, 3),
        mode_id="webnovel",
        auto_confirm=True,
    )

    assert result.final_status == "completed"
    assert result.chapters_completed == [1, 2, 3]
    assert result.chapters_failed == []

    # 验证 summaries 表有 3 条记录
    async with get_db() as conn:
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM summaries WHERE project_id = ?",
            (project_id,),
        )
        row = await cursor.fetchone()
    assert row[0] == 3

    # 验证 chapter_goals 表有记录（当前实现每章会创建 2 个 goal：
    # define_chapter_goal 内部 1 个 + goal_planner_node 1 个）
    async with get_db() as conn:
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM chapter_goals WHERE project_id = ?",
            (project_id,),
        )
        row = await cursor.fetchone()
    assert row[0] >= 3  # 至少 3 条（每章 1 条）


@pytest.mark.asyncio
async def test_multi_chapter_previous_summary_in_goal(test_db, mock_call_llm) -> None:
    """验证 chapter 2 的 goal 中 previous_summary 包含 chapter 1 的 summary."""
    project_id = await seed_project()

    mock_call_llm.responses = [  # type: ignore[attr-defined]
        # Chapter 1
        goal_resp(),
        brief_resp(),
        _writer_resp_ch(1),
        llm_clean_resp(),
        literary_resp(),
        _settlement_resp_ch(1),
        _summary_resp_ch(1),
        # Chapter 2
        goal_resp(),
        brief_resp(),
        _writer_resp_ch(2),
        llm_clean_resp(),
        literary_resp(),
        _settlement_resp_ch(2),
        _summary_resp_ch(2),
    ]

    result = await run_project_pipeline(
        project_id=project_id,
        chapter_range=(1, 2),
        auto_confirm=True,
    )

    assert result.final_status == "completed"

    # 读取 chapter 2 的 goal，验证 previous_summary 非空
    from sqlite3 import Row

    async with get_db() as conn:
        conn.row_factory = Row
        cursor = await conn.execute(
            """SELECT previous_summary FROM chapter_goals
            WHERE project_id = ? AND chapter_number = ?""",
            (project_id, 2),
        )
        row = await cursor.fetchone()

    assert row is not None
    prev_summary = row["previous_summary"] or ""
    # 第 1 章的 summary 是 "第1章剧情摘要：林动发现秘境1"
    assert "林动发现秘境1" in prev_summary


@pytest.mark.asyncio
async def test_multi_chapter_accumulated_summary(test_db, mock_call_llm) -> None:
    """验证 ProjectRunResult.accumulated_summary 正确拼接."""
    project_id = await seed_project()

    mock_call_llm.responses = [  # type: ignore[attr-defined]
        # Chapter 1
        goal_resp(),
        brief_resp(),
        _writer_resp_ch(1),
        llm_clean_resp(),
        literary_resp(),
        _settlement_resp_ch(1),
        _summary_resp_ch(1),
        # Chapter 2
        goal_resp(),
        brief_resp(),
        _writer_resp_ch(2),
        llm_clean_resp(),
        literary_resp(),
        _settlement_resp_ch(2),
        _summary_resp_ch(2),
    ]

    result = await run_project_pipeline(
        project_id=project_id,
        chapter_range=(1, 2),
        auto_confirm=True,
    )

    assert result.final_status == "completed"
    assert "第1章" in result.accumulated_summary
    assert "第2章" in result.accumulated_summary
    assert "林动发现秘境1" in result.accumulated_summary
    assert "林动发现秘境2" in result.accumulated_summary
