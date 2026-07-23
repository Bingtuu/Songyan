# Task 124: 候选硬门禁离线影响面分析

> **日期**: 2026-06-26
> **类型**: V5.1 数据分析 / 影响面评估
> **状态**: **DONE**
> **前置**: Task 123（ContextEmergency / health_low 候选硬门禁实现）已完成
> **输入数据**: `run-a2bed648`（Ch31-Ch150 可用，120/120，0 emergency，0 AutoHalt；Ch1-Ch30 无 JSONL/DB 记录）
> **关联文档**: `tasks/123-context-emergency-health-low-gate-proposal.md`

---

## 1. 目标

在**不发起新实跑**的前提下，基于已有干净长跑数据 `run-a2bed648`，对 Task 123 实现的候选硬门禁做离线仿真，量化各类 gate 在真实 150 章项目中的触发次数、分布和潜在误伤率，为是否开启 enforce 模式提供数据依据。

具体目标：

1. 模拟 `health_low_p1_halt` 会触发多少次 pause，分布在哪些章节。
2. 模拟 `health_low_streak_halt`（窗口 3，P1≥1 / P2≥2）会触发多少次 pause。
3. 模拟 `health_low_absolute_score_halt`（score < 3.0）会触发多少次 pause。
4. 模拟 `context_emergency_single_halt`（`budget_used_before_emergency > 1.3`）会触发多少次 pause。
5. 模拟 `context_emergency_failure_halt`（emergency + settlement/summary 失败）会触发多少次 pause。
6. 输出一份可归档的影响面报告，包含逐章明细和汇总统计。

---

## 1.5 实际执行结果摘要

- **分析脚本**: `scripts/analyze_124_gate_impact.py`
- **输出报告**: `archive/v5/reports/124-gate-impact-analysis-run-a2bed648.md`
- **分析范围**: Ch31 - Ch150（共 120 章）
- **关键发现**:
  - `health_low_p1_halt` / `health_low_absolute_score_halt` 各触发 **40 次**（每 3 章审计点均触发）。
  - `health_low_streak_halt` 触发 **118 次**，首次触发后几乎持续影响全部后续章节。
  - `context_emergency_*` 规则触发 **0 次**，与 run 中 `context_emergency=False` 一致。
  - `any_gate` 并集触发 **118 次**；若首次触发即完全阻断，将影响后续 **118** 章。
- **结论**: 当前候选阈值对 `run-a2bed648` 过于敏感，默认配置仍需保持 `gate_mode="observe"`，硬门禁阈值调整需待后续人工复核。

## 2. 数据源

### 2.1 主数据源：`logs/chapter_runs/run-a2bed648.jsonl`

每章一条 `ChapterRunLog`，已包含：

- `chapter_number`
- `success`
- `continuity_health_score`（每 3 章一次，其余为 `null`）
- `context_emergency`
- `budget_used_before_emergency`
- `settlement_success`
- `summary_success`
- `quality_gate_passed`
- `budget_used`
- `context_pressure`

当前文件实际范围：**Ch31-Ch150**（120 条记录）。Ch1-Ch30 在数据库中亦无对应 `chapter_run_logs` 记录，因此本次分析范围明确为 Ch31-Ch150。

### 2.2 补充数据源：SQLite 数据库

实际读取：

- `logs/chapter_runs/run-a2bed648.jsonl`：每章运行结果。
- `project_runs`：定位 `run-a2bed648` 对应的项目 ID。
- `continuity_reports`：获取每 3 章一次的完整 `ContinuityReport`，用于精确计算 P1/P2/P3 计数。

### 2.3 说明

- `run-a2bed648` 是 V5.0 最终成功证据：**0 ContextEmergency、0 AutoHalt、0 degraded_accept**。
- 因此，任何 gate 触发都属于“软信号在成功长跑中被触发”的情况，需判断是否为误伤。

---

## 3. 仿真规则

仿真程序使用 Task 123 实现的 `GateConfig` 和 `src/songyan/workflows/_gates.py` 中的判断函数，确保与生产代码一致。

### 3.1 单章 health_low 规则

```python
GateConfig(
    gate_mode="enforce",
    health_low_gate_enabled=True,
    health_low_p1_halt=True,
    health_low_absolute_score_halt=True,
    health_low_absolute_score_threshold=3.0,
)
```

触发条件：
- 该章 `ContinuityReport` 中 P1 计数 ≥ 1（state_mismatch / critical orphaned setting）。
- 或 `overall_health_score < 3.0`。

### 3.2 health_low streak 规则

```python
GateConfig(
    gate_mode="enforce",
    health_low_gate_enabled=True,
    health_low_streak_halt=True,
    health_low_streak_window=3,
    health_low_streak_p1_limit=1,
    health_low_streak_p2_limit=2,
)
```

触发条件：
- 连续 3 个审计点中 P1 总数 ≥ 1，或 P2 总数 ≥ 2。
- 注意：`ContinuityAuditor` 每 3 章运行一次，因此“连续 3 个审计点”对应约 9 章窗口。

### 3.3 ContextEmergency 单章规则

```python
GateConfig(
    gate_mode="enforce",
    context_emergency_gate_enabled=True,
    context_emergency_single_halt=True,
    context_emergency_budget_ratio_threshold=1.3,
    context_emergency_failure_halt=True,
)
```

