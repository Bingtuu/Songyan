# Task 129: enforce 模式 Ch1–Ch50 验证

> **类型**: 实跑验证  
> **日期**: 2026-06-26  
> **前置**: Task 125（阈值调优）、Task 126（Ch1–Ch20 小窗口）、Task 127（score halt 重构）、Task 128（严格模式容错与质量爬坡）  
> **目标**: 在 Task 128 修复后的稳定 baseline 上，以 `gate_mode="enforce"` 跑通 Ch1–Ch50，验证调优后的阈值在中段章节不误伤正常长跑。

---

## 1. 背景与问题

Task 126 验证了 Ch1–Ch19 小窗口：禁用 `health_low_absolute_score_halt` 后，0 次 gate 触发。但 V5.1 硬门禁要支撑的是 Ch1–Ch150 完整长跑，因此必须验证：

- 阈值在中段章节（Ch21–Ch50）是否仍然安全；
- 不同剧情阶段（铺垫期 → 展开期 → 小高潮）下，P1 计数和 health_score 的波动不会误触发 gate；
- 若出现 gate 触发，是真实异常还是误伤。

Task 128 发现 enforce 模式下 Ch2 因 QG false 导致 run 终止，因此必须先完成 Task 128 的容错修复，才能进行本验证。

---

## 2. 验证策略

采用 **策略 A 为主，策略 C 为辅**：

1. 在 Task 128 修复后的代码上，连续实跑 Ch1–Ch50（策略 A）。
2. 同时补充 50 章 Mock 压力场景（策略 C），覆盖健康分持续下跌、P1 streak、中段 score 新低等边界。
3. 若中途触发 gate，根据 continuity report 判断是误伤还是真异常。

---

## 3. 执行方式

### 3.1 项目准备
- 创建新的干净项目，配置与 baseline 同 genre/mode（`xuanhuan` + `webnovel`）。
- 清理环境：终止残留 Python 进程、删除测试数据、确保数据库状态干净。

### 3.2 Gate 配置

使用 Task 125 + Task 127 调优后的配置：

```python
GateConfig(
    gate_mode="enforce",
    health_low_gate_enabled=True,
    health_low_p1_halt=True,
    health_low_p1_min_absolute=50,
    health_low_p1_anomaly_factor=1.8,
    health_low_streak_halt=True,
    health_low_streak_audit_window=3,
    health_low_streak_p1_limit=250,
    health_low_streak_p2_limit=1000,
    health_low_score_halt_enabled=True,
    health_low_score_halt_window=3,
    health_low_score_halt_min_p1=20,
    health_low_score_halt_anomaly_factor=1.8,
    context_emergency_gate_enabled=True,
    context_emergency_single_halt=True,
    context_emergency_budget_ratio_threshold=1.3,
    context_emergency_failure_halt=True,
)
```

### 3.3 调用方式
- 使用 `scripts/run_129_enforce_validation_ch1_ch50.py` 调用 `run_project_pipeline(..., gate_config=gate_config)`。
- 记录 `run_id`、项目 ID、总耗时、每章 `gate_triggered` 字段。

---

## 4. 验收标准

### 4.1 实跑结果
- [ ] 单一 `run_id` 覆盖 Ch1–Ch50。
- [ ] Ch1–Ch50 全部进入 `completed` 或 `degraded_accept` 状态。
- [ ] `any_gate` 触发次数 **≤ 1 次**（理想为 0 次）。
- [ ] 若触发 gate，必须提供 continuity report 和人工复核结论。

### 4.2 关键指标
- [ ] ContextEmergency 次数 ≤ 3 次，且非连续。
- [ ] AutoHalt 次数 = 0 次。
- [ ] `failed` 章节 = 0 章。

### 4.3 输出物
- [ ] 实跑日志：`logs/chapter_runs/run-<id>.jsonl`。
- [ ] `songyan report --run-id <run_id>` 报告。
- [ ] 每章 continuity audit 摘要。

### 4.4 测试与 lint
- [ ] 新增 Mock 压力测试通过。
- [ ] 全量 pytest 通过。
- [ ] `ruff check src/ tests/` 通过。

---

## 5. 依赖关系

```
Task 125 阈值调优 ──┐
Task 126 Ch1-Ch19   ┤
Task 127 score halt ┤──► Task 128 严格模式容错与质量爬坡 ──┐
                           │                                 │
                           └── 修复 QG false 阻断 run 问题 ──┘
                                              │
                                              ▼
                                    Task 129 enforce Ch1–Ch50 验证
```

---

## 6. 风险与回滚

| 风险 | 影响 | 缓解 |
|------|------|------|
| 中段章节 P1 自然升高触发 gate | 误伤正常长跑 | 现场分析 continuity report；若属误伤，回滚 Task 125/127 调优 |
| 实跑成本过高 / 时间过长 | 验证周期拉长 | 可分两天跑；优先保证 Ch1–Ch30 证据 |
| 环境残留污染新项目 | 证据不可靠 | 严格执行 Task 121q 重跑前清理协议 |

---

## 7. 成功 / 失败口径

- **成功**：Ch1–Ch50 跑通，`any_gate` 触发 0 次，AutoHalt 0 次。
- **条件成功**：触发 1 次 gate，但经人工复核确认为真实异常。
- **失败**：触发 gate 且确认为误伤，需回滚到 Task 125/127 重新调优。

---

## 8. 交付物

- `archive/v5/tasks/129-enforce-mode-ch1-ch50-validation-DONE.md`
- 实跑日志：`logs/chapter_runs/run-<id>.jsonl`
- `songyan report` 输出
- 新增 Mock 压力测试
- 全量 pytest / ruff 通过记录
