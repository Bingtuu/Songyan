# Task 138m: Ch21-Ch30 Critical Orphan 根因分析与 V5.2 边界决策

> **类型**: 根因分析 / 架构决策
> **状态**: 已完成
> **前置**: Task 138k 已完成，Ch1-Ch30 长窗口 rehearsal 全部完成，Run `run-6f2a10d3`，最终 health=3.0、P1 critical orphan=35
>
> **边界**: 本任务先分析、再决策；若决策需要代码改动，优先在单测/小窗口验证后再合入主线
>
> **完成结论**: 本任务已按执行计划完成。决策报告见 `docs/reports/task-138m-critical-orphan-root-cause-report.md`。根因结论：35 个 P1 orphan 中 27 个为 Ch20+ 新引入后立即丢弃的 critical 设定；26 个因 `MAX_ORPHANED=8` 等约束预算截断从未获得 human_mark；全部 35 个均进入无上限的 `mandatory_references`（Ch30 达 43 条）但 Writer 未执行。推荐方案为 **A + C**（QG 阻断式 revision + mandatory_reference 上限/衰减调优），后续任务见 `tasks/138n-qg-mandatory-reference-revision-loop-DONE.md`。
>
> **归档说明**: 本任务产生的中间分析数据与脚本已归档至 `archive/v5/138m-analysis/`。

## 背景

Task 138k 的 Ch1-Ch30 实跑证明：

- 138h-138j 的 critical orphan 强制回收闭环在 **Ch1-Ch15** 有效（health 从 5.1 降至 3.0，但 P1 仅 5）。
- 进入 **Ch21-Ch30** 后，critical orphan 快速堆积，Ch30 达到 **P1=35**，health 被钉在 3.0 下限。
- 该任务 **不是 settlement 阻断**，而是 continuity health 长期恶化；在 observe 模式下 run 可以完成，但质量地板被击穿。

在继续扩大 rehearsal（Ch50/Ch100/Ch150）之前，必须先回答：

1. 这 35 个 P1 critical orphan 是什么？来自哪些 setting_key？
2. 它们为什么没有被 `mandatory_references` 注入、`recycle_hint` 提示或 `settings_recycled` 机制回收？
3. 是机制设计缺陷，还是阈值/提示力度不足？
4. V5.2 应该接受这个边界，还是继续投入改进？如果改进，选哪条路径？

## 目标

1. **分类根因**：对 Ch30 的 35 个 P1 critical orphan 按来源/机制失效类型分类（至少覆盖 Top 20）。
2. **量化影响**：统计每个根因类别占比，判断主要矛盾。
3. **评估选项**：从以下候选策略中挑选或组合：
   - A. **QG 阻断式 revision**：RuleAuditor 检测到 `mandatory_reference_missing` 后，强制触发 RevisionHandler patch，不通过则降级/循环。
   - B. **CreativeDirector 预回收**：在 brief 阶段自动识别需回收的关键设定，并在 scene outline 中显式分配复现场景。
   - C. **Context Diet 衰减调优**：降低长程 critical setting 的蒸发速率，或提升 `recycle_hint` 的上下文权重。
   - D. **接受边界**：将 health ≥ 3.0 / P1 ≤ 35 作为 V5.2 的验收基线，停止继续优化，转向 Ch50+ 实跑。
4. **形成决策文档**：输出 `docs/reports/task-138m-critical-orphan-root-cause-report.md`，明确推荐方案、风险、所需工作量。
5. **更新入口文档**：同步 `docs/STATUS.md`、`tasks/V5-README.md`、`docs/INDEX.md`。

## 不做的事

- **不直接跑 Ch50+ rehearsal**：在根因未明确前，不盲目扩大窗口。
- **不一次性重写 Writer/Settlement/ContextManager**：优先定位最小有效改动点。
- **不修改历史已归档任务**：138h-138j 的 DONE 文档保持只读。
- **不引入新 Agent 类型**：除非决策文档明确论证。

## 要做的事

### 1. 从 DB 提取 Ch30 的 critical orphan 清单

使用 `.tmp/task138k_ch1_ch30_rehearsal_20260629.db`：

```sql
SELECT setting_key, setting_name, last_appeared_chapter, category, confidence, priority
FROM setting_tracking
WHERE project_id = '3bef1af8d54d4d0e887658516e1ed350'
  AND priority = 'P1'
  AND status = 'active'
ORDER BY last_appeared_chapter, setting_key;
```

同时读取 `continuity_reports` 中 `cont_aba8cc2d` 的 `suggested` / `orphaned` 列表，拿到具体 key。

输出：`tmp/138m_p1_orphan_list.json`

