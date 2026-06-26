# Task 125: 候选硬门禁阈值调优与验证

> **日期**: 2026-06-26
> **类型**: V5.1 工程调整 / 阈值调优
> **状态**: **DONE**
> **前置**: Task 124（影响面分析与人复核）已完成
> **输入数据**: `run-a2bed648`（Ch31-Ch150）复核结论
> **关联文档**: `tasks/124-context-emergency-health-low-gate-impact-analysis.md`

---

## 1. 背景与问题

Task 124 发现当前候选硬门禁在干净成功长跑 `run-a2bed648` 上触发过于频繁：

- `health_low_p1_halt` / `health_low_absolute_score_halt` 各触发 40 次。
- `health_low_streak_halt` 触发 118 次。
- `any_gate` 并集触发 118/120 章。

人工复核结论：

- 所有 P1 均来自 `critical` 类型的 `orphaned_settings`（22→81 个），属于长篇叙事中正常累积的未回收关键设定。
- `state_mismatches` 为 0，`overdue_foreshadowings` 几乎为 0。
- `overall_health_score` 在 Ch>30 后被硬下限保护在 2.0，因此固定阈值 `< 3.0` 的 `absolute_score_halt` 必然误伤。

---

## 2. 目标

基于复核结果调整候选硬门禁阈值/规则，使得：

1. 在 `run-a2bed648` 这类干净长跑上，`any_gate` 触发率降到可接受范围（目标 **≤ 5 章**，理想 **0 章**）。
2. 仍能在真实异常场景（如 `state_mismatch` 激增、health_score 骤降、连续审计点 P1 异常）下触发 gate。
3. `ContextEmergency` 相关规则保持不变（当前无触发样本，保持默认关闭/观测）。
4. 所有调整通过新增单测 + 全量 pytest + ruff 验证。

---

## 3. 调整方案（方案 A）

### 3.1 `health_low_p1_halt`：从“有 P1 就 halt”改为“P1 异常才 halt”

新增判断维度：

- **最小绝对阈值**：`health_low_p1_min_absolute`（候选配置 50）。
- **异常倍数**：`health_low_p1_anomaly_factor`（候选配置 1.8）。
- **滚动基线**：取之前审计点 P1 计数的中位数。

触发条件：

```text
P1_count >= health_low_p1_min_absolute
AND
P1_count > rolling_median_P1 * health_low_p1_anomaly_factor
```

当无历史审计点时，中位数为 0，因此只检查绝对阈值；存在历史数据后，必须同时超过滚动基线。

### 3.2 `health_low_absolute_score_halt`：从“绝对分数”改为“相对跌幅”

`overall_health_score` 在长跑中被下限保护在 2.0，绝对阈值失效。改为检测**相邻审计点的分数跌幅**：

- 新增字段：`health_low_score_drop_threshold`（候选配置 2.0）。
- 触发条件：`previous_score - current_score >= threshold`。
- 首次审计点无 previous_score，不触发。

### 3.3 `health_low_streak_halt`：从“3 章窗口”改为“3 个审计点窗口”

当前 `streak_window=3` 个章节通常只包含 1 个审计点，导致 `p1_limit=1` 过敏感。改为：

- 窗口基于**审计点**（`health_low_streak_audit_window=3`，约 9 章）。
- `health_low_streak_p1_limit` 固定为 250；当存在足够历史数据且配置了异常倍数时，
  动态阈值取 `3 * rolling_median_P1 * anomaly_factor` 与固定阈值的较大者。
- `health_low_streak_p2_limit` 固定为 1000，当前 run 中 P2 始终为 0。

实现上，streak gate 接收的 `recent_results` 仅包含带 `continuity_health_severity` 的审计点记录；非审计点章节不进入统计。

### 3.4 `ContextEmergency` 规则

- 不做调整。
- 默认仍关闭 / `gate_mode="observe"`。

---

## 4. 不做范围

