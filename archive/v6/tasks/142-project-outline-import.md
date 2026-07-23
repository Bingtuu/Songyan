# Task 142: 项目创建可携带大纲

> **Phase**: V6 阶段 0（最小叙事骨架 MVP）
> **优先级**: P1
> **依赖**: Task 141（StoryOutline / ArcPlan / PlotThread 模型与 repository）
> **预计工作量**: 中
> **事实入口**: `tasks/V6-README.md`；规划：`docs/v6-plan.md` §3 阶段 0

---

## Goal

让 `create-project` 支持录入/导入全书大纲与弧规划（`StoryOutline` + `ArcPlan` + 初始 `PlotThread`），录入为**可选**，缺省时行为与现状完全一致，且大纲可被后续节点读取。

## Context

Task 141 建好了骨架的模型与持久化层，但没有入口写入数据。当前 `create-project`（`cli/main.py` `_create_project_async`，约 L114-163）只收集 title/genre/主角/core_hook/章数等，`arc_boundaries` 靠 `derive_arc_boundaries` 按百分比自动切分、无剧情内容。本 Task 提供录入骨架的入口，是 Task 143（GoalPlanner 派生）能读到骨架的前提。

**MVP 边界**：只做"能录入、能存、能读回"，不做大纲的智能生成或校验。无大纲的项目必须能完全回退到现状行为（这是 v6-plan §6 风险对策的硬要求）。

## In Scope（必须完成）

- [ ] `create-project` 新增可选的大纲录入路径：支持从 JSON 文件 `--outline-file` 导入（交互式录入全书大纲字段过重，MVP 采用文件导入为主）。
- [ ] 定义大纲导入文件的 schema（StoryOutline + ArcPlan[] + PlotThread[] 的 JSON 结构）与解析/校验。
- [ ] 导入成功后：写入 Task 141 的三张表（经 `NarrativeRepository`）。
- [ ] 缺省路径（不传 `--outline-file`）：项目创建行为与现状**逐字节等价**，不写骨架表。
- [ ] 大纲可被读回：提供/复用读取 API，供 Task 143 使用（若 141c 已提供 `get_outline`/`list_arc_plans` 则直接复用）。

## Out of Scope（明确不做）

- 不做交互式逐字段问答录入大纲（过重，留待后续按需增强）。
- 不做大纲的 LLM 自动生成（V7 可选）。
- 不做大纲与已生成章节的一致性校验。
- 不改 `derive_arc_boundaries` / `arc_boundaries` 现有逻辑——ArcPlan 与 arc_boundaries 并存，ArcPlan 通过 start/end_chapter 关联。

## 接口契约

```python
# cli/main.py 新增参数
@click.option("--outline-file", type=click.Path(exists=True), default=None,
              help="可选：全书大纲 JSON 文件，导入 StoryOutline/ArcPlan/PlotThread")

async def _load_outline_file(path: str, project_id: str) -> tuple[StoryOutline, list[ArcPlan], list[PlotThread]]:
    """解析大纲 JSON，返回骨架对象；格式错误抛自定义异常."""
    ...
```

### 大纲导入文件格式（示例）

```json
{
  "outline": {
    "core_conflict": "……",
    "mainline_synopsis": "……",
    "themes": ["……"],
    "intended_ending": "……"
  },
  "arc_plans": [
    {"arc_index": 0, "start_chapter": 1, "end_chapter": 20,
     "arc_goal": "……", "threads_to_open": ["t1"], "threads_to_resolve": [],
     "is_mainline": true}
  ],
  "plot_threads": [
    {"thread_id": "t1", "title": "……", "description": "……",
     "is_mainline": true, "expected_resolve_arc": 2}
  ]
}
```

## 测试要求

### Layer 2: 模块测试
- [ ] 正向：合法 outline JSON → 三张表被正确写入，thread_id 与 arc_plans 引用一致。
- [ ] 缺省：不传 `--outline-file` → 骨架表为空，项目其余字段与旧行为一致（快照对比）。
- [ ] 异常：JSON 格式错误 / 必填字段缺失 / thread_id 引用悬空 → 抛自定义异常，不写入半份数据（事务性）。
- [ ] Mock 策略：真实临时 SQLite；文件系统用 tmp_path fixture。

### Layer 3: 集成测试
- [ ] 带大纲创建项目 → 用 `NarrativeRepository` 读回，`get_arc_for_chapter(project_id, 5)` 返回 arc_index=0 的弧。

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/test_142_project_outline.py -v` 全部通过。
- [ ] `ruff check src/ tests/` 通过；全量 pytest 不回归。
- [ ] **缺省项目行为不变**：不传 `--outline-file` 的创建流程与现状等价（这是硬验收项）。
- [ ] 带大纲项目的骨架可被 `NarrativeRepository` 完整读回。
- [ ] 导入失败不留半份数据（事务保证）。
- [ ] 不违反不可违背规则：写操作经 repository/service，不直接拿 connection。
- [ ] 生成 `archive/v6/tasks/142-project-outline-import-DONE.md`，附大纲文件格式说明与一个可用样例。
- [ ] 更新 `tasks/V6-README.md` 与 `docs/STATUS.md`。

## 参考文档

- `docs/v6-plan.md` §3 阶段 0（Task 142 行）
- Task 141：`archive/v6/tasks/141-narrative-skeleton-data-model.md`（模型与 repository API）
- 现有 CLI：`src/songyan/cli/main.py` `_create_project_async`；`src/songyan/models/project.py` `derive_arc_boundaries`
