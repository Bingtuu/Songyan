# Task 076: Writer 强制字数截断

> **Phase**: V3.1 100章架构改造 — Phase A 止血
> **优先级**: P0
> **依赖**: 无
> **预计工作量**: 小（4-6 小时）

---

## Goal

在 Writer 输出正文后增加强制截断逻辑，将字数控制在目标 ±20% 以内。

## Context

V3.1 验证显示 Ch45 起字数稳定在目标的 160-220%：

| 章节 | 目标字数 | 实际字数 | 偏差 |
|------|---------|---------|:----:|
| Ch46 | 3200 | 7828 | **+145%** |
| Ch47 | 3200 | 6479 | +102% |
| Ch48 | 3200 | 5789 | +81% |
| Ch49 | 3200 | 6700 | +109% |
| Ch50 | 3200 | 6851 | **+114%** |

`word_count_target` 只是 Prompt 建议性参数，LLM 在复杂上下文中必然多写。超字数连锁引发上下文膨胀→预算恶化→Revision 匹配失败→截断重写。

本 Task 改动量最小、降压效果最大。

## In Scope

- [ ] `writer.py` `write_chapter()` 末尾新增 `_enforce_word_count()`
- [ ] 字数 > target × 1.30 → 截断到最近 scene 边界
- [ ] 截断后字数 < target × 0.5 → 保留最后一个完整 scene
- [ ] **新增** 单 scene 超长保护：若 scenes_count < 2 且字数 > target × 1.30，标记 `_disallowed_by_scene_structure: true`，不截断（避免破坏唯一 scene），放行到下一轮
- [ ] generation_metadata 记录 `_word_count_truncated`, `_word_count_original`, `_scene_count_after_truncation`, `_disallowed_by_scene_structure`
- [ ] 更新 ChapterVersion.word_count 和 scenes 为截断后值

## Out of Scope

- 不修改 Prompt
- 不修改 LLM max_tokens
- 不做截断后内容质量评估

## 测试要求

- [ ] 字数 ≤ target × 1.30 → 不截断
- [ ] 字数 > target × 1.30, 多 scene → 截断到最后一个 scene
- [ ] 字数 > target × 1.30, 单 scene → 标记 `_disallowed_by_scene_structure`，不截断
- [ ] 截断后字数 < target × 0.5 → 保留末 scene
- [ ] pytest tests/ -x -q 通过

## 验收标准

- [ ] Ch41-Ch50 模拟验证字数 ≤ target × 1.20
- [ ] 不违反 AGENTS.md 规则
- [ ] 生成 DONE 交接报告
- [ ] 更新 STATUS.md
