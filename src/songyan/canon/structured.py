"""fix #4: structured canon (subject + condition + value) compared in CODE.

The LLM only *extracts and links* (which canon slot a draft statement talks about);
equality/inequality is decided here deterministically, replacing the free-form judge.
"""
from __future__ import annotations

import difflib
import re
from typing import Any

from songyan.canon import store

_CN_DIGITS = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
              "六": 6, "七": 7, "八": 8, "九": 9}


def _cn_int(s: str) -> int | None:
    if not s or any(ch not in _CN_DIGITS and ch not in "十百" for ch in s):
        return None
    total, cur = 0, 0
    for ch in s:
        if ch == "百":
            total += (cur or 1) * 100; cur = 0
        elif ch == "十":
            total += (cur or 1) * 10; cur = 0
        else:
            cur = _CN_DIGITS[ch]
    return total + cur


def parse_number(x: Any) -> float | None:
    """'0.70秒' → 0.7, '+0.07s' → 0.07, '百分之四十三' → 43, '100%' → 100, '零点零七' → 0.07."""
    s = str(x or "").strip()
    m = re.search(r"[-+]?\d+(?:\.\d+)?", s)
    if m:
        return abs(float(m.group()))
    s = s.replace("百分之", "")
    m = re.search(r"([零〇一二两三四五六七八九十百]+)(?:点([零〇一二三四五六七八九]+))?", s)
    if not m:
        return None
    ip = _cn_int(m.group(1))
    if ip is None:
        return None
    if m.group(2):
        return float(f"{ip}." + "".join(str(_CN_DIGITS[c]) for c in m.group(2)))
    return float(ip)


def _decimals(x: Any) -> int:
    m = re.search(r"\d+\.(\d+)", str(x or ""))
    if m:
        return len(m.group(1))
    m = re.search(r"点([零〇一二三四五六七八九]+)", str(x or ""))
    return len(m.group(1)) if m else 0


def numbers_differ(a: Any, b: Any) -> bool:
    """Different values, tolerant to stated precision: 3.7 == 3.72, 3 == 3.72 (约3秒); 0.70 != 0.07."""
    fa, fb = parse_number(a), parse_number(b)
    if fa is None or fb is None:
        return False
    if abs(fa - fb) <= 1e-9:
        return False
    da, db = _decimals(a), _decimals(b)
    if da == db:
        return True
    coarse, fine = (fa, fb) if da < db else (fb, fa)
    d = min(da, db)
    q = 10 ** d
    return not (abs(round(fine * q) - coarse * q) < 1e-6 or abs(int(fine * q) - coarse * q) < 1e-6)


# ---------------------------------------------------------------- mutability (v4)
_IMMUTABLE_KW = re.compile(r"日期|年份|年龄|岁|生日|出生|地址|门牌|编号|案发|死亡时间|殉职|当年|历史|档案|原始记录|笔记|身高|血型")
_MUTABLE_KW = re.compile(r"周期|读数|进度|计数|次数|数量|人数|余额|存款|价格|钱|元|时间|时刻|剩余|倒计时|温度|体温|心率|"
                         r"频率|强度|速率|速度|浓度|电量|距离|深度|高度|偏移|压力|气压|衰减|功率")
_CHANGE_KW = re.compile(r"变|升|降|涨|跌|增|减|拉长|缩短|延长|衰减|跳到|跃至|升至|降至|到了|已经|仍在|继续|从.{0,12}[到至]")


def default_mutable(subject: str, condition: str = "", proposed: Any = None) -> bool:
    """Code default by quantity type; strong immutable markers win over the LLM proposal."""
    text = f"{subject}{condition}"
    if _IMMUTABLE_KW.search(text):
        return False
    if isinstance(proposed, bool):
        return proposed
    return bool(_MUTABLE_KW.search(text))


def change_narrated(quote: str) -> bool:
    return bool(_CHANGE_KW.search(str(quote or "")))


# ---------------------------------------------------------------- aliases
def alias_map(project_id: str) -> dict[str, str]:
    """alias → canonical name. Explicit aliases from canon + 老X/小X for unique surnames."""
    chars = store.get_entries(project_id, "character")
    m: dict[str, str] = {}
    by_surname: dict[str, list[str]] = {}
    for c in chars:
        k = c["key"]
        m[k] = k
        for a in c.get("aliases") or []:
            if a:
                m[str(a)] = k
        if len(k) >= 2:
            by_surname.setdefault(k[0], []).append(k)
    for sur, ks in by_surname.items():
        if len(ks) == 1:
            for p in ("老", "小", "阿"):
                m.setdefault(p + sur, ks[0])
    return m


