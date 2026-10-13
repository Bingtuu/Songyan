"""v3: chapter-to-chapter bridging.

1) planning layer gets the previous chapter END state, and the chapter goal gets an explicit
   bridge obligation (so the plan itself starts from the end state or transitions explicitly);
2) the opening gate accepts an explicit bridged transition (time marker + the new scene
   fulfils a pending item / continues), decided in code before the LLM judge.
"""
from __future__ import annotations

import re
from typing import Any

from songyan.canon import store

_TIME = re.compile(r"次日|第二天|翌日|隔天|一夜|整夜|昨夜|昨晚|昨天|今早|清晨|凌晨|早上|上午|天亮|"
                   r"[零〇一二两三四五六七八九十\d]{1,3}[点时](?:[零〇一二三四五六七八九十\d半]{0,3}分?)?")


def prev_end_state(project_id: str, chapter: int) -> dict[str, Any] | None:
    for e in store.get_entries(project_id, "end_state"):
        if e["chapter"] == chapter - 1:
            return e
    return None


def end_state_text(es: dict[str, Any]) -> str:
    pend = "；".join(es.get("pending") or []) or "无"
    return f"地点：{es.get('location','')}；处境：{es.get('situation','')}；未了结：{pend}"


def bridge_obligation(es: dict[str, Any]) -> str:
    return (f"【开头衔接·硬约束】上一章结束于“{es.get('location','')}”（{es.get('situation','')}）。"
            "本章开头前300字内必须从该处接续；若本章主场景不同（例如次日去执行上一章约定的任务），"
            "必须先写一两句明确过渡：时间标记（如“次日清晨六点五十”）＋如何到达/从哪里来，再进入新场景。")


def apply_to_goal(goal: Any, es: dict[str, Any]) -> Any:
    """Add the bridge obligation to a ChapterGoal-like object (idempotent)."""
    ob = list(getattr(goal, "obligations", None) or [])
    text = bridge_obligation(es)
    if not any("开头衔接" in str(o) for o in ob):
        ob.insert(0, text)
        try:
            goal.obligations = ob
        except Exception:  # noqa: BLE001 — frozen model
            goal = goal.model_copy(update={"obligations": ob})
    return goal


def _keywords(s: str) -> set[str]:
    toks = set(re.findall(r"[A-Za-z]-?\d+分?区|[\u4e00-\u9fff]{2,4}(?:区|室|局|站|口|廊|车|门)", s or ""))
    return {t for t in toks if len(t) >= 2}


def bridged_opening(es: dict[str, Any], head: str) -> bool:
    """Code decision: the opening explicitly bridges from the previous end state.
    True if (a) it re-uses the end location, or (b) it has a time-jump marker AND its scene
    matches a pending item (e.g. pending '明日七点C-7分区复测' + opening '六点五十七分…C-7分区入口')."""
    head = head[:300]
    loc = es.get("location", "") or ""
    core = re.sub(r"[外内里处旁前后附近]+$", "", loc)
    grams = {core[i:i + 4] for i in range(max(0, len(core) - 3))} if len(core) >= 4 else {core}
    if any(g and g in head for g in grams | _keywords(loc)):
        return True
    if not _TIME.search(head):
        return False
    for p in es.get("pending") or []:
        if any(k in head for k in _keywords(p)):
            return True
    return False
