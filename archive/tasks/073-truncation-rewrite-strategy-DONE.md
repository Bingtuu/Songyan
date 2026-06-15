# Task 073: 截断重写策略 — 交接报告

> **状态**: ✅ 已完成
> **完成日期**: 2026-06-06
> **耗时**: ~1.5 小时
> **提交**: `TODO`

---

## 做了什么

### 1. 状态机扩展

- `Phase1State` 新增字段：
  - `_was_rewritten: bool` — 标记本章是否已触发过重写
  - `_rewrite_reason: str | None` — 记录重写原因

### 2. revision_router 改造

```python
def revision_router(state) -> str:
    # 073: 已重写的章节直接 pass，避免无限循环
    if was_rewritten: return "pass"
    
    # 073: 2 轮不收敛 → 触发整章重写（最多 1 次）
    if needs and rround >= MAX_REVISION_ROUNDS:
        return "rewrite"
    
    # 原有逻辑
    if needs and rround < MAX_REVISION_ROUNDS:
        return "revise"
    return "pass"
```

### 3. rewrite_node 实现

- 加载 `ContextPackage` 并注入前 2 轮 issues 作为 `human_instructions`
- 调用 `write_chapter()` 生成全新正文
- 返回状态：`_was_rewritten=True`, `revision_round=0`, `_needs_revision=False`
- 重写后走 `rule_auditor`（生成审查报告供 human_confirm 参考），但 `revision_router` 强制 `pass`

### 4. 禁止清单构建

- 从 `_new_issues_introduced` 提取 issue 描述和证据
- 从 `review_report_id` 加载 `MergedReviewReport` 补充 issues
- 按描述去重，最多保留 10 条
- 格式：`{issue_description} — 证据："{evidence_quote[:50]}"`

### 5. 测试

| 测试文件 | 新增用例 | 结果 |
|---------|---------|------|
| `tests/test_rewrite_node.py` | 11 | ✅ 全部通过 |
| `tests/test_phase1_graph.py` | 6 revision router + 原有 | ✅ 全部通过 |

---

## 重写流程

```
Round 0: writer → audit → literary_auditor → revision_router → revise
Round 1: revision_handler → audit → literary_auditor → revision_router → revise
Round 2: revision_handler → audit → literary_auditor → revision_router → rewrite
Rewrite:  writer(+issues) → audit → literary_auditor → revision_router → pass
          → human_confirm → settlement_extractor → END
```

---

## 已知限制

- **禁止清单依赖 state 中的 `_new_issues_introduced`**：如果该字段为空（如 old_issues 未序列化），禁止清单可能不完整
- **不修改 Writer Prompt**：issues 通过 `human_instructions` 注入，Writer 需支持解析该字段
- **最多 1 次重写**：`_was_rewritten` 标记确保不无限循环，但 human 在 `human_confirm` 中仍可 reject 并触发重新写作

---

## 文件变更清单

```
src/songyan/workflows/phase1_graph.py       # Phase1State + revision_router + graph 边
src/songyan/workflows/_nodes.py              # +rewrite_node + _build_rewrite_avoid_list
tests/test_phase1_graph.py                   # 更新 revision_router 测试
tests/test_rewrite_node.py                   # 新建（11 个测试）
docs/STATUS.md                               # 更新 073 状态
```

---

## 下一步

- 端到端验证：运行 Ch31-Ch40，观察 2 轮不收敛章节是否正确触发重写
- 074: 对话质量专项（如需要）