def normalize_subject(s: str, amap: dict[str, str]) -> str:
    s = str(s or "")
    for a in sorted(amap, key=len, reverse=True):
        if a and a in s and amap[a] != a:
            s = s.replace(a, amap[a])
    return re.sub(r"\s+", "", s)


# mutually exclusive value families (label → surface words). Compared in code.
_FAMILIES: dict[str, dict[str, tuple[str, ...]]] = {
    "manner": {"walk": ("自己走", "步行", "走出", "走进", "走回", "走"), "carried": ("被背", "背出", "背进", "背着", "背", "抬"),
               "supported": ("扶", "搀"), "vehicle": ("上车", "乘车", "接驳车", "车")},
    "alive": {"dead": ("殉职", "死亡", "已死", "牺牲", "遇难", "去世", "被吞噬"), "alive": ("活着", "幸存", "生还", "失踪")},
    "open": {"open": ("开启", "打开", "开着"), "closed": ("关闭", "封闭", "锁死")},
}
_ABSENT = ("未提及", "无", "不明", "未知", "空", "未说明")


def _label(v: str) -> dict[str, str]:
    out = {}
    for fam, labels in _FAMILIES.items():
        for lab, words in labels.items():
            if any(w in v for w in words):
                out.setdefault(fam, lab)
    return out


def values_disagree(a: str, b: str) -> bool:
    """Short fact values. Disagree only when provably exclusive:
    both numeric & different (十二号 vs 七号), or same family with different labels (自己走 vs 被背)."""
    a, b = re.sub(r"[\s，。、“”\"']", "", str(a or "")), re.sub(r"[\s，。、“”\"']", "", str(b or ""))
    if not a or not b or a in b or b in a or any(x in (a, b) for x in _ABSENT):
        return False
    if parse_number(a) is not None and parse_number(b) is not None:
        res = lambda v: re.sub(r"[\d零〇一二两三四五六七八九十百.:：]", "", v)  # noqa: E731
        return res(a) == res(b) and numbers_differ(a, b)  # 十二号通道 vs 七号通道; not 07:58 vs 次日07:30
    la, lb = _label(a), _label(b)
    return any(f in lb and la[f] != lb[f] for f in la)


# ---------------------------------------------------------------- draft extraction
_J_STRUCT = """你是连续性档案员。只做“抽取与对号”，不要判断对错。只输出 JSON。

已确立的数值槽（M编号）：
{measures}

已确立的事实槽（F编号，主体｜属性＝值）：
{facts}

任务：
1) measures：列出草稿中每一个关键数值陈述（进度、偏移、时长、编号、百分比、计数等，≤20条）：
   subject=对象，condition=条件/场合，value=原文数字（照抄），quote=原文≤40字；差值、修正量、偏移量本身也要单独列为一条；
   canon_ref=若它说的就是某个 M 槽的同一个量（同对象同条件同事件），填该编号，否则空；
   same_as=若正文明确声称它与本列表中更早某条是同一个量（如“正是这个数”“早就记录过这个偏移量”“和上次一样”“吻合”），填那条的序号(从1开始)，否则 0。
   例：正文先写“差值0.70秒”，后写“笔记写着修正量+0.07s……父亲早就记录过这个偏移量”，则后一条 same_as 填前一条序号（即使数字不同——判断对错不是你的事）。
2) facts：对每个 F 槽，若草稿对同一主体同一属性给出了陈述，输出 {{"ref":"F编号","value":"草稿给出的值的核心词（动作/编号/状态，≤6字，如 自己走、被背、十二号、已死亡）","quote":"原文≤40字"}}；草稿未提及的不要输出。

{{"measures":[{{"subject":"","condition":"","value":"","quote":"","canon_ref":"","same_as":0}}],"facts":[{{"ref":"","value":"","quote":""}}]}}

【草稿】
{text}
"""


