# Task 079: RevisionHandler 重构 — 分段修订 + 提升 patch 成功率

> **Phase**: V3.1 100章架构改造 — Phase B 质量提升
> **优先级**: P1
> **依赖**: 076, 077, 078（推荐先止血再提升质量）
> **预计工作量**: 大（3-4 天）

---

## Goal

将 RevisionHandler 从"文本 patch 匹配"改为"分段修订"模式，彻底解决 content_truncated 和 patch_not_found 问题。

## Context

V3.1 验证报告问题 4.1.3（RevisionHandler 系统性失效）：

| 失败模式 | 现象 | 出现频率 |
|---------|------|---------|
| content_truncated | LLM 返回的修订被截断到 23-27% | Ch41×2, Ch46×2, Ch49×1 |
| patch_not_found / invalid_patch | 文本匹配失败 | 频繁出现 |
| partial_patches | 大量 issue 无法应用 | 几乎每章 |
| revision_rebound | 修订后问题反而增加 | Ch42: 7→17, Ch46: 9→16 |

当前 `_patch_engine.py` 的四级匹配策略（精确→归一化→difflib 90%/85%/80%→段落级）在上下文 15000+ tokens 时频繁失败。根本原因是：**文本匹配本身在 LLM 输出有微小变异时就脆弱**。

## In Scope

### 1. 分段修订模式

- [ ] 新增 `_segmented_revision.py` 模块，实现基于 scene 边界的分段修订：
  - 原文按 `### Scene N` 分割为 scene 段
  - Merger 将 issue 映射到各 scene 段
  - 每个有 issue 的 scene 段分别调用 LLM 修订
  - LLM 上下文只包含该 scene 的正文 + 针对该 scene 的 issue 列表
- [ ] 保留 `_patch_engine.py` 文本 patch 作为最后手段（当 scene 分割失败时回退）

### 2. Issue-Scene 映射器

- [ ] 实现 Merger，将 ReviewIssue 映射到 scene：
  - 按 `evidence_quote` 的文本位置匹配 scene 段
  - 无 evidence_quote 的 issue 分配到最接近的 text span 所属 scene
  - 完全无法定位的 issue 汇总到"全局 issue"列表，在最后提交

### 3. 修订后验证

- [ ] 每个 scene 段修订后立即检查内容保留率：
  - 保留率 < 50% → 回退到该 scene 的原版本
  - 保留率 ≥ 50% → 接受修订版本
- [ ] 所有 scene 段修订完成后，按 scene 顺序拼接成完整正文
- [ ] 全局 issue 仍然走 _patch_engine.py 文本匹配

### 4. RevisionOutput 增强

- [ ] 新增字段：`segmented: bool`（是否使用了分段修订）
- [ ] 新增字段：`scenes_modified: int`（被修改的 scene 数）
- [ ] 新增字段：`scenes_fallback_count: int`（回退到原始版本的 scene 数）

## Out of Scope

- 不修改 LLM 调用参数（max_tokens 等）
- 不修改 Writer Prompt（分段修订是 RevisionHandler 内部行为）
- 不做 AI 辅助证据定位（V3.2 考虑）
- 不改动 review_merger.py（审阅合并逻辑不受影响）

## 接口契约

```python
# 新增分段修订入口
async def run_segmented_revision(
    content: str,
    issues: list[ReviewIssue],
    prompt_card: dict,
    llm_config: dict,
) -> RevisionOutput:
    """按 scene 分段修订.
    
    1. 分割 content 为 scene 段
    2. 将 issues 映射到各 scene
    3. 对每个有 issue 的 scene 段调用 LLM 修订
    4. 验证每段修订的质量，回退失败段
    5. 拼接结果
    
    Returns:
        RevisionOutput (含 content, patches, fallback 信息)
    """


class RevisionOutput(BaseModel):
    """增强版修订输出."""
    ...
    segmented: bool = False  # 新增
    scenes_modified: int = 0  # 新增
    scenes_fallback_count: int = 0  # 新增
```

## 测试要求

- [ ] scene 分割：正确识别 ### Scene N 边界
- [ ] issue-scene 映射：evidence_quote 精确匹配
- [ ] 无 evidence_quote 的 issue → 分配到最近 scene
- [ ] 单 scene 修订后保留率 < 50% → 回退
- [ ] 多 scene 修订后拼接结果正确
- [ ] 分段修订后所有 scenes 的字符数之和 = 拼接结果字符数
- [ ] 回退到 _patch_engine.py 路径正常工作
- [ ] pytest tests/ -x -q 通过

## 验收标准

- [ ] patch_not_found 率降低 50%+（当前 ~30% vs 目标 <15%）
- [ ] content_truncated 不再出现（因为每个 scene 段文本短，LLM 不易截断）
- [ ] revision_rebound 率降低 50%+（当前 ~30% 触发率 vs 目标 <15%）
- [ ] 不违反 AGENTS.md 规则
- [ ] 生成 DONE 交接报告
- [ ] 更新 STATUS.md
