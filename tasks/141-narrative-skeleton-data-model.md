# Task 141: 叙事骨架数据模型（StoryOutline / ArcPlan / PlotThread）

> **Phase**: V6 阶段 0（最小叙事骨架 MVP）
> **优先级**: P0（阶段 0 基座，142/143/144 全部依赖）
> **依赖**: 无（V6 首个任务）
> **预计工作量**: 大（拆分为 141a / 141b / 141c 三个子任务）
> **事实入口**: `tasks/V6-README.md`；规划：`docs/v6-plan.md` §3 阶段 0

---

## Goal

为系统新增三个**自顶向下的叙事规划**数据模型与持久化层：`StoryOutline`（全书核心冲突/主线）、`ArcPlan`（弧目标 + 应开启/收束的线索）、`PlotThread`（线索：开启章、预期收束弧、生命周期状态），使后续 GoalPlanner 能从骨架派生章节目标、Settlement 能追踪线索状态。

## Context

`docs/300-chapter-gap-analysis.md` §1 确认：系统缺自顶向下叙事架构是 orphan 累积、文学质量无指标的共同根因。当前 `models/` 里只有**回顾型**结构（`ArcSummary`/`VolumeSummary` 是已完成章节的事后摘要，`OpenThread` 是 settlement 运行时提取的开放线索），`ProjectSetting.arc_boundaries` 只是章号数组、无剧情内容。本 Task 建立**前置规划型**骨架，是 V6 阶段 0 的地基。

### 与现有模型的关键区分（必须遵守，避免概念污染）

| 现有模型 | 性质 | V6 新增模型 | 性质 | 区分 |
|----------|------|-------------|------|------|
| `ArcSummary`（context.py:124） | 已完成弧的**事后摘要文本** | `ArcPlan` | 弧的**前置规划**（目标/应开启收束的线索） | 一个回顾、一个前瞻，不合并 |
| `OpenThread`（context.py:165） | settlement 从正文**提取**的开放线索，无状态机 | `PlotThread` | **规划的**线索，有 `opened/advanced/resolved` 状态机 + 预期收束弧 | OpenThread 是运行时副产物，PlotThread 是规划实体，二者独立共存 |
| `ProjectSetting.arc_boundaries`（project.py:26） | 章号边界数组 | `StoryOutline` + `ArcPlan` | 承载剧情内容 | 边界数组保留不动，ArcPlan 通过 `start_chapter/end_chapter` 关联 |

## In Scope（必须完成）

本 Task 拆分为三个子任务，按顺序交付：

- [ ] **141a**：三个 Pydantic v2 模型定义（`models/narrative.py` 新文件 + `__init__.py` re-export）
- [ ] **141b**：数据库 schema 与迁移（`_migrate_narrative_skeleton` + 三张表 + 索引 + `_EXPECTED_TABLES` 注册）
- [ ] **141c**：repository 层（`NarrativeRepository` + CRUD + PlotThread 状态生命周期方法）与单测

## Out of Scope（明确不做）

- 不做 GoalPlanner 派生逻辑（Task 143）。
- 不做 CLI 录入大纲（Task 142）。
- 不做线索状态随 settlement 自动更新（Task 144）——本 Task 只提供 repository 层的状态变更 API，不接入 settlement 流程。
- 不做自动重规划闭环（V7）。
- 不修改 `ArcSummary`/`OpenThread`/`ProjectSetting.arc_boundaries` 现有结构。

---

## 141a：叙事骨架 Pydantic 模型

### 数据模型

新建 `src/songyan/models/narrative.py`：

```python
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

PlotThreadStatus = Literal["planned", "opened", "advanced", "resolved", "abandoned"]


class StoryOutline(BaseModel):
    """全书大纲 — 自顶向下叙事骨架的顶层."""

    project_id: str
    core_conflict: str = ""            # 全书核心冲突（一句话）
    mainline_synopsis: str = ""        # 主线梗概（~300 字）
    themes: list[str] = Field(default_factory=list)
    intended_ending: str = ""          # 预期结局方向
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ArcPlan(BaseModel):
    """弧规划 — 前置规划（区别于回顾型 ArcSummary）."""

    arc_id: str
    project_id: str
    arc_index: int = Field(ge=0)       # 第几个弧
    start_chapter: int = Field(ge=1)
    end_chapter: int = Field(ge=1)
    arc_goal: str = ""                 # 本弧要达成的叙事目标
    threads_to_open: list[str] = Field(default_factory=list)   # 应开启的 thread_id
    threads_to_resolve: list[str] = Field(default_factory=list)  # 应收束的 thread_id
    is_mainline: bool = False          # 是否主线弧（T1 判据依赖）
    created_at: datetime = Field(default_factory=datetime.now)


class PlotThread(BaseModel):
    """剧情线索 — 规划实体，有生命周期状态机."""

    thread_id: str
    project_id: str
    title: str = ""
    description: str = ""
    is_mainline: bool = False          # 主线线索（T1 判据依赖）
    opened_chapter: int | None = None  # 实际开启章（opened 时写入）
    expected_resolve_arc: int | None = None  # 预期收束弧 arc_index
    status: PlotThreadStatus = "planned"
    last_status_chapter: int | None = None    # 最近一次状态变更章
    last_status_version_id: str | None = None  # 变更来源 version（T1 可追溯要求）
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
```

### 设计要点

- `PlotThreadStatus` 状态机：`planned → opened → advanced → resolved`，任意态可 `→ abandoned`（对应 Task 152 的显式作废）。
- `is_mainline`（在 ArcPlan 与 PlotThread 都有）是 §1.4-T1「主线线索可追溯状态跃迁」判据的结构基础。
- `last_status_version_id` 满足 T1「每次变更可定位到 source_version_id」的硬要求。

