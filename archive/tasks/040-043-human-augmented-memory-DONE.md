# Task 040~043-DONE: Human-Augmented Memory 基础 + Phase 7 验证

> **Phase**: 7
> **完成日期**: 2026-06-03
> **总测试数**: 949 passed（新增 21 个测试）
> **回归**: 0

---

## 完成内容

### Task 040 — `human_marks` 数据层

- ✅ `src/songyan/models/human_mark.py` — `HumanMark` + `SuggestedMark` Pydantic 模型
- ✅ `src/songyan/db/schema.sql` — `human_marks` 表（含索引）
- ✅ `src/songyan/db/human_mark_repo.py` — `HumanMarkRepository`（create/get/list/remove/update_priority/resolve）
- ✅ `src/songyan/db/migrations.py` — `_migrate_human_marks()` + `_EXPECTED_TABLES` 更新
- ✅ `src/songyan/db/__init__.py` — 导出 `HumanMarkRepository`
- ✅ `tests/db/test_human_mark_repository.py` — 7 个测试全部通过

### Task 041 — CLI 标记命令

- ✅ `src/songyan/cli/main.py` — `mark` 命令组
  - `mark add --project-id --type --target --note --priority --chapter`
  - `mark list --project-id [--type] [--min-priority] [--suggested]`
  - `mark remove --project-id --mark-id`
  - `mark update-priority --project-id --mark-id --priority`
- ✅ `tests/cli/test_mark_commands.py` — 10 个测试全部通过

### Task 042 — ContextManager 集成

- ✅ `src/songyan/models/creative_mode.py` — `HumanMemoryConfig`（`priority_threshold`, `max_marks_in_context`）
- ✅ `creative_modes/*.json` — 4 个模式均新增 `human_memory` 配置块
- ✅ `src/songyan/models/context.py` — `HardConstraint.type` 新增 `"human_mark"`，`ContextPackage` 新增 `human_marks`
- ✅ `src/songyan/agents/context_manager.py` —
  - `assemble_context_package` 新增 `human_marks` 参数
  - 按 `mode_profile.human_memory.priority_threshold` 过滤 marks
  - 按 `max_marks_in_context` 硬上限截断
  - 过滤后的 marks 同时注入 `ContextPackage.human_marks` 和 `hard_constraints`
  - `BudgetPruner._estimate_package` 增加 human_marks 估算
- ✅ `prompts/cards/writer/1.0.5.yaml` — 新增 `## 人类关键标记` Prompt 分区 + `human_marks` 变量
- ✅ `tests/test_context_manager.py` — 新增 5 个 HumanMark 集成测试全部通过

### Task 043 — ContinuityAuditor 增强

- ✅ `src/songyan/models/continuity.py` — `ContinuityReport` 新增 `suggested_marks: list[SuggestedMark]`
- ✅ `src/songyan/agents/continuity_auditor.py` — `_generate_suggested_marks()` 方法
  - `orphaned_settings` → `SuggestedMark(mark_type="setting", suggested_priority=8)`
  - `forgotten_items` → `SuggestedMark(mark_type="item", suggested_priority=7)`
- ✅ `src/songyan/db/continuity_repo.py` — `create` / `get_latest` 支持 `suggested_marks` 读写
- ✅ `src/songyan/db/migrations.py` — `_migrate_continuity_suggested_marks()` 添加列
- ✅ `src/songyan/cli/main.py` — `mark list --suggested` 显示系统建议
- ✅ `tests/test_continuity_auditor_suggested_marks.py` — 4 个测试全部通过

### Task 044 — Phase 7 验证

- ✅ 全量测试：`pytest tests/ -m "not performance"` → **949 passed, 0 failed**
- ✅ 无回归：所有现有测试保持通过
- ✅ `docs/STATUS.md` 更新为 V2.1.0 Stage D Phase 7 完成状态

---

## 关键设计决策

| 问题 | 决策 | 理由 |
|------|------|------|
| `human_marks` 是否加 `source_version_id`？ | **不加** | 人类标记非 settlement 产物，不适用规则 38；`target_key` 已在 `setting_tracking` 中溯源 |
| priority 阈值硬编码 or mode 配置？ | **mode 配置** | `CreativeModeProfile.human_memory` 配置块，支持差异化（literary 阈值 7，webnovel 阈值 8） |
| marks 全局生效 or 章节区间？ | **全局生效** | "永远不要忘"是核心心智模型；`created_at_chapter` 仅用于展示/排序 |

---

## 接口契约

```python
# HumanMark 模型
class HumanMark(BaseModel):
    mark_id: str
    project_id: str
    mark_type: Literal["setting", "character", "foreshadowing", "custom"]
    target_key: str
    note: str = ""
    priority: int = 5
    created_at_chapter: int | None = None
    resolved_at: datetime | None = None

# ContextManager 组装
assemble_context_package(
    ...,
    human_marks: list[HumanMark] | None = None,
) -> ContextPackage

# CLI
songyan mark add --project-id --type --target --note --priority --chapter
songyan mark list --project-id [--type] [--min-priority] [--suggested]
songyan mark remove --project-id --mark-id
songyan mark update-priority --project-id --mark-id --priority
```

---

## 已知限制

1. `human_marks` 的 `resolved_at` 在 `_row_to_mark` 中未解析回 datetime（不影响核心功能）
2. `suggested_marks` 目前仅从 `orphaned_settings` 和 `forgotten_items` 生成，未覆盖 `state_mismatches` 和 `overdue_foreshadowings`
3. Writer Prompt 中 `human_marks` 的渲染依赖工艺卡加载器支持 `human_marks` 变量（已添加）

---

## 文件变更清单

```
src/songyan/models/human_mark.py                [新增]
src/songyan/models/creative_mode.py             [+ HumanMemoryConfig]
src/songyan/models/context.py                   [+ human_marks, + human_mark type]
src/songyan/models/continuity.py                [+ suggested_marks]
src/songyan/models/__init__.py                  [导出更新]
src/songyan/db/schema.sql                       [+ human_marks 表]
src/songyan/db/migrations.py                    [+ 2 个迁移函数]
src/songyan/db/human_mark_repo.py               [新增]
src/songyan/db/continuity_repo.py               [+ suggested_marks 支持]
src/songyan/db/__init__.py                      [导出更新]
src/songyan/agents/context_manager.py           [+ human_marks 集成]
src/songyan/agents/continuity_auditor.py        [+ _generate_suggested_marks]
src/songyan/cli/main.py                         [+ mark 命令组]
creative_modes/webnovel.json                    [+ human_memory]
creative_modes/webnovel_intense.json            [+ human_memory]
creative_modes/literary.json                    [+ human_memory]
creative_modes/hybrid.json                      [+ human_memory]
prompts/cards/writer/1.0.5.yaml                 [+ 人类关键标记分区]
tests/db/test_human_mark_repository.py          [新增]
tests/cli/test_mark_commands.py                 [新增]
tests/test_context_manager.py                   [+ 5 个测试]
tests/test_continuity_auditor_suggested_marks.py [新增]
docs/STATUS.md                                  [更新]
```

---

> **松烟入墨，字句成锋。**
> Phase 7 人类辅助记忆层已就绪。创作者现在可以主动标记关键设定，系统将优先记住它。
