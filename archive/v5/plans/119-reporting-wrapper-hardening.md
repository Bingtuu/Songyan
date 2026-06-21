# Task 119: 长跑报告入口与 Windows Wrapper 加固

> **Phase**: V5.0 Phase 4 — 工程化收口
> **优先级**: P2
> **依赖**: Task 117 完成
> **预计工作量**: 1 天

---

## Goal

统一 V5.0 长跑报告生成入口，修复 Task 114c 暴露的报告文档漂移和 Windows wrapper 业务完成后仍显示 running 的问题，确保后续验证可以稳定执行、稳定退出、稳定复现报告。

## Context

Task 114c DONE 记录两个工程化问题：

1. 报告入口文档漂移：任务文档仍提到 `scripts/generate_streaming_report.py`，实际报告实现位于 `src/songyan/evals/streaming_report.py`。
2. 外层 wrapper 在业务日志显示完成后仍显示 running，需人工复核日志并停止进程。

这两个问题不影响 Task 114c 的业务结论，但会降低后续 V5.0 收口和 V5.1 长跑的可重复性。Task 119 负责把报告入口、wrapper 退出判定、日志落盘和验证命令整理成稳定工程流程。

## In Scope（必须完成）

- [ ] 统一报告生成入口和文档引用。
- [ ] 明确 CLI 或脚本调用方式，避免报告生成依赖隐式源码路径。
- [ ] 加固 PowerShell Job wrapper 的业务完成判定和退出流程。
- [ ] 确保 stdout/stderr、JSONL、report 路径命名一致。
- [ ] 补充最小测试或脚本级验证。
- [ ] 更新 `AGENTS.md` 或相关操作文档中的长跑执行说明，如需要。

## Out of Scope（明确不做）

- 不修改长跑业务逻辑。
- 不修改 QualityGate、Settlement 或 Context 策略。
- 不重跑 Ch111-Ch150。
- 不引入新的任务编排系统。

## 实现方案

### 1. 报告入口统一

选择一个正式入口：

- 优先：CLI 子命令，例如 `songyan report streaming`。
- 次选：保留脚本包装，但内部调用 `songyan.evals.streaming_report.generate_report()`。

统一后所有文档只引用一个入口，避免 `scripts/` 与 `src/` 实现分叉。

### 2. Wrapper 退出判定

PowerShell wrapper 应同时判断：

- 子进程 exit code。
- stdout 中是否出现 `project_pipeline.end`。
- JSONL 中 final_status 是否为 completed。
- 超时是否触发。
- 是否仍有残留 `python/pytest/songyan` 进程。

业务完成但 wrapper 未退出时，应输出明确状态，例如：

```text
WRAPPER_RESULT=PASS_BUSINESS_COMPLETED_WRAPPER_TIMEOUT
```

而不是让调用方只能人工判断。

### 3. 日志命名规范

建议命名：

```text
logs/task119/<task>-<chapters>-<timestamp>.out.log
logs/task119/<task>-<chapters>-<timestamp>.err.log
logs/reports/report-<task>-<range>.md
logs/chapter_runs/<run-id>.jsonl
```

Task 119 不迁移历史日志，只统一后续规范。

### 4. 报告一致性检查

报告生成后检查：

- 总章节数与 JSONL 一致。
- success/failure 与 JSONL 一致。
- budget、emergency、settlement、summary 字段完整。
- 缺失字段时给出明确 warning，不崩溃。

## 接口契约

```bash
python -m songyan.evals.streaming_report --input logs/chapter_runs/<run_id>.jsonl --output logs/reports/<report>.md
```

或：

```bash
songyan report streaming --input logs/chapter_runs/<run_id>.jsonl --output logs/reports/<report>.md
```

最终以项目现有 CLI 风格为准，但只能保留一个推荐入口。

## 数据模型

不新增业务模型。可新增 wrapper 结果结构：

```python
class WrapperResult(BaseModel):
    command: str
    exit_code: int | None
    business_completed: bool
    timed_out: bool
    result: str
    stdout_path: str
    stderr_path: str
```

## 执行流程

1. **入口盘点**
   - 搜索报告生成相关脚本、函数和文档引用。
   - 确认当前实际可用入口。

2. **入口统一**
   - 增加或修复推荐入口。
   - 将旧入口标记为兼容或删除引用。

3. **Wrapper 加固**
   - 梳理现有 PowerShell Job 包装方式。
   - 增加业务完成判定和明确结果输出。

4. **验证**
   - 用现有 Task 114c JSONL 生成报告。
   - 用短命令验证 wrapper 正常退出。
   - 用模拟超时验证 wrapper 输出明确状态。

5. **文档收口**
   - 生成 `tasks/119-reporting-wrapper-hardening-DONE.md`。
   - 更新 V5 状态入口和必要操作文档。

## 测试要求

### Layer 1: 报告入口测试

- [ ] 推荐入口可读取 Task 114c JSONL 并生成 markdown 报告。
- [ ] 缺失 optional 字段时不崩溃，并输出 warning。
- [ ] 生成结果与原 DG-2 报告关键指标一致。

### Layer 2: Wrapper 测试

- [ ] 正常完成命令输出 `PASS_NORMAL_EXIT`。
- [ ] 业务完成但 wrapper 超时输出 `PASS_BUSINESS_COMPLETED_WRAPPER_TIMEOUT`。
- [ ] 真超时输出 failure 状态并保留日志。

### Layer 3: 文档引用测试

- [ ] `rg "generate_streaming_report|streaming_report" tasks docs README.md` 中无过时入口。
- [ ] 新入口在 README/STATUS/任务文档中一致。

## 验收标准（Acceptance Criteria）

| 指标 | 目标 |
|------|------|
| 报告入口 | 只有一个推荐入口，文档引用一致 |
| 报告复现 | Task 114c JSONL 可重新生成同等关键指标报告 |
| wrapper 正常退出 | 正常短任务可自动退出 |
| wrapper 异常判定 | 业务完成但外层异常时有明确结果码 |
| 日志 | stdout/stderr/report/JSONL 路径可追踪 |
| 测试 | 聚焦测试或脚本验证通过；`ruff check src/ tests/` 通过 |

## 风险与应对

| 风险 | 应对 |
|------|------|
| 入口统一破坏旧脚本调用 | 保留兼容包装，但文档只推荐新入口 |
| wrapper 误杀仍在运行的业务进程 | 必须同时检查业务完成标记和超时 |
| 报告指标与历史报告有轻微差异 | 明确差异来源，不能静默覆盖 Task 114c 事实 |

## 参考文档

- `tasks/114-ch101-ch150-streaming-validation-DONE.md`
- `archive/v5/reports/report-task114c-dg2-ch111-ch150.md`
- `src/songyan/evals/streaming_report.py`
- `AGENTS.md`
