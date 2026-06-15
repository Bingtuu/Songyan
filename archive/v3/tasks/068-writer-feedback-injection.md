# Task 068: Writer Feedback 注入

> **Phase**: V3.1 — 质量跃迁
> **优先级**: P1
> **依赖**: 无（070 的 instrumentation 可并行）
> **预计工作量**: 中（~6 小时）

---

## Goal

在 `RevisionHandler` 构建 Prompt 时，注入上一轮 `LLMAuditor` 为该章标记的 show-dont-tell `evidence_quote` 列表，让 RevisionHandler 知道"具体哪几句需要改"，提高 patch 精度。

## Context

058b 数据显示 `show_dont_tell` 占全部 issues 的 42.5%（356/837），每章平均 3.7 个。这是当前最主要的 revision 触发原因。

当前 RevisionHandler 的 Prompt 只知道"本章有 show-dont-tell 问题"，但不知道**具体哪些句子**被标记。这导致：
1. LLM 需要重新扫描全文找问题（浪费 token）
2. patch 可能改错位置或遗漏关键句
3. 同一问题在 Round 1 和 Round 2 反复出现

**可在 V3.0 内做的最小代价改进**：在 `revision_handler` 构建 Prompt 时，把上一轮 `LLMAuditor` 为该章标记的 show-dont-tell 证据句追加到 revision prompt 中。这不需要改 Prompt 模板，只需在 prompt 组装时追加一段 evidence 列表。

## In Scope（必须完成）

- [ ] 确认 `ReviewIssue.evidence_quote` 在 `show_dont_tell` 类别中的填充率
- [ ] 在 `RevisionHandler` 的 Prompt 组装逻辑中，提取上一轮 `issues` 中 `category=show_dont_tell` 的 `evidence_quote`
- [ ] 将 evidence_quote 列表格式化为"需要修改的具体句子"段落，追加到 revision prompt
- [ ] 处理 evidence_quote 为空或过长的情况（截断或跳过）
- [ ] 补充单元测试：有 evidence 时 prompt 包含对应句子，无 evidence 时 prompt 不变化
- [ ] 补充回归测试：`pytest tests/test_revision_handler.py -v` 全部通过

## Out of Scope（明确不做）

- 不修改 Writer Prompt 模板（Writer 层的优化属于 Prompt Engineering，不在本 Task）
- 不做全维度 Feedback 注入（只注入 show-dont-tell，其他维度留待后续）
- 不做跨章 Feedback（只注入当前章的上一轮 issues）
- 不修改 `ReviewIssue` 模型结构

## 接口契约

```python
# 在 revision_handler/__init__.py 的 prompt 组装函数中

def _build_revision_prompt(
    content: str,
    issues: list[ReviewIssue],
    previous_issues: list[ReviewIssue] | None = None,
) -> str:
    """构建 RevisionHandler Prompt.
    
    Args:
        content: 当前版本正文
        issues: 本轮需要修复的 issues
        previous_issues: 上一轮审查结果（用于 Feedback 注入）
    """
    ...
```

## Feedback 注入格式

```markdown
## 上一轮审查的具体证据

以下句子在上一轮审查中被标记为"展示而非讲述"（show-dont-tell）问题，请优先修改这些句子：

1. "林凡不禁意识到一股暖流涌上心头。" — 过于抽象，缺乏感官细节
2. "他感到前所未有的愤怒。" — 直接陈述情绪，未通过动作/环境展示

修改时请保留原文的叙事位置和角色视角，只替换被标记的句子。
```

## 测试要求

- [ ] 有 `previous_issues` 且含 show-dont-tell 时，prompt 包含 evidence_quote
- [ ] 无 `previous_issues` 时，prompt 与当前行为一致
- [ ] evidence_quote 为空字符串时，跳过该项
- [ ] 总 evidence 长度超过 1000 字时截断
- [ ] 集成测试：RevisionHandler 输出包含对 evidence 的修改

## 验收标准

- [ ] `pytest tests/test_revision_handler.py -v` 全部通过 + 新增测试通过
- [ ] 至少 3 个场景的 Feedback 注入测试覆盖
- [ ] `docs/STATUS.md` 更新
- [ ] 生成 `tasks/068-writer-feedback-injection-DONE.md`

## 参考文档

- `src/songyan/agents/revision_handler/__init__.py` — RevisionHandler 主入口
- `src/songyan/models/review.py` — `ReviewIssue` 模型
- `prd/v3.0-058b-review-and-recommendations.md` — 5.3 节 show-dont-tell 分析
