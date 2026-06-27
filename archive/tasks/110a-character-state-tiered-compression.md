# Task 110a: CharacterState 分层保真压缩

> **Phase**: V5.0 Phase 4 准备 — 生产端保真压缩
> **优先级**: P0
> **依赖**: Task 107-109 完成
> **预计工作量**: 2-3 天

---

## Goal

解决 `character_states` 字段值膨胀问题，但不是粗暴截断，而是按角色重要性分层保真压缩，确保关键事实不丢失。

---

## Context

### 当前问题

105b 验证显示，Ch90+ 的 `mental_state`、`physical_state`、`protocol_status` 等字段已膨胀到数百字。这些长文本直接进入 ContextPackage，是 budget 超标和 ContextEmergency 频发的主因之一。

### 核心原则

**保真 ≠ 保长度**。保留叙事功能所需的关键事实，删除修辞、过程描写和重复状态。

---

## In Scope

- [ ] **角色分层策略定义**
  - protagonist：核心字段完整保留或轻度结构化
  - antagonist：关键字段完整保留
  - supporting：结构化压缩（标签 + 触发事件 + 影响）
  - functional：极简保留（位置 + 一个状态标签）

- [ ] **字段级压缩规则**
  - `location`：不压缩，标准化格式
  - `goals` / `relationships`：保留变化，限制单条长度
  - `mental_state`：提取 `mood` + `trigger` + `impact`
  - `physical_state`：提取 `status` + `action_impact`
  - `protocol_status`：提取 `system_state` + `available_actions`

- [ ] **关键事实清单（Critical Facts）**
  - settlement 阶段提取该章不可丢失事实
  - 压缩后验证这些事实是否仍能被覆盖

- [ ] **压缩后质量验证**
  - 规则检查：主角 last_goal 是否保留、关系变化是否记录
  - source_version_id 和 source_quote 保留，支持原文恢复

- [ ] **加载端适配**
  - `_build_character_snapshots` 理解分层压缩后的结构
  - 不因格式变化而丢失信息

## Out of Scope

- 不修改 Writer Prompt
- 不新增 Agent/Workflow 节点
- 不对 location 等不可压缩字段做截断
- 不删除已写入的历史状态记录（只改未来生产）

---

## 验收标准

| 指标 | 目标 |
|------|------|
| 单章 character_states token | Ch90+ 较 105b 下降 ≥ 30% |
| ContextEmergency 次数 | Ch80-Ch100 较 105b 下降 ≥ 30% |
| 关键事实丢失率 | 0%（通过规则验证） |
| 全量回归测试 | 无新增失败 |
| ruff 检查 | 修改文件无新增 lint |

---

## 技术要点

- 修改 `settlement_extractor/_apply.py` 中写入 `character_states` 前的逻辑
- 在 `context_manager/_assemblers.py` 中按角色层级解析压缩后的字段
- 引入 `MAX_STATE_VALUE_LENGTH` 常量，但 protagonist 可豁免
- 增加 `_extract_state_summary(value, field, role_type)` 辅助函数

---

## 风险

- **过度压缩**：supporting 角色的心理状态可能丢失细微转折。缓解：保留 `trigger` 字段记录转折点。
- **格式不兼容**：旧数据是长文本，新数据是结构化。缓解：加载端兼容两种格式。
- **主角状态仍膨胀**：protagonist 字段不压缩可能导致 budget 仍高。缓解：对 protagonist 做轻度结构化而非完整保留。
