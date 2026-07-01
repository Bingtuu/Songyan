# Task 143 DONE — GoalPlanner 自顶向下派生

> **Phase**: V6 阶段 0（最小叙事骨架 MVP）
> **状态**: ✅ 完成（143a + 143b）
> **完成日期**: 2026-07-01
> **依赖**: Task 141（骨架模型/repository）、Task 142（大纲录入）
> **规划**: `docs/v6-plan.md` §3 阶段 0；任务书：`tasks/143-goal-planner-topdown-derivation.md`

---

## 交付概览

让 GoalPlanner 的章节目标从"反应式只看上一章摘要"升级为"自顶向下从弧规划派生"：注入当前弧目标 + 本弧未收束线索 + 临近兑现伏笔，并在 `ChapterGoal.derived_from_arc` 记录派生来源弧。无骨架项目**逐字节回退**旧行为。

| 子任务 | 交付物 |
|--------|--------|
| 143a | `src/songyan/workflows/_narrative_context.py`：`NarrativeGoalContext` 模型 + `load_narrative_goal_context()` |
| 143b | 工艺卡 `prompts/cards/goal_planner/1.1.0.yaml`（+ manifest）；`goal_planner.py` prompt 注入 + 派生 + 回退；`ChapterGoal.derived_from_arc` 字段 + 迁移 + repository 持久化；`goal_planner_node` 接线 |
| 测试 | `tests/test_143_goal_planner_topdown.py`（9 用例：加载器 / 持久化 / prompt 注入 / 回退等价 / 派生） |

## 143a：骨架上下文加载器

`NarrativeGoalContext`（Pydantic v2）字段：`has_skeleton / arc_goal / arc_index / is_mainline_arc / open_threads / threads_to_resolve / due_foreshadowings`。

`load_narrative_goal_context(project_id, chapter_number, repo=None, foreshadowing_repo=None, *, due_window=5)`：
- 当前弧：`NarrativeRepository.get_arc_for_chapter`；无覆盖弧（无大纲/超出规划）→ `has_skeleton=False`。
- 未收束线索：`list_threads(status in {opened, advanced})`（MVP 取全项目未收束线索）。
- 应收束线索：`arc.threads_to_resolve` 逐条 `get_thread` 详情。
- 临近伏笔：**复用现有** `ForeshadowingRepository.list_active`（planted/due），过滤 `chapter <= expected_resolve_chapter <= chapter + due_window`；不新增伏笔机制。

## 143b：prompt 注入 + 派生 + 回退

- **工艺卡 1.1.0**：在 1.0.0 基础上于"## 最近剧情"后插入"## 叙事骨架（自顶向下）"段（弧目标 / 未收束线索 / 应收束线索 / 临近伏笔），新增 4 个字符串变量（`arc_goal` / `open_threads` / `threads_to_resolve` / `due_foreshadowings`）。1.0.0 未改动。
- **版本选择保证回退零差异**：`_render_prompt` 在 `narrative_ctx.has_skeleton=True` 时用 `version="1.1.0"` 注入；否则显式 `version="1.0.0"`，与历史行为逐字节等价（单测用 diff 断言 `narrative_ctx=None` 与 `has_skeleton=False` 输出相同且不含"叙事骨架"）。
- **派生回填**：`define_chapter_goal` 新增可选入参 `narrative_ctx`；`has_skeleton=True` 时 `goal.derived_from_arc = narrative_ctx.arc_index`，否则保持 `None`。`ChapterGoal` 输出结构不变（仅新增可选字段）。
- **持久化**：`ChapterGoal.derived_from_arc: int | None`；迁移 `_migrate_chapter_goal_derived_from_arc`（ALTER `chapter_goals` 加列，注册于 `init_schema` + `run_migrations`）；`ChapterGoalRepository.create/get/get_by_chapter` 读写该列。
- **管线接线**：`goal_planner_node` 先 `load_narrative_goal_context(project_id, chapter_number)` 再传入 `define_chapter_goal`；无骨架自动回退。

## 与阶段 0 出口的关系

本任务保证 `derived_from_arc` 被正确产出与持久化，支撑出口判据 (a)「≥90% 章节目标可追溯到 ArcPlan」。出口的 **report 展示** 依赖阶段 A（Task 145）的 report 读 DB 能力。

## 关键工程约束

- 无运行时循环依赖：`goal_planner`（agents 层）对 `NarrativeGoalContext` 仅在 `TYPE_CHECKING` 下引用，运行时鸭子读取属性；`_narrative_context`（workflows 层）只依赖 db + models。
- GoalPlanner 仍只输出结构化规划、不写正文；prompt 放工艺卡；类型标注齐全。

## 验证

- `pytest tests/test_143_goal_planner_topdown.py -q` → **9 passed**。
- `ruff check`（改动文件）→ **All checks passed**。
- 全量 `pytest tests/ -q` → **2056 passed, 2 skipped, 1 xfailed, 16 errors**（16 error 全为预存在的 `test_124` 缺脚本问题，与本任务无关；相对 142 基线 +9 = 本任务 9 个新单测，无新增失败）。

## Out of Scope（未做）

- 线索状态随 settlement 更新（Task 144）、自动重规划闭环（V7）、Writer ContextPackage 注入骨架（Task 144）均未在本任务实现。
