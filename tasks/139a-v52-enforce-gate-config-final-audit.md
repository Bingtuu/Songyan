# Task 139a：V5.2 Enforce 门禁配置最终审计与单测补强

> **类型**: 工程审计 / 测试补强
> **状态**: ✅ 已完成
> **前置**: Task 138p 已完成；V5.2 主干默认配置已提交（commit `923f286`）。
> **依赖**: `src/songyan/workflows/_gates.py`、`src/songyan/models/gate_config.py`、历史 run log（`run-ba25db19`、`run-01a32b97`）、`.tmp/task138n_ch1_ch30_rerun.db`。
> **执行时间**: 2026-06-30
> **执行结果**: Ch1-Ch50 离线模拟零 gate 触发；新增 8 个单测；pytest 2031 passed / 1 xfailed；ruff 通过。

## 背景

V5.2 最后一个未达成目标是 **默认启用 `gate_mode="enforce"`**。当前默认仍为 `observe`：gate 触发只记录，不主动暂停 run。要切换到 enforce，需要先确认：

- 所有 gate 阈值在 Ch1-Ch150 长序列上不会误触发（false positive）；
- 已有单测对 enforce 触发路径的覆盖足够；
- `GateConfig` 默认值和 CLI  help 文档一致。

Task 123-128 已实现候选硬门禁并做了小窗口验证，Task 129 的 enforce Ch1-Ch50 因底层缺陷暂停。现在 138n/138o 已解决 critical orphan / continuity 下滑问题，是重新审计 enforce 配置的好时机。

## 目标

完成 enforce 门禁配置的最终审计，确保阈值合理、单测覆盖充分，为 Task 139b/c 的实跑验证提供信心。

## 验收标准

- [x] 审阅 `GateConfig` 所有阈值（`health_low`、`context_emergency`、`quality_gate_fail_streak` 等），输出阈值决策说明。
- [x] 使用 `run-ba25db19`（Ch1-Ch30）+ `.tmp/task138n_ch1_ch30_rerun.db` 的 continuity report 和 `run-01a32b97`（Ch31-Ch50）做离线 gate 触发模拟，`any_gate` 触发次数为 0。
- [x] 未发现需要调整的阈值，无需调整。
- [x] 新增 `tests/test_139a_enforce_gate_audit.py` 覆盖：开局期 QG false 不触发 streak、质量爬坡期不触发 health_low、长窗口 stability 不触发任何 gate，共 8 个用例。
- [x] 全量 pytest 通过（2031 passed, 1 xfailed）；`ruff check src/ tests/ scripts/analyze_139a_enforce_gate_audit.py` 通过。
- [x] 更新本任务文件为 DONE，并同步 `tasks/V5-README.md`。

## 实现步骤（已执行）

1. **收集历史数据**
   - 从 `.tmp/task138n_ch1_ch30_rerun.db` 读取 project `987fccbd...` 的 continuity report（Ch1-Ch30）；
   - 从 `logs/chapter_runs/run-ba25db19.jsonl` 读取 Ch1-Ch30 run log；
   - 从 `logs/chapter_runs/run-01a32b97.jsonl` 读取 Ch31-Ch50 run log。

2. **离线模拟 gate 触发**
   - 复用 `src/songyan/workflows/_gates.py` 中的判定函数，对 Ch1-Ch50 逐章调用 enforce 配置；
   - 同时模拟 `quality_gate_fail_streak` 与 `context_emergency_degraded_streak`；
   - 结果：0 章触发任何 gate。

3. **阈值审计文档**
   - 已输出 `docs/reports/task-139a-enforce-gate-config-audit.md`；
   - 列出每个 gate 的阈值、依据、Ch1-Ch50 历史数据上的触发次数（均为 0）。

4. **单测补强**
   - 新增 `tests/test_139a_enforce_gate_audit.py`，8 个用例覆盖：
     - 开局期 Ch1-Ch3 单章/两章 QG false 不触发 `quality_gate_fail_streak`；
     - 连续 3 章 QG false 触发 `quality_gate_fail_streak`（正例）；
     - 正常质量爬坡期（health 8.7 / P1=0）不触发任何 health_low gate；
     - 连续审计点 P1=0 不触发 streak gate；
     - 长窗口 health 8.8 / P1=0 不触发任何 gate；
     - 连续 CE 但全部成功不触发 degraded streak；
     - 连续 CE 伴随 settlement 失败触发 degraded streak（正例）。

5. **验证**
   - `pytest tests/test_139a_enforce_gate_audit.py -v`：8 passed；
   - `pytest tests/ -q`：2031 passed, 1 xfailed；
   - `ruff check src/ tests/ scripts/analyze_139a_enforce_gate_audit.py`：通过。

## 不做的事

- 不新增 gate 类型；
- 不修改 `observe` 模式行为；
- 不直接切换默认 `gate_mode`（由 Task 139d 执行）。

## 风险与 Fallback

- **风险**：历史数据不足，无法覆盖新配置下的所有场景。
  - Fallback：以离线模拟结果为主，剩余风险由 Task 139b/c 实跑验证兜底。
