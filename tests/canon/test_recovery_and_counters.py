"""fix #1 (bounded explicit auto-recovery) and fix #5 (retry budget survives --resume)."""
import pytest

from songyan.canon import recovery, store
from songyan.config import settings


@pytest.fixture(autouse=True)
def _db(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path}/r.db")


def _st(**kw):
    base = {"project_id": "p", "chapter_number": 1, "status": "settlement_review",
            "_settlement_needs_human_review": True}
    base.update(kw)
    return base


@pytest.mark.asyncio
async def test_summary_missing_retries_summary_then_chapter_then_explicit_error():
    s = _st(_summary_missing_facts=["缺少主角决策/认知变化"])
    acts = [(await recovery.auto_recover_node(s))["_recover_action"] for _ in range(5)]
    assert acts == ["retry_summary", "retry_summary", "retry_chapter", "retry_chapter", "error"]
    out = await recovery.auto_recover_node(s)
    assert out["error"].startswith("auto_recover_exhausted[summary_missing_facts]")
    assert "缺少主角决策" in out["error"]


@pytest.mark.asyncio
async def test_qg_false_regenerates_chapter_and_resets_state():
    s = _st(_quality_gate_passed=False, _skip_settlement=True, _quality_gate_failures=["coherence"])
    out = await recovery.auto_recover_node(s)
    assert out["_recover_action"] == "retry_chapter" and out["revision_round"] == 0
    assert out["_quality_gate_passed"] is None and out["error"] is None


@pytest.mark.asyncio
async def test_accepted_chapter_is_done():
    out = await recovery.auto_recover_node({"project_id": "p", "chapter_number": 1, "status": "completed"})
    assert out["_recover_action"] == "done"


def test_retry_budget_resets_per_process_token():
    store.bump_count("p", 2, "canon", token="run-A")
    store.bump_count("p", 2, "canon", token="run-A")
    assert store.get_count("p", 2, "canon", token="run-A") == 2
    # a resumed run (new process token) gets a fresh, bounded budget
    assert store.get_count("p", 2, "canon", token="run-B") == 0
    assert store.bump_count("p", 2, "canon", token="run-B") == 1
