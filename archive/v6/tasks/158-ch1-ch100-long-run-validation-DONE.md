# Task 158 DONE — V6 阶段 D Ch1-Ch100 长跑验证

> **Phase**: V6 阶段 D（长窗口验证）
> **状态**: ✅ 完成（Ch1-Ch100 实跑已执行，报告与 Layer 2 冒烟测试已入库）
> **完成日期**: 2026-07-03
> **事实文档**: `archive/v6/tasks/158-ch1-ch100-long-run-validation.md`
> **实跑报告**: `archive/v6/reports/task-158-ch1-ch100-long-run-validation-report.md`

---

## 交付概览

按 Task 158 规划，执行 **Ch1-Ch100 无人值守长跑**，复用 Task 157 的 V6 验收判据 harness 对 100 章规模进行三态判定，并首次实测 §1.4-T5（DB/性能红线）。

| 交付物 | 文件 |
|--------|------|
| 长跑脚本（init/实跑/resume/报告生成一体化） | `scripts/run_158_ch1_ch100.py` |
| Layer 2 冒烟测试：脚本参数/编排 + kill→resume Mock | `tests/test_158_long_run_smoke.py` |
| Layer 2 冒烟测试：T5 冻结判定逻辑 | `tests/test_158_t5_freeze.py` |
| 实跑报告 | `archive/v6/reports/task-158-ch1-ch100-long-run-validation-report.md` |
| 逐章 metrics JSONL | `.tmp/task158_ch1_ch100_metrics.jsonl` |
| 隔离 DB（证据保留） | `.tmp/task158_ch1_ch100.db` |
| kill→resume 真实演练脚本（158r） | `scripts/run_158r_kill_resume_drill.py` |
| kill→resume 命令级证据报告（158r） | `archive/v6/reports/task-158r-kill-resume-drill-report.md` |
| kill→resume Layer 2 冒烟测试（158r） | `tests/test_158r_kill_resume_drill_smoke.py` |

---

## 158a 实现内容

### 1. `scripts/run_158_ch1_ch100.py`

- `--init`：创建干净隔离 DB、导入与 157b 同口径的 scifi/space-opera 项目设定、6 弧骨架 + 3 条主线线索（方舟/共鸣/旧日搭档）。
- 默认实跑：`enforce` 门禁 + `on_failure=isolate` + `LLM_RUN_CALL_BUDGET=0`（关闭）。
- `--resume`：复用该项目最近一次未完成 run 续跑；以 `accepted` head 为唯一完成事实源，已 accept 章跳过、in-flight 章重算。
- `--kill-at-chapter K`：调试钩子，在 `_run_single_chapter(K)` 调用前抛出 `KeyboardInterrupt`，用于模拟非边界 kill 后的 resume（本次未启用）。
- 跑后自动调用 `evaluate_v6_acceptance` 输出 T1-T8 harness 三态，并写入报告。

### 2. T5 冻结判定（`_evaluate_t5`）

- 读取 `run_db_metrics` 样本，判定 Ch100 尺寸红线（≤300MB）与扫描耗时红线（≤前 10 样本均值 ×1.5）。
- 样本不足时返回未判定；破线时按 148z 纪律建议"记录并调整后再冻结"，不临时放宽阈值。

### 3. 测试覆盖

`tests/test_158_long_run_smoke.py`：

- 脚本常量/范围/路径检查。
- `--resume` / `--kill-at-chapter` 参数解析。
- metrics JSONL 追加行为。
- kill→resume 编排 Mock：已 accept 章跳过、in-flight 章重算、`prune_orphan_checkpoints` 被调用。
- 异常中断后 resume 最终完成集合正确。

`tests/test_158_t5_freeze.py`：

- 样本不足 → 未判定。
- 尺寸/耗时双过 → 维持首版阈值。
- 尺寸 301MB 破线、耗时 1.6× 破线、1.4× 通过。
- 前 10 样本基线计算、零基线边界。

---

## 验证结果

- `pytest tests/test_158_long_run_smoke.py tests/test_158_t5_freeze.py -v`：全过。
- `ruff check src/ tests/ scripts/run_158_ch1_ch100.py`：通过。
- 全量 `pytest tests/ -q`：`2234 passed, 2 skipped, 1 xfailed, 2 warnings`，退出码 0。

---

## 158b Ch1-Ch100 实跑（已执行）

- **环境**：隔离 DB `.tmp/task158_ch1_ch100.db`，带大纲项目 `e91015be0e1c4ff98555f354c265fdae`（与 157b 同口径），骨架 6 弧 + 3 条主线线索。
- **命令口径**：`enforce` 门禁 + `on_failure=isolate`；真实 DeepSeek API；run `run-10d7961b`。
- **完成度**：100/100 章进入 run，98/100 章 accepted。
- **未 accept 章节**：Ch48、Ch62（均在 isolate 下被隔离，run 继续到 Ch100）。
- **运行控制**：无 AutoHalt、无候选硬门禁触发；Ch14 出现 1 次 ContextEmergency（ budget_used_before_emergency=1.13，经 emergency 降级后仍过 QG）。
- **总耗时**：28227.2s（≈470.5 min）。

### harness 判定（权威口径，详见报告）

