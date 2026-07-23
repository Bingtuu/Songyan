# Task 145 DONE — orphan 绝对量 + 新 critical 产生速率监控（阶段 A 度量框架）

> **Phase**: V6 阶段 A（度量同步）
> **状态**: ✅ 完成（度量框架 + orphan/T7 曲线 + `songyan metrics` 出口 + 138n 复算验证）
> **完成日期**: 2026-07-01
> **规划/设计**: `docs/v6-plan.md` §3 阶段 A；任务书 `archive/v6/tasks/145-orphan-and-critical-rate-metrics.md`

---

## 交付概览

建立 V6 阶段 A 的 **DB 支撑度量框架**（derive-on-read，可复算历史 DB），并实现 orphan 绝对量分类曲线与「每章新 critical 产生速率」（T7）曲线。146/147/148 复用同一模块与 `songyan metrics` 出口。

| 交付物 | 文件 |
|--------|------|
| 度量模块 | `src/songyan/evals/db_metrics.py`（`OrphanPoint`/`CriticalRatePoint`、`collect_orphan_metrics`、`collect_new_critical_rate`、`linear_slope`、render_* + `render_stage_a_metrics`） |
| repo 查询 | `SettingTrackingRepository.new_settings_by_chapter(project_id, start, end)`（`db/continuity_repo.py`） |
| CLI 出口 | `songyan metrics --project-id --chapters [--output]`（`cli/main.py`，DB 支撑，可 `DATABASE_URL` 覆盖指向历史库） |
| 测试 | `tests/test_145_stage_a_metrics.py`（7 用例：分类不变量 / 曲线+斜率 / 同章取最新 / T7 写入侧 / 空 / CLI 端到端） |

## 关键实现点

- **orphan 直接从 `report.orphaned_settings` 按 category 派生**（critical/recurring/other），满足不变量 `critical+recurring+other=total`；`forgotten_items` 单列。**不使用 `classify_report`**（它聚合 state_mismatches/forgotten_items，会污染 orphan 口径——review C1/S3 修正）。
- **T7 写入侧**：`setting_tracking` 按 `introduced_in_chapter` 聚合，`category='critical'` 计 new_critical；新增 `new_settings_by_chapter` GROUP BY 查询。
- **derive-on-read**：不新增逐章计数表；orphan 源自 continuity_reports、T7 源自 setting_tracking，读取时派生 → **能在早于 V6 的历史 DB 上复算**。
- **`songyan metrics`**（新命令，不动现有 `songyan report`）：渲染 orphan total/critical/recurring/other + T7 曲线 + orphan 斜率/critical 峰值/ T7 均值摘要。

## 138n 复算验证（acceptance）

历史库 `.tmp/task138n_ch1_ch30_rerun.db` 内含多个项目；真实 150 章长跑项目是 `e95a1fa3`（run-a2bed648）。命令：

```
DATABASE_URL=sqlite:///.tmp/task138n_ch1_ch30_rerun.db songyan metrics --project-id e95a1fa3 --chapters 1-150
```

还原出（真值，供 148z 标定）：
- orphan 总量线性斜率 **+6.28/章**（orphan 持续累积——正是旧 health 指标掩盖的退化）
- P1(critical) orphan 峰值 **81**（T6(b) 要求全程 =0）
- 每章新 critical 产生速率 T7 均值 **0.547**（合计 82）

> **给 148z 的注意**：138n 含多项目（`proj-001`/`p-1` 等为测试残留），标定须选 `e95a1fa3`（setting_tracking 941 行）。项目选择方式：`SELECT run_id, project_id, chapter_range_end FROM project_runs`，取 `chapter_range_end=150` 的 run。

## 验证

- `pytest tests/test_145_stage_a_metrics.py -q` → **7 passed**。
- `ruff check`（改动文件）→ **All checks passed**。
- 138n 复算命令产出四条曲线（见上）。
- 全量回归：见下方记录。

## Out of Scope（未做，属后续任务）

- 质量债（146）/文学趋势（147）/伏笔兑现（148）；阈值冻结标定报告（148z）。
- `songyan metrics` 目前只含 orphan+T7 两段；146/147/148 会向 `render_stage_a_metrics` 追加段。
