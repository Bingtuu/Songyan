# Task 166b: 人工确认后的 re-plan 应用

> **Phase**: V7 阶段 X（叙事自驱）
> **优先级**: P0（Task 166 的写入半段；必须在 166a 后执行）
> **依赖**: Task 166a DONE
> **预计工作量**: 中
> **事实入口**: `archive/v7/tasks/166-plan-generate-replan-loop.md`

> **执行结果**: 已完成，见
> `archive/v7/tasks/166b-approved-replan-application-DONE.md`。Task 166 总览同步收口为
> `archive/v7/tasks/166-plan-generate-replan-loop-DONE.md`。

---

## Goal

在 166a 已能生成 `ReplanProposal` 的基础上，实现人工确认后的 re-plan 应用能力：将 approved proposal 中的 actions 事务化写入未来规划，保留 diff、原因和状态，确保可审计、可回滚。

166b 是写操作任务，必须严格限制作用范围：只改未来规划，不改历史正文，不触发生成或修订。

## Preconditions

166b 开工前必须满足：

- `ReplanProposal` / `ReplanAction` 模型与表已存在。
- 166a 已有 DONE 文档与离线 evidence。
- 166a 已证明 proposal 默认不会自动应用。

## In Scope

- [x] 实现 proposal 状态流转：
  - `draft -> approved`
  - `draft -> rejected`
  - `approved -> applied`
- [x] 实现 `approve_replan_proposal(proposal_id, approved_by=...)`。
- [x] 实现 `reject_replan_proposal(proposal_id, reason=...)`。
- [x] 实现 `apply_replan_proposal(proposal_id, applied_by=...)`：
  - 只允许应用 `approved` proposal。
  - 应用必须事务化。
  - action 全部成功才 commit。
  - 任一 action 失败必须 rollback。
- [x] 支持 action target：
  - `arc_plan.arc_goal`
  - `arc_plan.threads_to_open`
  - `arc_plan.threads_to_resolve`
  - `plot_thread.expected_resolve_arc`
  - `style_constraint` 或等价未来规划约束存储。
- [x] 若现有 `NarrativeRepository` 不支持目标字段更新，新增最小 repository/service 方法；应用层不得直接散落 SQL 写规划表。
- [x] 每个 action 必须保留：
  - old_value
  - new_value
  - target_type
  - target_id
  - field
  - reason
- [x] 应用后更新 proposal 状态为 `applied`，记录 applied_at / applied_by。
- [x] 应用后重新读取 repository 验证目标值与 action 一致。

## Out of Scope

- 不创建 proposal（166a 负责）。
- 不生成或修改正文。
- 不接入主生成 workflow。
- 不允许自动 approve。
- 不改历史 ArcPlan 覆盖范围内已结束章节的事实。
- 不绕过 `PlotThread` 状态机。
- 不做 Task 167 的主动伏笔调度。

## 关键规则

- `draft` proposal 不能 apply。
- `rejected` proposal 不能 apply。
- `applied` proposal 不能二次 apply。
- 对 `PlotThread` 的状态相关变更必须复用或遵守 `NarrativeRepository` 的合法状态迁移规则。
- 对 list 字段的变更必须做结构化 JSON diff，不允许字符串拼接。
- 对 style constraint 的存储若无现成表，应在 166b 中选择最小事实源；不能塞进 LangGraph state。

## 测试要求

目标测试：

```powershell
python -m pytest tests/test_166b_replan_application.py -q
```

必要覆盖：

- [x] approve/reject 状态流转。
- [x] draft proposal apply 被拒绝。
- [x] approved proposal apply 成功。
- [x] applied proposal 二次 apply 被拒绝。
- [x] reject proposal 不修改 ArcPlan / PlotThread。
- [x] action 失败时事务 rollback。
- [x] list 字段结构化更新。
- [x] apply 后 repository 回读一致。

收尾：

```powershell
python -m pytest tests/ -q
ruff check src/ tests/
```

## 验收标准

- [x] approved proposal 可事务化应用。
- [x] 所有 action 有 old/new diff 与 reason。
- [x] rejected / draft / applied 状态保护生效。
- [x] 无任何正文或历史章节被修改。
- [x] 生成 `archive/v7/tasks/166b-approved-replan-application-DONE.md`。

## 参考文档

- `archive/v7/tasks/166-plan-generate-replan-loop.md`
- `archive/v7/tasks/166a-arc-outcome-evaluation-and-replan-proposal-DONE.md`
- `src/songyan/db/narrative_repo.py`
- `src/songyan/models/narrative.py`
