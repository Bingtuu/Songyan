# Task 111e: Task 112 报告与 DG-2 Gate 完整性修复

> **Phase**: V5.0 Phase 4 前置修复 — Streaming Report / Decision Gate
> **优先级**: P1
> **依赖**: Task 111d 完成
> **预计工作量**: 0.5-1 天

---

## Goal

修复 Task 112 长跑报告与 DG-2 决策门的指标缺口，确保报告不会因 `budget_used=None` 崩溃，并且 DG-2 判定覆盖 Task 112 的硬验收项，而不是只看 QG 通过率和平均预算。

## Context

post-111 review 确认两个 Major 问题：

1. `streaming_report.generate_report()` 使用 `{log.budget_used or '-':.3f}`，当 `budget_used=None` 时会把 `"-"` 用 `.3f` 格式化，导致报告生成崩溃。
2. DG-2 当前只检查 QG pass rate 与 average budget，没有覆盖 Task 112 文档要求的逐章 `budget_used <= 1.0`、ContextEmergency、settlement validation、accepted summary、失败原因和可恢复性。

## In Scope（必须完成）

- [ ] **修复 streaming report 格式化**
  - `budget_used is None` 时显示 `-`
  - `budget_used == 0` 时显示 `0.000`
  - report generation 不因失败章或缺失 metrics 崩溃

- [ ] **扩展 DG-2 判定指标**
  - 完成率 / 成功章节数
  - QG 通过率
  - 每章 `budget_used <= 1.0`
  - ContextEmergency 次数与章节列表
  - settlement validation failed 次数
  - accepted 后 summary 完整性
  - 失败章节、失败原因和是否可恢复

- [ ] **补齐 chapter run metrics 采集**
  - 确认 Phase2 / run logger 写入 DG-2 所需字段
  - 若现有 JSONL 缺字段，应新增轻量字段，不写完整业务对象
  - 报告应能处理旧日志缺字段的兼容场景

## Out of Scope（明确不做）

- 不执行 Ch101-Ch150 长跑
- 不改变 QualityGate 阈值
- 不改 Phase1 修复逻辑；Phase1 correctness 进入 Task 111d
- 不新增复杂 dashboard，只保证 CLI/report 文本可判定

## DG-2 Gate 建议口径

| 指标 | 通过 | 条件通过 | 不通过 |
|------|------|----------|--------|
| 运行完成率 | >= 95% | 90%-95% 且失败可恢复 | < 90% 或连续失败 |
| QG 通过率 | >= 70% | 60%-70% | < 60% |
| `budget_used` | 每章 <= 1.0 | 单章超限但有 emergency 记录且无污染 | 超限漏判或无记录 |
| ContextEmergency | 0 或可解释 | 少量且可恢复 | 连续触发或导致失败 |
| settlement validation failed | 0 自动落库 | 有失败但未落库且进入复核 | 自动落库或 accepted 污染 |
| accepted 后 summary | 100% | 仅 fallback summary 且有记录 | 缺 summary |

## 关键测试标准

### Layer 1: 单元测试

- [ ] `budget_used=None` 的 run log 生成报告时显示 `-`，不抛异常
- [ ] `budget_used=0` 的 run log 显示 `0.000`
- [ ] DG-2 在平均 budget <= 1.0 但存在单章 `budget_used=1.2` 时不应直接通过
- [ ] DG-2 在存在 `settlement_validation_failed > 0` 时不应通过
- [ ] DG-2 在 accepted 章节缺 summary 时不应通过
- [ ] 旧 JSONL 缺新字段时报告降级显示 unknown，不崩溃

### Layer 2: 模块测试

- [ ] 构造 3-5 条 mixed chapter logs，覆盖 success/failure/emergency/missing summary
- [ ] 报告输出包含失败章节列表、失败原因、budget 超限章节、summary 缺失章节
- [ ] `generate_report()` 返回结构化 `decision`，可被 DONE 文档引用

### Layer 3: 回归测试

- [ ] `pytest tests/test_eval_runner.py tests/evals -q` 或现有 streaming report 相关测试通过
- [ ] `pytest tests/ -q`
- [ ] 本次触及文件 `ruff check` 通过

## 验收标准（Acceptance Criteria）

- [ ] streaming report 可处理 `budget_used=None`
- [ ] DG-2 判定覆盖 Task 112 文档全部硬指标
- [ ] 报告明确输出：通过 / 条件通过 / 不通过，以及阻塞原因
- [ ] 旧日志兼容，不因缺字段失败
- [ ] 生成 `tasks/111e-task112-reporting-dg2-gate-fix-DONE.md`
- [ ] 更新 `docs/STATUS.md`
- [ ] Git commit 包含代码、测试、DONE 文档和状态更新

## 参考证据

- `src/songyan/evals/streaming_report.py`
- `src/songyan/workflows/phase2_graph.py`
- `src/songyan/workflows/_run_logger.py`
- `tasks/113-ch101-ch150-streaming-validation.md`

## 下一 Task

**Task 111f: Context Snapshot、Prompt 与 Metadata 一致性修复**
