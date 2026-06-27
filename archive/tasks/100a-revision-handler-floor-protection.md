# Task 100a: RevisionHandler 下限保护 + 字数守卫

> **Phase**: V4.0 Phase B — 修复收尾
> **优先级**: P0
> **依赖**: Task 098, Task 099
> **预计工作量**: 小

---

## Goal

消除 RevisionHandler segmented revision 在修复 issues 时过度删减正文的系统性缺陷，建立 0.85x 硬下限保护，防止达标初稿在 revision 环节被压到不足区间。

## Context

Task 099 验证发现 **Ch45 是 pipeline 机制导致的不足章节**：初稿 3695 字（1.055x 达标）→ 第一轮修订 3699 字 → 第二轮修订骤降至 2559 字（暴跌 31%，0.731x）。根因是 segmented revision 的逐场景修订缺乏全局字数下限保护，各 scene 的 LLM 独立删减产生累积效应。

当前代码仅在 `_enforce_revision_word_count` 有 0.80x 触发回退，但：
1. 该检查在 segmented revision 拼接完成后才执行，此时字数已损失
2. 回退到原始 draft 意味着 revision 白做，而非阻止删减
3. `MIN_CONTENT_RATIO = 0.50` 过低，允许保留率 50% 的灾难性删减

## In Scope（必须完成）

- [ ] 提升 `MIN_CONTENT_RATIO` 从 0.50 至 0.85（`revision_handler/__init__.py` 和 `_segmented_revision.py`）
- [ ] 在 `run_segmented_revision` 中增加**全局字数下限守卫**：拼接完整正文后，若字数 < 原始字数 × 0.85，直接回退到原始内容
- [ ] 在 `run_revision` 的 patch_engine 路径中增加同等下限保护（LLM 返回的 content 与 patch 应用结果均需检查）
- [ ] 在 `_enforce_revision_word_count` 中增加 `revision_min_preserve_ratio=0.85` 硬约束，低于此值不触发截断/回退，而是标记 `needs_human_review`
- [ ] 更新 Task 099 中 Ch45 类极端章节的 regression 测试，确保 0.85x 守卫生效
- [ ] 运行 5 章端到端验证（建议选择 Ch42-Ch46 区间，含截断/修订/rewrite 场景）

## Out of Scope（明确不做）

- 不修改 Writer 初稿生成逻辑（已在 Task 093/098 中优化）
- 不调整 GoalPlanner 字数目标映射（属于 Task 100c 范围）
- 不新增 Agent 或 Workflow 节点

## 接口契约

```python
# _segmented_revision.py
async def run_segmented_revision(
    content: str,
    issues: list[ReviewIssue],
    ...,
    target_word_count: int = 3000,
    min_preserve_ratio: float = 0.85,  # 新增参数
) -> tuple[RevisionOutput, str]:
    """按 scene 分段修订，增加全局字数下限守卫."""
    ...

# _enforce_revision_word_count 新增行为
if current < original_wc * 0.85:
    # 不再自动回退到原始 draft，而是标记 needs_human_review
    # 让上层决定是否继续 revision 或上报人工
```

## 数据模型

无新增模型，修改现有常量：

```python
# revision_handler/__init__.py
MIN_CONTENT_RATIO = 0.85  # 从 0.50 提升

# _segmented_revision.py
MIN_PRESERVATION_RATIO = 0.85  # 从 0.50 提升
```

## 测试要求

### Layer 1: 单元测试
- [ ] `run_segmented_revision` 输入 4000 字，模拟 LLM 返回 2500 字（0.625x）→ 预期回退到原始内容
- [ ] `run_segmented_revision` 输入 4000 字，模拟 LLM 返回 3500 字（0.875x）→ 预期接受修订
- [ ] `_enforce_revision_word_count` 在 0.85x 边界的行为验证

### Layer 2: 集成测试
- [ ] RevisionHandler 端到端：patchable issues + 模拟 LLM 过度删减 → 验证守卫触发

### Layer 3: 5 章验证
- [ ] 选择 5 章（含高 revision 风险章节）跑通端到端，检查无 Ch45 类暴跌

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/test_revision_handler.py -v` 全部通过（新增/更新测试）
- [ ] 5 章端到端验证：revision 后字数保留率 ≥ 85%，无 <0.80x 的 revision 结果
- [ ] ruff 检查无新增错误
- [ ] 生成 `tasks/100a-revision-handler-floor-protection-DONE.md` 交接文件

## 参考文档

- `tasks/099-ch71-ch100-extension-DONE.md` — Ch45 根因分析
- `src/songyan/agents/revision_handler/_segmented_revision.py` — 分段修订实现
- `src/songyan/agents/revision_handler/__init__.py` — RevisionHandler 主入口
