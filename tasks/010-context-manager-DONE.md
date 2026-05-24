# Task 010: ContextManager Agent — 完成报告

> **完成日期**: 2026-05-24
> **提交**: (待填写)

---

## 做了什么

实现了上下文包组装器 —— 将 GoalPlanner 的 ChapterGoal、CreativeDirector 的 CreativeBrief，以及角色状态、剧情摘要、伏笔线索、设定快照等数据源，组装成按 Token 预算裁剪的 `ContextPackage`，作为 Writer Agent 的输入。

---

## 改了哪些主要文件

### 新增文件

| 文件 | 说明 |
|------|------|
| `src/songyan/agents/context_manager.py` | ContextManager Agent：`assemble_context_package()` 主入口 + `TokenEstimator` + `BudgetPruner` + 7 个分区组装器 |
| `src/songyan/db/context_repo.py` | Context 相关 Repository：`SummaryRepository.list_recent()` + `CharacterStateRepository.list_recent_by_project()` / `list_latest_by_project()` |
| `tests/test_context_manager.py` | ContextManager 测试（36 个测试） |
| `tasks/010-context-manager.md` | 本任务规格文档 |

### 修改文件

| 文件 | 修改 |
|------|------|
| `src/songyan/agents/__init__.py` | 导出 `assemble_context_package` |
| `src/songyan/db/__init__.py` | 导出 `SummaryRepository` 和 `CharacterStateRepository` |

---

## 如何运行

```bash
# 运行 ContextManager 测试
pytest tests/test_context_manager.py -v

# 运行全量测试
pytest tests/ -v

# 代码检查
ruff check src/ tests/
```

---

## 如何验证

```bash
pytest tests/ -v
# 期望：370 passed

ruff check src/ tests/
# 期望：All checks passed
```

---

## 还没做什么（明确边界）

- 不实现 LLM 调用（ContextManager 是纯数据组装，无 LLM）
- 不做上下文包的持久化存储（由 Writer 的 generation_metadata 保存）
- 不做复杂的语义相关性排序（soft_references 按简单规则裁剪）
- Writer Agent（Task 011）

---

## 接口使用示例

```python
from songyan.agents.context_manager import assemble_context_package
from songyan.models import (
    ChapterGoal, CreativeBrief, GenreProfile, CreativeModeProfile,
    ProjectSetting, Character, CharacterState, ChapterSummary,
    ForeshadowingItem, NewSetting,
)

# 加载数据（各上游 Agent 输出 + 项目数据）
chapter_goal = ...      # ChapterGoal
brief = ...             # CreativeBrief | None
genre = ...             # GenreProfile
mode = ...              # CreativeModeProfile
project = ...           # ProjectSetting
characters = [...]      # list[Character]
states = [...]          # list[CharacterState]
summaries = [...]       # list[ChapterSummary]
foreshadowings = [...]  # list[ForeshadowingItem]
settings = [...]        # list[NewSetting]

# 组装上下文包
ctx = await assemble_context_package(
    chapter_goal=chapter_goal,
    creative_brief=brief,
    genre_profile=genre,
    mode_profile=mode,
    project=project,
    characters=characters,
    character_states=states,
    recent_summaries=summaries,
    active_foreshadowings=foreshadowings,
    setting_snapshots=settings,
    budget_tokens=8000,
)

print(ctx.estimated_tokens)   # Token 估算值
print(ctx.budget_used)        # 预算使用率
print(len(ctx.hard_constraints))
print(len(ctx.character_states))
```

---

## 设计要点

- **分区优先级**：chapter_goal (0) > creative_brief (1) > hard_constraints (2) > genre_rules (3) > mode_rules (4) > character_states (5) > recent_plot (6) > foreshadowing (7) > soft_references (8)
- **裁剪策略**：超预算时从低到高逐层裁剪，确保核心信息始终保留
- **Token 估算**：tiktoken (cl100k_base) 为主，字符数/2 为回退
- **预算下限**：MIN_BUDGET_TOKENS = 2000，低于此值自动 clamp
