# Task 121k: Prompt Quality Cleanup Plan

> **日期**: 2026-06-22
> **类型**: V5.1 quality / prompt cleanup
> **状态**: TODO
> **前置**: Task 121g 质量复盘已发现正文机械化与纯净度问题；Task 121h/121i/121j 负责工程修复与 single-run 证据。

---

## 1. 任务边界

本任务处理 Task 121g 暴露但不应混入 Ch115 工程修复的 Prompt / 正文质量问题。

本任务聚焦：

- 禁止正文输出 markdown 场景标题，如 `### Scene 1:`。
- 禁止正文输出 HTML 注释或元数据标记，如 `<!-- ... -->`。
- 降低短段落碎片化比例。
- 改善记忆、协议、系统说明类章节的信息堆叠。
- 提高后段 readability / momentum 的稳定性。

不做：

- 不修改 SQLite 事实源契约。
- 不修改 SettlementExtractor 校验规则。
- 不放宽 QualityGate 阈值。
- 不承担 Ch1-Ch150 single-run 工程证据；该步骤归 Task 121j。

---

## 2. 已知质量问题

Task 121g / `run-0fd1456e` 中观察到：

- 多章正文存在机械场景标题。
- 个别章节出现 `<!-- -->` 元标记泄漏。
- Ch113-Ch115 短段落比例偏高，约 `65% ~ 70%`。
- Ch111-Ch115 窗口 QG false / convergence_failed 密度升高。
- Ch114 readability 低至 `0.484`。
- Ch115 在 rewrite 后由高分候选劣化为截断版本。

---

## 3. 候选修复范围

### 3.1 Writer Prompt

调整方向：

- 明确正文不得包含 markdown 标题、HTML 注释、元数据标签。
- 场景切换必须以自然叙事段落完成，不使用 `Scene` 标题。
- 对“记忆/协议/系统说明”内容要求转化为动作、选择、冲突和可感知细节。
- 控制连续短段落，避免单句段落堆叠。

### 3.2 CreativeDirector Prompt

调整方向：

- 将 tension / forbidden patterns 写成可执行约束。
- 对高概念信息释放增加“行动承载”要求。
- 避免让章节目标退化为设定说明清单。

### 3.3 RuleAuditor / Quality Metrics

候选增强：

- 增加正文元标记检测。
- 增加 markdown 场景标题检测。
- 增加短段落比例观测指标。

注意：本任务可新增质量检测，但不应直接扩大阻断范围，除非已有足够实跑证据证明误伤率可控。

---

## 4. 验证方式

建议先做小窗口验证：

- Ch111-Ch115 聚焦窗口。
- Ch1-Ch20 早期窗口，确认不引入新阻断。
- 对比 Prompt 调整前后的 readability、momentum、短段落比例、元标记命中数。

通过后再考虑接入 full single-run。

---

## 5. 验收标准

本任务完成需满足：

- 抽样正文无 `<!-- -->` 元标记。
- 抽样正文无 `### Scene` / `Scene N` 机械标题。
- 短段落比例有可观测下降，或至少不再集中超过 65%。
- readability / momentum 不低于调整前窗口基线。
- 聚焦测试和 lint 通过。
- 若新增规则检测，必须有测试覆盖和误伤说明。

---

## 6. 后续

- 若 Task 121j 已完成 150/150，可将 Task 121k 作为 V5.1 质量专项推进。
- 若 Task 121j 仍因质量门阻断，Task 121k 的 Prompt 调整可作为下一轮修复输入。
