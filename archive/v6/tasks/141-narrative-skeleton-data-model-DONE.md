# Task 141 DONE — 叙事骨架数据模型（StoryOutline / ArcPlan / PlotThread）

> **Phase**: V6 阶段 0（最小叙事骨架 MVP）
> **状态**: ✅ 完成（141a + 141b + 141c 全部交付）
> **完成日期**: 2026-07-01
> **规划**: `docs/v6-plan.md` §3 阶段 0；任务书：`archive/v6/tasks/141-narrative-skeleton-data-model.md`

---

## 交付概览

为系统新增三个**自顶向下叙事规划**实体的模型、持久化与 repository 层，作为 V6 阶段 0 地基。与现有回顾型结构（`ArcSummary` / `OpenThread`）独立共存、不合并。

| 子任务 | 交付物 |
|--------|--------|
| 141a | `src/songyan/models/narrative.py`（3 个 Pydantic v2 模型）+ `models/__init__.py` re-export |
| 141b | `db/migrations.py` `_migrate_narrative_skeleton` + 3 张表 + 5 个索引 + `_EXPECTED_TABLES` 注册 + `init_schema`/`run_migrations` 调用 |
| 141c | `src/songyan/db/narrative_repo.py` `NarrativeRepository` + PlotThread 状态机 |
| 测试 | `tests/test_141_narrative_skeleton.py`（17 个用例，模型 / 迁移 / repository 三层） |

## 数据模型（`songyan.models.narrative`）

- `PlotThreadStatus = Literal["planned", "opened", "advanced", "resolved", "abandoned"]`
- `StoryOutline`：`project_id / core_conflict / mainline_synopsis / themes / intended_ending / created_at / updated_at`
- `ArcPlan`：`arc_id / project_id / arc_index(ge=0) / start_chapter(ge=1) / end_chapter(ge=1) / arc_goal / threads_to_open / threads_to_resolve / is_mainline / created_at`
- `PlotThread`：`thread_id / project_id / title / description / is_mainline / opened_chapter / expected_resolve_arc / status / last_status_chapter / last_status_version_id / created_at / updated_at`

均已加入 `songyan.models` re-export（`StoryOutline` / `ArcPlan` / `PlotThread` / `PlotThreadStatus`）。

## 三张表 schema

**story_outlines**（每项目一条，`project_id` 为 PK）
```
project_id TEXT PK → projects(project_id) ON DELETE CASCADE
core_conflict / mainline_synopsis / intended_ending  TEXT DEFAULT ''
themes  TEXT DEFAULT '[]'（JSON 数组）
created_at / updated_at  TEXT DEFAULT (datetime('now'))
```

**arc_plans**（`arc_id` PK）
```
arc_id TEXT PK
project_id TEXT NOT NULL → projects ON DELETE CASCADE
arc_index / start_chapter / end_chapter  INTEGER NOT NULL
arc_goal  TEXT DEFAULT ''
threads_to_open / threads_to_resolve  TEXT DEFAULT '[]'（JSON）
is_mainline  INTEGER DEFAULT 0
created_at  TEXT DEFAULT (datetime('now'))
```

**plot_threads**（`thread_id` PK）
```
thread_id TEXT PK
project_id TEXT NOT NULL → projects ON DELETE CASCADE
title / description  TEXT DEFAULT ''
is_mainline  INTEGER DEFAULT 0
opened_chapter / expected_resolve_arc / last_status_chapter  INTEGER (nullable)
status  TEXT DEFAULT 'planned'
last_status_version_id  TEXT (nullable)
created_at / updated_at  TEXT DEFAULT (datetime('now'))
```

**索引**：`idx_arc_plans_project`、`idx_arc_plans_index(project_id, arc_index)`、`idx_arc_plans_chapter(project_id, start_chapter, end_chapter)`、`idx_plot_threads_project`、`idx_plot_threads_status(project_id, status)`。

**注册（三处，缺一不可）**：`_EXPECTED_TABLES` 追加三表名；`init_schema()` 与 `run_migrations()` 均调用 `_migrate_narrative_skeleton`。schema 版本靠表计数，已确保 `verify_schema` 无 missing、`get_schema_version` 计入新表。

## Repository API（`NarrativeRepository`）

```
upsert_outline(outline)                      # ON CONFLICT(project_id) DO UPDATE
get_outline(project_id) -> StoryOutline|None
add_arc_plan(arc)
list_arc_plans(project_id) -> list[ArcPlan]  # ORDER BY arc_index
get_arc_for_chapter(project_id, chapter) -> ArcPlan|None  # 覆盖该章的弧
add_thread(thread)
list_threads(project_id, status=None) -> list[PlotThread]
get_thread(thread_id) -> PlotThread|None
count_threads_by_status(project_id) -> dict[str, int]     # 供阶段 A/Task 148
advance_thread_status(thread_id, new_status, chapter, version_id)  # T1 可追溯
```

### PlotThread 状态机（在 `advance_thread_status` 内校验）
- 合法迁移：`planned→opened→advanced(→advanced…)→resolved`；任意态 `→abandoned`。
- 非法迁移（如 `resolved→opened`）抛 `InvalidThreadTransitionError`；线索不存在抛 `NarrativeError`（均继承 `SongyanError`，定义于 `narrative_repo.py`）。
- 每次变更写 `last_status_chapter` + `last_status_version_id`（T1 硬要求）；首次转 `opened` 且 `opened_chapter` 为空时回填 `opened_chapter`，后续不覆盖。

## 关键区分自检（与现有模型无冲突）

| 现有 | V6 新增 | 结论 |
|------|---------|------|
| `ArcSummary`（回顾摘要） | `ArcPlan`（前置规划） | 独立表 `arc_summaries` vs `arc_plans`，不合并 |
| `OpenThread`（运行时提取，无状态机） | `PlotThread`（规划实体，有状态机） | 独立模型/表，二者共存 |
| `ProjectSetting.arc_boundaries`（章号数组） | `StoryOutline`+`ArcPlan`（承载剧情） | 边界数组不动，ArcPlan 用 start/end_chapter 关联 |

## 验证

- `pytest tests/test_141_narrative_skeleton.py -q` → **17 passed**。
- `ruff check`（新增/改动文件）→ **All checks passed**。
- 全量 `pytest tests/ -q` → **2035 passed, 2 skipped, 1 xfailed, 16 errors**。16 个 error 全部来自 `tests/test_124_gate_impact.py`，原因是它 import 的一次性调试脚本 `scripts/analyze_124_gate_impact.py` 在 2026-07-01 V6 清理时被删除（该脚本未纳入 git、不在磁盘）；与 Task 141 改动无关（本任务 diff 未触及 `scripts/` 或 test_124），属 **预存在环境问题**。除此之外无新增失败，Task 141 无回归。

## Out of Scope（留待后续任务）

- GoalPlanner 派生（143）、CLI 大纲录入（142）、线索状态随 settlement 更新（144）、显式 resolve/作废出口（阶段 B / 152）均未在本任务实现。
- 未改动 `ArcSummary`/`OpenThread`/`ProjectSetting.arc_boundaries` 现有结构。
