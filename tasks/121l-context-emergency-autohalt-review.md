# Task 121l: ContextEmergency AutoHalt Review

> **日期**: 2026-06-22
> **类型**: V5.1 preflight / long-run context stability
> **状态**: PARTIAL / strategy validated / new degraded-quality blocker
> **前置**: Task 121j `run-b063b6f0` 在 Ch13 后因 Ch11-Ch13 连续 3 章 ContextEmergency 触发 AutoHalt。

---

## 1. 任务边界

本任务目标是 review 并修复 Task 121j 暴露的连续 ContextEmergency 自动熔断问题，为下一次 Ch1-Ch150 full single-run 提供稳定长跑条件。

本任务聚焦：

- 复盘 `run-b063b6f0` 中 Ch8、Ch11、Ch12、Ch13 的 ContextEmergency 触发链。
- 判断 AutoHalt 条件是否过严、是否应区分“成功降级完成”和“真实上下文失控”。
- 分析 Ch11-Ch13 上下文压力来源：setting / foreshadowing / recent_plot / hard_constraints / summary 累积。
- 设计最小工程修复或配置调整，使连续成功降级不直接阻断 full-run。

不做：

- 不把 Task 121j partial 包装为 Ch1-Ch150 完成证据。
- 不修改 Ch115 quality gate / rewrite 状态逻辑。
- 不做大范围 Prompt 文风调优；正文质量问题仍归 Task 121k。

---

## 2. 事实入口

| 项 | 值 |
|----|----|
| 上一轮任务 | `tasks/121j-ch1-ch150-single-run-after-ch115-fix.md` |
| project_id | `fe44a161b8f94111800b6b0273046f32` |
| run_id | `run-b063b6f0` |
| JSONL | `logs/chapter_runs/run-b063b6f0.jsonl` |
| stdout | `logs/task121j/songyan-task121j-ch1-ch150-after-ch115-fix-20260622-113801.out.log` |
| stderr | `logs/task121j/songyan-task121j-ch1-ch150-after-ch115-fix-20260622-113801.err.log` |
| report | `logs/reports/report-run-b063b6f0.md` |

关键错误：

```text
songyan.exceptions.AutoHaltException: 连续 3 章触发 ContextEmergency（Ch11-Ch13）
```

---

## 3. 初步判断

Task 121j 的 Ch11-Ch13 均满足：

- `success=true`
- `quality_gate_passed=true`
- `settlement_success=true`
- `summary_success=true`
- `context_emergency=true`

因此这次阻断不是章节失败，而是长跑控制策略把“连续成功降级”视为必须暂停的风险信号。

需要 review 的核心问题：

- AutoHalt 是否应只在 ContextEmergency 后仍出现失败、QG false、settlement fail、summary fail 或 budget 失控时触发。
- 若 ContextEmergency 后章节完整完成，是否应改为 warning / degraded 状态并继续运行。
- 是否需要设置更高窗口，例如连续 5 章，或要求 rolling emergency ratio 超阈值。
- 是否应在 ContextEmergency 后记录更细粒度的上下文削减原因，便于判断是正常降级还是输入膨胀。

---

## 4. 执行步骤

1. 读取 `phase2_graph.py` 中 AutoHalt 规则。
2. 从 `run-b063b6f0.jsonl` 提取 Ch1-Ch13 的 `context_pressure`、`budget_used_before_emergency`、`budget_used`、`soft_refs_loaded`、`character_states_loaded`。
3. 从 stdout 抽取 Ch8、Ch11-Ch13 的 `context_manager.budget_breakdown` 和 `ContextEmergency` 降级日志。
4. 判断触发源是否来自 active setting / foreshadowing / summary / recent plot。
5. 设计并实现最小修复：
   - 优先方案：仅当连续 ContextEmergency 且存在章节失败或质量门/settlement/summary 异常时 AutoHalt。
   - 备选方案：成功降级连续出现时记录 warning，不暂停 run。
