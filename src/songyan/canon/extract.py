"""Extract canon facts from an accepted chapter (LLM)."""
from __future__ import annotations

from typing import Any

from songyan.canon._llm import ask_json

_PROMPT = """你是小说连续性档案员。从下面第{ch}章正文中抽取可作为后续章节硬约束的事实，只输出 JSON，不要解释。
主角：{protag}

JSON 结构：
{{
 "characters":[{{"name":"全名","gender":"男/女/未知（依据正文代词）","relation":"与主角关系，如 本人/父亲/上级/同事；无则空","role":"身份，≤15字","aliases":["正文中对此人的其他称呼，如 老周；无则空"]}}],
 "numbers":[{{"subject":"对象（如 回声延迟偏移、数据回传进度）","condition":"条件/场合/事件（如 17号区第三坐标·低功率·实测；第二章锚钉回传·章末）","value":"数字","unit":"单位"}}],
 "costs":[{{"key":"主角本人因规则付出的身体/精神/记忆代价（一句话，写明后果）","persistent":true}}],
 "facts":[{{"subject":"主体（人/物）","attribute":"属性（如 离开十七号区的方式、撤离指令通道）","value":"值的核心词（动作/编号/状态，≤6字，如 自己走、被背、十二号、已死亡）","statement":"后续不可违背的事实或指令，一句话"}}],
 "char_end":[{{"name":"章末在场或刚离场的重要人物","whereabouts":"章末去向/位置，≤10字","manner":"如何到达/离开的核心词（自己走/被背/被抬/乘车…），≤6字"}}],
 "end_state":{{"location":"章末主角所在位置","situation":"章末处境一句话","pending":["章末未了结、下一章必须回应的事项"]}}
}}
要求：costs 只收主角本人承受的损失（如记忆缺失、肢体失去知觉），设备损坏、样本异常不算；人物包括已故/被提及者（如父亲）；numbers 只取剧情关键数值（≤10条），同一个量在章内变化（如进度从43%到100%）只记章末最终值，condition 写明“章末”；facts ≤8 条。

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
                          "note": c.get("role", ""),
                          "aliases": [a for a in (c.get("aliases") or []) if a and a != c["name"]]})
    for n in d.get("numbers", []) or []:
        subj = n.get("subject") or n.get("key")
        if subj:
            cond = n.get("condition", "")
            facts.append({"kind": "number", "key": f"{subj}|{cond}", "subject": subj, "condition": cond,
                          "value": str(n.get("value", "")), "unit": n.get("unit", "")})
    for c in d.get("costs", []) or []:
        if c.get("key"):
            facts.append({"kind": "cost", "key": c["key"], "persistent": bool(c.get("persistent", True))})
    for f in d.get("facts", []) or []:
        if f.get("statement"):
            subj, attr = f.get("subject", ""), f.get("attribute", "")
            key = f"{subj}|{attr}" if subj and attr else (f.get("key") or f["statement"][:20])
            facts.append({"kind": "fact", "key": key, "subject": subj, "attribute": attr,
                          "value": f.get("value", ""), "statement": f["statement"]})
    for ce in d.get("char_end", []) or []:
        if ce.get("name") and ce.get("manner"):
            facts.append({"kind": "fact", "key": f"{ce['name']}|第{chapter}章章末去向方式", "subject": ce["name"],
                          "attribute": f"第{chapter}章章末去向方式", "value": ce["manner"],
                          "statement": f"第{chapter}章末{ce['name']}{ce['manner']}，{ce.get('whereabouts','')}"})
    es = d.get("end_state") or {}
    if es:
        facts.append({"kind": "end_state", "key": f"ch{chapter}", "location": es.get("location", ""),
                      "situation": es.get("situation", ""), "pending": es.get("pending", [])})
    return facts
