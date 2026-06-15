# Task 045 交接报告 — ProjectSetting 扩展 + DB 迁移 + Repository 更新

> **状态**: ✅ 已完成
> **完成日期**: 2026-06-03
> **测试**: 929 passed（排除 integration/performance），无回归

---

## 交付内容

### 1. 模型层
- `src/songyan/models/project.py`: `ProjectSetting` 追加 5 个字段
  - `estimated_chapters: int = 30`
  - `words_per_chapter: int = 3000`
  - `story_structure: Literal["three_act", "five_act", "serial", "free"] = "free"`
  - `arc_boundaries_auto: bool = False`
  - `sub_genre_id: str | None = None`
  - `word_range` property: 返回 `(words_per_chapter * 0.8, words_per_chapter * 1.2)`

### 2. DB 层
- `src/songyan/db/schema.sql`: projects 表追加 5 列（含默认值）
- `src/songyan/db/migrations.py`: 新增 `_migrate_project_seed_config()` 增量迁移函数
  - 幂等：多次运行不报错
  - 兼容旧 DB：ALTER TABLE ADD COLUMN IF NOT EXISTS 模式

### 3. Repository 层
- `ProjectRepository.create()`: 写入全部 19 个字段（含新增 5 个）
- `ProjectRepository.get()`: 读取新增字段，默认值兼容
- `ProjectRepository.update_seed_config()`: 部分更新种子配置字段
  - 仅更新非 None 参数
  - 支持 `arc_boundaries` 同时更新

### 4. 测试
- `tests/models/test_project_setting.py` (7 tests):
  - 默认值验证 / word_range property / 边界值 / 全字段 / 非法值拒绝
- `tests/db/test_repository.py` (7 tests 追加):
  - create round-trip / 默认值 round-trip / update_seed_config 全量+部分+空操作
  - 迁移列存在验证 / 迁移幂等性

---

## 修改文件清单

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `src/songyan/models/project.py` | 修改 | 新增 5 字段 + word_range property |
| `src/songyan/db/schema.sql` | 修改 | projects 表追加 5 列 |
| `src/songyan/db/migrations.py` | 修改 | 新增 `_migrate_project_seed_config()` |
| `src/songyan/db/repository.py` | 修改 | create/get/update_seed_config |
| `tests/models/test_project_setting.py` | 新增 | 7 个模型测试 |
| `tests/db/test_repository.py` | 修改 | 追加 7 个 Repository 测试 |
| `docs/STATUS.md` | 修改 | Task 045 标记完成 |
| `tasks/045-project-setting-extension.md` | 新增 | 任务规格 |
| `tasks/045-project-setting-extension-DONE.md` | 新增 | 本交接文件 |

---

## 验证方式

```bash
# 模型测试
pytest tests/models/test_project_setting.py -v

# Repository 测试
pytest tests/db/test_repository.py -v

# 全量（排除 integration/performance）
pytest -k "not performance and not integration" -v
```

---

## 已知限制

- `story_structure` 暂不改造 GoalPlanner，仅存储展示（Phase 8a 约束）
- `sub_genre_id` 不做外键约束，由应用层验证
- 4 个 integration 测试失败为预存问题（settlement mock 数据），与本次改动无关

---

## 下一步

Task 046: CLI `create-project` 新增交互 + 自动推导 arc_boundaries
