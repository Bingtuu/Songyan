# Task 103: SettingEvaporator — 设定蒸发器

> **Phase**: V5.0 Context Diet 2.0 — 核心组件 3/4
> **优先级**: P0
> **依赖**: Task 102（CharacterFocalDecay 完成）
> **预计工作量**: 2 天

---

## Goal

自动判断设定/伏笔是否已被叙事"自然覆盖"，低价值条目主动从上下文中移除，控制设定信息池的大小。

---

## Context

### 当前问题

`setting_snapshots` 和 `foreshadowings` 有 `lifecycle_status`（active/dormant/archived），但自动归档仅基于时间阈值（如 30 章未 resolve 则 archive）。这导致：
- 大量实际上已被正文遗忘的设定仍占 active 状态
- Ch50 时 active settings 可能仍有 30-50 条
- 时间阈值无法区分"被自然覆盖"和"被遗忘"

### 蒸发规则

| 条件 | 动作 | 触发时机 |
|------|------|---------|
| `resolve_confidence < 0.3` | archive | Settlement 后，轻量规则判断 |
| 连续 20 章未被任何 summary 引用 | archive | 生命周期调度器 |
| 被 LiteraryAuditor 标记 "已自然消解" | archive | Audit 后 |
| embedding 相似度 > 0.9 的重复设定 | 合并 | 每 50 章扫描 |

---

## In Scope

- [ ] **`resolve_confidence` 计算**: 基于设定被引用的频率、最近引用章节、与当前 narrative 的相关性
- [ ] **SettingEvaporator 节点**: SettlementExtractor 后的轻量规则节点（不调用 LLM）
- [ ] **设定合并逻辑**: 复用 RAG `Embedder` 计算设定 embedding 相似度，>0.9 合并
- [ ] **软约束降级**: `soft_references` 中指向已 archive 设定的条目自动降级或移除
- [ ] **单元测试**: 蒸发规则正确触发；合并后 setting_key 唯一
- [ ] **Ch60 验证**: active settings 数量 < Ch50 的 70%

## Out of Scope

- 不调用 LLM 做蒸发判断（纯规则，保性能）
- 不删除 DB 中的 setting_snapshots 记录（只改 `lifecycle_status`）
- 不修改 SettlementExtractor 核心逻辑

---

## 验收标准

| 指标 | 目标 |
|------|------|
| Ch60 active settings 数量 | < Ch50 的 70% |
| 蒸发误判率（archive 了仍需要的设定） | < 5%（人工抽检） |
| 设定合并准确率 | ≥ 90% |
| `resolve_confidence` 计算耗时 | < 10ms/章 |
| 测试通过 | pytest 新增测试全部通过 |

---

## 技术要点

- `resolve_confidence` 公式：
  ```
  confidence = 0.5 * (1 - chapters_since_last_reference / 50)
             + 0.3 * (narrative_relevance_score)
             + 0.2 * (is_hard_constraint ? 1.0 : 0.0)
  ```
- `narrative_relevance_score` 通过 RAG `Embedder` 计算设定与当前 ChapterGoal 的相似度
- 设定合并时，保留最早创建的 `setting_key`，其余指向它
- `SettingEvaporator` 在 SettlementExtractor 之后、SummaryWriter 之前执行

---

## 风险

- **误 archive 关键设定**: 纯规则判断可能误伤
- **缓解**: hard_constraint 标记的设定永不蒸发；误 archive 可在人类标记中恢复
