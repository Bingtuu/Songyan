# Songyan 统一评分体系说明（Task 106 + Patch）

## 1. 设计目标

- **五维固定结构**：长度、预算、一致性、推动力、可读性。
- **直接简洁**：1/0 标志用于快速决策，线性评分用于细粒度比较。
- **与多 Agent 工作流配合**：评分由 `ScoreAggregator` 在 `review_merger_node` 统一聚合，向后兼容旧状态。
- **内部扩展**：后续新增子指标只放入 `DimensionScore.details`，不新增第 6 个维度。

## 2. 五维评分结构

### 2.1 维度与权重

| 维度 | 权重 | 数据来源 | 评分方式 |
|---|---|---|---|
| **length** | 0.15 | `RuleAuditResult.word_count` | 分段线性 |
| **budget** | 0.10 | `ContextPackage.budget_used` | 分段线性 |
| **coherence** | 0.30 | `LLMAuditResult.issues` | 按 issue 扣分 |
| **momentum** | 0.20 | `RuleAuditResult.hooks/punch` | 1/0 累加 |
| **readability** | 0.25 | `RuleAuditResult.ai_tell/fatigue/rhythm` | 线性扣分 |

`overall_score` 为加权平均分；若某维度未评估（`score == -1.0`，如 momentum 无 punch_points 时），自动排除该维度并重新归一化权重。

### 2.2 评分细则

#### length（长度合规）

基于 `word_count / word_count_target` 的 ratio：

| ratio 区间 | score |
|---|---|
| [0.90, 1.10] | 1.0 |
| [0.80, 0.90) 或 (1.10, 1.20] | 线性下降到 0.6 |
| [0.50, 0.80) 或 (1.20, 1.50] | 线性下降到 0.0 |
| < 0.50 或 > 1.50 | 0.0 |

`flags.length_ok = length_score >= 0.6`

#### budget（Token 成本）

| budget_used | score |
|---|---|
| <= 0.80 | 1.0 |
| (0.80, 1.00] | 线性下降到 0.0 |
| > 1.00 | 0.0 |

`flags.budget_ok = budget_score >= 0.5`

#### coherence（一致性 + 逻辑稳健）

只统计 consistency 类 issue（`WORLD_CONSISTENCY`、`CHARACTER_BEHAVIOR`、`TIMELINE`、`NEW_SETTING_UNREGISTERED`）：

| issue 等级 | 扣分 |
|---|---|
| critical | 0.40 / 个 |
| major | 0.25 / 个 |
| minor | 0.10 / 个 |

`flags.coherence_critical = critical > 0`  
`flags.coherence_major = major > 0`

#### momentum（情节推动力 + 爆点）

当 `expected_punch_count > 0` 时评估：

| 条件 | 加分 |
|---|---|
| 有 opening_hook | +0.2 |
| 有 ending_hook | +0.3 |
| punch_density_ok | +0.3 |
| emotion_switch_ok | +0.2 |

无 punch_points 时 `score = -1.0`（未评估）。  
`flags.momentum_present = score >= 0.5 or score == -1.0`

#### readability（可读性）

| 问题 | 扣分 |
|---|---|
| ai_tell_count | 0.15 / 个，上限 0.5 |
| fatigue_word_count | 0.08 / 个，上限 0.3 |
| paragraph_rhythm_score < 5.0 | (5.0 - score) * 0.05 |

`flags.readability_ok = readability_score >= 0.6`

## 3. 快速决策标志（ScoreFlags）

```python
class ScoreFlags:
    length_ok: bool = True
    budget_ok: bool = True
    coherence_critical: bool = False
    coherence_major: bool = False
    momentum_present: bool = True
    readability_ok: bool = True
```

- `has_blocking_issue` = `coherence_critical or not budget_ok`
- `needs_revision` = `coherence_critical or coherence_major`

**注意**：`needs_revision` 目前只覆盖 coherence 维度。`literary_auditor_node` 的 critical 文学观察仍独立设置 `_needs_revision`。

## 4. 工作流中的使用

### 4.1 review_merger_node

- 调用 `ScoreAggregator.aggregate()` 生成 `ChapterScoreCard`
- 使用 `score_card.flags.needs_revision` 覆盖旧判定
- **持久化**：将 `score_card` 写入 `chapter_versions.score_card`（Task 106-patch）
- **保存 best**：初稿需要 revision 时，保存 `_best_score_card` 供回滚恢复

### 4.2 反弹检测（Revision Rebound Detection）

在第 1 轮及以后 revision，若满足以下任一条件，回滚到 best_version：

1. **issues 增加 > 20%**
2. **overall_score 下降 > 0.3**（统一为 score_card 口径，Task 106-patch）
3. **任一维度下降 > 0.3**（新增维度级劣化检测，Task 106-patch）

回滚时：
- 废弃当前版本
- 恢复 `current_version_id = best_version`
- 恢复 `_score_card = _best_score_card`（避免 score_card 与 version 不匹配）

### 4.3 quality_gate_node

基于 `_score_card` 做五维检查：

```
length_ok ? pass : fail
budget_ok ? pass : fail
coherence_critical ? fail
coherence_major ? fail
momentum_present ? pass : fail
readability_ok ? pass : fail
```

无 `_score_card` 时 fallback 到原始字数检查（ratio > 1.30 或 < 0.80）。

### 4.4 human_gate_node

accept 路径透传 `_score_card` 到 settlement。

### 4.5 JSONL 日志

`ChapterRunLog.score_card` 记录：
- `overall_score`
- 五个维度分数（含 `details` 子指标）
- `flags`

## 5. 数据持久化

| 位置 | 字段 | 说明 |
|---|---|---|
| `chapter_versions` 表 | `score_card` (TEXT) | 版本级评分卡，JSON 对象 |
| `ChapterRunLog` (JSONL) | `score_card` (dict) | 运行日志中的评分快照 |
| LangGraph state | `_score_card` | 当前流转的评分卡 |
| LangGraph state | `_best_score_card` | best 版本的评分卡（回滚恢复用） |

## 6. 扩展指南

### 6.1 新增子指标（推荐）

在现有维度内部扩展，不新增维度：

```python
# 示例：在 readability.details 中增加"句式多样性"
card.readability.details["sentence_variety_score"] = 0.8
```

JSONL 日志会自动保留 `details` 中的子指标。

### 6.2 调整阈值

修改 `ScoreAggregator` 中的硬编码阈值：
- `length_ok`: `length_score >= 0.6`
- `budget_ok`: `budget_score >= 0.5`
- `readability_ok`: `readability_score >= 0.6`
- `momentum_present`: `momentum_score >= 0.5`

### 6.3 新增维度（不推荐）

若必须新增第 6 维，需同步修改：
- `ChapterScoreCard` 模型
- `ScoreAggregator._DIMENSION_WEIGHTS`
- `quality_gate_node` 检查逻辑
- `review_merger_node` 反弹检测逻辑

## 7. 变更历史

| 版本 | 变更 |
|---|---|
| Task 106 | 初始五维评分体系 |
| Task 106-patch | 1. 回滚时恢复 `_best_score_card`<br>2. 反弹检测统一使用 `score_card.overall_score`<br>3. `score_card` 持久化到 `chapter_versions`<br>4. 新增维度级劣化检测（下降 > 0.3） |
