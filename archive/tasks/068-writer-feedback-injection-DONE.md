# Task 068: Writer Feedback 注入 — 交接报告

> **状态**: ✅ 已完成
> **完成日期**: 2026-06-06
> **关联 commit**: (待填入)

---

## 变更摘要

在 `RevisionHandler` 构建 Prompt 时，注入上一轮 `LLMAuditor` 为该章标记的 show-dont-tell `evidence_quote` 列表，让 RevisionHandler 知道"具体哪几句需要改"，提高 patch 精度。

---

## 修改文件

| 文件 | 变更内容 |
|------|---------|
| `src/songyan/agents/revision_handler/__init__.py` | 新增 `_render_previous_show_dont_tell_feedback()`；修改 `_render_prompt()` 和 `run_revision()` 支持 `previous_issues` 参数 |
| `src/songyan/workflows/_nodes.py` | `revision_handler_node`: 当 `revision_round > 0` 时，通过 `parent_version_id` 加载父版本的 merged report，提取 LLMAuditor issues 传给 `run_revision()` |
| `tests/test_revision_handler.py` | 新增 10 个测试覆盖 feedback 注入的各场景 |
| `docs/STATUS.md` | 更新 Task 068 状态为已完成 |

---

## 技术实现要点

### 1. Feedback 渲染逻辑

- 过滤条件：`category == SHOW_DONT_TELL` 且 `evidence_quote` 非空
- 格式化输出：带序号的 evidence_quote + issue_description 列表
- 截断保护：总长度超过 1000 字符时，在最后完整行截断并追加 `...（证据列表已截断）`

### 2. 调用链

```
revision_handler_node (workflows/_nodes.py)
  └── 当 revision_round > 0:
      └── 加载 parent_version 的 merged_report.llm_audit.issues
          └── 传入 run_revision(previous_issues=...)
              └── _render_prompt(previous_issues=...)
                  └── _render_previous_show_dont_tell_feedback()
```

### 3. 边界处理

- `previous_issues=None/[]` → 不追加 feedback 段落（与原有行为一致）
- `evidence_quote=""` → 跳过该 issue
- feedback 过长 → 截断到最后一个完整条目

---

## 测试覆盖

| 测试类 | 测试数 | 覆盖场景 |
|--------|--------|---------|
| `TestRenderPreviousShowDontTellFeedback` | 6 | 空输入、非 show-dont-tell 过滤、evidence 渲染、空 quote 跳过、过长截断 |
| `TestRenderPromptFeedbackInjection` | 2 | prompt 包含/不包含 feedback 段落 |
| `TestRunRevision` | 2 | 集成测试：LLM prompt 捕获验证 previous_issues 注入 / 无注入 |

**总计新增测试**: 10 个
**全部测试通过**: `pytest tests/test_revision_handler.py -v` → 69 passed

---

## 验收标准检查

- [x] `pytest tests/test_revision_handler.py -v` 全部通过 + 新增测试通过
- [x] 至少 3 个场景的 Feedback 注入测试覆盖（实际 8 个单元 + 2 个集成）
- [x] `docs/STATUS.md` 更新
- [x] 生成 `tasks/068-writer-feedback-injection-DONE.md`

---

## 已知限制

- 只注入 show-dont-tell 维度的 feedback（符合任务边界）
- 只注入当前章的上一轮 issues（不做跨章 feedback）
- 依赖 `parent_version_id` 追溯父版本，若 parent_version 无 LLMAuditor 报告则 previous_issues 为 None
