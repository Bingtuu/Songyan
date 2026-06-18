# Task 112: Ch101-Ch150 流式验证 + 决策门 DG-2

> **Phase**: V5.0 Phase 4 — 150 章规模化验证
> **优先级**: P0
> **依赖**: Task 111a、111b、111c 完成
> **预计工作量**: 2-4 天

---

## Goal

在 Task 111a-111c 修复 Agent/Workflow/Settlement/Context 契约后，执行 Ch101-Ch150 流式验证，判断 V5.0 Context Diet 2.0 是否具备支撑 150 章全自动生成的稳定性。

## Context

原 Task 111 是 “Ch101-Ch150 流式验证 + 决策门 DG-2”。整体 review 后发现多个 P0/P1 一致性问题，因此该验证顺延为 Task 112。Task 112 不再承担前置修复职责，只负责规模化实跑、指标收集、报告生成和决策门判断。

## In Scope（必须完成）

- [ ] **准备验证基线**
  - 确认 Task 111a-111c 的 DONE 文档和回归测试结果
  - 确认当前 DB、`.env`、logs 路径、checkpointer 模式和项目 ID
  - 记录 Ch80-Ch96 / Ch51-Ch100 的最新对比基线

- [ ] **执行 Ch101-Ch150 流式验证**
  - 使用 scifi + webnovel_intense
  - 使用 `--auto-confirm`
  - 保留 JSONL chapter run metrics
  - 出现连续失败时按现有熔断策略停机分析

- [ ] **收集 DG-2 指标**
  - 成功章节数
  - QG 通过率
  - `budget_used`
  - ContextEmergency 次数
  - coherence/readability/momentum/length 各维失败原因
  - revision/rewrite 次数
  - settlement validation 状态
  - summary / lifecycle / RAG / evaporator 后置维护结果

- [ ] **生成一键报告**
  - 输出 DG-2 报告
  - 对比 Task 105b、110d、110e 基线
  - 标明是否进入 V5.1 或继续 P0 修复

## Out of Scope（明确不做）

- 不在长跑中临时改评分阈值
- 不做 Prompt 调优
- 不新增 Workflow 节点
- 不修复非阻断 P2 清理项

## 接口契约

```bash
songyan run --project-id <project_id> --chapters 101-150 --auto-confirm
```

```bash
python scripts/generate_streaming_report.py --run-id <run_id>
```

实际命令以当前 CLI 和脚本参数为准；执行前必须通过 `--help` 或源码确认。

## 数据模型

不新增模型。复用现有 chapter run JSONL、project run metrics、score card、settlement 和 summary 数据。

## 测试要求

### Layer 1: 前置回归
- [ ] `pytest tests/ -q` 通过
- [ ] `ruff check src/ tests/` 无新增 lint 错误

### Layer 2: 长跑验证
- [ ] Ch101-Ch150 运行不中断，或按熔断策略留下可诊断日志
- [ ] 每章都有 chapter run metrics
- [ ] 每个 accepted 章节都有 settlement + summary，除非明确 skip_settlement 且有 fallback summary

### Layer 3: 报告验证
- [ ] DG-2 报告可复现统计数据
- [ ] 报告中标明失败章节、失败原因和是否可自动恢复

## 验收标准（Acceptance Criteria）

| 指标 | 目标 |
|------|------|
| Ch101-Ch150 运行完成率 | >= 95%，或失败可按熔断策略诊断恢复 |
| QG 通过率 | >= 70% |
| `budget_used` | 每章 <= 1.0；如超出必须触发并记录 emergency |
| ContextEmergency | 目标 0；若出现需说明触发分区和后续影响 |
| settlement validation failed | 0 个自动落库 |
| accepted 后 summary | 100% 有真实 summary 或 fallback summary |
| DG-2 报告 | 已生成并写入任务 DONE 文档 |

## 决策门 DG-2

- **通过**：QG 通过率 >= 70%，无 P0 状态污染，budget 稳定，进入 V5.1 文学质量与 Prompt 层优化。
- **条件通过**：QG 通过率 60%-70%，无 P0 状态污染，可进入局部 P1 修复后重跑失败窗口。
- **不通过**：QG 通过率 < 60%，或出现 accepted/settlement/summary 长期事实源污染，停止长跑并拆分 P0 修复任务。

## 验收标准（工程流程）

- [ ] 生成 `tasks/112-ch101-ch150-streaming-validation-DONE.md`
- [ ] 更新 `docs/STATUS.md`
- [ ] 更新 `README.md`
- [ ] Git commit 包含验证报告、DONE 文档和状态更新

## 参考文档

- `tasks/105-ch51-ch100-streaming-validation-DONE.md` — 流式验证基础设施
- `tasks/105b-ch51-ch100-validation-restart-DONE.md` — Ch51-Ch100 重启验证基线
- `tasks/110e-coherence-major-fix-DONE.md` — Ch80-Ch96 最新成功基线
- `tasks/111a-workflow-decision-contract-fix.md` — 工作流决策契约前置修复
- `tasks/111b-settlement-state-integrity-fix.md` — Settlement 事实源前置修复
- `tasks/111c-context-prompt-consistency-fix.md` — Context/Prompt 一致性前置修复
