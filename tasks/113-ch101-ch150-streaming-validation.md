# Task 113: Ch101-Ch150 流式验证 + 决策门 DG-2

> **Phase**: V5.0 Phase 4 — 150 章规模化验证
> **优先级**: P0
> **依赖**: Task 111a-111g 完成；Task 112 前置阻断修复完成
> **预计工作量**: 2-4 天

---

## Goal

在 Task 111a-111g 修复 Agent/Workflow/Settlement/Context/Report/Performance 契约，并由 Task 112 恢复 Ch97 accepted 基线后，执行 Ch101-Ch150 流式验证，判断 V5.0 Context Diet 2.0 是否具备支撑 150 章全自动生成的稳定性。

## Context

原 Task 112 是 “Ch101-Ch150 流式验证 + 决策门 DG-2”。进入长跑前的基线检查发现 Ch97 当前 head 为 draft 且 `accepted_version_id=None`，补跑 Ch97 时又暴露 Settlement `setting_key` 非法值阻断，因此正式长跑顺延为 Task 113。

Task 113 不承担前置修复职责，只负责规模化实跑、指标收集、报告生成和决策门判断。

## In Scope（必须完成）

- [ ] **准备验证基线**
  - 确认 Task 111a-111g 的 DONE 文档和回归测试结果
  - 确认 Task 112 已恢复 Ch97 accepted + settlement + summary
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
songyan run --project-id <project_id> --chapters 101-150 --mode-id webnovel_intense --auto-confirm
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

- [ ] 生成 `tasks/113-ch101-ch150-streaming-validation-DONE.md`
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
- `tasks/111d-quality-gate-settlement-blockers-fix.md` — QualityGate 与 Settlement 阻断项修复
- `tasks/111e-task112-reporting-dg2-gate-fix.md` — Task 112 报告与 DG-2 Gate 完整性修复
- `tasks/111f-context-snapshot-prompt-metadata-fix.md` — Context Snapshot、Prompt 与 Metadata 一致性修复
- `tasks/111g-long-run-performance-containment.md` — 长跑性能缺陷收敛
- `tasks/112-preflight-blocker-fix.md` — Task 112 前置阻断修复
