# Task 168b: 自适应门禁窗口聚合与报告出口

> **Phase**: V7 阶段 Y（enforce 可生产化）
> **优先级**: P0
> **状态**: ✅ 完成
> **父任务**: `tasks/168-adaptive-gate-data-plane.md`
> **依赖**: Task 168a（signal snapshot 事实源）

---

## Goal

基于 168a 的 `adaptive_gate_signal_snapshots` 计算窗口级 gate 输入面，并把结果暴露到 `songyan metrics`。168b 不触发 halt，不修改 `_gates.py`，只为 Task 169 提供稳定的趋势、滑窗和异常因子数据。

## 背景

已有 `_gates.py` 里部分逻辑依赖 `previous_p1_counts`、rolling median、min health score 等临时输入。Task 169 要把这些判断升级为生产可用的自适应 halt，前提是这些输入不再由 phase2 临时拼装，而是来自可审计的数据面。

168b 的关键是把“原始快照”变成“判定层可消费的窗口读模型”：

- 采样是否充分。
- 最近窗口是否相对历史基线异常。
- 质量债是否进入持续区间。
- schedule lifecycle 是否出现主动调度失效。
- context / DB 压力是否只是孤立抖动还是持续趋势。

## In Scope

- [x] 新增窗口模型：
  - `AdaptiveGateSignalWindow`
  - `AdaptiveGateTrendPoint`
  - `AdaptiveGateDataPlaneReport`
- [x] 新增聚合函数：
  - `collect_adaptive_gate_windows(project_id, start, end, run_id=None, window=5)`
  - `build_adaptive_gate_data_plane_report(project_id, start, end, run_id=None)`
- [x] 新增刷新入口：
  - `refresh_adaptive_gate_signal_snapshots(project_id, start, end, run_id=None)`
  - 可从历史 DB / 当前 run 复算，不要求重新跑章节。
- [x] 计算窗口级信号：
  - continuity：health rolling min/median、P1/P2 rolling median、orphan slope、recent delta。
  - quality debt：degraded/convergence/qg_false window ratio。
  - literary：四维度 W=5 均值、conceptual grounding 首尾窗口比。
  - cleanliness：meta/duplicate hard count、timeline observation count。
  - context/T5：context emergency rate、budget pressure、DB size max、scan latency observation/hard 来源标记。
  - schedule：active/injected/satisfied/missed/cancelled 计数、hit rate、missed rate、overdue rate。
- [x] `songyan metrics` 追加“自适应门禁数据面”段。
- [x] 报告中必须标明：
  - 只供 Task 169 判定使用。
  - 当前不改变 enforce 行为。
  - insufficient / observation 不计入 hard pass/fail。

## Out of Scope

- 不调用 `_gates.evaluate_all_gates`。
- 不生成 `gate_reasons`。
- 不写 `project_runs.final_status`。
- 不改变 AutoHalt 策略。
- 不接入主 workflow。
- 不做 T12 阈值冻结；T12 留给 Task 170。
- 不启动 Ch200。

## 推荐窗口口径

| 窗口 | 用途 | 说明 |
|------|------|------|
| W=5 | 最近短窗波动 | 对齐 T3/T10 常用短窗；用于 health/P1/schedule 最近状态 |
| W=10 | 中窗稳定性 | 对齐质量债和 context pressure 的短期趋势 |
| W=50 | 长窗质量债 | 沿用 Task 146 T4 质量债窗口 |

168b 可以先实现 W=5 的统一模型，再为质量债保留 W=50 专项字段。不要在 168b 阶段引入新的 hard threshold。

## 报告结构建议

`songyan metrics` 追加段落：

```markdown
## 自适应门禁数据面（Task 168；只供 Task 169 判定使用）

### 样本充分性
| 信号域 | present | missing | insufficient | observation |

### Continuity / Orphan 窗口
| 窗口 | health_min | health_median | P1_median | orphan_slope | orphan_delta |

### Quality Debt 窗口
| 窗口 | degraded% | convergence% | qg_false% |

### Schedule Lifecycle 窗口
| 窗口 | injected | satisfied | missed | hit_rate | missed_rate | overdue_rate |

### Context / T5 压力
| 窗口 | context_emergency% | budget_max | db_max_mb | scan_observation | scan_hard_source |
```

报告只展示趋势和样本状态，不输出“pass/fail/halt”。

## 测试要求

目标测试建议：

```powershell
python -m pytest tests/test_168b_adaptive_gate_window_reporting.py -q
```

必要覆盖：

- [x] 空 snapshot 返回空报告，不报错。
- [x] insufficient 来源不会进入窗口硬计算。
- [x] W=5 health / P1 rolling 计算正确。
- [x] orphan slope / recent delta 计算正确。
- [x] quality debt window ratio 计算正确。
- [x] schedule hit rate / missed rate / overdue rate 计算正确。
- [x] context emergency rate 与 budget max 计算正确。
- [x] `songyan metrics` 渲染段包含“只供 Task 169 判定使用”。
- [x] 不调用 `_gates.py`，不产生 halt reason。

## 验收标准

- [x] `songyan metrics --project-id <id> --chapters A-B` 能显示自适应门禁数据面。
- [x] 168b 的聚合结果只依赖 168a repository 范围读取。
- [x] 所有窗口结果可用 Pydantic 模型序列化。
- [x] 缺失数据展示为 missing/insufficient，不污染趋势。
- [x] 169 可基于窗口模型实现判定，无需直接读底层多表。
- [x] 生成 `tasks/168b-adaptive-gate-window-reporting-DONE.md`。

## 与 Task 169 的交接

168b 应给 169 留出明确消费接口：

```python
report = await build_adaptive_gate_data_plane_report(
    project_id,
    start,
    end,
    run_id=run_id,
)
```

169 只能基于 `AdaptiveGateDataPlaneReport` 判定，不应重新散读 `continuity_reports`、JSONL run log 或 schedule 表。这样可以把“数据是否可信”和“是否 halt”分开测试。