触发条件：
- `context_emergency == True` 且 `budget_used_before_emergency >= 1.3`。
- 或 `context_emergency == True` 且 `settlement_success == False` / `summary_success == False`。

### 3.4 组合规则

分别跑以上规则，再跑一次“全部启用”的组合规则，统计总 pause 次数和首次 pause 章节号。

---

## 4. 输出报告结构

### 4.1 汇总表

| 规则 | 触发次数 | 首次触发章 | 连续触发章数 | 备注 |
|------|----------|------------|--------------|------|
| health_low_p1_halt | N | ChX | 最长 M 章 | |
| health_low_absolute_score_halt | N | ChX | 最长 M 章 | |
| health_low_streak_halt | N | ChX | - | |
| context_emergency_budget_ratio_halt | N | ChX | - | |
| context_emergency_failure_halt | N | ChX | - | |
| 全部启用（并集） | N | ChX | - | |

### 4.2 逐章明细表

| 章号 | health_score | P1/P2/P3 | context_emergency | budget_used_before_emergency | 触发规则 | 原因 |
|------|--------------|----------|-------------------|------------------------------|----------|------|
| 33 | 2.0 | 1/0/0 | false | null | health_low_p1_halt, health_low_absolute_score_halt | state_mismatch |
| ... | ... | ... | ... | ... | ... | ... |

### 4.3 结论与建议

- 若某规则在干净成功长跑中触发次数为 0，说明阈值宽松，可直接开启 enforce。
- 若触发次数 > 0，需逐条复核是否为真实问题或误伤，并给出阈值调整建议。
- 最终给出推荐配置（默认观测/ enforce 开关组合）。

---

## 5. 验收标准

- [x] 新建 `tasks/124-context-emergency-health-low-gate-impact-analysis.md`（本文档）。
- [x] 实现离线仿真脚本 `scripts/analyze_124_gate_impact.py`。
- [x] 脚本能够读取 `logs/chapter_runs/run-a2bed648.jsonl` 和 SQLite 数据。
- [x] 脚本复用 `src/songyan/workflows/_gates.py` 的判断函数，不自行重写规则。
- [x] 输出报告文件 `archive/v5/reports/124-gate-impact-analysis-run-a2bed648.md`。
- [x] 报告中包含汇总表、逐章明细表、结论与建议。
- [x] 新增 `tests/test_124_gate_impact.py` 单测（16 个）。
- [x] `ruff check src/ tests/ scripts/analyze_124_gate_impact.py` 通过。
- [x] 全量 pytest 通过，零回归：`1816 passed, 1 xfailed, 2 warnings`。

---

## 6. 不做范围

1. **不发起新的 LLM 实跑**：本任务只分析历史数据。
2. **不修改 gate 阈值/规则**：仅做观测和报告；阈值调整由报告结论驱动后再执行。
3. **不做跨项目泛化验证**：仅针对 `run-a2bed648` 一个项目。
4. **不人工复核每一章**：报告列出触发章节，人工复核是后续可选步骤。
5. **不改动生产默认配置**：默认仍保持 `gate_mode="observe"`。

---

## 7. 建议的实施步骤

1. **Step 1**: 确认 `run-a2bed648` 数据完整范围（JSONL 是否缺失 Ch1-Ch30，如何从 DB 补充）。
2. **Step 2**: 编写数据加载器，统一输出每章的 `continuity_health_score`、`severity`、`context_emergency`、`budget_used_before_emergency`、`settlement_success`、`summary_success`。
3. **Step 3**: 编写仿真器，遍历每章，调用 `_gates.py` 的判断函数，记录触发结果。
4. **Step 4**: 生成汇总表和逐章明细表，写入报告。
5. **Step 5**: 为仿真器添加单测（使用 mock 数据），确保规则复用正确。
6. **Step 6**: 全量 pytest + ruff，更新本文档状态为 DONE。

---

## 8. 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| JSONL 缺失 Ch1-Ch30 | 分析范围不完整 | 从 SQLite 补充；报告明确标注数据范围 |
| `continuity_health_score` 为 null 的章节无法精确算 P1/P2/P3 | 单章/连续 gate 仿真不完整 | 仅对审计点章节计算 severity，null 章节视为无 continuity 问题 |
| `context_emergency` 在干净长跑中为 0 | ContextEmergency 相关规则无样本 | 报告如实记录；可构造 synthetic case 验证规则正确性 |
| 仿真脚本依赖 `run-a2bed648` 文件路径 | 文件移动后脚本失效 | 脚本支持通过 `run_id` 从 DB 读取，JSONL 作为可选缓存 |

---

## 9. 相关代码入口

- 判断函数：`src/songyan/workflows/_gates.py`
- 配置模型：`src/songyan/models/gate_config.py`
- 历史日志：`logs/chapter_runs/run-a2bed648.jsonl`
- 数据库表：`continuity_reports`、`human_marks`、`context_snapshots`、`chapter_run_logs`

---

**一句话总结**：Task 124 的目标是基于 `run-a2bed648` 历史数据，对 Task 123 的候选硬门禁做离线仿真，输出影响面报告，为后续是否开启 enforce 模式提供量化依据。
