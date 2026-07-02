# Task 157 DONE — V6 验收判据 harness（157a）已交付；157b Ch1-Ch50 实跑待执行

> **Phase**: V6 阶段 D（长窗口验证）
> **状态**: ⚠️ 条件完成（157a 工程实现 + Layer 2 单测已收口；157b 无人值守 Ch1-Ch50 实跑因需要 >10h LLM 长跑，待后续安排资源执行）
> **完成日期**: 2026-07-02（157a）
> **事实文档**: `tasks/157-ch1-ch50-integration-validation.md`

---

## 交付概览

按 Task 157 规划，先补齐 **V6 验收判据 harness（157a）**，使 T1/T2/T6a/T6b/T6c/T6c-obs/T7 从散文/报告表格收敛为可单测、可复用的函数，供 158/159 复用；同时把 harness 输出并入 `songyan metrics`。

| 交付物 | 文件 |
|--------|------|
| V6 验收判据 harness | `src/songyan/evals/v6_acceptance.py` |
| metrics 报告追加验收段 | `src/songyan/evals/db_metrics.py`（局部导入，避免循环依赖） |
| harness Layer 2 单测 | `tests/test_157_v6_acceptance.py`（32 个用例） |

---

## 157a 实现内容

### 1. 新增 `src/songyan/evals/v6_acceptance.py`

- 阈值常量集中在模块顶部，带出处注释（`docs/v6-plan.md` §1.4 / Task 148z）：
  - T6a 斜率阈值 `3.14`（=138n 基线 6.2836×0.5）
  - T6a 归因基线 `6.2836`
  - T6c T7 基线 `1.767`
  - T6c 归因比 `0.5`
  - T6c-obs 观察上限 `15%`
- 单项判据函数：
  - `check_t1`：主线线索 `opened→advanced`/`advanced→resolved` 跃迁，且 `last_status_chapter > opened_chapter`、`last_status_version_id` 非空。
  - `check_t2`：目标区间每章 `chapter_heads.status == accepted`（当前无 `edited` 状态，只认 accepted）。
  - `check_t6a`：orphan_total 线性斜率 ≤ 阈值，样本不足返回 `None`。
  - `check_t6b`：全程每章 `orphan_critical == 0`，缺 continuity_report 的章视为未判定。
  - `check_t6c_attribution`：T7 降幅 ≥ orphan 斜率降幅 50%；orphan 斜率未下降时直接 fail。
  - `check_t6c_observation`：candidate critical 占同窗新增 critical 比例（观察项，不进入 `all_passed`）。
  - `check_t7_rate`：返回每章新 critical 速率（不独立设红线）。
  - `check_t3_t8`：复用 `detect_literary_trend.breached_dimensions`。
  - `check_t4`：复用 `compute_quality_debt`，50 章满窗，样本不足返回 `None`。
  - `check_t5`：复用 `check_t5_size_redline`/`check_t5_latency_redline`。
  - `check_health_low`：附加项 health ≥ 7.0。
- 聚合入口 `evaluate_v6_acceptance(...)` 返回三态结果：`all_passed` 只看 sufficient 项；`undecided` 列出 `passed=None` 的判据。
- 渲染函数 `render_v6_acceptance_section` 输出 markdown 表格。

### 2. `songyan metrics` 追加验收段

- `render_stage_a_metrics` 尾部通过**局部导入**调用 `evaluate_v6_acceptance` + `render_v6_acceptance_section`；历史 DB 缺表时 `_guard` 降级，不影响既有段。
- 因 `v6_acceptance.py` 已导入 `db_metrics`，顶层 import 会造成循环引用，故在函数内部局部导入。

### 3. 测试覆盖

`tests/test_157_v6_acceptance.py` 共 32 个用例，覆盖：

- T2：全 accepted 通过、缺口/未 accept 失败、无 heads 未判定。
- T6a：斜率 3.0 通过、4.0 失败、点数不足未判定。
- T6b：全 0 通过、critical>0 失败、缺报告未判定。
- T6c：归因通过、归因失败、样本不足未判定。
- T6c-obs：降级比例计算。
- T7：速率返回。
- T3/T8：无 breach 通过、有 breach 失败。
- T4：通过、degraded 破线、convergence 破线、样本不足。
- T5：通过、尺寸破线、耗时破线、样本不足。
- T1：主线 advanced 通过、无主线失败、仅 opened 失败。
- 聚合：全通过、含失败、渲染输出。
- 只读：调用前后 `setting_tracking` 行数不变。

---

## 验证结果

- `pytest tests/test_157_v6_acceptance.py -v`：32 passed。
- `ruff check src/ tests/`：通过。
- 全量 `pytest tests/ -q`：`2219 passed, 2 skipped, 1 xfailed, 2 warnings`，退出码 0。

---

## 未竟项：157b Ch1-Ch50 实跑

157b 要求：

1. 用隔离副本 DB（带大纲项目）无人值守跑 Ch1-Ch50，enforce 门禁。
2. 跑后用 157a harness 判定 T2/T6/T1/T3/T4 + health≥7.0。
3. 产出 `docs/reports/task-157-ch1-ch50-integration-validation-report.md`。

该步骤需要真实的 LLM 调用与数小时运行时间，不在本次会话执行。执行前请确认：

- 使用 `.tmp/` 外的隔离 DB 副本。
- 选择 `--on-failure isolate` 或 `--on-failure retry`（推荐 isolate，避免单章抖动白跑）。
- metrics 逐章追加到 `.tmp/task157_ch1_ch50_metrics.jsonl`。
- 跑完后用 `evaluate_v6_acceptance(project_id, 1, 50, run_id=..., run_logs=...)` 出判定。

---

## 与 158/159 的衔接

- 158/159 **必须复用**本 harness，不新增/不 fork 判据函数。
- 158 负责 T5 首次实测冻结；159 负责在 150 章规模调用并产出 N/D/S/R/V 验收报告。

---

## 参考

- `docs/v6-plan.md` §1.3/§1.4
- `tasks/148z-stage-a-threshold-calibration-DONE.md`
- `src/songyan/evals/v6_acceptance.py`
- `tests/test_157_v6_acceptance.py`
