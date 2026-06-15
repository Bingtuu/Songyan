# Task 029: Human-in-the-Loop 增强

> **Phase**: Phase 2
> **优先级**: P0
> **依赖**: Task 028（Punch Engine）已完成
> **核心目标**: 建立深度协作接口，人类可自由注入修改意见、指令或完整内容

---

## Goal

将僵化的"接受/编辑/拒绝/回退"人工确认升级为灵活的深度协作接口，支持人类在创作流程中注入自由指令或直接改写内容。

## In Scope

- [x] 新增 `HumanInstruction` 数据模型
- [x] 新增 `human_instructions` DB 表
- [x] 改造 `human_confirm_node` → `human_gate_node`：
  - 保留 `accept/edit/reject/back` 决策
  - 新增 `inject` 决策：人类注入自由指令
  - `edit` 时记录 `rewrite` 类型 HumanInstruction
  - 保留 `human_confirm_node` 别名兼容旧代码
- [x] `ContextPackage` 新增 `human_instructions` 字段
- [x] `context_manager_node` 将 `human_instructions` 从 state 注入 ContextPackage
- [x] Writer prompt 新增"人类指令（最高优先级）"区块
- [x] Writer `_render_prompt()` 注入 `human_instructions` 变量
- [x] CLI 新增 `run` 命令，支持 `--project-id`、`--chapters`、`--human-gates`、`--auto-confirm`
- [x] 测试全部通过

## Out of Scope

- 不新增 pre-write gate 节点（避免大幅改变 graph 结构）
- 不修改 RevisionHandler 消费 human_instructions（Phase 2 后续迭代）
- 不修改 SettlementExtractor 消费 human_instructions
- 不新增 audit_report gate 和 settlement_extraction gate

## 回滚策略

- `human_confirm_node = human_gate_node` 别名保留，兼容旧代码
- `auto_confirm=True` 时行为完全不变
- `ContextPackage.human_instructions` 默认为空列表
- `human_instructions` 表不影响现有表

## 验收标准

- [x] `pytest tests/` 全部通过（153 targeted tests passed）
- [x] `human_confirm_node` 别名工作正常
- [x] `ContextPackage` 支持 `human_instructions`
- [x] Writer prompt 条件渲染人类指令区块
- [x] CLI `run` 命令可导入

## 参考

- `docs/architecture/roadmap_v2_phases.md` — Phase 2 详细设计