6. 补充单测覆盖：
   - 连续 3 章 ContextEmergency 但均成功时不 AutoHalt。
   - 连续 ContextEmergency 且后续章节失败时仍 AutoHalt。
7. 聚焦重跑 Ch11-Ch18 或新 clean run Ch1-Ch18，验证能越过 Ch13 和 Ch18。

---

## 5. 验收标准

- 单测覆盖 AutoHalt 新契约。
- 能解释 Ch11-Ch13 的上下文压力来源。
- 聚焦验证至少越过 Ch13，并确认 Ch18 仍能通过。
- 更新 `docs/STATUS.md`、`tasks/V5-README.md`、`README.md` 和本文状态。

---

## 6. 后续

- 若 121l 通过，重新执行 Ch1-Ch150 full single-run。
- 若聚焦验证显示 Prompt / 正文质量导致上下文膨胀，联动 Task 121k。

---

## 7. 完成记录

Task 121l 已完成代码修复、单测验证和新 clean project Ch1-Ch18 聚焦实跑。实跑结果为 **partial**：`run-08689f68` 完成 Ch1-Ch12，失败章节为 0，但 Ch12 后按新策略触发 degraded ContextEmergency AutoHalt，因此未达成 Ch1-Ch18 完整通过。

### 7.1 问题复盘

`run-b063b6f0` 中 Ch8、Ch11、Ch12、Ch13 都触发了 ContextEmergency，但章节最终均完成：

| Ch | Success | QG | Settlement | Summary | Budget Before | Budget After | Overall |
|----|---------|----|------------|---------|---------------|--------------|---------|
| 8 | true | true | true | true | 1.0628 | 0.7059 | 0.7776 |
| 11 | true | true | true | true | 1.0207 | 0.6615 | 0.8700 |
| 12 | true | true | true | true | 1.0189 | 0.6229 | 0.8433 |
| 13 | true | true | true | true | 1.0614 | 0.6927 | 0.8714 |

结论：

- 这是 BudgetHardCeiling 的合理降级路径：触发前略高于预算，降级后稳定回落到 0.62-0.71。
- Ch11-Ch13 没有 QG、settlement、summary 或章节失败。
- 原 AutoHalt 策略只看最近 3 章 `context_emergency=true`，没有区分“成功降级”和“真实失控”，因此误暂停 full-run。

### 7.2 上下文压力来源

Ch13 触发前日志显示：

```text
context_manager.budget_breakdown step=after_focal_distance budget_used=1.278 total=11557
context_manager.budget_breakdown step=after_character_prune budget_used=1.214 total=10971
context_manager.budget_breakdown step=after_partition_budgets budget_used=1.214 total=10971
context_manager.context_emergency_triggered before_tokens=9595 budget=9040 after_tokens=6262
```

主要压力项：

- `human_marks=1696`
- `recent_plot=1446`
- `foreshadowing=1089`，character prune 后仍有 559
- `open_threads=418`
- `hard_constraints=316`

Ch12/Ch13 还出现 `settlement.foreshadowing_pressure pressure=high`，说明中段上下文压力来自伏笔和近期剧情累积，而不是角色状态或 soft refs 膨胀。降级后 `soft_refs_loaded=0`、`character_states_loaded=0`，预算得分仍为 1.0。

### 7.3 修复内容

修改文件：

- `src/songyan/workflows/phase2_graph.py`
- `tests/test_phase2_graph.py`

新增策略：

- 最近 3 章均 `context_emergency=true` 且全部 `success=true`、`quality_gate_passed=true`、`settlement_success=true`、`summary_success=true`：记录 `project_pipeline.context_emergency_success_streak` warning，继续运行。
- 最近 3 章均 `context_emergency=true` 且窗口内存在章节失败、QG false、settlement fail 或 summary fail：暂停 run，并抛出 `AutoHaltException(reason="context_emergency_degraded_streak")`。
- 原连续 3 章 QG false 的熔断逻辑保持不变：`quality_gate_fail_streak`。

