# Task 067: genre_rules 按需加载

> **Phase**: V3.1 — 质量跃迁
> **优先级**: P1
> **依赖**: 无
> **预计工作量**: 小（~3 小时）

---

## Goal

将 `GenreProfile` 的全量注入改为按需加载，按当前章节类型 (`chapter_type`) 过滤 `reviewer_focus` 子集，预计节约 ~500 tokens/章。

## Context

058b 数据显示 `genre_profile` 是一个 927 tokens 的静态对象，每章全量注入 ContextPackage。但实际每章只涉及 `reviewer_focus` 的某个子集：

- 战斗章只需要 `combat_pacing`, `tension_escalation`
- 日常章只需要 `character_development`, `world_building`
- 转折章只需要 `plot_twist`, `revelation`

当前 `ContextManager` 将 `genre_profile` 作为整体对象序列化后注入，没有过滤逻辑。

## In Scope（必须完成）

- [ ] 分析 `GenreProfile` 各字段的 token 占用（`reviewer_focus`, `writer_rules`, `taboos`, `satisfaction_types` 等）
- [ ] 设计按需加载规则：按 `chapter_goal.chapter_type` 映射到 `reviewer_focus` 的子集
- [ ] 在 `ContextManager` 或 `_helpers.py` 中实现 `filter_genre_profile()` 函数
- [ ] 确保过滤后的 `GenreProfile` 仍能正确序列化并注入 Prompt
- [ ] 补充单元测试：不同 `chapter_type` 下过滤结果正确
- [ ] 补充回归测试：`pytest tests/ -x -q` 全部通过

## Out of Scope（明确不做）

- 不修改 `genres/*.json` 配置文件格式
- 不做 `fatigue_words` 按需加载（已在 V2.x 实现）
- 不做 `pacing_templates` / `emotion_arc_library` 按需加载（复杂度超出本 Task）
- 不做多 genre 混合场景

## 接口契约

```python
from songyan.models.genre import GenreProfile
from songyan.models.chapter import ChapterGoal

def filter_genre_profile(
    genre_profile: GenreProfile,
    chapter_goal: ChapterGoal,
) -> GenreProfile:
    """按章节类型过滤 GenreProfile，只保留相关的 reviewer_focus 子集."""
    ...
```

## 数据模型

`GenreProfile.reviewer_focus` 当前为 `list[str]`，建议增加分类标记（可选，不改模型）：

```json
// genres/scifi.json 中 reviewer_focus 的分类约定（不强制改格式）
{
  "reviewer_focus": [
    "combat_pacing",      // 战斗相关
    "tension_escalation", // 战斗/转折相关
    "character_development", // 日常/成长相关
    "world_building",     // 日常/探索相关
    "plot_twist",         // 转折相关
    "revelation"          // 转折相关
  ]
}
```

过滤规则（硬编码映射，不依赖配置文件）：

| chapter_type | 保留 reviewer_focus |
|-------------|---------------------|
| `combat` / `battle` / `action` | `combat_pacing`, `tension_escalation` |
| `daily` / `slice_of_life` / `interlude` | `character_development`, `world_building` |
| `twist` / `revelation` / `turning_point` | `plot_twist`, `revelation`, `tension_escalation` |
| `growth` / `breakthrough` | `character_development`, `tension_escalation` |
| 默认/未知 | 保留全部（不降级）|

## 测试要求

- [ ] `filter_genre_profile` 对 `combat` 类型只返回 2 个 focus
- [ ] `filter_genre_profile` 对未知类型保留全部 focus
- [ ] 过滤后的 `GenreProfile.model_dump_json()` 长度 < 原长度的 60%
- [ ] 集成测试：ContextManager 组装后的 context tokens 减少 >= 400

## 验收标准

- [ ] `pytest tests/ -k "genre or context" -v` 全部通过
- [ ] 至少 3 种 `chapter_type` 的过滤测试覆盖
- [ ] `docs/STATUS.md` 更新
- [ ] 生成 `tasks/067-genre-rules-on-demand-DONE.md`

## 参考文档

- `src/songyan/agents/context_manager/__init__.py` — ContextManager 主入口
- `src/songyan/models/genre.py` — `GenreProfile` 模型
- `src/songyan/models/chapter.py` — `ChapterGoal.chapter_type`
- `genres/scifi.json` — 实际 genre 配置示例