1. **不修改生产默认配置**：系统默认 `GateConfig` 仍保持 `gate_mode="observe"`、所有 gate 关闭。
2. **不修改 ContinuityAuditor 评分逻辑**：`_compute_health_score` 的下限保护机制不在本任务改动。
3. **不发起新的 LLM 实跑**：仅基于已有 `run-a2bed648` 和 synthetic 数据验证。
4. **不做跨项目泛化验证**：调优目标先让 `run-a2bed648` 零误伤，泛化性由后续更多 run 数据验证。

---

## 5. 验收标准

- [x] 完成 Task 125 文档（本文档）。
- [x] 修改 `src/songyan/models/gate_config.py`、`src/songyan/workflows/_gates.py`、
      `src/songyan/workflows/phase2_graph.py`、
      `scripts/analyze_124_gate_impact.py`，实现上述阈值调整。
- [x] 更新 `scripts/analyze_124_gate_impact.py` 的候选配置，重跑后在 `run-a2bed648` 上 `any_gate` 触发 **0 章**。
- [x] 新增/更新单测覆盖：
  - [x] P1 异常检测（基线正常 vs 基线异常）：`tests/test_125_gate_thresholds.py`。
  - [x] health_score 相对跌幅检测：`tests/test_125_gate_thresholds.py`。
  - [x] streak 审计点窗口检测：`tests/test_125_gate_thresholds.py`。
  - [x] ContextEmergency budget ratio / failure 触发（保持已有覆盖）。
  - [x] 旧行为向后兼容：`tests/test_125_gate_thresholds.py`。
- [x] 全量 `pytest tests/` 通过，零回归：`1828 passed, 1 xfailed, 2 warnings`。
- [x] `ruff check src/ tests/ scripts/analyze_124_gate_impact.py` 通过。
- [x] 更新 `docs/STATUS.md`，将 Task 125 标记为完成。

---

## 6. 建议的实施步骤

1. **Step 1**: 在 `GateConfig` 中新增/调整阈值字段（`health_low_p1_min_absolute`、`health_low_p1_anomaly_factor`、`health_low_score_drop_threshold`、`health_low_streak_audit_window` 等）。
2. **Step 2**: 在 `_gates.py` 中新增异常检测辅助函数，并调整 `check_health_low_single_gate` / `check_health_low_streak_gate`（或新增独立 gate 函数）。
3. **Step 3**: 更新 `phase2_graph.py` 中 gate 调用点，传入必要的历史审计数据。
4. **Step 4**: 更新 `scripts/analyze_124_gate_impact.py` 中的候选配置。
5. **Step 5**: 重跑分析脚本，确认 `any_gate` 触发率达标。
6. **Step 6**: 补充单测。
7. **Step 7**: 全量 pytest + ruff。
8. **Step 8**: 更新 `docs/STATUS.md` 和 Task 125 状态为 DONE。

---

## 7. 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| 异常检测需要历史审计数据，接口变化影响 `phase2_graph.py` | 中等 | 保持向后兼容：无历史数据时不触发 gate |
| 阈值调优过度，导致真实问题漏检 | 中等 | 用 synthetic 异常用例确保异常场景仍能触发；保留 observe 模式作为默认 |
| `run-a2bed648` 外项目行为未知 | 低 | 文档明确本任务仅保证该 run 零误伤；泛化性后续验证 |

---

## 8. 相关代码入口

- 配置模型：`src/songyan/models/gate_config.py`
- 判断函数：`src/songyan/workflows/_gates.py`
- 调用点：`src/songyan/workflows/phase2_graph.py`
- 离线仿真：`scripts/analyze_124_gate_impact.py`
- 影响面报告：`docs/reports/124-gate-impact-analysis-run-a2bed648.md`

---

**一句话总结**：Task 125 的目标是把候选硬门禁从“对正常叙事累积过度敏感”调整为“对真实异常敏感”，并以 `run-a2bed648` 零误伤作为验收基线。