实现细节：

- 新增 `_append_recent_result()`，成功和失败章节都会进入最近 3 章熔断窗口。
- 新增 `_has_context_emergency_degradation()`，显式区分成功降级和真实降级。
- 新增 `_check_auto_halt_window()`，集中维护项目级熔断策略。
- `_run_single_chapter()` 成功路径向外透传 `settlement_success` / `summary_success`。
- `_run_single_chapter()` 失败路径从 `final_state["_context_metrics"]` 透传 `budget_used` / `context_emergency`，避免失败章节丢失熔断指标。

### 7.4 测试

已通过：

```powershell
python -m pytest tests/test_phase2_graph.py -q
# 16 passed

python -m pytest tests/test_phase2_graph.py tests/test_run_logger.py tests/test_119_reporting_wrapper.py -q
# 46 passed

python -m pytest tests/test_105_streaming_validation.py tests/test_phase2_graph.py -q
# 48 passed

python -m pytest tests/ -q
# 1725 passed, 1 xfailed, 1 xpassed, 14 warnings

ruff check src/songyan/workflows/phase2_graph.py tests/test_phase2_graph.py
# All checks passed!

ruff check src/ tests/
# All checks passed!
```

新增/调整测试：

- `test_pipeline_continues_on_successful_context_emergency_streak`
- `test_pipeline_halts_on_degraded_context_emergency_streak`

### 7.5 剩余验证

本轮聚焦实跑已完成，但未通过 Ch1-Ch18 出口。

- 已验证：连续 ContextEmergency 但章节成功且 QG/settlement/summary 均通过时可继续，例如 Ch11-Ch12 未因成功降级误暂停。
- 已验证：连续 ContextEmergency 伴随质量异常时会暂停，例如 Ch10-Ch12 窗口触发 `context_emergency_degraded_streak`。
- 未达成：越过 Ch13 和 Ch18。

下一步应先处理质量门/正文长度导致的 degraded emergency，再重新执行 Ch1-Ch18 聚焦实跑。通过后再创建新 `run_id` 执行 Ch1-Ch150 full single-run。

### 7.6 聚焦验证项目

已创建一个专用于 Task 121l Ch1-Ch18 实跑验证的干净项目。

| 项 | 值 |
|----|----|
| project_id | `0e131271e2f844998334d0d6398a5ad0` |
| title | `Task 121l Ch1-Ch18 ContextEmergency Focused Validation` |
| genre | `scifi` |
| mode | `webnovel_intense` |
| estimated_chapters | 18 |
| words_per_chapter | 3500 |
| target_word_count | 63000 |
| chapter_versions | 0 |
| chapter_heads | 0 |
| project_runs | 0 |
| DB integrity | `ok` |

建议运行命令：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_songyan_chapter.ps1 `
  -ProjectId '0e131271e2f844998334d0d6398a5ad0' `
  -Chapters '1-18' `
  -ModeId 'webnovel_intense' `
  -Tag 'ch1-ch18-context-emergency-focus' `
  -TaskName 'task121l' `
  -TimeoutSec 21600 `
  -BusinessDoneGraceSec 120
```

验收关注：

- 必须越过 Ch13。
- 必须越过 Ch18。
- `project_pipeline.context_emergency_success_streak` 可以出现，但不能导致 `paused`。
- 若出现 `context_emergency_degraded_streak`，需检查同一窗口内是否存在章节失败、QG false、settlement fail 或 summary fail。

### 7.7 聚焦实跑结果

运行命令：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_songyan_chapter.ps1 `
  -ProjectId '0e131271e2f844998334d0d6398a5ad0' `
  -Chapters '1-18' `
  -ModeId 'webnovel_intense' `
  -Tag 'ch1-ch18-context-emergency-focus' `
  -TaskName 'task121l' `
  -TimeoutSec 21600 `
  -BusinessDoneGraceSec 120
```

