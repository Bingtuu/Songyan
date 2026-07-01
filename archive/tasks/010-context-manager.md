# Task 010: ContextManager Agent

> **Phase**: Phase 2 — 写前管线
> **优先级**: P0
> **依赖**: Task 008 (GoalPlanner), Task 009 (CreativeDirector), Task 003 (SQLite Schema), Task 004 (Repository)
> **预计工作量**: 中

---

## Goal

实现上下文包组装器 —— 将 GoalPlanner 的 ChapterGoal、CreativeDirector 的 CreativeBrief，以及角色状态、剧情摘要、伏笔线索、设定快照等数据源，组装成按 Token 预算裁剪的 `ContextPackage`，作为 Writer Agent 的输入。

## Context

ContextPackage 是 Writer Agent 的输入上下文。它包含 7 个分区，按优先级排列：
1. 硬约束（最高优先级，不可裁剪）
2. 角色状态快照
3. 最近剧情
4. 伏笔线索
5. 软参考（最低优先级，超预算时先裁剪）
6. 题材规则
7. 创作模式规则

当组装内容超出 Token 预算时，按优先级从低到高裁剪，确保核心信息（ChapterGoal + CreativeBrief + 硬约束）始终保留。

## In Scope（必须完成）

- [ ] `ContextManager` 模块：`assemble_context_package()` 主入口
- [ ] 分区组装：硬约束、角色状态、最近剧情、伏笔、软参考、题材规则、模式规则
- [ ] Token 估算：`tiktoken` 为主，字符数/4 为回退
- [ ] Token 预算裁剪：按优先级从低到高裁剪
- [ ] 新增 Repository 方法：`SummaryRepository.list_recent()`、`CharacterRepository.list_recent_states_by_project()`
- [ ] 测试：Token 估算、分区组装、预算裁剪、边界条件

## Out of Scope（明确不做）

- 不实现 LLM 调用（ContextManager 是纯数据组装，无 LLM）
- 不做上下文包的持久化存储（由 Writer 的 generation_metadata 保存）
- 不做复杂的语义相关性排序（soft_references 按简单规则裁剪）

## 接口契约

```python
# 主入口
async def assemble_context_package(
    chapter_goal: ChapterGoal,
    creative_brief: CreativeBrief | None,
    genre_profile: GenreProfile,
    mode_profile: CreativeModeProfile,
    project: ProjectSetting,
    characters: list[Character],
    character_states: list[CharacterState],
    recent_summaries: list[ChapterSummary],
    active_foreshadowings: list[ForeshadowingItem],
    setting_snapshots: list[NewSetting],
    budget_tokens: int = 8000,
) -> ContextPackage:
    """组装上下文包并按 Token 预算裁剪."""

# Token 估算
class TokenEstimator:
    def estimate(self, text: str) -> int: ...
    def estimate_model(self, obj: BaseModel) -> int: ...

# 预算裁剪
class BudgetPruner:
    def prune(self, ctx: ContextPackage, budget: int) -> ContextPackage: ...
```

## 数据模型

复用已有的 `ContextPackage` 及其子模型（`HardConstraint`, `CharacterStateSnapshot`, `RecentPlot`, `ChapterSummary`, `ForeshadowingItem`, `SoftReference`, `GenreRules`, `ModeRules`）。

## 测试要求

### Layer 1: Token 估算
- [ ] `TokenEstimator.estimate()` 对空字符串返回 0
- [ ] `TokenEstimator.estimate()` 对中文文本返回合理值
- [ ] `TokenEstimator.estimate_model()` 对 Pydantic 模型返回合理值

### Layer 2: 分区组装
- [ ] 硬约束从 chapter_goal.obligations + genre.taboos + project.taboos 组装
- [ ] 角色状态从 characters + character_states 组装
- [ ] 最近剧情从 summaries 组装
- [ ] 伏笔从 active foreshadowings 组装
- [ ] 软参考从 setting_snapshots 组装
- [ ] GenreRules 从 GenreProfile 转换
- [ ] ModeRules 从 CreativeModeProfile 转换

### Layer 3: 预算裁剪
- [ ] 未超预算时不裁剪
- [ ] 超预算时先裁剪 soft_references
- [ ] 继续超预算时裁剪 foreshadowing
- [ ] 继续超预算时裁剪 recent_plot（减少 summaries 数量）
- [ ] 继续超预算时裁剪 character_states（只保留主角）
- [ ] chapter_goal 和 creative_brief 始终保留

### Layer 4: 集成测试
- [ ] 端到端组装 + 裁剪流程

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/test_context_manager.py -v` 全部通过
- [ ] 代码符合 CLAUDE.md 规范（类型标注、单文件 < 400 行等）
- [ ] 不违反任何不可违背规则
- [ ] 全量测试通过，ruff 0 errors
- [ ] 生成了 tasks/010-context-manager-DONE.md 交接文件

## 参考文档

- `src/songyan/models/context.py` — ContextPackage 数据模型
- `src/songyan/db/schema.sql` — 数据库 Schema
- `src/songyan/db/repository.py` — 现有 Repository
- `src/songyan/db/settlement_repo.py` — Foreshadowing/Setting Repository
