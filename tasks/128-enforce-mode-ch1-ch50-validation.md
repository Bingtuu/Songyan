# Task 128: 硬门禁 enforce 模式 Ch1–Ch50 验证

> **类型**: 实跑验证  
> **日期**: 2026-06-26  
> **前置**: Task 125（阈值调优）、Task 126（Ch1–Ch20 小窗口）、Task 127（score halt 重构，可选但推荐）  
> **目标**: 在干净新项目上以 `gate_mode="enforce"` 跑通 Ch1–Ch50，验证 Task 125 调优后的阈值（及 Task 127 重构后的 score 规则）在中段章节不误伤正常长跑。

---

## 1. 背景与问题

Task 126 验证了 Ch1–Ch19 小窗口：禁用 `health_low_absolute_score_halt` 后，0 次 gate 触发。但 V5.1 硬门禁要支撑的是 Ch1–Ch150 完整长跑，因此必须验证：

- 阈值在中段章节（Ch21–Ch50）是否仍然安全；
- 不同剧情阶段（铺垫期 → 展开期 → 小高潮）下，P1 计数和 health_score 的波动不会误触发 gate；
- 若出现 gate 触发，是真实异常还是误伤。

---

## 2. 可选验证策略（Brainstorming）

### 策略 A：单次连续实跑 Ch1–Ch50
- **做法**：一个干净新项目，从 Ch1 连续跑到 Ch50，全程 enforce。
- **优点**：最接近真实使用场景；一次获得完整证据。
- **缺点**：成本高（时间 + API 费用）；若中途触发 gate，后续章节无法继续，需要修复后重跑。
- **推荐**: **首选策略**。

### 策略 B：分段接力实跑
- **做法**：Ch1–Ch20、Ch21–Ch35、Ch36–Ch50 分三次跑，使用同一项目但不同 run。
- **优点**：成本分散；某一段失败后不影响其他段证据。
- **缺点**：无法验证"连续长跑到中段"时的状态演化；衔接处可能有状态污染风险。
- **适用**: 作为辅助验证，不能替代策略 A。

### 策略 C：重度 Mock 长序列测试
- **做法**：在测试中 Mock 50 章的 audit 结果，模拟各种 health_score / P1 曲线，验证 gate 决策。
- **优点**：成本低、可复现、可覆盖极端情况。
- **缺点**：无法替代真实 LLM 生成的不确定性；只能验证阈值逻辑，不能验证 prompt/生成质量变化。
- **适用**: 已部分由 Task 122d 覆盖，本任务以真实实跑为主。

### 策略 D：与历史 run 对比
- **做法**：在 `run-a2bed648`（Ch1–Ch150 成功）的 continuity report 上回放新的 gate 配置，计算若在 enforce 下会触发几次。
- **优点**：快速、成本低。
- **缺点**：不能验证新配置对未来运行的影响；无法暴露 Task 126 那种"新项目开局期"的特殊行为。
- **适用**: 作为前置分析，已在 Task 124/125 完成。

---

## 3. 推荐方案

采用 **策略 A 为主，策略 C 为辅**：

1. 先在干净新项目上连续实跑 Ch1–Ch50（策略 A）。
2. 同时补充 50 章 Mock 压力场景（策略 C），覆盖健康分持续下跌、P1  streak、中段 score 新低等边界。
3. 若策略 A 中途触发 gate，根据 continuity report 判断是误伤还是真异常，决定是否回滚到 Task 127/125 调优。

---

## 4. 执行方式

### 4.1 项目准备
- 创建新的干净项目，配置与 `run-a2bed648` 同 genre/mode。
- 清理环境：终止残留 Python 进程、删除测试数据、确保数据库状态干净（参考 Task 121q 重跑前清理协议）。

### 4.2 Gate 配置

使用 Task 125 调优后的配置，并叠加 Task 127 重构后的规则：

