# Songyan 项目状态

> 短版状态板。长版历史状态已归档：`archive/v5/context-docs/STATUS-full-20260621.md`。

## 当前结论

| 项 | 状态 |
|----|------|
| 当前阶段 | **V5.0 已完成，V5.1 预研** |
| 最终验收 | Task 120 Final Acceptance Package 已交付 |
| 风险口径 | P0/P1 风险为 0 |
| 最近全量测试 | `1718 passed, 1 xfailed, 1 xpassed, 14 warnings` |
| 当前 lint | `ruff check src/ tests/` 已通过 |
| Python | 3.11.9 |
| 事实入口 | `tasks/V5-README.md` |
| 下一步规划 | `tasks/121-v50-goal-assessment-and-v51-plan.md` |

测试说明：`1 xfailed` 是 Windows SQLite 并发写入限制；`1 xpassed` 是性能测试预热/冷启动差异，均为已知非阻断项。

## 当前优先级

1. 补 Ch1-Ch150 single-run rehearsal 证据，支撑“单命令一次性 150 章”宣称。
2. 启动 V5.1 Prompt 调优，聚焦字数控制、钩子质量、叙事展开和 QG 通过率。
3. 后置预研 ContextEmergency / health_low 硬门禁，不在当前阶段一刀切启用。

## V5.0 交付摘要

- Context Diet 2.0 四组件已完成：TemporalCompressor、CharacterFocalDecay、SettingEvaporator、BudgetHardCeiling。
- Ch111-Ch150 分段验证完成：40/40 成功，QG/settlement/summary 均 40/40。
- Task 115-117 已关闭 DG-2 条件通过风险窗口。
- Task 118 已完成 ContinuityAuditor health_low P1/P2/P3 分级和 human marks 追踪。
- Task 119 已统一 `songyan report` 入口并加固 Windows wrapper。
- Task 120 给出 V5.0 最终通过结论。

## 遗留项

| 项 | 级别 | 处理 |
|----|------|------|
| 一次性 Ch1-Ch150 单命令证据 | P2 | 按 Task 121 建议补 single-run rehearsal |
| Prompt 质量瓶颈 | V5.1 | 进入 Prompt 调优，不回填到 V5.0 |
| health_low 硬门禁 | 预研 | 已有软复核与追踪，硬门禁后置 |
| ContextEmergency 硬门禁 | 预研 | 保持合理降级，后置评估 |

## 文档入口

- 开发代理规则：`AGENTS.md`
- 文档索引：`docs/INDEX.md`
- V5 任务事实：`tasks/V5-README.md`
- V5.0 最终验收：`tasks/120-v5-final-acceptance-DONE.md`
- V5.1 下一步：`tasks/121-v50-goal-assessment-and-v51-plan.md`
- V5 归档：`archive/v5/INDEX.md`
