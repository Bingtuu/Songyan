# Task 106-DONE: Unified Scoring System — 统一评分体系

> 完成日期: 2026-06-14
> 测试: 1507 passed, 4 skipped, 2 xfailed, 3 xpassed（无新增失败）
> ruff: 无新增错误（178 pre-existing）

---

## 做了什么

建立直接简洁的 5 维评分体系，将分散在 `RuleAuditResult`、`LLMAuditResult`、`MergedReviewReport`、`QualityGate` 中的评分逻辑统一为单一入口 `ChapterScoreCard`。

### 核心设计

| 维度 | 权重 | 数据源 | 评分方式 |
|------|------|--------|---------|
| length | 0.15 | RuleAuditResult.word_count_ratio | 线性 0~1，分区间下降 |
| budget | 0.10 | ContextPackage.budget_used | 线性 0~1 |
| coherence | 0.30 | LLMAuditor consistency 类 issues | 按 severity 扣分 |
| momentum | 0.20 | PunchCheck + hooks | 0~1 累加；-1 表示未评估 |
| readability | 0.25 | AI腔 + 疲劳词 + 段落节奏 | 反向扣分 |

- `ScoreFlags` 提供 1/0 布尔决策：`_needs_revision`、`_quality_gate_passed`、`has_blocking_issue`
- `overall_score` 加权聚合，未评估维度自动排除并归一化权重

### 改动文件

| 文件 | 变更 |
|------|------|
| `src/songyan/models/score_card.py` | **新增** ChapterScoreCard, DimensionScore, ScoreFlags |
| `src/songyan/evals/score_aggregator.py` | **新增** ScoreAggregator 聚合逻辑 |
| `src/songyan/models/__init__.py` | 导出新模型 |
| `src/songyan/models/run_log.py` | ChapterRunLog 增加 `score_card` 字段 |
| `src/songyan/workflows/review_merger.py` | 未改动（保持向后兼容） |
| `src/songyan/workflows/_nodes.py` | review_merger_node 聚合 score_card；quality_gate_node 基于 score_card 检查（fallback 到原有字数检查）；human_gate_node accept 时透传 score_card |
| `src/songyan/workflows/phase1_graph.py` | Phase1State / initial_state 增加 `_score_card` |
| `src/songyan/workflows/_run_logger.py` | build_chapter_run_log 提取 score_card 维度分数到 JSONL |
| `tests/test_106_scoring_system.py` | **新增** 24 个单元测试 |
| `tasks/106-unified-scoring-system.md` | 规格文档 |

### 关键决策

1. **向后兼容**: `quality_gate_node` 在无 `_score_card` 时回退到原有字数检查逻辑，避免破坏已有测试和旧 state。
2. **不新增 Auditor/节点**: 评分逻辑集中在 `ScoreAggregator`，不触碰 Writer/RevisionHandler/Auditor 内部。
3. **不阻塞 auto_confirm**: accept 条件仍由 `human_gate_node` 控制，score_card 只提供结构化指标。
4. **扩展规则**: 后续只增加 `dimension_details` 中的子指标，不新增第 6 个维度。

---

## 验证结果

### 单元测试（Task 106）
```bash
pytest tests/test_106_scoring_system.py -v
# 24 passed
```

### 全量回归
```bash
pytest tests/ -q
# 1507 passed, 4 skipped, 2 xfailed, 3 xpassed
```

### ruff
```bash
ruff check src/ tests/
# 无新增错误（178 pre-existing）
```

---

## 已知限制

1. **LiteraryAuditor 未接入主评分**: `literary_result` 参数已预留，当前只把 `literary_quality_score` 放入 `readability.details`，不影响主 score。后续可在 `readability` 维度内部增加子指标权重。
2. **Momentum 未评估时默认通过**: `momentum_present=True` 当 `expected_punch_count=0`，这是合理的（无爆点要求时不扣分）。
3. **Coherence 只覆盖 4 个 consistency 类别**: `WORLD_CONSISTENCY`、`CHARACTER_BEHAVIOR`、`TIMELINE`、`NEW_SETTING_UNREGISTERED`。其他 issue 类别（如 `NARRATIVE_HOOK`）归入各自维度或通过 RuleAudit 处理。
4. **budget_used 依赖 ContextPackage**: 如果 `context_package` 未写入 state（如某些旧流程），`budget` 维度会 fallback 到 `budget_used=0` → score=1.0，不算劣化。
