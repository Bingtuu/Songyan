"""Authoritative canon store (add-only)."""
from __future__ import annotations

import json
import os
import re
import time
import sqlite3
from typing import Any

import structlog

from songyan.db.connection import get_db_path

logger = structlog.get_logger(__name__)

_DDL = """
CREATE TABLE IF NOT EXISTS canon_entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL, kind TEXT NOT NULL, key TEXT NOT NULL,
  value TEXT NOT NULL, chapter INTEGER NOT NULL DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(project_id, kind, key)
);
CREATE TABLE IF NOT EXISTS canon_conflicts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL, chapter INTEGER, kind TEXT, key TEXT,
  canon_value TEXT, new_value TEXT, reason TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS retry_counters (
  project_id TEXT NOT NULL, chapter INTEGER NOT NULL, kind TEXT NOT NULL,
  token TEXT NOT NULL, count INTEGER DEFAULT 0, PRIMARY KEY(project_id, chapter, kind)
);
CREATE TABLE IF NOT EXISTS canon_feedback (
  project_id TEXT NOT NULL, chapter INTEGER NOT NULL, attempts INTEGER DEFAULT 0,
  feedback TEXT DEFAULT '', PRIMARY KEY(project_id, chapter)
);
"""

# kinds whose value may legitimately change chapter to chapter (keyed per chapter)
_PER_CHAPTER_KINDS = {"end_state"}
# immutable identity fields of a character
_CHAR_FIXED = ("name", "gender", "relation")


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(get_db_path(), timeout=30)
    c.executescript(_DDL)
    return c


def get_entries(project_id: str, kind: str | None = None) -> list[dict[str, Any]]:
    with _conn() as c:
        q = "SELECT kind, key, value, chapter FROM canon_entries WHERE project_id=?"
        args: list[Any] = [project_id]
        if kind:
            q += " AND kind=?"
            args.append(kind)
        rows = c.execute(q + " ORDER BY id", args).fetchall()
    return [{"kind": k, "key": key, "chapter": ch, **json.loads(v)} for k, key, v, ch in rows]


def _norm(v: Any) -> str:
    return str(v or "").strip()


