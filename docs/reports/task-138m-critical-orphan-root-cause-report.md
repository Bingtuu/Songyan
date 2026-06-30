# Task 138m：Ch21-Ch30 Critical Orphan 根因分析与 V5.2 边界决策报告

> **Run**: `run-6f2a10d3`  
> **Project ID**: `3bef1af8d54d4d0e887658516e1ed350`  
> **Rehearsal DB**: `.tmp/task138k_ch1_ch30_rehearsal_20260629.db`  
> **分析日期**: 2026-06-29  
> **前置报告**: `docs/reports/task-138k-long-window-rehearsal-report.md`

## 执行摘要

Task 138k 的 Ch1-Ch30 长窗口 rehearsal 在 Ch30 留下 **35 个 P1 critical orphan**，health 被钉在 3.0。
本报告对其逐条追踪来源与机制覆盖后，得到以下核心结论：

- **77%（27/35）是 Ch20 及之后新引入的 critical 设定，且在引入后 1 章内即被丢弃**；它们多数因为 setting_key/描述中含 `核心/锚/anchor/core` 等关键词，被 `_infer_setting_category` 自动标为 critical。
- **74%（26/35）从未获得 continuity_auditor 的 human_mark 提示**，原因是 `_generate_constraints` 每次 audit 仅取前 `MAX_ORPHANED=8` 个 orphan，且单章 unresolved human_mark 上限为 20；后续 audit 中，老 orphan 被新 orphan 挤出提示队列。
- **100%（35/35）都被 `_load_critical_mandatory_references` 加载进了 Writer 的 `mandatory_references`**；但该列表无上限，Ch30 时达到 43 条，导致 Writer 在长列表下选择性忽略。
- **26%（9/35）既有 continuity human_mark 又有 mandatory_reference，仍被 Writer 忽略**，说明仅靠提示/注入不足以保证回收。
- 没有证据支持 `recycled_but_forgotten_again`：35 条 P1 orphan 中 resolved human_mark 数为 0。

## 数据摘要

Ch30 ContinuityReport 构成（来自 `continuity_reports`）：

| 指标 | 数值 |
|------|------|
| overall_health_score | 3.0 |
| orphaned_settings 总数 | 52 |
| — critical（P1） | 35 |
| — background（P3） | 9 |
| — technical（P3） | 8 |
| forgotten_items | 1 |
| state_mismatches | 0 |
| overdue_foreshadowings | 0 |
| 报告 P1 / P2 / P3 | 35 / 0 / 18 |

`mandatory_references` 每章加载量（来自 `context_snapshots.payload`）：

| 章节 | MR 条数 |
|------|--------|
| 16 | 7 |
| 17 | 5 |
| 18 | 2 |
| 19 | 4 |
| 20 | 11 |
| 21 | 11 |
| 22 | 12 |
| 23 | 10 |
| 24 | 8 |
| 25 | 25 |
| 26 | 30 |
| 27 | 33 |
| 28 | 39 |
| 29 | 44 |
| 30 | 43 |

> 注：Ch29/Ch30 的 MR 条数（44/43）已超过多数章节的 scene 数量，Writer 无法在每个场景都完成回收。

## Top 20 P1 Critical Orphan 明细

按 `last_mentioned_chapter` 升序取前 20。`hints` = continuity_auditor human_mark 次数；`MR` = 在 last_mentioned 之后被 mandatory_references 注入的章节数。

