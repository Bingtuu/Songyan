# Task 138m: Critical Orphan 根因分析执行计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从 `.tmp/task138k_ch1_ch30_rehearsal_20260629.db` 中提取并分析 Ch30 的 P1 critical orphan，定位机制失效点，输出根因分类与 V5.2 边界决策报告。

**Architecture:** 纯分析任务，不改动业务代码。以 SQLite 查询为主线，结合 `context_snapshots`、`chapter_versions`、`setting_snapshots`、`human_marks`、`continuity_reports` 五张表做关联追踪；必要时阅读现有 Agent 代码确认机制边界。

**Tech Stack:** Python 3.11，aiosqlite/Pydantic 可选，SQLite 直接查询，输出 JSON/Markdown。

---

### Task 1: 提取 Ch30 P1 critical orphan 清单

**Files:**
- Read: `.tmp/task138k_ch1_ch30_rehearsal_20260629.db`
- Create: `.tmp/138m_p1_orphans_raw.json`
- Test: 无（数据提取步骤，人工校验 JSON 非空）

- [ ] **Step 1: 执行 SQL 查询并落盘**

```python
import sqlite3, json
from pathlib import Path

DB = Path(".tmp/task138k_ch1_ch30_rehearsal_20260629.db")
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
rows = conn.execute("""
    SELECT setting_key, setting_name, category, confidence, priority,
           last_appeared_chapter, status
    FROM setting_tracking
    WHERE project_id = '3bef1af8d54d4d0e887658516e1ed350'
      AND priority = 'P1'
      AND status = 'active'
    ORDER BY last_appeared_chapter, setting_key
""").fetchall()
orphans = [dict(r) for r in rows]
Path(".tmp/138m_p1_orphans_raw.json").write_text(
    json.dumps({"count": len(orphans), "orphans": orphans}, ensure_ascii=False, indent=2)
)
print(f"Extracted {len(orphans)} P1 orphans")
conn.close()
```

- [ ] **Step 2: 核对数量与报告一致**

```bash
python - <<'PY'
import json
print(json.load(open(".tmp/138m_p1_orphans_raw.json"))["count"])
PY
```

Expected: `35`

- [ ] **Step 3: Commit 数据快照（可选，若仓库跟踪 .tmp 则跳过）**

本步骤产物留在 `.tmp/`，不进入 git。

---

### Task 2: 为每个 P1 orphan 补充首次引入与生命周期信息

**Files:**
- Read: `.tmp/task138k_ch1_ch30_rehearsal_20260629.db`
- Create: `.tmp/138m_p1_orphans_enriched.json`

- [ ] **Step 1: 编写 enrichment 脚本**

```python
import sqlite3, json
from pathlib import Path

DB = Path(".tmp/task138k_ch1_ch30_rehearsal_20260629.db")
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

raw = json.loads(Path(".tmp/138m_p1_orphans_raw.json").read_text())["orphans"]

for o in raw:
    # 首次引入
    first = conn.execute("""
        SELECT MIN(chapter_number) AS ch, source_version_id
        FROM setting_snapshots
        WHERE project_id = '3bef1af8d54d4d0e887658516e1ed350'
          AND setting_key = ?
    """, (o["setting_key"],)).fetchone()
    o["first_chapter"] = first["ch"] if first else None
    o["source_version_id"] = first["source_version_id"] if first else None

    # 是否被 recycle_hint 标记过
    hints = conn.execute("""
        SELECT COUNT(*) AS cnt, GROUP_CONCAT(DISTINCT chapter_number) AS chapters
        FROM human_marks
        WHERE project_id = '3bef1af8d54d4d0e887658516e1ed350'
          AND target_key = ?
          AND mark_type = 'continuity_recycle_hint'
    """, (o["setting_key"],)).fetchone()
    o["recycle_hint_count"] = hints["cnt"]
    o["recycle_hint_chapters"] = hints["chapters"]

    # 是否被 settings_recycled 回收过
    recycles = conn.execute("""
        SELECT COUNT(*) AS cnt
        FROM human_marks
        WHERE project_id = '3bef1af8d54d4d0e887658516e1ed350'
          AND target_key = ?
          AND mark_type = 'continuity_setting_recycled'
    """, (o["setting_key"],)).fetchone()
    o["recycled_count"] = recycles["cnt"]

Path(".tmp/138m_p1_orphans_enriched.json").write_text(
    json.dumps({"count": len(raw), "orphans": raw}, ensure_ascii=False, indent=2)
)
conn.close()
print("Enrichment done")
```