def add_facts(project_id: str, chapter: int, facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add facts; never overwrite. Returns list of conflicts (recorded + blocked)."""
    conflicts: list[dict[str, Any]] = []
    with _conn() as c:
        for f in facts:
            kind, key = f["kind"], _norm(f["key"])
            if not key:
                continue
            val = {k: v for k, v in f.items() if k not in ("kind", "key", "chapter")}
            row = c.execute(
                "SELECT value FROM canon_entries WHERE project_id=? AND kind=? AND key=?",
                (project_id, kind, key),
            ).fetchone()
            if row is None:
                # character: relation already bound to a different name → conflict
                rel_words = ("父", "母", "兄", "姐", "弟", "妹", "妻", "夫", "子", "女儿")
                if kind == "character" and any(w in key for w in rel_words) and len(key) > 3:
                    continue  # descriptive alias like “沈栖父亲”, not a proper name
                if kind == "character" and _norm(val.get("relation")) not in ("", "本人", "无", "未知"):
                    for e in get_entries(project_id, "character"):
                        if _norm(e.get("relation")) == _norm(val.get("relation")) and e["key"] != key:
                            conflicts.append({"kind": kind, "key": key, "canon": e["key"],
                                              "new": key, "reason": f"关系“{val.get('relation')}”已绑定为{e['key']}"})
                            break
                    else:
                        c.execute("INSERT INTO canon_entries(project_id,kind,key,value,chapter) VALUES(?,?,?,?,?)",
                                  (project_id, kind, key, json.dumps(val, ensure_ascii=False), chapter))
                    continue
                c.execute("INSERT INTO canon_entries(project_id,kind,key,value,chapter) VALUES(?,?,?,?,?)",
                          (project_id, kind, key, json.dumps(val, ensure_ascii=False), chapter))
                continue
            old = json.loads(row[0])
            if kind in _PER_CHAPTER_KINDS:
                continue
            fields = _CHAR_FIXED if kind == "character" else ("value",)
            merged, changed = dict(old), False
            if kind == "character" and val.get("aliases"):
                al = list(dict.fromkeys((old.get("aliases") or []) + list(val["aliases"])))
                if al != (old.get("aliases") or []):
                    merged["aliases"], changed = al, True
            for fld in fields:
                o, n = _norm(old.get(fld)), _norm(val.get(fld))
                if n and not o or (n and o in ("未知", "unknown")):
                    merged[fld] = val[fld]
                    changed = True  # filling a gap is an ADD, allowed
                elif n and o and n != o and n not in ("未知", "unknown") and not (
                    kind == "number" and not _num_differ(o, n)) and not (
                    kind == "fact" and not _fact_differ(o, n)) and not (
                    fld == "relation" and (n in o or o in n or set(re.split(r"[/、,，]", n)) & set(re.split(r"[/、,，]", o)))
                ):
                    conflicts.append({"kind": kind, "key": key, "canon": o, "new": n,
                                      "reason": f"{fld} 与 canon 冲突"})
            if changed:
                c.execute("UPDATE canon_entries SET value=? WHERE project_id=? AND kind=? AND key=?",
                          (json.dumps(merged, ensure_ascii=False), project_id, kind, key))
        for cf in conflicts:
            c.execute("INSERT INTO canon_conflicts(project_id,chapter,kind,key,canon_value,new_value,reason)"
                      " VALUES(?,?,?,?,?,?,?)", (project_id, chapter, cf["kind"], cf["key"],
                                                 cf["canon"], cf["new"], cf["reason"]))
    if conflicts:
        logger.warning("canon.conflicts_blocked", project_id=project_id, chapter=chapter, conflicts=conflicts)
    return conflicts


def seed_from_project(project_id: str) -> None:
    """Seed canon from the project's seed characters (idempotent)."""
    with _conn() as c:
        if c.execute("SELECT 1 FROM canon_entries WHERE project_id=? LIMIT 1", (project_id,)).fetchone():
            return
        rows = c.execute("SELECT name, role_type, background FROM characters WHERE project_id=?",
                         (project_id,)).fetchall()
    facts = []
    for name, role, bg in rows:
        facts.append({"kind": "character", "key": name, "name": name, "role": role,
                      "relation": "本人" if role == "protagonist" else "",
                      "gender": "未知", "note": (bg or "")[:80]})
    add_facts(project_id, 0, facts)


def get_feedback(project_id: str, chapter: int) -> tuple[int, str]:
    """(attempts in THIS process, feedback text)."""
    with _conn() as c:
        r = c.execute("SELECT feedback FROM canon_feedback WHERE project_id=? AND chapter=?",
                      (project_id, chapter)).fetchone()
    return get_count(project_id, chapter, "canon"), (r[0] if r else "")


def set_feedback(project_id: str, chapter: int, attempts: int, feedback: str) -> None:
    """Store feedback; attempts are tracked by retry_counters (kind='canon')."""
    with _conn() as c:
        c.execute("INSERT OR REPLACE INTO canon_feedback(project_id,chapter,attempts,feedback) VALUES(?,?,?,?)",
                  (project_id, chapter, attempts, feedback))
    while get_count(project_id, chapter, "canon") < attempts:
        bump_count(project_id, chapter, "canon")


def render_block(project_id: str, chapter: int) -> str:
    """Render the 'must obey' canon block for the writer prompt."""
    seed_from_project(project_id)
    # only facts established BEFORE this chapter (no leakage from later/out-of-order chapters)
    ents = [e for e in get_entries(project_id) if e["chapter"] < chapter]
    if not ents:
        return ""
    chars = [e for e in ents if e["kind"] == "character"]
    nums = [e for e in ents if e["kind"] == "number"][-20:]
    costs = [e for e in ents if e["kind"] == "cost" and e.get("persistent", True)]
    facts = [e for e in ents if e["kind"] == "fact"][-15:]
    prev = [e for e in ents if e["kind"] == "end_state" and e["chapter"] == chapter - 1]
    L = ["【CANON 硬约束 — 必须逐条遵守，优先级高于其他所有背景材料；违反将被拒稿重写】"]
    if chars:
        L.append("■ 人物（姓名/性别/与主角关系不可更改；新人物不得复用已有关系位）：")
        for e in chars:
            g = e.get("gender") or "未知"
            pron = {"男": "，代词用“他”", "女": "，代词用“她”"}.get(g, "")
            L.append(f"- {e['key']}｜性别:{g}{pron}｜关系:{e.get('relation') or '—'}｜{e.get('note', '')}")
    if prev:
        p = prev[0]
        L.append(f"■ 上一章（第{chapter-1}章）结尾状态——本章开头必须从这里接续，不得无交代地跳回之前的场景：")
        L.append(f"- 地点：{p.get('location', '')}；处境：{p.get('situation', '')}")
        for h in p.get("pending", []) or []:
            L.append(f"- 未了结事项（本章须回应或至少交代）：{h}")
    if costs:
        L.append("■ 已付出的规则代价（持续生效，本章须保持一致，相关场景应体现）：")
        L += [f"- 第{e['chapter']}章：{e['key']}" for e in costs]
    if nums:
        L.append("■ 已确立的数值（再次提及时必须一致；同章内也不得自相矛盾）：")
        L += [f"- {e['key']} = {e.get('value')}{e.get('unit', '')}" for e in nums]
    if facts:
        L.append("■ 已确立的事实/指令（不得与之矛盾）：")
        L += [f"- {e.get('statement', e['key'])}" for e in facts]
    _, fb = get_feedback(project_id, chapter)
    if fb:
        L.append("■ 上一稿因违反 CANON 被拒，务必修正：")
        L.append(fb)
    L.append("【CANON 结束】\n")
    return "\n".join(L)


# ---------------------------------------------------------------------------
# fix #5: retry budgets are scoped to one process invocation (one `songyan run`),
# so `--resume` starts with a fresh, still-bounded budget instead of zero.
PROCESS_TOKEN = f"{os.getpid()}-{time.time():.0f}"


def get_count(project_id: str, chapter: int, kind: str, token: str | None = None) -> int:
    token = token or PROCESS_TOKEN
    with _conn() as c:
        r = c.execute("SELECT token, count FROM retry_counters WHERE project_id=? AND chapter=? AND kind=?",
                      (project_id, chapter, kind)).fetchone()
    return int(r[1]) if r and r[0] == token else 0


def bump_count(project_id: str, chapter: int, kind: str, token: str | None = None) -> int:
    token = token or PROCESS_TOKEN
    n = get_count(project_id, chapter, kind, token) + 1
    with _conn() as c:
        c.execute("INSERT OR REPLACE INTO retry_counters(project_id,chapter,kind,token,count) VALUES(?,?,?,?,?)",
                  (project_id, chapter, kind, token, n))
    return n


def _num_differ(a: str, b: str) -> bool:
    from songyan.canon.structured import numbers_differ
    return numbers_differ(a, b)


def _fact_differ(a: str, b: str) -> bool:
    from songyan.canon.structured import values_disagree
    return values_disagree(a, b)