| # | setting_key | 引入章 | 最后出现章 | 沉寂章数 | hints | MR 覆盖 | 根因标签 |
|---|-------------|--------|------------|----------|-------|---------|----------|
| 1 | `ruins.inner_chamber.neural_reading` | 6 | 6 | 24 | 1 | 22 | `hinted_and_injected_but_not_used` |
| 2 | `third_party.symbol.three_rings` | 16 | 16 | 14 | 1 | 12 | `hinted_and_injected_but_not_used` |
| 3 | `ruins.wall.neural_reading_ability` | 17 | 17 | 13 | 1 | 11 | `hinted_and_injected_but_not_used` |
| 4 | `sample.neural_network.topology` | 3 | 17 | 13 | 1 | 11 | `hinted_and_injected_but_not_used` |
| 5 | `ruins.inner_chamber.main_node_activation` | 6 | 18 | 12 | 1 | 10 | `hinted_and_injected_but_not_used` |
| 6 | `ruins.quantum_matrix.space` | 20 | 20 | 10 | 1 | 8 | `hinted_and_injected_but_not_used` |
| 7 | `entropy_corrosion.core.contamination` | 22 | 22 | 8 | 0 | 6 | `injected_without_prior_hint` |
| 8 | `entropy_corrosion.core.white_spots` | 22 | 22 | 8 | 0 | 6 | `injected_without_prior_hint` |
| 9 | `ruins.core.builders_demise` | 22 | 22 | 8 | 0 | 6 | `injected_without_prior_hint` |
| 10 | `ruins.core.civilization_layering` | 22 | 22 | 8 | 0 | 6 | `injected_without_prior_hint` |
| 11 | `ruins.core.direct_understanding` | 22 | 22 | 8 | 0 | 6 | `injected_without_prior_hint` |
| 12 | `ruins.core.discrete_curvature` | 22 | 22 | 8 | 0 | 6 | `injected_without_prior_hint` |
| 13 | `ruins.core.key_relationship` | 22 | 22 | 8 | 0 | 6 | `injected_without_prior_hint` |
| 14 | `ruins.core.light_deflection` | 22 | 22 | 8 | 0 | 6 | `injected_without_prior_hint` |
| 15 | `ruins.core.memory_city` | 22 | 22 | 8 | 0 | 6 | `injected_without_prior_hint` |
| 16 | `ruins.core.memory_vision` | 22 | 22 | 8 | 0 | 6 | `injected_without_prior_hint` |
| 17 | `ruins.core.mournful_sound` | 22 | 22 | 8 | 0 | 6 | `injected_without_prior_hint` |
| 18 | `ruins.core.sentinel_relationship` | 22 | 22 | 8 | 0 | 6 | `injected_without_prior_hint` |
| 19 | `ruins.singularity_node_chamber.spacetime_properties` | 22 | 22 | 8 | 0 | 6 | `injected_without_prior_hint` |
| 20 | `prosthetic.coordinate.anchor` | 23 | 23 | 7 | 0 | 5 | `injected_without_prior_hint` |

## 根因分类与占比

基于机制覆盖与生命周期两个维度交叉分类：

| 根因类别 | 计数 | 占比 | 关键证据 |
|----------|------|------|----------|
| `new_critical_introduced_ch20plus_then_abandoned` | 27 | 77.1% | Ch20+ 新设定引入后 1 章内再无提及；27 例中 26 例无 human_mark |
| `continuity_human_mark_budget_truncated` | 26 | 74.3% | 有 mandatory_reference 但无 continuity human_mark；受 MAX_ORPHANED=8 / 每章 20 条 unresolved 上限限制 |
| `writer_ignored_explicit_constraint` | 9 | 25.7% | human_mark 与 mandatory_reference 均存在，但正文仍未回收 |

**分类说明**：
- `new_critical_introduced_ch20plus_then_abandoned` 与 `continuity_human_mark_budget_truncated` 高度重叠（26/27 重叠），前者强调生命周期特征，后者强调机制失效。
- 不存在 `recycled_but_forgotten_again`：35 条中 resolved human_mark 数为 0。

## 机制失效点定位

结合代码阅读，定位到以下失效点：

1. **`_load_critical_mandatory_references` 无上限注入**（`src/songyan/workflows/_helpers.py:481-545`）
   - 只要 `status=active`、`category=critical`、沉寂章数 ≥3 就全部注入；Ch30 时达 43 条。
   - `ContextPackage.mandatory_references` 在 `BudgetPruner` 各阶段均不被裁剪，超长列表持续进入 Writer prompt。

2. **`_generate_constraints` 生成预算过紧**（`src/songyan/agents/continuity_auditor/_constraints.py:14-15,35`）
   - `MAX_ORPHANED = 8`，`MAX_CONSTRAINTS_GENERATED = 30`；单次 audit 只有前 8 个 orphan 能变成 human_mark。
   - 当 Ch21+ 每章新增 5-10 个 critical 设定时，老 orphan 永远排不进前 8，导致 `human_marks_total=0`。

3. **`write_constraints` 写入上限进一步压缩提示**（`src/songyan/agents/continuity_auditor/_constraints.py:152-174`）
   - 每章 unresolved human_mark 数 ≥20 时跳过写入；老约束未被回收，新约束无法进入。

4. **Writer 对长列表的合规性下降**（`prompts/cards/writer/1.2.0.yaml:43-53` 与 `src/songyan/agents/writer.py:335-350`）
   - Prompt 明确要求“不要跳过任何一个设定”，但当列表超过 30 条时，模型无法全部执行。
   - 9 条既有 human_mark 又有 MR 的 orphan 仍未被回收，证明仅靠提示不足以保证执行。

5. **自动分类启发式过宽**（`src/songyan/agents/settlement_extractor/_apply.py:688-714`）
   - `_infer_setting_category` 将含 `核心/锚/anchor/core` 的设定一律判为 critical。
   - 25/35 的 P1 orphan 的 setting_key 含 `core` 或 `anchor`，其中 22 个是 Ch20+ 新引入后立即丢失的世界观细节。

6. **RuleAuditor 检测到缺失但不触发修订**（`src/songyan/agents/rule_auditor.py:189-225`）
   - `_check_mandatory_references` 能正确识别缺失，但当前 `gate_mode=observe`，缺失只被记录，不强制 RevisionHandler patch。

