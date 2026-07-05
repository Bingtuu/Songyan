# Task 166: 阶段 X 起点 — plan→generate→re-plan 闭环总览

> **Phase**: V7 阶段 X（叙事自驱）
> **优先级**: P0（阶段 W 通过后的第一项；T11/T12 与 Ch200+ 的前置）
> **状态**: ✅ 完成（166a / 166b 均已完成）
> **依赖**: Task 165 / 165p 阶段 W 出口通过，T9/T10 已冻结
> **事实入口**: `tasks/V7-README.md`；规划：`docs/v7-plan.md` §3 阶段 X

> **执行结果**: 已完成，见 `tasks/166-plan-generate-replan-loop-DONE.md`。

---

## Review 结论（2026-07-05）

原单体 Task 166 规划把“只读评估”和“事务写入应用”放在同一个任务里，风险面过大：

- **166a** 是只读/追加式能力：从 SQLite 读取 ArcPlan、PlotThread、摘要与度量，生成 `ReplanProposal`。它可以离线验证，不应修改既有规划。
- **166b** 是写操作能力：人工确认后应用 proposal，事务化更新后续 `ArcPlan` / `PlotThread` / 规划约束。它必须依赖 166a 的模型、表和 proposal 证据。

因此 Task 166 拆为两个任务文档，本文件只保留总览和路由。

## 拆分后的任务顺序

| Task | 名称 | 状态 | 文档 |
|------|------|:----:|------|
| 166a | 弧后评估与 ReplanProposal 生成 | ✅ 完成 | `tasks/166a-arc-outcome-evaluation-and-replan-proposal-DONE.md` |
| 166b | 人工确认后的 re-plan 应用 | ✅ 完成 | `tasks/166b-approved-replan-application-DONE.md` |

## 总目标

给 Songyan 建立最小可用的 **plan→generate→re-plan** 闭环：在一段章节或一个 Arc 生成完成后，系统能基于 SQLite 事实源评估“前置规划是否被真实生成结果兑现”，生成可审计的 `ReplanProposal`，并在人工确认后更新后续规划。

本阶段的核心不是让系统自动改正文，而是让系统具备“生成后读回现实结果，再调整后续计划”的能力。完成后，后续 Task 167 才能把长程伏笔主动调度建立在真实、可回滚的 re-plan 结果上。

## 统一边界

- SQLite 是唯一事实源；输入必须从 repository/service 读取。
- 不从 LangGraph state 或日志正文拼装业务对象。
- 不生成、不修改正文。
- 不触发 RevisionHandler / rewrite。
- 不把 re-plan 自动接入每章生成主流程。
- 不新增长期运行 workflow 节点。
- proposal 默认只生成，不自动应用；必须显式 approve/apply。
- 只改未来规划，不改历史章节。
- 所有应用动作必须可审计、可回滚。

## 阶段 W 读后质量债如何进入 166

阶段 W 人工阅读发现的风格债不作为 166 的自动修文目标，但应作为后续规划约束进入 proposal：

- 句式模型化：限制“不是 A，是 B”“像……”等模板继续强化。
- 概念解释密度高：要求新概念通过动作、场景、冲突落地。
- 人物声纹同质：要求关键角色承担可区分的行为和语言功能。

这些只进入 `ReplanAction(target_type="style_constraint")` 或等价结构，不自动改写既有正文。

## 总体验收

Task 166 完成时必须满足：

- 166a 能在无骨架项目上 no-op，在有骨架项目上生成结构化 proposal。
- 166b 能在人工确认后事务化应用 proposal，并保留 diff。
- Task 166 不破坏 Task 165/165p 冻结的 T9/T10 口径。
- 生成 `tasks/166-plan-generate-replan-loop-DONE.md` 前，必须有可重复的离线 evidence。

## 参考文档

- `tasks/166a-arc-outcome-evaluation-and-replan-proposal.md`
- `tasks/166b-approved-replan-application.md`
- `tasks/165-stage-w-ch150-rerun-and-threshold-freeze-DONE.md`
- `tasks/165p-stage-w-harness-calibration-DONE.md`
- `docs/reports/task-165-stage-w-exit-report.md`
- `src/songyan/models/narrative.py`
- `src/songyan/db/narrative_repo.py`
- `src/songyan/workflows/_thread_economy.py`
- `src/songyan/evals/db_metrics.py`
