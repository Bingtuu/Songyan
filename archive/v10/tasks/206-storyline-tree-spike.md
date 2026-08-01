# Task 206: Storyline Tree spike

> **阶段**: V10.4 结构升级 spike
> **类型**: 独立离线 report-only spike
> **状态**: ✅ 已完成；DONE: `tasks/206-storyline-tree-spike-DONE.md`
> **日期**: 2026-08-01

---

## 任务边界

本任务只验证 shadow Storyline Tree 是否能解释 Task 204/205 剩余的 open thread、长程伏笔、弧级收束与已兑现未关闭事实之间的边界。它不实现生产级 Storyline Tree，不修改 SQLite schema，不写 SQLite，不迁移历史库，不调用 LLM，不重跑 Ch200，不修改 Writer / CreativeDirector prompt，不进入自动 gate，不修改 CED / five-gate / segment audit / T9。

---

## 输入

| 输入 | 路径 | 用途 |
|------|------|------|
| Task 204 manifest | `archive/v10/artifacts/204-kg-diff-sample-manifest.json` | 样本、truth label、DB/project/run/version 溯源 |
| Task 204 report | `archive/v10/artifacts/204-kg-diff-spike-report.json` | KG diff 命中与 needs_validity_interval |
| Task 205 report | `archive/v10/artifacts/205-facttrack-validity-interval-report.json` | validity interval 解释结果与 needs_storyline_tree |
| 历史冻结 DB | `.tmp/backups/*/task_v10_*.db` | positive 样本 DB facts |
| Ch200 clean DB | `.tmp/task_v10_*_ch200.db` | negative controls |

---

## 输出

| 输出 | 路径 |
|------|------|
| 离线模块 | `src/songyan/evals/storyline_tree_spike.py` |
| 薄 CLI | `scripts/run_206_storyline_tree_spike.py` |
| JSON 报告 | `archive/v10/artifacts/206-storyline-tree-spike-report.json` |
| Markdown 报告 | `archive/v10/reports/206-storyline-tree-spike-report.md` |
| 测试 | `tests/evals/test_206_storyline_tree_spike.py` |

---

## Shadow tree schema

- `storyline_id`
- `parent_id`
- `node_type`: mainline / subplot / arc / thread / payoff
- `genre`
- `chapter_start`
- `chapter_end`
- `status`: open / active / resolved / stale / unknown
- `linked_facts`: foreshadowing_id / setting_key / human_mark_id
- `evidence`
- `confidence`
- `source_rule`
- `consumer_impact`
- `migration_cost`

---

## 决策规则

| 决策 | 规则 |
|------|------|
| `continue` | Storyline Tree 对 open thread / payoff / arc 收束有稳定解释力，negative controls 无高置信误报，可先以 derived view 落地 |
| `defer` | 有效但依赖更强 alias policy、人工标注、历史 backfill 或 validity interval 集成 |
| `reject` | 主要复刻 foreshadowing/status/summary，不能提供结构增益 |

---

## 验收标准

- [x] Task 206 任务书与 DONE 文档落盘。
- [x] Storyline Tree JSON + Markdown 报告落盘。
- [x] 复用 Task 204/205 样本，尤其覆盖 3 个 needs_storyline_tree 样本。
- [x] 每个 tree 判断都有 evidence、confidence、source_rule。
- [x] 输出 impact matrix、迁移成本表和 continue / defer / reject 决策。
- [x] 明确 report-only，不污染 CED / five-gate / segment audit / T9，不进入 hard gate。
- [x] 测试、ruff、git diff --check 通过。

---

## 失败路由

| 条件 | 路由 |
|------|------|
| Task 204/205 输入缺失或 schema 不兼容 | 失败并记录 |
| 样本 DB 缺失 | 降级为 document-truth-only，不静默跳过 |
| positive 无法解释 | 标记 unclear，不编造有效性 |
| negative control 高置信误报 | 降低采用结论 |
| 主要缺 alias / validity interval | `defer`，登记后续生产化依赖 |
| 需要改 schema / runtime / gate | 停止并拆后续任务，Task 206 不做 |
