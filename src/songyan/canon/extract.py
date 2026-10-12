"""Extract canon facts from an accepted chapter (LLM)."""
from __future__ import annotations

from typing import Any

from songyan.canon._llm import ask_json

_PROMPT = """你是小说连续性档案员。从下面第{ch}章正文中抽取可作为后续章节硬约束的事实，只输出 JSON，不要解释。
主角：{protag}

JSON 结构：
{{
 "characters":[{{"name":"全名","gender":"男/女/未知（依据正文代词）","relation":"与主角关系，如 本人/父亲/上级/同事；无则空","role":"身份，≤15字"}}],
 "numbers":[{{"key":"数值含义的简短标签（含对象与条件，如 '17号区第三坐标回声延迟偏移(实测)'）","value":"数字","unit":"单位"}}],
 "costs":[{{"key":"主角本人因规则付出的身体/精神/记忆代价（一句话，写明后果）","persistent":true}}],
 "facts":[{{"key":"短标签","statement":"后续不可违背的事实或指令，一句话"}}],
 "end_state":{{"location":"章末主角所在位置","situation":"章末处境一句话","pending":["章末未了结、下一章必须回应的事项"]}}
}}
要求：costs 只收主角本人承受的损失（如记忆缺失、肢体失去知觉），设备损坏、样本异常不算；人物包括已故/被提及者（如父亲）；numbers 只取剧情关键数值（≤10条）；facts ≤8 条。

正文：
{text}
"""


async def extract_canon(text: str, chapter: int, protagonist: str) -> list[dict[str, Any]]:
    d = await ask_json(_PROMPT.format(ch=chapter, protag=protagonist, text=text))
    facts: list[dict[str, Any]] = []
    for c in d.get("characters", []) or []:
        if c.get("name"):
            facts.append({"kind": "character", "key": c["name"], "name": c["name"],
                          "gender": c.get("gender") or "未知", "relation": c.get("relation") or "",
                          "note": c.get("role", "")})
    for n in d.get("numbers", []) or []:
        if n.get("key"):
            facts.append({"kind": "number", "key": n["key"], "value": str(n.get("value", "")),
                          "unit": n.get("unit", "")})
    for c in d.get("costs", []) or []:
        if c.get("key"):
            facts.append({"kind": "cost", "key": c["key"], "persistent": bool(c.get("persistent", True))})
    for f in d.get("facts", []) or []:
        if f.get("statement"):
            facts.append({"kind": "fact", "key": f.get("key") or f["statement"][:20],
                          "statement": f["statement"]})
    es = d.get("end_state") or {}
    if es:
        facts.append({"kind": "end_state", "key": f"ch{chapter}", "location": es.get("location", ""),
                      "situation": es.get("situation", ""), "pending": es.get("pending", [])})
    return facts