### 2. 按来源分类

对每个 Top 20 P1 orphan，追溯：

- **首次引入章节**：从 `setting_snapshots` 查 `chapter_number` / `source_version_id`。
- **最后出现章节**：从正文或 summary 确认是否真的被遗忘。
- **是否进入过 mandatory_references**：查对应章节的 `context_snapshots.context_json` 中 `mandatory_references` 字段。
- **是否被 recycle_hint 标记**：查 `human_marks` 表中 `target_key` 与 `mark_type='continuity_recycle_hint'`。
- **是否被 settings_recycled 回收**：查 settlement 日志中 `settings_recycled`。

分类标签示例：

- `never_recycled`：从未出现在任何回收机制中。
- `hinted_but_not_used`：recycle_hint 已注入，但 Writer 未在正文中复现。
- `recycled_but_forgotten_again`：曾被回收，后续再次丢失。
- `newly_introduced_long_tail`：Ch20+ 新设定，生命周期自然短但 priority 被标为 P1。
- `category_misclassified`：实际是 background，不应为 P1。

### 3. 机制失效点定位

结合代码阅读：

- `src/songyan/agents/context_manager/_assemble.py`：硬约束/强制引用如何衰减？
- `src/songyan/agents/creative_director/`：是否将 recycle_hint 转成 scene outline？
- `src/songyan/agents/writer/`：工艺卡 1.2.0 对 `recycle_hint` / `mandatory_references` 的遵循情况。
- `src/songyan/agents/settlement_extractor/`：settings_recycled 的选择逻辑与 `human_mark_resolved`。
- `src/songyan/agents/continuity_auditor/`：P1 判定标准、health 计算、human_marks 写入。

重点问题：

- `mandatory_references` 数量是否被 budget 截断？
- `recycle_hint` 是否只提示一次？后续章节是否衰减消失？
- Writer 在 Ch20+ 是否因 scene 过多而忽略提示？
- settlement 阶段回收的 setting 是否再次因蒸发/归档而丢失？

### 4. 评估四个候选策略

对每个选项，从以下维度打分（1-5）：

| 维度 | A QG 阻断 | B CD 预回收 | C 衰减调优 | D 接受边界 |
|---|---|---|---|---|
| 预计 P1 orphan 降幅 | ? | ? | ? | - |
| 工程复杂度 | 中 | 高 | 低 | 无 |
| 对现有架构侵入 | 中 | 高 | 低 | 无 |
| 副作用风险 | 可能增加 revision 循环/成本 | 可能限制创作自由度 | 可能增加上下文噪音 | 质量风险 |
| 与 V5.1 收口冲突 | 小 | 中 | 小 | 无 |

根据根因分类结果，选择单一或组合方案。

### 5. 输出决策报告

`docs/reports/task-138m-critical-orphan-root-cause-report.md` 必须包含：

- 数据摘要：Ch30 P1/P2/P3 分布、Top 20 orphan 列表。
- 根因分类饼图/表格。
- 机制失效点定位。
- 候选策略评估矩阵。
- **推荐方案**：明确选 A/B/C/D 或其组合，给出理由。
- **下一步 Task 编号**：如推荐需要代码改动，指定 Task 138n（或 139）负责实现与验证。

### 6. 同步入口文档

- `docs/STATUS.md`：当前阶段改为“Task 138m 根因分析进行中/已完成，等待 138n 实现”。
- `tasks/V5-README.md`：追加 138m 状态与报告链接。
- `docs/INDEX.md`：增加 138m 文档索引。

## 验收标准

- [x] Ch30 的 35 个 P1 critical orphan 已分类，Top 20 每个都有来源/机制失效标签。
- [x] 根因分类占比统计完成，主要矛盾明确。
- [x] 四个候选策略评估矩阵已填写，有据可依。
- [x] 决策报告已输出到 `docs/reports/task-138m-critical-orphan-root-cause-report.md`。
- [x] 推荐方案对应的下一步 Task 文件已创建：`tasks/138n-qg-mandatory-reference-revision-loop.md`。
- [x] `docs/STATUS.md`、`tasks/V5-README.md`、`docs/INDEX.md` 已同步。

## 参考

- 138k 报告：`docs/reports/task-138k-long-window-rehearsal-report.md`
- 138k 任务：`tasks/138k-long-window-rehearsal-ch1-ch50.md`
- 138h-138j DONE：`tasks/138h-critical-orphan-mandatory-recall-loop-DONE.md`
- 138l DONE：`tasks/138l-settlement-telemetry-false-positive-fix-DONE.md`
- DB 副本：`.tmp/task138k_ch1_ch30_rehearsal_20260629.db`
