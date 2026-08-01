# Task 204: KG 图 diff spike

> **阶段**: V10.4 结构升级 spike
> **类型**: 独立离线 report-only spike
> **状态**: ✅ 已完成；DONE: `tasks/204-kg-graph-diff-spike-DONE.md`
> **日期**: 2026-08-01

---

## 任务边界

本任务只验证“只读事实图快照 + 章级 diff”是否能在 V10.2 历史结构性问题样本上复现或更清晰定位问题。它不建设正式 KG 系统，不接入 `songyan report`，不调用 LLM，不重新抽取正文完整事实，不写 SQLite，不修改 Writer / CreativeDirector prompt，不进入自动 gate，不修改 CED / five-gate / segment audit / T9。

KG diff 只作为 spike 输出 `continue / defer / reject` 决策，不替代 segment audit，也不成为 hard gate。

---

## 输入

| 输入 | 路径 | 用途 |
|------|------|------|
| 样本 manifest | `tasks/204-kg-diff-sample-manifest.json` | 固定 positive / negative 样本、DB 路径、truth 来源、expected signal |
| V10 Ch200 final DB | `.tmp/task_v10_xuanhuan_ch200.db` / `.tmp/task_v10_wuxia_ch200.db` / `.tmp/task_v10_urban_ch200.db` | negative controls 与 clean 对照 |
| V10 修复冻结 DB | `.tmp/backups/*/task_v10_*.db` | positive hotspot 样本 |
| 修复 DONE 文档 | `tasks/192.*-DONE.md` / `tasks/193.*-DONE.md` / `tasks/194.*-DONE.md` | truth label 与历史原因 |
| Task 195 / 203 | `tasks/195-cross-genre-ch200-acceptance-DONE.md` / `tasks/203-excellence-report-integration-DONE.md` | V10.2 总验收与后续路由 |

正文只用于 evidence quote 校验和上下文引用；Task 204 不从正文自由抽取完整 KG。

---

## 输出

| 输出 | 路径 |
|------|------|
| 离线模块 | `src/songyan/evals/kg_diff_spike.py` |
| 薄 CLI | `scripts/run_204_kg_diff_spike.py` |
| 样本 manifest | `tasks/204-kg-diff-sample-manifest.json` |
| JSON 报告 | `tasks/204-kg-diff-spike-report.json` |
| Markdown 报告 | `docs/reports/204-kg-diff-spike-report.md` |
| 测试 | `tests/evals/test_204_kg_diff_spike.py` |

---

## Snapshot 语义

- `before_snapshot`: chapter N 之前，按 `up_to=N-1` 截断的结构化事实视图。
- `after_snapshot`: chapter N accepted 后，按 `up_to=N` 截断的结构化事实视图。
- `setting_tracking`: 使用 `introduced_in_chapter`、`last_mentioned_chapter` 与 `source_version_id` 所属章节截断，避免未来修复污染旧章节视图。
- `foreshadowings`: 保留 `status`、`lifecycle_status`、`expected_resolve_chapter`、`source_version_id`。
- `human_marks`: 保留 `created_at_chapter`、`resolved_at`、`lifecycle_status`、`version_id`、`severity`。
- `continuity_reports`: 保留 `checked_up_to_chapter`、`overall_health_score`、`created_at`；同章多报告用于 stale candidate 判断。
- 修复前 / 修复后 DB 分别构建快照，不混用。

---

## MVP Schema

- `nodes`: setting / foreshadowing / human_mark / continuity_report / chapter_version。
- `edges`: introduced_in / mentioned_in / refreshed_by / resolved_in / marked_by / reported_by / stale_after_candidate。
- `snapshots`: before_chapter / after_chapter / source_db / project_id / version_id。
- `diffs`: added / refreshed / stale_candidate / unresolved_candidate / resolved_candidate / missing_refresh_candidate。
- `evidence`: source_table / source_row_id / chapter / version_id / source_quote / detail。
- `evaluation`: truth_label / detected_by_kg_diff / covered_by_segment_audit / covered_by_ced / covered_by_human_marks / unique_gain / false_positive / confidence / decision_note。

---

## 样本口径

最小样本规模：

- 6 个 positive samples。
- 3 个 negative controls。
- 覆盖 xuanhuan / wuxia / urban 三体裁。
- DB 缺失时必须显式降级为 `document_truth_only`，不得静默跳过。

Positive 类型：

- `setting_tracking_missing_refresh`
- `critical_orphan`
- `foreshadowing_unresolved`
- `stale_continuity_report`

Negative controls：

- xuanhuan / wuxia / urban final Ch200 clean endpoint。

---

## 决策规则

| 决策 | 规则 |
|------|------|
| `continue` | 至少两个 issue_type 有稳定独有增益，negative controls 无高置信误报，且不主要依赖 validity interval / alias 后续机制 |
| `defer` | 能复现有效信号，但主要受缺 validity interval、alias、历史 DB 不完整限制；路由 Task 205 |
| `reject` | 主要复刻 segment audit / CED，或误报不可控，或无法从 DB facts 复现 truth label |

---

## 验收标准

- [x] Task 204 任务书与 DONE 文档落盘。
- [x] 样本 manifest 落盘，且每个样本有 DB / project / run / version / truth 溯源。
- [x] KG diff JSON + Markdown 报告落盘。
- [x] 至少覆盖 6 个 positive samples 与 3 个 negative controls。
- [x] 每个 KG diff 命中都有 evidence、truth label、现有工具覆盖对比和 confidence。
- [x] 输出增益矩阵与 `continue / defer / reject` 决策。
- [x] 明确只读 report-only，不污染 CED / five-gate / segment audit / T9，不进入 hard gate。
- [x] 测试、ruff、git diff --check 通过。

---

## 失败路由

| 条件 | 路由 |
|------|------|
| 必需 manifest 缺失或 schema 不兼容 | 失败并记录 |
| 样本 DB 缺失 | 降级为 `document_truth_only`，报告低置信，不静默跳过 |
| positive signal 无法复现 | 记录 unclear，不补造有效性 |
| negative control 高置信误报 | 降低采用结论，必要时 `reject` |
| 主要受缺 validity interval 影响 | 路由 Task 205 |
| 需要主线/支线结构才能判断 | 路由 Task 206 |
| 需要改 prompt / runtime / gate | 停止并拆后续任务，Task 204 不做 |
