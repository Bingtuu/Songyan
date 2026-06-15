# Task 090a: 字数达标率修复计划（含端到端验证）

> **Phase**: V4.0 Phase B — Agent 约束硬化
> **优先级**: P0
> **依赖**: Task 088, 089（字数约束全部硬化）
> **预计工作量**: 中（3 天）
> **状态**: 🔄 修复完成，端到端验证中

---

## Goal

修复字数达标率系统性失效问题。基线运行显示达标率仅 36.8%（7/19），需通过阈值收紧 + bug 修复提升到 >60%。

## 执行过程

### Phase 1 — 基线运行（已完成）

| 指标 | 值 |
|------|-----|
| 完成章节 | 19/19 (Ch2-Ch20) |
| 达标率（±20%）| **36.8% (7/19)** |
| 平均字数 | 3742 |
| 字数范围 | 2391 ~ 5068 |
| 平均 budget_used | 1.146 |
| Writer 截断次数 | 仅 3 次 |

### Phase 2 — 根因分析（已完成）

发现 3 类根因：

1. **技术缺陷**: `MIN_CONTENT_RATIO` 在 `revision_handler/__init__.py` 的 `run_revision()` 内部定义，导致 `UnboundLocalError`。segmented revision 成功后总是 fallback 到 patch_engine，增加一次冗余 LLM 调用。
2. **设计缺陷**: Writer 阈值 1.50x/0.70x 与 ±20% 达标标准严重脱节，产生 1.2x~1.5x 灰色地带（7/9 超标章节落在此区间）。
3. **决策错误**: Task 088/089 中"与 RevisionHandler 对齐"的伪论证阻止了阈值收紧，错误认为两阶段存在"耦合循环"。

### Phase 3 — 修复实施（已完成）

| 修复 | 文件 | 变更 |
|------|------|------|
| 修复1 — MIN_CONTENT_RATIO 作用域 | `revision_handler/__init__.py` | 从 `run_revision()` 内部移到模块顶部常量 |
| 修复2 — Writer 阈值收紧 | `writer.py` | 1.50x/0.70x → **1.20x/0.80x** |
| 修复3 — RevisionHandler 阈值收紧 | `_segmented_revision.py` | 1.50x/0.70x → **1.25x/0.75x** |
| 修复4 — 测试更新 | `test_076_word_count_truncation.py` | 硬编码 1.50 → 1.20 |
| 修复4 — 测试更新 | `test_088_revision_word_limit.py` | 阈值和场景数据更新 |

**阈值设计 rationale**: Writer 1.2x/0.8x（直接控制初稿，严格）+ RevisionHandler 1.25x/0.75x（修复后略宽松，避免过度截断）。两阶段串行，不存在"耦合循环"。

### Phase 4 — 端到端验证（进行中）

新阈值端到端运行：`evals/output/task_090a_scifi_webnovel_tightened/`

**Ch2 观察**:
- Writer 初稿 2931 字（目标 3200，未触发截断）
- RevisionHandler 3125 字（未触发字数约束，**segmented 成功运行无 fallback**）
- 回滚机制正常：第二轮修订劣化（issues 8→10, score 8.16→7.94），自动回滚到 v2
- 最终 accept：3125 字，budget 0.977，**达标** ✅

**Ch3 观察**:
- Writer 初稿 2851 字（目标 3500，偏差 -19%）
- `word_count_mismatch` 警告触发，RuleAuditor `word_count_ok=False`
- 说明新阈值下偏低初稿会被更严格检测

## Context

Phase B 是 Agent 约束硬化。本 Task 用 Ch1-Ch20 短程验证快速确认字数约束生效，为 Task 091 的长程验证（Ch21-Ch50）提供信心。

## In Scope（必须完成）

- [ ] **Ch1-Ch20 端到端跑通**：使用真实 LLM 或 Mock 模式
- [ ] **字数达标率统计**：±20% 范围内章节占比 > 60%
- [ ] **V3.x 基线对比**：
  - budget_used 变化趋势
  - 字数分布变化
  - revision 触发率变化
- [ ] **异常分析**：任何字数超标/低于下限的章节，分析根因

## Out of Scope（明确不做）

- Ch21+ 验证（Task 091）
- 任何代码修改（Phase B 代码已完成）
- 动态预算验证（Task 087 已做）

## 验收标准（Acceptance Criteria）

- [ ] Ch1-Ch20 端到端跑通
- [ ] 字数达标率（±20%）> 60%
- [ ] 与 V3.x 基线对比报告（budget_used、字数、revision 触发率）
- [ ] 生成了 `tasks/090-phase-b-ch1-ch20-e2e-DONE.md`

## 参考

- `docs/v4.0-tech-plan.md` — 第 7.2 节
- `tasks/088-revision-word-limit.md`
- `tasks/089-writer-truncation-tighten.md`
