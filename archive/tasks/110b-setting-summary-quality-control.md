# Task 110b: Setting/Summary/HardConstraint 生产端质量控制

> **Phase**: V5.0 Phase 4 准备 — 结构与质量控制
> **优先级**: P0
> **依赖**: Task 110a 完成
> **预计工作量**: 2-3 天

---

## Goal

解决设定 key 不规范、摘要过长、hard_constraints 膨胀等生产端问题，提升信息密度和可检索性。

---

## Context

### 当前问题

1. **Setting key 不规范**：105b 中 Ch99-Ch100 出现 `anomaly_x.communication_antenna_construction` 等不符合 `category.subcategory.name` 格式的 key，导致 SettingEvaporator 去重和 critical 判断失效。
2. **Summary 过长**：SummaryWriter 输出可能包含过多描写细节，增加 downstream token 负担。
3. **HardConstraints 膨胀**：marks 和 obligations 累积，挤压其他分区空间。

---

## In Scope

- [ ] **Setting key 规范化**
  - settlement 写入 setting 前强制校验 key 格式
  - 不符合规范的 key 不入 `setting_snapshots`，仅作为临时背景
  - 提供 fallback key 生成规则（基于 setting_name 关键词）

- [ ] **Setting 版本化增强**
  - 同一 setting_key 多次更新时，旧版本自动 archived
  - 只保留最新版本为 active
  - 增强 Task 110 的去重效果

- [ ] **SummaryWriter 模板化输出**
  - 输出格式固定为：关键事件 / 角色变化 / 新设定伏笔 / 情绪转折 / 下章钩子
  - 每部分设置最大字数限制
  - 删除环境描写和对话原文

- [ ] **Summary 关键事实验证**
  - 检查 summary 是否包含 protagonist 决策变化
  - 检查新设定/伏笔是否被记录
  - 超长时按优先级截断（保留关键事件，删除描写）

- [ ] **HardConstraint 长度审计**
  - 限制 obligations 总数（按章节阶段动态调整）
  - 限制 mark.note 长度
  - 超过 budget 20% 时只保留高 priority marks

## Out of Scope

- 不修改 SummaryWriter 的 Prompt 内容（只改输出后处理/截断）
- 不新增 Agent/Workflow 节点
- 不删除已有 setting/summary 历史记录

---

## 验收标准

| 指标 | 目标 |
|------|------|
| setting key 规范率 | 100%（新写入） |
| 单章 summary 字数 | ≤ 500 字（含 arc summary ≤ 800 字） |
| hard_constraints token | Ch90+ 较 105b 下降 ≥ 20% |
| 关键事实覆盖率 | summary 验证通过 ≥ 95% |
| 全量回归测试 | 无新增失败 |

---

## 技术要点

- 修改 `settlement_extractor/_apply.py` 中 setting 写入逻辑
- 修改 `summary_writer/` 节点输出后处理
- 修改 `_build_hard_constraints` 增加长度上限
- 增加 `_validate_setting_key(key)` 和 `_fallback_setting_key(name)` 辅助函数

---

## 风险

- **key 规范化导致信息丢失**：临时性设定被丢弃。缓解：保留到正文中，可通过 RAG 检索。
- **summary 模板化让摘要变干**：可能丢失情绪转折。缓解：保留"情绪转折"部分不被截断。
- **marks 截断影响人工干预**：高 priority marks 仍完整保留。
