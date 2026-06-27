# Task 081: Ch51-Ch70 验证

> **Phase**: V3.1 100章架构改造 — Phase C 验证
> **优先级**: P1
> **依赖**: 076, 077, 078（Phase A 止血全部完成，含 BudgetPruner 硬断言 + ContinuityAuditor 输出预算化）
> **预计工作量**: 大（36-60 小时生成等待 + 1 天分析）

---

## Goal

在 076（字数截断）、077（分层 Setting + BudgetPruner 硬断言）、078（伏笔管理 + ContinuityAuditor 输出预算化）全部完成后，运行 Ch51-Ch70 真实 LLM 验证。

## Context

V3.1 验证已证明 Ch41-Ch50 可跑通（budget_used ≈ 2.0）。076-078 的结构性修复后，预期：

| 指标 | Ch50 基线 | Ch70 目标 | 验收条件 |
|------|----------|----------|---------|
| budget_used 最大值 | 2.0x | < 1.5x | 所有章节 ≤ 1.5x |
| final_tokens | 19175 | < 12000 | 所有章节 ≤ 12000 |
| 字数偏差 | +114% | ±20% | 所有章节在 target ±20% |
| 连续性健康分 | 0.0 | ≥ 5.0 | 全段平均 ≥ 5.0 |
| 截断重写触发率 | ~30% | < 15% | 全段平均 < 15% |
| _budget_enforced 触发率 | — | < 30% | 少于 1/3 章节触发 |
| 流程跑通率 | 100% | 100% | 无阻塞 |

## In Scope

- [ ] Mock 构建 Ch2-Ch50 历史
- [ ] 运行 Ch51-Ch60（全 auto_confirm）
- [ ] 分析 076-078 效果：字数、budget_used、约束数量、硬断言触发率
- [ ] 运行 Ch61-Ch70
- [ ] 生成验证报告 `docs/reports/v3.1_ch51_ch70_validation_report.md`

## Out of Scope

- 不做人工干预（全 auto_confirm）
- 不做 Prompt 调优（V3.2）
- 不修改代码结构（只运行和分析）

## 验收标准

- [ ] Ch51-Ch60 全通（10/10）
- [ ] Ch61-Ch70 全通（10/10）
- [ ] budget_used 所有章节 ≤ 1.5x
- [ ] 实际字数所有章节在 target ±20% 以内
- [ ] 连续性健康分全段平均 ≥ 5.0
- [ ] _budget_enforced 触发率 < 30%
- [ ] 生成验证报告
- [ ] 更新 STATUS.md
- [ ] 若未达标，输出差距分析并启动 079-080

## 参考

- `docs/reports/v3.1_ch41_ch50_validation_report.md`
