"""LangGraph nodes for the canon loop (enabled with SONGYAN_CANON_LOOP=1)."""
from __future__ import annotations

import json
import os
from typing import Any

import structlog

from songyan.canon import store, verify
from songyan.canon.extract import extract_canon

logger = structlog.get_logger(__name__)

MAX_RETRIES = int(os.environ.get("SONGYAN_CANON_MAX_RETRIES", "2"))
HARD_TYPES = {"name", "gender", "opening", "number"}  # never accepted while present
_LOG = os.environ.get("SONGYAN_CANON_LOG", "")


def enabled() -> bool:
    return os.environ.get("SONGYAN_CANON_LOOP", "") == "1"


def _audit(rec: dict[str, Any]) -> None:
    if _LOG:
        with open(_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


async def _protagonist(project_id: str) -> str:
    for e in store.get_entries(project_id, "character"):
        if e.get("relation") == "本人":
            return e["key"]
    return ""


async def canon_verify_node(state: dict[str, Any]) -> dict[str, Any]:
    from songyan.workflows._helpers import load_version

    pid, ch = state["project_id"], state["chapter_number"]
    version = await load_version(state["current_version_id"])
    if version is None:
        return {}
    vs = await verify.verify(pid, ch, version.content)
    errs = verify.errors_only(vs)
    attempts, _ = store.get_feedback(pid, ch)
    rec = {"chapter": ch, "version_id": version.version_id, "attempt": attempts,
           "violations": vs, "decision": None}
    if not errs:
        store.set_feedback(pid, ch, attempts, "")
        rec["decision"] = "pass"
        _audit(rec)
        logger.info("canon_verify.pass", project_id=pid, chapter_number=ch, attempt=attempts)
        return {"_canon_decision": "pass"}
    if attempts < MAX_RETRIES:
        store.set_feedback(pid, ch, attempts + 1, verify.format_feedback(errs))
        rec["decision"] = "retry"
        _audit(rec)
        logger.warning("canon_verify.retry", project_id=pid, chapter_number=ch, attempt=attempts + 1,
                       violations=errs)
        return {"_canon_decision": "retry", "revision_round": 0, "_best_version_id": None,
                "_best_overall_score": None, "_best_issues_count": None}
    hard = [v for v in errs if v.get("type") in HARD_TYPES]
    if hard:
        rec["decision"] = "reject"
        _audit(rec)
        reason = "CANON 拒稿：" + "；".join(f"[{v['type']}] {v.get('explanation','')}" for v in hard)
        logger.error("canon_verify.reject", project_id=pid, chapter_number=ch, violations=hard)
        return {"_canon_decision": "reject", "error": reason}
    store.set_feedback(pid, ch, attempts, "")
    rec["decision"] = "pass_with_soft_warnings"
    _audit(rec)
    logger.warning("canon_verify.soft_pass", project_id=pid, chapter_number=ch, violations=errs)
    return {"_canon_decision": "pass"}


def canon_verify_router(state: dict[str, Any]) -> str:
    d = state.get("_canon_decision")
    if d == "retry":
        return "retry"
    if d == "reject" or state.get("error"):
        return "error"
    return "pass"


async def canon_update_node(state: dict[str, Any]) -> dict[str, Any]:
    """After acceptance: extract facts and ADD to canon (conflicts are blocked & recorded)."""
    from songyan.db.repository import ChapterHeadRepository
    from songyan.workflows._helpers import load_version

    pid, ch = state["project_id"], state["chapter_number"]
    head = await ChapterHeadRepository().get(pid, ch)
    if head is None or not head.accepted_version_id:
        return {}
    version = await load_version(head.accepted_version_id)
    if version is None:
        return {}
    store.seed_from_project(pid)
    try:
        facts = await extract_canon(version.content, ch, await _protagonist(pid))
    except Exception as exc:  # noqa: BLE001
        logger.warning("canon_update.extract_failed", error=str(exc), chapter_number=ch)
        return {}
    conflicts = store.add_facts(pid, ch, facts)
    _audit({"chapter": ch, "canon_update": len(facts), "conflicts": conflicts})
    logger.info("canon_update.done", project_id=pid, chapter_number=ch, facts=len(facts),
                conflicts=len(conflicts))
    return {}
