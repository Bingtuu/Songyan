# Task 142 DONE — 项目创建可携带大纲（--outline-file 导入）

> **Phase**: V6 阶段 0（最小叙事骨架 MVP）
> **状态**: ✅ 完成
> **完成日期**: 2026-07-01
> **依赖**: Task 141（叙事骨架模型 / repository）
> **规划**: `docs/v6-plan.md` §3 阶段 0；任务书：`archive/v6/tasks/142-project-outline-import.md`

---

## 交付概览

为 `songyan create-project` 增加**可选**的全书大纲导入路径：从 JSON 文件导入 `StoryOutline` + `ArcPlan[]` + `PlotThread[]`，原子写入 Task 141 的三张骨架表。缺省（不传 `--outline-file`）时项目创建行为与现状逐字节等价，不写任何骨架表。

| 交付物 | 文件 |
|--------|------|
| 大纲解析/校验 + 自定义异常 | `src/songyan/cli/outline_import.py`（`load_outline_file` / `OutlineImportError`） |
| 原子导入 | `src/songyan/db/narrative_repo.py` `NarrativeRepository.import_outline`（单事务 + 失败回滚）；三个写方法新增可选 `conn` 参数 |
| CLI 接线 | `src/songyan/cli/main.py`：`--outline-file` 选项 + `_create_project_async(outline_file=None)` + `SongyanError` 清晰报错 |
| 测试 | `tests/test_142_project_outline.py`（12 用例：解析 / 原子导入 / CLI 缺省 vs 带大纲） |

## 大纲文件格式

```json
{
  "outline": {
    "core_conflict": "少年对抗宗门",
    "mainline_synopsis": "……",
    "themes": ["成长", "复仇"],
    "intended_ending": "登顶宗门之巅"
  },
  "arc_plans": [
    {"arc_index": 0, "start_chapter": 1, "end_chapter": 20,
     "arc_goal": "开局立威", "threads_to_open": ["t1"],
     "threads_to_resolve": [], "is_mainline": true},
    {"arc_index": 1, "start_chapter": 21, "end_chapter": 40,
     "arc_goal": "宗门风波", "threads_to_open": [],
     "threads_to_resolve": ["t1"], "is_mainline": true}
  ],
  "plot_threads": [
    {"thread_id": "t1", "title": "身世之谜", "description": "主角真实身世",
     "is_mainline": true, "expected_resolve_arc": 1}
  ]
}
```

**字段说明**
- `outline`：可全部缺省（各字段有默认值）；`project_id` 由创建流程注入，文件内无需填。
- `arc_plans[]`：`arc_index` / `start_chapter` / `end_chapter` 为必填（缺失即报错）；`arc_id` 可省略，缺省自动生成 `<project_id>-arc<arc_index>`。
- `plot_threads[]`：`thread_id` 必填且唯一。
- 引用完整性：`arc_plans` 的 `threads_to_open` / `threads_to_resolve` 引用的 thread_id 必须在 `plot_threads` 中存在，否则报 `OutlineImportError`。

## 校验与事务性

- `load_outline_file` 逐项校验：JSON 合法、顶层为对象、`arc_plans`/`plot_threads` 为数组、必填字段齐全（Pydantic 约束）、thread_id 唯一、引用不悬空——任一失败抛 `OutlineImportError`（`SongyanError` 子类），**在写库之前**完成。
- `import_outline` 在单个 `get_db()` 事务内写入大纲 + 所有弧 + 所有线索，末尾统一 commit；任一步异常 `rollback` 并抛 `NarrativeError`，**不留半份数据**。
- CLI 命令捕获 `SongyanError` → `click.ClickException`，坏文件给出清晰报错而非未捕获 traceback。

## 缺省行为不变（硬验收）

- `--outline-file` 缺省时 `_create_project_async` 不进入导入分支，骨架三表为空；项目字段（genre/mode/protagonist/story_structure/estimated_chapters 等）与旧流程一致（CLI 测试用 mock 选择器 + `CliRunner` 驱动交互，断言骨架表 `(0,0,0)` 且项目字段正确）。
- 未改动 `derive_arc_boundaries` / `ProjectSetting.arc_boundaries`；ArcPlan 与 arc_boundaries 并存。

## 验证

- `pytest tests/test_142_project_outline.py -q` → **12 passed**。
- `pytest tests/test_141_narrative_skeleton.py tests/test_142_project_outline.py tests/db/test_migrations.py tests/db/test_schema.py -q` → **50 passed**（141 refactor 后无回归）。
- `ruff check`（改动文件）→ **All checks passed**。
- 全量 `pytest tests/ -q`：仅 `tests/test_124_gate_impact.py` 的 16 个预存在 error（缺失一次性脚本 `scripts/analyze_124_gate_impact.py`，与本任务无关），无新增失败。

## Out of Scope（未做）

- 交互式逐字段问答录入大纲、大纲 LLM 自动生成、大纲与已生成章节一致性校验——均按任务书留待后续。
