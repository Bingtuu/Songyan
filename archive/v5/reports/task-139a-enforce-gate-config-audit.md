# Task 139a：V5.2 Enforce 门禁配置最终审计报告

> 数据来源:
> - Ch1-Ch30: `.tmp/task138n_ch1_ch30_rerun.db` (Task 138n 重跑数据)
> - Ch31-Ch50: `logs/chapter_runs/run-01a32b97.jsonl` (Task 138o 延续验证数据)
> - 模拟配置: `GateConfig.for_mode('enforce')`

## 总体结论

- 分析章节数: 50
- 触发 gate 章节数: 0
- 触发比例: 0.0%

## 各 gate 触发统计

| Gate 类型 | 触发次数 |
|-----------|----------|
| (无) | 0 |

## 逐章触发详情

| 章节 | gate_triggered | 触发原因 | health_score | QG | CE |
|------|----------------|----------|--------------|----|----|
| 1 | False | - | None | True | False |
| 2 | False | - | None | True | False |
| 3 | False | - | 10.0 | True | False |
| 4 | False | - | None | True | False |
| 5 | False | - | None | True | False |
| 6 | False | - | 10.0 | True | False |
| 7 | False | - | None | True | False |
| 8 | False | - | None | True | False |
| 9 | False | - | 9.1 | True | False |
| 10 | False | - | None | True | False |
| 11 | False | - | None | True | False |
| 12 | False | - | 9.0 | True | False |
| 13 | False | - | None | False | False |
| 14 | False | - | None | True | False |
| 15 | False | - | 8.9 | True | False |
| 16 | False | - | None | True | False |
| 17 | False | - | None | True | False |
| 18 | False | - | 8.5 | True | False |
| 19 | False | - | None | True | False |
| 20 | False | - | None | True | False |
| 21 | False | - | 9.2 | True | False |
| 22 | False | - | None | True | False |
| 23 | False | - | None | True | False |
| 24 | False | - | 8.4 | True | False |
| 25 | False | - | None | True | False |
| 26 | False | - | None | True | False |
| 27 | False | - | 8.6 | True | False |
| 28 | False | - | None | True | False |
| 29 | False | - | None | True | False |
| 30 | False | - | 8.5 | True | False |
| 31 | False | - | None | True | False |
| 32 | False | - | None | True | False |
| 33 | False | - | 9.2 | True | False |
| 34 | False | - | None | True | False |
| 35 | False | - | None | True | False |
| 36 | False | - | 9.2 | True | False |
| 37 | False | - | None | True | False |
| 38 | False | - | None | True | False |
| 39 | False | - | 9.4 | True | False |
| 40 | False | - | None | True | False |
| 41 | False | - | None | True | False |
| 42 | False | - | 8.8 | True | False |
| 43 | False | - | None | True | False |
| 44 | False | - | None | True | False |
| 45 | False | - | 8.7 | True | False |
| 46 | False | - | None | True | False |
| 47 | False | - | None | True | False |
| 48 | False | - | 8.8 | True | False |
| 49 | False | - | None | True | False |
| 50 | False | - | None | True | False |

## 阈值审计说明

本次离线模拟使用 `GateConfig.for_mode('enforce')` 的默认阈值:

- `health_low_p1_halt`: 任意 P1 触发（经 P1 异常检测保护）。
- `health_low_score_halt`: 历史新低 + P1 超过近期中位数 1.8 倍且 ≥20。
- `health_low_streak_halt`: 连续 3 章审计点窗口内 P1≥1 或 P2≥2。
- `context_emergency_single_halt`: ContextEmergency 且 `budget_used_before_emergency ≥ 1.3`。
- `context_emergency_failure_halt`: ContextEmergency 导致 settlement/summary 失败。
- `quality_gate_fail_streak`: 连续 3 章 QG 失败。
- `context_emergency_degraded_streak`: 连续 3 章 ContextEmergency 且伴随降级。

## 结论

离线模拟结果显示，当前 enforce 默认配置在 Ch1-Ch50 历史数据上 **零误触发**，满足进入 Task 139b 实跑验证的条件。
