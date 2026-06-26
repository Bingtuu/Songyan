# Task 121r: Prompt Quality Cleanup Execution

> **日期**: 2026-06-23
> **类型**: V5.1 Prompt 修复
> **状态**: TODO
> **前置**: Task 121k Prompt Quality Cleanup Plan

---

## 1. 任务边界

承接 Task 121k 的规划，执行 Prompt / 正文质量修复。

本任务不修改 SQLite 事实源契约，不修改 SettlementExtractor 校验规则，不放宽 QualityGate 阈值（该工作由 Task 121q 负责）。

---

## 2. 已知问题

Task 121g / `run-0fd1456e` 中观察到：
- 多章正文存在机械场景标题（`### Scene 1:`）
- 个别章节出现 `<!-- -->` 元标记泄漏
- Ch113-Ch115 短段落比例偏高（65% ~ 70%）
- Ch111-Ch115 窗口 QG false / convergence_failed 密度升高

---

## 3. 修复范围

### 3.1 Writer Prompt

- 明确正文不得包含 markdown 标题、HTML 注释、元数据标签
- 场景切换必须以自然叙事段落完成，不使用 `Scene` 标题
- 对"记忆/协议/系统说明"内容要求转化为动作、选择、冲突和可感知细节
- 控制连续短段落，避免单句段落堆叠

### 3.2 CreativeDirector Prompt

- 将 tension / forbidden patterns 写成可执行约束
- 对高概念信息释放增加"行动承载"要求
- 避免让章节目标退化为设定说明清单

### 3.3 RuleAuditor / Quality Metrics

- 增加正文元标记检测（观测指标，不直接阻断）
- 增加 markdown 场景标题检测（观测指标，不直接阻断）
- 增加短段落比例观测指标

---

## 4. 验证方式

- Ch1-Ch5 抽样验证，确认无元标记泄漏、无场景标题
- Ch111-Ch115 聚焦窗口，确认短段落比例下降

---

## 5. 交付标准

- [ ] Writer / CreativeDirector Prompt 更新
- [ ] RuleAuditor 检测新增
- [ ] 抽样验证通过
