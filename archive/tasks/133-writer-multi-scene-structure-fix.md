# Task 133: Writer 多场景结构输出修复

> **类型**: 代码修复 / 质量强化  
> **日期**: 2026-06-27  
> **前置**: Task 121r（Prompt 质量清理）、Task 129（enforce 模式 Ch1–Ch50 验证）  
> **目标**: 修复 enforce 模式下 Writer 输出 `scenes_count=1` 的结构退化问题，确保每章至少输出 2 个可辨识场景，并能够被 RuleAuditor / parser 正确检测。

---

## 1. 背景与问题

`Task 129` enforce 模式验证（`run-89d7a2d4`）发现所有章节的 `scenes_count=1`，明显低于 Writer prompt 中“每章 2+ 场景”的要求。该问题直接导致：

- 可读性（readability）分数在 Ch3/Ch14/Ch15 跌至 0.2–0.3 区间。
- 连贯性（coherence）因场景切换不足而承压。
- enforce 模式下 quality gate streak 在 Ch15 触发 AutoHalt。

在 observe 模式下，该问题被 `degraded_accept` 和 human_marks 掩盖；一旦启用 enforce，便成为阻断性缺陷。

---

## 2. 根因假设（Brainstorming）

### 假设 A：Prompt 约束不够显式
Writer 1.1.0 虽然要求“空行分隔场景”，但未在输出格式中强制要求场景编号或场景标题，LLM 容易退化为单场景长段落。

### 假设 B：Parser 对场景边界的识别过宽
当前 parser 可能把整章识别为一个场景，或者对“空行+时间/地点切换”的启发式规则不足。

### 假设 C：RevisionHandler 在 patch 过程中破坏了场景结构
readability 专精路径可能为了修正段落节奏而合并场景，导致场景数下降。

### 假设 D：QualityGate / RuleAuditor 未把 `scenes_count` 作为硬指标
缺少对 `scenes_count < 2` 的明确惩罚，Writer 没有动力维持多场景结构。

---

## 3. 修复策略

1. **Prompt 强化**：在 Writer 1.2.0 工艺卡中明确要求输出至少 2 个场景，并使用统一场景分隔符（如双空行或 `### 场景 N` 标记）。
2. **Parser 校验**：在 `Writer` / `RuleAuditor` 中增加 `scenes_count` 计算逻辑，识别场景分隔符、时间/地点切换、人物转换等信号。
3. **RuleAuditor 新增规则**：`scene_structure_major` —— 若 `scenes_count < 2` 且字数 > 1500，记为 major issue，触发 RevisionHandler 结构调整。
4. **RevisionHandler 结构调整路径**：新增 `scene_split` patch 类型，按情节转折点将单场景长段落拆分为 2+ 场景。
5. **回归测试**：新增单元测试覆盖 parser 场景计数、RuleAuditor 场景结构规则、RevisionHandler scene_split patch。

---

## 4. 验收标准

- [ ] `pytest` 新增 8–12 个测试，覆盖场景计数、结构规则、patch 拆分。
- [ ] enforce 模式 Ch1–Ch20 验证中，`scenes_count >= 2` 的章节占比 ≥ 90%。
- [ ] 不破坏 observe 模式下 `run-a2bed648` 已验证的 150/150 成功路径。
- [ ] `ruff check src/ tests/` 通过。
- [ ] 输出 `archive/v5/tasks/133-writer-multi-scene-structure-fix-DONE.md`。

---

## 5. 依赖关系

```
Task 121r Writer 1.1.0 ──┐
Task 129 enforce 验证 ───┼──► Task 133 Writer 多场景结构修复
Task 130 模式决策 ───────┘   （为 V5.2 enforce 默认启用提供证据）
```

---

## 6. 风险与回滚

| 风险 | 影响 | 缓解 |
|------|------|------|
| 场景拆分过度导致片段化 | 可读性反而下降 | 设置最小场景字数（≥600 字/场景） |
| Parser 误判场景边界 | 误报 major issue | 使用多信号（空行 + 时间/地点 + 人物）联合判断 |
| Prompt 变化影响 observe 模式稳定性 | 破坏 150/150 基线 | 先在 Ch1–Ch20 小窗口验证，再扩到 Ch1–Ch150 |

---

## 7. 交付物

- `archive/v5/tasks/133-writer-multi-scene-structure-fix-DONE.md`
- Writer / RuleAuditor / RevisionHandler 相关代码改动
- 新增测试文件
- enforce 模式 Ch1–Ch20 验证报告
