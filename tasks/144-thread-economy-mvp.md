# Task 144: 线索经济约束（MVP）

> **Phase**: V6 阶段 0（最小叙事骨架 MVP）
> **优先级**: P0（阶段 0 出口 (b)(c) 的直接实现）
> **依赖**: Task 141（PlotThread 模型/状态机 API）、Task 143（GoalPlanner 骨架上下文）
> **预计工作量**: 大
> **事实入口**: `tasks/V6-README.md`；规划：`docs/v6-plan.md` §3 阶段 0

---

## Goal

给 CreativeDirector / Writer 注入"本章应推进/收束的线索；非必要不开新线"的约束，并让 `PlotThread` 状态在 settlement 后随正文进展更新（`opened/advanced/resolved`），使线索开启-兑现可追踪、可计数，并把每章新 critical 产生速率（T7）压下来。

## Context

Task 141 建了 PlotThread 状态机 API（`advance_thread_status`），Task 143 让 GoalPlanner 能读到未收束线索。但目前：CreativeDirector/Writer 没有"先兑现已开线索、别乱开新线"的约束（根因下游：Writer 反应式随手抛新 critical 设定 → orphan 累积）；PlotThread 状态也没有随 settlement 自动更新的闭环。本 Task 补上这两条，是阶段 0 出口 (b)「至少一条主线线索完成 opened→advanced→resolved 跃迁」和 (c)「T7 下降 ≥30%」的直接实现。

**MVP 边界**：只做"约束注入 + 状态跟随更新"，不做自动重规划。线索状态更新基于 settlement 已有的证据（不新增 LLM 调用做线索判断，优先复用 settlement 输出）。

## In Scope（必须完成）

- [ ] **线索约束注入**：CreativeDirector（和/或 Writer 工艺卡）注入"本章应推进的线索 / 应收束的线索 / 非必要不开新线索"约束。复用 Task 143 的 `NarrativeGoalContext`（`open_threads` / `threads_to_resolve`）。
- [ ] **PlotThread 状态跟随更新**：settlement 完成后，依据本章证据更新相关线索状态（`planned→opened`：首次推进；`opened→advanced`：继续推进；`advanced→resolved`：本章收束）。状态变更调用 Task 141 的 `advance_thread_status`，写入 `last_status_chapter` + `last_status_version_id`（T1 可追溯）。
- [ ] **线索状态可计数**：提供查询让线索 `opened/advanced/resolved` 计数可被 report 读取（为阶段 A Task 148 弧级兑现率铺路）。
- [ ] **遵守 Agent 边界**：状态更新逻辑放在 settlement 后处理（service 层），不让 Writer/CreativeDirector 直接写 DB。

## Out of Scope（明确不做）

- 不做自动重规划闭环（V7）。
- 不新增独立 LLM 调用判断线索状态——优先基于 settlement 已产出的证据/映射；若必须让模型标注线索推进，复用 settlement 或 CreativeDirector 已有调用，不加新 Agent。
- 不做线索的显式 resolve/作废出口（那是阶段 B Task 152）——本 Task 只做正文进展驱动的自动状态推进。
- 不改 SettlementExtractor 的证据校验规则（不可违背规则不动）。

## 接口契约

```python
# settlement 后处理：依据本章 settlement 更新线索状态
async def update_plot_threads_after_settlement(
    project_id: str, chapter_number: int, version_id: str,
    settlement: Settlement, narrative_repo: NarrativeRepository, ...
) -> list[str]:
    """返回本章发生状态变更的 thread_id 列表；每次变更写 version_id（T1）."""
    ...
```

### 状态推进判定（MVP 规则，基于 settlement 证据）

- 线索被本章正文推进（settlement 中出现相关 foreshadowing/setting 引用）→ `opened`（若之前 planned）或 `advanced`。
- 线索被本章收束（对应 foreshadowing 兑现 / 冲突解决）→ `resolved`。
- 判定优先用 settlement 已有的结构化输出映射，规则可解释、可单测；不引入新的模糊 LLM 判断。

## 测试要求

### Layer 2: 模块测试
- [ ] 约束注入：带 open_threads 的上下文 → CreativeDirector/Writer prompt 含"应推进/收束线索、非必要不开新线"约束变量。
- [ ] 状态机跟随：构造 settlement 证据 → `update_plot_threads_after_settlement` 正确推进状态；`last_status_version_id` 写入本章 version。
- [ ] 计数：多章推进后，`opened/advanced/resolved` 计数查询返回正确值。
- [ ] 边界：无相关线索的章节 → 不误改任何线索状态。
- [ ] Mock：真实临时 SQLite；Mock LLM（约束注入测 prompt 变量组装）。

### Layer 3: 小窗口复跑验证（阶段 0 出口判据）
- [ ] 在带大纲项目上跑 Ch1-Ch20（隔离副本 DB），验证：
  - (b) 至少一条 `is_mainline=true` 的 PlotThread 完成完整 `opened→advanced→resolved` 跃迁，且每步可定位章节号 + version_id（T1）。
  - (c) 每章新 critical 产生速率（T7）相对 138k 同区间基线**下降 ≥30%**。

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/test_144_thread_economy.py -v` 全部通过（状态机 + 约束注入 + 计数）。
- [ ] `ruff check src/ tests/` 通过；全量 pytest 不回归。
- [ ] 线索 `opened/advanced/resolved` 状态被追踪且可在查询/report 计数。
- [ ] Ch1-Ch20 小窗口复跑满足阶段 0 出口 (b)(c)：≥1 条主线线索完成 T1 跃迁；T7 较 138k 基线降 ≥30%（报告入 `docs/reports/`）。
- [ ] 不违反不可违背规则：状态更新经 service/repository；SettlementExtractor 证据规则不变；不新增 Agent 节点。
- [ ] 生成 `tasks/144-thread-economy-mvp-DONE.md`，含状态推进规则、Ch1-Ch20 复跑证据（T1 跃迁链 + T7 对比）。
- [ ] 更新 `tasks/V6-README.md`（144 状态 + 阶段 0 出口结论）与 `docs/STATUS.md`。

### 依赖与顺序提示

- 阶段 0 出口的**报告展示**（"report 可计数线索状态"）与阶段 A 的 report 度量能力相关（见 v6-plan 修正说明 / Task 145）。本 Task 保证状态数据被正确产出与持久化；若阶段 A 尚未落地 report 展示，用直接 DB 查询/脚本验证 (b)(c)，并在 DONE 文档注明。
- T7 基线取 `.tmp/task138k_ch1_ch30_rehearsal_20260629.db`（V6 阶段 A 校准依赖，已在 V6-README 标注不得清理）。

## 参考文档

- `docs/v6-plan.md` §1.4-T1/T7、§3 阶段 0（Task 144 行 + 阶段 0 出口）
- Task 141（PlotThread 状态机 `advance_thread_status`）、Task 143（NarrativeGoalContext）
- 现有代码：`src/songyan/agents/creative_director/`、`src/songyan/agents/settlement_extractor/`、Writer 工艺卡
