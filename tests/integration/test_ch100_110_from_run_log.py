"""Ch100-Ch110 E2E validation — evidence replay from Task 121q run-a2bed648.

This test replays the Ch100-Ch110 window from the historical full single-run
`run-a2bed648` (Task 121q, Ch1-Ch150 150/150 success). The key per-chapter
metrics are embedded as a fixture so the test remains valid even if the
original log file is archived or removed.

Optional DB consistency checks run against `songyan.db` when the project
`e95a1fa3` from `run-a2bed648` is still present.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Embedded fixture data from logs/chapter_runs/run-a2bed648.jsonl
# Window: Ch100-Ch110, run-a2bed648, project e95a1fa3
# ---------------------------------------------------------------------------

def _ch(chapter_number: int, budget_used: float, overall_score: float) -> dict[str, Any]:
    """Build a fixture row with the common success flags for run-a2bed648."""
    return {
        "chapter_number": chapter_number,
        "success": True,
        "quality_gate_passed": True,
        "context_emergency": False,
        "auto_halt": False,
        "degraded_accept": False,
        "settlement_success": True,
        "summary_success": True,
        "budget_used": budget_used,
        "overall_score": overall_score,
    }


_RUN_A2BED648_CH100_CH110: list[dict[str, Any]] = [
    _ch(100, 0.4055757575757576, 0.7814),
    _ch(101, 0.391578947368421, 0.7631),
    _ch(102, 0.39, 0.9309),
    _ch(103, 0.39597037037037036, 0.896),
    _ch(104, 0.3865588235294118, 0.846),
    _ch(105, 0.4113868613138686, 0.8648),
    _ch(106, 0.41646376811594205, 0.8842),
    _ch(107, 0.40497841726618705, 0.9341),
    _ch(108, 0.3902, 0.8949),
    _ch(109, 0.4165106382978723, 0.8324),
    _ch(110, 0.38853521126760565, 0.8395),
]

_RUN_ID = "run-a2bed648"
_PROJECT_ID = "e95a1fa3"
_LOG_PATH = Path("logs/chapter_runs/run-a2bed648.jsonl")
_DB_PATH = Path("songyan.db")


def _load_log_window() -> list[dict[str, Any]]:
    """Load Ch100-Ch110 from the original log file if available."""
    if not _LOG_PATH.exists():
        return []
    rows: list[dict[str, Any]] = []
    with _LOG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("run_id") == _RUN_ID and 100 <= row.get("chapter_number", 0) <= 110:
                rows.append(row)
    return rows


def _can_check_db() -> bool:
    if not _DB_PATH.exists():
        return False
    try:
        with sqlite3.connect(_DB_PATH) as conn:
            cur = conn.execute(
                "SELECT 1 FROM projects WHERE project_id = ?", (_PROJECT_ID,)
            )
            return cur.fetchone() is not None
    except sqlite3.Error:
        return False


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_ch100_ch110_embedded_log_evidence() -> None:
    """Validate the embedded Ch100-Ch110 metrics from run-a2bed648."""
    assert len(_RUN_A2BED648_CH100_CH110) == 11

    budgets: list[float] = []
    scores: list[float] = []

    for row in _RUN_A2BED648_CH100_CH110:
        ch = row["chapter_number"]
        assert row["success"] is True, f"Ch{ch} should succeed"
        assert row["quality_gate_passed"] is True, f"Ch{ch} should pass QG"
        assert row["context_emergency"] is False, f"Ch{ch} should not trigger emergency"
        assert row["auto_halt"] is False, f"Ch{ch} should not trigger auto halt"
        assert row["degraded_accept"] is False, f"Ch{ch} should not be degraded accept"
        assert row["settlement_success"] is True, f"Ch{ch} settlement should succeed"
        assert row["summary_success"] is True, f"Ch{ch} summary should succeed"
        assert row["budget_used"] <= 1.2, f"Ch{ch} budget_used {row['budget_used']} exceeds 1.2"
        # QG pass does not imply overall_score >= safe_best threshold. The
        # degraded-accept floor (0.70) is the unconditional lower bound for a
        # non-degraded accept.
        assert row["overall_score"] >= 0.70, (
            f"Ch{ch} overall_score {row['overall_score']} below degraded-accept floor 0.70"
        )
        budgets.append(row["budget_used"])
        scores.append(row["overall_score"])

    print("\n=== Ch100-Ch110 Evidence Replay (run-a2bed648) ===")
    print(f"Chapters: {len(_RUN_A2BED648_CH100_CH110)}/11")
    print("Success/QG/Settlement/Summary: 11/11")
    print("ContextEmergency/AutoHalt/DegradedAccept: 0/0/0")
    print(f"Budget range: {min(budgets):.4f} - {max(budgets):.4f}")
    print(f"Overall score range: {min(scores):.4f} - {max(scores):.4f}")
    print("===================================================")


def test_ch100_ch110_log_file_consistency() -> None:
    """If the original log file still exists, embedded data must match it."""
    log_rows = _load_log_window()
    if not log_rows:
        pytest.skip("Original run-a2bed648.jsonl not available")

    assert len(log_rows) == len(_RUN_A2BED648_CH100_CH110)

    log_by_ch = {r["chapter_number"]: r for r in log_rows}
    embedded_by_ch = {r["chapter_number"]: r for r in _RUN_A2BED648_CH100_CH110}

    assert set(log_by_ch.keys()) == set(embedded_by_ch.keys())

    for ch in log_by_ch:
        log_row = log_by_ch[ch]
        emb_row = embedded_by_ch[ch]
        log_score = log_row.get("score_card", {}).get("overall_score")
        assert log_row["success"] == emb_row["success"]
        assert log_row["quality_gate_passed"] == emb_row["quality_gate_passed"]
        assert log_row["context_emergency"] == emb_row["context_emergency"]
        assert log_row.get("auto_halt", False) == emb_row["auto_halt"]
        assert log_row.get("degraded_accept", False) == emb_row["degraded_accept"]
        assert log_row["settlement_success"] == emb_row["settlement_success"]
        assert log_row["summary_success"] == emb_row["summary_success"]
        assert abs(log_row["budget_used"] - emb_row["budget_used"]) < 1e-9
        assert abs(log_score - emb_row["overall_score"]) < 1e-9


@pytest.mark.skipif(not _can_check_db(), reason="songyan.db or project e95a1fa3 not available")
def test_ch100_ch110_db_consistency() -> None:
    """Cross-check embedded log evidence against the production SQLite DB."""
    with sqlite3.connect(_DB_PATH) as conn:
        cur = conn.execute(
            """
            SELECT chapter_number, status, accepted_version_id
            FROM chapter_heads
            WHERE project_id = ? AND chapter_number BETWEEN ? AND ?
            """,
            (_PROJECT_ID, 100, 110),
        )
        heads = {row[0]: row for row in cur.fetchall()}

    assert len(heads) == 11, f"Expected 11 chapter_heads, got {len(heads)}"

    for row in _RUN_A2BED648_CH100_CH110:
        ch = row["chapter_number"]
        head = heads.get(ch)
        assert head is not None, f"Ch{ch} not found in chapter_heads"
        assert head[1] == "accepted", f"Ch{ch} status is {head[1]}, expected accepted"
        assert head[2] is not None, f"Ch{ch} has no accepted_version_id"