- [ ] **Step 2: 运行并检查输出**

```bash
python .tmp/enrich_138m.py
python - <<'PY'
import json
d = json.load(open(".tmp/138m_p1_orphans_enriched.json"))
print(d["count"])
print(d["orphans"][0].keys())
PY
```

Expected: 35 条记录，每条包含 `first_chapter`, `recycle_hint_count`, `recycled_count`。

---

### Task 3: 抽样检查 mandatory_references 注入覆盖

**Files:**
- Read: `.tmp/task138k_ch1_ch30_rehearsal_20260629.db`
- Create: `.tmp/138m_mandatory_reference_coverage.json`

- [ ] **Step 1: 选取 Top 20 最近未出现的 P1 orphan**

```python
import sqlite3, json
from pathlib import Path

DB = Path(".tmp/task138k_ch1_ch30_rehearsal_20260629.db")
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

orphans = json.loads(Path(".tmp/138m_p1_orphans_enriched.json").read_text())["orphans"]
top20 = sorted(orphans, key=lambda x: x["last_appeared_chapter"])[:20]

for o in top20:
    hits = []
    for ch in range(o["last_appeared_chapter"] + 1, 31):
        ctx = conn.execute("""
            SELECT context_json FROM context_snapshots
            WHERE project_id = '3bef1af8d54d4d0e887658516e1ed350'
              AND chapter_number = ?
            ORDER BY created_at DESC LIMIT 1
        """, (ch,)).fetchone()
        if ctx and o["setting_key"] in (ctx["context_json"] or ""):
            hits.append(ch)
    o["mandatory_reference_chapters_after_last_seen"] = hits
    o["mandatory_reference_count"] = len(hits)

Path(".tmp/138m_mandatory_reference_coverage.json").write_text(
    json.dumps({"sample_size": len(top20), "orphans": top20}, ensure_ascii=False, indent=2)
)
conn.close()
print("Mandatory reference coverage done")
```

- [ ] **Step 2: 统计未被任何机制覆盖的 orphan 比例**

```bash
python - <<'PY'
import json
d = json.load(open(".tmp/138m_mandatory_reference_coverage.json"))
uncovered = [o for o in d["orphans"]
             if o["mandatory_reference_count"] == 0
             and o["recycle_hint_count"] == 0
             and o["recycled_count"] == 0]
print(f" uncovered: {len(uncovered)} / {d['sample_size']}")
PY
```

---

### Task 4: 代码审查机制边界

**Files:**
- Read:
  - `src/songyan/agents/context_manager/_assemble.py`
  - `src/songyan/agents/creative_director/` 相关 prompt/实现
  - `src/songyan/agents/writer/` 工艺卡与 prompt
  - `src/songyan/agents/settlement_extractor/`
  - `src/songyan/agents/continuity_auditor/`

- [ ] **Step 1: 确认 mandatory_references 在 ContextManager 中的衰减/截断逻辑**

搜索关键词：`mandatory_references`、`hard_constraints`、`budget_used`、`focal_distance`。
记录：
- 每章最多注入多少个 mandatory reference？
- 是否按 priority 排序？
- 长程 setting 是否会因为 focal distance 变化被移除？

- [ ] **Step 2: 确认 recycle_hint 的产生与生命周期**

搜索关键词：`continuity_recycle_hint`、`recycle_hint`、`settings_recycled`。
记录：
- 谁生成 recycle_hint？（continuity_auditor？settlement？）
- hint 写入 human_marks 后是否会在后续章节被读取？
- hint 是否会过期或被清理？

- [ ] **Step 3: 确认 Writer 工艺卡对 mandatory_reference / recycle_hint 的遵循**

读取 `prompts/cards/writer/1.2.0/`（若存在）或 `_manifest.yaml` 中的相关 section。
记录：prompt 是否明确要求 Writer 在场景中复现这些引用。

---

### Task 5: 根因分类与统计

