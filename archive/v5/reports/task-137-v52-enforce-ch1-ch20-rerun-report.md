# Task 137: V5.2 Ch1-Ch20 采集窗口复跑验证报告

- 生成时间: 2026-06-28T11:36:05
- 验证项目 ID: `56fbb888d78f4b29bb1a0e8aa7e6a675`
- Run ID: `run-06ae5101`
- 源项目 ID: `e95a1fa3`（Task 121q full single-run，基线 `run-a2bed648`）
- Writer 工艺卡: 1.2.0（验证期间临时切换，退出时恢复运行前 manifest default_version）
- Gate 配置: 基于 enforce profile 的采集窗口（为完整采集指标，临时关闭 health_low 相关 halt；ContextEmergency 门禁仍开启）

## 1. 总体结果

- 完成章数: 12 / 20
- Run 终态: `partial`
- 完成章节: Ch1-Ch11
- 失败章节: Ch12
- 完成率: 60.00%
- 综合通过: 否

本次 Task 137 复跑未达到验收标准，且未跑到 Ch15/Ch20，因此 orphan 增速减半目标不能被完整评估。

## 2. 已验证通过项

- Writer 1.2.0 多场景结构仍有效：Ch1-Ch12 `scenes_count >= 2` 占比 100%。
- Ch1-Ch10 均完成 accept、settlement、summary。
- Continuity 审计点 Ch3/Ch6 health score 均为 10.0。
- 运行退出后 Writer manifest 已恢复到运行前默认版本 `1.1.0`。

## 3. 未通过项与阻塞

- Ch11 run log 标记 `success=true`，但 `quality_gate_passed=false`、`settlement_success=false`、`summary_success=false`；DB 中 Ch11 `chapter_heads.status='draft'` 且 `accepted_version_id` 为空，暴露章节成功判定与 head 状态不一致风险。
- Ch12 在 `settlement_review` 阶段失败，`settlement_needs_human_review=true`，最终 run 进入 `partial`。
- Ch9 ContinuityAuditor 已出现 `orphaned_settings=10`、`health_score=7.1`，但由于 run 未到 Ch12/Ch15，Task 137 的 orphan 增速指标不可判定。
- Ch1-Ch20 全窗口 Settlement+Summary 成功且含角色/数值记录占比为 0.00%，低于 95% 目标；主要原因是 Ch11/Ch12 失败且本窗口角色/数值记录计数为 0。

## 4. 每章结果摘要

| Ch | Word | Scenes | Settlement | Summary | QG | 备注 |
|---:|---:|---:|:---|:---|:---|---|
| 1 | 3244 | 2 | True | True | Y | 通过 |
| 2 | 4007 | 3 | True | True | Y | 通过 |
| 3 | 3785 | 2 | True | True | Y | continuity health 10.0 |
| 4 | 3985 | 2 | True | True | Y | 通过 |
| 5 | 4197 | 3 | True | True | Y | 通过 |
| 6 | 4125 | 3 | True | True | Y | continuity health 10.0 |
| 7 | 3823 | 2 | True | True | Y | 通过 |
| 8 | 3746 | 2 | True | True | Y | 通过 |
| 9 | 4053 | 3 | True | True | Y | orphaned 10, health 7.1 |
| 10 | 4141 | 3 | True | True | Y | 通过 |
| 11 | 4545 | 3 | False | False | N | run log success 与 DB draft head 不一致 |
| 12 | 2776 | 2 | False | False | Y | settlement_review 失败 |

## 5. 结论

Task 137 代码单测已通过，但实跑验证未通过。下一步不应直接扩大窗口或设为默认配置，应先修复：

- settlement 数值更新校验失败导致 Ch12 中断的问题；
- QG false / convergence failed 章节被记为 success 但未 accepted 的状态一致性问题；
- Ch9 起 orphaned settings 仍快速出现的问题；
- Writer 1.2.0 在 Ch11 附近的长度、预算与 rewrite 稳定性问题。

## 6. 后续修复记录

2026-06-28 已完成 Ch12 settlement_review 的直接修复：

- `prompts/cards/settlement_extractor/1.0.2.yaml` 明确温度、倒计时、仪表读数、传感器读数属于状态快照，不应编造增减台账。
- `src/songyan/agents/settlement_extractor/_validate.py` 在公式校验前，对有明确正文/quote 读数证据的温度、倒计时 numerical_update 规整为 `telemetry_snapshot`。
- 新增回归测试覆盖 Ch12 类温度读数、倒计时读数、无读数证据不静默修正。

该修复尚未构成 Task 137 验收通过证据；仍需处理 Ch11 状态一致性与 Ch9 orphaned settings 后重新执行 Ch1-Ch20 复跑。
