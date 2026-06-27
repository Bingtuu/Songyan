# Task 104: BudgetHardCeiling — 预算硬天花板

> **Phase**: V5.0 Context Diet 2.0 — 核心组件 4/4
> **优先级**: P0
> **依赖**: Task 103（SettingEvaporator 完成）
> **预计工作量**: 1 天

---

## Goal

确保 `budget_used` 永不超过 1.0。超预算时触发 ContextEmergency，强制降级到最小上下文。

---

## Context

### 当前问题

`BudgetPruner` 的 `fullness_factor = 1.0 - fullness * 0.5` 在 `fullness=0.9` 时：
- `fullness_factor = 1.0 - 0.9 * 0.5 = 0.55`
- 仍然可能 `budget_used > 1.0`（当硬约束本身已接近预算上限时）

当前没有**绝对硬 ceiling**，Writer 可能拿到超载的上下文包。

### 目标行为

| budget_used | 动作 |
|-------------|------|
| < 0.90 | 正常加载（Context Diet 2.0 标准流程） |
| 0.90 ~ 1.00 | aggressive 裁剪（focal_distance=close，软参考清空） |
| > 1.00 | **ContextEmergency**：只保留硬约束 + 主角档案 + ChapterGoal |

---

## In Scope

- [ ] **`_dynamic_fullness_factor` 调参**: `fullness * 0.5` → `fullness * 0.7`
- [ ] **ContextEmergency 分支**: `budget_used > 1.0` 时的强制降级逻辑
- [ ] **Emergency 上下文包**:
  - 保留：genre_rules, mode_rules, chapter_goal, creative_brief, protagonist_profile
  - 丢弃：所有 soft_references, 非核心角色, 历史摘要（除最近 1 章）
- [ ] **`context_emergency` 记录**: 写入 `generation_metadata`，供流式验证监控
- [ ] **单元测试**: emergency 触发正确；emergency 后 token < budget
- [ ] **Ch65 验证**: budget_used > 1.0 时 emergency 触发，不崩溃

## Out of Scope

- 不修改 Writer Prompt
- 不修改 Agent 签名
- 不影响正常路径（budget_used < 0.9 时行为不变）

---

## 验收标准

| 指标 | 目标 |
|------|------|
| `fullness_factor` 公式 | `1.0 - fullness * 0.7` |
| ContextEmergency 触发阈值 | `budget_used > 1.0` |
| Emergency 后 token 数 | < budget × 0.95 |
| Emergency 触发率（Ch51-Ch65） | < 10% |
| 测试通过 | pytest 新增测试全部通过 |

---

## 技术要点

- ContextEmergency 是**最后防线**，不是正常路径。频繁触发说明 Context Diet 2.0 前面组件失效
- Emergency 后 Writer 的上下文极度精简，可能导致叙事质量下降，但这是"有记录的可控降级"而非"崩溃"
- `context_emergency` 字段供流式验证监控：若某项目连续 3 章触发 emergency，自动告警

---

## 风险

- **Emergency 过于 aggressive**: 正常章节因计算误差触发 emergency
- **缓解**: 阈值用 `budget_used > 1.05`（留 5% 缓冲），或增加"连续 2 章超预算才触发"
