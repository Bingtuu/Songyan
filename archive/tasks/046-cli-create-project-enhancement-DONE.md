# Task 046 交接报告 — CLI `create-project` 新增交互 + 自动推导 arc_boundaries

> **状态**: ✅ 已完成
> **完成日期**: 2026-06-03
> **测试**: 931 passed（排除 integration/performance），无回归
> **依赖**: Task 045

---

## 交付内容

### 1. 模型层
- `src/songyan/models/project.py`: 新增 `derive_arc_boundaries(structure, chapters)` 函数
  - `three_act`: 25% / 50% / 25% 分界
  - `five_act`: 每 20% 一个分界
  - `serial`: 每 25 章一个分界
  - `free`: 返回空列表

### 2. CLI 层
- `src/songyan/cli/main.py`:
  - `_select_story_structure()`: 4 选 1 交互选择（带默认 free）
  - `_select_sub_genre(genre_id)`: 基于 GenreProfile.sub_genres 动态列出子类型，空列表时自动跳过
  - `_create_project_async()`: 追加 4 个交互步骤 + 自动推导 arc_boundaries
  - `create_project` 输出: 新增预估章数/每章字数/结构/子类型/Arc 边界展示

### 3. 测试
- `tests/cli/test_cli.py` (3 个新测试):
  - `test_seed_fields_stored_in_db`: 验证 DB 写入新增字段
  - `test_three_act_derives_arc_boundaries`: 验证三幕式 → [10, 30] 自动推导
  - 更新了 `_INPUT` 和 `_CREATE_INPUT` 以覆盖新增交互

---

## 修改文件清单

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `src/songyan/models/project.py` | 修改 | 新增 `derive_arc_boundaries()` |
| `src/songyan/cli/main.py` | 修改 | 交互增强 + 自动推导 |
| `tests/cli/test_cli.py` | 修改 | 3 个新测试 + 输入更新 |
| `docs/STATUS.md` | 修改 | Task 046 标记完成 |
| `tasks/046-cli-create-project-enhancement.md` | 新增 | 任务规格 |
| `tasks/046-cli-create-project-enhancement-DONE.md` | 新增 | 本交接文件 |

---

## 验证方式

```bash
pytest tests/cli/test_cli.py -v
```

---

## 已知限制

- 当前所有 genre 配置中 `sub_genres` 为空列表，CLI 自动跳过子类型选择
- 自动推导的 arc_boundaries 可通过 `update_seed_config` 后续修改

---

## 下一步

Task 047: `GenreProfile.sub_genres` 注入 ContextManager
