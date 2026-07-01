# Task 008: 实现 GoalPlanner Agent（拆分自 Planner）

> **Phase**: Phase 2
> **优先级**: P0
> **依赖**: Task 002（数据模型）, Task 004（Repository）, Task 005（Genre Profile）, Task 006（CreativeModeProfile）, Task 007（CLI 创建项目）
> **预计工作量**: 中

---

## Goal

实现章节目标制定 Agent —— 根据项目设定、题材规则、创作模式约束和最近剧情，输出结构化的 `ChapterGoal`。

这是第一个需要调用 LLM 的 Agent，因此本任务同时建立**最小 LLM Client 基础设施**（`llm/client.py`）。

---

## Context

GoalPlanner 是写前阶段的第一个 Agent，负责为每一章制定清晰、可执行的写作目标。它不写正文，只做规划。

在整体流程中的位置：
```
GoalPlanner → CreativeDirector → ContextManager → Writer → ...
```

输入来自 SQLite（项目设定、角色状态、最近章节摘要）和配置文件（Genre Profile、CreativeModeProfile），输出为 `ChapterGoal` 对象，保存到 SQLite。

---

## In Scope（必须完成）

### 1. 最小 LLM Client 基础设施

- `src/songyan/llm/__init__.py`
- `src/songyan/llm/client.py`: `get_llm(temperature: float = 0.7) -> BaseChatModel`
  - 使用 `langchain_community.chat_models.lite_llm.ChatLiteLLM`
  - 从环境变量读取：`LLM_MODEL`（默认 `deepseek-chat`）、`LLM_API_KEY`、`LLM_BASE_URL`
  - 支持温度参数透传
  - 异常处理：API 错误包装为自定义异常 `LLMError`，带 3 次指数退避重试
- `src/songyan/llm/retry.py`: `retry_with_backoff()` 装饰器/包装函数（指数退避）
- `src/songyan/exceptions.py`: 新增 `LLMError`、`LLMResponseParseError`

### 2. GoalPlanner Agent 核心

- `src/songyan/agents/__init__.py`
- `src/songyan/agents/goal_planner.py`:
  - `async def define_chapter_goal(...)` —— 主入口
  - `async def _call_llm_for_goal(...)` —— LLM 调用 + 解析
  - `def _build_goal_prompt(...)` —— Prompt 组装（从 `prompts/goal_planner.md` 加载模板）
  - `def _parse_llm_response(...)` —— 解析 LLM 返回为 `ChapterGoal`

### 3. Prompt 模板

- `prompts/goal_planner.md`: GoalPlanner 专用 Prompt 模板
  - 基于设计文档 `DEFINE_CHAPTER_GOAL_PROMPT`
  - 使用 Jinja2 风格 `{{ variable }}` 占位符
  - 明确输出 JSON Schema 要求

### 4. 数据流

```python
# define_chapter_goal 的输入参数
async def define_chapter_goal(
    db: ChapterGoalRepository,          # Repository 用于保存
    project: ProjectSetting,             # 项目设定
    genre_profile: GenreProfile,         # 题材规则
    mode_profile: CreativeModeProfile,   # 创作模式约束
    chapter_number: int,                 # 章节号
    previous_summary: str,               # 最近剧情摘要
    character_states: list[dict],        # 角色当前状态快照（可选）
) -> ChapterGoal
```

**输出保存**：将 `ChapterGoal` 序列化后通过 `ChapterGoalRepository` 保存到 SQLite。

### 5. 约束遵守

- 遵守 `GenreProfile.pacing_rule`（节奏规则注入 Prompt）
- 遵守 `CreativeModeProfile` 约束（模式描述、容忍阈值注入 Prompt）
- `target_events` 必须具体可执行（1-3 个）
- `hooks` 必须有信息量（不能是空洞的"悬念"）
- `word_count_target` 范围 2000-5000
- `chapter_type` 从 `GenreProfile.chapter_types` 中选择

### 6. 错误处理

| 错误类型 | 处理方式 |
|----------|----------|
| LLM API 错误 | 指数退避重试 3 次，最终抛 `LLMError` |
| LLM 返回非 JSON | 尝试提取 JSON 块，失败则抛 `LLMResponseParseError` |
| Pydantic 验证失败 | 记录原始输出，抛 `LLMResponseParseError` |
| 字段缺失 | 使用默认值填充，记录 warning |

---

## Out of Scope（明确不做）

- 状态结算（SettlementExtractor 负责，Task 016）
- 摘要生成（后续 task）
- ContextManager（Task 010）
- CreativeDirector（Task 009）
- Writer（Task 011）
- 多模型路由（V1.0 只用单一模型）
- Prompt 版本管理系统（V1.5+）
- 流式输出（V1.5+）

---

## 接口契约

```python
# src/songyan/llm/client.py
from langchain_core.language_models.chat_models import BaseChatModel

async def get_llm(temperature: float = 0.7) -> BaseChatModel:
    """获取配置好的 LLM 实例."""
    ...

# src/songyan/agents/goal_planner.py
from songyan.db.repository import ChapterGoalRepository
from songyan.models.chapter import ChapterGoal
from songyan.models.project import ProjectSetting
from songyan.models.genre import GenreProfile
from songyan.models.creative_mode import CreativeModeProfile

async def define_chapter_goal(
    db: ChapterGoalRepository,
    project: ProjectSetting,
    genre_profile: GenreProfile,
    mode_profile: CreativeModeProfile,
    chapter_number: int,
    previous_summary: str = "",
    character_states: list[dict] | None = None,
) -> ChapterGoal:
    """制定章节目标.
    
    1. 加载 Prompt 模板
    2. 组装输入变量（项目设定 + Genre + Mode + 最近剧情）
    3. 调用 LLM（temperature=0.7）
    4. 解析 JSON 输出为 ChapterGoal
    5. 通过 Repository 保存
    6. 返回 ChapterGoal
    """
    ...
```