结果：

| 项 | 值 |
|----|----|
| run_id | `run-08689f68` |
| project_id | `0e131271e2f844998334d0d6398a5ad0` |
| 状态 | `paused` |
| 完成章节 | Ch1-Ch12 |
| 失败章节 | `[]` |
| heads | 12 |
| summaries | 12 |
| stdout | `logs/task121l/songyan-task121l-ch1-ch18-context-emergency-focus-20260622-151524.out.log` |
| stderr | `logs/task121l/songyan-task121l-ch1-ch18-context-emergency-focus-20260622-151524.err.log` |

暂停原因：

```text
songyan.exceptions.AutoHaltException:
连续 3 章触发 ContextEmergency 且伴随章节失败或质量异常（Ch10-Ch12）
```

关键证据：

- Ch7 触发 ContextEmergency，但 `quality_gate_passed=True`，章节成功并继续到 Ch8。
- Ch10 触发 ContextEmergency，rewrite 结构失败后回滚到 `rev-10-3-3f611a99`，`quality_gate_passed=False`，但 settlement/summary 完成。
- Ch11 触发 ContextEmergency，`quality_gate_passed=True`，章节成功并继续到 Ch12。
- Ch12 触发 ContextEmergency，rewrite 结构失败后回滚到 `rev-12-3-938d8831`，`quality_gate_passed=True`，章节成功；随后最近三章 Ch10-Ch12 构成连续 ContextEmergency 窗口，且窗口内存在 Ch10 QG false，因此按新策略暂停。

接受版本质量窗口：

| Ch | Head | Words | Overall | Budget | Length | Momentum |
|----|------|-------|---------|--------|--------|----------|
| 1 | `rev-1-2-858e7126` | 3674 | 0.9478 | 1.0000 | 1.0000 | 0.8000 |
| 2 | `v-2-4-ef242c64` | 3562 | 0.8393 | 1.0000 | 0.9600 | 0.5000 |
| 3 | `rev-3-3-97f7bbdb` | 4103 | 0.7801 | 1.0000 | 0.7200 | 0.5000 |
| 4 | `rev-4-3-8753b45c` | 3323 | 0.7853 | 0.5529 | 1.0000 | 0.5000 |
| 5 | `v-5-4-0d75dece` | 3615 | 0.8090 | 0.7196 | 0.8800 | 0.5000 |
| 6 | `v-6-4-7b82a68d` | 3591 | 0.8362 | 0.4169 | 1.0000 | 0.8000 |
| 7 | `v-7-1-eacd3806` | 4108 | 0.8185 | 1.0000 | 0.7200 | 0.5000 |
| 8 | `rev-8-3-9b1f7a4c` | 4165 | 0.7314 | 0.1806 | 0.4000 | 1.0000 |
| 9 | `v-9-4-5e948ca9` | 3732 | 0.7997 | 0.3217 | 0.7200 | 0.8000 |
| 10 | `rev-10-3-3f611a99` | 2308 | 0.7551 | 1.0000 | 0.4400 | 0.5000 |
| 11 | `v-11-4-85ecffe3` | 4194 | 0.8600 | 1.0000 | 0.6000 | 0.8000 |
| 12 | `rev-12-3-938d8831` | 3579 | 0.8085 | 1.0000 | 0.6400 | 0.5000 |

结论：

- 121l 的策略修复有效：成功降级不再误熔断，真实降级连续窗口仍会暂停。
- 本次未通过 Ch1-Ch18，是因为质量链路进入 degraded emergency，而不是因为旧策略误杀。
- 新暴露问题是中段正文长度/预算/动能不稳，以及 `quality_gate_passed=False` 版本仍可进入 settlement/summary 的放行边界。该问题应在下一轮工程/质量任务中处理，再重新跑 Ch1-Ch18。