## 候选策略评估矩阵

| 维度 | A QG 阻断式 revision | B CreativeDirector 预回收 | C Context Diet 衰减调优 | D 接受边界 |
|------|:--------------------:|:--------------------------:|:------------------------:|:----------:|
| 预计 P1 降幅 | 4 | 3 | 2 | — |
| 工程复杂度 | 中 | 高 | 低 | 无 |
| 架构侵入 | 中 | 高 | 低 | 无 |
| 副作用风险 | 中 | 高 | 低 | 高 |
| 与 V5.1 收口冲突 | 小 | 中 | 小 | 无 |

评分说明：1=最低/最负面，5=最高/最正面；D 的 P1 降幅记为“—”。

## 推荐方案：A + C

**推荐**：优先实施 **A（QG 阻断式 revision）+ C（Context Diet / mandatory_reference 上限调优）**，不引入新的 Agent 类型，也不一次性重写 Writer/Settlement。

### 理由

1. **数据直接指向 Writer 执行缺口，而非缺少提示**：35 条 P1 orphan 全部曾被 `mandatory_references` 注入，其中 9 条还有 human_mark，但仍未被回收。提示已经“送到”，但模型没做。只有 A 能把缺失变成可执行的反馈闭环。
2. **MR 列表无上限是过载根源**：C 通过给 `_load_critical_mandatory_references` 设置每章上限（如 Top 10 最紧急 critical orphan），先把任务量降到 Writer 可处理范围，A 才能有效执行；否则 43 条强制约束会触发大量 revision 甚至死锁。
3. **B 成本高且效果不确定**：让 CreativeDirector 在 brief 阶段预分配回收场景需要改动 brief schema 和 LLM prompt，并且仍然依赖 Writer 执行；在 A 未验证有效前，不宜扩大架构。
4. **D 会击穿质量地板**：当前 health=3.0 已接近 floor，若接受此边界进入 Ch50+，P1 orphan 很可能继续增长并引发 state mismatch / 设定冲突，后续修复成本更高。

### 建议的 A+C 具体措施

- **A1**：在 `rule_auditor_node` 中，当 `gate_mode != observe` 时，将 `mandatory_reference_missing` 作为硬 gate fail；在 `observe` 模式下仍记录但不阻断（保持默认）。
- **A2**：新增 `RevisionHandler` 专用 patch 路径：收到 `mandatory_reference_missing` issue 时，只要求补充缺失设定的提及，不整章重写；最多 2 轮。
- **C1**：`_load_critical_mandatory_references` 增加上限（建议 `max_mandatory_references = min(10, 3 + chapter_number//10)`），按 `silent_chapters` 与 `introduced_in_chapter` 综合排序，只注入最紧急的 N 条。
- **C2**：调高 `MAX_ORPHANED` 至与上限匹配（如 12-16），并允许按优先级（critical>recurring）分配 human_mark 预算，确保进入 MR 列表的设定同时获得 human_mark 提示。
- **C3（可选）**：收紧 `_infer_setting_category` 的 critical 关键词，要求同时命中 `核心/锚` **和** 与主角/主线强相关描述，减少世界观细节被误判为 critical。

### 风险与工作量

- **主要风险**：A 实施后，若 MR 上限未同步，可能导致单章 revision 次数增加、运行时间变长；需通过小窗口（Ch10-Ch20 / Ch21-Ch30）验证 revision 轮数与运行时长。
- **工作量估算**：A 约 1-2 天（RuleAuditor gate 集成 + RevisionHandler patch 路径 + 单测）；C 约 1 天（上限/排序 + 单测）；合计 2-3 天工程 + 1 轮 Ch1-Ch30 重跑验证。

## 下一步

创建并执行 **Task 138n：QG 阻断式 critical orphan revision + mandatory_reference 上限调优**。
目标：在 Ch1-Ch30 重跑中把 P1 critical orphan 从 35 降至 ≤15，health 恢复到 ≥4.0；验证通过后再决定是否扩大窗口到 Ch50+。

## 附录：中间产物清单

| 产物 | 路径 |
|------|------|
| P1 orphan 原始清单 | `.tmp/138m_p1_orphans_raw.json` |
| enriched 生命周期与机制覆盖 | `.tmp/138m_p1_orphans_enriched.json` |
| Top 20 mandatory reference 覆盖 | `.tmp/138m_mandatory_reference_coverage.json` |
| 根因分类与全量明细 | `.tmp/138m_root_cause_classification.json` |
| 根因分类摘要 Markdown | `.tmp/138m_root_cause_summary.md` |
| 每章 MR 加载量 | `.tmp/138m_mandatory_refs_per_chapter.json` |

---

报告结束。