---

## 数据模型

本任务**不新增** Pydantic 模型，复用已有模型：

- `ChapterGoal`（`models/chapter.py`）— 已存在
- `ProjectSetting`（`models/project.py`）— 已存在
- `GenreProfile`（`models/genre.py`）— 已存在
- `CreativeModeProfile`（`models/creative_mode.py`）— 已存在

**新增异常类**（`exceptions.py`）：

```python
class SongyanError(Exception):
    """Base exception."""
    ...

class LLMError(SongyanError):
    """LLM API 调用失败（重试后仍失败）."""
    ...

class LLMResponseParseError(SongyanError):
    """LLM 返回内容无法解析为预期格式."""
    ...
```

---

## Prompt 模板规范

### prompts/goal_planner.md

```markdown
你是 Songyan 的目标规划师。请根据以下信息制定第 {{ chapter_number }} 章的写作目标。

## 项目设定
题材：{{ genre_name }}
创作模式：{{ mode_name }}
主角：{{ protagonist_name }}（{{ protagonist_background }}）
核心爽点：{{ core_hook }}
基调：{{ tone }}
读者预期：{{ target_reader_expectation }}
禁忌：{{ taboos }}

## Genre Profile 规则
{{ genre_pacing_rule }}
爽点类型：{{ genre_satisfaction_types }}
章节类型：{{ genre_chapter_types }}

## CreativeModeProfile 约束
{{ mode_constraints }}

## 最近剧情
{{ recent_summaries }}

## 输出要求

请输出严格的 JSON，格式如下：

```json
{
  "chapter_number": {{ chapter_number }},
  "previous_summary": "{{ recent_summaries }}",
  "target_events": ["事件1", "事件2"],
  "emotional_arc": "情感走向描述",
  "hooks": ["章末钩子1"],
  "obligations": ["必须兑现的承诺1"],
  "word_count_target": 3000,
  "chapter_type": "从章节类型列表中选择"
}
```

要求：
1. target_events 要具体可执行（1-3 个），不要笼统
2. hooks 必须有信息量，不能是空洞的"悬念"
3. 遵循题材节奏规则
4. 遵守创作模式的约束
5. word_count_target 在 2000-5000 之间
```

---

## 测试要求

### Layer 1: LLM Client 测试
- [ ] `get_llm()` 返回正确类型的实例（mock 配置）
- [ ] 重试逻辑：第 1/2 次失败、第 3 次成功 → 最终成功
- [ ] 重试逻辑：3 次都失败 → 抛 `LLMError`
- [ ] 环境变量缺失时给出明确错误

### Layer 2: GoalPlanner 测试
- [ ] **正向用例**：Mock LLM 返回合法 JSON → 成功解析为 `ChapterGoal`
- [ ] **Prompt 组装验证**：确认所有必要变量被注入（genre_pacing_rule、mode_constraints 等）
- [ ] **约束遵守**：`word_count_target` 在 2000-5000 范围内（若 LLM 返回越界，clamp 或 warning）
- [ ] **chapter_type 验证**：从 `GenreProfile.chapter_types` 中选择（若 LLM 返回无效值，fallback 到第一个）
- [ ] **Repository 保存**：调用 `db.create()` 成功
- [ ] **异常用例**：LLM 返回非 JSON → `LLMResponseParseError`
- [ ] **异常用例**：LLM 返回 JSON 但字段缺失 → 用默认值填充
- [ ] **异常用例**：LLM 返回 JSON 但字段类型错误 → `LLMResponseParseError`

### Layer 3: 集成测试（如适用）
- [ ] 从 SQLite 加载项目 → GoalPlanner → 保存 ChapterGoal → 可查询（可选，用内存 DB）

### Mock 策略
- LLM 调用使用 `unittest.mock.AsyncMock` 或 `pytest-asyncio` 的 `mocker.patch`
- Repository 使用 `AsyncMock`
- 不依赖真实 LLM API（测试必须离线通过）

---

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/test_goal_planner.py -v` 全部通过（≥ 10 个测试）
- [ ] `pytest tests/test_llm_client.py -v` 全部通过（≥ 4 个测试）
- [ ] 代码符合 CLAUDE.md 规范（类型标注、单文件 < 400 行等）
- [ ] 不违反任何不可违背规则
- [ ] Prompt 模板放在 `prompts/goal_planner.md`，不在 Python 代码中写长字符串
- [ ] LLM Client 使用 `ChatLiteLLM`，温度 0.7
- [ ] 错误处理使用自定义异常（`LLMError`、`LLMResponseParseError`）
- [ ] 更新了 `docs/STATUS.md`
- [ ] 生成了 `tasks/008-goal-planner-DONE.md` 交接文件

---

## 参考文档

- `docs/architecture/04-vibe-coding-engineering.md` — Task 008 原始定义
- `docs/architecture/05-tech-reference.md` — LLM Client 技术实现参考
- `docs/architecture/02-vibe-coding-prompts.md` — GoalPlanner Prompt 模板（§3.1）
- `src/songyan/models/chapter.py` — ChapterGoal 模型
- `src/songyan/db/repository.py` — ChapterGoalRepository
