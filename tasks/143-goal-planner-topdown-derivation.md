# Task 143: GoalPlanner 自顶向下派生

> **Phase**: V6 阶段 0（最小叙事骨架 MVP）
> **优先级**: P0（阶段 0 出口 (a) ≥90% 章节目标可追溯到 ArcPlan 的直接实现）
> **依赖**: Task 141（骨架模型/repository）、Task 142（大纲录入，用于产出测试数据）
> **预计工作量**: 大（拆分为 143a / 143b 两个子任务）
> **事实入口**: `tasks/V6-README.md`；规划：`docs/v6-plan.md` §3 阶段 0

---

## Goal

让 GoalPlanner 的章节目标从"反应式只看上一章摘要"升级为"自顶向下从弧规划派生"：输入增加**当前弧目标 + 本弧未收束线索 + 临近兑现伏笔**，使 ≥90% 的章节目标可在 report 追溯到某条 `ArcPlan`；无大纲项目完全回退旧行为。

## Context

代码核实（探查确认）：`goal_planner.py` `define_chapter_goal`（约 L184-266）当前输入仅 `previous_summary`（→ prompt 变量 `recent_summaries`）+ 静态设定（project/genre/mode profile）；`character_states` 参数存在但注释明确"当前版本不注入 Prompt"。prompt 是工艺卡系统，加载 `prompts/cards/goal_planner/1.0.0.yaml`（不是 `PROMPT_PATH` 常量指向的旧 md）。输出为 `ChapterGoal`（chapter.py）。

这是 §1 根因（GoalPlanner 只看上一章 120 字、无前瞻结构）的直接修复点。

**MVP 边界**：只做"骨架上下文注入 + 从弧派生"，不做 plan→generate→re-plan 自动重规划闭环（V7）。无大纲时**必须**回退到现有行为（v6-plan §6 硬要求）。

## In Scope（必须完成）

拆分为两个子任务：

- [ ] **143a**：骨架上下文加载器——给定 project_id + chapter_number，返回"当前弧目标 + 本弧未收束线索 + 临近兑现伏笔"结构化上下文；无骨架时返回空并标记 fallback。
- [ ] **143b**：GoalPlanner prompt 注入 + 派生逻辑 + 回退——工艺卡升版注入弧/线索上下文，`define_chapter_goal` 消费骨架上下文，无骨架走旧路径。

## Out of Scope（明确不做）

- 不做线索状态随 settlement 更新（Task 144）。
- 不做自动重规划闭环（V7）。
- 不改 `ChapterGoal` 输出结构（保持向后兼容；如需新增可追溯字段，只加可选字段不删旧字段）。
- 不改 Context Diet 2.0 预算组装逻辑；骨架上下文作为 GoalPlanner 专用输入，不进 Writer 的 ContextPackage（那是 Task 144 的事）。

---

## 143a：骨架上下文加载器

### 接口契约

新建 `src/songyan/workflows/_narrative_context.py`（或置于 `_helpers.py`，遵循现有组织）：

```python
class NarrativeGoalContext(BaseModel):
    """GoalPlanner 用的骨架派生上下文（无骨架时全空 + has_skeleton=False）."""
    has_skeleton: bool = False
    arc_goal: str = ""
    arc_index: int | None = None
    is_mainline_arc: bool = False
    open_threads: list[dict] = Field(default_factory=list)     # 本弧未收束线索（thread_id/title/status）
    threads_to_resolve: list[dict] = Field(default_factory=list)  # 本弧应收束线索
    due_foreshadowings: list[dict] = Field(default_factory=list)  # 临近兑现伏笔（复用现有 foreshadowing 查询）

async def load_narrative_goal_context(
    project_id: str, chapter_number: int, repo: NarrativeRepository, ...
) -> NarrativeGoalContext:
    """从骨架表 + 现有伏笔表组装 GoalPlanner 上下文；无骨架返回 has_skeleton=False."""
    ...
```

### 设计要点

- "当前弧"：`repo.get_arc_for_chapter(project_id, chapter_number)`。
- "本弧未收束线索"：`list_threads(project_id, status in [opened, advanced])` 且 thread 属于当前/更早弧。
- "临近兑现伏笔"：复用现有 foreshadowing 查询（不新建机制），取 expected_resolve 临近当前章的。
- 无当前弧（无大纲或超出规划范围）→ `has_skeleton=False`，触发 143b 的回退。

