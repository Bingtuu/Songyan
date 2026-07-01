# Task 062: 端到端重跑验证 — Ch31-Ch40

> **Phase**: V3.0 Layer 2 — 核心验证层（闭环）
> **优先级**: P0
> **依赖**: Task 059, Task 060（确保监控数据完整 + 字数检测生效）
> **预计工作量**: 大（生成等待 2-5 小时 + 分析 1 小时）

---

## Goal

用含 058c+058d+059+060 全部修复的代码，在 `orbital_horror_058b` 项目上继续生成 Ch31-Ch40，对比 058b 基线（Ch2-Ch30）验证 10 项修复的实际效果，完成 V3.0 闭环。

## Context

058c/058d 的 8 项修复 + 059/060 的 2 项修复全部通过单元测试验证，但**从未在真实 LLM 运行中被端到端验证过**。这是 V3.0 闭环的最后一块拼图。

### 058b 基线数据（Ch2-Ch30，29 章）

| 指标 | 基线值 |
|------|--------|
| 总字数 | 130,356 |
| 平均字数 | 4,495 |
| 字数 CV | 17.2% |
| 字数超标率（>120% 目标） | 13/29 = 45% |
| 平均 revision 轮次 | 1.83 |
| 0 轮通过率 | 0% (0/29) |
| 2 轮通过率 | 83% (24/29) |
| 平均 RuleAudit 得分 | 0.95 |
| Ch30 budget_used | 4.29x |
| new_issues_introduced 检测 | 0（硬编码盲区） |
| continuity_health_score | 全 null |
| content_preservation_ratio | 全 null |

### 待验证的 10 项修复

| # | 修复 | Task | 预期影响 |
|---|------|------|---------|
| 1 | Writer Prompt 字数威慑 | 058c | 字数超标率降低 |
| 2 | RuleAuditor `word_count_ratio` 检测 | 058c | 超标章触发 revision |
| 3 | BudgetPruner 终止条件修复 | 058c | prune 后达标检测 |
| 4 | 不出场角色过滤 | 058c | context tokens -30~50% |
| 5 | obligations 上限 10 条 | 058c | 硬约束不膨胀 |
| 6 | key_events / characters_appeared 截断 | 058c | recent_plot 瘦身 |
| 7 | `_detect_new_issues` 4 维检测 | 058d | 首次检测到 revision 引入的新问题 |
| 8 | `merge_reviews` 合并 previous_new_issues | 058d | Round 2 拿到完整 issue 列表 |
| 9 | JSONL error_stage 补录 | 059 | error 条目有阶段名 |
| 10 | 字数阈值 120% + violation 写入验证 | 060 | 实际超标章被标记 |

## In Scope（必须完成）

### 1. 运行前准备
- [ ] 确认 059、060 代码已合并到当前工作树
- [ ] 确认 `orbital_horror_058b` 项目的 Ch1-Ch30 在 DB 中数据完整
- [ ] 设置 `chapter_range=(31, 40)`，`auto_confirm=True`，`continuity_health_threshold=7.0`
- [ ] 运行方式确认：方案 B（`phase2_graph.run_project_pipeline`）以获得 JSONL 日志

### 2. 运行与监控
- [ ] 生成 Ch31-Ch40，10 章连续运行
- [ ] 实时检查 `logs/chapter_runs/{run_id}.jsonl` 追加
- [ ] 记录每章 `duration_sec`、`error_stage`、`settlement_needs_human_review`

### 3. 指标对比分析

| 验证项 | 基线 | 目标 | 度量方式 |
|--------|------|------|---------|
| 字数 CV | 17.2% | **<12%** | word_count 标准差/均值 |
| 字数超标率（>120%目标） | 45% | **<20%** | word_count_ratio >= 1.20 的章数/总章数 |
| 平均 revision 轮次 | 1.83 | **<1.5** | revision_rounds 均值 |
| 0 轮通过率 | 0% | **>10%** | revision_rounds=0 的章数/总章数 |
| budget_used (Ch35+) | ~4.1x | **<3.0x** | estimated_tokens / budget_tokens |
| new_issues_introduced 率 | 0（盲区） | 记录基线 | revision 后检测到新问题的章数 |
| continuity_health_score | 全 null | **全部有值** | 非 null 比例 |
| content_preservation_ratio | 全 null | **全部有值** | 非 null 比例 |
| error_stage 覆盖率 | 18% (7/38) | **100%** | 有 error_stage 的 error 条目/总 error 条目 |

### 4. 定性检查
- [ ] 抽查 Ch35、Ch40 的正文质量（是否保持 Ch1-Ch30 的水准）
- [ ] 检查是否有 new_issues_introduced 导致的新 critical issue
- [ ] 检查 settlement 完整性

### 5. 验证报告
- [ ] 输出 `docs/review/062-e2e-verification-report.md`
- [ ] 对比表列出每项修复的"基线值 → 修复后值 → 是否达标"
- [ ] 记录未达预期的项及可能原因
- [ ] 记录新发现的问题

## Out of Scope（明确不做）

- 不重跑 Ch1-Ch30（保持 058b 基线不变）
- 不修改 Prompt 模板
- 不修改 Agent 行为
- 不修复本次运行中发现的新问题（归入后续 Task）
- 不做人工盲测或质量评分

## 接口契约

```python
from songyan.workflows.phase2_graph import run_project_pipeline

result = await run_project_pipeline(
    project_id="proj-e74ef1e4",  # orbital_horror_058b
    chapter_range=(31, 40),
    mode_id="webnovel",
    auto_confirm=True,
    on_failure="retry",
    continuity_health_threshold=7.0,
)
```

## 验收标准

- [ ] Ch31-Ch40 全部 `accepted`（零崩溃）
- [ ] `docs/review/062-e2e-verification-report.md` 包含完整的前后对比表
- [ ] 至少 6/9 项指标达到目标或显著改善
- [ ] 更新了 `docs/STATUS.md`（标记 V3.0 闭环）
- [ ] 生成 `tasks/062-e2e-verification-DONE.md` 交接文件
- [ ] 产出 `projects/orbital_horror_058b/chapters/chapter_31-40.md`

## 参考文档

- `prd/v3.0-058b-review-and-recommendations.md` — 本次 Review 报告（含基线数据和行动路线）
- `docs/review/v30_layer2_runlog.jsonl` — 058b 运行日志
- `docs/review/058c_context_bloat_analysis.md` — 上下文膨胀根因分析
- `docs/review/058c_issue_type_distribution.md` — Issues 类型分布
- `docs/review/058d_validation_report.md` — 058d 验证报告
- `projects/orbital_horror_058b/` — 30 章产物 + 进度记录