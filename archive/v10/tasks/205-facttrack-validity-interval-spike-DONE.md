# Task 205 DONE: FactTrack validity interval spike

> **任务书**: `tasks/205-facttrack-validity-interval-spike.md`
> **状态**: ✅ 完成
> **完成时间**: 2026-08-01

---

## 结论

Task 205 已完成 FactTrack validity interval 的离线 shadow model spike。报告复用 Task 204 的 6 个 positive 样本与 3 个 Ch200 clean negative controls，基于现有 SQLite 结构化事实推导 `setting / foreshadowing / human_mark / continuity_report` 的有效期区间。

结论为 **defer**：shadow interval 能解释 Task 204 暴露的 6/6 positive 信号，3/3 negative controls 没有高置信误报；但生产化仍需要 alias policy 与 Storyline Tree 语义，才能区分“已兑现但 DB 未关闭”“真实仍开放”“命名漂移 / 同义刷新缺口”。

本任务没有修改 SQLite schema，没有写 DB，没有迁移历史库，没有调用 LLM，没有重跑 Ch200，没有接 `songyan report`，没有修改 Writer / CreativeDirector prompt，没有进入 gate，没有修改 CED / five-gate / segment audit / T9。

---

## 产物

| 产物 | 路径 |
|------|------|
| 离线模块 | `src/songyan/evals/facttrack_validity_interval.py` |
| 薄 CLI | `scripts/run_205_facttrack_validity_interval.py` |
| JSON 报告 | `archive/v10/artifacts/205-facttrack-validity-interval-report.json` |
| Markdown 报告 | `archive/v10/reports/205-facttrack-validity-interval-report.md` |
| 测试 | `tests/evals/test_205_facttrack_validity_interval.py` |

---

## 报告摘要

| 指标 | 值 |
|------|---:|
| sample_count | 9 |
| positive_samples | 6 |
| negative_controls | 3 |
| db_backed_samples | 9 |
| document_truth_only_samples | 0 |
| interval_explained | 6 |
| false_positive_count | 0 |
| needs_alias_policy_count | 2 |
| needs_storyline_tree_count | 3 |
| decision | defer |

Impact matrix：

| issue_type | explained | FP | reduce FN | alias | storyline |
|------------|----------:|---:|----------:|------:|----------:|
| critical_orphan | 1 | 0 | 1 | 1 | 0 |
| foreshadowing_unresolved | 3 | 0 | 3 | 0 | 3 |
| setting_tracking_missing_refresh | 1 | 0 | 1 | 1 | 0 |
| stale_continuity_report | 1 | 0 | 1 | 0 | 0 |
| negative_control | 0 | 0 | 0 | 0 | 0 |

---

## 数据模型影响

| target | 结论 |
|--------|------|
| `derived_fact_validity_view` | 可先 report-only 派生，不需要 DB 迁移 |
| `fact_validity_intervals` | 若生产化，可作为 additive table，迁移成本 medium |
| `foreshadowings` | 生产化需要 `resolved_chapter` / `resolved_version_id` / `resolved_reason` 才能减少文档真值依赖 |
| `setting_tracking` | alias-aware validity 可能需要 `alias_group_id` 与有效期字段 |

Task 205 不建议在 V10 内直接迁移 schema；更务实的路线是先保留 derived view / report-only，Task 206 验证 Storyline Tree 后再决定是否进入 V11+ 生产化。

---

## 边界自查

- 只读 SQLite：使用 `mode=ro` 打开 DB。
- 不改 SQLite schema。
- 不写 DB。
- 不调用 LLM。
- 不从正文自由抽取新事实。
- 不新增 Agent / Workflow 节点。
- 不改 Writer / CreativeDirector prompt。
- 不改 CED / five-gate / segment audit / T9。
- 不把 validity interval 作为 hard gate。

---

## 验证

```powershell
python scripts/run_205_facttrack_validity_interval.py
python -m pytest tests/evals/test_205_facttrack_validity_interval.py -q
ruff check src/songyan/evals/facttrack_validity_interval.py scripts/run_205_facttrack_validity_interval.py tests/evals/test_205_facttrack_validity_interval.py
python -m pytest tests/ -q
ruff check src/ tests/ scripts/run_204_kg_diff_spike.py scripts/run_205_facttrack_validity_interval.py
git diff --check
```

结果：

- Task 205 脚本：成功生成 JSON + Markdown 报告。
- 聚焦测试：7 passed。
- 全量 pytest：3063 passed, 2 skipped, 1 xfailed, 7 warnings；wrapper `PASS_NORMAL_EXIT`。
- ruff：All checks passed。

---

## 后续

下一步进入 **Task 206 Storyline Tree spike**。Task 205 已证明 validity interval 能解释 DB 状态边界，但 foreshadowing 类问题仍需要主线 / 支线结构来判断：

- 是真实仍开放的 thread；
- 还是正文已兑现但 Settlement / status 未关闭；
- 或是需要 alias / 同义策略聚合的状态漂移。

Task 206 不应回写 Ch200 主线，也不应把 Storyline Tree 接入 hard gate；仍保持 V10 结构 spike 的 report-only 纪律。
