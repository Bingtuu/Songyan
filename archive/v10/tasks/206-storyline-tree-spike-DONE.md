# Task 206 DONE: Storyline Tree spike

> **任务书**: `tasks/206-storyline-tree-spike.md`
> **状态**: ✅ 完成
> **完成时间**: 2026-08-01

---

## 结论

Task 206 已完成 Storyline Tree 的离线 shadow model spike。报告复用 Task 204/205 的 6 个 positive 样本与 3 个 Ch200 clean negative controls，基于现有 SQLite 结构化事实推导 `mainline / arc / thread / payoff / subplot` 的影子树节点。

结论为 **defer**：Storyline Tree 能解释 Task 205 标记的 open-thread 语义边界，3 个 needs_storyline_tree 样本均被覆盖，negative controls 没有高置信 stale storyline；但生产化仍需要 alias policy 与 validity interval 集成，不能在 V10 内直接接入 runtime 或 hard gate。

本任务没有写 SQLite，没有修改 schema，没有迁移历史库，没有调用 LLM，没有重跑 Ch200，没有接 `songyan report`，没有修改 Writer / CreativeDirector prompt，没有进入 gate，没有修改 CED / five-gate / segment audit / T9。

---

## 产物

| 产物 | 路径 |
|------|------|
| 离线模块 | `src/songyan/evals/storyline_tree_spike.py` |
| 薄 CLI | `scripts/run_206_storyline_tree_spike.py` |
| JSON 报告 | `archive/v10/artifacts/206-storyline-tree-spike-report.json` |
| Markdown 报告 | `archive/v10/reports/206-storyline-tree-spike-report.md` |
| 测试 | `tests/evals/test_206_storyline_tree_spike.py` |

---

## 报告摘要

| 指标 | 值 |
|------|---:|
| sample_count | 9 |
| positive_samples | 6 |
| negative_controls | 3 |
| db_backed_samples | 9 |
| needs_storyline_tree_samples | 3 |
| tree_explained | 5 |
| false_positive_count | 0 |
| still_needs_alias_policy_count | 2 |
| still_needs_validity_interval_count | 1 |
| decision | defer |

Impact matrix：

| issue_type | tree_explained | FP | reduce FN | alias | validity |
|------------|---------------:|---:|----------:|------:|---------:|
| critical_orphan | 1 | 0 | 1 | 1 | 0 |
| foreshadowing_unresolved | 3 | 0 | 3 | 0 | 0 |
| setting_tracking_missing_refresh | 1 | 0 | 1 | 1 | 0 |
| stale_continuity_report | 0 | 0 | 0 | 0 | 1 |
| negative_control | 0 | 0 | 0 | 0 | 0 |

---

## 数据模型影响

| target | 结论 |
|--------|------|
| `derived_storyline_tree_view` | 可先 report-only 派生，不需要 DB 迁移 |
| `storyline_tree_nodes` | 若生产化，可作为 additive table，迁移成本 medium |
| `storyline_fact_links` | 若生产化，可链接 foreshadowing / setting / human_mark 等事实，迁移成本 medium |

Task 206 不建议在 V10 内接入 runtime。若进入 V11+，建议先以 derived report view 方式和 Task 204/205 产物一起作为诊断 bundle，而不是直接影响 GoalPlanner / CreativeDirector / ContextManager。

---

## 边界自查

- 只读 SQLite：使用 `mode=ro` 打开 DB。
- 不改 SQLite schema。
- 不写 DB。
- 不调用 LLM。
- 不从正文自由抽取剧情树。
- 不新增 Agent / Workflow 节点。
- 不改 Writer / CreativeDirector prompt。
- 不改 CED / five-gate / segment audit / T9。
- 不把 Storyline Tree 作为 hard gate。

---

## 验证

```powershell
python scripts/run_206_storyline_tree_spike.py
python -m pytest tests/evals/test_206_storyline_tree_spike.py -q
ruff check src/songyan/evals/storyline_tree_spike.py scripts/run_206_storyline_tree_spike.py tests/evals/test_206_storyline_tree_spike.py
python -m pytest tests/ -q
ruff check src/ tests/ scripts/run_204_kg_diff_spike.py scripts/run_205_facttrack_validity_interval.py scripts/run_206_storyline_tree_spike.py
git diff --check
```

结果：

- Task 206 脚本：成功生成 JSON + Markdown 报告。
- 聚焦测试：6 passed。
- 全量 pytest：3063 passed, 2 skipped, 1 xfailed, 7 warnings；wrapper `PASS_NORMAL_EXIT`。
- ruff：All checks passed。

---

## 后续

下一步进入 **Task 207 V10 收口与归档**。Task 204/205/206 三个结构 spike 的共同结论是：

- KG diff 有定位价值；
- validity interval 能解释 DB 状态边界；
- Storyline Tree 能解释 open-thread 语义边界；
- 但生产化需要 alias policy、历史 backfill 与 derived view 策略，不应在 V10 内接入 runtime 或 hard gate。

Task 207 应负责把这些结论登记为 V10 收口事实，并决定是否路由 V11+。
