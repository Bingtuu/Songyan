# Task 127: 重构 `health_low_absolute_score_halt`

> **类型**: 工程修复 / 阈值调优  
> **日期**: 2026-06-26  
> **前置**: Task 125（阈值调优）、Task 126（enforce 小窗口验证）  
> **目标**: 解决 `health_low_absolute_score_halt` 在新项目开局期误触发的问题，使其仅在真正异常的健康分崩溃场景下触发。

---

## 1. 背景与问题

Task 126 在 `run-13bb5303` 上以 `gate_mode="enforce"` 跑 Ch1–Ch20 时发现：

- `health_low_absolute_score_halt` 配置为 `score_drop >= 2.0` 时，在 **Ch6** 误触发。
- 原因：新项目开局期 `health_score` 从初始高值 10.0 正常回落至 5.2，并非质量崩溃，但相对跌幅达到 4.8，远超阈值。
- 结论：基于"相对跌幅"的单一指标不适合开局期，会阻断正常长跑。

Task 126 的临时处理是**禁用**该子规则，但这会削弱 gate 对真实健康分崩溃的拦截能力。本任务要给出长期稳定的重构方案。

---

## 2. 可选方案（Brainstorming）

### 方案 A：彻底移除
- **做法**：从 `GateConfig` 和 `_gates.py` 中删除 `health_low_absolute_score_halt`。
- **优点**：最简单，不会再误伤；测试维护成本低。
- **缺点**：失去对健康分断崖式下跌的硬拦截能力；未来若出现非 P1 主导但整体质量崩塌的场景无保护。
- **适用**: 若后续 Task 128/129 证明 P1 + streak 两条规则已足够覆盖真实风险，则可选。

### 方案 B：复合条件——"历史新低 + P1 同步激增"
- **做法**：
  - 记录截至目前最低的 `health_score`（per-project 或 per-run）。
  - 仅当当前 `health_score` **低于历史最低值** 且 **同章 P1 计数超过异常阈值**（如 `anomaly_factor * mean_p1`）时才触发。
- **优点**：
  - 过滤掉开局期从 10.0 正常回落到 5.2 的波动（没有创新低时不触发）。
  - 只在健康分真正恶化且审计已标记 P1 问题时才阻断。
- **缺点**：需要维护历史最低分状态；对"缓慢持续下跌"不敏感。
- **推荐**: **首选方案**。

### 方案 C：章节窗口延迟启用
- **做法**：`health_low_absolute_score_halt` 仅在 `chapter_number >= N`（如 N=20 或 30）后启用。
- **优点**：避开开局期波动。
- **缺点**：硬编码章节号，跨项目/体裁不通用；后段若出现健康分从高位回落也会误伤。
- **适用**: 临时补丁，不建议作为长期方案。

### 方案 D：改用相对百分位跌幅
- **做法**：不比较绝对 score 差值，而比较"当前 score 处于历史分布的哪个百分位"，如低于 5th percentile 触发。
- **优点**：比固定阈值更自适应。
- **缺点**：需要足够样本才能建立分布；开局期样本不足时不稳定。
- **适用**: 可作为 V5.2 研究方向，当前不做。

---

## 3. 推荐方案

采用 **方案 B：历史新低 + P1 同步激增**。

### 触发条件

```python
# 伪代码
score_is_new_low = current_health_score < project_min_health_score_ever
p1_anomaly = current_p1_count > anomaly_factor * mean_p1_recent_window

if score_is_new_low and p1_anomaly:
    trigger health_low_score_halt
```

### 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `score_halt_enabled` | `True` | 是否启用本规则 |
| `p1_anomaly_factor` | `1.8` | P1 计数超过近期均值多少倍视为异常 |
| `p1_audit_window` | `3` | 计算 P1 均值的近期章节窗口 |
| `min_absolute_p1` | `20` | P1 计数绝对下限，避免均值极小时的小波动 |

### 历史最低分维护

- 存储位置：`run_log` 的每章记录中保留 `min_health_score_so_far`；或存储在 `projects` 表的元数据字段。
- 更新时机：每章 audit 完成后，若当前 `health_score` 低于历史最低值则更新。
- 初始值：第一章的 `health_score` 即为初始最低值。

---

## 4. 验收标准

### 4.1 代码变更
- [ ] `src/songyan/models/gate_config.py` 更新 `GateConfig` 字段，替换或重命名 `health_low_absolute_score_halt` 为 `health_low_score_halt`（或保留旧名但改变语义）。
- [ ] `src/songyan/workflows/_gates.py` 实现"历史新低 + P1 异常"判断逻辑。
- [ ] 若需要，`src/songyan/workflows/_run_logger.py` 或 repository 层增加 `min_health_score_so_far` 记录。

### 4.2 测试覆盖（新增 `tests/test_127_gate_score_halt.py`）
- [ ] **Case 1**：开局期 score 从 10.0 → 5.2，P1 正常（< 阈值）→ **不触发**。
- [ ] **Case 2**：score 创新低，但 P1 正常 → **不触发**。
- [ ] **Case 3**：score 未创新低，但 P1 激增 → **不触发**（应由 `health_low_p1_halt` 处理）。
- [ ] **Case 4**：score 创新低 **且** P1 激增 → **触发**。
- [ ] **Case 5**：`score_halt_enabled=False` 时，Case 4 也不触发。
- [ ] **Case 6**：历史最低分在运行过程中正确更新。

### 4.3 回归验证
- [ ] 全量 pytest 通过：`1828 passed, 1 xfailed, 2 warnings` 基线保持或更优。
- [ ] `ruff check src/ tests/ scripts/` 通过。
- [ ] Task 125 已有测试（`test_125_gate_thresholds.py`）若包含原 `absolute_score_halt` 测试，需同步更新语义或移除。

### 4.4 实跑验证（可选，可与 Task 128 合并）
- [ ] 在 Task 128 的 Ch1–Ch50 enforce 实跑中，确认 score halt 规则不再在 Ch1–Ch20 误触发。

---

## 5. 依赖关系

```
Task 125 阈值调优 ──┐
Task 126 小窗口验证 ┤──► Task 127 重构 score halt ──┬──► Task 128 Ch1-Ch50 enforce 验证
                    │                              │
                    └─ 已知 score_drop 误触发 ──────┘
```

---

## 6. 风险与回滚

| 风险 | 影响 | 缓解 |
|------|------|------|
| 复合条件过严，漏掉真实崩溃 | P1 风险 | 保留 `health_low_p1_halt` 与 `health_low_streak_halt` 作为保底；本规则作为辅助 |
| 复合条件仍误触发 | 中断长跑 | 默认仍 `gate_mode="observe"`，Task 128/129 验证后再决定是否 enforce |
| 历史最低分状态丢失/错误 | gate 行为异常 | 新增单测覆盖更新逻辑；运行日志中保留可观测字段 |
| 破坏现有 gate 配置序列化 | 向后兼容 | 若重命名字段，保留旧字段别名或迁移逻辑 |

---

## 7. 交付物

- `archive/v5/tasks/127-health-low-score-halt-refactor-DONE.md`
- 代码改动：`src/songyan/models/gate_config.py`、`src/songyan/workflows/_gates.py`、相关 logger/repository
- 新增测试：`tests/test_127_gate_score_halt.py`
- 更新测试：`tests/test_125_gate_thresholds.py`（如需）
- 全量 pytest / ruff 通过记录
