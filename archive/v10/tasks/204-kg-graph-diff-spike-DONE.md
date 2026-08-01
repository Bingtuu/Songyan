# Task 204 DONE: KG 图 diff spike

> **任务书**: `tasks/204-kg-graph-diff-spike.md`
> **状态**: ✅ 完成
> **完成时间**: 2026-08-01

---

## 结论

Task 204 已完成只读 KG 图 diff spike。实现基于 Task 204 manifest 中固定的 6 个历史 positive 样本与 3 个 Ch200 clean negative controls，构建 `before_snapshot / after_snapshot` 事实图并输出章级 diff。

结论为 **defer**：KG diff 能在 6/6 positive 样本上高置信复现 expected signal，3 个 negative controls 未产生高置信误报；但大部分增益来自 `setting_tracking` / `foreshadowings` / `continuity_reports` 的状态关联，产品化判断仍需要 Task 205 的 validity interval / alias 策略支撑。

本任务没有写 SQLite，没有调用 LLM，没有重跑 Ch200，没有接 `songyan report`，没有修改 Writer / CreativeDirector prompt，没有进入 gate，没有修改 CED / five-gate / segment audit / T9。

---

## 产物

| 产物 | 路径 |
|------|------|
| 离线模块 | `src/songyan/evals/kg_diff_spike.py` |
| 薄 CLI | `scripts/run_204_kg_diff_spike.py` |
| 样本 manifest | `archive/v10/artifacts/204-kg-diff-sample-manifest.json` |
| JSON 报告 | `archive/v10/artifacts/204-kg-diff-spike-report.json` |
| Markdown 报告 | `archive/v10/reports/204-kg-diff-spike-report.md` |
| 测试 | `tests/evals/test_204_kg_diff_spike.py` |

---

## 样本与真值

| 类型 | 数量 | 说明 |
|------|-----:|------|
| positive samples | 6 | xuanhuan / wuxia / urban 历史冻结 DB 热点 |
| negative controls | 3 | 三体裁 final Ch200 clean endpoint |
| DB-backed samples | 9 | 当前工作区均可只读打开 |
| document-truth-only | 0 | 本轮无降级样本 |

Positive 覆盖：

- `foreshadowing_unresolved`
- `stale_continuity_report`
- `setting_tracking_missing_refresh`
- `critical_orphan`

---

## 报告摘要

| 指标 | 值 |
|------|---:|
| sample_count | 9 |
| positive_samples | 6 |
| negative_controls | 3 |
| high_confidence_detections | 6 |
| unique_gain_count | 6 |
| decision | defer |

Gain matrix：

| issue_type | TP | FP | unique | validity needed |
|------------|---:|---:|-------:|----------------:|
| critical_orphan | 1 | 0 | 1 | 1 |
| foreshadowing_unresolved | 3 | 0 | 3 | 3 |
| setting_tracking_missing_refresh | 1 | 0 | 1 | 1 |
| stale_continuity_report | 1 | 0 | 1 | 1 |
| negative_control | 0 | 0 | 0 | 0 |

---

## 边界自查

- 只读 SQLite：使用 `mode=ro` 打开 DB。
- DB 缺失时显式降级为 `document_truth_only`，不静默跳过。
- 不调用 LLM。
- 不从正文自由抽取完整 KG。
- 不写 SQLite。
- 不新增 Agent / Workflow 节点。
- 不改 Writer / CreativeDirector prompt。
- 不改 CED / five-gate / segment audit / T9。
- 不把 KG diff 作为 hard gate。

---

## 验证

```powershell
python scripts/run_204_kg_diff_spike.py
python -m pytest tests/evals/test_204_kg_diff_spike.py -q
ruff check src/songyan/evals/kg_diff_spike.py scripts/run_204_kg_diff_spike.py tests/evals/test_204_kg_diff_spike.py
python -m pytest tests/ -q
ruff check src/ tests/ scripts/run_204_kg_diff_spike.py
git diff --check
```

结果：

- Task 204 脚本：成功生成 JSON + Markdown 报告。
- 聚焦测试：6 passed。
- 全量 pytest：3063 passed, 2 skipped, 1 xfailed, 7 warnings；wrapper `PASS_NORMAL_EXIT`。
- ruff：All checks passed。

---

## 后续

下一步进入 **Task 205 FactTrack validity interval spike**。Task 204 的 `defer` 决策不是失败，而是说明 KG diff 已有可解释信号，但需要有效期建模来区分：

- 已兑现但 DB 仍 overdue 的伏笔；
- stale continuity report；
- alias / 命名漂移导致的 missing refresh；
- open thread 与真实未解决问题。

Storyline Tree 仍保留给 Task 206，不在 Task 204 内展开。
