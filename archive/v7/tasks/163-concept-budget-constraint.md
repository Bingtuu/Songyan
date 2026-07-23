# Task 163: 概念预算约束（治概念通胀）

> **Phase**: V7 阶段 W（篇章级质量修复）
> **优先级**: P1（世界观落地不足，conceptual_grounding 中后段 7.12→6.02 持续退化；L 项 T10 的直接前置）
> **依赖**: 阶段 0 骨架（Task 141-144 的 GoalPlanner/CreativeDirector 注入链路）、Task 147 文学趋势查询
> **预计工作量**: 中（规划侧约束注入 + 概念台账 + 收紧触发；不做自动改写）
> **事实入口**: `tasks/V7-README.md`；规划：`docs/v7-plan.md` §3 阶段 W

---

## Goal

治理 `run-bba292da` 中后段的**概念通胀**（每章堆叠新名词但不落地，`conceptual_grounding_score` 从 7.12 单调降到 6.02，"不是X—是Y"句式空转）：在**章节规划阶段约束单章新概念引入数**、强制"已引入概念先落地再造新的"，并让 conceptual_grounding 下滑**触发概念预算收紧**（诊断 + 告警 + 规划侧约束，**不做自动 LLM 改写**）。

## Context

设计核实（2026-07-04，创建前对主干代码核对）：

- **退化实测**：`conceptual_grounding_score`（`literary_observations` 表列，Task 147 已可趋势查询）在 158（`run-10d7961b`）Ch10 即触 T3 红线；159 全程从 7.12 降到 6.02。根因是**每章造新概念但旧概念未落地**——世界观名词只增不消化。
- **注入点在规划侧**：章节生成前的规划链路（GoalPlanner 自顶向下派生章节目标 Task 143、CreativeDirector/Writer 约束注入 Task 144 线索经济）是**约束"本章该引入/落地什么"的天然位置**。Task 144 已有"本章应推进/收束线索、非必要不开新线"的先例——概念预算是同构的"非必要不造新概念、先落地旧概念"约束。
- **概念台账需要来源**：判断"概念是否已落地"需要一个**概念台账**——已引入概念清单 + 其"落地状态"。这与 PlotThread（线索状态机 Task 141/144）、new_settings（settlement 录入 Task 149）是相邻但不同的对象：概念台账关注**世界观名词的引入与消化**，可复用 settlement 的 new_settings 作为"引入侧"信号，用 conceptual_grounding + 后续章是否复用该概念作为"落地侧"信号。
- **保守边界——不自动改写**：按 V7 决策边界，本 Task **只在规划侧注入约束 + 诊断告警**，不触发自动 LLM 改写闭环。conceptual_grounding 下滑时，收紧动作是"规划阶段更强地要求落地旧概念、抑制新概念"（prompt 约束 + 台账驱动），而非事后重写正文。

**边界**：MVP 概念预算——"限量引入 + 优先落地 + 下滑收紧"，**不做**概念图谱/语义聚类等大系统。约束注入走现有规划链路（prompt/context），不新增 Agent/Workflow 节点。无骨架/无台账项目须能回退旧行为。

## In Scope（必须完成）

- [ ] **单章新概念预算**：在章节规划阶段（GoalPlanner/CreativeDirector 注入）约束**单章新概念引入数上限**（可配置默认，随活跃概念数自适应可选）；超额时规划提示"优先落地已有概念、非必要不造新的"。约束以 prompt/context 注入实现，不新增门禁。
- [ ] **概念台账（MVP）**：建立已引入概念的最小台账——引入章 + 落地状态（复用 new_settings 引入侧信号 + 后续章复用/conceptual_grounding 落地侧信号）。台账可查、可在 report 计数"未落地概念数"。
- [ ] **下滑触发收紧**：当 conceptual_grounding 滑窗均值下滑（复用 Task 147 趋势查询，按 T3/T8 口径）时，**触发概念预算收紧**——规划侧更强约束落地、告警入 report。**不自动改写正文**。
- [ ] **回退保障**：无骨架/无概念台账的项目行为可回退（不比现状更差）；约束注入不劣化正文质量（用小窗口对比验证）。

