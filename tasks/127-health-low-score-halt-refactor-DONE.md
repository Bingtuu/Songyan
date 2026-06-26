# Task 127: 重构 `health_low_absolute_score_halt` — DONE

> **类型**: 工程修复 / 阈值调优  
> **日期**: 2026-06-26  
> **前置**: Task 125（阈值调优）、Task 126（enforce 小窗口验证）  
> **结论**: 已采用 **方案 B：历史新低 + P1 同步激增** 复合条件，解决开局期误触发问题。

---

## 1. 问题回顾

Task 126 在 `run-13bb5303` 上以 `gate_mode="enforce"` 跑 Ch1–Ch20 时发现：

- `health_low_absolute_score_halt` 配置为 `score_drop >= 2.0` 时，在 **Ch6** 误触发。
- 原因：新项目开局期 `health_score` 从初始高值 10.0 正常回落至 5.2，相对跌幅达到 4.8，远超阈值。
- Task 126 临时禁用该子规则，本任务给出长期稳定的重构方案。

---

## 2. 采用方案

**方案 B：复合条件——"历史新低 + P1 同步激增"**

### 触发条件

```python
score_is_new_low = current_health_score < project_min_health_score_ever
p1_anomaly = current_p1_count > anomaly_factor * median_p1_recent_window

if score_is_new_low and p1_anomaly:
    trigger health_low_score_halt
```

### 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `health_low_score_halt_enabled` | `False` | 是否启用本规则 |
| `health_low_score_halt_anomaly_factor` | `1.8` | P1 计数超过近期中位数多少倍视为异常 |
| `health_low_score_halt_window` | `3` | 计算 P1 近期中位数的审计点窗口 |
| `health_low_score_halt_min_p1` | `20` | P1 计数绝对下限，避免均值极小时的小波动 |

---

## 3. 代码变更

### 3.1 `src/songyan/models/gate_config.py`

- 移除字段：`health_low_absolute_score_halt`、`health_low_absolute_score_threshold`、`health_low_score_drop_threshold`
- 新增字段：
  - `health_low_score_halt_enabled`
  - `health_low_score_halt_window`
  - `health_low_score_halt_min_p1`
  - `health_low_score_halt_anomaly_factor`

### 3.2 `src/songyan/workflows/_gates.py`

- `check_health_low_single_gate` 返回三元组 `(triggered, reasons, updated_min_health_score)`
- 实现复合条件判断：score 创历史新低 **且** P1 超过近期中位数倍数
- `evaluate_all_gates` 透传 `min_health_score_so_far` 并返回更新后的最低分

### 3.3 `src/songyan/workflows/phase2_graph.py`

- `project_pipeline` 维护 `_min_health_score_so_far` 状态
- 每章运行后通过 `chapter_result["updated_min_health_score"]` 更新
- `_run_single_chapter` 接收并透传 `min_health_score_so_far`

### 3.4 配套脚本与测试

- `scripts/analyze_124_gate_impact.py`：将 `health_low_absolute_score_halt` 候选配置重命名为 `health_low_score_halt`，并维护 `min_health_score_so_far`
- `scripts/run_126_enforce_validation.py`：更新为 `health_low_score_halt_enabled=False`
- `tests/test_123_gates.py`：更新字段名与解包方式
- `tests/test_125_gate_thresholds.py`：移除旧的 score_drop 测试，改为 Task 127 复合条件测试
- `tests/test_124_gate_impact.py`：更新规则名与测试数据
- `tests/test_127_gate_score_halt.py`：新增 8 个单测覆盖全部 case

---

## 4. 测试覆盖

新增 `tests/test_127_gate_score_halt.py`，覆盖：

| Case | 场景 | 期望 |
|------|------|------|
| 1 | 开局期 score 10.0 → 5.2，P1 正常 | 不触发 |
| 2 | score 创新低，P1 正常 | 不触发 |
| 3 | score 未创新低，P1 激增 | 不触发 |
| 4 | score 创新低 **且** P1 激增 | 触发 |
| 5 | `health_low_score_halt_enabled=False` | 不触发 |
| 6 | 历史最低分跨调用正确更新 | 通过 |
| 边界 | `previous_p1_counts` 不足窗口 | 使用可用数据 |
| 集成 | `evaluate_all_gates` 正确返回 `updated_min_health_score` | 通过 |

---

## 5. 验证结果

### 5.1 全量 pytest

```text
1842 passed, 2 skipped, 1 xfailed
```

- 基线（STATUS.md）: `1828 passed, 1 xfailed, 2 warnings`
- 新增 14 个测试：8 个来自 `test_127_gate_score_halt.py`，6 个来自旧测试重构与补充
- `1 xfailed` 仍为已知非阻断项

### 5.2 ruff

```text
ruff check src/ tests/          # All checks passed!
ruff check scripts/analyze_124_gate_impact.py scripts/run_126_enforce_validation.py  # All checks passed!
```

> 注：`scripts/` 目录存在历史遗留 lint 问题（非本次改动引入），本次修改的两个脚本已通过检查。

---

## 6. 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| 复合条件过严，漏掉真实崩溃 | P1 风险 | 保留 `health_low_p1_halt` 与 `health_low_streak_halt` 作为保底 |
| 复合条件仍误触发 | 中断长跑 | 默认 `health_low_score_halt_enabled=False`，Task 128/129 验证后再决定是否 enforce |
| 历史最低分状态丢失 | gate 行为异常 | 每章通过返回值更新，运行日志中保留可观测字段 |
| 破坏旧配置序列化 | 向后兼容 | 旧字段已移除，相关脚本与测试已同步更新 |

---

## 7. 交付物

- [x] `tasks/127-health-low-score-halt-refactor-DONE.md`（本文档）
- [x] `src/songyan/models/gate_config.py`
- [x] `src/songyan/workflows/_gates.py`
- [x] `src/songyan/workflows/phase2_graph.py`
- [x] `scripts/analyze_124_gate_impact.py`
- [x] `scripts/run_126_enforce_validation.py`
- [x] `tests/test_127_gate_score_halt.py`
- [x] 更新 `tests/test_123_gates.py`
- [x] 更新 `tests/test_125_gate_thresholds.py`
- [x] 更新 `tests/test_124_gate_impact.py`
- [x] 全量 pytest / ruff 通过记录

---

## 8. 下一步

- **Task 128**: 在 enforce 模式下验证 Ch1–Ch50，确认 score halt 不再在开局期误伤。
- **Task 129**: 基于验证证据决定 `gate_mode` 默认值。
- **Task 130**: 归档过时规划稿，更新文档索引与状态板。