### 143a 测试要求

- [ ] Layer 2 正向：带骨架项目 → 返回正确 arc_goal + open_threads + threads_to_resolve。
- [ ] Layer 2 回退：无骨架项目 → `has_skeleton=False`，各列表为空。
- [ ] 边界：chapter 超出所有 ArcPlan 范围 → `has_skeleton=False`。
- [ ] Mock：真实临时 SQLite + Task 141 repository。

---

## 143b：GoalPlanner prompt 注入 + 派生 + 回退

### 交付物

- [ ] 工艺卡升版：`prompts/cards/goal_planner/1.1.0.yaml`（+ manifest 更新），新增可选注入块——弧目标 / 本弧应推进收束的线索 / 临近伏笔。措辞遵循"从弧目标派生本章目标、优先推进未收束线索"。
- [ ] `define_chapter_goal` 新增可选入参 `narrative_ctx: NarrativeGoalContext | None`；`has_skeleton=True` 时注入新变量，`False`（或 None）时**走完全等价的旧 prompt 路径**。
- [ ] 章节目标可追溯：`ChapterGoal` 增加可选字段 `derived_from_arc: int | None`（记录派生自哪个 arc_index），供 report 统计"≥90% 章节目标可追溯到 ArcPlan"。

### 接口契约

```python
async def define_chapter_goal(
    ..., previous_summary: str = "",
    narrative_ctx: NarrativeGoalContext | None = None,  # 新增
    ...
) -> ChapterGoal:
    """has_skeleton 时从弧派生并回填 derived_from_arc；否则旧行为不变."""
    ...
```

### 143b 测试要求

- [ ] Layer 2 派生：注入骨架上下文 → prompt 含弧目标/线索变量；产出 `ChapterGoal.derived_from_arc == 当前 arc_index`。
- [ ] Layer 2 回退：`narrative_ctx=None` 或 `has_skeleton=False` → prompt 与旧版逐字段等价，`derived_from_arc is None`，产出结构不变。
- [ ] Mock：Mock LLM（返回固定 ChapterGoal JSON），断言 prompt 组装变量而非 LLM 输出。
- [ ] 行为漂移防护：用固定输入对比新旧 prompt 文本 diff，确认无骨架时零差异。

---

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/test_143_goal_planner_topdown.py -v` 全部通过。
- [ ] `ruff check src/ tests/` 通过；全量 pytest 不回归。
- [ ] **回退等价性**：无骨架项目的 GoalPlanner prompt 与产出与现状零差异（硬验收，用 diff 断言）。
- [ ] 带骨架项目：`ChapterGoal.derived_from_arc` 正确回填，可支撑"≥90% 章节目标追溯到 ArcPlan"统计。
- [ ] 不违反不可违背规则：GoalPlanner 仍只输出结构化规划、不写正文；prompt 放工艺卡不写代码里；类型标注齐全。
- [ ] 生成 `tasks/143-goal-planner-topdown-derivation-DONE.md`，含新旧 prompt 对比结论与派生逻辑说明。
- [ ] 更新 `tasks/V6-README.md` 与 `docs/STATUS.md`。

### 与阶段 0 出口的关系

本 Task 直接支撑 v6-plan 阶段 0 出口判据 (a)「≥90% 章节目标可在 report 追溯到某条 ArcPlan」。该出口的**报告展示**依赖阶段 A 的 report 能力（见 Task 145 及 v6-plan 修正说明），本 Task 只保证 `derived_from_arc` 数据被正确产出与持久化。

## 参考文档

- `docs/v6-plan.md` §3 阶段 0（Task 143 行 + 阶段 0 出口）、§6 风险（GoalPlanner prompt 膨胀/漂移对策）
- Task 141/142：骨架模型、repository、大纲录入
- 现有代码：`src/songyan/agents/goal_planner.py` `define_chapter_goal`；`prompts/cards/goal_planner/1.0.0.yaml`；`src/songyan/models/chapter.py` `ChapterGoal`
