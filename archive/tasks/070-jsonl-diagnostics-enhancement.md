# Task 070: JSONL 诊断增强

> **Phase**: V3.1 — 质量跃迁
> **优先级**: P2
> **依赖**: 无
> **预计工作量**: 小（~3 小时）

---

## Goal

增强 JSONL 运行日志的诊断价值：新增 `_metrics_version` 字段区分 null 原因，补录 `error_stage` 全链路阶段名。

## Context

058b 运行中暴露了 JSONL 诊断的两个盲区：

1. **metrics null 无法追溯原因**：`continuity_health_score` 和 `content_preservation_ratio` 在 058b runlog 中全为 null，原因是 058c 修复在 058b 运行之后。但分析时无法区分"null 因为版本不支持"和"null 因为采集失败"。

2. **error_stage 覆盖率低**：38 条 error 条目中仅 7 条有明确的 `error_stage`，其余 31 条为空字符串。空的 `error_stage` 无法用于根因分析。

## In Scope（必须完成）

### 7.1 `_metrics_version` 字段

- [ ] 在 JSONL 日志的每条记录中增加 `"_metrics_version": "v1"`（或对应版本）
- [ ] 版本号定义在 `src/songyan/models/run_log.py` 中作为常量
- [ ] 确保新旧版本混合的 runlog 可被正确解析

### 7.2 `error_stage` 全链路补录

- [ ] 在 `phase1_graph.py` 的各节点入口/出口增加当前阶段名记录
- [ ] 在 `phase2_graph.py` 的 `_run_single_chapter` 异常捕获时记录当前阶段名
- [ ] 确保所有 pipeline 阶段（writer, rule_auditor, llm_auditor, review_merger, revision_handler, settlement_extractor, summary_writer）都有明确的 stage 名

## Out of Scope（明确不做）

- 不改 JSONL schema 的整体结构
- 不增加新的 metrics 采集（只增强已有字段的可追溯性）
- 不做历史 runlog 的回填

## 接口契约

```python
# src/songyan/models/run_log.py

METRICS_VERSION = "v3.1"  # 每次新增/修改 metrics 时递增

class ChapterRunLog(BaseModel):
    # ... 现有字段 ...
    _metrics_version: str = METRICS_VERSION
    error_stage: str = ""  # 如 "writer", "rule_auditor", "settlement_extractor"
```

## Stage 命名规范

| Stage 名 | 对应节点 |
|----------|----------|
| `writer` | Writer 生成初稿 |
| `rule_auditor` | RuleAuditor 代码检测 |
| `llm_auditor` | LLMAuditor 语义审查 |
| `review_merger` | ReviewMerger 合并结果 |
| `revision_handler` | RevisionHandler 自动修订 |
| `settlement_extractor` | SettlementExtractor 状态结算 |
| `summary_writer` | SummaryWriter 摘要生成 |
| `context_manager` | ContextManager 上下文加载 |
| `creative_director` | CreativeDirector 生成 Brief |
| `goal_planner` | GoalPlanner 规划目标 |

## 测试要求

- [ ] 正常流程的 JSONL 记录包含 `"_metrics_version": "v3.1"`
- [ ] Writer 节点抛异常时，`error_stage="writer"`
- [ ] Settlement 节点抛异常时，`error_stage="settlement_extractor"`
- [ ] 非预期异常（如未知节点）时，`error_stage="unknown"`
- [ ] 现有 JSONL 解析逻辑向后兼容（无 `_metrics_version` 的记录仍可解析）

## 验收标准

- [ ] `pytest tests/test_run_logger.py -v` 全部通过 + 新增测试通过
- [ ] 模拟 3 个不同阶段的 error，确认 `error_stage` 正确
- [ ] `docs/STATUS.md` 更新
- [ ] 生成 `tasks/070-jsonl-diagnostics-enhancement-DONE.md`

## 参考文档

- `src/songyan/models/run_log.py` — RunLog 模型
- `src/songyan/workflows/phase2_graph.py` — `_run_single_chapter` 异常捕获
- `tasks/059-jsonl-diagnostics-DONE.md` — 059 已完成的基础诊断
