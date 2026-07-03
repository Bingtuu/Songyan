# Task 157 DONE — V6 验收判据 harness（157a）+ Ch1-Ch50 实跑（157b）均已交付

> **Phase**: V6 阶段 D（长窗口验证）
> **状态**: ✅ 完成（157a harness + Layer 2 单测已收口；157b 无人值守 Ch1-Ch50 实跑已执行，报告入库）
> **完成日期**: 2026-07-02（157a）/ 2026-07-03（157b）
> **事实文档**: `tasks/157-ch1-ch50-integration-validation.md`
> **实跑报告**: `docs/reports/task-157-ch1-ch50-integration-validation-report.md`

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

## 157b Ch1-Ch50 实跑（已执行）

- **环境**：隔离 DB `.tmp/task157_ch1_ch50.db`，带大纲项目 `806223daee344baa92cf84110258c04d`（scifi/space-opera，与 139b 基线对齐），骨架 6 弧 + 3 条主线线索（方舟/共鸣/旧日搭档）。
- **命令口径**：`enforce` 门禁 + `on_failure=isolate`；真实 DeepSeek API；run `run-e4528e8c`，总耗时约 3.7h（13276s / 50 章）。
- **脚本**：`scripts/run_157b_ch1_ch50.py`（`--init` 建库导纲 → 实跑 → 调用 `evaluate_v6_acceptance` 出三态 → 写报告）。

### harness 判定（权威口径，详见报告）

| 判据 | 结果 | 关键值 |
|------|------|--------|
| T1 主线跃迁 | ✅ pass | 2 条：t_ark(Ch1→2)、t_resonance(Ch4→5) |
| T2 完成率 | 🔴 48/50 | Ch14/Ch27 未 accept（见下） |
| T6a orphan 斜率 | ✅ pass | 0.46/章 ≪ 3.14 |
| T6b P1 critical | 实测 0（harness 标未判定） | 16 审计点 orphan_critical 全 0 |
| T6c 归因 | 🔴 fail（口径失真） | T7=0.02/章、orphan 斜率=0.46/章，均远优于基线 |
| T3/T8 文学 | ✅ pass | 无维度触红线 |
| T4 质量债 | ✅ pass | degraded 0%、convergence 2% |
| T5 DB/性能 | ✅ pass（采样） | 41.23MB、1.20×（冻结归 158） |
| health≥7.0 | ✅ pass | 全程 8.1-10.0 |

### 两项未过均非治理退化

- **Ch14**：QG 通过但 settlement 数值幻觉（`vision_left_eye` 0≠33、`right_hand_grip_strength` 50≠100）→ 被「closing_value 必须等于公式值」硬校验正确拦截 → `needs_human_review`。
- **Ch27**：正文仅 2475 字（length_score 0.42）→ QG 未过、`convergence_failed`、无 safe-best 可回滚 → 未 accept。
- **T6c**：骨架治理把新 critical 速率压到 ≈0（0.02/章），归因比值判据在退化基线下算术失真，实为"源头收敛过度达标"（T6c-obs candidate critical=0，无录入丢弃）。
- 全程 **无 AutoHalt、无候选硬门禁触发、无 ContextEmergency**；两章在 isolate 下被隔离、run 跑完 Ch50。

### 后续动作（不在本 Task 改治理，符合纪律）

1. `--resume` 定点复跑 Ch14/Ch27，判定 settlement 数值幻觉是否偶发；复现率高则另开 settlement 数值鲁棒性修复 Task。
2. 登记 **T6c 归因判据小基数失真** 为 158/159 复用前的 harness 口径校准候选。

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
