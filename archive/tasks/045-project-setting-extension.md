# Task 045 — ProjectSetting 扩展 + DB 迁移 + Repository 更新

> **目标**: 扩展 `ProjectSetting` 模型，支撑长期规划、RAG 阈值计算和人工介入节点。
> **Phase**: 8a
> **优先级**: P0
> **依赖**: 无

---

## 新增字段

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `estimated_chapters` | int | 30 | 预估总章数，RAG 阈值计算依据 |
| `words_per_chapter` | int | 3000 | 每章目标字数 |
| `story_structure` | Literal["three_act", "five_act", "serial", "free"] | "free" | 故事结构类型 |
| `arc_boundaries_auto` | bool | False | arc_boundaries 是否为系统自动推导 |
| `sub_genre_id` | str \| None | None | 题材子类型 |

---

## 实现清单

### 1. 模型层
- [ ] `src/songyan/models/project.py`: `ProjectSetting` 追加 5 个字段
- [ ] `word_range` property: 返回 `(words_per_chapter * 0.8, words_per_chapter * 1.2)`

### 2. DB 层
- [ ] `src/songyan/db/schema.sql`: projects 表追加 5 列
- [ ] `src/songyan/db/migrations.py`: 新增 `_migrate_project_seed_config()` 函数
- [ ] `init_schema()` 中调用新迁移

### 3. Repository 层
- [ ] `ProjectRepository.create()`: 写入新增字段
- [ ] `ProjectRepository.get()`: 读取新增字段
- [ ] `ProjectRepository.update_seed_config()`: 支持后续修改种子配置

### 4. 测试
- [ ] `test_project_setting_defaults`: 默认值验证
- [ ] `test_project_setting_word_range`: word_range property
- [ ] `test_repository_create_with_seed_fields`: round-trip
- [ ] `test_repository_update_seed_config`: 更新后读取验证
- [ ] `test_migration_adds_columns`: 迁移后列存在

---

## 验收标准

- [ ] 所有现有测试通过（无回归）
- [ ] 新增 5+ 测试通过
- [ ] `ProjectSetting` 模型验证通过 Pydantic
- [ ] 迁移幂等（多次运行不报错）
- [ ] `update_seed_config` 仅更新允许字段

---

## 已知限制

- `story_structure` 暂不改造 GoalPlanner，仅存储展示
- `sub_genre_id` 不做外键约束，由应用层验证
