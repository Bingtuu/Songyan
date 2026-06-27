# Task 129 enforce 模式 Ch1–Ch50 验证报告

> **运行ID**: `run-89d7a2d4`  
> **项目ID**: `3cf71586df2a4b5c9170d9b1a5f059cf`  
> **生成时间**: 2026-06-27T04:10:31.938486  
> **状态**: **AutoHalt 终止**（未跑完 Ch1–Ch50）  

## 1. 执行摘要

- **目标**: 以 `gate_mode="enforce"` 跑通 Ch1–Ch50。
- **实际完成**: Ch1–Ch15（共 15 章）。
- **终止原因**: `paused` —— quality_gate_fail_streak。
- **总字数**: 46,160 字。
- **总耗时**: 58m 11s。
- **平均每章耗时**: 3m 52s。

## 2. 关键指标 vs 验收标准

| 指标 | 实际值 | 验收标准 | 是否达标 |
|------|--------|----------|----------|
| 覆盖章节 | Ch1–Ch15 | Ch1–Ch50 | ❌ |
| AutoHalt 次数 | 1 | 0 | ❌ |
| Gate 触发次数 | 0 | ≤ 1 | ✅ |
| Quality Gate 失败 | 4 章 | 0 | ❌ |
| Convergence 失败 | 4 章 | 0 | ❌ |
| Settlement 失败 | 4 章 | 0 | ❌ |
| Degraded accept | 0 章 | 0 | ✅ |
| ContextEmergency | 0 次 | ≤ 3 | ✅ |
| Failed 章节 | 0 | 0 | ✅ |

## 3. 各章节质量概览

| Ch | 字数 | QG | Settlement | Converge | 预算 | 总分 | 健康分 | 耗时 |
|----|------|----|------------|----------|------|------|--------|------|
| 1 | 2845 | ✅ | ✅ | ✅ | 0.550 | 0.8684 | — | 2m 31s |
| 2 | 2883 | ✅ | ✅ | ✅ | 0.761 | 0.9314 | — | 4m 9s |
| 3 | 3596 | ❌ | ❌ | ❌ | 0.871 | 0.5766 | 10.00 | 4m 23s |
| 4 | 2561 | ✅ | ✅ | ✅ | 0.745 | 0.8027 | — | 4m 1s |
| 5 | 3215 | ✅ | ✅ | ✅ | 0.833 | 0.9031 | — | 4m 8s |
| 6 | 2669 | ✅ | ✅ | ✅ | 0.892 | 0.8377 | 7.40 | 4m 52s |
| 7 | 3252 | ✅ | ✅ | ✅ | 0.910 | 0.7226 | — | 4m 4s |
| 8 | 2990 | ✅ | ✅ | ✅ | 0.955 | 0.8387 | — | 3m 51s |
| 9 | 3015 | ✅ | ✅ | ✅ | 0.906 | 0.8105 | 1.20 | 4m 18s |
| 10 | 2765 | ✅ | ✅ | ✅ | 0.911 | 0.8821 | — | 2m 18s |
| 11 | 2589 | ❌ | ❌ | ❌ | 0.958 | 0.6710 | — | 3m 30s |
| 12 | 2933 | ✅ | ✅ | ✅ | 0.956 | 0.7282 | 0.00 | 4m 13s |
| 13 | 3829 | ✅ | ✅ | ✅ | 0.974 | 0.6665 | — | 3m 22s |
| 14 | 3801 | ❌ | ❌ | ❌ | 0.927 | 0.5332 | — | 3m 59s |
| 15 | 3217 | ❌ | ❌ | ❌ | 0.877 | 0.6900 | 0.00 | 4m 25s |

## 4. AutoHalt 根因分析

进程在 Chapter 15 后因 **quality_gate_fail_streak** 暂停。根据日志，Chapter 13、14、15 连续出现 `quality_gate_passed=False`，满足 streak 条件。

质量门失败章节详情：

| Ch | 失败原因 | 字数比 | 预算 | 可读性 | 连贯性 | 总分 |
|----|----------|--------|------|--------|--------|------|
| 3 | readability | 1.20 | 0.871 | 0.2065 | 0.8500 | 0.5766 |
| 11 | coherence_major | 0.81 | 0.958 | 0.8400 | 0.7000 | 0.6710 |
| 14 | readability, coherence_major | 1.19 | 0.927 | 0.3355 | 0.7000 | 0.5332 |
| 15 | readability | 1.01 | 0.877 | 0.3425 | 0.8500 | 0.6900 |

## 5. Continuity Health 趋势

| 检查点 | 健康分 | Orphaned | Forgotten | StateMismatch | OverdueShadow |
|--------|--------|----------|-----------|-------------|---------------|
| Ch3 | 10.00 | 0 | 0 | 0 | 0 |
| Ch6 | 7.40 | 7 | 0 | 0 | 0 |
| Ch9 | 1.20 | 12 | 0 | 0 | 0 |
| Ch12 | 0.00 | 21 | 2 | 0 | 0 |
| Ch15 | 0.00 | 27 | 2 | 0 | 2 |

## 6. 发现的关键问题

1. **Writer 结构输出单一**：所有章节的 `scenes_count=1`，明显低于 prompt 要求的 2+ 场景结构，导致可读性和连贯性承压。
2. **角色状态表为空**：`character_states` 记录数为 0，`numerical_ledgers` 记录数也为 0，说明 settlement extractor 未成功建立角色状态快照。
3. **Orphaned settings 快速累积**：从 Ch6 的 7 个上升到 Ch15 的 27 个，设定回收严重不足。
4. **Continuity health 持续恶化**：Ch9 健康分 1.2，Ch12/Ch15 跌至 0.0，P1/P3 问题大量堆积。
5. **Settlement 失败章未建立摘要**：Ch3、Ch11、Ch14、Ch15 `settlement_success=False`，对应 `summary_id=None`，导致后续上下文缺乏结算信息。
6. **质量门阈值在中段过于严格**：Chapter 12 健康分 0.0 但 quality_gate_passed=True，而 Chapter 14/15 在总分更低时失败，显示 budget/readability 权重与 continuity 健康分存在错位。

## 7. 数据资产

- 运行日志：`logs\chapter_runs\run-89d7a2d4.jsonl`
- 数据库：`songyan.db`（project_id=`3cf71586df2a4b5c9170d9b1a5f059cf`）
- 状态表统计：
  - `character_states`: 0
  - `setting_tracking`: 32
  - `foreshadowings`: 35
  - `numerical_ledgers`: 0
  - `summaries`: 11

## 8. 结论与下一步建议

**结论**：本次 enforce 模式 Ch1–Ch50 验证 **未能跑通**，在 Ch15 因 quality gate streak 触发 AutoHalt。问题集中在 Writer 结构输出、Settlement 提取、设定回收与连续性维护四个环节。

**建议下一步**：
1. **Task 130**：修复 Writer 多场景结构输出（prompt / parser 调优），确保每章至少 2 个 scene。
2. **Task 131**：修复 SettlementExtractor 角色状态与数值台账提取，解决 `character_states` 和 `numerical_ledgers` 为空的问题。
3. **Task 132**：优化设定回收策略，降低 orphaned settings 累积速度；或调整 continuity auditor 的评分/衰减逻辑。
4. 在完成上述修复后，重新发起 Task 129 复跑，目标 Ch1–Ch50 无 AutoHalt。

---

*报告由 `scripts/generate_task129_report.py` 自动生成。*
