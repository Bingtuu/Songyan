"""Verify a draft against canon: deterministic checks + LLM judge."""
from __future__ import annotations

import re
from typing import Any

from songyan.canon import store
from songyan.canon._llm import ask_json


def deterministic_checks(project_id: str, text: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    from songyan.canon.structured import alias_map

    chars = [c for c in store.get_entries(project_id, "character")]
    amap = alias_map(project_id)
    names = {c["key"] for c in chars} | set(amap)
    from songyan.canon.structured import normalize_subject

    ntext = normalize_subject(text, amap)  # 老周 → 周德望 before relation-slot matching
    # 1) relation-slot name drift: e.g. 父亲沈远 → 父亲沈拓
    for c in chars:
        rel, name = (c.get("relation") or "").strip(), c["key"]
        if not rel or rel in ("本人", "无", "未知") or len(name) < 2:
            continue
        pat = re.compile(rf"{re.escape(rel)}[^，。！？\n]{{0,6}}?({re.escape(name[0])}[\u4e00-\u9fff]{{{len(name)-1}}})")
        for m in pat.finditer(ntext):
            cand = m.group(1)
            if cand != name and cand not in names:
                out.append({"type": "name", "severity": "error", "quote": ntext[max(0, m.start()-5):m.end()+5],
                            "canon": f"{rel}={name}", "explanation": f"{rel}的名字被写成“{cand}”"})
    # 2) pronoun/gender drift for characters with known gender
    paras = [p for p in text.split("\n") if p.strip()]
    for c in chars:
        g = c.get("gender")
        if g not in ("男", "女"):
            continue
        wrong, right = ("她", "他") if g == "男" else ("他", "她")
        n_w = n_r = 0
        for p in paras:
            mine = {a for a, k in amap.items() if k == c["key"]} | {c["key"]}
            others = [o for o in names if o not in mine and amap.get(o) != c["key"] and o in p]
            if any(m in p for m in mine) and not others:
                n_w += p.count(wrong)
                n_r += p.count(right)
        if n_w >= 3 and n_w > n_r:
            out.append({"type": "gender", "severity": "error", "quote": f"{c['key']}所在段落中“{wrong}”{n_w}次/“{right}”{n_r}次",
                        "canon": f"{c['key']} 性别{g}", "explanation": "代词与 canon 性别不符"})
    return out


_J_NUM = """检查小说草稿内部的数值一致性。步骤：
1) 找出正文中所有“把两个数值关联起来”的地方：例如“X 记录过这个偏移量”“和刚才一样”“正是这个数”“与……一致/吻合/相同”“差值 Y”“修正量 Z”，以及同一对象同一条件的量在不同段落再次出现；
2) 对每一处，写出被关联的两个数值；
3) 若两数值不同（包括小数点位置不同，如 0.70 与 0.07），且正文暗示它们是同一个量，则记为违规。
只输出 JSON：
{{"pairs":[{{"quote":"原文片段≤40字","value_a":"","value_b":"","same_quantity":true}}]}}

【草稿】
{text}
"""

_J_OPEN = """判断小说本章开头是否与上一章结尾衔接。
上一章结尾：地点={loc}；处境={sit}
上一章未了结事项：{pending}

本章开头（前800字）：
{head}

规则：若本章开头主角所处的时空/处境与上一章结尾不同，且开头没有任何交代（时间跳转、如何回到某地、对未了结事项的处理），判 broken=true。有交代（哪怕一句）即 false。只输出 JSON：
{{"broken":false,"quote":"本章开头相关原文≤40字","explanation":"≤60字"}}
"""

_J_COST = """以下是主角在上一章付出的、持续生效的代价。逐条判断本章草稿中是否体现了**该代价本身的后果**（例如代价是记忆丢失，则须出现遗忘、想不起、记忆模糊等；代价是手指失去知觉，则须出现相应不便）。仅仅提到相关人物、物品或事件不算体现。只输出 JSON：
{{"items":[{{"index":1,"reflected":true,"quote":"体现处原文≤30字，无则空"}}]}}

代价：
{costs}

【草稿】
{text}
"""

_J_FACT = """以下是本书已确立的事实/指令（CANON），以及新一章草稿。只找**直接矛盾**：草稿陈述与某条 CANON 相反；或同一人物在草稿中给出的指令与其先前（CANON 或本章更早处）的指令相反且无解释。新信息、补充、推进都不算。没有就返回空列表。只输出 JSON：
{{"violations":[{{"index":0,"canon_says":"","draft_says":"","quote":"草稿原文≤40字","explanation":"≤40字"}}]}}
（index 为 CANON 编号；若是本章内部自相矛盾，index 填 0）

CANON：
{facts}

【草稿】
{text}
"""


_J_NUM_CONFIRM = """下面是从小说草稿中找出的若干“疑似数值矛盾”候选。对每个候选，阅读草稿原文判断：正文是否**明确声称**两个数是同一个量（同一对象、同一条件、同一含义），而两数实际不同？
注意：实测值与历史值的差值、不同坐标/功率下的值、逐步变化的量，都不是矛盾。真正的矛盾例如：正文说“父亲五年前就记录过这个偏移量”，但实测偏移 0.70 而父亲记录写 0.07。
只输出 JSON：{{"results":[{{"index":1,"contradiction":false,"reason":"≤40字"}}]}}

候选：
{cands}

【草稿】
{text}
"""


async def _safe(coro):  # type: ignore[no-untyped-def]
    try:
        return await coro
    except Exception as exc:  # noqa: BLE001 — verifier must not crash the pipeline
        return {"_error": str(exc)}


def is_hard_unverified(vs: list[dict[str, Any]]) -> bool:
    """A hard-gate judge (opening/struct) failed to run → cannot certify the chapter."""
    return any(v.get("type") == "verifier_error" and v.get("canon") in ("open", "struct") for v in vs)


async def llm_judge(project_id: str, chapter: int, text: str) -> list[dict[str, Any]]:
    import asyncio

    ents = [e for e in store.get_entries(project_id) if e["chapter"] < chapter]
    prev = [e for e in ents if e["kind"] == "end_state" and e["chapter"] == chapter - 1]
    costs = [e for e in ents if e["kind"] == "cost" and e["chapter"] == chapter - 1 and e.get("persistent", True)]
    facts = [e for e in ents if e["kind"] == "fact"][-25:]
    from songyan.canon.structured import structured_check

    from songyan.canon.structured import anaphora_check

    jobs = {"struct": structured_check(project_id, chapter, text), "ana": anaphora_check(text)}
    if prev:
        p = prev[0]
        jobs["open"] = ask_json(_J_OPEN.format(loc=p.get("location", ""), sit=p.get("situation", ""),
                                               pending="；".join(p.get("pending") or []) or "无",
                                               head=text[:800]), max_tokens=400)
    if costs:
        jobs["cost"] = ask_json(_J_COST.format(costs="\n".join(f"{i+1}. {c['key']}" for i, c in enumerate(costs)),
                                               text=text), max_tokens=600)
    legacy_facts = [f for f in facts if not f.get("attribute")]
    if legacy_facts:  # unstructured facts from older canon only
        facts = legacy_facts
        jobs["fact"] = ask_json(_J_FACT.format(facts="\n".join(f"{i+1}. {f.get('statement', f['key'])}" for i, f in enumerate(facts)),
                                               text=text), max_tokens=1000)
    keys = list(jobs)
    res = dict(zip(keys, await asyncio.gather(*(_safe(jobs[k]) for k in keys))))
    out: list[dict[str, Any]] = []
    def _f(x: str) -> float | None:
        m = re.search(r"[-+]?\d+(?:\.\d+)?", x)
        return float(m.group()) if m else None

    for k in ("struct", "ana"):
        if isinstance(res.get(k), list):
            out += res[k]
    o = res.get("open") or {}
    if o.get("broken") is True:
        out.append({"type": "opening", "severity": "error", "quote": o.get("quote", ""),
                    "canon": f"上一章结尾：{prev[0].get('location','')}／{prev[0].get('situation','')}",
                    "explanation": o.get("explanation", "")})
    for it in (res.get("cost") or {}).get("items", []) or []:
        i = int(it.get("index", 0) or 0)
        if it.get("reflected") is False and 1 <= i <= len(costs):
            out.append({"type": "cost", "severity": "error", "quote": "",
                        "canon": costs[i - 1]["key"], "explanation": "上一章付出的持续代价在本章完全未体现"})
    for v in (res.get("fact") or {}).get("violations", []) or []:
        i = int(v.get("index", 0) or 0)
        if v.get("canon_says") and v.get("draft_says") and v["canon_says"] != v["draft_says"] and 0 <= i <= len(facts):
            out.append({"type": "fact", "severity": "error", "quote": v.get("quote", ""),
                        "canon": (facts[i - 1].get("statement", "") if i else "本章内部") ,
                        "explanation": f"{v.get('explanation','')}（CANON:{v['canon_says']} / 草稿:{v['draft_says']}）"})
    for k, r in res.items():
        if isinstance(r, dict) and r.get("_error"):
            out.append({"type": "verifier_error", "severity": "warn", "quote": "", "canon": k, "explanation": r["_error"][:120]})
    return out


async def verify(project_id: str, chapter: int, text: str) -> list[dict[str, Any]]:
    store.seed_from_project(project_id)
    from songyan.canon.structured import decimal_slips

    vs = deterministic_checks(project_id, text) + decimal_slips(text)
    vs += await llm_judge(project_id, chapter, text)
    return vs


def errors_only(vs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [v for v in vs if v.get("severity") == "error"]


def format_feedback(vs: list[dict[str, Any]]) -> str:
    return "\n".join(f"- [{v.get('type')}] “{v.get('quote','')}” 违反：{v.get('canon','')}（{v.get('explanation','')}）"
                     for v in vs)
