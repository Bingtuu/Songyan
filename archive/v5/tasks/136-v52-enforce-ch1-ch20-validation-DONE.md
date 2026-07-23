# Task 136: V5.2 Ch1–Ch20 采集窗口跨项目验证 — DONE

> **类型**: 实跑验证 / 证据收集  
> **日期**: 2026-06-27  
> **状态**: 已完成；本次验证 orphan 增长速率未达标，但后续 Task 138n/138o 长窗口验证已证明问题收敛  
> **报告**: `archive/v5/reports/task-136-v52-enforce-ch1-ch20-validation-report.md`

---

## 执行摘要

本次验证以 `GateConfig.for_mode("enforce")` 为配置底座实跑 Ch1–Ch20，统一验证 Task 133（Writer 多场景结构）、Task 134（SettlementExtractor 提取修复）、Task 135（设定回收与 continuity health 治理）的修复效果。

| 验证项目 ID | Run ID | 总耗时 |
|---|---:|---:|
| `a83f922d0b034db289fdbf0e63b8d8d1` | `run-21a382fe` | 5821 秒（≈1h 37m） |

复跑口径说明：

- Writer 工艺卡在验证期间由脚本临时切换为 `1.2.0`，验证结束后恢复运行前的 manifest `default_version`（当时为 `1.1.0`）。
- 普通 pipeline / CLI 默认仍读取 `prompts/cards/writer/_manifest.yaml`，当前默认 Writer 仍为 `1.1.0`；若不用本脚本或等效显式配置，无法覆盖 Task 133 的 Writer 1.2.0 修复。
- 本次为完整采集 Ch1–Ch20 指标，临时关闭 health_low 相关 halt，仅保留 ContextEmergency 门禁；因此它不是完整默认 `gate_mode="enforce"` 行为的通过证据。

---

## 验收结果

### 通过项

| 检查项 | 结果 | 说明 |
|---|---|---|
| Ch1–Ch20 完成率 | ✅ 100% | 20/20 章均完成，无 AutoHalt |
| Task 133 多场景结构 | ✅ 通过 | 多场景占比 **100%**（20/20 章 scenes_count ≥ 2） |
| Task 134 Settlement 提取 | ✅ 条件通过 | 旧报告按 settlement 成功章节为分母，记录占比 **100%**；后续复跑必须改用 Ch1–Ch20 全窗口为分母，并同时要求 summary 成功 |
| Task 135 Health floor | ✅ 通过 | Ch12/Ch15 health score 均为 3.0（≥3.0） |

### 未通过项

| 检查项 | 结果 | 说明 |
|---|---|---|
| Task 135 orphan 增长速率减半 | ❌ 未通过 | Ch9–Ch12 orphan 增长 2.667/章，Ch12–Ch15 反而上升到 4.0/章，未降至前者一半 |
| Ch15/Ch16 quality gate | ⚠️ 降级接受 | Ch15、Ch16 `quality_gate_passed=False`，以 `degraded_accept` 形式完成，settlement/summary 未执行 |

---

## 关键指标

```text
Completion rate:        100.00%
Multi-scene ratio:      100.00%
Settlement record ratio: 100.00%
Orphan rate Ch9-12:      2.667 / 章
Orphan rate Ch12-15:     4.000 / 章
Health Ch12:             3.0
Health Ch15:             3.0
Pass all criteria:       False
```

---

## 与 Task 129 基线对比（Ch1–Ch15 重叠段）

| 维度 | 基线（run-89d7a2d4） | 本轮（run-21a382fe） | 变化 |
|---|---|---|---|
| Scenes | 全部 1 | 全部 ≥2 | 显著改善 |
| Settlement | 部分失败/无记录 | 成功且有记录 | 显著改善 |
| Orphan 增速 | 快 | Ch12–Ch15 更快 | 未改善 |
| Health floor | 部分低于 3.0 | Ch12/Ch15 均 3.0 | 改善 |

---

## 结论与下一步

1. **Writer 1.2.0 多场景结构修复有效**：20 章全部满足 scenes_count ≥ 2，Task 133 目标达成；但该结论依赖脚本临时切换 Writer 1.2.0，普通默认 pipeline 不具备相同复现口径。
2. **SettlementExtractor 1.0.2 提取修复条件有效**：所有成功通过 QG 且完成 settlement 的章节均有角色/数值记录；后续复跑需使用全窗口分母，避免 settlement/summary 失败章节被排除。
3. **设定回收提示尚未显著降低 orphan 累积速度**：Task 135 的 health floor 指标通过，但 orphan 增长速率未减半，反而在 Ch12–Ch15 加速。
4. **默认切换 enforce 的条件未满足**：因 Task 135 未完全达标，暂不建议将 `gate_mode="enforce"` 或 Writer 1.2.0 设为默认。

**下一步建议**：
- 为 CreativeDirector 注入「近期必须回收设定」清单，强制每章至少回收 1–2 个高优先级 orphan。
- 优化 continuity auditor 的 orphaned_settings 判定与蒸发策略，避免设定只增不减。
- 完成上述调优后，先使用 Task 136 脚本或等效显式 Writer 1.2.0 配置复跑 Ch1–Ch20；通过后再做完整默认 `gate_mode="enforce"` 的 Ch1–Ch50/Ch1–Ch150 验证，最后评估默认切换。
