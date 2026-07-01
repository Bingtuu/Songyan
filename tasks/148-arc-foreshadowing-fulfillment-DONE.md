# Task 148 DONE — 弧级伏笔兑现率 + 长程伏笔台账

> **Phase**: V6 阶段 A（度量同步）
> **状态**: ✅ 完成（弧级兑现率 + 长程台账 + 真兑现/逾期归档区分 + metrics 段）
> **完成日期**: 2026-07-01
> **规划/设计**: `docs/v6-plan.md` §3 阶段 A；任务书 `tasks/148-arc-foreshadowing-fulfillment.md`

---

## 交付概览

基于 ArcPlan 弧章节范围统计弧级伏笔兑现率，暴露长程未兑现伏笔台账，并明确区分「真兑现」与「逾期归档（被系统遗忘）」。

| 交付物 | 文件 |
|--------|------|
| repo | `db/settlement_repo.py` `ForeshadowingRepository.list_with_lifecycle(project_id)`（raw SQL，含 lifecycle_status） |
| 度量模块 | `evals/db_metrics.py`：`ArcFulfillment`/`ForeshadowingLedgerRow`、`collect_arc_fulfillment`、`collect_long_range_ledger`、render 两段 |
| metrics 段 | `render_stage_a_metrics` 追加"弧级伏笔兑现率"与"长程伏笔台账"两段 |
| 测试 | `tests/test_148_foreshadowing_metrics.py`（5 用例） |

## 关键实现点

- **真兑现 vs 逾期归档**：fulfilled ⇔ `status='resolved'`（archived+resolved 仍算兑现）；abandoned ⇔ `status!='resolved' AND lifecycle_status IN ('dormant','archived')`。二者在正交列上，`list_with_lifecycle` 直接查表（`ForeshadowingItem` 模型不带 lifecycle_status，故用 raw SQL）。
- **弧归属**：伏笔 `planted_in_chapter` ∈ `[arc.start_chapter, arc.end_chapter]` 桶化；弧外为散点（不计入弧）。
- **优雅降级（C4 修正）**：`collect_arc_fulfillment` 在 `arc_plans` 空（历史 DB / 无大纲）时返回 `[]`，不报错；渲染显示"无 arc_plans"。
- **长程台账**：列所有 `status!='resolved'` 伏笔 + `span=current-planted` + `is_abandoned` 标记；汇总"被遗忘"数。

## 验证

- `pytest tests/test_148_foreshadowing_metrics.py -q` → **5 passed**（弧级兑现率 / archived+resolved 仍兑现 / overdue+archived 判 abandoned / 弧外散点 / arc_plans 空降级 / 台账 span + 被遗忘标记）。
- `pytest`（145-148 合计）→ **31 passed**；`ruff check`（改动文件）→ **All checks passed**。

## Out of Scope（未做）

- 不改伏笔生命周期/归档逻辑；不引入伏笔↔PlotThread 显式关联（MVP）。
- 138n 因无 arc_plans 只能复算全局台账（resolved vs abandoned），弧级兑现率不可复算 → 由 `tasks/148z` 标定报告注明。
