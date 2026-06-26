# Task 124: 候选硬门禁离线影响面分析 — run-a2bed648

- **项目 ID**: `e95a1fa3`
- **Run ID**: `run-a2bed648`
- **分析章节范围**: Ch31 - Ch150
- **总章节数**: 120

## 1. 汇总表（enforce 模式仿真）

| 规则 | 触发次数 | 首次触发章 | 首次触发后阻断章节数 | 触发章节列表 |
|------|----------|------------|----------------------|--------------|
| health_low_p1_halt | 0 | - | 0 | - |
| health_low_absolute_score_halt | 0 | - | 0 | - |
| health_low_streak_halt | 0 | - | 0 | - |
| context_emergency_budget_ratio_halt | 0 | - | 0 | - |
| context_emergency_failure_halt | 0 | - | 0 | - |
| any_gate | 0 | - | 0 | - |

## 2. 关键发现

在本次分析的章节范围内，所有候选硬门禁规则均未触发。这表明当前默认阈值对于该 run 是安全的，可以考虑在监控下逐步开启 enforce 模式。

## 3. 审计点 severity 分布

- 审计点章节数：40
- overall_health_score：min=2.0, max=2.0, avg=2.00, median=2.00
- P1 计数：min=22, max=81, avg=53.92, median=54.50
- P2 计数：min=0, max=0, avg=0.00, median=0.00
- P3 计数：min=142, max=840, avg=484.55, median=468.00

## 4. 逐章触发明细

仅列出触发至少一条规则的章节。

| 章号 | health_score | P1/P2/P3 | context_emergency | budget_used_before_emergency | 触发规则 |
|------|--------------|----------|-------------------|------------------------------|----------|
| - | - | - | - | - | 无 |

## 5. 建议

1. 当前候选阈值（P1 异常检测、health_score 相对跌幅、审计点 streak）在该 run 中零触发，说明调整后的阈值对干净长跑是安全的。
2. 可在观测模式下继续收集更多样本，逐步验证 enforce 模式的误伤率。
3. 定期用本脚本复盘新的 run_id，形成 gate 阈值调整的闭环。

---

*本报告由 `scripts/analyze_124_gate_impact.py` 自动生成，仿真规则复用 `src/songyan/workflows/_gates.py`。*