# Task 139a：V5.2 Enforce 门禁配置最终审计与单测补强

> **类型**: 工程审计 / 测试补强
> **状态**: 待执行
> **前置**: Task 138p 已完成；V5.2 主干默认配置已提交（commit `923f286`）。
> **依赖**: `src/songyan/workflows/_gates.py`、`src/songyan/models/gate_config.py`、历史 run log（`run-a2bed648`、`run-01a32b97`）。

## 背景

V5.2 最后一个未达成目标是 **默认启用 `gate_mode="enforce"`**。当前默认仍为 `observe`：gate 触发只记录，不主动暂停 run。要切换到 enforce，需要先确认：

- 所有 gate 阈值在 Ch1-Ch150 长序列上不会误触发（false positive）；
- 已有单测对 enforce 触发路径的覆盖足够；
- `GateConfig` 默认值和 CLI  help 文档一致。

Task 123-128 已实现候选硬门禁并做了小窗口验证，Task 129 的 enforce Ch1-Ch50 因底层缺陷暂停。现在 138n/138o 已解决 critical orphan / continuity 下滑问题，是重新审计 enforce 配置的好时机。

## 目标

完成 enforce 门禁配置的最终审计，确保阈值合理、单测覆盖充分，为 Task 139b/c 的实跑验证提供信心。

## 验收标准

- [ ] 审阅 `GateConfig` 所有阈值（`health_low`、`context_emergency`、`quality_gate_fail_streak` 等），输出一份阈值决策说明。
- [ ] 使用 `run-a2bed648`（旧配置 Ch1-Ch150 成功数据）和 `run-01a32b97`（新配置 Ch31-Ch50 数据）做离线 gate 触发模拟，确认 `any_gate` 触发次数为 0 或在可接受范围。
- [ ] 若发现会误触发的阈值，提出并实施调整方案（不新增 gate 类型）。
- [ ] 新增/更新单测覆盖：enforce 模式在开局期、质量爬坡期、长窗口期的 true negative / false positive 场景。
- [ ] 全量 `pytest tests/ -q` 与 `ruff check src/ tests/` 通过。
- [ ] 更新本任务文件为 DONE，并同步 `tasks/V5-README.md`。

## 实现步骤

1. **收集历史数据**
   - 从 `.tmp/task138n_ch1_ch30_rerun.db`、`songyan.db` 或 `logs/chapter_runs/*.jsonl` 读取 `run-a2bed648` 和 `run-01a32b97` 的每章指标。

2. **离线模拟 gate 触发**
   - 复用 `src/songyan/workflows/_gates.py` 中的判定函数，对历史数据逐章调用；
   - 记录哪些章节会触发 `health_low_halt`、`context_emergency_halt`、`quality_gate_fail_streak_halt` 等。

3. **阈值审计文档**
   - 输出 `docs/reports/task-139a-enforce-gate-config-audit.md`；
   - 列出每个 gate 的阈值、依据、历史数据上的触发次数、调整建议。

4. **单测补强**
   - 在 `tests/test_139a_enforce_gate_audit.py` 中新增：
     - 开局期 Ch1-Ch3 QG false 不触发 `quality_gate_fail_streak`；
     - 正常质量爬坡期不触发 `health_low_halt`；
     - 长窗口 health 8.5+ / P1=0 不触发任何 gate。

5. **验证**
   - `pytest tests/test_139a_enforce_gate_audit.py -v`；
   - `pytest tests/ -q`。

## 不做的事

- 不新增 gate 类型；
- 不修改 `observe` 模式行为；
- 不直接切换默认 `gate_mode`（由 Task 139d 执行）。

## 风险与 Fallback

- **风险**：历史数据不足，无法覆盖新配置下的所有场景。
  - Fallback：以离线模拟结果为主，剩余风险由 Task 139b/c 实跑验证兜底。
