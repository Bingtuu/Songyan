import sqlite3, json, re
from pathlib import Path
from collections import Counter

DB = Path('.tmp/task138k_ch1_ch30_rehearsal_20260629.db')
PROJECT = '3bef1af8d54d4d0e887658516e1ed350'

def load_json_field(value):
    if value is None:
        return None
    try:
        return json.loads(value)
    except Exception:
        return value

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

# ---------- Task 1: extract P1 critical orphans from Ch30 continuity report ----------
row = conn.execute(
    "SELECT orphaned_settings FROM continuity_reports WHERE project_id=? AND checked_up_to_chapter=?",
    (PROJECT, 30)
).fetchone()
orphaned = load_json_field(row['orphaned_settings']) or []
critical_orphans = [o for o in orphaned if o.get('category') == 'critical']
# sort by last_mentioned_chapter ascending (longest silent first)
critical_orphans.sort(key=lambda x: (x.get('last_mentioned_chapter', 0), x.get('setting_key', '')))
raw = {
    "count": len(critical_orphans),
    "source": "continuity_reports.orphaned_settings@Ch30",
    "note": "setting_tracking lacks priority/last_appeared_chapter; P1 critical orphans identified by category=='critical'",
    "orphans": critical_orphans,
}
Path('.tmp/138m_p1_orphans_raw.json').write_text(json.dumps(raw, ensure_ascii=False, indent=2))
print(f"Task1: {len(critical_orphans)} P1 critical orphans extracted")

# ---------- Helpers for context payloads ----------
def latest_payload(chapter_number: int):
    r = conn.execute(
        "SELECT payload FROM context_snapshots WHERE project_id=? AND chapter_number=? ORDER BY created_at DESC LIMIT 1",
        (PROJECT, chapter_number)
    ).fetchone()
    if not r:
        return None
    return load_json_field(r['payload']) or {}

# Preload all payloads ch1-30
payloads = {ch: latest_payload(ch) for ch in range(1, 31)}

def mandatory_refs_for_key(key: str, after_ch: int):
    """Return list of chapter numbers > after_ch where key appears in mandatory_references."""
    hits = []
    for ch in range(after_ch + 1, 31):
        p = payloads.get(ch) or {}
        refs = p.get('mandatory_references') or []
        for ref in refs:
            if ref.get('setting_key') == key:
                hits.append(ch)
                break
    return hits

def human_marks_for_key(key: str):
    rows = conn.execute(
        """SELECT mark_id, created_at_chapter, resolved_at, note, priority, severity, lifecycle_status
           FROM human_marks
           WHERE project_id=? AND target_key=? AND mark_type='setting' AND source='continuity_auditor'
           ORDER BY created_at_chapter""",
        (PROJECT, key)
    ).fetchall()
    return [dict(r) for r in rows]

def setting_tracking_row(key: str):
    r = conn.execute(
        "SELECT * FROM setting_tracking WHERE project_id=? AND setting_key=?",
        (PROJECT, key)
    ).fetchone()
    return dict(r) if r else None

# ---------- Task 2: enrich ----------
enriched = []
for o in critical_orphans:
    key = o['setting_key']
    st = setting_tracking_row(key)
    marks = human_marks_for_key(key)
    resolved = [m for m in marks if m.get('resolved_at')]
    unresolved = [m for m in marks if not m.get('resolved_at')]
    mandatory_hits = mandatory_refs_for_key(key, o.get('last_mentioned_chapter', 0))
    enriched.append({
        **o,
        "setting_tracking": {
            "status": st.get('status') if st else None,
            "category": st.get('category') if st else None,
            "recovery_required": st.get('recovery_required') if st else None,
            "introduced_in_chapter_db": st.get('introduced_in_chapter') if st else None,
            "last_mentioned_chapter_db": st.get('last_mentioned_chapter') if st else None,
        },
        "human_marks_total": len(marks),
        "human_marks_unresolved": len(unresolved),
        "human_marks_resolved": len(resolved),
        "human_marks_chapters": [m['created_at_chapter'] for m in marks],
        "human_marks_resolved_chapters": [m['created_at_chapter'] for m in resolved],
        "mandatory_reference_chapters": mandatory_hits,
        "mandatory_reference_count": len(mandatory_hits),
    })
