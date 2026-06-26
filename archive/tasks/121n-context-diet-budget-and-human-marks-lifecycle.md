# Task 121n: Context Diet 2.0 预算调整与 human_marks 生命周期优化

> **日期**: 2026-06-22
> **类型**: V5.1 preflight / 上下文稳定性
> **状态**: ✅ 已完成（2026-06-22）
> **验证**: `pytest tests/ -q` 1731 passed, `ruff check src/ tests/` 通过
> **前置**: Task 121l `run-08689f68` 暴露 Ch10-Ch12 连续 ContextEmergency，根因为上下文输入膨胀速度持续超过预算天花板增长速度。

---

## 1. 任务边界

本任务目标是从配置侧削减中段（Ch8–Ch20）ContextEmergency 的触发频率，为下一次 Ch1-Ch150 full single-run 提供稳定上下文基线。

聚焦：

- 调整 `DEFAULT_BASE_BUDGET` 和/或 `BUDGET_INCREMENT_PER_CHAPTER`，使中段预算能容纳正常的设定/伏笔/剧情累积。
- 优化 `human_marks` 生命周期清理策略，降低中段固定 overhead。
- 监控 `budget_used_before_emergency`、`soft_references`、`recent_plot`、`foreshadowing` 的滚动趋势。

不做：

- 不修改 Context Diet 2.0 的四组件架构（TemporalCompressor、CharacterFocalDecay、SettingEvaporator、BudgetHardCeiling）。
- 不修改 settlement 提取算法或 writer 生成逻辑。
- 不处理 Prompt 文风问题（归 Task 121k）。

---

## 2. 事实入口

| 项 | 值 |
|----|----|
| 上一轮任务 | `tasks/121l-context-emergency-autohalt-review.md` |
| 关键证据 | `run-08689f68` Ch10-Ch12 `budget_breakdown` |
| 代码 | `src/songyan/agents/context_manager/_assemblers.py` |
| 代码 | `src/songyan/db/human_mark_repo.py` |
| 代码 | `src/songyan/db/lifecycle_cleaners.py` |

---

## 3. 问题复盘

### 3.1 预算天花板增长过慢

当前公式（`_assemblers.py` L99-112）：

```python
DEFAULT_BASE_BUDGET: int = 8000
BUDGET_INCREMENT_PER_CHAPTER: int = 80
```

| 章节 | 预算 | 组装前 tokens | budget_used_before |
|------|------|---------------|--------------------|
| Ch10 | 8800 | 13808 | 1.569 |
| Ch11 | 8880 | 14203 | 1.599 |
| Ch12 | 8960 | 14592 | 1.629 |

每章仅 +80 tokens，而中段正常的 `soft_references`（3700–3900）、`recent_plot`（1300–1800）、`foreshadowing`（1000+）持续净增长。即使经过 partition budget 和 prune，原始输入已稳定超出预算 55%–63%，导致每章都必须触发 emergency。

### 3.2 human_marks 固定死重

Ch10-Ch12 的 `human_marks` 固定为 1506 tokens。日志显示 lifecycle cleanup 对 human_marks 的 transitions=0，说明这些 marks 全部因 `priority >= 8` 或 `created_at_chapter` 未过窗口而未被清理。

`archive_stale` 窗口为 10 章，`archive_very_stale` 窗口为 20 章。对于新创建的项目，早期大量 marks 会在 Ch1-Ch9 持续累积，直到 Ch11+ 才开始 dormancy，Ch21+ 才开始 archive。这导致中段（Ch10-Ch20）的 human_marks 处于峰值。

---

## 4. 执行步骤

### Step A: 预算参数调整

**方案 A1（推荐）：提高增量**

将 `BUDGET_INCREMENT_PER_CHAPTER` 从 80 提高到 200–300，使中段预算与输入膨胀匹配：

```python
BUDGET_INCREMENT_PER_CHAPTER: int = 250
# Ch10 预算 = 8000 + 2500 = 10500
# Ch12 预算 = 8000 + 3000 = 11000
```

**方案 A2（备选）：提高基础预算**

将 `DEFAULT_BASE_BUDGET` 提高到 10000：

```python
DEFAULT_BASE_BUDGET: int = 10000
```

**决策建议**：优先尝试 A1（增量 250）。若调整后 `budget_used_before_emergency` 仍 > 1.15，再叠加 A2。

### Step B: human_marks 生命周期优化

**方案 B1：缩短 stale 窗口**

将 `archive_stale` 窗口从 10 章缩短到 5 或 6 章：

```python
# human_mark_repo.py L142
window: int = 6,
```

这样 Ch7 创建的 marks 在 Ch13 就会被标记为 dormant，减少中段峰值。

**方案 B2：限制 priority>=8 的 marks 加载体量**

当前 `priority >= 8` 的 marks 永久不被 archive。如果这类 marks 数量过多，应考虑：
- 在 `context_manager` 组装时，对 priority>=8 的 marks 也设置一个加载上限（如最多 800 tokens）。
- 或引入 `"critical"` 与 `"high"` 分级，仅 `"critical"`（priority=10）永久保留，"high"（priority=8-9）窗口缩短到 15 章。

**决策建议**：优先执行 B1（窗口 6 章），监控效果。若 human_marks 仍 > 1200 tokens，再执行 B2。

### Step C: 监控指标

在 `run-08689f68` 的日志基础上，建立中段上下文压力基线：

| 指标 | 当前值（Ch12） | 目标值 |
|------|----------------|--------|
| `budget_used_before_emergency` | 1.629 | < 1.15 |
| `human_marks` | 1506 | < 800 |
| `soft_references`（prune 后） | 1908 | < 1500 |
| `recent_plot`（partition 后） | 1777 | < 1500 |

### Step D: 代码检查

```powershell
python -m pytest tests/ -q
ruff check src/ tests/
```

---

## 5. 验收标准

- [ ] `BUDGET_INCREMENT_PER_CHAPTER` 调整为 250（或经实验验证的其他值）。
- [ ] `human_marks` 的 `archive_stale` 窗口缩短到 6 章（或经实验验证的其他值）。
- [ ] 在干净的 Ch1-Ch18 聚焦验证中，Ch10-Ch12 的 `budget_used_before_emergency` 降至 1.15 以下。
- [ ] Ch10-Ch12 不再连续触发 ContextEmergency，或触发后 `budget_used_after_emergency` 稳定在 0.75–0.85 区间。
- [ ] `pytest` 全量通过，`ruff` 无报错。

---

## 6. 后续

- Task 121n 完成后，与 Task 121m（QG false 阻断 + 元标记清理）共同进入 Task 121o（Ch1-Ch18 聚焦验证重跑）。
- 若 Ch1-Ch18 验证通过，创建新 `run_id` 执行 Ch1-Ch150 full single-run。
