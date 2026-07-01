# Task 009: 实现 CreativeDirector Agent

> **Phase**: Phase 2
> **优先级**: P0
> **依赖**: Task 002（数据模型）, Task 004（Repository）, Task 005（Genre Profile）, Task 006（CreativeModeProfile）, Task 008（GoalPlanner）
> **预计工作量**: 中

---

## Goal

实现创作导演 Agent——在 Writer 动笔前，基于 GoalPlanner 输出的 ChapterGoal，生成本章的 `CreativeBrief`（创作意图 + 张力地图 + 禁忌清单）。

---

## Context

CreativeDirector 是写前阶段的第二个 Agent，职责是"不写正文，只输出结构化指令"。

在整体流程中的位置：
```
GoalPlanner → CreativeDirector → ContextManager → Writer → ...
```

输入来自 GoalPlanner 的 `ChapterGoal` + 项目数据（Genre Profile、角色状态、CreativeModeProfile），输出为 `CreativeBrief`，保存到 SQLite `creative_briefs` 表。

---

## In Scope（必须完成）

### 1. CreativeDirector Agent 核心

- `src/songyan/agents/creative_director.py`:
  - `async def generate_creative_brief(...)` —— 主入口
  - `async def _call_llm_for_brief(...)` —— LLM 调用 + 解析
  - `def _build_creative_prompt(...)` —— Prompt 组装（从 `prompts/creative_director.md` 加载模板）
  - `def _parse_llm_response(...)` —— 解析 LLM 返回为 `CreativeBrief`

### 2. Prompt 模板

- `prompts/creative_director.md`: CreativeDirector 专用 Prompt 模板
  - 基于设计文档 `CREATIVE_DIRECTOR_PROMPT`
  - Jinja2 风格占位符
  - 明确输出 JSON Schema（含 `required_tensions`, `forbidden_patterns` 等）

### 3. 数据流

```python
async def generate_creative_brief(
    db: CreativeBriefRepository,
    project_id: str,
    chapter_goal: ChapterGoal,
    genre_profile: GenreProfile,
    mode_profile: CreativeModeProfile,
    characters: list[Character],
    previous_summary: str = "",
) -> CreativeBrief
```

**输出要求**：
- `creative_intent`: 1-2 句话概括本章核心创作意图（不是剧情梗概，而是"要在读者心中制造什么效果"）
- `required_tensions`: 1-3 个张力对象，每个包含 tension_id, description, tension_type, characters_involved, intensity
- `forbidden_patterns`: 至少 3 个具体套路（"不要出现 XXX" 而不是"不要写得不好"）
- `allowed_fissures`: 允许保留的裂隙列表
- `style_constraints`: 风格约束列表
- `reader_contract`: 1 句话概括本章对读者的"承诺"

### 4. 约束遵守

- 遵守 `GenreProfile.taboos`（题材禁忌注入 Prompt）
- 遵守 `CreativeModeProfile` 约束（模式参数注入 Prompt）
- `forbidden_patterns` 必须具体（不能是空洞的）
- `required_tensions` 必须有有效的 `tension_type`（从枚举中选）
- 温度 0.7（与 GoalPlanner 相同，需要创造性）

### 5. 错误处理

| 错误类型 | 处理方式 |
|----------|----------|
| LLM API 错误 | 指数退避重试 3 次，最终抛 `LLMError` |
| LLM 返回非 JSON | 尝试提取 JSON 块，失败则抛 `LLMResponseParseError` |
| Pydantic 验证失败 | 记录原始输出，抛 `LLMResponseParseError` |
| tension_type 无效 | 过滤掉无效的 Tension，记录 warning |

---

## Out of Scope（明确不做）

- 不写正文（Writer 负责）
- 不做审查（RuleAuditor/LLMAuditor 负责）
- 不做修订（RevisionHandler 负责）
- 不做状态结算（SettlementExtractor 负责）
- ContextManager（Task 010）

---

## 接口契约

```python
# src/songyan/agents/creative_director.py
from songyan.db.review_repo import CreativeBriefRepository
from songyan.models.chapter import ChapterGoal
from songyan.models.creative_mode import CreativeBrief, CreativeModeProfile
from songyan.models.genre import GenreProfile
from songyan.models.character import Character

async def generate_creative_brief(
    db: CreativeBriefRepository,
    project_id: str,
    chapter_goal: ChapterGoal,
    genre_profile: GenreProfile,
    mode_profile: CreativeModeProfile,
    characters: list[Character],
    previous_summary: str = "",
) -> CreativeBrief:
    """生成本章创作导演简报.

    1. 加载并渲染 Prompt 模板
    2. 调用 LLM（temperature=0.7）
    3. 解析 JSON 输出为 CreativeBrief
    4. 通过 Repository 保存
    5. 返回 CreativeBrief
    """
    ...
```

---

## 数据模型

本任务**不新增** Pydantic 模型，复用已有模型：

- `CreativeBrief`（`models/creative_mode.py`）— 已存在
- `Tension`（`models/creative_mode.py`）— 已存在
- `ChapterGoal`（`models/chapter.py`）— 已存在
- `GenreProfile`（`models/genre.py`）— 已存在
- `CreativeModeProfile`（`models/creative_mode.py`）— 已存在
- `Character`（`models/character.py`）— 已存在

---

## 测试要求

### Layer 1: 单元测试
- [ ] `_extract_json` 正确提取 markdown 代码块中的 JSON
- [ ] `_parse_llm_response` 解析合法 JSON 成功
- [ ] `_parse_llm_response` 非法 JSON 抛出 `LLMResponseParseError`
- [ ] `_build_creative_brief` 完整数据构建成功
- [ ] `_build_creative_brief` 无效 `tension_type` 被过滤
- [ ] `_build_creative_brief` 字段缺失使用默认值

### Layer 2: Agent 集成测试（Mock LLM）
- [ ] 正常流程：Mock LLM 返回合法 JSON → 成功解析为 `CreativeBrief`
- [ ] Prompt 组装验证：确认所有必要变量被注入
- [ ] `forbidden_patterns` 至少 3 个（若 LLM 返回不足，补默认值）
- [ ] `required_tensions` 1-3 个，有效 tension_type
- [ ] Repository 保存：调用 `db.create()` 成功
- [ ] LLM 解析失败：抛出 `LLMResponseParseError`
- [ ] LLM 调用失败：抛出 `LLMError`

### Mock 策略
- LLM 调用使用 `AsyncMock` mock `call_llm`
- Repository 使用 `AsyncMock`
- 不依赖真实 LLM API

---

## 验收标准（Acceptance Criteria）

- [ ] `pytest tests/test_creative_director.py -v` 全部通过（≥ 10 个测试）
- [ ] 代码符合 CLAUDE.md 规范（类型标注、单文件 < 400 行等）
- [ ] Prompt 模板放在 `prompts/creative_director.md`，不在代码中写长字符串
- [ ] 错误处理使用自定义异常（`LLMError`, `LLMResponseParseError`）
- [ ] 更新了 `docs/STATUS.md`
- [ ] 生成了 `tasks/009-creative-director-DONE.md` 交接文件

---

## 参考文档

- `docs/architecture/04-vibe-coding-engineering.md` — Task 009 原始定义
- `docs/architecture/02-vibe-coding-prompts.md` — CreativeDirector Prompt 模板（§3.2）
- `src/songyan/models/creative_mode.py` — CreativeBrief, Tension 模型
- `src/songyan/db/review_repo.py` — CreativeBriefRepository
