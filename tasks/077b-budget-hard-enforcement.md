# Task 077b: BudgetPruner 硬断言

> **Phase**: V3.1 100章架构改造 — Phase A 止血
> **优先级**: P0
> **依赖**: 无（与 077a 互不依赖，可并行）
> **预计工作量**: 中（0.5-1 天）

---

## Goal

在 BudgetPruner 中增加**硬断言**——当逐层裁剪后仍超预算时，启动独立的核裁通道逐级丢弃低优先级分区，直到预算达标或无可裁分区。

这是**最后一道防线**：前面的分层 Setting 库（077a）从根源减少入站量，但无法预测所有场景。硬断言确保 budget 永远不会被突破 1.3 倍以上。

## Context

V3.1 验证报告 4.1.1（Token 预算不可恢复地超支）: Ch50 的 BudgetPruner 在逐层裁剪所有可裁分区后，final_tokens = 19175 >> budget 9600。当前实现只做了一件事：logger.warning()。System 在超载状态下继续运行。

Ch50 数据：
- current_tokens: 32139（预算的 3.3 倍）
- final_tokens: 19175（预算的 2.0 倍）
- 超预算 90-110% 是持续现象

现有的 BudgetPruner 已经做了逐层裁剪（soft_refs -> open_threads -> permanent_scenes -> foreshadowing -> recent_plot -> character_states -> hard_constraints/human_marks -> arc/volume），但如果全部完成后仍超预算，直接返回超载 ContextPackage。

**硬断言是独立通道**：不走两遍裁剪。逐层裁剪完成后，如果 still > budget x 1.3，启动核裁，用全新的丢弃逻辑（比逐层裁剪更激进）。

## In Scope

### 1. 新增 _enforce_budget_hard() 方法

在 BudgetPruner.prune() 末尾（逐层裁剪全部完成后）增加硬断言：

```python
HARD_ENFORCE_THRESHOLD: float = 1.3  # 超过预算 130% 触发

def _enforce_budget_hard(
    ctx: ContextPackage,
    budget: int,
) -> ContextPackage:
    """硬断言：逐级丢弃低优先级分区，直到预算达标或无可裁分区。
    从不裁剪: hard_constraints, genre_rules, mode_rules
    """
```

丢弃顺序（按优先级从低到高）：

1. dialogue_style_cards -> 全部丢弃
2. open_threads -> 保留 priority > 0.8 的线索，上限 2
3. soft_references -> 保留 Top-4（已按 relevance 排序）
4. foreshadowing -> 只保留 due/overdue
5. character_states -> 只保留 protagonist + importance >= 0.9
6. **终极兜底**（以上 5 步完成后仍超预算）:
   - arc_context.arc_summary 截断到 <=100 字
   - volume_context.volume_summary 截断到 <=80 字
   - recent_plot.summaries 只保留最近 1 章

每一步后重估算 token，达标即停止。

### 2. 集成到 prune() 控制流

- [ ] 逐层裁剪（现有逻辑）全部完成后，检查 current_tokens > budget x HARD_ENFORCE_THRESHOLD
- [ ] 仅当超过阈值时调用 _enforce_budget_hard()（避免不必要的性能开销）
- [ ] 若硬断言后仍超预算 -> logger.warning（但已尽力，返回最终状态）
- [ ] 若硬断言后达标 -> 正常返回

### 3. 跟踪字段

- [ ] ContextPackage._budget_enforced: bool = False
  - 文件: src/songyan/models/context.py
- [ ] Phase1State._budget_was_enforced: bool
  - 文件: src/songyan/workflows/phase1_graph.py
  - 仅存标志位传给下一轮

### 4. structlog 裁剪日志

每次丢弃操作记录：
```
context_manager.hard_enforce
  from_partition="dialogue_style_cards", dropped_count=3,
  tokens_saved=500, current_total=12500, budget=9600
```

### 5. 测试

- [ ] 硬断言循环正确触发：模拟 current_tokens >> budget x 1.3
- [ ] 各步骤丢弃顺序验证（dialogue_style_cards -> open_threads -> soft_refs -> foreshadowing -> character_states）
- [ ] 终极兜底在 Ch70+ 极端情况下生效
- [ ] 硬断言从不裁到 hard_constraints / genre_rules / mode_rules
- [ ] _budget_enforced = True 正确记录
- [ ] 断言后最终 tokens <= budget x 1.3（或记录 warning）
- [ ] Ch50 集成场景：final_tokens <= 14000
- [ ] pytest 通过

## Out of Scope

- 不修改 DB
- 不修改 Writer prompt
- 不修改 setting_snapshots 加载逻辑（077a 负责）
- 不修改 genre_rules / mode_rules / hard_constraints 结构

## 验收标准

- [ ] Ch50 场景：final_tokens <= 14000（当前 19175）
- [ ] 硬断言触发后 _budget_enforced = True
- [ ] 所有裁剪操作通过 structlog 可追溯
- [ ] 从不裁到 hard_constraints / genre_rules / mode_rules
- [ ] 终极兜底在极端情况下生效
- [ ] 不违反 AGENTS.md 规则
- [ ] 生成 DONE 交接报告 + 更新 STATUS.md
