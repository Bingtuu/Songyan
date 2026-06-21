# Songyan 项目状态

> 短版状态板。长版历史状态已归档：`archive/v5/context-docs/STATUS-full-20260621.md`。

## 当前结论

| 项 | 状态 |
|----|------|
| 当前阶段 | **V5.0 已完成，V5.1 预研** |
| 最终验收 | Task 120 Final Acceptance Package 已交付 |
| 风险口径 | P0/P1 风险为 0 |
| 最近全量测试 | `1718 passed, 2 xfailed, 15 warnings` |
| 当前 lint | `ruff check src/ tests/` 已通过 |
| Python | 3.11.9 |
| 事实入口 | `tasks/V5-README.md` |
| single-run rehearsal | Task 121b 已执行：`run-21ff158b`，Ch1-Ch4 成功，Ch5 阻断，最终 `partial` |
| Task 121c | 已修复 rewrite fallback 后 `_skip_settlement=True` 错误阻断 settlement 的契约 |
| Task 121d | 已创建修复后重跑边界；下一步使用新干净 rehearsal 项目重跑 Ch1-Ch150 |
| 重跑前清理 | 已清理缓存、`__pycache__`、旧 WAL/SHM；无 `python/pytest/songyan` 残留进程；`songyan.db` 完整性检查为 `ok` |
| 下一步规划 | 执行 Task 121d，验证 Ch5 是否解除阻断 |

测试说明：`2 xfailed` 为已知非阻断项，其中包含 Windows SQLite 并发写入限制，以及冷启动下 embedding model 加载导致的性能 xfail。

## 当前优先级

1. 执行 Task 121d：使用新的干净 rehearsal 项目重跑 Ch1-Ch150，验证 Task 121c 是否解除 Ch5 settlement skip 阻断。
2. 若 single-run 继续暴露新阻断，按失败点继续收敛；通过后再启动 V5.1 Prompt 调优。
3. ContextEmergency / health_low 硬门禁继续后置预研。

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
| 一次性 Ch1-Ch150 单命令证据 | P1 | **Task 121b 已执行但未通过；Task 121c 已修复直接阻断；Task 121d 已创建重跑边界**。下一步用新干净项目重跑 rehearsal |
| Prompt 质量瓶颈 | V5.1 | 进入 Prompt 调优，不回填到 V5.0 |
| health_low 硬门禁 | 预研 | 已有软复核与追踪，硬门禁后置 |
| ContextEmergency 硬门禁 | 预研 | 保持合理降级，后置评估 |

## 文档入口

- 开发代理规则：`AGENTS.md`
- 文档索引：`docs/INDEX.md`
- V5 任务事实：`tasks/V5-README.md`
- V5.0 最终验收：`tasks/120-v5-final-acceptance-DONE.md`
- V5.1 下一步：`tasks/121a-v50-goal-assessment-and-v51-plan.md`
- Single-run rehearsal：`tasks/121b-ch1-ch150-single-run-rehearsal-DONE.md`
- Rewrite fallback settlement 修复：`tasks/121c-rewrite-fallback-settlement-contract-DONE.md`
- 修复后 single-run 重跑：`tasks/121d-ch1-ch150-single-run-rerun.md`
- V5 归档：`archive/v5/INDEX.md`