## Out of Scope（明确不做）

- 不做元标记（160）、去重（161）、时间线（162）。
- **不做自动 LLM 改写闭环**——收紧只在规划侧约束 + 诊断告警（V7 决策边界）。
- 不做概念语义图谱/聚类/嵌入相似度等大系统——保持"计数 + 落地状态"MVP。
- 不新增 Agent/Workflow 节点（约束走现有 GoalPlanner/CreativeDirector 注入链路）。
- 不做 T10 阈值冻结（留 Task 165 阶段 W 出口用 Ch150 修复后基线标定）。

## 接口契约

```python
# 概念台账（MVP）：引入 + 落地状态
class ConceptLedgerEntry(BaseModel):
    concept_key: str
    introduced_chapter: int
    grounded: bool          # 是否已落地（后续章复用 / grounding 信号）
    last_referenced_chapter: int | None

# 规划侧约束注入（走现有链路，返回注入片段/约束）
def build_concept_budget_constraint(
    project_id: str,
    chapter_no: int,
    *,
    max_new_concepts: int,
    tighten: bool,          # conceptual_grounding 下滑时为 True
) -> str:
    """生成"限量引入 + 优先落地旧概念"的规划约束（prompt 注入）."""
```

## 测试要求

### Layer 2: 模块测试（`tests/test_163_concept_budget.py`）
- [ ] **预算约束生成**：给定活跃概念数/未落地数，验证 `build_concept_budget_constraint` 在正常/收紧两态生成正确约束文案与上限。
- [ ] **台账落地状态**：构造"引入后被复用" vs "引入后再未提及"的概念，验证 grounded/未落地判定正确、report 计数正确。
- [ ] **下滑触发收紧**：Mock conceptual_grounding 滑窗下滑（复用 147 趋势判定），断言触发 `tighten=True` 分支；未下滑时不触发。
- [ ] **无骨架回退**：无台账/无骨架项目，验证回退旧行为、不报错、不劣化。

### Layer 3: 小窗口复跑（可选，归因佐证）
- [ ] 带概念预算约束的小窗口复跑，对比 conceptual_grounding 趋势是否止跌 + 正文质量不劣化（人工抽查 + 度量）。

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/test_163_*.py -v` 全过；`ruff check src/ tests/` 通过；全量 pytest 不回归。
- [ ] 单章新概念预算约束在规划侧生效；概念台账可查未落地概念数；conceptual_grounding 下滑触发收紧且**不自动改写正文**。
- [ ] 无骨架/无台账项目可回退旧行为、不劣化。
- [ ] 不违反不可违背规则：GoalPlanner/CreativeDirector 不写正文只输出结构化规划；不新增 Agent/Workflow 节点；无自动改写闭环；MVP 边界不膨胀。
- [ ] 生成 `archive/v7/tasks/163-concept-budget-constraint-DONE.md`（含预算口径、台账设计、收紧触发条件、小窗口对比结果）。
- [ ] 更新 `tasks/V7-README.md`（163 状态）与 `docs/STATUS.md`。

## 参考文档

- `docs/v7-plan.md` §0（概念通胀缺陷行）、§3 阶段 W（Task 163 行）、§4 T10
- 规划注入先例：Task 143（GoalPlanner 自顶向下派生）、Task 144（线索经济约束注入）：`src/songyan/workflows/_thread_economy.py`、`_nodes.py`
- 文学趋势查询（下滑判定复用）：Task 147 `archive/v6/tasks/147-literary-quality-trend-DONE.md`、`src/songyan/evals/db_metrics.py`（`collect_literary_scores` / `detect_literary_trend`）
- 引入侧信号：Task 149 `src/songyan/workflows/_input_side_governance.py`（new_settings 录入）
- 缺陷证据：`archive/v6/reports/task-159-v6-final-acceptance-report.md`（conceptual_grounding 7.12→6.02）