Path('.tmp/138m_p1_orphans_enriched.json').write_text(
    json.dumps({"count": len(enriched), "orphans": enriched}, ensure_ascii=False, indent=2)
)
print(f"Task2: enriched {len(enriched)} orphans")

# ---------- Task 3: mandatory reference coverage for Top 20 ----------
top20 = sorted(enriched, key=lambda x: x.get('last_mentioned_chapter', 0))[:20]
Path('.tmp/138m_mandatory_reference_coverage.json').write_text(
    json.dumps({"sample_size": len(top20), "orphans": top20}, ensure_ascii=False, indent=2)
)
uncovered = [o for o in top20 if o['mandatory_reference_count'] == 0 and o['human_marks_total'] == 0]
print(f"Task3: top20 sample, uncovered by any mechanism: {len(uncovered)}/{len(top20)}")

# ---------- Task 5: root cause classification ----------
def label(o):
    has_hint = o['human_marks_total'] > 0
    has_unresolved_hint = o['human_marks_unresolved'] > 0
    has_resolved_hint = o['human_marks_resolved'] > 0
    has_mandatory = o['mandatory_reference_count'] > 0
    # If it was previously resolved (recycled) and is orphan again -> re-forgotten
    if has_resolved_hint:
        if has_unresolved_hint and has_mandatory:
            return "recycled_then_lost_with_current_injection"
        if has_unresolved_hint:
            return "recycled_then_lost_hinted_now"
        return "recycled_but_lost_again"
    # Never recycled
    if has_hint and has_mandatory:
        return "hinted_and_injected_but_not_used"
    if has_hint and not has_mandatory:
        return "hinted_but_not_injected"
    if not has_hint and not has_mandatory:
        return "never_recycled_or_hinted"
    if not has_hint and has_mandatory:
        return "injected_without_prior_hint"
    return "other"

for o in enriched:
    o['root_cause'] = label(o)

counts = Counter(o['root_cause'] for o in enriched)
classification = {
    "total": len(enriched),
    "counts": dict(counts.most_common()),
    "orphans": enriched,
}
Path('.tmp/138m_root_cause_classification.json').write_text(
    json.dumps(classification, ensure_ascii=False, indent=2)
)

# Summary markdown
lines = ["# 138m 根因分类摘要", "", f"Total P1 critical orphans (Ch30): {len(enriched)}", ""]
for k, v in counts.most_common():
    lines.append(f"- {k}: {v}")
lines.append("")
lines.append("## 机制覆盖统计")
covered_any = sum(1 for o in enriched if o['human_marks_total'] > 0 or o['mandatory_reference_count'] > 0)
lines.append(f"- 至少被 hint 或 mandatory_reference 覆盖过: {covered_any}/{len(enriched)}")
lines.append(f"- 完全无机制覆盖: {len(enriched)-covered_any}/{len(enriched)}")
lines.append(f"- 被 mandatory_reference 注入过: {sum(1 for o in enriched if o['mandatory_reference_count']>0)}/{len(enriched)}")
lines.append(f"- 被 continuity human_mark 提示过: {sum(1 for o in enriched if o['human_marks_total']>0)}/{len(enriched)}")
lines.append(f"- 曾经被 resolved（回收过）: {sum(1 for o in enriched if o['human_marks_resolved']>0)}/{len(enriched)}")
Path('.tmp/138m_root_cause_summary.md').write_text("\n".join(lines))
print("Task5: classification counts", counts.most_common())

# ---------- Extra: per-chapter mandatory reference load ----------
mr_load = {}
for ch in range(1, 31):
    p = payloads.get(ch) or {}
    mr_load[ch] = len(p.get('mandatory_references') or [])
Path('.tmp/138m_mandatory_refs_per_chapter.json').write_text(
    json.dumps(mr_load, ensure_ascii=False, indent=2)
)
print("MR load per chapter:", mr_load)

conn.close()
