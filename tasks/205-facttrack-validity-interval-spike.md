# Task 205: FactTrack validity interval spike

> **阶段**: V10.4 结构升级 spike
> **类型**: 独立离线 report-only spike
> **状态**: ✅ 已完成；DONE: `tasks/205-facttrack-validity-interval-spike-DONE.md`
> **日期**: 2026-08-01

---

## 任务边界

本任务只验证 shadow validity interval 是否能解释 Task 204 KG diff 暴露的 stale / unresolved / missing refresh 边界。它不实现生产级 FactTrack，不修改 SQLite schema，不写 SQLite，不迁移历史库，不调用 LLM，不重跑 Ch200，不修改 Writer / CreativeDirector prompt，不进入自动 gate，不修改 CED / five-gate / segment audit / T9。

---

## 输入

| 输入 | 路径 | 用途 |
|------|------|------|
| Task 204 manifest | `tasks/204-kg-diff-sample-manifest.json` | 样本、truth label、DB/project/run/version 溯源 |
| Task 204 JSON report | `tasks/204-kg-diff-spike-report.json` | KG diff 命中、gain matrix、needs_validity_interval |
| Task 204 Markdown report | `docs/reports/204-kg-diff-spike-report.md` | 人读摘要与路由 |
| 历史冻结 DB | `.tmp/backups/*/task_v10_*.db` | positive 样本 DB facts |
| Ch200 clean DB | `.tmp/task_v10_*_ch200.db` | negative control |

---

## 输出

| 输出 | 路径 |
|------|------|
| 离线模块 | `src/songyan/evals/facttrack_validity_interval.py` |
| 薄 CLI | `scripts/run_205_facttrack_validity_interval.py` |
| JSON 报告 | `tasks/205-facttrack-validity-interval-report.json` |
| Markdown 报告 | `docs/reports/205-facttrack-validity-interval-report.md` |
| 测试 | `tests/evals/test_205_facttrack_validity_interval.py` |

---

## Shadow interval schema

- `fact_id`
- `fact_type`: setting / foreshadowing / human_mark / continuity_report
- `source_table` / `source_row_id`
- `valid_from_chapter`
- `valid_to_chapter`
- `valid_status`: active / resolved / stale / superseded / unknown
- `interval_rule`: db_status / resolved_marker / same_chapter_report_order / expected_resolve / source_version_boundary / document_truth
- `confidence`
- `evidence`
- `migration_cost`
- `consumer_impact`

---

## 决策规则

| 决策 | 规则 |
|------|------|
| `continue` | interval 对至少两个 issue_type 有稳定解释力，negative controls 无高置信误报，且可先以 derived view 落地，不依赖 alias / Storyline Tree |
| `defer` | 信号有效但依赖 alias policy、历史 backfill 或 Storyline Tree |
| `reject` | 主要复刻现有 status/lifecycle 字段，无法减少 Task 204 暴露的问题 |

---

## 验收标准

- [x] Task 205 任务书与 DONE 文档落盘。
- [x] FactTrack validity interval JSON + Markdown 报告落盘。
- [x] 至少复用 Task 204 的 6 positive + 3 negative 样本。
- [x] 每个 interval 判断都有 source_table / source_row_id / chapter / confidence / evidence。
- [x] 输出 impact matrix、迁移成本表和 continue / defer / reject 决策。
- [x] 明确只读 report-only，不修改 SQLite schema，不污染 CED / five-gate / segment audit / T9，不进入 hard gate。
- [x] 测试、ruff、git diff --check 通过。

---

## 失败路由

| 条件 | 路由 |
|------|------|
| Task 204 manifest / report 缺失或 schema 不兼容 | 失败并记录 |
| 样本 DB 缺失 | 降级为 document-truth-only，不静默跳过 |
| positive 无法解释 | 标记 unclear，不编造有效性 |
| negative control 高置信误报 | 降低采用结论 |
| 主要缺 alias policy | `defer`，登记后续 alias/backfill |
| 主要缺主线/支线结构 | 路由 Task 206 Storyline Tree spike |
| 需要改 schema / runtime / gate | 停止并拆后续任务，Task 205 不做 |
