# Task 090b: Rewrite 字数护栏 + One-shot Revision 修复

> **Phase**: V4.0 Phase B — Agent 约束硬化
> **优先级**: P0
> **依赖**: Task 088, 089, 090
> **预计工作量**: 小（1 天）
> **状态**: 🔄 待执行

---

## Goal

修复 `rewrite_node` 导致的字数达标率系统性劣化。为 rewrite 注入字数约束指令（±25% 软约束），并允许 rewrite 后保留 **1 轮 revision** 做最终修正，而非直接 pass。

---

## Context

Task 090a 端到端验证（`task_090a_scifi_webnovel_tightened`）表面达标率 57.9%，但数据库版本链分析揭示：

- **6 个章节**（Ch3, Ch7, Ch12, Ch14, Ch15, Ch16）在 revision 两轮后字数已接近/达标，触发 `rewrite_node` 后字数剧烈失控
- `rewrite_node` 调用 `write_chapter()` 时**未注入任何字数约束**，且 rewrite 后 `_was_rewritten=True` 导致 `revision_router` 直接 pass，不再修正
- 如果没有 rewrite 漏洞，仅接受 revision 最终版字数，达标率应为 **~79%** 而非 57.9%

本 Task 在 Phase B 约束硬化框架下，用最小改动封堵该漏洞，同时给叙事创作保留合理空间。

---

## In Scope（必须完成）

- [ ] **`rewrite_node` 注入字数约束**：向 `ctx.human_instructions` 追加 `word_count_constraint` 类型指令，明确要求 rewrite 后字数落在目标 ±25% 内
- [ ] **`revision_router` 放开一轮 revision**：`_was_rewritten=True` 时不再直接 pass，允许 `revision_round=0` 时进入 1 轮 revision，`>=1` 时强制 pass
- [ ] **测试更新**：新增/更新 `revision_router` 路由逻辑测试，覆盖 rewrite → revise → pass 路径
- [ ] **端到端快速验证**：选取 Ch12/Ch15/Ch16 种子运行，确认 rewrite 后字数落在 ±25% 内
- [ ] **生成 `tasks/090b-rewrite-word-count-guardrail-DONE.md`**

## Out of Scope（明确不做）

- 不改 Writer 初稿阈值（保持 1.20x/0.80x）
- 不改 RevisionHandler 阈值（保持 1.25x/0.75x）
- 不新增 Agent、Workflow 节点、Prompt 版本
- 不做 Ch21+ 长程验证（Task 091）
- 不做 Prompt 调优（V3.1 范围外）

---

## 接口契约

无新增公共接口，行为变更如下：

```python
# revision_router 行为变更
# 变更前：was_rewritten=True → 直接 "pass"
# 变更后：was_rewritten=True → needs and rround<1 → "revise", 否则 "pass"

def revision_router(state: Phase1State) -> str:
    ...
```

---

## 数据模型

无新增或修改 Pydantic 模型。`human_instructions` 列表中新增 `type="word_count_constraint"` 条目：

```python
{
    "type": "word_count_constraint",
    "content": "【重写约束】本章目标字数为 3000。重写后正文必须控制在 2250 ~ 3750 字之间..."
}
```

---

## 测试要求

### Layer 2: 模块测试
- [ ] `revision_router` 正例：
  - `was_rewritten=False, rround=0, needs=True` → `"revise"`
  - `was_rewritten=False, rround=2, needs=True` → `"rewrite"`
  - `was_rewritten=True, rround=0, needs=True` → `"revise"`（**新增**）
  - `was_rewritten=True, rround=1, needs=True` → `"pass"`（**新增**）
  - `was_rewritten=True, rround=0, needs=False` → `"pass"`
- [ ] `rewrite_node` 注入指令验证：Mock `write_chapter`，断言传入的 `context_package.human_instructions` 包含 `word_count_constraint`

### Layer 3: 集成测试（可选）
- [ ] 端到端单章验证：触发 rewrite 场景的章节，rewrite 后字数 `budget_used` ∈ [0.75, 1.25]

---

## 验收标准（Acceptance Criteria）

- [ ] `pytest -v` 全部通过（含新增/更新测试）
- [ ] 代码符合 AGENTS.md 规范（类型标注、单文件 < 400 行、异步优先）
- [ ] 不违反任何不可违背规则（尤其：RevisionHandler 只做 patch 不整章重写、Writer 只做初稿）
- [ ] 端到端验证：rewrite 触发章节字数落在 ±25% 内（Ch12/Ch15/Ch16 任意 2 章验证即可）
- [ ] 更新了 `docs/STATUS.md`（添加 090b 状态）
- [ ] 生成了 `tasks/090b-rewrite-word-count-guardrail-DONE.md` 交接文件

---

## 参考文档

- `tasks/090a-phase-b-ch1-ch20-e2e.md` — Task 090a 原始规格
- `tasks/090a-phase-b-ch1-ch20-e2e-DONE.md` — Task 090a 交接报告（含劣化分析）
- `src/songyan/workflows/phase1_graph.py` — `revision_router` 路由逻辑
- `src/songyan/workflows/_nodes.py` — `rewrite_node` 实现
- `src/songyan/agents/writer.py` — `write_chapter` 及 `human_instructions` 注入路径
