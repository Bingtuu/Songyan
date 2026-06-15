# Task 088: RevisionHandler 字数硬约束

> **Phase**: V4.0 Phase B — Agent 约束硬化
> **优先级**: P0
> **依赖**: Task 087（Phase A 通过决策门 0）
> **预计工作量**: 中（3 天）

---

## Goal

为 RevisionHandler 增加字数硬约束：revision 后字数 > target×1.25 时二次截断，< target×0.75 时回退到原始 draft。保留率验证仍 ≥ 50%。

> **V4.0 调整说明**：RevisionHandler 阈值（1.25x/0.75x）略宽于 Writer（1.20x/0.80x），避免两阶段过度截断。Writer 已做初稿截断，Revision 作为二次保护。下界 0.75x 与 Writer 0.80x 形成梯度。

## Context

V3.x 中 RevisionHandler 无字数约束，Ch56 draft 3731 → accepted 5797（+55%）。分段修订引擎的 LLM prompt 无字数约束，scene 级重写可能大幅增删文本。本 Task 在 revision 输出后增加截断/回退逻辑，不改 Prompt、不改分段引擎核心逻辑。

## In Scope（必须完成）

- [ ] **`_enforce_revision_word_count()` 函数**：
  - 输入：revision 后 content、scenes、target_word_count
  - 上限：`> target * 1.25` → 调用 `_enforce_word_count()` 二次截断
  - 下限：`< target * 0.75` → 回退到原始 draft content
  - 保留率验证：二次截断后保留率仍 ≥ 50%（复用 Task 079 的 `_compute_preservation_ratio()`）
  - 日志：记录 `_revision_truncated` / `_revision_underflow` / `_revision_accepted`
- [ ] **run_segmented_revision 集成**：在返回前调用字数约束函数
- [ ] **run_patch_engine 集成**：在返回前调用字数约束函数
- [ ] **单元测试**：
  - 超上限场景（draft 3000 → revision 5000，target=3000）：二次截断到 4500
  - 低于下限场景（draft 3000 → revision 1500，target=3000）：回退到 3000
  - 正常场景（draft 3000 → revision 3200，target=3000）：不变

## Out of Scope（明确不做）

- 修改 RevisionHandler Prompt（V3.x 1.0.0 保持不变）
- 修改分段引擎核心逻辑（scene 拆分、issue 映射、patch 生成）
- Writer 截断阈值调整（Task 089）
- 任何 workflow 节点签名修改

## 接口契约

```python
# src/songyan/agents/revision_handler/_segmented_revision.py（修改）

def _enforce_revision_word_count(
    revision_content: str,
    revision_scenes: list[dict],
    original_content: str,
    target_word_count: int,
) -> tuple[str, list[dict], int, bool, str]:
    """
    Revision 后字数硬约束。
    
    Returns:
        content, scenes, word_count, was_adjusted, reason
    """
    upper = int(target_word_count * 1.25)
    lower = int(target_word_count * 0.75)
    current = _count_chinese_words(revision_content)
    
    if current > upper:
        # 二次截断
        content, scenes, wc, _, reason = _enforce_word_count(
            revision_content, revision_scenes, target_word_count, current
        )
        return content, scenes, wc, True, f"revision_truncated:{reason}"
    
    if current < lower:
        # 回退到原始 draft
        original_scenes = _parse_scenes(original_content)
        original_wc = _count_chinese_words(original_content)
        return original_content, original_scenes, original_wc, True, "revision_underflow_fallback"
    
    return revision_content, revision_scenes, current, False, "revision_accepted"

# 在 run_segmented_revision() 和 run_patch_engine() 返回前调用：
content, scenes, wc, adjusted, reason = _enforce_revision_word_count(
    content, scenes, original_content, target_word_count
)
```

## 测试要求

### Layer 2: 模块测试
- [ ] 超上限：revision 字数 = target×1.25+1 → 截断到 ≤ target×1.20
- [ ] 低于下限：revision 字数 = target×0.5 → 回退到原始 draft
- [ ] 正常：revision 字数 = target×1.1 → 不变
- [ ] 边界：刚好 target×1.25 → 不截断；刚好 target×0.75 → 不回退

### Layer 3: 集成测试
- [ ] Ch1-Ch10 端到端：无 revision 后字数 > target×1.25 或 < target×0.75

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/agents/test_revision_handler.py -v` 全部通过
- [ ] Ch1-Ch10 端到端无字数超限/低于下限
- [ ] 保留率验证：二次截断后保留率 ≥ 50%
- [ ] 生成了 `tasks/088-revision-word-limit-DONE.md`

## 参考

- `docs/v4.0-tech-plan.md` — 第 5.1 节
- `src/songyan/agents/revision_handler/_segmented_revision.py` — 现有分段引擎
- `tasks/079-revision-handler-restructuring-DONE.md` — 分段引擎设计
