# Task 082: Ch71-Ch100 验证

> **Phase**: V3.1 100章架构改造 — Phase C 验证
> **优先级**: P1
> **依赖**: 079（RevisionHandler 重构）+ 080（角色出场窗口）+ 081（Ch51-Ch70 已通过）
> **预计工作量**: 大（48-72 小时生成等待 + 2 天分析）

---

## Goal

跑通 100 章里程碑，验证全部结构性改造的综合效果：上下文预算控制在 1.5x 以内、字数稳定在 ±10%、Revision 成功率 >90%。

## Context

如果 076-080 全部完成，预期：

| 指标 | Ch50 基线 | Ch100 目标 | 验收条件 |
|------|----------|-----------|---------|
| budget_used 最大值 | 2.0x | < 1.5x | 所有章节 ≤ 1.5x |
| final_tokens | 19175 | < 12000 | 所有章节 ≤ 12000 |
| 字数偏差 | +114% | ±10% | 所有章节在 target ±10% |
| 连续性健康分 | 0.0 | ≥ 5.0 | 全段平均 ≥ 5.0 |
| 截断重写触发率 | ~30% | < 10% | 全段平均 < 10% |
| _budget_enforced 触发率 | — | < 50% | 即使触发也控制在 budget × 1.5 |
| 流程跑通率 | 100% | 100% | 无阻塞 |

## In Scope

- [ ] Mock 构建 Ch2-Ch70 历史
- [ ] 运行 Ch71-Ch80，中期检查 budget_used 趋势
- [ ] 运行 Ch81-Ch90
- [ ] 运行 Ch91-Ch100
- [ ] 生成完整验证报告 `docs/reports/v3.1_ch71_ch100_validation_report.md`

## Out of Scope

- 不做 100+ 章测试（V4.0）
- 不修改代码结构

## 验收标准

- [ ] Ch71-Ch100 全通（30/30）
- [ ] budget_used 所有章节 ≤ 1.5x
- [ ] 实际字数所有章节在 target ±10%
- [ ] 连续性健康分全段平均 ≥ 5.0
- [ ] 截断重写触发率 < 10%
- [ ] DB 检查：foreshadowing 归档正常，human_marks 未爆炸
- [ ] 生成完整验证报告
- [ ] 更新 STATUS.md 为 V3.1-100章验证通过

## 参考

- `docs/reports/v3.1_ch41_ch50_validation_report.md`
- `docs/reports/v3.1_ch51_ch70_validation_report.md`
