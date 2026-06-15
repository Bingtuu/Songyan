# Task 077b 交接报告 — BudgetPruner 硬断言（核裁通道）

> **状态**: ✅ 已完成
> **完成日期**: 2026-06-07
> **关联 Task**: 077a（分层 Setting 库），076（Writer 字数截断）
> **测试覆盖**: 15 个单元测试，全部通过

---

## 完成的工作

### 1. HARD_ENFORCE_THRESHOLD 常量

- `src/songyan/agents/context_manager/__init__.py` 中新增 `HARD_ENFORCE_THRESHOLD: float = 1.3`
- 含义：当 `prune()` 常规裁剪后 token 总数仍超过 `budget_tokens × 1.3` 时触发硬断言

### 2. _enforce_budget_hard() 核裁方法

6 步逐级丢弃，不裁剪 `hard_constraints` / `genre_rules` / `mode_rules`：

| Step | 分区 | 丢弃策略 |
|------|------|----------|
| 1 | dialogue_style_cards | 全部丢弃 |
| 2 | open_threads | 只保留 priority > 0.8，上限 2 |
| 3 | soft_references | 按 relevance_score 排序，保留 Top-4 |
| 4 | foreshadowing | 只保留 status in ("due", "overdue") |
| 5 | character_states | 只保留 importance_score >= 0.9 |
| N | 核裁保底 | 逐项丢弃直到达标或无可裁分区 |

- 每步独立检查 `_over()`（基于原始预算，非阈值化预算）
- 每步输出结构化日志：`context_manager.hard_enforce`
- 优先丢弃 Token 占比大的分区，避免轻微超标时过度裁剪

### 3. _budget_enforced 传播

- `ContextPackage._budget_enforced: bool = False` — 标记是否触发硬断言
- `Phase1State._budget_was_enforced: bool` — LangGraph state 携带该标记
- `_nodes.py context_manager_node()` 在 return dict 中注入 `"_budget_was_enforced": ctx._budget_enforced`
- 传播路径：`prune() → ContextPackage → Phase1State → downstream nodes`

### 4. 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| src/songyan/models/context.py | 修改 | ContextPackage 增加 _budget_enforced 字段 |
| src/songyan/workflows/phase1_graph.py | 修改 | Phase1State 增加 _budget_was_enforced 字段 |
| src/songyan/workflows/_nodes.py | 修改 | context_manager_node() 注入 _budget_was_enforced |
| src/songyan/agents/context_manager/__init__.py | 修改 | HARD_ENFORCE_THRESHOLD + _enforce_budget_hard() + prune() 集成 |
| tests/test_077b_budget_hard_enforcement.py | 新增 | 15 个单元测试 |

### 5. 测试结果

```
15 passed in 0.49s
覆盖：触发条件(3) + 丢弃顺序(6) + 保护分区(1) + flag 标记(3) + 边界情况(2)
```

回归测试（排除已有 embedding benchmark 问题）：103 passed，0 regression

---

## 架构设计决策

1. **核裁在 prune() 末尾触发**，而非覆盖 prune() 逻辑
   - `prune()` 先做常规按优先级裁剪（现有逻辑）
   - 若仍超阈值 → `_enforce_budget_hard()` 做降级裁剪
   - 两者解耦，互不影响

2. **1.3x 阈值** = 默认预算的 130%
   - 1.0x~1.2x 区间由常规 prune 覆盖
   - 1.3x+ 触发核裁，意味常规裁剪已耗尽
   - 可根据运行经验调整（如改到 1.5 降低触发频率）

3. **`_budget_enforced` 是标记而非阻断**
   - 下游节点可检查 `_budget_was_enforced` 获取上下文被严重裁剪的信号
   - 不影响 writer/auditor 的正常流程
   - 人工可在产出的 CreativeBrief 末尾看到标记

---

## 已知限制

1. `_over()` 基于 `_estimate_package()` 的静态估算，与真实 tokenizer 可能有 10-20% 偏差
2. 核裁后 `character_states` 完整性可能受影响（如男主状态被裁剪）
3. 尚无降级后重试机制（如裁剪后 Writer 产出不够好 → 自动扩预算重试）

---

## 与 077a 的边界

- **077a**：入站环节过滤，从源头减少 setting_snapshots 输入
- **077b**：出站环节兜底，ContextPackage 组装后核裁超预算分区
- 两者互补：077b 不受 077a 影响，可独立验证

---

## 验收状态

- [x] 1.3x 阈值触发硬断言，核裁生效
- [x] 6 步降级丢弃按优先级有序执行
- [x] 核裁后 `_budget_enforced=True`，向下游传播
- [x] hard_constraints/genre_rules/mode_rules 永不丢弃
- [x] 所有步骤有结构化日志
- [x] 不违反 AGENTS.md 规则
- [x] 生成 DONE 交接报告
- [x] 更新 STATUS.md