def canon_slots(project_id: str, chapter: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ents = [e for e in store.get_entries(project_id) if e["chapter"] < chapter]
    ms = [e for e in ents if e["kind"] == "number" and e.get("subject")][-30:]
    fs = [e for e in ents if e["kind"] == "fact" and e.get("subject") and e.get("attribute")][-30:]
    return ms, fs


def _same_subject(a: Any, b: Any) -> bool:
    a, b = re.sub(r"\s", "", str(a or "")), re.sub(r"\s", "", str(b or ""))
    if not a or not b:
        return False
    m = difflib.SequenceMatcher(None, a, b).find_longest_match(0, len(a), 0, len(b))
    return m.size >= max(2, min(len(a), len(b)) - 1)


def _fallback_link(measures: list[dict[str, Any]], dm: list[dict[str, Any]], chapter: int | None) -> None:
    """Code-side linking for the continuity seam: a previous chapter's END value re-stated
    in this chapter's opening (first ~25% of measures) with the same subject is the same quantity."""
    if not chapter:
        return
    ends = [(i, m) for i, m in enumerate(measures) if m["chapter"] == chapter - 1 and "章末" in (m.get("condition") or "")]
    if any("_pos" in x for x in dm):  # v4: opening = first 30% of the text (by quote position)
        cand = [x for x in dm if 0 <= x.get("_pos", 1.0) < 0.3]
    else:
        cand = dm[: max(3, len(dm) // 4)]
    for x in cand:
        if x.get("canon_ref"):
            continue
        for i, m in ends:
            subj = re.sub(r"\s", "", m.get("subject") or "")
            xs = re.sub(r"\s", "", f"{x.get('subject','')}{x.get('quote','')}")
            if len(subj) >= 2 and (subj in xs or difflib.SequenceMatcher(None, subj, x.get("subject") or "").ratio() >= 0.6):
                x["canon_ref"], x["_linked_by"] = f"M{i+1}", "code_opening_seam"
                break


_COORD = re.compile(r"北纬|南纬|东经|西经|经度|纬度|坐标")
_DIST = re.compile(r"米|公里|距离|千米")


def _qkind(x: dict[str, Any]) -> str:
    t = f"{x.get('subject','')}{x.get('value','')}"
    if _COORD.search(t):
        return "coord"
    if _DIST.search(t):
        return "dist"
    return ""


def _comparable(a: dict[str, Any], b: dict[str, Any]) -> bool:
    ka, kb = _qkind(a), _qkind(b)
    return not (ka and kb and ka != kb) and not ("coord" in (ka, kb) and ka != kb)


def compare(project_id: str, measures: list[dict[str, Any]], facts: list[dict[str, Any]],
            draft: dict[str, Any], chapter: int | None = None) -> list[dict[str, Any]]:
    """Pure code comparison of extracted draft structure against canon slots."""
    out: list[dict[str, Any]] = []
    dm = [x for x in (draft.get("measures") or []) if isinstance(x, dict)]
    _fallback_link(measures, dm, chapter)
    # a canon slot that >=3 draft numbers link to with different values is a varying family
    # (e.g. 回声延迟 at several coordinates), not one quantity → ambiguous link, drop it
    from collections import Counter
    refs = Counter(str(x.get("canon_ref") or "").upper() for x in dm if x.get("canon_ref"))
    for x in dm:
        if refs.get(str(x.get("canon_ref") or "").upper(), 0) >= 3:
            x["canon_ref"] = ""
    for i, x in enumerate(dm):
        ref = str(x.get("canon_ref") or "").strip().upper()
        if ref.startswith("M") and ref[1:].isdigit() and 1 <= int(ref[1:]) <= len(measures):
            c = measures[int(ref[1:]) - 1]
            # state quantities: a later chapter-END value of the same subject supersedes older ones
            later = [m for m in measures if m["chapter"] > c["chapter"] and "章末" in (m.get("condition") or "")
                     and (m.get("subject") or "") == (c.get("subject") or "")]
            if later:
                c = later[-1]
            # code verifies the LLM link: subjects must share a core (声源频率 ≠ 回声起始频率)
            if x.get("subject") and x.get("_linked_by") is None and not _same_subject(c.get("subject"), x["subject"]):
                pass
            elif c.get("mutable", default_mutable(c.get("subject", ""), c.get("condition", ""))) and (change_narrated(x.get("quote", "")) or not (
                    chapter and c["chapter"] == chapter - 1 and "章末" in (c.get("condition") or ""))):
                pass  # v4: mutable — narrated change, or not at the prev-chapter-end seam, is acceptable
            elif _comparable(c, x) and numbers_differ(c.get("value"), x.get("value")):
                out.append({"type": "number", "severity": "error", "quote": x.get("quote", ""),
                            "canon": f"第{c['chapter']}章 {c['subject']}｜{c.get('condition','')} = {c.get('value')}{c.get('unit','')}",
                            "explanation": f"同一个量，草稿写成 {x.get('value')}"})
        try:
            j = int(x.get("same_as") or 0)
        except (TypeError, ValueError):
            j = 0
        if 1 <= j <= len(dm) and j != i + 1 and _comparable(dm[j - 1], x) and \
                numbers_differ(dm[j - 1].get("value"), x.get("value")):
            out.append({"type": "number", "severity": "error", "quote": x.get("quote", ""),
                        "canon": f"本章：{dm[j-1].get('quote','')}",
                        "explanation": f"正文声称是同一个量，但 {dm[j-1].get('value')} ≠ {x.get('value')}"})
    for x in draft.get("facts") or []:
        if not isinstance(x, dict):
            continue
        ref = str(x.get("ref") or "").strip().upper()
        if ref.startswith("F") and ref[1:].isdigit() and 1 <= int(ref[1:]) <= len(facts):
            c = facts[int(ref[1:]) - 1]
            if x.get("quote") and values_disagree(c.get("value", ""), x.get("value", "")):
                out.append({"type": "fact", "severity": "error", "quote": x.get("quote", ""),
                            "canon": f"第{c['chapter']}章 {c['subject']}｜{c['attribute']} = {c.get('value')}",
                            "explanation": f"草稿：{x.get('value')}"})
    return out


async def structured_check(project_id: str, chapter: int, text: str) -> list[dict[str, Any]]:
    from songyan.canon._llm import ask_json

    ms, fs = canon_slots(project_id, chapter)
    prompt = _J_STRUCT.format(
        measures="\n".join(f"M{i+1}. {m['subject']}｜{m.get('condition','')}" for i, m in enumerate(ms)) or "（无）",
        facts="\n".join(f"F{i+1}. {f['subject']}｜{f['attribute']}" for i, f in enumerate(fs)) or "（无）",
        text=text)
    draft = await ask_json(prompt, max_tokens=3000)
    for x in draft.get("measures") or []:
        if isinstance(x, dict) and x.get("quote"):
            i = text.find(str(x["quote"])[:12])
            x["_pos"] = i / max(1, len(text)) if i >= 0 else 1.0
    LAST_DRAFT_EXTRACTION[(project_id, chapter)] = draft
    return compare(project_id, ms, fs, draft, chapter)


LAST_DRAFT_EXTRACTION: dict[tuple[str, int], Any] = {}


# ---------------------------------------------------------------- settlement interception
PENDING_SETTING_CONFLICTS: list[dict[str, Any]] = []  # flushed to canon_conflicts by canon_update_node


def flush_setting_conflicts(project_id: str, chapter: int) -> int:
    rows = [r for r in PENDING_SETTING_CONFLICTS if r["project_id"] == project_id]
    for r in rows:
        PENDING_SETTING_CONFLICTS.remove(r)
    if rows:
        with store._conn() as c:
            for r in rows:
                for h in r["hits"]:
                    c.execute("INSERT INTO canon_conflicts(project_id,chapter,kind,key,canon_value,new_value,reason)"
                              " VALUES(?,?,?,?,?,?,?)", (project_id, chapter, "setting_snapshot", r["setting"],
                                                         h["canon"], h["quote"], h["explanation"]))
    return len(rows)

def screen_setting(project_id: str, name: str, description: str) -> list[dict[str, Any]]:
    """Check a settlement `setting_snapshots` row against canon before it is written."""
    from songyan.canon.verify import deterministic_checks

    text = f"{name}：{description}"
    hits = [v for v in deterministic_checks(project_id, text) if v["type"] == "name"]
    amap = alias_map(project_id)
    nt = normalize_subject(text, amap)
    for m in store.get_entries(project_id, "number"):
        subj = normalize_subject(m.get("subject") or "", amap)
        cond = m.get("condition") or ""
        if len(subj) < 2 or subj not in nt or (cond and cond not in nt):
            continue
        seg = nt[nt.index(subj): nt.index(subj) + len(subj) + 30]
        nums = re.findall(r"[-+]?\d+(?:\.\d+)?%?", seg)
        if nums and all(numbers_differ(m.get("value"), n) for n in nums):
            hits.append({"type": "number", "severity": "error", "quote": seg,
                         "canon": f"{m['subject']}｜{cond} = {m.get('value')}", "explanation": "设定快照数值与 canon 冲突"})
    return hits


# ---------------------------------------------------------------- anaphoric number claims
# v3: an anaphor only counts when bound to a NAMED quantity (not bare 这个数字/一模一样)
_QTY = r"(?:偏移量?|延迟|差值|修正量|进度|百分比|读数|频率|温度|功率|衰减系数|速率)"
_ANAPHORA = re.compile(rf"(?:这个|那个|同一个|同样的){_QTY}|{_QTY}[^，。！？\n]{{0,8}}(?:一模一样|分毫不差|完全一致|完全吻合)|"
                       rf"早就记录过(?:这个|那个){_QTY}|正是这个{_QTY}")
_J_ANA = """下面每条是小说中一句“回指某个数值”的句子（如“父亲早就记录过这个偏移量”），附带它之前的上下文。
对每条，抽取两个数（照抄原文数字，不做判断）：
- referent_value：句中“这个X/同一个X”在上下文中所指的那个量，最早被测出/提出时的数值（例如前文先测得“差值0.70秒”，后面又提到“笔记写0.07秒……早就记录过这个偏移量”，则 referent_value=0.70秒）；
- asserted_value：该句或紧邻前一句声称/引用的数值（上例为 0.07秒）。没有就填空。
只输出 JSON：{{"items":[{{"index":1,"referent_value":"","asserted_value":"","quote":"≤40字"}}]}}

{items}
"""


def anaphora_sites(text: str, limit: int = 8) -> list[tuple[str, str]]:
    sites = []
    for m in _ANAPHORA.finditer(text):
        s = max(text.rfind("。", 0, m.start()), text.rfind("\n", 0, m.start())) + 1
        e = min([i for i in (text.find("。", m.end()), text.find("\n", m.end())) if i != -1] or [len(text)]) + 1
        sent = text[s:e].strip()
        ctx = text[max(0, s - 1200):s]
        if (sent, ctx) not in sites:
            sites.append((sent, ctx))
    return sites[:limit]


def compare_anaphora(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for it in items or []:
        if isinstance(it, dict) and numbers_differ(it.get("referent_value"), it.get("asserted_value")):
            out.append({"type": "number", "severity": "error", "quote": it.get("quote", ""),
                        "canon": f"前文同一个量 = {it.get('referent_value')}",
                        "explanation": f"回指句声称是同一个量，但写成 {it.get('asserted_value')}"})
    return out


async def anaphora_check(text: str) -> list[dict[str, Any]]:
    from songyan.canon._llm import ask_json

    sites = anaphora_sites(text)
    if not sites:
        return []
    items = "\n\n".join(f"[{i+1}] 上下文：…{c[-600:]}\n句子：{s}" for i, (s, c) in enumerate(sites))
    d = await ask_json(_J_ANA.format(items=items), max_tokens=1200)
    return compare_anaphora(d.get("items") or [])


_NUM_RE = re.compile(r"(?<![\d.])(\d+\.\d+|零点[零〇一二三四五六七八九]+)\s*(秒|s|Hz|赫兹|毫米|厘米|米|%|单位|度|ppm)?")
_UNIT_NORM = {"s": "秒", "赫兹": "Hz"}


def _num_units(seg: str) -> list[tuple[float, str]]:
    out = []
    for n, u in _NUM_RE.findall(seg):
        v = parse_number(n)
        if v is not None:
            out.append((v, _UNIT_NORM.get(u, u)))
    return out


def _digits(v: float) -> str:
    return re.sub(r"[^1-9]", "", f"{v:.6f}").rstrip("0")


def decimal_slips(text: str) -> list[dict[str, Any]]:
    """Deterministic: at a sentence that claims 'this is the same quantity' (anaphora),
    a cited decimal that equals an earlier decimal shifted by 10^k (0.70 ↔ 0.07)."""
    out = []
    for m in _ANAPHORA.finditer(text):
        win_s = max(0, m.start() - 120)
        local = _num_units(text[win_s:m.end()])
        earlier = _num_units(text[:win_s])
        for a, ua in local:
            for b, ub in earlier:
                # v3: same non-empty unit required (0.03单位 vs 0.3米 is not one quantity)
                if ua and ua == ub and a and b and a != b and _digits(a) == _digits(b) \
                        and abs(max(a, b) / min(a, b) - 10.0) < 1e-6:
                    out.append({"type": "number", "severity": "error", "quote": text[win_s:m.end()][-40:],
                                "canon": f"前文 {b:g}", "explanation": f"回指同一个量却写成 {a:g}（小数点错位）"})
                    break
    seen, uniq = set(), []
    for v in out:
        if v["canon"] + v["explanation"] not in seen:
            seen.add(v["canon"] + v["explanation"]); uniq.append(v)
    return uniq
