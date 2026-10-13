"""fix #1: explicit, bounded auto-recovery for settlement-review dead ends in batch (auto-confirm) mode.

Before: settlement_extractor returned status=settlement_review and the chapter was
counted as failed with error=None. Now:
  - summary fact-check miss  -> regenerate summary (re-run settlement) up to SUMMARY_RETRIES,
                                then regenerate chapter with an explicit instruction up to CHAPTER_RETRIES
  - QG false after rollback  -> regenerate chapter up to CHAPTER_RETRIES
  - anything else / exhausted -> fail with an explicit error reason
"""
from __future__ import annotations

import os
from typing import Any

import structlog

from songyan.canon import store

logger = structlog.get_logger(__name__)

SUMMARY_RETRIES = int(os.environ.get("SONGYAN_SUMMARY_RETRIES", "2"))
CHAPTER_RETRIES = int(os.environ.get("SONGYAN_RECOVER_CHAPTER_RETRIES", "2"))

_RESET = {
    "revision_round": 0, "_best_version_id": None, "_best_overall_score": None,
    "_best_issues_count": None, "_best_report_id": None, "_best_score_card": None,
    "_quality_gate_passed": None, "_quality_gate_failures": [], "_skip_settlement": False,
    "_settlement_needs_human_review": False, "_convergence_failed": False, "error": None,
    "_canon_decision": None, "_summary_missing_facts": [],
}


def classify(state: dict[str, Any]) -> str | None:
    """Return the dead-end reason, or None when the chapter is fine (accepted)."""
    if state.get("status") == "human_review_required":
        return "qg_false_after_rollback"
    if state.get("status") != "settlement_review" and not state.get("_settlement_needs_human_review"):
        return None
    if state.get("_skip_settlement") and (state.get("_quality_gate_passed") is False
                                          or state.get("_convergence_failed")):
        # v3: convergence failed → settlement skipped (even if QG recovered a best version)
        return "qg_false_after_rollback"
    if state.get("_summary_missing_facts"):
        return "summary_missing_facts"
    if state.get("_settlement_validation_errors"):
        return "settlement_validation"
    if state.get("_startup_validation_findings"):
        return "startup_validation"
    return "settlement_review_other"


async def auto_recover_node(state: dict[str, Any]) -> dict[str, Any]:
    pid, ch = state["project_id"], state["chapter_number"]
    reason = classify(state)
    if reason is None:
        return {"_recover_action": "done"}
    detail = {
        "qg_false_after_rollback": f"质量门未通过：{state.get('_quality_gate_failures') or []}",
        "summary_missing_facts": f"摘要事实检查缺失：{state.get('_summary_missing_facts') or []}",
        "settlement_validation": f"结算校验失败：{state.get('_settlement_validation_errors') or []}",
        "startup_validation": f"开篇校验失败：{state.get('_startup_validation_findings') or []}",
    }.get(reason, "settlement 需要人工复核")
    if reason == "summary_missing_facts" and store.get_count(pid, ch, "summary") < SUMMARY_RETRIES:
        n = store.bump_count(pid, ch, "summary")
        logger.warning("auto_recover.retry_summary", project_id=pid, chapter_number=ch, attempt=n, reason=detail)
        return {"_recover_action": "retry_summary", "_summary_missing_facts": [],
                "current_version_id": state.get("_settlement_input_version_id") or state.get("current_version_id"),
                "_settlement_needs_human_review": False, "status": "settlement_extractor"}
    if reason in ("qg_false_after_rollback", "summary_missing_facts") and \
            store.get_count(pid, ch, "chapter_regen") < CHAPTER_RETRIES:
        n = store.bump_count(pid, ch, "chapter_regen")
        hint = ("本章必须让主角做出至少一个明确的、可被概括的决策或认知变化。"
                if reason == "summary_missing_facts" else "上一稿未通过质量门，请整体重写并提高完成度。")
        _, fb = store.get_feedback(pid, ch)
        store.set_feedback(pid, ch, store.get_count(pid, ch, "canon"), (fb + "\n- " + hint).strip())
        logger.warning("auto_recover.retry_chapter", project_id=pid, chapter_number=ch, attempt=n,
                       reason=reason, detail=detail)
        return {**_RESET, "_recover_action": "retry_chapter", "status": "writer"}
    err = f"auto_recover_exhausted[{reason}]: {detail}"
    logger.error("auto_recover.exhausted", project_id=pid, chapter_number=ch, reason=reason, detail=detail)
    return {"_recover_action": "error", "error": err}


def auto_recover_router(state: dict[str, Any]) -> str:
    return str(state.get("_recover_action") or "done")
