# Task 139c：V5.2 Enforce 模式 Ch51-Ch150 长窗口验证

> **类型**: 实跑验证
> **状态**: 待执行
> **前置**: Task 139b 已完成，Ch1-Ch50 enforce 验证通过。
> **依赖**: Task 139b 创建的项目、enforce 模式、V5.2 主干默认配置。

## 背景

Task 121q 已在 `observe` 模式下完成 Ch1-Ch150 full single-run（`run-a2bed648`），但那是旧配置。要默认启用 enforce 模式，必须证明：在长窗口（Ch51-Ch150）下，gate 仍不会因为正常的 continuity 波动、budget 压力或 QG 抖动而误触发。

## 目标

延续 Task 139b 的项目，从 Ch51 跑到 Ch150，获得 enforce 模式下 Ch1-Ch150 的完整证据。

## 验收标准

- [ ] 复用 Task 139b 的项目，避免从头重建（保证 Ch1-Ch50 已是 enforce 接受状态）。
- [ ] 执行 `songyan run --gate-mode enforce` 从 Ch51 跑到 Ch150。
- [ ] Ch51-Ch150 全部 `accepted`，`failed=[]`，无 `AutoHaltException`。
- [ ] Ch150 最终 continuity health ≥ 6.0，P1/P2 critical orphan ≤ 5。
- [ ] 所有 gate 触发次数为 0（或均为真实问题且已闭环）。
- [ ] 生成报告 `docs/reports/task-139c-enforce-ch51-ch150-validation-report.md`。
- [ ] 更新本任务文件为 DONE，并同步 `tasks/V5-README.md`。

## 实现步骤

1. **延续项目**
   ```powershell
   $env:PROJECT_ID = "<139b_project_id>"
   python -m songyan.cli run --gate-mode enforce --start-chapter 51 --end-chapter 150
   ```
   或编写 `scripts/run_139c_enforce_ch51_ch150.py`。

2. **监控重点**
   - Ch60、Ch90、Ch120、Ch150 等长窗口检查点的 health / orphaned / budget_used；
   - 是否有 `context_emergency` 触发；
   - 是否有 `quality_gate_fail_streak` 触发。

3. **失败处理**
   - 若 AutoHalt，分析触发章节和 gate 类型；
   - 若是阈值问题，回退 Task 139a；
   - 若是 defect，新建修复任务。

4. **生成报告**
   - 汇总 Ch1-Ch150 完整指标；
   - 重点展示 enforce 模式下的 gate 触发统计；
   - 与 Task 121q `run-a2bed648` 对比。

## 不做的事

- 不切换回 `observe` 模式（全程 enforce）；
- 不临时调整 Writer 版本或 gate 阈值；
- 不新建项目（延续 139b）。

## 风险与 Fallback

- **风险**：Ch100+ 长窗口 budget 压力导致 `context_emergency` 触发。
  - Fallback：Task 121q 已证明旧配置下无 emergency；若新配置触发，说明 138n/138o 改动影响了 budget 分布，需回滚或调整。
- **风险**：长窗口 continuity health 下滑触发 `health_low_halt`。
  - Fallback：138o 已验证 Ch50 health 8.8；若 Ch150 低于 6.0，需分析是正常衰减还是 regression。