**Files:**
- Read: `.tmp/138m_p1_orphans_enriched.json`, `.tmp/138m_mandatory_reference_coverage.json`
- Create: `.tmp/138m_root_cause_classification.json`, `.tmp/138m_root_cause_summary.md`

- [ ] **Step 1: 编写分类脚本**

```python
import json
from pathlib import Path
from collections import Counter

orphans = json.loads(Path(".tmp/138m_p1_orphans_enriched.json").read_text())["orphans"]

def label(o):
    if o["recycled_count"] > 0 and o["recycle_hint_count"] == 0:
        return "recycled_but_no_further_hint"
    if o["recycle_hint_count"] > 0 and o["mandatory_reference_count"] == 0:
        return "hinted_but_not_injected"
    if o["recycle_hint_count"] > 0 and o["mandatory_reference_count"] > 0:
        return "hinted_and_injected_but_not_used"
    if o["recycle_hint_count"] == 0 and o["mandatory_reference_count"] == 0 and o["recycled_count"] == 0:
        return "never_recycled_or_hinted"
    if o["category"] in {"background", "minor"}:
        return "misclassified_priority"
    return "other"

counts = Counter(label(o) for o in orphans)
Path(".tmp/138m_root_cause_classification.json").write_text(
    json.dumps({"total": len(orphans), "counts": dict(counts),
                "orphans": [{**o, "root_cause": label(o)} for o in orphans]},
               ensure_ascii=False, indent=2)
)
print(counts)
```

- [ ] **Step 2: 生成 Markdown 摘要**

```python
import json
from pathlib import Path

c = json.loads(Path(".tmp/138m_root_cause_classification.json").read_text())
lines = ["# 138m 根因分类摘要", "", f"Total P1 orphans: {c['total']}", ""]
for k, v in c["counts"].items():
    lines.append(f"- {k}: {v}")
Path(".tmp/138m_root_cause_summary.md").write_text("\n".join(lines))
print("Summary written")
```

---

### Task 6: 评估候选策略并撰写决策报告

**Files:**
- Create: `docs/reports/task-138m-critical-orphan-root-cause-report.md`
- Modify: `tasks/138m-critical-orphan-root-cause-and-v52-boundary.md`（更新状态/进度）

- [ ] **Step 1: 填写评估矩阵**

基于 Task 5 的分类结果，对四个选项 A/B/C/D 打分（1-5）。在报告中用表格呈现：

| 维度 | A QG 阻断式 revision | B CD 预回收 | C 衰减调优 | D 接受边界 |
|---|---:|---:|---:|---:|
| 预计 P1 降幅 | x | x | x | - |
| 工程复杂度 | x | x | x | 0 |
| 架构侵入 | x | x | x | 0 |
| 副作用风险 | x | x | x | x |
| 与 V5.1 收口冲突 | x | x | x | 0 |

- [ ] **Step 2: 写出推荐方案与理由**

必须给出明确选择。如果选组合方案，说明组合顺序与触发条件。

- [ ] **Step 3: 指定下一步 Task**

若推荐需要代码改动，创建 `tasks/138n-<short-name>.md`（如 `138n-qg-mandatory-reference-revision-loop.md`），简述目标、验收标准、依赖。

---

### Task 7: 同步入口文档

**Files:**
- Modify: `docs/STATUS.md`
- Modify: `tasks/V5-README.md`
- Modify: `docs/INDEX.md`

- [ ] **Step 1: 更新 `docs/STATUS.md`**

将当前阶段改为：

```text
| 当前阶段 | **V5.2 进行中：Task 138m 已完成；Ch30 P1 critical orphan 根因分析结论为 [X]，下一步执行 Task 138n [或接受当前边界并进入 Ch50+ rehearsal]。** |
```

- [ ] **Step 2: 更新 `tasks/V5-README.md`**

在顶部当前口径与任务列表中追加 138m 完成状态、报告链接。

- [ ] **Step 3: 更新 `docs/INDEX.md`**

将 138m 行状态改为“已完成”，并追加报告文件链接。

---

## Self-Review Checklist

- [ ] Spec coverage: 是否覆盖了 138m 任务文件中的所有目标？
- [ ] Placeholder scan: 计划中没有 TBD/TODO/"implement later"。
- [ ] Type consistency: 所有输出文件字段名一致。
