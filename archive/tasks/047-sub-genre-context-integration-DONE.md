# Task 047 交接报告 — GenreProfile.sub_genres 注入 ContextManager

> **状态**: ✅ 已完成
> **完成日期**: 2026-06-03
> **测试**: 919 passed（排除 performance/integration/eval_runner），无回归
> **依赖**: Task 045

---

## 交付内容

### 1. 模型层
- `src/songyan/models/context.py`: `GenreRules` 新增 `sub_genre_rules: list[str]` 字段

### 2. ContextManager
- `src/songyan/agents/context_manager.py`:
  - `_build_genre_rules()` 新增 `project: ProjectSetting` 参数
  - 当 `project.sub_genre_id` 匹配 `genre_profile.sub_genres` 时，注入 `SubGenre.differentiation_rules`
  - 不匹配或无 `sub_genre_id` 时，`sub_genre_rules` 保持空列表

### 3. 调用点修复
- `src/songyan/workflows/_nodes.py`: 两处 `_build_genre_rules(genre)` → `_build_genre_rules(genre, project)`
  - `rule_auditor_node` (line 207)
  - `settlement_extractor_node` (line 541)

### 4. 测试
- `tests/test_context_manager.py` (4 个测试):
  - `test_conversion`: 基础转换 + sub_genre_rules 为空
  - `test_sub_genre_rules_injected`: 匹配成功时注入 differentiation_rules
  - `test_sub_genre_mismatch_ignored`: 不匹配时保持空列表
  - `test_no_sub_genre_id_empty_rules`: 无 sub_genre_id 时保持空列表

---

## 修改文件清单

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `src/songyan/models/context.py` | 修改 | `GenreRules` 新增 `sub_genre_rules` |
| `src/songyan/agents/context_manager.py` | 修改 | `_build_genre_rules` 注入子类型规则 |
| `src/songyan/workflows/_nodes.py` | 修改 | 两处调用更新参数 |
| `tests/test_context_manager.py` | 修改 | 4 个 GenreRules 测试 |
| `docs/STATUS.md` | 修改 | Task 047 标记完成 |
| `tasks/047-sub-genre-context-integration.md` | 新增 | 任务规格 |
| `tasks/047-sub-genre-context-integration-DONE.md` | 新增 | 本交接文件 |

---

## 验证方式

```bash
pytest tests/test_context_manager.py::TestBuildGenreRules -v
```

---

## 已知限制

- 当前 genre 配置中 `sub_genres` 为空列表，功能已就绪但无实际子类型可注入
- 子类型规则追加到 `GenreRules.sub_genre_rules`，Writer Prompt 尚未渲染此字段（Phase 8b 可考虑注入）

---

## Phase 8a 完成总结

Task 045~047 全部完成：
- ✅ Task 045: ProjectSetting 扩展 + DB 迁移 + Repository
- ✅ Task 046: CLI create-project 交互增强 + arc_boundaries 自动推导
- ✅ Task 047: sub_genre 注入 ContextManager

**Phase 8a 全部完成**。下一步进入 Phase 8b：
- Task 048: Embedding 模型选型基准测试（BGE-M3 验证）