### 141a 测试要求（Layer 1: 模型测试）

- [ ] 三个模型可正确实例化（最小字段 + 全字段）。
- [ ] `PlotThread.status` 只接受 `PlotThreadStatus` 枚举值，非法值抛 `ValidationError`。
- [ ] `ArcPlan.arc_index` 边界（`ge=0`）、`start_chapter/end_chapter`（`ge=1`）验证。
- [ ] `__init__.py` re-export 后 `from songyan.models import StoryOutline, ArcPlan, PlotThread` 可用。

---

## 141b：数据库 schema 与迁移

### 交付物

在 `src/songyan/db/migrations.py` 新增 `async def _migrate_narrative_skeleton(conn)`，建三张表（`story_outlines` / `arc_plans` / `plot_threads`），全部 `CREATE TABLE IF NOT EXISTS` + `REFERENCES projects(project_id) ON DELETE CASCADE`，并建常用索引（`project_id`、`plot_threads.status`、`arc_plans.arc_index`）。

### 接口契约

```python
async def _migrate_narrative_skeleton(conn: aiosqlite.Connection) -> None:
    """创建叙事骨架三张表（story_outlines / arc_plans / plot_threads）."""
    ...
```

### 注册要求（三处，缺一不可）

- [ ] `init_schema()` 中调用 `_migrate_narrative_skeleton`。
- [ ] `run_migrations()` 中调用 `_migrate_narrative_skeleton`。
- [ ] 三张表名加入 `_EXPECTED_TABLES`（migrations.py:20-52）——注意：schema 版本靠表计数（`get_schema_version` = 已存在期望表数），漏注册会导致 `verify_schema` 误判。

### 141b 测试要求

- [ ] 新建临时 DB 跑 `init_schema()` 后，三张表存在（`sqlite_master` 查询）。
- [ ] 对已有旧 DB（缺三张表）跑 `run_migrations()` 后三张表被补齐，且不破坏现有表数据。
- [ ] `verify_schema` 无 missing；`get_schema_version` 计入新表。
- [ ] `ON DELETE CASCADE`：删除 project 后关联的三表记录被级联删除。

---

## 141c：repository 层与状态生命周期

### 接口契约

新建 `src/songyan/db/narrative_repo.py`，`NarrativeRepository`（遵守"写操作集中在 repository、Agent 不直接拿 connection"规则）：

```python
class NarrativeRepository:
    # StoryOutline
    async def upsert_outline(self, outline: StoryOutline) -> None: ...
    async def get_outline(self, project_id: str) -> StoryOutline | None: ...

    # ArcPlan
    async def add_arc_plan(self, arc: ArcPlan) -> None: ...
    async def list_arc_plans(self, project_id: str) -> list[ArcPlan]: ...
    async def get_arc_for_chapter(self, project_id: str, chapter: int) -> ArcPlan | None: ...

    # PlotThread
    async def add_thread(self, thread: PlotThread) -> None: ...
    async def list_threads(self, project_id: str, status: PlotThreadStatus | None = None) -> list[PlotThread]: ...
    async def get_thread(self, thread_id: str) -> PlotThread | None: ...
    async def advance_thread_status(
        self, thread_id: str, new_status: PlotThreadStatus,
        chapter: int, version_id: str,
    ) -> None:
        """变更线索状态，写入 last_status_chapter/version_id（T1 可追溯）."""
        ...
```

### 状态机约束（在 `advance_thread_status` 内校验）

- 合法迁移：`planned→opened→advanced→resolved`；任意态 `→abandoned`。
- 非法迁移（如 `resolved→opened`）抛自定义异常（不用裸 except）。
- 每次变更必须写 `last_status_chapter` 与 `last_status_version_id`（T1 硬要求）。

### 141c 测试要求

- [ ] **Layer 2 正向**：upsert/get outline；add/list arc_plans；`get_arc_for_chapter` 返回覆盖该章的弧。
- [ ] **Layer 2 状态机**：合法迁移链 `planned→opened→advanced→resolved` 逐步成功，每步 `last_status_version_id` 正确写入。
- [ ] **Layer 2 异常**：非法迁移抛异常；`abandoned` 可从任意态进入。
- [ ] Mock 策略：真实临时 SQLite（本地文件/内存），不 Mock DB（repository 层测真实 SQL）。

---

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/test_141_narrative_skeleton.py -v` 全部通过（模型 + 迁移 + repository 三层）。
- [ ] `ruff check src/ tests/` 通过。
- [ ] 全量 `pytest tests/ -q` 不回归（现有 2036 passed 基线不降）。
- [ ] 不破坏现有 schema：旧项目 DB 跑迁移后现有表与数据完好。
- [ ] 不违反不可违背规则：写操作集中在 repository；模型 Pydantic v2 字段完整；类型标注齐全。
- [ ] 与 `OpenThread`/`ArcSummary` 无字段/语义冲突（本文「关键区分」表逐条自检）。
- [ ] 生成 `tasks/141-narrative-skeleton-data-model-DONE.md` 交接文件，记录三张表 schema 与 repository API。
- [ ] 更新 `tasks/V6-README.md`（141 状态 → 完成）与 `docs/STATUS.md`。

## 参考文档

- `docs/v6-plan.md` §1.4-T1（主线线索可追溯状态跃迁判据）、§3 阶段 0
- `docs/300-chapter-gap-analysis.md` §1（根因：缺自顶向下叙事架构）
- 现有模型参考：`src/songyan/models/context.py`（ArcSummary/OpenThread）、`src/songyan/models/project.py`（ProjectSetting）
- 迁移参考：`src/songyan/db/migrations.py` `_migrate_layered_context_tables`（建表示例）
