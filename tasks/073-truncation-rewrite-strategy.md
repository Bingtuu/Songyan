# Task 073: 截断重写策略

> **Phase**: V3.1 — 质量跃迁
> **优先级**: P3
> **依赖**: 068, 069
> **预计工作量**: 中（~1 天）

---

## Goal

实现"2 轮 revision 不收敛时触发整章重写"的截断重写策略，作为 revision 回弹的最后防线。

## Context

058d 数据分析：
- 24/29 章打满 2 轮 revision
- 其中部分章节在 Round 2 引入了新的 critical issue（new_issues_introduced 检测已上线）
- 当前策略：2 轮后无论是否收敛都 accept，可能导致质量问题沉淀

截断重写策略：
- 当 Round 2 结束后仍有 unresolved critical/major issues，或检测到 `new_issues_introduced`
- 不再尝试 Round 3 revision
- 触发整章重写：以 CreativeBrief + ChapterGoal 为输入，要求 Writer 重新生成完整正文
- 重写后直接进入 accept（不再走 revision 流程，避免无限循环）

## In Scope（必须完成）

- [ ] 在 `phase1_graph.py` 的 revision 路由逻辑中增加"2 轮不收敛 → 重写"分支
- [ ] 实现 `rewrite_chapter()` 函数：调用 Writer 重新生成，绕过 revision
- [ ] 重写时注入前 2 轮的所有 issues 作为"禁止清单"，避免重复犯错
- [ ] 增加重写次数上限（最多 1 次重写，防止无限循环）
- [ ] 记录重写事件到 JSONL 日志（`was_rewritten=true`, `rewrite_reason`）
- [ ] 补充单元测试：2 轮不收敛时触发重写，重写后 accept
- [ ] 补充回归测试：`pytest tests/test_phase1_graph.py -v` 全部通过

## Out of Scope（明确不做）

- 不做 Round 3+ revision（保持最多 2 轮）
- 不重写已 accepted 的历史章节
- 不做人工确认 gate（auto-confirm 模式下全自动）
- 不修改 Writer Prompt 模板（只追加禁止清单）

## 接口契约

```python
# 在 phase1_graph 的 revision 路由中

async def _handle_revision_convergence(
    state: PipelineState,
    round_count: int,
    issues: list[ReviewIssue],
    new_issues: list[ReviewIssue],
) -> PipelineState:
    """处理 revision 收敛判断.
    
    策略：
    - Round 0: 初稿
    - Round 1: 第一次 revision
    - Round 2: 第二次 revision
    - Round 2 后仍有 critical/major 或 new_issues → 触发整章重写
    """
    if round_count >= 2 and (issues or new_issues):
        return await _trigger_full_rewrite(state)
    return state

async def _trigger_full_rewrite(state: PipelineState) -> PipelineState:
    """触发整章重写."""
    ...
```

## 重写 Prompt 追加内容

```markdown
## 重写注意事项

本章之前经历了 2 轮修订但仍未通过审查。以下是之前被发现的问题，请在重写时避免：

1. [issue 描述] — [evidence_quote]
2. [issue 描述] — [evidence_quote]

请重新生成完整正文，确保以上问题不再出现。
```

## 测试要求

- [ ] 2 轮 revision 后仍有 critical issue → 触发重写
- [ ] 重写后的正文与初稿不同（确认 Writer 被调用）
- [ ] 重写后直接进入 accept（不再走 revision）
- [ ] 最多只触发 1 次重写（防止无限循环）
- [ ] JSONL 日志包含 `was_rewritten=true`

## 验收标准

- [ ] `pytest tests/test_phase1_graph.py -v` 全部通过 + 新增测试通过
- [ ] 重写流程在模拟运行中不崩溃
- [ ] `docs/STATUS.md` 更新
- [ ] 生成 `tasks/073-truncation-rewrite-strategy-DONE.md`

## 参考文档

- `src/songyan/workflows/phase1_graph.py` — revision 路由逻辑
- `src/songyan/agents/writer.py` — Writer Agent
- `src/songyan/agents/revision_handler/__init__.py` — RevisionHandler
- `tasks/058d-revision-convergence-fix-DONE.md` — 058d 的 new_issues 检测
