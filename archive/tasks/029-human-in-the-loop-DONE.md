# Task 029: Human-in-the-Loop 增强（已完成）

> **Phase**: Phase 2
> **优先级**: P0
> **依赖**: Task 028（Punch Engine）
> **完成日期**: 2026-06-02
> **执行者**: AI Agent

---

## 完成项

- [x] 新增 `HumanInstruction` 数据模型：`instruction_type` / `content` / `priority` / `chapter_scope` / `created_at`
- [x] 新增 `human_instructions` DB 表（`IF NOT EXISTS`）
- [x] 改造 `human_confirm_node` → `human_gate_node`：
  - 保留 `accept/edit/reject/back` 四种决策
  - 新增 `inject` 决策：人类注入自由指令（最高优先级）
  - `edit` 时自动记录 `rewrite` 类型的 `HumanInstruction`
  - 保留 `human_confirm_node = human_gate_node` 别名兼容旧代码
- [x] `ContextPackage` 新增 `human_instructions: list[HumanInstruction]` 字段
- [x] `context_manager_node` 将 `human_instructions` 从 state 注入 `ContextPackage`
- [x] Writer Prompt 新增"人类指令（最高优先级）"区块（Jinja2 条件渲染）
- [x] Writer `_render_prompt()` 注入 `human_instructions` 变量
- [x] CLI 新增 `run` 命令：
  - `--project-id` / `--chapters` / `--human-gates` / `--auto-confirm`
  - 支持批量章节生成和人工门控点配置
- [x] 测试：38 passed

---

## 关键决策

### human_gate_node 重命名但保留别名
将 `human_confirm_node` 重命名为 `human_gate_node` 以反映功能扩展（不仅是"确认"，还包括"注入"），但保留 `human_confirm_node = human_gate_node` 别名。这确保所有现有调用点无需修改。

### inject 作为最高优先级指令
`inject` 决策不直接修改章节内容，而是将人类指令写入 `human_instructions` 表，由下一章的 `ContextPackage` 携带进入 Writer Prompt。这样人类可以在任意断点注入修改意见，Writer 在下一章执行时自动读取。

---

## 基线验证

| 指标 | 目标 | 验证方式 |
|------|------|----------|
| 意图执行率 | ≥ 90% | 人工注入指令后 Writer Prompt 正确渲染 |
| 别名兼容性 | 100% | `human_confirm_node` 别名调用不报错 |

---

## 交付物

- `src/songyan/models/human_instruction.py` — `HumanInstruction` 模型
- `src/songyan/workflows/_nodes.py` — `human_gate_node`
- `src/songyan/agents/writer.py` — 人类指令区块渲染
- `src/songyan/agents/context_manager.py` — `human_instructions` 注入 `ContextPackage`
- `src/songyan/cli/commands.py` — `run` 命令
- `src/songyan/db/schema.sql` — `human_instructions` 表
- `src/songyan/db/migrations.py` — 增量迁移

---

## 遗留风险

| 风险 | 严重度 | 说明 |
|------|--------|------|
| 无重大遗留 | — | HITL 功能完整，inject/edit/accept/reject/back 均正常工作 |

---

## 下一步

**Task 030: ContinuityAuditor — 跨章一致性引擎**
- 消除跨章断点，自动发现设定/道具/角色的不一致
- 每 3 章自动审计一次
