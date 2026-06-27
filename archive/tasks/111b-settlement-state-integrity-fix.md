# Task 111b: Settlement 与事实源一致性修复

> **Phase**: V5.0 Phase 4 前置修复 — SQLite 事实源与状态结算
> **优先级**: P0
> **依赖**: Task 111a 完成
> **预计工作量**: 1-2 天

---

## Goal

修复 accept、chapter version、settlement、summary、LangGraph state 之间的事实源一致性问题，确保每章 accepted 后不会留下“已接受但未结算”“结算校验失败却落库”“state 指向不存在记录”等长期污染。

## Context

V5.0 的长期稳定性依赖 SQLite 作为唯一事实源。整体 review 发现当前结算链路存在 P0 风险：

1. `human_gate_node` 先提交 `chapter_heads.accepted_version_id`，再单独更新 `chapter_versions.version_type='accepted'`，settlement 在后续节点另开事务执行。中途失败会留下半提交状态。
2. `extract_settlement()` 将 validation failed 的 settlement 标记为 `needs_human_review`，但 workflow 仍调用 `apply_settlement()` 写入角色状态、设定、伏笔和数值账本。
3. `write_chapter_summary()` 内部生成真实 summary id 并保存，但 `settlement_extractor_node` 丢弃返回值后又生成一个新的 `summary_id` 写入 state。
4. `context_manager_node` 将完整 `ContextPackage` 写入 LangGraph state，违反“state 只存 ID/控制字段”，也会放大 checkpoint 体积和序列化风险。

本 Task 优先保护长期事实源，避免 Task 112 长跑污染 DB。

## In Scope（必须完成）

- [ ] **阻止 validation failed settlement 落库**
  - `settlement.validation_status != "valid"` 时禁止调用 `apply_settlement`
  - state 返回 `_settlement_needs_human_review=True`
  - 日志记录 validation errors 和 version_id

- [ ] **修复 accept 与 settlement 的一致性边界**
  - 设计最小 UnitOfWork 或 staged accept 策略
  - 确保 accepted/current head、version accepted、settlement apply 的状态不会半提交
  - 若 settlement 失败，不能把该章标记为完整 accepted + settled

- [ ] **返回真实 summary_id**
  - `write_chapter_summary()` 返回真实落库 ID，或由节点生成并传入 repository
  - `settlement_extractor_node` state 中的 `summary_id` 必须能查到对应记录

- [ ] **清理 LangGraph state 中的完整 `ContextPackage`**
  - state 不再长期保存完整 `context_package`
  - 下游节点通过 helper 从 SQLite/Service 重新组装，或只传递轻量 context snapshot id / metrics
  - `_context_metrics`、`_budget_was_enforced` 等控制指标可保留

- [ ] **修复 HumanGate `inject` 路由契约**
  - 要么补齐 `inject` 的 router 分支和后续状态流
  - 要么从 interrupt options 中移除 `inject`
  - 不允许出现用户可选但 workflow 视为 unknown decision 的分支

## Out of Scope（明确不做）

- 不改 SettlementExtractor 的抽取 prompt
- 不调整 SettingEvaporator 策略
- 不重构完整 Repository 层
- 不跑 Ch101-Ch150 长跑验证

## 接口契约

```python
async def accept_with_settlement_boundary(
    *,
    project_id: str,
    chapter_number: int,
    version_id: str,
    settlement: StateSettlement | None,
) -> None:
    """在一致性边界内完成 accept 与 settlement 状态更新."""
    ...
```

```python
async def write_chapter_summary(...) -> tuple[str, ChapterSummary]:
    """写入章节摘要并返回真实 summary_id 与摘要对象."""
    ...
```

## 数据模型

不强制新增 SQLite 表。若需要记录 settlement pending 状态，应优先复用现有 `chapter_heads.status` 或已有 run log 字段，避免扩大 schema 面。

## 测试要求

### Layer 1: 模型/Repository 测试
- [ ] validation failed settlement 不调用任何写入角色/设定/伏笔/数值账本的 repository 方法
- [ ] `summary_id` 能从 repository 读取到真实 summary

### Layer 2: 工作流节点测试
- [ ] settlement validation failed 时章节不被标记为完整 settled
- [ ] settlement LLM/解析失败时不会留下 accepted + missing settlement 的静默成功状态
- [ ] HumanGate `inject` 选择不会进入 unknown decision
- [ ] state 中不再出现完整 `ContextPackage`

### Layer 3: 回归测试
- [ ] skip-settlement 成功路径仍能生成 fallback summary 并维护 context
- [ ] Task 107 的 best_version 回滚 + skip settlement 逻辑不回退

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/ -v` 全部通过
- [ ] `pytest tests/ -q` 全量回归无新增失败
- [ ] `ruff check src/ tests/` 无新增 lint 错误
- [ ] 不违反 AGENTS.md P0 #1、#2、#4、#6、#7、#24、#25、#26、#27、#29、#30
- [ ] 生成 `tasks/111b-settlement-state-integrity-fix-DONE.md`
- [ ] 更新 `docs/STATUS.md`
- [ ] Git commit 包含代码、测试、DONE 文档和状态更新

## 参考文档

- `AGENTS.md` — P0 数据与状态、状态结算规则
- `.trae/specs/review-agent-workflow-consistency/spec.md` — 整体 review 规格
- `tasks/107-repair-convergence-guardrail-DONE.md` — skip settlement 与 convergence guardrail 历史修复

## 下一 Task

**Task 111c: Context 与 Prompt 一致性修复**
