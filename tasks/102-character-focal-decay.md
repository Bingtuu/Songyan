# Task 102: CharacterFocalDecay — 角色焦点衰减

> **Phase**: V5.0 Context Diet 2.0 — 核心组件 2/4
> **优先级**: P0
> **依赖**: Task 101（TemporalCompressor 完成）
> **预计工作量**: 1-2 天

---

## Goal

角色档案的详细度随"未出场章数"指数衰减，控制活跃角色信息池的大小。

---

## Context

### 当前问题

`character_states` 是快照表，永远 INSERT 不 UPDATE。ContextManager 加载角色时：
- 不出场的角色：已按规则 42 不加载详细档案
- 但**出场过的角色**：即使 20 章没出场，仍然加载完整档案（心理、目标、关系）
- Ch50 时活跃角色 4-8 个，Ch100 时可能膨胀到 10-15 个

### 衰减规则

| 未出场章数 | 加载内容 | token 估算 |
|-----------|---------|-----------|
| 0-3 章 | 完整档案（心理、目标、关系、当前状态） | ~800 |
| 4-10 章 | 精简档案（现状 + 当前目标 + 核心关系） | ~400 |
| 11-30 章 | 符号档案（名字 + 一句话定位 + 最后已知状态） | ~100 |
| 30+ 章 | 不加载（出场时由 RAG 检索或人类注入） | 0 |

---

## In Scope

- [ ] **`CharacterStateRepository.load_by_chapter()` 增强**: 增加 `last_appeared_chapter` 过滤 + 衰减逻辑
- [ ] **档案模板分级**:
  - `full_profile`: 完整档案（心理模型 + 目标 + 关系网 + 近期变化）
  - `compact_profile`: 精简档案（现状 + 当前目标 + 核心关系）
  - `symbol_profile`: 符号档案（名字 + 一句话定位 + 最后状态）
- [ ] **出场追踪**: SettlementExtractor 记录每个角色的 `last_appeared_chapter`
- [ ] **单元测试**: 不同衰减级别的角色档案正确生成
- [ ] **Ch55 单章验证**: 确认衰减后 `character_states` token 减少 ≥ 30%

## Out of Scope

- 不修改 SettlementExtractor 的核心结算逻辑（只增加出场记录）
- 不删除现有角色档案格式
- 不修改 Writer Prompt

---

## 验收标准

| 指标 | 目标 |
|------|------|
| Ch55 `character_states` token 数 | < Ch50 的 70% |
| 衰减规则覆盖率 | 100% 角色按未出场章数正确分级 |
| `last_appeared_chapter` 准确率 | ≥ 95%（与正文章节号一致） |
| Ch55 单章达标率 | ≥ 75% |
| 测试通过 | pytest 新增测试全部通过 |

---

## 技术要点

- `character_states` 表已有 `lifecycle_status`（active/dormant/archived），但衰减是**独立于生命周期**的加载策略
- 衰减逻辑在 Repository 查询层实现，不修改 DB schema
- `full_profile` 用现有格式；`compact_profile` 和 `symbol_profile` 是裁剪后的变体
- `last_appeared_chapter` 从 `chapter_character_appearances` 表或 Settlement 输出中提取

---

## 风险

- **角色"失忆"导致一致性断裂**: 衰减过猛时，Writer 忘记角色之前的设定
- **缓解**: 核心角色（protagonist, antagonist）永不衰减（配置 `core_characters` 列表）
