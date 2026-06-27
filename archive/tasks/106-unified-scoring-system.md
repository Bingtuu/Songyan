# Task 106: Unified Scoring System — 统一评分体系

> **目标**: 建立直接简洁的 5 维评分体系，替代现有分散的 `overall_score` + `has_critical/major` + quality_gate 三联检，使 revision/rewrite/accept 决策统一基于同一套分数。
> **范围**: 模型定义 + 聚合器 + review_merger/quality_gate/revision_router/human_gate 适配
> **约束**: 不新增 Auditor，不新增工作流节点，不阻塞 auto_confirm

---

## 背景

当前评分分散在多个组件中：
- `RuleAuditResult`: word_count_ok, scene_count_ok, has_opening_hook, ai_tell_count...
- `LLMAuditResult`: dimension_scores, cliche_risk_score...
- `MergedReviewReport`: overall_score, has_critical, has_major, patchable_issues
- `LiteraryAuditResult`: 文学性评分（不阻塞）
- `QualityGate`: 三联检（字数、保留率、新问题）与 above 不同口径

导致的问题：
1. `review_merger` 用 `overall_score` 做反弹检测，`quality_gate` 用独立规则拦截，`revision_router` 又只看 `has_critical/major`
2. 新增检查维度需要改多处（如 Task 106 原本想加 token 成本控制，无统一入口）
3. 无法回答"这章到底哪里不行"的结构性问题

---

## 设计要点

### 1. 五维评分结构（固定不变）

| 维度 | 英文名 | 数据源 | 评分方式 | Flags |
|------|--------|--------|---------|-------|
| 长度合规 | `length` | RuleAuditResult.word_count_ratio | 线性 0~1 | `length_ok` |
| Token 成本 | `budget` | ContextPackage.budget_used | 线性 0~1 | `budget_ok` |
| 一致性+逻辑 | `coherence` | LLMAuditor issues (consistency类) | 线性 0~1 | `coherence_critical`, `coherence_major` |
| 推动力+爆点 | `momentum` | RuleAuditResult.punch_check + hooks | 线性 0~1 | `momentum_present` |
| 可读性 | `readability` | RuleAuditResult (AI腔+疲劳词+节奏) | 线性 0~1 | `readability_ok` |

- 每个维度 `score: float` 范围 **0.0 ~ 1.0**
- 每个维度配套 `flags` 为 **1/0 布尔**
- `momentum` 如果无法评估（无 punch_points）则 score = -1.0，表示 N/A

### 2. 总分计算

```
overall_score = weighted_average of valid dimensions
weights: length=0.15, budget=0.10, coherence=0.30, momentum=0.20, readability=0.25
```

若 `momentum == -1`（未评估），则重新归一化权重。

### 3. 决策映射（单一入口）

```python
# revision_router 使用 score_card
needs_revision = score_card.flags.coherence_critical or score_card.flags.coherence_major

# quality_gate 使用 score_gate（基于 score_card）
failures = score_gate.check(score_card)
# 内部统一判断：哪个维度 score < threshold

# human_gate accept 条件（auto_confirm 路径）
accept_ok = score_card.overall_score >= 0.60 and not score_card.flags.coherence_critical
```

### 4. 扩展规则

- **后续只增加维度内部的子指标**，不新增第 6 个维度
- 子指标放入 `dimension_details: dict[str, float]`，不影响主结构
- 新增评分逻辑只改 `ScoreAggregator`，不改下游决策节点

---

## 验收条件

| # | 条件 | 验证方式 |
|---|------|---------|
| 1 | `ChapterScoreCard` 模型定义完整，含 5 维度 + flags + overall_score | 单元测试 |
| 2 | `ScoreAggregator` 能从 `RuleAuditResult + LLMAuditResult + LiteraryAuditResult + ContextMetrics` 产出 `ChapterScoreCard` | 单元测试 |
| 3 | `review_merger_node` 输出 `_score_card` 到 state | 集成测试 |
| 4 | `revision_router` 基于 `_score_card.flags` 判断 `needs_revision` | 集成测试 |
| 5 | `quality_gate_node` 基于 `_score_card` 做检查，向后兼容原有 `_quality_gate_passed` | 集成测试 |
| 6 | `human_gate_node` accept 时记录 `_score_card` 到 JSONL 指标 | 检查 log_chapter_run |
| 7 | 全量回归无新增失败，ruff 无新增错误 | pytest + ruff |

---

## 改动文件清单

| 文件 | 变更 |
|------|------|
| `src/songyan/models/score_card.py` | **新增** ChapterScoreCard, ScoreFlags, DimensionScore |
| `src/songyan/evals/score_aggregator.py` | **新增** ScoreAggregator 聚合逻辑 |
| `src/songyan/models/__init__.py` | 导出 ScoreCard 模型 |
| `src/songyan/workflows/review_merger.py` | 调用 ScoreAggregator，输出 score_card |
| `src/songyan/workflows/_nodes.py` | review_merger_node 透传 score_card；revision_router / quality_gate_node / human_gate_node 适配 |
| `src/songyan/workflows/phase1_graph.py` | State 增加 `_score_card` 字段 |
| `src/songyan/workflows/_run_logger.py` | log_chapter_run 收集 score_card 维度分数 |
| `tests/test_106_scoring_system.py` | **新增** 单元测试 |

---

## 不改的内容

- 不修改 `RuleAuditor` / `LLMAuditor` / `LiteraryAuditor` 的内部检测逻辑
- 不修改 `RevisionHandler` 的 patch 逻辑
- 不修改 `Writer` 的生成逻辑
- 不新增工作流节点
- 不引入人工阻塞节点