```python
gate_config = GateConfig(
    mode="enforce",
    health_low_p1_halt={
        "enabled": True,
        "min_absolute": 50,
        "anomaly_factor": 1.8,
    },
    health_low_streak_halt={
        "enabled": True,
        "audit_window": 3,
        "p1_limit": 250,
    },
    # Task 127 重构后的规则
    health_low_score_halt={
        "enabled": True,
        "p1_anomaly_factor": 1.8,
        "p1_audit_window": 3,
        "min_absolute_p1": 20,
    },
    context_emergency_halt={
        "enabled": True,
        # Task 125 调优参数
    },
)
```

> 若 Task 127 尚未完成，可先按 Task 126 的做法禁用 `health_low_absolute_score_halt`，完成 Ch1–Ch50 验证后再补跑一次带 Task 127 的版本。

### 4.3 调用方式
- CLI `songyan run` 暂未暴露 `--gate-mode`，参考 Task 126 直接调用 `run_project_pipeline(..., gate_config=gate_config)`。
- 记录 `run_id`、项目 ID、总耗时、每章 gate_triggered 字段。

---

## 5. 验收标准

### 5.1 实跑结果
- [ ] 单一 `run_id` 覆盖 Ch1–Ch50。
- [ ] Ch1–Ch50 全部进入 `completed` 状态，或失败原因被明确记录。
- [ ] `any_gate` 触发次数 **≤ 1 次**（理想为 0 次）。
- [ ] 若触发 gate，必须提供 continuity report 和人工复核结论。

### 5.2 关键指标
- [ ] ContextEmergency 次数 ≤ 合理阈值（建议 ≤ 3 次，且非连续）。
- [ ] AutoHalt 次数 ≤ 合理阈值（建议 0 次）。
- [ ] `degraded_accept` 次数 ≤ 合理阈值（建议 0 次）。
- [ ] `failed` 章节 ≤ 1 章，且失败原因非 gate 误触发。

### 5.3 输出物
- [ ] 实跑日志：`logs/chapter_runs/run-<id>.jsonl`。
- [ ] `songyan report --run-id <run_id>` 报告。
- [ ] 每章 continuity audit 摘要（P1 计数、health_score、gate_triggered 原因）。

### 5.4 测试与 lint
- [ ] 若新增 Mock 压力测试，全量 pytest 通过。
- [ ] `ruff check src/ tests/ scripts/` 通过。

---

## 6. 依赖关系

```
Task 125 阈值调优 ──┐
Task 126 Ch1-Ch19   ├──► Task 128 Ch1-Ch50 enforce 验证 ──┬──► Task 129 默认模式决策
Task 127 score halt ┘                                   │
Task 122d 压力测试（可选参考）───────────────────────────────┘
```

---

## 7. 风险与回滚

| 风险 | 影响 | 缓解 |
|------|------|------|
| 中段章节 P1 自然升高触发 gate | 误伤正常长跑 | 现场分析 continuity report；若属误伤，回滚 Task 125/127 调优 |
| 实跑成本过高 / 时间过长 | 验证周期拉长 | 可分两天跑；使用后台任务；优先保证 Ch1–Ch30 证据 |
| Ch20 之后再次遇到 QG false block | 非 gate 问题但中断 run | 沿用 Task 121m 的 QG false 拦截；若新原因出现，单独开 task 修复 |
| 环境残留污染新项目 | 证据不可靠 | 严格执行 Task 121q 重跑前清理协议 |

---

## 8. 成功 / 失败口径

- **成功**：Ch1–Ch50 跑通，`any_gate` 触发 0 次，AutoHalt 0 次。
- **条件成功**：触发 1 次 gate，但经人工复核确认为真实异常（如主线设定冲突、state mismatch），且 gate 行为符合设计。
- **失败**：触发 gate 且确认为误伤，需回滚到 Task 125/127 重新调优。

---

## 9. 交付物

- `tasks/128-enforce-mode-ch1-ch50-validation-DONE.md`
- 实跑日志：`logs/chapter_runs/run-<id>.jsonl`
- `songyan report` 输出
- 新增 Mock 压力测试（如需）
- 全量 pytest / ruff 通过记录
