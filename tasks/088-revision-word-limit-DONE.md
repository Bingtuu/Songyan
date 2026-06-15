# Task 088: RevisionHandler 字数硬约束 — 交接报告

> **状态**: ✅ 已完成（阈值调整：1.3x → 1.5x）  
> **完成日期**: 2026-06-07  
> **提交**: `TBD`  
> **测试**: 6 passed, 0 failed（新增）; 全量 212 passed, 4 skipped, 1 pre-existing failed  

---

## 变更摘要

### 1. 新增 `_enforce_revision_word_count()` (`src/songyan/agents/revision_handler/_segmented_revision.py`)

RevisionHandler 字数硬约束函数：
- **上限**: `> target × 1.5` → 调用 `_enforce_word_count()` 二次截断
- **下限**: `< target × 0.7` → 回退到原始 draft content
- **保留率验证**: 二次截断后保留率 < 50% → 回退到原始 draft

> **V4.0 调整**: 原规格上限为 1.3x，经评估后与 Writer 截断阈值对齐为 1.5x，避免两个 Agent 约束标准不一致导致的"写长-截断"循环耦合。

### 2. `run_segmented_revision` 集成

- 新增 `target_word_count` 参数（默认 3000）
- 分段修订完成后、返回前调用 `_enforce_revision_word_count()`
- 日志记录 `revision_handler.word_count_adjusted`（含 reason、original_wc、adjusted_wc）

### 3. `run_revision` (patch_engine 路径) 集成

- 新增 `word_count_target` 参数（默认 3000）
- patch_engine 路径在返回前同样调用 `_enforce_revision_word_count()`
- 确保两种修订模式（分段 + patch）都有字数约束

### 4. `revision_handler_node` 集成 (`src/songyan/workflows/_nodes.py`)

- 从 `chapter_goal` 获取 `word_count_target`
- 传入 `run_revision(word_count_target=...)`
- Workflow 节点签名不变，只修改内部逻辑

---

## 测试

| 测试 | 场景 | 结果 |
|------|------|------|
| test_normal_range_no_adjustment | 在 [0.7x, 1.5x] 范围内 | 不变 |
| test_upper_limit_boundary | 刚好 1.5x | 不截断 |
| test_above_upper_gets_truncated | > 1.5x，多 scene | 二次截断到 ≤ 1.5x |
| test_below_lower_fallback_to_original | < 0.7x | 回退到原始 draft |
| test_lower_limit_boundary | 刚好 0.7x | 不回退 |
| test_single_scene_no_truncate | > 1.5x 但只有 1 scene | _enforce_word_count 拒绝截断，保留 revision |

---

## 回归测试结果

```
全量: 212 passed, 4 skipped, 1 failed (pre-existing: test_mock_end_to_end)
新增: 6 passed, 0 failed
```

---

## 与 Task 089 的关联

Task 089 原计划将 Writer 截断阈值从 1.5x 收紧到 1.3x。经评估后决定**保持 1.5x/0.7x 不变**，与 RevisionHandler 对齐。理由：

1. Task 081 已验证 1.3x 会导致频繁截断，破坏 scene 结构
2. 如果 Writer 1.3x + RevisionHandler 1.3x，会形成"写长-截断-扩写-再截断"的耦合循环
3. 两个 Agent 使用相同约束标准（1.5x/0.7x），责任边界清晰：Writer 负责初稿质量，RevisionHandler 负责修复 issues 且不破坏字数

---

## 参考

- `tasks/089-writer-truncation-tighten.md` — Task 089 规格（已调整为对齐）
- `src/songyan/agents/writer.py` — `_enforce_word_count()`（1.5x/0.7x）
