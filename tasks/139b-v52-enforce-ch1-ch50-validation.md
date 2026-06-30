# Task 139b：V5.2 Enforce 模式 Ch1-Ch50 复跑验证

> **类型**: 实跑验证
> **状态**: 待执行
> **前置**: Task 139a 已完成，enforce 配置审计通过，阈值无调整或已调整到位。
> **依赖**: `songyan run --gate-mode enforce`、新 clean 项目、V5.2 主干默认配置。

## 背景

Task 129 曾在 enforce 模式下跑 Ch1-Ch50，但 Ch15 因 `quality_gate_fail_streak` 暂停，暴露的是 Writer 结构退化、SettlementExtractor 提取失败、orphaned settings 快速累积等底层缺陷。这些缺陷已由 Task 133/134/135 及 138n/138o 修复。现在需要用当前默认配置重新验证 enforce 模式能否跑完 Ch1-Ch50 而不误触发 AutoHalt。

## 目标

在 **新 clean 项目** 中以 `gate_mode="enforce"` 跑完 Ch1-Ch50，确认无 false positive gate 触发，为默认启用 enforce 模式提供 Ch1-Ch50 证据。

## 验收标准

- [ ] 新建项目并使用与 `run-a2bed648` / `run-01a32b97` 相同的 genre（scifi）和 mode（webnovel_intense）。
- [ ] 执行 `songyan run --gate-mode enforce`（或等价调用）从 Ch1 跑到 Ch50。
- [ ] Ch1-Ch50 全部 `accepted`，`failed=[]`，无 `AutoHaltException`。
- [ ] 所有 gate 触发次数为 0（或均为真实问题，且真实问题已被 revision 闭环解决）。
- [ ] settlement / QG 通过率 ≥ 95%（允许开局期少量 `degraded_accept`）。
- [ ] 生成报告 `docs/reports/task-139b-enforce-ch1-ch50-validation-report.md`。
- [ ] 更新本任务文件为 DONE，并同步 `tasks/V5-README.md`。

## 实现步骤

1. **创建新项目**
   ```powershell
   python -m songyan.cli create-project --genre scifi --mode webnovel_intense --protagonist "Lin Yuan"
   ```
   记录返回的 `project_id`。

2. **启动 enforce 模式运行**
   ```powershell
   $env:PROJECT_ID = "<project_id>"
   python -m songyan.cli run --gate-mode enforce --start-chapter 1 --end-chapter 50
   ```
   或调用 `run_project_pipeline` 编写脚本 `scripts/run_139b_enforce_ch1_ch50.py`。

3. **监控与记录**
   - 每章记录 `quality_gate_passed`、`settlement_success`、`gate_triggers`、`context_emergency`、`health_score`。
   - 若触发 AutoHalt，立即停止，分析触发原因。

4. **失败处理**
   - 若是阈值误触发，回退到 Task 139a 调整；
   - 若是新缺陷，新建 Task 139x 修复后再重跑。

5. **生成报告**
   - 汇总 50 章关键指标；
   - 与 Task 129 `run-89d7a2d4` 做对比，说明改进。

## 不做的事

- 不克隆旧项目（避免历史数据污染）；
- 不临时切换 Writer 版本（使用 manifest 默认版本）；
- 不修改 gate 配置（只验证）。

## 风险与 Fallback

- **风险**：Ch1-Ch10 开局期 QG false 仍可能触发 `quality_gate_fail_streak`。
  - Fallback：若发生，确认 Task 128 的 `degraded_accept` 标记是否正确生效；若未生效，修复后重跑。
- **风险**： enforce 模式暴露新缺陷导致暂停。
  - Fallback：记录问题，修复后重跑；V5.2 可继续延后 enforce 默认启用。