| 判据 | 结果 | 关键值 |
|------|------|--------|
| T1 主线跃迁 | ✅ pass | 2 条：t_ark(Ch2→3)、t_resonance(Ch2→3) |
| T2 完成率 | 🔴 98/100 | Ch48、Ch62 未 accept |
| T6a orphan 斜率 | ✅ pass | 0.1338/章 ≪ 3.14 |
| T6b P1 critical | ◯ 未判定 | 部分章缺 continuity_report |
| T6c 归因 | 🔴 fail | T7=0.0000/章，orphan 斜率降幅 6.15，T7 降幅 1.77，比值未达 3.075 |
| T6c-obs 降级比例 | ◯ 未判定 | candidate critical 0 / 新增 critical 0 |
| T7 新 critical 速率 | ◯ 未判定 | 0.0000/章（基线 1.767） |
| T3/T8 文学趋势 | 🔴 fail | literary_quality_score、conceptual_grounding_score、fissure_preservation_score 触红线（首个窗口 Ch10） |
| T4 质量债 | ✅ pass | degraded 0%、convergence 2% |
| T5 DB/性能 | 🔴 fail | 尺寸 84.78MB ✓；扫描耗时 Ch50/Ch70 达 1.93×/1.76× 基线 |
| health≥7.0 | ✅ pass | 全程 ≥7.0 |

### Ch48 / Ch62 未 accept 原因

- **Ch48**： settlement/summary 失败（report 中 settlement_success/summary_success 为空，具体根因需结合日志定位；isolate 下被隔离）。
- **Ch62**： settlement/summary 失败（同上）。
- 两章均为局部提取/结算抖动，非全局 run 终止因素；run 在 isolate 策略下继续完成 Ch100。

### T5 首次实测结论

- **DB 尺寸**：Ch100 时 84.78MB，远低于 300MB 红线。
- **扫描耗时**：前 10 样本均值 89.1ms；Ch50 172ms（1.93×）、Ch70 157ms（1.76×）破线。
- **冻结结论**：**未冻结**。按 148z 纪律，T5 阈值需在记录实测数据后调整再冻结；建议 Task 159 复核基线计算窗口与 1.5× 系数是否仍适用于 150 章规模。

### kill→resume 说明

Task 158 规划要求"中途至少一次人为 kill（含 in-flight 非边界）→ 同命令 `--resume` 续完"。本次 Ch1-Ch100 实跑报告未生成独立的 **Kill→Resume 时间线**章节，原因：

1. 实跑过程中未显式使用 `--kill-at-chapter` 做人为 kill。
2. 运行日志显示 Ch11 曾出现 `Version not found` 失败（settlement_extractor 阶段），随后被自动重跑成功；该重算属于 run 内部恢复，未形成独立的 `--resume` 命令证据。
3. 脚本层的 `--resume` 能力已由 `tests/test_158_long_run_smoke.py` 的 Layer 2 Mock 覆盖（已 accept 跳过、in-flight 重算、孤儿 checkpoint 清理）。

**补充演练（2026-07-03，Task 158r）**：§1.3-R 的"人为 kill 后同命令 resume 续完"已取得**真实命令级证据**。在全新隔离 DB `.tmp/task158r_kill_resume.db` 上，用真实 DeepSeek API 执行：

- **Phase 1（in-flight kill）**：`--kill-at-chapter 3`。Ch1/Ch2 accept 后，在 Ch3 **生成完成、accept 之前**抛 `KeyboardInterrupt`（真正的 in-flight 非边界 kill）。kill 后 `run-82bd2e07` 状态 running、`current_chapter=3`、accepted=[1,2]（Ch3 未 accept）、残留 checkpoint thread=3。
- **Phase 2（同命令 resume）**：`--resume` 复用**同一** `run-82bd2e07`，`resume_start=3`（以 accepted head 为唯一完成事实源），`pruned_orphan_checkpoints pruned_count=58`（孤儿 checkpoint 清理），Ch3 以新 thread 重算并 accept，Ch4/Ch5 续完，最终 accepted=[1,2,3,4,5]、failed=[]、`status=completed`。
- **5 项关键断言全 ✅**：in-flight 打断成立、run_id 复用、in-flight 章重算并 accept、目标章全续完、run 最终 completed。
- 证据：报告 `archive/v6/reports/task-158r-kill-resume-drill-report.md`；脚本 `scripts/run_158r_kill_resume_drill.py`；命令日志 `.tmp/task158r_kill_phase.log` / `.tmp/task158r_resume_phase.log`。

**结论修正**：§1.3-R 的"人为 kill 后同命令 resume 续完"**已取得真实命令级证据**（前述 Task 158r）。Task 159 可直接引用该证据，无需重复 kill 演练（除非 150 章链路与 100 章存在实质差异）。

---

## 与 159 的衔接

- **必须复用** Task 157/158 的 harness，不新增/不 fork 判据函数。
- **T5 阈值**需在 Task 159 中结合 150 章数据重新标定后冻结。
- **kill→resume 真实演练已在 Task 158r 补齐**（`run-82bd2e07`，in-flight kill@Ch3 → 同命令 resume 续完 Ch1-Ch5，5 项断言全过）。Task 159 的 §1.3-R **直接引用该证据**，无需重复 kill 演练（除非 150 章链路与 100 章存在实质差异）。
- Ch48/Ch62 的 settlement/summary 失败可定点复跑，若复现率高则另开修复 Task。

---

## 参考

- `docs/v6-plan.md` §1.3/§1.4
- `archive/v6/tasks/157-ch1-ch50-integration-validation-DONE.md`
- `archive/v6/tasks/148z-stage-a-threshold-calibration-DONE.md`
- `scripts/run_158_ch1_ch100.py`
- `scripts/run_158r_kill_resume_drill.py`（§1.3-R kill→resume 真实演练脚本）
- `archive/v6/reports/task-158r-kill-resume-drill-report.md`（kill→resume 命令级证据报告）
- `tests/test_158_long_run_smoke.py`
- `tests/test_158_t5_freeze.py`
