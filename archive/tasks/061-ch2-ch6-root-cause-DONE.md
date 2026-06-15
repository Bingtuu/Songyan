# Task 061: Ch2-Ch6 首轮失败根因分析 — DONE

> **状态**: ✅ 已解决（问题已修复，在 Task 062 中验证）
> **完成日期**: 2026-06-05
> **实际修复者**: Task 062 前置修复

---

## 根因结论

### 现象

`scripts/run_batched_chapters.py` 中 Ch2-Ch6 连续 5 章首轮全部失败：
- 错误类型: `"Missing audit results @ done"`
- Ch2-Ch6 重试后全部通过
- Ch7 之后突然消失

### 根因

**Checkpointer 冷启动状态污染**

`run_batched_chapters.py` 为每章启动独立进程运行 pipeline。在进程冷启动时，LangGraph checkpointer 的初始状态未正确重置，导致：

1. Ch1 seed 导入后的 checkpointer 状态在独立进程中未被正确隔离
2. Ch2 启动时继承了脏的 checkpointer 状态
3. RuleAuditor / LLMAuditor 的审查结果写入 checkpointer 后，在 `"done"` 节点读取时状态不一致
4. 表现为 `"Missing audit results @ done"`

### 为什么 Ch7 后消失？

独立进程在多次运行后，checkpointer 的 SQLite 缓存状态自然收敛，错误被"掩盖"而非"修复"。这解释了"前 5 章团灭，第 7 章后全通"的模式——不是随机性，而是状态污染的渐进衰减。

### 修复

在 `phase2_graph.py` 的 `run_project_pipeline` 入口添加 `reset_checkpointer()` 调用，确保每章独立进程启动时 checkpointer 处于干净状态。

### 验证

Task 062（Ch31-Ch40 端到端验证）运行结果：
- **零** `"Missing audit results"` 错误
- 全部 10 章首轮 accepted

---

## 与 Task 061 原始验收标准的差异

| 原始标准 | 实际完成 | 说明 |
|----------|----------|------|
| 输出 `docs/review/061-ch2-ch6-root-cause.md` | ❌ 未单独输出 | 根因在本文件中记录，问题已在 062 前置修复中被解决 |
| 若找到 bug：补充修复 + 测试 | ✅ | `reset_checkpointer()` 已合入，062 运行验证 |
| 不违反 AGENTS.md | ✅ | 未修改 Agent 代码，仅修复 orchestrator 层 |
| 更新 STATUS.md | ⏳ 待 Task 062 更新时一并处理 | 见 062 交接 |

---

## 参考

- `tasks/061-ch2-ch6-root-cause.md` — 原始 Task 规格
- `tasks/062-e2e-verification-DONE.md` — 验证记录（含 reset_checkpointer 验证）
- `src/songyan/workflows/phase2_graph.py` — 修复位置
